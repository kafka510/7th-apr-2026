import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone as dt_timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from celery import shared_task
from django.db import connection, transaction
from django.utils import timezone

from data_collection.services.solar_window import (
    _parse_timezone_offset_minutes,
    get_sunrise_sunset_hours_local,
    is_time_in_solar_window,
    utc_to_local_hour,
)
from main.models import AssetList, RealTimeKPI, device_list, kpis, timeseries_data

logger = logging.getLogger(__name__)


def _asset_tz_offset_minutes(asset: AssetList) -> int:
    """Minutes east of UTC from `asset_list.timezone` (+05:30 style). Invalid/missing → 0."""
    off = _parse_timezone_offset_minutes(getattr(asset, "timezone", None))
    return 0 if off is None else int(off)


def _asset_fixed_tz(asset: AssetList):
    """tzinfo for this asset's fixed offset (from AssetList.timezone). Used for local-day bounds."""
    return dt_timezone(timedelta(minutes=_asset_tz_offset_minutes(asset)))


def _asset_local_dt(asset: AssetList, now_utc: datetime) -> Tuple[datetime, int]:
    """
    Return (approximate local wall-clock time as naive UTC+offset shift, tz_offset_minutes)
    for scheduling windows. Offset comes from `asset_list.timezone`.
    """
    offset = _asset_tz_offset_minutes(asset)
    return (now_utc + timedelta(minutes=offset), offset)


def _utc_bounds_for_asset_local_date(asset: AssetList, local_d: date) -> Tuple[datetime, datetime]:
    """
    UTC [start, end] inclusive for the asset's local calendar day `local_d`.

    Uses `AssetList.timezone` (stored offset e.g. +05:30). Bounds are converted with
    `.astimezone(UTC)` so DB filters (`ts__gte` / `ts__lte`) match the correct instants
    for that site's local day regardless of offset.
    """
    tz = _asset_fixed_tz(asset)
    start_local = datetime.combine(local_d, dt_time.min, tzinfo=tz)
    end_local = datetime.combine(local_d, dt_time.max, tzinfo=tz)
    return (start_local.astimezone(dt_timezone.utc), end_local.astimezone(dt_timezone.utc))


def _parse_iso_date_optional(s: Any) -> Optional[date]:
    if s is None:
        return None
    text = str(s).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _normalize_asset_codes_arg(raw: Any) -> Optional[List[str]]:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return None
    out = [str(c).strip() for c in raw if c is not None and str(c).strip()]
    return out if out else None


def _local_date_range_inclusive(start: date, end: date) -> List[date]:
    out: List[date] = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _has_device_source(raw_source: Any, wanted_source: str) -> bool:
    wanted = (wanted_source or "").strip().lower()
    if not wanted:
        return False
    if raw_source is None:
        return False
    if isinstance(raw_source, str):
        s = raw_source.strip()
        if not s:
            return False
        try:
            import json
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return any(str(item).strip().lower() == wanted for item in parsed)
        except Exception:
            pass
        return s.lower() == wanted
    if isinstance(raw_source, (list, tuple, set)):
        return any(str(item).strip().lower() == wanted for item in raw_source)
    return False


def _fetch_metric_rows(
    device_id: str,
    metric: str,
    start_utc: datetime,
    end_utc: datetime,
) -> List[Tuple[datetime, float]]:
    rows = (
        timeseries_data.objects.filter(
            device_id=device_id,
            metric=metric,
            ts__gte=start_utc,
            ts__lte=end_utc,
        )
        .order_by("ts")
        .values_list("ts", "value")
    )
    out: List[Tuple[datetime, float]] = []
    for ts, value in rows:
        fv = _safe_float(value)
        if fv is None:
            continue
        out.append((ts, fv))
    return out


def _local_hour(ts_utc: datetime, tz_offset_minutes: int) -> float:
    local = ts_utc + timedelta(minutes=tz_offset_minutes)
    return local.hour + local.minute / 60.0 + local.second / 3600.0


def _exclude_night_window_rows(
    rows: List[Tuple[datetime, float]],
    tz_offset_minutes: int,
) -> List[Tuple[datetime, float]]:
    # Ignore 23:00 to 01:00 local to avoid false positives around day rollover.
    out: List[Tuple[datetime, float]] = []
    for ts, val in rows:
        h = _local_hour(ts, tz_offset_minutes)
        if h >= 23.0 or h < 1.0:
            continue
        out.append((ts, val))
    return out


