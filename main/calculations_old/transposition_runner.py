"""
Run GHI→GII transposition for an asset and date range.

Used by the Celery task and (optionally) by the calculation test view.
All heavy work is intended to run in a worker, not in the HTTP request.
"""
import time
from datetime import datetime
from django.db.models import Q
from django.utils import timezone as django_timezone

from main.models import AssetList, timeseries_data
from main.calculations.ghi_to_gii import ghi_to_gii, gii_device_id
from main.calculations.timeseries_writer import TimeseriesWriter

import logging

logger = logging.getLogger(__name__)


def _asset_fixed_tz(asset):
    """Asset timezone as fixed offset for date parsing."""
    tz_str = (getattr(asset, "timezone", "") or "").strip()
    m = __import__("re").match(r"^([+-])(\d{2}):?(\d{2})$", tz_str)
    if not m:
        return django_timezone.get_current_timezone()
    sign, hh, mm = m.groups()
    offset_min = int(hh) * 60 + int(mm)
    if sign == "-":
        offset_min = -offset_min
    return django_timezone.get_fixed_timezone(offset_min)


def run_transpose_asset_ghi_to_gii(
    asset_code: str,
    irradiance_device_id: str,
    metric: str,
    start_date: datetime,
    end_date: datetime,
) -> dict:
    """
    Run GHI→GII transposition for the given asset and date range.
    Writes GII to timeseries_data with synthetic device_ids.

    Args:
        asset_code: Asset code
        irradiance_device_id: Device ID that has GHI data
        metric: Metric name for GHI (e.g. 'ghi')
        start_date: Start of range (timezone-aware)
        end_date: End of range (timezone-aware)

    Returns:
        Dict with success, time_taken_seconds, device_ids_used, records_written,
        ghi_points, tilt_configs_count, or error key on failure.
    """
    asset = AssetList.objects.filter(asset_code=asset_code).first()
    if not asset:
        return {"success": False, "error": f"Asset {asset_code} not found"}

    tilt_configs = getattr(asset, "tilt_configs", None)
    if not tilt_configs or not isinstance(tilt_configs, list) or len(tilt_configs) == 0:
        return {
            "success": False,
            "error": "Asset has no tilt_configs. Add tilt/azimuth/panel_count in site onboarding.",
        }

    lat_deg = float(asset.latitude)
    lon_deg = float(asset.longitude)
    altitude_m = float(asset.altitude_m) if getattr(asset, "altitude_m", None) is not None else 0.0
    albedo = float(asset.albedo) if getattr(asset, "albedo", None) is not None else 0.2
    albedo = max(0.0, min(1.0, albedo))
    asset_tz = _asset_fixed_tz(asset)

    ghi_rows = list(
        timeseries_data.objects.filter(
            device_id=irradiance_device_id,
            ts__gte=start_date,
            ts__lte=end_date,
        )
        .filter(Q(metric=metric) | Q(oem_metric=metric))
        .values("ts", "value")
        .order_by("ts")
    )

    if not ghi_rows:
        return {
            "success": False,
            "error": f"No GHI data found for device {irradiance_device_id}, metric '{metric}' in date range.",
        }

    ghi_by_ts = {}
    for row in ghi_rows:
        try:
            ghi_by_ts[row["ts"]] = float(row["value"])
        except (ValueError, TypeError):
            continue

    if not ghi_by_ts:
        return {"success": False, "error": "No valid numeric GHI values in the selected data."}

    # Delete existing GII for this asset in date range
    gii_prefix = f"{asset_code}_gii_"
    timeseries_data.objects.filter(
        device_id__startswith=gii_prefix,
        ts__gte=start_date,
        ts__lte=end_date,
        metric="gii",
    ).delete()

    writer = TimeseriesWriter()
    device_ids_used = set()
    records_written = 0
    t0 = time.perf_counter()

    for ts, ghi in ghi_by_ts.items():
        for cfg in tilt_configs:
            try:
                tilt_deg = float(cfg.get("tilt_deg", 0))
                azimuth_deg = float(cfg.get("azimuth_deg", 0))
            except (TypeError, ValueError):
                continue
            gii_val = ghi_to_gii(
                ghi,
                ts,
                lat_deg,
                lon_deg,
                tilt_deg,
                azimuth_deg,
                altitude_m=altitude_m,
                rho=albedo,
                local_tz=asset_tz,
            )
            dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
            device_ids_used.add(dev_id)
            res = writer.write_batch(
                device_id=dev_id,
                metrics={"gii": gii_val},
                timestamp=ts,
                device_type="weather",
            )
            if res.get("gii"):
                records_written += 1

    time_taken_seconds = time.perf_counter() - t0
    return {
        "success": True,
        "time_taken_seconds": round(time_taken_seconds, 2),
        "device_ids_used": sorted(device_ids_used),
        "records_written": records_written,
        "ghi_points": len(ghi_by_ts),
        "tilt_configs_count": len(tilt_configs),
    }
