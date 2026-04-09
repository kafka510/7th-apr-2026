"""
Celery tasks for data collection: acquisition (5-min, 30-min), timeout alert,
SolarGIS daily (stub), and daily loss calculation trigger.

Acquisition tasks run on queue data_acquisition; others on default.
"""
import logging
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, time as dt_time, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Tuple

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from data_collection.services.acquisition_runner import run_acquisition_for_interval
from data_collection.services.solar_window import _parse_timezone_offset_minutes
from shared_app.utils.email_utils import build_email_subject

logger = logging.getLogger(__name__)

# Threshold (seconds) for "acquisition took too long" email
try:
    ACQUISITION_TIMEOUT_SECONDS = int(getattr(settings, "ACQUISITION_TIMEOUT_SECONDS", 300))
except (TypeError, ValueError):
    ACQUISITION_TIMEOUT_SECONDS = 300

DATA_ACQUISITION_ALERT_EMAIL = getattr(
    settings,
    "DATA_ACQUISITION_ALERT_EMAIL",
    getattr(settings, "SECURITY_ALERT_EMAIL", None),
)

LOSS_CALCULATION_REPORT_EMAIL = getattr(
    settings,
    "LOSS_CALCULATION_REPORT_EMAIL",
    getattr(settings, "SECURITY_ALERT_EMAIL", None),
)

DATA_ACQUISITION_REPORT_EMAIL = getattr(
    settings,
    "DATA_ACQUISITION_REPORT_EMAIL",
    DATA_ACQUISITION_ALERT_EMAIL or LOSS_CALCULATION_REPORT_EMAIL,
)

try:
    MAX_FUSION_SOLAR_BACKFILL_DEFERS = int(getattr(settings, "MAX_FUSION_SOLAR_BACKFILL_DEFERS", 30))
except (TypeError, ValueError):
    MAX_FUSION_SOLAR_BACKFILL_DEFERS = 30

try:
    FUSION_SOLAR_BACKFILL_RESUME_LOCAL_HOUR = int(getattr(settings, "FUSION_SOLAR_BACKFILL_RESUME_LOCAL_HOUR", 0))
except (TypeError, ValueError):
    FUSION_SOLAR_BACKFILL_RESUME_LOCAL_HOUR = 0

try:
    FUSION_SOLAR_BACKFILL_RESUME_LOCAL_MINUTE = int(getattr(settings, "FUSION_SOLAR_BACKFILL_RESUME_LOCAL_MINUTE", 10))
except (TypeError, ValueError):
    FUSION_SOLAR_BACKFILL_RESUME_LOCAL_MINUTE = 10


def _fusion_solar_has_quota_407(out: Optional[Dict[str, Any]], fallback_error: str = "") -> bool:
    """
    Return True when adapter output indicates Huawei historical API quota/throttle (failCode=407).
    Checks structured fields and free-text fallback.
    """
    text_bits: List[str] = []
    if isinstance(out, dict):
        if str(out.get("failCode") or out.get("fail_code") or "") == "407":
            return True
        provider_failures = out.get("provider_failures") or []
        if isinstance(provider_failures, list):
            text_bits.extend([str(x) for x in provider_failures if x is not None])
        err = out.get("error")
        if err:
            text_bits.append(str(err))
    if fallback_error:
        text_bits.append(str(fallback_error))
    joined = " | ".join(text_bits)
    return "failCode=407" in joined or "failCode 407" in joined or "fail_code=407" in joined


def _resolve_asset_timezone_offset_minutes(asset_code: Optional[str]) -> Optional[int]:
    """Resolve timezone offset minutes from AssetList.timezone for a given asset."""
    if not asset_code:
        return None
    try:
        from main.models import AssetList

        tz_raw = (
            AssetList.objects.filter(asset_code=asset_code)
            .values_list("timezone", flat=True)
            .first()
        )
        return _parse_timezone_offset_minutes(str(tz_raw) if tz_raw is not None else None)
    except Exception:
        logger.exception("Failed resolving asset timezone for %s", asset_code)
        return None


def _next_day_resume_eta(now_dt: datetime, tz_offset_minutes: Optional[int] = None) -> datetime:
    """
    Schedule retry at next local day based on asset timezone, then convert to UTC for Celery ETA.
    """
    offset = int(tz_offset_minutes or 0)
    now_utc = now_dt.astimezone(dt_timezone.utc)
    local_now = now_utc + timedelta(minutes=offset)
    next_local_day = (local_now + timedelta(days=1)).date()
    local_resume = datetime.combine(
        next_local_day,
        dt_time(
            hour=FUSION_SOLAR_BACKFILL_RESUME_LOCAL_HOUR,
            minute=FUSION_SOLAR_BACKFILL_RESUME_LOCAL_MINUTE,
        ),
    )
    resume_utc = (local_resume - timedelta(minutes=offset)).replace(tzinfo=dt_timezone.utc)
    return resume_utc