def _row_is_inside_asset_solar_window(
    asset: AssetList,
    ts_utc: datetime,
    tz_offset_minutes: int,
    local_day: date,
) -> bool:
    """
    Check whether a UTC timestamp falls inside the asset's solar window for local_day.
    Uses the same solar window utilities as data collection.
    """
    try:
        lat = float(getattr(asset, "latitude", None))
        lon = float(getattr(asset, "longitude", None))
    except (TypeError, ValueError):
        # Be permissive when site metadata is invalid/missing.
        return True

    sr_ss = get_sunrise_sunset_hours_local(lat, lon, local_day)
    if sr_ss is None:
        return True
    sunrise_hour, sunset_hour = sr_ss
    local_hour = utc_to_local_hour(ts_utc, tz_offset_minutes)
    return is_time_in_solar_window(local_hour, sunrise_hour, sunset_hour)


def _filter_rows_inside_asset_solar_window(
    asset: AssetList,
    rows: List[Tuple[datetime, float]],
    tz_offset_minutes: int,
    local_day: date,
) -> List[Tuple[datetime, float]]:
    return [r for r in rows if _row_is_inside_asset_solar_window(asset, r[0], tz_offset_minutes, local_day)]


def _find_increment_span(
    rows: List[Tuple[datetime, float]],
    epsilon: float = 1e-6,
) -> Tuple[Optional[Tuple[datetime, float]], Optional[Tuple[datetime, float]]]:
    """
    Return (start_row, stop_row) for the incrementing segment in chronological rows.
    start_row: sample from which value starts increasing
    stop_row: last sample at which incrementing is observed to have stopped
    """
    if len(rows) == 0:
        return (None, None)
    if len(rows) == 1:
        return (rows[0], rows[0])

    first_inc_idx: Optional[int] = None
    last_inc_idx: Optional[int] = None
    for i in range(len(rows) - 1):
        if rows[i + 1][1] > rows[i][1] + epsilon:
            if first_inc_idx is None:
                first_inc_idx = i
            last_inc_idx = i

    if first_inc_idx is None or last_inc_idx is None:
        # No increment seen: keep chronological boundaries.
        return (rows[0], rows[-1])
    return (rows[first_inc_idx], rows[last_inc_idx + 1])


def _night_increment_from_increment_span_timestamps(
    asset: AssetList,
    first_row: Tuple[datetime, float],
    last_row: Tuple[datetime, float],
    tz_offset_minutes: int,
    local_day: date,
) -> bool:
    """
    Night anomaly if increment span starts or ends outside the solar window.
    """
    return (not _row_is_inside_asset_solar_window(asset, first_row[0], tz_offset_minutes, local_day)) or (
        not _row_is_inside_asset_solar_window(asset, last_row[0], tz_offset_minutes, local_day)
    )


def _first_last_rows(rows: List[Tuple[datetime, float]]) -> Tuple[Optional[Tuple[datetime, float]], Optional[Tuple[datetime, float]]]:
    if not rows:
        return (None, None)
    return (rows[0], rows[-1])


