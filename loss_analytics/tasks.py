"""
Celery tasks for loss_analytics.

- transpose_asset_ghi_to_gii: run GHI→GII transposition for an asset/date range.
- run_string_loss_for_date_range: one task per string device (expected + actual + loss).
- run_inverter_expected_power_for_date_range: one task per inverter (expected power from GII).
- run_asset_loss_pipeline: orchestrator — optionally runs transpose, then enqueues one task per device.
- run_scheduled_expected_power_after_sunset: Beat-scheduled; for each asset in night window, runs expected power for that day.
"""
import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Optional

from celery import shared_task
from django.utils import timezone as django_timezone

from loss_analytics.pipeline.transpose_runner import run_transpose, parse_dt_utc
from loss_analytics.pipeline import config_resolver
from main.models import AssetList, device_list, log_loss_task_started, log_loss_task_completed

logger = logging.getLogger(__name__)


def _parse_iso_dt_utc(dt_str: str) -> datetime:
    """Parse ISO date/datetime string to timezone-aware UTC. Naive strings treated as UTC."""
    s = (dt_str or "").strip()
    if not s:
        raise ValueError("empty datetime")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if django_timezone.is_naive(dt):
        dt = django_timezone.make_aware(dt, dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


@shared_task(bind=True, queue="default")
def transpose_asset_ghi_to_gii(
    self,
    asset_code: str,
    irradiance_device_id: str,
    start_date: str,
    end_date: str,
    metric: str = "ghi",
) -> dict:
    """
    Run GHI→GII transposition for the given asset and date range. Writes GII
    to timeseries_data. Accepts start_date and end_date as strings (ISO or
    date-only); naive datetimes are interpreted in asset timezone.

    Returns dict with success, records_written, device_ids_used, error, etc.
    """
    task_id = str(getattr(getattr(self, "request", None), "id", "") or "")
    if task_id:
        try:
            log_loss_task_started(task_id)
        except Exception:
            pass
    try:
        asset = AssetList.objects.filter(asset_code=asset_code).first()
        if not asset:
            res = {"success": False, "error": f"Asset {asset_code} not found", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=res["error"])
                except Exception:
                    pass
            return res

        start_date_utc = parse_dt_utc(start_date, asset)
        end_date_utc = parse_dt_utc(end_date, asset)
        if start_date_utc >= end_date_utc:
            res = {"success": False, "error": "start_date must be before end_date", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=res["error"])
                except Exception:
                    pass
            return res

        result = run_transpose(
            asset_code=asset_code,
            irradiance_device_id=irradiance_device_id,
            start_date_utc=start_date_utc,
            end_date_utc=end_date_utc,
            metric=metric or "ghi",
        )
        result["task_id"] = task_id
        if task_id:
            try:
                log_loss_task_completed(
                    task_id,
                    success=bool(result.get("success")),
                    error_message=result.get("error"),
                )
            except Exception:
                pass
        return result
    except Exception as e:
        logger.exception("transpose_asset_ghi_to_gii failed: %s", e)
        res = {"success": False, "error": str(e), "task_id": task_id}
        if task_id:
            try:
                log_loss_task_completed(task_id, success=False, error_message=res["error"])
            except Exception:
                pass
        return res

@shared_task(bind=True, queue="default")
def run_string_loss_for_date_range(
    self,
    device_id: str,
    start_date: str,
    end_date: str,
    time_interval_minutes: int = 15,
) -> dict:
    """
    Run loss calculation for a single string device over a date range.
    Uses main.calculations.CalculationService.calculate_string_loss_sync.
    Returns result dict with success, device_id, task_id, error, etc.
    """
    task_id = str(getattr(getattr(self, "request", None), "id", "") or "")
    if task_id:
        try:
            log_loss_task_started(task_id)
        except Exception:
            pass
    try:
        device = device_list.objects.filter(device_id=device_id).first()
        if not device:
            res = {"success": False, "device_id": device_id, "error": "Device not found", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=res["error"])
                except Exception:
                    pass
            return res
        asset = AssetList.objects.filter(asset_code=device.parent_code).first()
        if not asset:
            res = {"success": False, "device_id": device_id, "error": "Asset not found", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=res["error"])
                except Exception:
                    pass
            return res
        start_dt = parse_dt_utc(start_date, asset)
        end_dt = parse_dt_utc(end_date, asset)
        if start_dt >= end_dt:
            res = {"success": False, "device_id": device_id, "error": "start_date must be before end_date", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=res["error"])
                except Exception:
                    pass
            return res
        from loss_analytics.calculations import CalculationService
        result = CalculationService().calculate_string_loss_sync(
            device_id=device_id,
            start_date=start_dt,
            end_date=end_dt,
            time_interval_minutes=time_interval_minutes,
        )
        result["task_id"] = task_id
        if task_id:
            try:
                log_loss_task_completed(
                    task_id,
                    success=bool(result.get("success")),
                    error_message=result.get("error"),
                    processed_devices=1 if result.get("success") else 0,
                    failed_devices=0 if result.get("success") else 1,
                )
            except Exception:
                pass
        return result
    except Exception as e:
        logger.exception("run_string_loss_for_date_range failed for %s: %s", device_id, e)
        res = {"success": False, "device_id": device_id, "error": str(e), "task_id": task_id}
        if task_id:
            try:
                log_loss_task_completed(task_id, success=False, error_message=res["error"])
            except Exception:
                pass
        return res


@shared_task(bind=True, queue="default")
def run_inverter_expected_power_for_date_range(
    self,
    inverter_id: str,
    asset_code: str,
    start_date: str,
    end_date: str,
    inverter_efficiency: float = 0.97,
) -> dict:
    """
    Run inverter expected power (from GII) for a date range and persist to timeseries_data.
    Uses main.calculations.inverter_expected_power_service.compute_and_persist_inverter_expected_power.
    """
    task_id = str(getattr(getattr(self, "request", None), "id", "") or "")
    if task_id:
        try:
            log_loss_task_started(task_id)
        except Exception:
            pass
    try:
        start_dt = _parse_iso_dt_utc(start_date)
        end_dt = _parse_iso_dt_utc(end_date)
        logger.info(
            "run_inverter_expected_power_for_date_range: inverter_id=%s asset_code=%s start_date=%s end_date=%s -> start_dt=%s end_dt=%s",
            inverter_id,
            asset_code,
            start_date,
            end_date,
            start_dt.isoformat() if start_dt else None,
            end_dt.isoformat() if end_dt else None,
        )
        if start_dt >= end_dt:
            res = {"success": False, "inverter_id": inverter_id, "error": "start_date must be before end_date", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=res["error"])
                except Exception:
                    pass
            return res
        from loss_analytics.calculations.inverter_expected_power_service import (
            compute_and_persist_inverter_expected_power,
        )
        res = compute_and_persist_inverter_expected_power(
            asset_code=asset_code,
            inverter_id=inverter_id,
            start_ts=start_dt,
            end_ts=end_dt,
            inverter_efficiency=inverter_efficiency,
        )
        # After expected power is persisted, generate state-aware loss events for this inverter.
        # This is DB-backed and intentionally avoids cache.
        logger.info(
            "Loss event phase: inverter_id=%s asset_code=%s start_ts=%s end_ts=%s",
            inverter_id,
            asset_code,
            start_dt.isoformat(),
            end_dt.isoformat(),
        )
        try:
            from loss_analytics.calculations.inverter_loss_event_service import (
                compute_and_persist_inverter_loss_events,
            )

            power_model_name = getattr(res, "power_model_used", None) or "sdm"
            ev_res = compute_and_persist_inverter_loss_events(
                asset_code=asset_code,
                inverter_id=inverter_id,
                start_ts=start_dt,
                end_ts=end_dt,
                power_model_name=power_model_name,
            )
        except Exception as e:
            logger.exception("Loss event generation failed for inverter %s: %s", inverter_id, e)
            ev_res = None
        out = {
            "success": True,
            "inverter_id": inverter_id,
            "task_id": task_id,
            "points_written": res.points_written,
            "points_skipped_missing_gii": res.points_skipped_missing_gii,
            "groups_count": res.groups_count,
            "loss_events": (
                {
                    "events_created": getattr(ev_res, "events_created", 0),
                    "deleted_existing_events": getattr(ev_res, "deleted_existing_events", 0),
                    "points_used": getattr(ev_res, "points_used", 0),
                    "warnings": getattr(ev_res, "warnings", []) or [],
                    "loss_metric": getattr(ev_res, "loss_metric", None),
                    "loss_points_written": getattr(ev_res, "loss_points_written", 0),
                }
                if ev_res is not None
                else {
                    "events_created": 0,
                    "deleted_existing_events": 0,
                    "points_used": 0,
                    "warnings": ["loss event generation failed"],
                    "loss_metric": None,
                    "loss_points_written": 0,
                }
            ),
        }
        if task_id:
            try:
                log_loss_task_completed(task_id, success=True, processed_devices=1, failed_devices=0)
            except Exception:
                pass
        return out
    except Exception as e:
        logger.exception("run_inverter_expected_power_for_date_range failed for %s: %s", inverter_id, e)
        out = {"success": False, "inverter_id": inverter_id, "error": str(e), "task_id": task_id}
        if task_id:
            try:
                log_loss_task_completed(task_id, success=False, error_message=out["error"])
            except Exception:
                pass
        return out


@shared_task(bind=True, queue="default")
def run_asset_loss_pipeline(
    self,
    asset_code: str,
    start_date: str,
    end_date: str,
    time_interval_minutes: int = 15,
    run_transpose: bool = False,
    irradiance_device_id: str = "",
    transpose_metric: str = "ghi",
) -> dict:
    """
    Orchestrator: optionally run transposition, then enqueue one task per configured
    string and one per configured inverter. Returns orchestrator task_id and list of
    child task_ids. Does not wait for child tasks to finish.
    """
    task_id = str(getattr(getattr(self, "request", None), "id", "") or "")
    if task_id:
        try:
            log_loss_task_started(task_id)
        except Exception:
            pass
    try:
        asset = AssetList.objects.filter(asset_code=asset_code).first()
        if not asset:
            out = {"success": False, "error": f"Asset {asset_code} not found", "task_id": task_id}
            if task_id:
                try:
                    log_loss_task_completed(task_id, success=False, error_message=out["error"])
                except Exception:
                    pass
            return out
        start_dt = parse_dt_utc(start_date, asset)
        end_dt = parse_dt_utc(end_date, asset)
        logger.info(
            "run_asset_loss_pipeline: asset_code=%s start_date=%s end_date=%s -> start_dt=%s end_dt=%s",
            asset_code,
            start_date,
            end_date,
            start_dt.isoformat() if start_dt else None,
            end_dt.isoformat() if end_dt else None,
        )
        if start_dt >= end_dt:
            return {"success": False, "error": "start_date must be before end_date", "task_id": task_id}
        if run_transpose and irradiance_device_id:
            # Run transposition synchronously in this task so GII is ready before child tasks
            trans_result = run_transpose(
                asset_code=asset_code,
                irradiance_device_id=irradiance_device_id,
                start_date_utc=start_dt,
                end_date_utc=end_dt,
                metric=transpose_metric or "ghi",
            )
            if not trans_result.get("success"):
                return {"success": False, "error": trans_result.get("error", "Transposition failed"), "task_id": task_id}
        strings_qs = config_resolver.get_configured_string_devices_for_asset(asset_code)
        string_ids = list(strings_qs.values_list("device_id", flat=True))
        inverters_qs = config_resolver.get_configured_inverter_devices_for_asset(asset_code)
        inverter_ids = list(inverters_qs.values_list("device_id", flat=True))
        string_tasks = []
        inverter_tasks = []
        for dev_id in string_ids:
            t = run_string_loss_for_date_range.apply_async(
                kwargs={
                    "device_id": dev_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "time_interval_minutes": time_interval_minutes,
                },
                queue="default",
            )
            string_tasks.append({"device_id": dev_id, "task_id": t.id})
        for inv_id in inverter_ids:
            t = run_inverter_expected_power_for_date_range.apply_async(
                kwargs={
                    "inverter_id": inv_id,
                    "asset_code": asset_code,
                    "start_date": start_dt.isoformat(),
                    "end_date": end_dt.isoformat(),
                },
                queue="default",
            )
            inverter_tasks.append({"device_id": inv_id, "task_id": t.id})
        out = {
            "success": True,
            "task_id": task_id,
            "asset_code": asset_code,
            "asset_name": getattr(asset, "asset_name", None),
            "string_tasks": string_tasks,
            "inverter_tasks": inverter_tasks,
            "message": f"Queued {len(string_tasks)} string(s) and {len(inverter_tasks)} inverter(s). Poll child task_ids for status.",
        }
        if task_id:
            try:
                # Mark orchestrator itself as succeeded (child tasks tracked separately).
                log_loss_task_completed(task_id, success=True, processed_devices=len(string_tasks) + len(inverter_tasks), failed_devices=0)
            except Exception:
                pass
        return out
    except Exception as e:
        logger.exception("run_asset_loss_pipeline failed: %s", e)
        out = {"success": False, "error": str(e), "task_id": task_id}
        if task_id:
            try:
                log_loss_task_completed(task_id, success=False, error_message=out["error"])
            except Exception:
                pass
        return out


@shared_task(bind=True, queue="default")
def run_scheduled_transpose_after_sunset(self) -> dict:
    """
    Scheduled task to run GHI→GII transposition for each asset **once per local day**,
    shortly after sunset.

    - Picks the irradiance device from device_list where parent_code == asset_code
      and device_source == 'ghi'.
    - Uses metric 'ghi'.
    - Date range: the asset's local calendar day (start_date = YYYY-MM-DD, end_date = YYYY-MM-DD 23:59:59).
    - Runs only when the asset is in its night window with a 0.5 hour buffer after sunset,
      and only once per (asset, date) via ScheduledJobRun.
    """
    from data_collection.services.solar_window import is_asset_after_sunset
    from loss_analytics.models import ScheduledJobRun

    now = django_timezone.now()
    triggered = []
    skipped_no_night = 0
    skipped_already = 0
    skipped_no_ghi_device = 0
    errors = []

    assets = AssetList.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    ).exclude(timezone__isnull=True).exclude(timezone="").values_list("asset_code", flat=True)

    for asset_code in assets:
        try:
            # 0.5h buffer after sunset for transposition
            result = is_asset_after_sunset(asset_code, now=now, sunset_buffer_hours=0.5)
            if result is None:
                continue
            after_sunset, local_date = result
            if not after_sunset:
                skipped_no_night += 1
                continue

            # DB dedup per (asset, date)
            _, created = ScheduledJobRun.objects.get_or_create(
                job_name="transpose_after_sunset",
                run_date=local_date,
                scope_key=asset_code,
            )
            if not created:
                skipped_already += 1
                continue

            # Resolve GHI device for this asset
            ghi_device = (
                device_list.objects.filter(parent_code=asset_code, device_source__iexact="ghi")
                .order_by("device_id")
                .first()
            )
            if not ghi_device:
                skipped_no_ghi_device += 1
                errors.append(f"{asset_code}: no device with device_source='ghi' found")
                continue

            date_iso = local_date.isoformat()
            transpose_asset_ghi_to_gii.apply_async(
                kwargs={
                    "asset_code": asset_code,
                    "irradiance_device_id": ghi_device.device_id,
                    "start_date": date_iso,
                    "end_date": f"{date_iso} 23:59:59",
                    "metric": "ghi",
                },
                queue="default",
            )
            triggered.append(
                {"asset_code": asset_code, "date": date_iso, "irradiance_device_id": ghi_device.device_id}
            )
        except Exception as e:
            logger.exception("run_scheduled_transpose_after_sunset failed for %s: %s", asset_code, e)
            errors.append(f"{asset_code}: {e}")

    return {
        "triggered": len(triggered),
        "triggered_details": triggered,
        "skipped_no_night": skipped_no_night,
        "skipped_already": skipped_already,
        "skipped_no_ghi_device": skipped_no_ghi_device,
        "errors": errors,
    }