@shared_task
def send_celery_test_email(recipient_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a single test email via Celery to verify workers are functional.

    Used by the test_celery_workers management command. Runs on default queue.
    """
    to = recipient_email or getattr(settings, "SECURITY_ALERT_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL")
    if not to:
        return {"success": False, "error": "No recipient (set SECURITY_ALERT_EMAIL or pass recipient_email)"}
    subject = build_email_subject("[Celery Test] Workers are active and functional")
    body = (
        "This email was sent by a Celery worker.\n\n"
        "If you received it, the Celery worker is active and the email backend is working.\n\n"
        "Sent from the data_collection test (send_celery_test_email task)."
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
        return {"success": True, "recipient": to}
    except Exception as e:
        logger.exception("send_celery_test_email failed")
        return {"success": False, "error": str(e), "recipient": to}


def _check_acquisition_timeout_and_alert(
    task_id: str,
    start_time: float,
    task_name: str,
) -> None:
    """If elapsed time > ACQUISITION_TIMEOUT_SECONDS, enqueue send_acquisition_timeout_alert."""
    elapsed = time.time() - start_time
    if elapsed > ACQUISITION_TIMEOUT_SECONDS and DATA_ACQUISITION_ALERT_EMAIL:
        send_acquisition_timeout_alert.delay(
            task_id=task_id,
            start_iso=datetime.utcfromtimestamp(start_time).isoformat() + "Z",
            duration_seconds=round(elapsed, 1),
            task_name=task_name,
        )


@shared_task(bind=True)
def run_data_acquisition(self, sun_hours_check: bool = True) -> Dict[str, Any]:
    """
    Run 5-minute data acquisition for all assets configured with interval=5.

    Runs on queue data_acquisition 24/7 at schedule. If run exceeds ACQUISITION_TIMEOUT_SECONDS,
    an email alert is sent. sun_hours_check is deprecated and ignored (no run-level gate).
    """
    start = time.time()
    task_id = self.request.id or "unknown"
    # Log job lifecycle in LossCalculationTask (generic background job log)
    from main.models import log_loss_task_started, log_loss_task_completed

    log_loss_task_started(task_id)
    try:
        result = run_acquisition_for_interval(
            interval_minutes=5,
            sun_hours_check=sun_hours_check,
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition",
        )
        processed = int(result.get("success_count", 0) or 0)
        failed = int(result.get("failed_count", 0) or 0)
        # Send failure email only when an asset fails (no email on successful runs)
        results = result.get("results") or []
        for r in results:
            if not r.get("success"):
                send_data_acquisition_failure_email.delay(
                    asset_code=r.get("asset_code", "?"),
                    adapter_id=r.get("adapter_id", "?"),
                    error=str(r.get("error", "unknown")),
                    interval_minutes=5,
                )
        log_loss_task_completed(
            task_id=task_id,
            success=failed == 0,
            processed_devices=processed,
            failed_devices=failed,
        )
        return result
    except Exception as e:
        logger.exception("run_data_acquisition failed")
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=str(e),
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition",
        )
        raise


@shared_task(bind=True)
def run_data_acquisition_30min(
    self,
    sun_hours_check: bool = True,
    replace_all_day_data: bool = False,
    duration_days: int = 0,
) -> Dict[str, Any]:
    """
    Run 30-minute data acquisition for all assets configured with interval=30.

    Runs on queue data_acquisition 24/7 at schedule. sun_hours_check is deprecated and ignored.
    """
    start = time.time()
    task_id = self.request.id or "unknown"
    from main.models import log_loss_task_started, log_loss_task_completed

    log_loss_task_started(task_id)
    try:
        result = run_acquisition_for_interval(
            interval_minutes=30,
            sun_hours_check=sun_hours_check,
            replace_all_day_data=replace_all_day_data,
            duration_days=duration_days,
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition_30min",
        )
        processed = int(result.get("success_count", 0) or 0)
        failed = int(result.get("failed_count", 0) or 0)
        results = result.get("results") or []
        for r in results:
            if not r.get("success"):
                send_data_acquisition_failure_email.delay(
                    asset_code=r.get("asset_code", "?"),
                    adapter_id=r.get("adapter_id", "?"),
                    error=str(r.get("error", "unknown")),
                    interval_minutes=30,
                )
        log_loss_task_completed(
            task_id=task_id,
            success=failed == 0,
            processed_devices=processed,
            failed_devices=failed,
        )
        return result
    except Exception as e:
        logger.exception("run_data_acquisition_30min failed")
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=str(e),
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition_30min",
        )
        raise


@shared_task(bind=True)
def run_data_acquisition_hourly(
    self,
    sun_hours_check: bool = True,
    duration_days: int = 0,
) -> Dict[str, Any]:
    """
    Run hourly data acquisition for all assets configured with interval=60.

    Intended for Laplace minute data pull every hour.
    On demand, optional duration_days>0 enables sequential hour-by-hour backfill.
    Runs on queue data_acquisition 24/7 at schedule. sun_hours_check is deprecated and ignored.
    """
    start = time.time()
    task_id = self.request.id or "unknown"
    from main.models import log_loss_task_started, log_loss_task_completed

    log_loss_task_started(task_id)
    try:
        result = run_acquisition_for_interval(
            interval_minutes=60,
            sun_hours_check=sun_hours_check,
            duration_days=duration_days,
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition_hourly",
        )
        processed = int(result.get("success_count", 0) or 0)
        failed = int(result.get("failed_count", 0) or 0)
        results = result.get("results") or []
        for r in results:
            if not r.get("success"):
                send_data_acquisition_failure_email.delay(
                    asset_code=r.get("asset_code", "?"),
                    adapter_id=r.get("adapter_id", "?"),
                    error=str(r.get("error", "unknown")),
                    interval_minutes=60,
                )
        log_loss_task_completed(
            task_id=task_id,
            success=failed == 0,
            processed_devices=processed,
            failed_devices=failed,
        )
        return result
    except Exception as e:
        logger.exception("run_data_acquisition_hourly failed")
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=str(e),
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition_hourly",
        )
        raise


@shared_task(bind=True)
def run_data_acquisition_daily(self, sun_hours_check: bool = False) -> Dict[str, Any]:
    """
    Run daily data acquisition for all assets configured with interval=1440 (Daily).

    Runs on queue data_acquisition. sun_hours_check is deprecated and ignored (no run-level gate).
    """
    start = time.time()
    task_id = self.request.id or "unknown"
    from main.models import log_loss_task_started, log_loss_task_completed

    log_loss_task_started(task_id)
    try:
        result = run_acquisition_for_interval(
            interval_minutes=1440,
            sun_hours_check=sun_hours_check,
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition_daily",
        )
        processed = int(result.get("success_count", 0) or 0)
        failed = int(result.get("failed_count", 0) or 0)
        results = result.get("results") or []
        for r in results:
            if not r.get("success"):
                send_data_acquisition_failure_email.delay(
                    asset_code=r.get("asset_code", "?"),
                    adapter_id=r.get("adapter_id", "?"),
                    error=str(r.get("error", "unknown")),
                    interval_minutes=1440,
                )
        log_loss_task_completed(
            task_id=task_id,
            success=failed == 0,
            processed_devices=processed,
            failed_devices=failed,
        )
        return result
    except Exception as e:
        logger.exception("run_data_acquisition_daily failed")
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=str(e),
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_data_acquisition_daily",
        )
        raise


@shared_task
def send_acquisition_timeout_alert(
    task_id: str,
    start_iso: str,
    duration_seconds: float,
    task_name: str,
) -> None:
    """
    Send email when a data-acquisition task ran longer than the timeout threshold.

    Runs on default queue (so general workers send the email).
    """
    if not DATA_ACQUISITION_ALERT_EMAIL:
        logger.warning("DATA_ACQUISITION_ALERT_EMAIL not set; skipping timeout alert")
        return
    subject = build_email_subject(
        f"[Data Acquisition] Task exceeded {ACQUISITION_TIMEOUT_SECONDS}s: {task_name}"
    )
    body = (
        f"Task ID: {task_id}\n"
        f"Task name: {task_name}\n"
        f"Started (UTC): {start_iso}\n"
        f"Duration: {duration_seconds:.1f} seconds\n"
        f"Threshold: {ACQUISITION_TIMEOUT_SECONDS} seconds\n\n"
        "Consider increasing the number of data-acquisition workers to avoid backlog."
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_ALERT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send acquisition timeout email: %s", e)


@shared_task
def send_solargis_ingest_completion_email(
    date_window: str,
    duration_seconds: float,
    total_sites: int,
    success_count: int,
    failed_count: int,
    total_api_calls: int = 0,
    errors: Optional[List[str]] = None,
) -> None:
    """Send email after SolarGIS daily ingest completes. Runs on default queue."""
    if not DATA_ACQUISITION_REPORT_EMAIL:
        logger.warning("DATA_ACQUISITION_REPORT_EMAIL not set; skipping SolarGIS completion email")
        return
    errors = errors or []
    subject = build_email_subject(
        "[Data Acquisition] SolarGIS daily ingest completed"
    )
    err_block = "\n".join(errors[:50]) if errors else "None"
    if len(errors) > 50:
        err_block += f"\n... and {len(errors) - 50} more."
    body = (
        f"Date window fetched (last 3 days): {date_window}\n"
        f"Duration: {duration_seconds:.1f} seconds\n"
        f"Total API calls: {total_api_calls}\n"
        f"Sites processed (source assets): {total_sites}\n"
        f"Successful: {success_count}\n"
        f"Failed: {failed_count}\n\n"
        f"Errors:\n{err_block}"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_REPORT_EMAIL],
            fail_silently=False,
        )
        logger.info(
            "SolarGIS completion email sent to %s (sites=%d success=%d failed=%d)",
            DATA_ACQUISITION_REPORT_EMAIL,
            total_sites,
            success_count,
            failed_count,
        )
    except Exception as e:
        logger.exception("Failed to send SolarGIS completion email: %s", e)


@shared_task
def send_solargis_failure_email(asset_code: str, error: str) -> None:
    """Send email when SolarGIS ingest fails for a single asset. Runs on default queue."""
    if not DATA_ACQUISITION_ALERT_EMAIL:
        return
    subject = build_email_subject(
        f"[Data Acquisition] SolarGIS failed for {asset_code}"
    )
    body = f"Asset/site: {asset_code}\n\nError: {error}"
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_ALERT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send SolarGIS failure email: %s", e)


@shared_task
def send_data_acquisition_failure_email(
    asset_code: str,
    adapter_id: str,
    error: str,
    interval_minutes: Optional[int] = None,
    extra_details: Optional[Dict[str, Any]] = None,
) -> None:
    """Send email when any data acquisition adapter fails for a single asset. Runs on default queue."""
    if not DATA_ACQUISITION_ALERT_EMAIL:
        return
    subject = build_email_subject(
        f"[Data Acquisition] {adapter_id} failed for {asset_code}"
    )
    body_parts = [
        f"Asset: {asset_code}",
        f"Adapter: {adapter_id}",
        f"Error: {error}",
    ]
    if interval_minutes is not None:
        body_parts.append(f"Schedule: {interval_minutes}-min run")
    if extra_details:
        for k, v in extra_details.items():
            if v is not None and v != "" and v != []:
                body_parts.append(f"{k}: {v}")
    body = "\n\n".join(body_parts)
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_ALERT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send data acquisition failure email: %s", e)


@shared_task
def send_data_acquisition_backfill_partial_failure_email(
    date_from: str,
    date_to: str,
    written: List[Dict[str, Any]],
    failed_or_missed: List[Dict[str, Any]],
    errors: Optional[List[str]] = None,
) -> None:
    """
    Send email when Fusion Solar backfill has partial failure or missed data.
    written: list of {"asset_code", "points_written"}; failed_or_missed: list of {"asset_code", "error"}.
    """
    if not DATA_ACQUISITION_ALERT_EMAIL:
        return
    errors = errors or []
    subject = build_email_subject("[Data Acquisition] Fusion Solar backfill: partial failure or missed data")
    written_block = "\n".join(f"  {w.get('asset_code', '?')}: {w.get('points_written', 0)} points" for w in written[:30])
    if len(written) > 30:
        written_block += f"\n  ... and {len(written) - 30} more assets."
    failed_block = "\n".join(f"  {f.get('asset_code', '?')}: {f.get('error', 'unknown')}" for f in failed_or_missed[:30])
    if len(failed_or_missed) > 30:
        failed_block += f"\n  ... and {len(failed_or_missed) - 30} more."
    err_block = "\n".join(errors[:20]) if errors else "None"
    body = (
        f"Date range: {date_from} to {date_to}\n\n"
        f"What was written:\n{written_block or '  None'}\n\n"
        f"Failed or missed:\n{failed_block or '  None'}\n\n"
        f"Errors:\n{err_block}"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_ALERT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send backfill partial failure email: %s", e)


@shared_task
def send_fusion_solar_backfill_progress_email(
    date_from: str,
    date_to: str,
    total_assets: int,
    completed_assets: int,
    remaining_assets: int,
    written_today: int,
    failed_today: int,
    defer_count: int,
    next_eta_utc: str,
    next_eta_local: str,
    remaining_asset_codes: Optional[List[str]] = None,
) -> None:
    """Send daily progress update when backfill is deferred due to provider limit."""
    if not DATA_ACQUISITION_ALERT_EMAIL:
        return
    remaining_asset_codes = remaining_asset_codes or []
    preview = ", ".join(remaining_asset_codes[:30]) if remaining_asset_codes else "None"
    if len(remaining_asset_codes) > 30:
        preview += f", ... (+{len(remaining_asset_codes) - 30} more)"
    queue_len = len(remaining_asset_codes) if remaining_asset_codes else int(remaining_assets)
    subject = build_email_subject("[Data Acquisition] Fusion Solar backfill deferred (daily limit)")
    body = (
        f"Date range: {date_from} to {date_to}\n"
        f"Total assets in run: {total_assets}\n\n"
        f"Fully completed assets (cumulative): {completed_assets}\n"
        f"  (Entire date range finished for that asset; not incremented if failCode=407 stopped mid-asset.)\n"
        f"Assets still queued for continuation: {queue_len}\n"
        f"  (Includes the current asset if the daily limit hit before its backfill finished.)\n\n"
        f"Assets with points written this session: {written_today}\n"
        f"  (May be partial for one asset when 407 occurred after some chunks succeeded.)\n"
        f"Failed/missed this session: {failed_today}\n"
        f"Deferral number (this continuation chain): {defer_count}\n\n"
        f"Next run (local, from first queued asset timezone in AssetList): {next_eta_local}\n"
        f"Next run (UTC): {next_eta_utc}\n"
        f"(If offset shows +0 min, check AssetList.timezone for the first remaining asset.)\n\n"
        f"Remaining asset codes preview:\n{preview}"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_ALERT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send Fusion Solar backfill progress email: %s", e)


@shared_task
def send_data_acquisition_completion_email(
    interval_minutes: int,
    duration_seconds: float,
    total: int,
    success_count: int,
    failed_count: int,
    errors: Optional[List[str]] = None,
    devices_with_no_datapoints: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Send summary email after a 5/30/1440-min acquisition run.
    devices_with_no_datapoints: list of {"asset_code": str, "adapter_id": str, "device_ids": list}.
    Runs on default queue.
    """
    if not DATA_ACQUISITION_REPORT_EMAIL:
        return
    errors = errors or []
    devices_with_no_datapoints = devices_with_no_datapoints or []
    subject = build_email_subject(
        f"[Data Acquisition] {interval_minutes}-min run completed"
    )
    err_block = "\n".join(errors[:50]) if errors else "None"
    if len(errors) > 50:
        err_block += f"\n... and {len(errors) - 50} more."
    no_data_block = "None"
    if devices_with_no_datapoints:
        lines = []
        for item in devices_with_no_datapoints[:30]:
            ac = item.get("asset_code", "?")
            ad = item.get("adapter_id", "?")
            dids = item.get("device_ids") or []
            lines.append(f"  {ac} ({ad}): {', '.join(str(d) for d in dids[:20])}{' ...' if len(dids) > 20 else ''}")
        no_data_block = "\n".join(lines)
        if len(devices_with_no_datapoints) > 30:
            no_data_block += f"\n  ... and {len(devices_with_no_datapoints) - 30} more assets with devices with no data."
    body = (
        f"Interval: {interval_minutes} min\n"
        f"Duration: {duration_seconds:.1f} seconds\n"
        f"Total assets: {total}\n"
        f"Successful: {success_count}\n"
        f"Failed: {failed_count}\n\n"
        f"Errors:\n{err_block}\n\n"
        f"Devices with no datapoints this run:\n{no_data_block}"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DATA_ACQUISITION_REPORT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send data acquisition completion email: %s", e)


@shared_task(bind=True)
def run_fusion_solar_backfill(
    self,
    asset_codes: List[str],
    date_from: str,
    date_to: str,
    adapter_id: str = "fusion_solar",
    adapter_account_id: int | None = None,
    start_asset_index: int = 0,
    defer_count: int = 0,
    original_total_assets: Optional[int] = None,
    completed_assets: int = 0,
) -> Dict[str, Any]:
    """
    Run Fusion Solar data backfill for the given assets and date range.
    Superuser-only; exposed via Background jobs UI.
    For each asset loads adapter config and calls fetch_and_store with date_from/date_to in config.
    If any asset fails or has no data written, sends partial-failure email.
    """
    from data_collection.adapters import fetch_and_store as adapter_fetch_and_store
    from data_collection.models import AssetAdapterConfig

    asset_codes = [str(c).strip() for c in (asset_codes or []) if c and str(c).strip()]
    date_from = (date_from or "").strip()
    date_to = (date_to or "").strip()
    if not date_from or not date_to:
        return {"success": False, "error": "date_from and date_to are required (YYYY-MM-DD)"}
    try:
        from_d = datetime.strptime(date_from, "%Y-%m-%d").date()
        to_d = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError:
        return {"success": False, "error": "date_from/date_to must be YYYY-MM-DD"}
    if from_d > to_d:
        return {"success": False, "error": "date_from cannot be after date_to"}
    # No hard day-range cap here; adapter handles provider-safe request splitting.
    if not asset_codes:
        return {"success": True, "reason": "no_assets", "written": [], "failed": []}
    if start_asset_index < 0:
        start_asset_index = 0
    if start_asset_index >= len(asset_codes):
        return {
            "success": True,
            "reason": "resume_index_past_end",
            "written": [],
            "failed_or_missed": [],
            "errors": [],
            "start_asset_index": start_asset_index,
        }
    try:
        completed_assets = max(0, int(completed_assets or 0))
    except (TypeError, ValueError):
        completed_assets = 0
    try:
        original_total_assets = int(original_total_assets) if original_total_assets is not None else None
    except (TypeError, ValueError):
        original_total_assets = None
    if not original_total_assets or original_total_assets <= 0:
        original_total_assets = max(len(asset_codes) + completed_assets, len(asset_codes))

    qs = AssetAdapterConfig.objects.filter(
        adapter_id=adapter_id,
        asset_code__in=asset_codes,
    ).select_related("adapter_account")
    if adapter_account_id is not None:
        qs = qs.filter(adapter_account_id=adapter_account_id)
    configs = list(qs)
    config_by_asset = {r.asset_code: r.get_effective_config() for r in configs}
    written: List[Dict[str, Any]] = []
    failed_or_missed: List[Dict[str, Any]] = []
    errors: List[str] = []

    quota_deferred = False
    deferred_task_id: Optional[str] = None
    deferred_remaining_assets: List[str] = []
    completed_in_this_run = 0
    for idx in range(start_asset_index, len(asset_codes)):
        asset_code = asset_codes[idx]
        config = config_by_asset.get(asset_code)
        if not config:
            failed_or_missed.append({"asset_code": asset_code, "error": "No Fusion Solar config or not enabled"})
            errors.append(f"[{asset_code}] No config")
            completed_in_this_run += 1
            continue
        config = dict(config)
        config["date_from"] = date_from
        config["date_to"] = date_to
        config["acquisition_interval_minutes"] = config.get("acquisition_interval_minutes", 5)
        try:
            out = adapter_fetch_and_store(asset_code=asset_code, adapter_id="fusion_solar", config=config)
            if out.get("success"):
                pts = int(out.get("points_written", 0) or 0)
                written.append({"asset_code": asset_code, "points_written": pts})
                if _fusion_solar_has_quota_407(out):
                    quota_deferred = True
                    deferred_remaining_assets = asset_codes[idx:]
                    errors.append(f"[{asset_code}] Historical API limit reached (failCode=407). Deferred remaining assets to next day.")
                    logger.warning(
                        "Fusion Solar backfill hit failCode=407 while processing %s; deferring %s assets",
                        asset_code,
                        len(deferred_remaining_assets),
                    )
                    break
                if pts == 0:
                    failed_or_missed.append({"asset_code": asset_code, "error": "No data written (0 points)"})
                completed_in_this_run += 1
            else:
                err_text = str(out.get("error", "unknown"))
                failed_or_missed.append({"asset_code": asset_code, "error": err_text})
                errors.append(f"[{asset_code}] {err_text}")
                if _fusion_solar_has_quota_407(out, err_text):
                    quota_deferred = True
                    deferred_remaining_assets = asset_codes[idx:]
                    errors.append(f"[{asset_code}] Historical API limit reached (failCode=407). Deferred remaining assets to next day.")
                    logger.warning(
                        "Fusion Solar backfill hit failCode=407 while processing %s; deferring %s assets",
                        asset_code,
                        len(deferred_remaining_assets),
                    )
                    break
                completed_in_this_run += 1
        except Exception as e:
            failed_or_missed.append({"asset_code": asset_code, "error": str(e)})
            errors.append(f"[{asset_code}] {e}")
            logger.exception("Fusion Solar backfill failed for %s", asset_code)
            if _fusion_solar_has_quota_407(None, str(e)):
                quota_deferred = True
                deferred_remaining_assets = asset_codes[idx:]
                errors.append(f"[{asset_code}] Historical API limit reached (failCode=407). Deferred remaining assets to next day.")
                break
            completed_in_this_run += 1

    completed_assets_total = min(original_total_assets, completed_assets + completed_in_this_run)
    remaining_assets_total = max(original_total_assets - completed_assets_total, 0)
    if quota_deferred and deferred_remaining_assets:
        remaining_assets_total = len(deferred_remaining_assets)

    if quota_deferred and deferred_remaining_assets:
        if int(defer_count or 0) >= MAX_FUSION_SOLAR_BACKFILL_DEFERS:
            limit_msg = (
                f"Backfill defer limit reached ({MAX_FUSION_SOLAR_BACKFILL_DEFERS}) after repeated failCode=407. "
                "No further automatic retries scheduled."
            )
            errors.append(limit_msg)
            for ac in deferred_remaining_assets:
                failed_or_missed.append({"asset_code": ac, "error": limit_msg})
            quota_deferred = False
            logger.error(limit_msg)
        else:
            first_remaining_asset = deferred_remaining_assets[0] if deferred_remaining_assets else None
            asset_offset_minutes = _resolve_asset_timezone_offset_minutes(first_remaining_asset)
            eta = _next_day_resume_eta(timezone.now(), tz_offset_minutes=asset_offset_minutes)
            async_result = run_fusion_solar_backfill.apply_async(
                kwargs={
                    "asset_codes": deferred_remaining_assets,
                    "date_from": date_from,
                    "date_to": date_to,
                    "adapter_id": adapter_id,
                    "adapter_account_id": adapter_account_id,
                    "start_asset_index": 0,
                    "defer_count": int(defer_count or 0) + 1,
                    "original_total_assets": original_total_assets,
                    "completed_assets": completed_assets_total,
                },
                eta=eta,
            )
            deferred_task_id = async_result.id
            local_eta = (
                (eta + timedelta(minutes=int(asset_offset_minutes or 0))).replace(tzinfo=None).isoformat(sep=" ")
                + f" (asset offset {asset_offset_minutes:+d} min)"
            )
            logger.info(
                "Fusion Solar backfill deferred due to failCode=407. next_task_id=%s eta_utc=%s eta_local=%s remaining_assets=%s",
                deferred_task_id,
                eta.isoformat(),
                local_eta,
                deferred_remaining_assets,
            )
            send_fusion_solar_backfill_progress_email.delay(
                date_from=date_from,
                date_to=date_to,
                total_assets=original_total_assets,
                completed_assets=completed_assets_total,
                remaining_assets=remaining_assets_total,
                written_today=len(written),
                failed_today=len(failed_or_missed),
                defer_count=int(defer_count or 0) + 1,
                next_eta_utc=eta.isoformat(),
                next_eta_local=local_eta,
                remaining_asset_codes=deferred_remaining_assets,
            )

    if failed_or_missed and DATA_ACQUISITION_ALERT_EMAIL:
        send_data_acquisition_backfill_partial_failure_email.delay(
            date_from=date_from,
            date_to=date_to,
            written=written,
            failed_or_missed=failed_or_missed,
            errors=errors,
        )

    return {
        "success": (len(failed_or_missed) == 0) and (not quota_deferred),
        "date_from": date_from,
        "date_to": date_to,
        "written": written,
        "failed_or_missed": failed_or_missed,
        "errors": errors,
        "quota_deferred": quota_deferred,
        "deferred_task_id": deferred_task_id,
        "deferred_remaining_assets": deferred_remaining_assets,
        "defer_count": int(defer_count or 0),
        "original_total_assets": original_total_assets,
        "completed_assets": completed_assets_total,
        "remaining_assets": remaining_assets_total,
    }


@shared_task(bind=True)
def run_fusion_solar_oem_daily_kpi(
    self,
    asset_codes: List[str],
    date_from: str,
    date_to: str,
    adapter_id: str = "fusion_solar",
    adapter_account_id: int | None = None,
) -> Dict[str, Any]:
    """
    Fusion Solar getDevKpiDay only (devTypeId 1 string inverters): upserts kpis.oem_daily_product_kwh (creates row if needed).
    date_from/date_to: inclusive month range (YYYY-MM or YYYY-MM-DD); one getDevKpiDay call per month (collectTime in ms).
    Does not run 5-minute historical backfill or realtime timeseries acquisition.

    Result extras when some API batches fail: ``oem_daily_kpi_errors_by_asset`` (asset_code -> messages),
    ``oem_daily_kpi_assets_with_api_errors`` (sorted codes), and per-row ``oem_daily_kpi_errors`` only for that asset.
    """
    from data_collection.adapters.fusion_solar import fusion_solar_sync_oem_daily_kpis_for_assets_bundle
    from data_collection.models import AssetAdapterConfig

    asset_codes = [str(c).strip() for c in (asset_codes or []) if c and str(c).strip()]
    date_from = (date_from or "").strip()
    date_to = (date_to or "").strip()
    if not date_from or not date_to:
        return {"success": False, "error": "date_from and date_to are required (YYYY-MM or YYYY-MM-DD month range)"}
    if not asset_codes:
        return {"success": True, "reason": "no_assets", "results": [], "oem_daily_kpi_rows_updated_total": 0}

    qs = AssetAdapterConfig.objects.filter(
        adapter_id=adapter_id,
        asset_code__in=asset_codes,
    ).select_related("adapter_account")
    if adapter_account_id is not None:
        qs = qs.filter(adapter_account_id=adapter_account_id)
    configs = list(qs)
    config_by_asset = {r.asset_code: r.get_effective_config() for r in configs}
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_oem_updates = 0
    oem_api_errors_by_asset: Dict[str, List[str]] = defaultdict(list)

    for ac in asset_codes:
        if ac not in config_by_asset:
            msg = "No Fusion Solar config or not enabled for this asset"
            results.append({"asset_code": ac, "success": False, "error": msg})
            errors.append(f"[{ac}] {msg}")

    configured = [ac for ac in asset_codes if ac in config_by_asset]
    cred_groups: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for ac in configured:
        cfg = config_by_asset[ac]
        cfg_dict = dict(cfg) if isinstance(cfg, dict) else {}
        key = (
            (cfg_dict.get("api_base_url") or "").strip(),
            (cfg_dict.get("username") or "").strip(),
            (cfg_dict.get("password") or cfg_dict.get("system_code") or "").strip(),
        )
        cred_groups[key].append(ac)

    for key, group_assets in cred_groups.items():
        group_assets = sorted(set(group_assets))
        base_u, user_u, _pass_u = key
        if not base_u or not user_u or not _pass_u:
            for ac in group_assets:
                msg = "Incomplete Fusion Solar credentials in adapter config"
                results.append({"asset_code": ac, "success": False, "error": msg})
                errors.append(f"[{ac}] {msg}")
            continue
        cfg0 = config_by_asset[group_assets[0]]
        try:
            out = fusion_solar_sync_oem_daily_kpis_for_assets_bundle(
                group_assets,
                dict(cfg0),
                date_from,
                date_to,
            )
        except Exception as e:
            logger.exception("Fusion Solar OEM daily KPI sync failed for %s", group_assets)
            for ac in group_assets:
                results.append({"asset_code": ac, "success": False, "error": str(e)})
                errors.append(f"[{ac}] {e}")
            continue
        if out.get("success"):
            by_asset = out.get("oem_daily_kpi_rows_updated_by_asset") or {}
            eba = out.get("oem_daily_kpi_errors_by_asset") or {}
            for err_ac, msgs in eba.items():
                if isinstance(msgs, list):
                    oem_api_errors_by_asset[err_ac].extend(str(m) for m in msgs if m is not None)
            for ac in group_assets:
                n = int(by_asset.get(ac, 0) or 0)
                total_oem_updates += n
                asset_errs = list(eba.get(ac) or [])
                row: Dict[str, Any] = {"asset_code": ac, "success": True, "oem_daily_kpi_rows_updated": n}
                if asset_errs:
                    row["oem_daily_kpi_errors"] = asset_errs
                    row["oem_daily_kpi_had_api_errors"] = True
                results.append(row)
        else:
            err = str(out.get("error", "unknown"))
            for ac in group_assets:
                results.append({"asset_code": ac, "success": False, "error": err})
                errors.append(f"[{ac}] {err}")

    unknown_parent_errs = list(oem_api_errors_by_asset.get("__unknown_parent__", []))
    clean_eba = {
        k: v for k, v in oem_api_errors_by_asset.items() if v and k != "__unknown_parent__"
    }
    assets_with_api_errors = sorted(clean_eba.keys())
    out: Dict[str, Any] = {
        "success": len(errors) == 0,
        "date_from": date_from,
        "date_to": date_to,
        "oem_daily_kpi_rows_updated_total": total_oem_updates,
        "results": results,
        "errors": errors,
    }
    if clean_eba:
        out["oem_daily_kpi_errors_by_asset"] = clean_eba
        out["oem_daily_kpi_assets_with_api_errors"] = assets_with_api_errors
    if unknown_parent_errs:
        out["oem_daily_kpi_errors_unknown_parent_batch"] = unknown_parent_errs

    if assets_with_api_errors:
        logger.info(
            "Fusion Solar OEM daily KPI finished: %s asset(s) had at least one getDevKpiDay batch failure: %s",
            len(assets_with_api_errors),
            ", ".join(assets_with_api_errors[:50]) + ("…" if len(assets_with_api_errors) > 50 else ""),
        )

    return out


@shared_task(bind=True)
def run_laplace_span_historical_backfill(
    self,
    date_from: str,
    date_to: str,
    asset_codes: Optional[List[str]] = None,
    split_batch_size: int = 5,
) -> Dict[str, Any]:
    """
    Run Laplace CSV historical backfill via span.php for enabled laplaceid assets.

    Uses calendar from/to dates (YYYY-MM-DD). For each date in range and each asset:
    - csv_api=span.php
    - unit=minute
    - from=YYYYMMDD00
    - to=YYYYMMDD23
    """
    from data_collection.adapters import fetch_and_store as adapter_fetch_and_store
    from data_collection.models import AssetAdapterConfig
    from main.models import log_loss_task_started, log_loss_task_completed

    start = time.time()
    task_id = getattr(self.request, "id", None) or "unknown"
    log_loss_task_started(task_id)

    try:
        date_from = (date_from or "").strip()
        date_to = (date_to or "").strip()
        if not date_from or not date_to:
            return {"success": False, "error": "date_from and date_to are required (YYYY-MM-DD)"}
        try:
            from_d = datetime.strptime(date_from, "%Y-%m-%d").date()
            to_d = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            return {"success": False, "error": "date_from/date_to must be YYYY-MM-DD"}
        if from_d > to_d:
            return {"success": False, "error": "date_from cannot be after date_to"}

        day_count = (to_d - from_d).days + 1
        if day_count > 31:
            return {"success": False, "error": "Maximum allowed range is 31 days"}

        requested_assets = [str(c).strip() for c in (asset_codes or []) if c and str(c).strip()]
        qs = AssetAdapterConfig.objects.filter(adapter_id="laplaceid", enabled=True).select_related("adapter_account")
        if requested_assets:
            qs = qs.filter(asset_code__in=requested_assets)
        configs = list(qs.order_by("asset_code"))
        if not configs:
            return {"success": True, "reason": "no_enabled_laplace_assets", "results": []}

        results: List[Dict[str, Any]] = []
        success_count = 0
        failed_count = 0
        total_points = 0
        missing_assets: List[str] = []
        if requested_assets:
            configured = {c.asset_code for c in configs}
            missing_assets = [a for a in requested_assets if a not in configured]

        try:
            batch_size = int(split_batch_size or 5)
        except (TypeError, ValueError):
            batch_size = 5
        if batch_size <= 0:
            batch_size = 5

        # Split work into smaller asset batches to reduce long continuous runs and isolate failures.
        for i in range(0, len(configs), batch_size):
            batch = configs[i : i + batch_size]
            for row in batch:
                asset_code = row.asset_code
                base_cfg = dict(row.get_effective_config())
                base_cfg["acquisition_interval_minutes"] = 60
                base_cfg["csv_api"] = "span.php"
                base_cfg["unit"] = "minute"
                base_cfg["data"] = str(base_cfg.get("data") or "measuringdata")
                base_cfg["type"] = str(base_cfg.get("type") or "pcs")

                asset_points = 0
                asset_ok = True
                first_error = None
                for offset_days in range(day_count):
                    cur = from_d + timedelta(days=offset_days)
                    cfg = dict(base_cfg)
                    cfg["from"] = cur.strftime("%Y%m%d") + "00"
                    cfg["to"] = cur.strftime("%Y%m%d") + "23"
                    out = adapter_fetch_and_store(asset_code=asset_code, adapter_id="laplaceid", config=cfg)
                    if out.get("success"):
                        pts = int(out.get("points_written", 0) or 0)
                        asset_points += pts
                        total_points += pts
                    else:
                        asset_ok = False
                        if first_error is None:
                            first_error = str(out.get("error", "unknown"))
                        logger.warning(
                            "Laplace span backfill failed for %s day=%s: %s",
                            asset_code,
                            cur.isoformat(),
                            out.get("error", "unknown"),
                        )

                entry: Dict[str, Any] = {
                    "asset_code": asset_code,
                    "success": asset_ok,
                    "days_requested": day_count,
                    "points_written": asset_points,
                }
                if not asset_ok:
                    entry["error"] = first_error or "one or more day fetches failed"
                results.append(entry)
                if asset_ok:
                    success_count += 1
                else:
                    failed_count += 1

        out = {
            "success": failed_count == 0,
            "date_from": from_d.isoformat(),
            "date_to": to_d.isoformat(),
            "days_requested": day_count,
            "asset_count": len(configs),
            "requested_asset_count": len(requested_assets) if requested_assets else len(configs),
            "missing_assets": missing_assets,
            "split_batch_size": batch_size,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_points_written": total_points,
            "results": results,
        }
        log_loss_task_completed(
            task_id=task_id,
            success=failed_count == 0,
            processed_devices=success_count,
            failed_devices=failed_count,
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_laplace_span_historical_backfill",
        )
        return out
    except Exception as e:
        logger.exception("run_laplace_span_historical_backfill failed")
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=str(e),
        )
        _check_acquisition_timeout_and_alert(
            task_id=task_id,
            start_time=start,
            task_name="run_laplace_span_historical_backfill",
        )
        raise


@shared_task(bind=True)
def run_solargis_daily_ingest(
    self,
    run_at_utc_hour: Optional[int] = None,
    run_at_utc_minute: Optional[int] = None,
    hourly: bool = False,
    on_demand: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    asset_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Daily SolarGIS ingest: invoke SolarGIS adapter for SOURCE assets.

    Schedule modes:
    - hourly=True (recommended): run every hour (e.g. crontab 0 * * * *). Processes all
      source assets whose configured run time falls in the current UTC hour (same hour).
      So each site runs when its configured time has arrived in that hour slot.
    - hourly=False with run_at_utc_hour/minute: process only assets whose configured
      run time exactly matches (run_at_utc_hour, run_at_utc_minute). Legacy/single-slot.
    - on_demand=True: process ALL source assets regardless of configured run time.

    Optional date_from, date_to (ISO dates) override the default last-3-days window.
    """
    from data_collection.adapters import fetch_and_store as adapter_fetch_and_store
    from data_collection.models import AssetAdapterConfig
    from data_collection.solargis_schedule import get_daily_run_utc
    from main.models import AssetList, log_loss_task_started, log_loss_task_completed

    start = time.time()
    task_id = getattr(self.request, "id", None) or "unknown"
    log_loss_task_started(task_id)
    now = timezone.now()
    today = now.date()
    default_from = (today - timedelta(days=3)).isoformat()
    default_to = (today - timedelta(days=1)).isoformat()
    date_from_str = (date_from and str(date_from).strip()) or default_from
    date_to_str = (date_to and str(date_to).strip()) or default_to
    date_window = f"{date_from_str} to {date_to_str}"

    # Hourly mode: use current UTC hour; include assets whose configured run hour == current hour
    if hourly:
        current_hour = now.hour
        run_at = (current_hour, 0)  # used only for logging
        logger.info(
            "run_solargis_daily_ingest: hourly=True current_utc_hour=%s date_window=%s",
            current_hour,
            date_window,
        )
    else:
        run_at = (
            int(run_at_utc_hour) if run_at_utc_hour is not None else 2,
            int(run_at_utc_minute) if run_at_utc_minute is not None else 0,
        )
        logger.info(
            "run_solargis_daily_ingest: on_demand=%s run_at=%s date_window=%s",
            on_demand,
            run_at,
            date_window,
        )

    configs = list(
        AssetAdapterConfig.objects.filter(adapter_id="solargis", enabled=True).select_related("adapter_account")
    )
    source_configs: List[Dict] = []
    for row in configs:
        asset_code = row.asset_code
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            logger.warning("run_solargis_daily_ingest: asset %s not in asset_list, skipping", asset_code)
            continue
        # Use effective config (account credentials + per-asset overrides when adapter_account is set)
        cfg = row.get_effective_config()
        # When an adapter account is linked, force api_url/api_key to come from the account only
        if row.adapter_account_id:
            account_cfg = dict(getattr(row.adapter_account, "config", {}) or {})
            cfg = dict(cfg)
            cfg["api_url"] = (account_cfg.get("api_url") or "").strip()
            cfg["api_key"] = (account_cfg.get("api_key") or account_cfg.get("subscription_token") or "").strip()
        # Solargis API uses "subscription token"; adapter expects config["api_key"]. Normalize if stored as subscription_token.
        if not (cfg.get("api_key") or "").strip() and (cfg.get("subscription_token") or "").strip():
            cfg = dict(cfg)
            cfg["api_key"] = (cfg.get("subscription_token") or "").strip()
        # Ensure we have credentials: Solargis requires api_url and api_key (subscription token)
        api_url_val = (cfg.get("api_url") or "").strip()
        api_key_val = (cfg.get("api_key") or "").strip()
        account_src = row.adapter_account_id if row.adapter_account_id else "inline"
        logger.info(
            "run_solargis_daily_ingest: asset %s config source=adapter_account_id=%s api_url_present=%s api_key_present=%s",
            asset_code,
            account_src,
            bool(api_url_val),
            bool(api_key_val),
        )
        if not api_url_val or not api_key_val:
            logger.warning(
                "run_solargis_daily_ingest: skipping %s - missing api_url or api_key in effective config (adapter_account_id=%s). "
                "Check Adapter Account config has api_url and api_key, or set them in the asset adapter config.",
                asset_code,
                account_src,
            )
            continue
        cfg["date_from"] = date_from_str
        cfg["date_to"] = date_to_str
        if not on_demand:
            asset_run = get_daily_run_utc(cfg)
            if hourly:
                if asset_run[0] != now.hour:
                    continue
            else:
                if asset_run != run_at:
                    continue
        consumers = list(
            AssetList.objects.filter(
                satellite_irradiance_source_asset_code=asset_code
            ).values_list("asset_code", flat=True)
        )
        cfg["linked_asset_codes"] = consumers
        source_configs.append({"asset_code": asset_code, "config": cfg})

    # On-demand: optionally restrict to selected asset codes (empty list = run none)
    if on_demand and asset_codes is not None:
        if len(asset_codes) == 0:
            source_configs = []
        else:
            allowed = {c.strip() for c in asset_codes if c and str(c).strip()}
            if allowed:
                source_configs = [r for r in source_configs if r["asset_code"] in allowed]

    if not source_configs:
        logger.info("run_solargis_daily_ingest: no source assets for solargis")
        log_loss_task_completed(
            task_id=task_id,
            success=True,
            processed_devices=0,
            failed_devices=0,
        )
        return {"success": True, "reason": "no_assets", "assets_processed": 0, "total_api_calls": 0}

    success_count = 0
    failed_count = 0
    errors: List[str] = []
    total_api_calls = 0

    for row in source_configs:
        asset_code = row["asset_code"]
        try:
            out = adapter_fetch_and_store(
                asset_code=asset_code,
                adapter_id="solargis",
                config=row["config"],
            )
            total_api_calls += 1  # 1 API call per source
            if out.get("success"):
                success_count += 1
            else:
                failed_count += 1
                err_msg = str(out.get("error", "unknown"))
                errors.append(f"[{asset_code}] {err_msg}")
                logger.warning(
                    "SolarGIS ingest failed for %s: %s",
                    asset_code,
                    err_msg,
                )
                send_solargis_failure_email.delay(asset_code=asset_code, error=err_msg)
        except Exception as e:
            failed_count += 1
            err_msg = str(e)
            errors.append(f"[{asset_code}] {err_msg}")
            logger.exception("SolarGIS ingest failed for %s", asset_code)
            send_solargis_failure_email.delay(asset_code=asset_code, error=err_msg)

    duration = time.time() - start

    # Always queue completion email task so it appears in Celery logs; task no-ops if no recipient set
    send_solargis_ingest_completion_email.delay(
        date_window=date_window,
        duration_seconds=duration,
        total_sites=len(source_configs),
        success_count=success_count,
        failed_count=failed_count,
        total_api_calls=total_api_calls,
        errors=errors,
    )
    logger.info(
        "run_solargis_daily_ingest: queued completion email (recipient=%s)",
        DATA_ACQUISITION_REPORT_EMAIL or "not set",
    )

    # Solargis API call count is incremented in the adapter on each request (so all callers are counted).

    success = failed_count == 0
    log_loss_task_completed(
        task_id=task_id,
        success=success,
        error_message="\n".join(errors[:10]) if errors and not success else None,
        processed_devices=success_count,
        failed_devices=failed_count,
    )

    return {
        "success": success,
        "reason": "ok",
        "assets_processed": len(source_configs),
        "success_count": success_count,
        "failed_count": failed_count,
        "total_api_calls": total_api_calls,
        "duration_seconds": round(duration, 1),
        "errors": errors,
    }


@shared_task(bind=True)
def run_hourly_dispatcher(self) -> Dict[str, Any]:
    """
    Hourly dispatcher for SolarGIS + loss.

    - SolarGIS: trigger run_solargis_daily_ingest(hourly=True), which uses adapter config
      to decide which assets should run in the current UTC hour.
    - Loss: for each asset, compute its local time from AssetList.timezone and, when the
      local hour matches a configured trigger hour (default 23), enqueue run_asset_daily_loss
      for the previous local calendar day.
    """
    from django.conf import settings
    from main.models import AssetList, log_loss_task_started, log_loss_task_completed

    now = timezone.now()
    task_id = getattr(self.request, "id", None) or "unknown"
    results: Dict[str, Any] = {
        "solargis_triggered": False,
        "loss_assets_triggered": 0,
        "loss_assets_skipped": 0,
        "errors": [],
    }

    # 1. SolarGIS: reuse existing hourly mode
    try:
        run_solargis_daily_ingest.delay(hourly=True)
        results["solargis_triggered"] = True
    except Exception as e:
        logger.exception("run_hourly_dispatcher: failed to enqueue SolarGIS ingest: %s", e)
        results["errors"].append(f"solargis: {str(e)}")

    # 2. Loss: per-asset local-time trigger
    trigger_hour_local = getattr(settings, "LOSS_LOCAL_TRIGGER_HOUR", 23)

    assets = AssetList.objects.all().values("asset_code", "timezone")
    for row in assets:
        asset_code = row["asset_code"]
        tz_str = row.get("timezone") or ""
        try:
            offset_min = _parse_timezone_offset_minutes(tz_str)
            if offset_min is None:
                offset_min = 0
            local_dt = now + timedelta(minutes=offset_min)
            local_hour = local_dt.hour
            if local_hour != int(trigger_hour_local):
                results["loss_assets_skipped"] += 1
                continue

            # Previous local calendar day for this asset
            prev_local_date = (local_dt.date() - timedelta(days=1)).isoformat()

            try:
                run_asset_daily_loss.delay(asset_code=asset_code, calculation_date_iso=prev_local_date)
                results["loss_assets_triggered"] += 1
            except Exception as e:
                logger.exception(
                    "run_hourly_dispatcher: failed to enqueue run_asset_daily_loss for %s: %s",
                    asset_code,
                    e,
                )
                results["errors"].append(f"loss[{asset_code}]: {str(e)}")
        except Exception as e:
            logger.exception("run_hourly_dispatcher: error processing asset %s: %s", asset_code, e)
            results["errors"].append(f"asset[{asset_code}]: {str(e)}")

    # Log completion of hourly dispatcher itself
    log_loss_task_started(task_id)
    log_loss_task_completed(
        task_id=task_id,
        success=not results["errors"],
        error_message="\n".join(results["errors"]) if results["errors"] else None,
        processed_devices=results.get("loss_assets_triggered", 0),
        failed_devices=len(results["errors"]),
    )

    return results


def _parse_calculation_date(calculation_date_iso: Optional[str]) -> date:
    """Return calculation date (UTC calendar date). Default: yesterday."""
    if calculation_date_iso:
        try:
            return datetime.strptime(calculation_date_iso.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return (timezone.now() - timedelta(days=1)).date()


def _end_of_day_utc(d: date):
    """Return timezone-aware datetime for end of day d in UTC (23:59:59)."""
    naive = datetime.combine(d, dt_time(23, 59, 59))
    return timezone.make_aware(naive, timezone.utc)


@shared_task(bind=True)
def run_asset_daily_loss(self, asset_code: str, calculation_date_iso: str) -> Dict[str, Any]:
    """
    Run loss calculation for one asset for the given date (end-of-day timestamp).

    Calls calculate_string_loss for each **configured and enabled** string device.
    Used by run_daily_loss_calculation. This task **does not wait** for per-device tasks;
    it enqueues them and returns a summary.
    """
    from main.calculations.tasks import calculate_string_loss
    from main.models import (
        get_configured_loss_string_devices_for_asset,
        log_loss_task_started,
        log_loss_task_completed,
    )

    task_id = getattr(getattr(self, "request", None), "id", None)
    if task_id:
        log_loss_task_started(task_id)

    try:
        calc_date = _parse_calculation_date(calculation_date_iso)
        end_ts = _end_of_day_utc(calc_date)

        strings_qs = get_configured_loss_string_devices_for_asset(asset_code)
        strings = list(strings_qs.values_list("device_id", flat=True))
        if not strings:
            if task_id:
                log_loss_task_completed(
                    task_id,
                    success=True,
                    processed_devices=0,
                    failed_devices=0,
                )
            return {
                "asset_code": asset_code,
                "success_count": 0,
                "failed_count": 0,
                "errors": [f"No configured string devices for asset {asset_code}"],
                "queued_devices": 0,
                "device_tasks": [],
            }

        device_tasks: List[Dict[str, Any]] = []

        for device_id in strings:
            try:
                task = calculate_string_loss.delay(
                    device_id=device_id,
                    timestamp=end_ts,
                    asset_code=asset_code,
                )
                device_tasks.append({"device_id": device_id, "task_id": task.id})
            except Exception as e:
                logger.warning("Failed to enqueue loss calculation for %s: %s", device_id, e)

        if task_id:
            log_loss_task_completed(
                task_id,
                success=True,
                processed_devices=len(strings),
                failed_devices=0,
            )

        return {
            "asset_code": asset_code,
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "queued_devices": len(device_tasks),
            "device_tasks": device_tasks,
        }
    except Exception as e:
        logger.exception("run_asset_daily_loss failed for %s: %s", asset_code, e)
        if task_id:
            log_loss_task_completed(
                task_id,
                success=False,
                error_message=str(e),
            )
        return {
            "asset_code": asset_code,
            "success_count": 0,
            "failed_count": 0,
            "errors": [str(e)],
            "queued_devices": 0,
            "device_tasks": [],
        }


@shared_task
def send_loss_calculation_completion_email(
    calculation_date_iso: str,
    duration_seconds: float,
    total_assets: int,
    success_count: int,
    failed_count: int,
    errors: List[str],
) -> None:
    """Send email after daily loss calculation completes. Runs on default queue."""
    if not LOSS_CALCULATION_REPORT_EMAIL:
        logger.warning("LOSS_CALCULATION_REPORT_EMAIL not set; skipping completion email")
        return
    subject = build_email_subject(
        f"[Loss Calculation] Daily run completed – {calculation_date_iso}"
    )
    err_block = "\n".join(errors[:50]) if errors else "None"
    if len(errors) > 50:
        err_block += f"\n... and {len(errors) - 50} more."
    body = (
        f"Calculation date: {calculation_date_iso}\n"
        f"Duration: {duration_seconds:.1f} seconds\n"
        f"Assets processed: {total_assets}\n"
        f"Successful: {success_count}\n"
        f"Failed: {failed_count}\n\n"
        f"Errors:\n{err_block}"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[LOSS_CALCULATION_REPORT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send loss calculation completion email: %s", e)


@shared_task(bind=True)
def run_daily_loss_calculation(self, calculation_date_iso: Optional[str] = None) -> Dict[str, Any]:
    """
    Run daily loss calculation for all assets (sun-down).

    Resolves calculation date (default: previous day), enqueues run_asset_daily_loss for each
    asset and returns immediately with a summary of queued per-asset tasks.
    Runs on default queue. Does **not** wait for completion or send email; monitoring is via logs/job log.
    """
    start = time.time()
    calc_date = _parse_calculation_date(calculation_date_iso)
    calc_date_str = calc_date.isoformat()

    from main.models import AssetList, log_loss_task_enqueued, log_loss_task_started, log_loss_task_completed

    task_id = getattr(getattr(self, "request", None), "id", None) or "unknown"

    # Mark orchestrator as started in loss task log
    log_loss_task_started(task_id)

    asset_codes = list(AssetList.objects.values_list("asset_code", flat=True).distinct())
    if not asset_codes:
        logger.info("run_daily_loss_calculation: no assets")
        return {
            "success": True,
            "reason": "no_assets",
            "calculation_date": calc_date_str,
            "assets_processed": 0,
            "assets_queued": 0,
            "errors": [],
        }

    all_errors: List[str] = []
    asset_tasks: List[Dict[str, Any]] = []

    for asset_code in asset_codes:
        try:
            task = run_asset_daily_loss.delay(asset_code=asset_code, calculation_date_iso=calc_date_str)
            asset_tasks.append({"asset_code": asset_code, "task_id": task.id})
            # Log per-asset task as enqueued
            if task.id:
                log_loss_task_enqueued(
                    task_id=task.id,
                    task_name="data_collection.tasks.run_asset_daily_loss",
                    asset_code=asset_code,
                )
        except Exception as e:
            all_errors.append(f"[{asset_code}] enqueue_failed: {str(e)}")
            logger.exception("Failed to enqueue run_asset_daily_loss for %s", asset_code)

    duration = time.time() - start

    # Mark orchestrator completion in loss task log
    log_loss_task_completed(
        task_id=task_id,
        success=len(all_errors) == 0,
        error_message="\n".join(all_errors[:10]) if all_errors else None,
    )

    return {
        "success": len(all_errors) == 0,
        "reason": "queued",
        "calculation_date": calc_date_str,
        "assets_processed": len(asset_codes),
        "assets_queued": len(asset_tasks),
        "duration_seconds": round(duration, 1),
        "errors": all_errors,
        "asset_tasks": asset_tasks[:200],
    }