def _latest_metric_per_device_sum(
    device_ids: List[str],
    metric: str,
    start_utc: datetime,
    end_utc: datetime,
) -> Optional[float]:
    """
    Sum the latest value per device_id within [start_utc, end_utc] for a given metric.
    Returns None if no data found.
    """
    if not device_ids:
        return None
    total = 0.0
    found = 0
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (device_id) device_id, value
            FROM timeseries_data
            WHERE device_id = ANY(%s)
              AND metric = %s
              AND ts >= %s AND ts <= %s
            ORDER BY device_id, ts DESC
            """,
            [device_ids, metric, start_utc, end_utc],
        )
        for _device_id, value in cursor.fetchall():
            fv = _safe_float(value)
            if fv is None:
                continue
            total += fv
            found += 1
    return total if found > 0 else None


def _integrate_irradiance_kwh_per_m2(
    rows: List[Tuple[datetime, Any]],
    max_gap_hours: float = 1.0,
) -> float:
    """
    Integrate irradiance readings (W/m^2) over time to kWh/m^2 using trapezoidal rule.
    Expects rows sorted by ts ascending.
    """
    prev_ts: Optional[datetime] = None
    prev_val: Optional[float] = None
    acc = 0.0
    for ts, v in rows:
        fv = _safe_float(v)
        if fv is None:
            continue
        if fv < 0 or fv > 2000:
            continue
        if prev_ts is not None and prev_val is not None:
            dt_h = (ts - prev_ts).total_seconds() / 3600.0
            if 0 < dt_h <= max_gap_hours:
                acc += ((prev_val + fv) / 2.0) * dt_h / 1000.0
        prev_ts = ts
        prev_val = fv
    return acc


def _daily_irradiation_from_timeseries(
    ghi_device_ids: List[str],
    start_utc: datetime,
    end_utc: datetime,
) -> Optional[float]:
    """
    Compute average daily irradiation across available GHI devices.
    Uses metric='ghi' primarily; falls back to metric='gii' if no ghi records exist.
    Returns None if no data for any device.
    """
    if not ghi_device_ids:
        return None
    device_irr: List[float] = []
    for did in ghi_device_ids:
        # Try ghi first
        rows = list(
            timeseries_data.objects.filter(
                device_id=did,
                metric="ghi",
                ts__gte=start_utc,
                ts__lte=end_utc,
            )
            .order_by("ts")
            .values_list("ts", "value")
        )
        if not rows:
            rows = list(
                timeseries_data.objects.filter(
                    device_id=did,
                    metric="gii",
                    ts__gte=start_utc,
                    ts__lte=end_utc,
                )
                .order_by("ts")
                .values_list("ts", "value")
            )
        if not rows:
            continue
        irr = _integrate_irradiance_kwh_per_m2(rows)
        if irr > 0:
            device_irr.append(irr)
    if not device_irr:
        return None
    return sum(device_irr) / float(len(device_irr))


@shared_task(bind=True)
def update_real_time_kpi_10min(self) -> Dict[str, Any]:
    """
    Update `real_time_kpi` every 10 minutes for assets where data is available.

    Rules:
    - Run only in local window [04:00, 20:00) per asset.
    - If no data is available (daily_kwh and daily_irr both missing), do NOT write anything.
    - After 20:00 local, set `is_frozen=True` for today's row (if it exists) and do not update values.
    - Never overwrite frozen rows.
    - Uses default Celery queue.
    """
    now_utc = timezone.now()
    processed = 0
    updated = 0
    skipped_no_data = 0
    skipped_window = 0
    frozen_marked = 0
    errors: List[str] = []

    assets = AssetList.objects.all().only("asset_code", "asset_number", "timezone")

    for asset in assets:
        processed += 1
        try:
            local_dt, tz_offset = _asset_local_dt(asset, now_utc)
            local_hour = local_dt.hour + local_dt.minute / 60.0
            local_date = local_dt.date()

            # After 20:00 local: mark frozen and stop updating
            if local_hour >= 20.0:
                key = str(getattr(asset, "asset_number", "") or asset.asset_code or "").strip()
                if key:
                    changed = RealTimeKPI.objects.filter(
                        asset_code=key,
                        date=local_date,
                        is_frozen=False,
                    ).update(is_frozen=True)
                    if changed:
                        frozen_marked += int(changed)
                skipped_window += 1
                continue

            # Before 04:00 local: do nothing
            if local_hour < 4.0:
                skipped_window += 1
                continue

            key = str(getattr(asset, "asset_number", "") or asset.asset_code or "").strip()
            if not key:
                skipped_window += 1
                continue

            start_utc, end_utc = _utc_bounds_for_asset_local_date(asset, local_date)

            # Skip if frozen
            existing = RealTimeKPI.objects.filter(asset_code=key, date=local_date).first()
            if existing and existing.is_frozen:
                skipped_window += 1
                continue

            # Devices
            inverter_device_ids = list(
                device_list.objects.filter(
                    parent_code=asset.asset_code,
                    device_type__in=["central_inv", "string_inv"],
                ).values_list("device_id", flat=True)
            )
            daily_kwh = _latest_metric_per_device_sum(inverter_device_ids, "inv_daily_kwh", start_utc, end_utc)

            # GHI device discovery: prefer explicit device_source='ghi' when present;
            # also include common weather/met station device types as fallback.
            ghi_ids_a = list(
                device_list.objects.filter(
                    parent_code=asset.asset_code,
                    device_source__iexact="ghi",
                ).values_list("device_id", flat=True)
            )
            ghi_ids_b = list(
                device_list.objects.filter(
                    parent_code=asset.asset_code,
                    device_type__in=["wst", "gmt", "weather_station", "met_station"],
                ).values_list("device_id", flat=True)
            )
            ghi_device_ids = sorted(set([*ghi_ids_a, *ghi_ids_b]))

            daily_irr = _daily_irradiation_from_timeseries(ghi_device_ids, start_utc, end_utc)

            # Data availability gate: do not write anything if both are missing
            if daily_kwh is None and daily_irr is None:
                skipped_no_data += 1
                continue

            daily_generation_mwh = (daily_kwh / 1000.0) if daily_kwh is not None else None
            daily_irradiation_mwh = daily_irr if daily_irr is not None else None

            with transaction.atomic():
                obj, created = RealTimeKPI.objects.get_or_create(
                    asset_code=key,
                    date=local_date,
                    defaults={
                        "daily_kwh": daily_kwh,
                        "daily_irr": daily_irr,
                        "daily_generation_mwh": daily_generation_mwh,
                        "daily_irradiation_mwh": daily_irradiation_mwh,
                        "is_frozen": False,
                    },
                )
                if not created:
                    # Only update the fields this task owns; do not overwrite other-source columns.
                    if daily_kwh is not None:
                        obj.daily_kwh = daily_kwh
                        obj.daily_generation_mwh = daily_generation_mwh
                    if daily_irr is not None:
                        obj.daily_irr = daily_irr
                        obj.daily_irradiation_mwh = daily_irradiation_mwh
                    obj.is_frozen = False
                    obj.save()

            updated += 1

        except Exception as e:
            errors.append(f"{getattr(asset, 'asset_code', '?')}: {e}")
            logger.exception("update_real_time_kpi_10min failed for asset %s", getattr(asset, "asset_code", None))

    return {
        "success": True,
        "processed_assets": processed,
        "updated_assets": updated,
        "skipped_no_data": skipped_no_data,
        "skipped_window": skipped_window,
        "frozen_marked": frozen_marked,
        "errors": errors,
    }


def _compute_kpi_for_device_day(
    asset: AssetList,
    dev: device_list,
    target_local_day: date,
) -> Tuple[bool, bool]:
    """
    Compute and persist one KPI row for a revenue device on a local calendar day.
    Timeseries queries use UTC bounds derived from `asset.timezone` (asset_list).
    Min/max reads are derived from the first/last increment span using solar-window
    filtering for "daytime" behavior.
    Returns (inserted_or_updated, skipped).
    """
    tz_offset = _asset_tz_offset_minutes(asset)
    start_utc, end_utc = _utc_bounds_for_asset_local_date(asset, target_local_day)
    prev_start_utc, prev_end_utc = _utc_bounds_for_asset_local_date(asset, target_local_day - timedelta(days=1))

    dev_type = (getattr(dev, "device_type", "") or "").strip().lower()
    metric_used: Optional[str] = None
    day_rows: List[Tuple[datetime, float]] = []
    prev_rows: List[Tuple[datetime, float]] = []
    inv_daily_rows: List[Tuple[datetime, float]] = []
    anomalies: Dict[str, Any] = {}

    if dev_type in ("string_inv", "central_inv"):
        inv_daily_rows = _fetch_metric_rows(dev.device_id, "inv_daily_kwh", start_utc, end_utc)
        day_rows = _fetch_metric_rows(dev.device_id, "inv_total_kwh", start_utc, end_utc)
        prev_rows = _fetch_metric_rows(dev.device_id, "inv_total_kwh", prev_start_utc, prev_end_utc)
        metric_used = "inv_total_kwh"
        if not day_rows:
            day_rows = inv_daily_rows
            prev_rows = _fetch_metric_rows(dev.device_id, "inv_daily_kwh", prev_start_utc, prev_end_utc)
            metric_used = "inv_daily_kwh"
    elif dev_type == "emt":
        day_rows = _fetch_metric_rows(dev.device_id, "emt_total_kwh", start_utc, end_utc)
        prev_rows = _fetch_metric_rows(dev.device_id, "emt_total_kwh", prev_start_utc, prev_end_utc)
        metric_used = "emt_total_kwh"
    else:
        return (False, True)

    if not day_rows:
        return (False, True)

    # Continuity compares raw day boundaries.
    day_first = day_rows[0]
    prev_last_row = _first_last_rows(prev_rows)[1] if prev_rows else None

    # Use solar-window daytime rows to identify where increment starts/stops.
    rows_for_calc = _filter_rows_inside_asset_solar_window(asset, day_rows, tz_offset, target_local_day)
    if not rows_for_calc:
        rows_for_calc = day_rows
    first_row, last_row = _find_increment_span(rows_for_calc)
    if first_row is None or last_row is None:
        return (False, True)

    daily_max_min_span = float(last_row[1] - first_row[1])
    daily_max_min = daily_max_min_span

    if metric_used in ("inv_total_kwh", "emt_total_kwh") and prev_last_row is not None:
        mismatch = abs(float(prev_last_row[1] - day_first[1]))
        if mismatch > 1e-3:
            # Continuity break: use previous day's last (end-of-day) counter as baseline for production.
            daily_max_min = float(last_row[1] - prev_last_row[1])
            anomalies["prev_day_end_mismatch"] = {
                "prev_day_last_kwh": float(prev_last_row[1]),
                "today_first_kwh": float(day_first[1]),
                "delta_kwh": float(mismatch),
                "daily_max_min_within_day_span": daily_max_min_span,
                "daily_max_min_basis": "present_daily_max_read_kwh_minus_prev_day_last_read_kwh",
                "daily_max_min_adjusted": daily_max_min,
            }

    daily_prod_rec: float
    daily_prod_rec_time: datetime

    if metric_used == "inv_daily_kwh":
        # inv_daily_kwh: value is the daily production; "stopped" time = last sample in valid window.
        daily_prod = float(last_row[1])
        daily_prod_rec = daily_prod
        daily_prod_rec_time = last_row[0]
    else:
        # inv_total_kwh / emt_total_kwh: production = daily_max_min (span or adjusted after mismatch).
        daily_prod = daily_max_min
        daily_prod_rec = daily_prod
        daily_prod_rec_time = last_row[0]
        if daily_prod < 0:
            anomalies["negative_generation"] = True

    # Business rule: for inverter devices, daily_prod_rec and its timestamp must come
    # from inv_daily_kwh at the point it stopped incrementing.
    if dev_type in ("string_inv", "central_inv"):
        inv_daily_for_prod = _filter_rows_inside_asset_solar_window(asset, inv_daily_rows, tz_offset, target_local_day)
        if not inv_daily_for_prod:
            inv_daily_for_prod = inv_daily_rows
        inv_daily_first, inv_daily_last = _find_increment_span(inv_daily_for_prod) if inv_daily_for_prod else (None, None)
        if inv_daily_last is not None:
            daily_prod_rec = float(inv_daily_last[1])
            daily_prod_rec_time = inv_daily_last[0]

    # inv_daily_kwh vs inv_total_kwh span: large gap suggests comms loss or bad reads.
    _PROD_REC_VS_MAX_MIN_KWH = 2.0
    if abs(float(daily_prod_rec) - float(daily_max_min)) > _PROD_REC_VS_MAX_MIN_KWH:
        anomalies["prod_rec_vs_total_discrepancy"] = {
            "daily_prod_rec_kwh": float(daily_prod_rec),
            "daily_max_min_kwh": float(daily_max_min),
            "delta_kwh": float(abs(daily_prod_rec - daily_max_min)),
            "threshold_kwh": _PROD_REC_VS_MAX_MIN_KWH,
            "note": "Possible communication loss or incorrect inverter read; compare inv_daily_kwh to inv_total_kwh span.",
        }

    if _night_increment_from_increment_span_timestamps(asset, first_row, last_row, tz_offset, target_local_day):
        anomalies["night_increment"] = True

    with transaction.atomic():
        obj, _created = kpis.objects.update_or_create(
            device_id=dev.device_id,
            day_date=target_local_day,
            defaults={
                "asset_code": asset.asset_code,
                "asset_number": asset.asset_number,
                "device_name": getattr(dev, "device_name", "") or "",
                "asset_name": asset.asset_name,
                "daily_min_read_time": first_row[0],
                "daily_min_read_kwh": float(first_row[1]),
                "daily_max_read_time": last_row[0],
                "daily_max_read_kwh": float(last_row[1]),
                "daily_max_min": daily_max_min,
                "daily_prod_rec": daily_prod_rec,
                "daily_prod_rec_time": daily_prod_rec_time,
                "day_1_max_read_time": prev_last_row[0] if prev_last_row else last_row[0],
                "day_1_max_read_kwh": float(prev_last_row[1]) if prev_last_row else float(last_row[1]),
                "generation_metric": metric_used,
                "has_anomaly": bool(anomalies),
                "anomaly_flags": anomalies if anomalies else None,
                "anomaly_notes": ", ".join(sorted(anomalies.keys())) if anomalies else None,
            },
        )
        _ = obj
    return (True, False)


@shared_task(bind=True)
def compute_daily_kpis_previous_day(
    self,
    asset_codes: Any = None,
    date_from: Any = None,
    date_to: Any = None,
) -> Dict[str, Any]:
    """
    Compute KPI rows for revenue devices.

    Scheduled (no kwargs) or explicit previous-day mode:
    - For each asset's **previous local calendar day**, one row per eligible device.

    Backfill (date_from and date_to set, YYYY-MM-DD inclusive):
    - For each local calendar day in the range per asset, compute KPIs and write to `kpis`.

    Optional asset_codes: restrict to these asset_code values; omit or null for all assets.

    Rules implemented:
    - Eligible devices: parent_code == asset.asset_code and device_source contains 'revenue'
    - Device type:
      * string_inv / central_inv: use inv_total_kwh, fallback to inv_daily_kwh when missing
      * emt: use emt_total_kwh
    - Min/max from increment span within solar window; inv_daily_kwh used for daily_prod_rec on inverters.
    - daily_max_min = last_read - first_read within day; if prev_day_end_mismatch, use
      present daily_max_read - prev_day_last_read instead (recorded in anomaly_flags).
    - prod_rec_vs_total_discrepancy: abs(daily_prod_rec - daily_max_min) > 2 kWh (inv_daily vs total span).
    - Anomalies:
      * prev_day_end_mismatch (inv_total/emt): continuity break; daily_max_min adjusted as above
      * night_increment: increment span start/end outside solar window
      * prod_rec_vs_total_discrepancy: see threshold above
    """
    now_utc = timezone.now()
    processed_assets = 0
    processed_devices = 0
    inserted_or_updated = 0
    skipped_devices = 0
    errors: List[str] = []

    d_from = _parse_iso_date_optional(date_from)
    d_to = _parse_iso_date_optional(date_to)
    range_mode = d_from is not None and d_to is not None
    if (d_from is None) != (d_to is None):
        return {
            "success": False,
            "error": "date_from and date_to must both be set for a date range, or omit both for previous-day mode.",
            "processed_assets": 0,
            "processed_devices": 0,
            "inserted_or_updated": 0,
            "skipped_devices": 0,
            "errors": [],
        }
    if range_mode and d_to is not None and d_from is not None and d_to < d_from:
        return {
            "success": False,
            "error": "date_to must be on or after date_from",
            "processed_assets": 0,
            "processed_devices": 0,
            "inserted_or_updated": 0,
            "skipped_devices": 0,
            "errors": [],
        }

    filtered_codes = _normalize_asset_codes_arg(asset_codes)

    assets_qs = AssetList.objects.all().only("asset_code", "asset_name", "asset_number", "timezone")
    if filtered_codes:
        assets_qs = assets_qs.filter(asset_code__in=filtered_codes)

    for asset in assets_qs:
        processed_assets += 1
        try:
            local_now, _ = _asset_local_dt(asset, now_utc)
            if range_mode and d_from is not None and d_to is not None:
                local_days = _local_date_range_inclusive(d_from, d_to)
            else:
                local_days = [local_now.date() - timedelta(days=1)]

            devices = list(
                device_list.objects.filter(parent_code=asset.asset_code).only(
                    "device_id",
                    "device_name",
                    "device_type",
                    "device_source",
                )
            )

            for target_local_day in local_days:
                for dev in devices:
                    if not _has_device_source(getattr(dev, "device_source", None), "revenue"):
                        continue

                    processed_devices += 1
                    try:
                        ok, skipped = _compute_kpi_for_device_day(asset, dev, target_local_day)
                        if skipped:
                            skipped_devices += 1
                        elif ok:
                            inserted_or_updated += 1
                    except Exception as dev_err:
                        errors.append(
                            f"{asset.asset_code}/{getattr(dev, 'device_id', '?')}/{target_local_day}: {dev_err}"
                        )
                        logger.exception(
                            "compute_daily_kpis_previous_day failed for asset=%s device=%s day=%s",
                            asset.asset_code,
                            getattr(dev, "device_id", None),
                            target_local_day,
                        )
        except Exception as asset_err:
            errors.append(f"{getattr(asset, 'asset_code', '?')}: {asset_err}")
            logger.exception(
                "compute_daily_kpis_previous_day failed for asset %s",
                getattr(asset, "asset_code", None),
            )

    return {
        "success": True,
        "processed_assets": processed_assets,
        "processed_devices": processed_devices,
        "inserted_or_updated": inserted_or_updated,
        "skipped_devices": skipped_devices,
        "errors": errors,
    }