@shared_task(bind=True, queue="default")
def run_scheduled_expected_power_after_sunset(
    self,
    on_demand: bool = False,
    calculation_date_iso: Optional[str] = None,
) -> dict:
    """
    Run expected power for all assets (inverter + string loss pipeline) for a given day.

    - **Scheduled mode** (on_demand=False, default): Run via Celery Beat every 1 hour. For each
      asset with lat/lon/timezone, runs only when the asset is in its night window (after
      sunset + 1h buffer). Each (asset, date) is triggered at most once (DB deduplication via
      ScheduledJobRun); survives server restarts so the calculation is not repeated.
    - **On-demand mode** (on_demand=True): Run regardless of time of day. Use from the loss
      calculation test page or Background Jobs "Run task on demand". Runs for calculation_date_iso
      (default: yesterday UTC). Does not use cache, so it always executes for the given date.
    """
    from data_collection.services.solar_window import is_asset_after_sunset, NIGHT_WINDOW_SUNSET_BUFFER_HOURS
    from loss_analytics.models import ScheduledJobRun

    now = django_timezone.now()
    triggered = []
    skipped_no_night = 0
    skipped_already = 0
    errors = []

    assets = AssetList.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    ).exclude(timezone__isnull=True).exclude(timezone="").values_list("asset_code", flat=True)

    for asset_code in assets:
        try:
            if on_demand:
                # On-demand: run for the given date (or yesterday UTC) regardless of time
                if calculation_date_iso:
                    try:
                        target_date = datetime.strptime(calculation_date_iso.strip()[:10], "%Y-%m-%d").date()
                    except ValueError:
                        errors.append(f"{asset_code}: invalid calculation_date_iso")
                        continue
                else:
                    target_date = (now - timedelta(days=1)).date()
                date_iso = target_date.isoformat()
                run_asset_loss_pipeline.apply_async(
                    kwargs={
                        "asset_code": asset_code,
                        "start_date": date_iso,
                        "end_date": f"{date_iso} 23:59:59",
                        "run_transpose": False,
                    },
                    queue="default",
                )
                triggered.append({"asset_code": asset_code, "date": date_iso})
                continue

            # Scheduled: only run when asset is in night window, and only once per (asset, date)
            result = is_asset_after_sunset(
                asset_code, now=now, sunset_buffer_hours=NIGHT_WINDOW_SUNSET_BUFFER_HOURS
            )
            if result is None:
                continue
            after_sunset, local_date = result
            if not after_sunset:
                skipped_no_night += 1
                continue
            date_iso = local_date.isoformat()
            _, created = ScheduledJobRun.objects.get_or_create(
                job_name="expected_power_after_sunset",
                run_date=local_date,
                scope_key=asset_code,
            )
            if not created:
                skipped_already += 1
                continue
            run_asset_loss_pipeline.apply_async(
                kwargs={
                    "asset_code": asset_code,
                    "start_date": date_iso,
                    "end_date": f"{date_iso} 23:59:59",
                    "run_transpose": False,
                },
                queue="default",
            )
            triggered.append({"asset_code": asset_code, "date": date_iso})
        except Exception as e:
            logger.exception("run_scheduled_expected_power_after_sunset failed for %s: %s", asset_code, e)
            errors.append(f"{asset_code}: {e}")

    return {
        "on_demand": on_demand,
        "triggered": len(triggered),
        "triggered_details": triggered,
        "skipped_no_night": skipped_no_night,
        "skipped_already": skipped_already,
        "errors": errors,
    }
