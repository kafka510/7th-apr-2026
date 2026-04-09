"""
Acquisition runner: resolve adapter per asset or per account (batched).

Used by Celery tasks run_data_acquisition and run_data_acquisition_30min.
Queries AssetAdapterConfig for assets with the given interval; when multiple
assets share the same adapter account and adapter is fusion_solar, runs a
single batched fetch. Otherwise calls fetch_and_store per asset.
"""
import logging
from collections import defaultdict
from datetime import timedelta
from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional, Tuple

from data_collection.adapters import fetch_and_store as adapter_fetch_and_store
from data_collection.models import AssetAdapterConfig
from django.db.models import Q
from django.db.models import Count
from django.utils import timezone as dj_tz

logger = logging.getLogger(__name__)
MAX_HOURLY_DURATION_DAYS = 7


def run_acquisition_for_interval(
    interval_minutes: int,
    sun_hours_check: bool = True,
    replace_all_day_data: bool = False,
    duration_days: int = 0,
    now=None,
) -> Dict[str, Any]:
    """
    Run data acquisition for all assets configured for the given interval.

    Groups by adapter_account_id. For fusion_solar with multiple assets per account,
    calls fusion_solar_fetch_and_store_batch once; for solargis or single-asset
    groups, calls fetch_and_store per asset.

    Solargis is excluded from 5/30/1440 runs; it runs only via run_solargis_daily_ingest.
    """
    # Laplace dual cadence support (fixed scheduler behavior):
    # - run ALL enabled laplaceid assets on 30-min task (WH cadence)
    # - run ALL enabled laplaceid assets on hourly task (minute cadence)
    # - NEVER run laplaceid on 5-min task
    # The per-asset acquisition_interval_minutes value for laplaceid is ignored for scheduling.
    if interval_minutes == 5:
        base_filter = Q(acquisition_interval_minutes=5, enabled=True) & ~Q(adapter_id="laplaceid")
    elif interval_minutes in (30, 60):
        base_filter = Q(acquisition_interval_minutes=interval_minutes, enabled=True) | Q(enabled=True, adapter_id="laplaceid")
    else:
        base_filter = Q(acquisition_interval_minutes=interval_minutes, enabled=True)
    configs_qs = (
        AssetAdapterConfig.objects.filter(base_filter)
        .exclude(adapter_id="solargis")
        .select_related("adapter_account")
    )
    configs = list(configs_qs)

    if not configs:
        enabled_qs = AssetAdapterConfig.objects.filter(enabled=True)
        by_adapter = list(
            enabled_qs.values("adapter_id")
            .annotate(total=Count("id"))
            .order_by("adapter_id")
        )
        laplace_total = enabled_qs.filter(adapter_id="laplaceid").count()
        logger.info(
            "No assets configured for interval=%s (enabled_by_adapter=%s, laplace_enabled=%s)",
            interval_minutes,
            by_adapter,
            laplace_total,
        )
        return {
            "ran": True,
            "reason": "no_assets_configured",
            "results": [],
            "total": 0,
            "success_count": 0,
            "failed_count": 0,
            "diagnostics": {
                "interval_minutes": interval_minutes,
                "enabled_by_adapter": by_adapter,
                "laplace_enabled": laplace_total,
            },
        }

    # Group by (adapter_account_id, adapter_id). Legacy rows (no account) get adapter_account_id=None.
    groups: Dict[Tuple[Optional[int], str], List[AssetAdapterConfig]] = defaultdict(list)
    for row in configs:
        key = (row.adapter_account_id, row.adapter_id)
        groups[key].append(row)

    results: List[Dict] = []
    success_count = 0
    failed_count = 0

    # On-demand backfill for Laplace:
    # - hourly task (interval=60): duration_days => sequential hour windows
    # - 30-min task (interval=30): duration_days => sequential local-day windows
    hourly_duration_days = 0
    try:
        hourly_duration_days = int(duration_days or 0)
    except (TypeError, ValueError):
        hourly_duration_days = 0
    if hourly_duration_days < 0:
        hourly_duration_days = 0
    if hourly_duration_days > MAX_HOURLY_DURATION_DAYS:
        logger.warning(
            "Hourly duration_days=%s exceeds max=%s; capping",
            hourly_duration_days,
            MAX_HOURLY_DURATION_DAYS,
        )
        hourly_duration_days = MAX_HOURLY_DURATION_DAYS

    tz_by_asset: Dict[str, Optional[str]] = {}
    if interval_minutes in (30, 60) and hourly_duration_days > 0:
        try:
            from main.models import AssetList

            laplace_assets = [r.asset_code for (_acc, aid), rs in groups.items() if aid == "laplaceid" for r in rs]
            if laplace_assets:
                tz_by_asset = dict(
                    AssetList.objects.filter(asset_code__in=laplace_assets).values_list("asset_code", "timezone")
                )
        except Exception:
            tz_by_asset = {}

    for (_account_id, adapter_id), rows in groups.items():
        if adapter_id == "fusion_solar" and len(rows) > 1 and _account_id is not None:
            # Batched path: one account, multiple assets (use model merge so account creds are kept)
            base_config = dict(rows[0].get_effective_config())
            base_config["acquisition_interval_minutes"] = interval_minutes
            if adapter_id == "laplaceid" and replace_all_day_data:
                base_config["replace_all_day_data"] = True
            asset_codes = [r.asset_code for r in rows]
            try:
                from data_collection.adapters.fusion_solar import fusion_solar_fetch_and_store_batch

                out = fusion_solar_fetch_and_store_batch(asset_codes=asset_codes, config=base_config)
            except Exception as e:
                logger.exception("Fusion Solar batch failed for account %s", _account_id)
                out = {"success": False, "error": str(e), "asset_codes": asset_codes}
            batch_results = out.get("results") if isinstance(out.get("results"), list) else []
            if batch_results:
                seen_assets = set()
                for item in batch_results:
                    ac = item.get("asset_code")
                    if not ac:
                        continue
                    seen_assets.add(ac)
                    normalized = {
                        "success": bool(item.get("success")),
                        "asset_code": ac,
                        "adapter_id": adapter_id,
                        "points_written": int(item.get("points_written", 0) or 0),
                    }
                    if item.get("error"):
                        normalized["error"] = str(item.get("error"))
                    if item.get("warning"):
                        normalized["warning"] = str(item.get("warning"))
                    results.append(normalized)
                    if normalized["success"]:
                        success_count += 1
                    else:
                        failed_count += 1
                        logger.warning("Fusion Solar batch asset failed for %s: %s", ac, normalized.get("error", "unknown"))
                # Fallback for assets missing from batch response.
                for ac in asset_codes:
                    if ac in seen_assets:
                        continue
                    results.append({
                        "success": False,
                        "asset_code": ac,
                        "adapter_id": adapter_id,
                        "points_written": 0,
                        "error": "Batch response missing per-asset result",
                    })
                    failed_count += 1
                    logger.warning("Fusion Solar batch missing per-asset result for %s", ac)
            elif out.get("success"):
                # Backward compatibility path: old adapter shape without per-asset results.
                pts = int(out.get("points_written", 0) or 0)
                for ac in asset_codes:
                    results.append({
                        "success": True,
                        "asset_code": ac,
                        "adapter_id": adapter_id,
                        "points_written": pts,
                    })
                success_count += len(asset_codes)
            else:
                for ac in asset_codes:
                    results.append({
                        "success": False,
                        "asset_code": ac,
                        "adapter_id": adapter_id,
                        "points_written": 0,
                        "error": out.get("error", "batch failed"),
                    })
                failed_count += len(asset_codes)
                logger.warning("Fusion Solar batch failed for %s: %s", asset_codes, out.get("error"))
        else:
            # Per-asset path (use model merge so account creds are kept when asset config has blank fields)
            for row in rows:
                asset_code = row.asset_code
                config = dict(row.get_effective_config())
                config["acquisition_interval_minutes"] = interval_minutes
                if row.adapter_id == "laplaceid" and replace_all_day_data:
                    config["replace_all_day_data"] = True
                # Hourly backfill mode for Laplace: query each hour sequentially in the selected duration.
                if row.adapter_id == "laplaceid" and interval_minutes == 60 and hourly_duration_days > 0:
                    from data_collection.services.laplace_request_time import fixed_timezone_from_asset_offset

                    hours_to_fetch = hourly_duration_days * 24
                    tz = fixed_timezone_from_asset_offset(tz_by_asset.get(asset_code)) or dt_timezone.utc
                    local_now = dj_tz.now().astimezone(tz)
                    end_hour = local_now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                    start_hour = end_hour - timedelta(hours=hours_to_fetch - 1)

                    all_ok = True
                    first_error = None
                    total_points = 0
                    for idx in range(hours_to_fetch):
                        t = start_hour + timedelta(hours=idx)
                        hour_cfg = dict(config)
                        hour_cfg["time"] = t.strftime("%Y%m%d%H")
                        out = adapter_fetch_and_store(asset_code=asset_code, adapter_id=row.adapter_id, config=hour_cfg)
                        if out.get("success"):
                            total_points += int(out.get("points_written", 0) or 0)
                        else:
                            all_ok = False
                            if first_error is None:
                                first_error = str(out.get("error", "unknown"))
                            logger.warning(
                                "Hourly backfill failed for %s at %s: %s",
                                asset_code,
                                hour_cfg["time"],
                                out.get("error", "unknown"),
                            )
                    summary = {
                        "success": all_ok,
                        "asset_code": asset_code,
                        "adapter_id": row.adapter_id,
                        "points_written": total_points,
                        "hours_requested": hours_to_fetch,
                        "duration_days": hourly_duration_days,
                    }
                    if not all_ok:
                        summary["error"] = first_error or "hourly backfill partially failed"
                    results.append(summary)
                    if all_ok:
                        success_count += 1
                    else:
                        failed_count += 1
                elif row.adapter_id == "laplaceid" and interval_minutes == 30 and hourly_duration_days > 0:
                    from data_collection.services.laplace_request_time import fixed_timezone_from_asset_offset

                    days_to_fetch = hourly_duration_days
                    tz = fixed_timezone_from_asset_offset(tz_by_asset.get(asset_code)) or dt_timezone.utc
                    local_today = dj_tz.now().astimezone(tz).date()
                    start_day = local_today - timedelta(days=days_to_fetch - 1)

                    all_ok = True
                    first_error = None
                    total_points = 0
                    for idx in range(days_to_fetch):
                        d = start_day + timedelta(days=idx)
                        day_cfg = dict(config)
                        day_cfg["time"] = d.strftime("%Y%m%d")
                        out = adapter_fetch_and_store(asset_code=asset_code, adapter_id=row.adapter_id, config=day_cfg)
                        if out.get("success"):
                            total_points += int(out.get("points_written", 0) or 0)
                        else:
                            all_ok = False
                            if first_error is None:
                                first_error = str(out.get("error", "unknown"))
                            logger.warning(
                                "30-min day backfill failed for %s at %s: %s",
                                asset_code,
                                day_cfg["time"],
                                out.get("error", "unknown"),
                            )
                    summary = {
                        "success": all_ok,
                        "asset_code": asset_code,
                        "adapter_id": row.adapter_id,
                        "points_written": total_points,
                        "days_requested": days_to_fetch,
                        "duration_days": hourly_duration_days,
                    }
                    if not all_ok:
                        summary["error"] = first_error or "30-min day backfill partially failed"
                    results.append(summary)
                    if all_ok:
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    out = adapter_fetch_and_store(asset_code=asset_code, adapter_id=row.adapter_id, config=config)
                    out["asset_code"] = asset_code
                    out["adapter_id"] = row.adapter_id
                    results.append(out)
                    if out.get("success"):
                        success_count += 1
                    else:
                        failed_count += 1
                        logger.warning("Acquisition failed for %s: %s", asset_code, out.get("error", "unknown"))

    return {
        "ran": True,
        "reason": "ok",
        "results": results,
        "total": len(configs),
        "success_count": success_count,
        "failed_count": failed_count,
    }
