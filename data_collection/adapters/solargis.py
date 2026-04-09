"""
SolarGIS data collection adapter.

Fetches satellite irradiance (GHI, GTI, DNI, DIF, PVOUT, TMOD, TEMP, WS, WD, RH)
from SolarGIS REST API and writes to timeseries_data only for the source asset:
  device_id = {asset_code}_sat, metric = sat_ghi (GHI), sat_amb_temp (TEMP), etc.,
  ts = timestamp with timezone from Solargis (per-row, not aggregated).
Sites B and C that use A's data (satellite_irradiance_source_asset_code) have nothing
written; A's data is read for them at display/calculation time to avoid duplicate storage.
"""
import csv
import io
import logging
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

import pandas as pd
import requests

from data_collection.adapters import register
from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

SOLARGIS_NS = "http://geomodel.eu/schema/ws/data"
SATELLITE_DEVICE_SUFFIX = "_sat"
STAGING_TABLE = "staging_timeseries"
# Session-scoped temp table (per connection); safe for concurrent workers.
# No id column: timeseries_data.id is bigint (DB-generated); we only insert device_id, ts, oem_metric, metric, value.
CREATE_STAGING_TEMP_TABLE_SQL = f"""
CREATE TEMP TABLE IF NOT EXISTS {STAGING_TABLE} (
    device_id text NOT NULL,
    ts timestamptz NOT NULL,
    oem_metric text NOT NULL,
    metric text NOT NULL,
    value text NOT NULL
);
"""

# SolarGIS column name -> timeseries metric name (device_id = asset_code_sat, ts = timestamp from Solargis)
METRIC_MAP = {
    "GHI": "sat_ghi",
    "GTI": "sat_gti",
    "DNI": "sat_dni",
    "DIF": "sat_dif",
    "TEMP": "sat_amb_temp",  # ambient temperature
    "PVOUT": "sat_pvout",
    "TMOD": "sat_tmod",
    "WS": "sat_ws",
    "WD": "sat_wd",
    "RH": "sat_rh",
}
# Only these two metrics are written to the database
WRITE_METRICS = {"GHI": "sat_ghi", "TEMP": "sat_amb_temp"}
# No-data sentinel values from Solargis (do not write to DB)
NO_DATA_VALUES = (-9.0, -99.0)

DEFAULT_PROCESSING_KEYS = "GHI DNI DIF GTI SE SA PVOUT TMOD TEMP WS WD RH CI_FLAG"
DEFAULT_SUMMARIZATION = "MIN_5"
DEFAULT_TIMESTAMP_TYPE = "CENTER"


def _parse_timezone_offset(tz_str: Optional[str]) -> float:
    """Parse asset_list.timezone (+05:30 or -08:00) to numeric offset (e.g. 5.5, -8.0)."""
    if not tz_str or not str(tz_str).strip():
        return 0.0
    s = str(tz_str).strip()
    try:
        if s.startswith("+"):
            sign = 1
            s = s[1:]
        elif s.startswith("-"):
            sign = -1
            s = s[1:]
        else:
            sign = 1
        parts = s.split(":")
        h = int(parts[0]) if parts else 0
        m = int(parts[1]) * (1 / 60.0) if len(parts) > 1 else 0
        return sign * (h + m)
    except (ValueError, IndexError):
        return 0.0


def _timezone_gmt_string(offset: float) -> str:
    """Convert numeric offset to GMT+9 or GMT-5 format for SolarGIS."""
    if offset >= 0:
        return f"GMT+{int(offset)}" if offset == int(offset) else f"GMT+{offset}"
    return f"GMT{int(offset)}" if offset == int(offset) else f"GMT{offset}"


