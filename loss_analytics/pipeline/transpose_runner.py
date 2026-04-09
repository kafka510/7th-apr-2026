"""
Run GHI→GII transposition for an asset and date range.

Used by the Celery task and can be called from data acquisition.
Returns a result dict (success, records_written, device_ids_used, error, etc.).
"""
import re
import logging
from datetime import datetime, timezone as dt_timezone
from typing import Dict, Any, List, Optional

from django.db.models import Q
from django.utils import timezone as django_timezone

from main.models import AssetList, timeseries_data
from loss_analytics.calculations import TimeseriesWriter

from loss_analytics.pipeline.transposition import ghi_to_gii, gii_device_id
from loss_analytics.defaults import get_default_albedo, get_default_altitude_m

logger = logging.getLogger(__name__)


def _asset_fixed_tz(asset) -> Any:
    """Return fixed timezone from asset.timezone (e.g. '+08:00')."""
    tz_str = (getattr(asset, "timezone", "") or "").strip()
    m = re.match(r"^([+-])(\d{2}):?(\d{2})$", tz_str)
    if not m:
        return django_timezone.get_current_timezone()
    sign, hh, mm = m.groups()
    offset_min = int(hh) * 60 + int(mm)
    if sign == "-":
        offset_min = -offset_min
    return django_timezone.get_fixed_timezone(offset_min)


def parse_dt_utc(dt_str: str, asset) -> datetime:
    """
    Parse datetime string to UTC. Naive strings interpreted in asset timezone.
    """
    s = (dt_str or "").strip()
    if not s:
        raise ValueError("empty datetime")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            raise ValueError(f"Invalid datetime: {dt_str}")
    if django_timezone.is_naive(dt):
        dt = django_timezone.make_aware(dt, _asset_fixed_tz(asset))
    return dt.astimezone(dt_timezone.utc)


def run_transpose(
    asset_code: str,
    irradiance_device_id: str,
    start_date_utc: datetime,
    end_date_utc: datetime,
    metric: str = "ghi",
) -> Dict[str, Any]:
    """
    Run GHI→GII transposition for the asset and date range. Writes GII to
    timeseries_data. Returns result dict with success, records_written,
    device_ids_used, error, etc.
    """
    try:
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
        altitude_m = float(asset.altitude_m) if getattr(asset, "altitude_m", None) is not None else get_default_altitude_m()
        albedo = float(asset.albedo) if getattr(asset, "albedo", None) is not None else get_default_albedo()
        albedo = max(0.0, min(1.0, albedo))
        asset_tz = _asset_fixed_tz(asset)

        ghi_rows = list(
            timeseries_data.objects.filter(
                device_id=irradiance_device_id,
                ts__gte=start_date_utc,
                ts__lte=end_date_utc,
            )
            .filter(Q(metric=metric) | Q(oem_metric=metric))
            .values("ts", "value")
            .order_by("ts")
        )

        if not ghi_rows:
            return {
                "success": False,
                "error": f"No GHI data found for device {irradiance_device_id}, metric \"{metric}\" in date range.",
            }

        ghi_by_ts = {}
        for row in ghi_rows:
            try:
                ghi_by_ts[row["ts"]] = float(row["value"])
            except (ValueError, TypeError):
                continue
        if not ghi_by_ts:
            return {"success": False, "error": "No valid numeric GHI values in the selected data."}

        # Build staged writes grouped by synthetic GII device id (one staging+COPY per device id).
        # This avoids per-point INSERT/DELETE and noisy constraint/mapping logs.
        rows_by_device: Dict[str, List[tuple]] = {}
        device_ids_used = set()

        for ts, ghi in ghi_by_ts.items():
            for cfg in tilt_configs:
                try:
                    tilt_deg = float(cfg.get("tilt_deg", 0))
                    azimuth_deg = float(cfg.get("azimuth_deg", 0))
                except (TypeError, ValueError):
                    continue
                dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
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
                rows_by_device.setdefault(dev_id, []).append((ts, {"gii": gii_val}))
                device_ids_used.add(dev_id)

        writer = TimeseriesWriter()
        records_written = 0
        for dev_id, rows in rows_by_device.items():
            ok = writer.write_loss_range_with_staging(
                device_id=dev_id,
                rows=rows,
                start_ts=start_date_utc,
                end_ts=end_date_utc,
                device_type="weather",
                delete_existing=True,
            )
            if ok:
                records_written += len(rows)
            else:
                return {"success": False, "error": f"Failed to persist GII rows for {dev_id}"}

        return {
            "success": True,
            "records_written": records_written,
            "device_ids_used": sorted(device_ids_used),
            "ghi_points": len(ghi_by_ts),
            "tilt_configs_count": len(tilt_configs),
        }
    except Exception as e:
        logger.exception("run_transpose failed: %s", e)
        return {"success": False, "error": str(e)}