def _get_tilt_azimuth(asset: Any, config: Dict[str, Any]) -> Tuple[float, float]:
    """Resolve tilt and azimuth from asset_list.tilt_configs or config."""
    tilt = config.get("tilt")
    azimuth = config.get("azimuth")
    if tilt is not None and azimuth is not None:
        try:
            return float(tilt), float(azimuth)
        except (ValueError, TypeError):
            pass
    tilt_configs = getattr(asset, "tilt_configs", None)
    if tilt_configs and isinstance(tilt_configs, list) and len(tilt_configs) > 0:
        tc = tilt_configs[0]
        if isinstance(tc, dict):
            tilt = tc.get("tilt_deg", tc.get("tilt")) or 0
            azimuth = tc.get("azimuth_deg", tc.get("azimuth")) or 180
            try:
                return float(tilt), float(azimuth)
            except (ValueError, TypeError):
                pass
    return 0.0, 180.0


def _get_date_range() -> Tuple[date, date]:
    """Return last 3 calendar days: (day-3, day-1) inclusive."""
    today = timezone.now().date()
    end_date = today - timedelta(days=1)  # yesterday
    start_date = today - timedelta(days=3)  # day-3
    return start_date, end_date


def _parse_date_range_from_config(config: Dict[str, Any]) -> Optional[Tuple[date, date]]:
    """
    If config has date_from and date_to (ISO date strings), parse and return (start_date, end_date).
    Otherwise return None (caller uses _get_date_range()).
    """
    date_from_str = config.get("date_from")
    date_to_str = config.get("date_to")
    if not date_from_str or not date_to_str:
        return None
    try:
        start_date = date.fromisoformat(str(date_from_str).strip())
        end_date = date.fromisoformat(str(date_to_str).strip())
        if start_date > end_date:
            return None
        return (start_date, end_date)
    except (ValueError, TypeError):
        return None


@register("solargis")
def solargis_fetch_and_store(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch SolarGIS data for last 3 days and write to timeseries_data.

    Reads lat/lng/alt/capacity/timezone from asset_list; api_url, api_key,
    summarization, processing_keys from config.
    Overwrites existing data for that device_id and time window (delete + bulk insert).
    """
    from main.models import AssetList

    api_url = config.get("api_url") or ""
    api_key = config.get("api_key") or ""
    summarization = config.get("summarization") or DEFAULT_SUMMARIZATION
    processing_keys = config.get("processing_keys") or DEFAULT_PROCESSING_KEYS
    terrain_shading = config.get("terrain_shading", True)
    time_stamp_type = config.get("time_stamp_type") or DEFAULT_TIMESTAMP_TYPE

    if not api_url or not api_key:
        return {"success": False, "error": "api_url and api_key are required in config"}

    try:
        asset = AssetList.objects.get(asset_code=asset_code)
    except AssetList.DoesNotExist:
        return {"success": False, "error": f"Asset {asset_code} not found in asset_list"}

    lat = asset.latitude
    lng = asset.longitude
    if lat is None or lng is None:
        return {"success": False, "error": f"Asset {asset_code} has no latitude/longitude"}

    alt = getattr(asset, "altitude_m", None) or 0
    cap = float(asset.capacity) if asset.capacity is not None else 0
    if cap <= 0:
        return {"success": False, "error": f"Asset {asset_code} has no capacity"}

    tz_offset = _parse_timezone_offset(asset.timezone)
    tz_str = _timezone_gmt_string(tz_offset)
    tilt, azimuth = _get_tilt_azimuth(asset, config)
    sitename = (asset.asset_name or asset_code).replace(" ", "_")

    date_range = _parse_date_range_from_config(config)
    if date_range is not None:
        start_date, end_date = date_range
        logger.info(
            "Solargis adapter %s: using config date range %s to %s",
            asset_code,
            start_date.isoformat(),
            end_date.isoformat(),
        )
    else:
        start_date, end_date = _get_date_range()
        logger.debug("Solargis adapter %s: using default date range (last 3 days)", asset_code)
    date_from = start_date.isoformat()
    date_to = end_date.isoformat()

    # Solargis site id:
    # - Prefer explicit config["asset_id"] when provided (so user can control the id used in Solargis).
    # - Fallback to asset_code.
    # - Ensure the id matches XML NCName pattern ([\i-[:]][\c-[:]]*): cannot start with a digit.
    raw_site_id = (config.get("asset_id") or "").strip()
    site_id = raw_site_id or asset_code
    if not site_id or not str(site_id)[0].isalpha():
        site_id = f"S_{site_id or asset_code}"

    request_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ws:dataDeliveryRequest dateFrom="{date_from}" dateTo="{date_to}"
  xmlns="http://geomodel.eu/schema/data/request"
  xmlns:ws="http://geomodel.eu/schema/ws/data"
  xmlns:geo="http://geomodel.eu/schema/common/geo"
  xmlns:pv="http://geomodel.eu/schema/common/pv"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <site id="{site_id}" name="{sitename}" lat="{lat}" lng="{lng}">
    <pv:geometry xsi:type="pv:GeometryFixedOneAngle" tilt="{tilt}" azimuth="{azimuth}"/>
    <pv:system installedPower="{cap}" installationType="FREE_STANDING" selfShading="true">
      <pv:module type="CSI"></pv:module>
      <pv:inverter></pv:inverter>
      <pv:losses></pv:losses>
      <pv:topology xsi:type="pv:TopologyRow" relativeSpacing="2.5" type="UNPROPORTIONAL2"/>
    </pv:system>
  </site>
  <processing key="{processing_keys}" summarization="{summarization}" terrainShading="{str(terrain_shading).lower()}">
    <timeZone>{tz_str}</timeZone>
    <timestampType>{time_stamp_type}</timestampType>
  </processing>
</ws:dataDeliveryRequest>'''

    url = f"{api_url.rstrip('?')}?key={api_key}" if "?" not in api_url else f"{api_url}&key={api_key}"

    try:
        resp = requests.post(
            url,
            data=request_xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            timeout=120,
        )
    except requests.RequestException as e:
        logger.exception("SolarGIS API request failed for %s", asset_code)
        return {"success": False, "error": str(e)}

    # Count this API call in data_collection_last_written_reading (persistent, shared across workers)
    try:
        from data_collection.services.solargis_daily_calls import increment_solargis_daily_api_calls

        increment_solargis_daily_api_calls()
    except Exception:
        pass

    if resp.status_code != 200:
        return {
            "success": False,
            "error": f"SolarGIS API returned {resp.status_code}: {resp.text[:500]}",
        }

    try:
        root = ElementTree.fromstring(resp.text)
    except ElementTree.ParseError as e:
        return {"success": False, "error": f"Invalid SolarGIS response XML: {e}"}

    columns_elem = root.find(f".//{{{SOLARGIS_NS}}}columns")
    if columns_elem is None or columns_elem.text is None:
        return {"success": False, "error": "SolarGIS response missing columns"}

    columns = columns_elem.text.split()
    data_dict = {}
    for row_elem in root.iter(f"{{{SOLARGIS_NS}}}row"):
        attrs = row_elem.attrib
        ts_str = attrs.get("dateTime")
        vals_str = attrs.get("values")
        if not ts_str or not vals_str:
            continue
        try:
            values = [float(v) for v in vals_str.split()]
        except ValueError:
            continue
        if len(values) == len(columns):
            data_dict[ts_str] = values

    if not data_dict:
        return {"success": False, "error": "SolarGIS response contained no data rows"}

    df = pd.DataFrame.from_dict(data_dict, orient="index", columns=columns)
    idx = pd.to_datetime(df.index, errors="coerce")
    if getattr(idx, "tz", None) is None:
        # If provider returns naive local timestamps, attach asset timezone from asset_list.
        asset_tz = dt_timezone(timedelta(hours=tz_offset))
        idx = idx.tz_localize(asset_tz, nonexistent="shift_forward", ambiguous="infer")
    idx = idx.tz_convert(dt_timezone.utc)
    df.index = idx
    df.index.name = "time"
    df = df.reset_index()
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Only write for the source asset (device_id = asset_code_sat). B and C do not get data
    # written; they use A's data at read time via satellite_irradiance_source_asset_code.
    device_id = f"{asset_code}{SATELLITE_DEVICE_SUFFIX}"

    numeric_cols = [c for c in columns if c in WRITE_METRICS]
    if not numeric_cols:
        logger.warning("SolarGIS adapter: no write metrics in columns for %s", asset_code)
        return {"success": True, "points_written": 0, "asset_code": asset_code}

    # Vectorized: melt to long form, filter, then build rows (faster than iterrows())
    long = df.melt(
        id_vars=["time"],
        value_vars=numeric_cols,
        var_name="oem_metric",
        value_name="value",
    )
    long = long.dropna(subset=["value"])
    if long.empty:
        logger.warning("SolarGIS adapter: no rows to insert for %s", asset_code)
        return {"success": True, "points_written": 0, "asset_code": asset_code}
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["value"])
    long = long[~long["value"].isin(NO_DATA_VALUES)]
    if long.empty:
        return {"success": True, "points_written": 0, "asset_code": asset_code}
    long["metric"] = long["oem_metric"].map(WRITE_METRICS)
    long = long.dropna(subset=["metric"])
    # Rows for staging: (device_id, ts, oem_metric, metric, value) — no id; timeseries_data.id is bigint (DB-generated)
    insert_rows = []
    for ts, oem, metric, val in zip(
        long["time"], long["oem_metric"], long["metric"], long["value"]
    ):
        ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        if ts_dt.tzinfo is None:
            ts_dt = timezone.make_aware(ts_dt, dt_timezone.utc)
        insert_rows.append((device_id, ts_dt, oem, metric, str(val)))

    if not insert_rows:
        logger.warning("SolarGIS adapter: no rows to insert for %s", asset_code)
        return {"success": True, "points_written": 0, "asset_code": asset_code}

    start_ts = min(r[1] for r in insert_rows)
    end_ts = max(r[1] for r in insert_rows)

    with connection.cursor() as cursor:
        # Ensure session-scoped temp staging table exists (per connection; safe for concurrent workers)
        cursor.execute(CREATE_STAGING_TEMP_TABLE_SQL)
        # Bulk-load into staging via COPY
        buf = io.StringIO()
        writer = csv.writer(buf)
        for r in insert_rows:
            writer.writerow([r[0], r[1].isoformat(), r[2], r[3], r[4]])
        buf.seek(0)
        cursor.copy_expert(
            f"""
            COPY {STAGING_TABLE} (device_id, ts, oem_metric, metric, value)
            FROM STDIN WITH (FORMAT csv)
            """,
            buf,
        )

        # Validate staging
        cursor.execute(
            f"""
            SELECT COUNT(*), MIN(ts), MAX(ts) FROM {STAGING_TABLE}
            """
        )
        count, min_ts, max_ts = cursor.fetchone()
        if count == 0:
            cursor.execute(f"TRUNCATE {STAGING_TABLE}")
            return {"success": True, "points_written": 0, "asset_code": asset_code}
        if count != len(insert_rows):
            cursor.execute(f"TRUNCATE {STAGING_TABLE}")
            logger.error(
                "SolarGIS adapter: staging count %s != expected %s for %s",
                count,
                len(insert_rows),
                asset_code,
            )
            return {"success": False, "points_written": 0, "asset_code": asset_code}

        # Atomic replace: DELETE for this device + ts range, then INSERT from staging
        with transaction.atomic():
            cursor.execute(
                """
                DELETE FROM timeseries_data
                WHERE device_id = %s AND ts >= %s AND ts <= %s
                """,
                [device_id, start_ts, end_ts],
            )
            deleted = cursor.rowcount
            cursor.execute(
                f"""
                INSERT INTO timeseries_data (device_id, ts, oem_metric, metric, value)
                SELECT device_id, ts, oem_metric, metric, value FROM {STAGING_TABLE}
                """
            )
        cursor.execute(f"TRUNCATE {STAGING_TABLE}")

    logger.info(
        "SolarGIS adapter: asset_code=%s device_id=%s deleted=%d written=%d",
        asset_code,
        device_id,
        deleted,
        len(insert_rows),
    )
    return {
        "success": True,
        "points_written": len(insert_rows),
        "asset_code": asset_code,
        "deleted_count": deleted,
    }


def solargis_fetch_raw_data_delivery_xml(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the same dataDeliveryRequest as ``solargis_fetch_and_store`` and return the raw HTTP body.

    Used for onboarding verification downloads. Does **not** write to the database and does **not**
    increment the SolarGIS daily API call counter.
    """
    from main.models import AssetList

    api_url = config.get("api_url") or ""
    api_key = config.get("api_key") or ""
    summarization = config.get("summarization") or DEFAULT_SUMMARIZATION
    processing_keys = config.get("processing_keys") or DEFAULT_PROCESSING_KEYS
    terrain_shading = config.get("terrain_shading", True)
    time_stamp_type = config.get("time_stamp_type") or DEFAULT_TIMESTAMP_TYPE

    if not api_url or not api_key:
        return {"success": False, "error": "api_url and api_key are required in config"}

    try:
        asset = AssetList.objects.get(asset_code=asset_code)
    except AssetList.DoesNotExist:
        return {"success": False, "error": f"Asset {asset_code} not found in asset_list"}

    lat = asset.latitude
    lng = asset.longitude
    if lat is None or lng is None:
        return {"success": False, "error": f"Asset {asset_code} has no latitude/longitude"}

    alt = getattr(asset, "altitude_m", None) or 0
    cap = float(asset.capacity) if asset.capacity is not None else 0
    if cap <= 0:
        return {"success": False, "error": f"Asset {asset_code} has no capacity"}

    tz_offset = _parse_timezone_offset(asset.timezone)
    tz_str = _timezone_gmt_string(tz_offset)
    tilt, azimuth = _get_tilt_azimuth(asset, config)
    sitename = (asset.asset_name or asset_code).replace(" ", "_")

    date_range = _parse_date_range_from_config(config)
    if date_range is not None:
        start_date, end_date = date_range
    else:
        start_date, end_date = _get_date_range()
    date_from = start_date.isoformat()
    date_to = end_date.isoformat()

    raw_site_id = (config.get("asset_id") or "").strip()
    site_id = raw_site_id or asset_code
    if not site_id or not str(site_id)[0].isalpha():
        site_id = f"S_{site_id or asset_code}"

    request_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ws:dataDeliveryRequest dateFrom="{date_from}" dateTo="{date_to}"
  xmlns="http://geomodel.eu/schema/data/request"
  xmlns:ws="http://geomodel.eu/schema/ws/data"
  xmlns:geo="http://geomodel.eu/schema/common/geo"
  xmlns:pv="http://geomodel.eu/schema/common/pv"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <site id="{site_id}" name="{sitename}" lat="{lat}" lng="{lng}">
    <pv:geometry xsi:type="pv:GeometryFixedOneAngle" tilt="{tilt}" azimuth="{azimuth}"/>
    <pv:system installedPower="{cap}" installationType="FREE_STANDING" selfShading="true">
      <pv:module type="CSI"></pv:module>
      <pv:inverter></pv:inverter>
      <pv:losses></pv:losses>
      <pv:topology xsi:type="pv:TopologyRow" relativeSpacing="2.5" type="UNPROPORTIONAL2"/>
    </pv:system>
  </site>
  <processing key="{processing_keys}" summarization="{summarization}" terrainShading="{str(terrain_shading).lower()}">
    <timeZone>{tz_str}</timeZone>
    <timestampType>{time_stamp_type}</timestampType>
  </processing>
</ws:dataDeliveryRequest>'''

    url = f"{api_url.rstrip('?')}?key={api_key}" if "?" not in api_url else f"{api_url}&key={api_key}"

    try:
        resp = requests.post(
            url,
            data=request_xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            timeout=120,
        )
    except requests.RequestException as e:
        logger.exception("SolarGIS raw preview request failed for %s", asset_code)
        return {"success": False, "error": str(e)}

    if resp.status_code != 200:
        return {
            "success": False,
            "error": f"SolarGIS API returned {resp.status_code}: {resp.text[:500]}",
        }

    return {"success": True, "content": resp.text, "asset_code": asset_code}
