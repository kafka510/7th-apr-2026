"""
Laplace System (L-eye / Solar Link ARCH) adapter.

This adapter is designed for projects like Minamata where the provider exposes measurement
data via Digest-authenticated endpoints and CSV download APIs.

Key mapping convention (finalized in PLAN_LAPLACEID.md):
- device_list.device_code is the provider-facing "node id" (XML unit=node) and the CSV header prefix.
- device_list.device_id is the internal id written into timeseries_data.device_id.
- CSV device-specific columns are named: "{device_code} {oem_tag}".
- device_mapping.oem_tag maps the provider tag (CSV suffix or XML tag name) to internal metric.

Writes are staging-based and overwrite-safe: delete destination range then insert staged rows.
"""

from __future__ import annotations

import csv
import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

import requests
from requests.auth import HTTPDigestAuth

from data_collection.adapters import register
from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


STAGING_TABLE = "staging_timeseries"
CREATE_STAGING_TEMP_TABLE_SQL = f"""
CREATE TEMP TABLE IF NOT EXISTS {STAGING_TABLE} (
    device_id text NOT NULL,
    ts timestamptz NOT NULL,
    oem_metric text NOT NULL,
    metric text NOT NULL,
    value text NOT NULL
);
"""


def _sleep_if_needed(last_call_monotonic: List[float], min_seconds: float) -> None:
    if min_seconds <= 0:
        return
    now = time.monotonic()
    if last_call_monotonic:
        elapsed = now - last_call_monotonic[0]
        if elapsed < min_seconds:
            time.sleep(min_seconds - elapsed)
    if last_call_monotonic:
        last_call_monotonic[0] = time.monotonic()
    else:
        last_call_monotonic.append(time.monotonic())


def _parse_asset_timezone_offset(asset_tz: Any) -> Optional[dt_timezone]:
    """
    Parse AssetList.timezone string like '+09:00' into datetime.timezone.
    Returns None when invalid/missing.
    """
    s = ("" if asset_tz is None else str(asset_tz)).strip()
    if not s:
        return None
    if len(s) < 6 or s[0] not in "+-":
        return None
    try:
        sign = 1 if s[0] == "+" else -1
        hh, mm = s[1:].split(":")
        offset = timedelta(hours=int(hh) * sign, minutes=int(mm) * sign)
        return dt_timezone(offset)
    except Exception:
        return None


def _parse_provider_datetime(value: Any, default_tz: Optional[dt_timezone]) -> Optional[datetime]:
    """
    Parse provider datetime strings.

    We do not "shift" timestamps. If value is naive, we attach default_tz (asset timezone)
    if provided; otherwise we assume UTC to keep timestamptz consistent.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Common provider forms:
    # - YYYY/MM/DD HH:MM
    # - YYYY/MM/DD HH:MM:SS
    # - YYYY-MM-DD HH:MM:SS
    # - DD-MM-YYYY HH:MM[:SS] (seen in some exports)
    s_norm = " ".join(s.split())
    for fmt in (
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s_norm, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=default_tz or dt_timezone.utc)
            return dt
        except Exception:
            pass
    # ISO-ish: 'YYYY/MM/DDTHH:MM+0900' or '+09:00'
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=default_tz or dt_timezone.utc)
        return dt
    except Exception:
        return None


def _decode_csv_bytes(content: bytes) -> str:
    """
    Laplace CSV is Shift-JIS in provider exports. Decode with Shift-JIS first,
    then fallback to compatible encodings.
    """
    for enc in ("shift_jis", "cp932", "utf-8-sig", "utf-8"):
        try:
            return content.decode(enc)
        except Exception:
            continue
    # last resort
    return content.decode("utf-8", errors="replace")


def _request_get(
    base_url: str,
    path: str,
    params: Dict[str, Any],
    username: str,
    password: str,
    timeout_s: int = 60,
) -> requests.Response:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    return requests.get(url, params=params, auth=HTTPDigestAuth(username, password), timeout=timeout_s)


def _build_api_root(
    *,
    api_base_url: str,
    path_username: str,
    api_root_suffix: str,
) -> str:
    """
    Build full API root URL.

    Your provider convention:
      api_base_url = "https://services.energymntr.com/megasolar/"
      full root    = "{api_base_url}/{path_username}/{api_root_suffix}/"

    Where api_root_suffix typically is:
      - "services/api/download"    (CSV)
      - "services/api/generating"  (XML instant.php in some deployments)
    """
    base = (api_base_url or "").strip().rstrip("/")
    u = (path_username or "").strip().strip("/")
    suf = (api_root_suffix or "").strip().strip("/")
    if not base or not u or not suf:
        return ""
    return f"{base}/{u}/{suf}/"


@dataclass(frozen=True)
class DeviceInfo:
    device_id: str
    device_code: str
    device_type: str


def _load_devices_for_asset(asset_code: str) -> Dict[str, DeviceInfo]:
    """
    Return map: device_code -> DeviceInfo (internal device_id, type).
    """
    from main.models import device_list

    out: Dict[str, DeviceInfo] = {}
    for row in device_list.objects.filter(parent_code=asset_code).values("device_id", "device_code", "device_type"):
        code = (row.get("device_code") or "").strip()
        if not code:
            continue
        out[code] = DeviceInfo(
            device_id=(row.get("device_id") or "").strip(),
            device_code=code,
            device_type=(row.get("device_type") or "").strip(),
        )
    return out


def _load_metric_map(mapping_asset_code: str) -> Dict[str, str]:
    """
    Return map: oem_tag -> metric.

    mapping_asset_code is either 'laplaceid' (adapter-level) or an asset_code (asset-level),
    depending on how device_mapping is maintained.
    """
    from main.models import device_mapping

    out: Dict[str, str] = {}
    for row in device_mapping.objects.filter(asset_code=mapping_asset_code).values("oem_tag", "metric"):
        oem = (row.get("oem_tag") or "").strip()
        if not oem:
            continue
        out[oem] = (row.get("metric") or "").strip() or oem
    return out


def _split_header(header: str) -> Tuple[Optional[str], str]:
    """
    Split CSV header into (device_code, oem_tag) using "{device_code} {oem_tag}".
    If no split possible, returns (None, header).
    """
    h = (header or "").strip()
    if not h:
        return (None, "")
    if " " not in h:
        return (None, h)
    first, rest = h.split(" ", 1)
    first = first.strip()
    rest = rest.strip()
    if not first or not rest:
        return (None, h)
    return (first, rest)


def _rows_from_csv_text(
    *,
    asset_code: str,
    csv_text: str,
    mapping_asset_code: str,
    site_level_device_id: Optional[str] = None,
) -> Tuple[List[Tuple[str, datetime, str, str, str]], Optional[datetime], Optional[datetime], Dict[str, Any]]:
    """
    Convert provider CSV into timeseries rows.

    Returns:
    - rows: [(device_id, ts, oem_metric, metric, value)]
    - min_ts, max_ts
    - stats dict
    """
    from main.models import AssetList

    asset = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
    default_tz = _parse_asset_timezone_offset(getattr(asset, "timezone", None)) if asset else None

    devices_by_code = _load_devices_for_asset(asset_code)
    metric_map = _load_metric_map(mapping_asset_code)
    if site_level_device_id is None:
        site_level_device_id = asset_code

    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        return [], None, None, {"error": "CSV has no headers"}
    fieldnames = [x.strip() for x in (reader.fieldnames or []) if x and str(x).strip()]
    date_col = None
    for c in fieldnames:
        if c.lower() == "date":
            date_col = c
            break
    if not date_col:
        # Provider CSV uses 'Date' in your scripts; keep strict to avoid silent misparse
        return [], None, None, {"error": "CSV missing 'Date' column"}

    rows: List[Tuple[str, datetime, str, str, str]] = []
    min_ts: Optional[datetime] = None
    max_ts: Optional[datetime] = None

    columns_processed = 0
    device_columns = 0
    site_columns = 0

    for rec in reader:
        ts = _parse_provider_datetime(rec.get(date_col), default_tz)
        if not ts:
            continue
        if min_ts is None or ts < min_ts:
            min_ts = ts
        if max_ts is None or ts > max_ts:
            max_ts = ts

        for hdr in fieldnames:
            if hdr == date_col:
                continue
            raw_v = rec.get(hdr)
            if raw_v is None:
                continue
            s = str(raw_v).strip()
            if s == "":
                continue
            # Normalize numeric-like strings but keep original if not parseable
            try:
                v = str(float(s))
            except Exception:
                v = s

            device_code, oem_tag = _split_header(hdr)
            if device_code is not None:
                device_columns += 1
                dev = devices_by_code.get(device_code)
                if not dev or not dev.device_id:
                    continue
                metric = metric_map.get(oem_tag) or oem_tag
                rows.append((dev.device_id, ts, oem_tag, metric, v))
                columns_processed += 1
            else:
                site_columns += 1
                metric = metric_map.get(oem_tag) or oem_tag
                rows.append((site_level_device_id, ts, oem_tag, metric, v))
                columns_processed += 1

    stats = {
        "field_count": len(fieldnames),
        "device_columns_seen": device_columns,
        "site_columns_seen": site_columns,
        "rows_emitted": len(rows),
    }
    return rows, min_ts, max_ts, stats


def _write_rows_staging_overwrite(
    rows: List[Tuple[str, datetime, str, str, str]],
    *,
    delete_start_ts: Optional[datetime] = None,
    delete_end_ts: Optional[datetime] = None,
) -> int:
    if not rows:
        return 0
    # Overwrite scope must be limited to the incoming query family.
    # If we delete only by device_id + ts window, daily and minute datasets can clobber each other.
    delete_scope: Dict[str, set[str]] = {}
    for device_id, _ts, oem_metric, _metric, _value in rows:
        delete_scope.setdefault(device_id, set()).add(oem_metric)
    start_ts = delete_start_ts or min(r[1] for r in rows)
    end_ts = delete_end_ts or max(r[1] for r in rows)

    with connection.cursor() as cursor:
        cursor.execute(CREATE_STAGING_TEMP_TABLE_SQL)
        buf = io.StringIO()
        w = csv.writer(buf)
        for device_id, ts, oem_metric, metric, value in rows:
            w.writerow([device_id, ts.isoformat(), oem_metric, metric, value])
        buf.seek(0)
        cursor.copy_expert(
            f"""
            COPY {STAGING_TABLE} (device_id, ts, oem_metric, metric, value)
            FROM STDIN WITH (FORMAT csv)
            """,
            buf,
        )
        with transaction.atomic():
            for did, oem_metrics in delete_scope.items():
                if not oem_metrics:
                    continue
                cursor.execute(
                    """
                    DELETE FROM timeseries_data
                    WHERE device_id = %s
                      AND oem_metric = ANY(%s)
                      AND ts >= %s AND ts <= %s
                    """,
                    [did, list(oem_metrics), start_ts, end_ts],
                )
            cursor.execute(
                f"""
                INSERT INTO timeseries_data (device_id, ts, oem_metric, metric, value)
                SELECT device_id, ts, oem_metric, metric, value FROM {STAGING_TABLE}
                """
            )
        cursor.execute(f"TRUNCATE {STAGING_TABLE}")
    return len(rows)


def fetch_nodes_xml(
    *,
    base_url: str,
    username: str,
    password: str,
    groupid: str = "1",
    time_param: str = "now",
    aliases: bool = True,
    api_path: str = "instant.php",
    min_seconds_between_calls: float = 0.0,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Return list of nodes from XML unit=node.

    Each node: { "node_id": "3", "name": "...", "setTime": "...", "tags": ["acEnergy", ...] }
    """
    meta, nodes, err = fetch_instant_xml(
        base_url=base_url,
        username=username,
        password=password,
        groupid=groupid,
        time_param=time_param,
        aliases=aliases,
        api_path=api_path,
        min_seconds_between_calls=min_seconds_between_calls,
    )
    _ = meta
    return nodes, err


def fetch_instant_xml(
    *,
    base_url: str,
    username: str,
    password: str,
    groupid: str = "1",
    time_param: str = "now",
    aliases: bool = True,
    api_path: str = "instant.php",
    min_seconds_between_calls: float = 0.0,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
    """
    Fetch XML instant.php unit=node and return (meta, nodes, error).

    meta includes:
    - instant_date: <instant><date>
    - instant_name: <instant><name> (group / site name)
    - api_version: <apiVersion>
    """
    last_call: List[float] = []
    _sleep_if_needed(last_call, min_seconds_between_calls)
    params = {"unit": "node", "groupid": groupid, "time": time_param}
    if aliases:
        params["aliases"] = "true"
    resp = _request_get(base_url, api_path, params, username, password, timeout_s=60)
    if resp.status_code != 200:
        return {}, [], f"HTTP {resp.status_code}"
    txt = resp.text
    try:
        root = ET.fromstring(txt)
    except Exception as e:
        return {}, [], f"Invalid XML: {e}"
    status = (root.findtext("apiStatus") or "").strip().lower()
    if status != "succeed":
        return {}, [], f"apiStatus={status or 'unknown'}"
    instant = root.find(".//instant")
    if instant is None:
        return {}, [], "Missing <instant>"

    meta = {
        "api_version": (root.findtext("apiVersion") or "").strip(),
        "instant_date": (instant.findtext("date") or "").strip(),
        "instant_name": (instant.findtext("name") or "").strip(),
    }
    nodes_out: List[Dict[str, Any]] = []
    for node in instant.findall("node"):
        nid = (node.findtext("id") or "").strip()
        nm = (node.findtext("name") or "").strip()
        st = (node.findtext("setTime") or "").strip()
        tags = []
        for child in list(node):
            if child.tag in ("id", "name", "setTime"):
                continue
            tags.append(child.tag)
        nodes_out.append({"node_id": nid, "name": nm, "setTime": st, "tags": tags})
    return meta, nodes_out, None


@register("laplaceid")
def laplaceid_fetch_and_store(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main adapter entrypoint.

    Supports two acquisition modes:
    - CSV download (recommended for bulk writes): config.mode="csv"
    - XML instant/node (for discovery or limited real-time): config.mode="xml"

    Required config (usually from AdapterAccount):
    - api_base_url, username, password

    CSV config keys (recommended):
    - csv_api: path like "daily.php" (default "daily.php")
    - unit: "halfhour" or "minute" (default depends on acquisition interval)
    - groupid: default "1"
    - time: provider time parameter (if omitted: minute → previous local hour YYYYMMDDHH using asset_list.timezone; else day/month defaults)
    - type: "pcs" | "string" | "battery" | "approvedmeter" (default "pcs")
    - data: "measuringdata" (default)
    - format: "csv" (default)
    - summarize: optional bool

    Mapping config keys:
    - mapping_asset_code: device_mapping.asset_code to use; default "laplaceid"
    - site_level_device_id: device_id to use for non-prefixed headers; default asset_code
    """
    api_base_url = (config.get("api_base_url") or "").strip()
    username = (config.get("username") or "").strip()
    password = (config.get("password") or "").strip()
    if not api_base_url or not username or not password:
        return {"success": False, "error": "laplaceid requires api_base_url, username, password"}

    # Path username convention: default to digest username unless explicitly overridden.
    path_username = (config.get("path_username") or username).strip()
    csv_api_root_suffix = (config.get("csv_api_root_suffix") or "services/api/download").strip()
    xml_api_root_suffix = (config.get("xml_api_root_suffix") or "services/api/generating").strip()

    csv_root = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=csv_api_root_suffix)
    xml_root = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=xml_api_root_suffix)
    if not csv_root:
        return {"success": False, "error": "Invalid api_base_url/path_username/csv_api_root_suffix configuration"}

    mode = (config.get("mode") or "csv").strip().lower()
    mapping_asset_code = (config.get("mapping_asset_code") or "laplaceid").strip() or "laplaceid"
    site_level_device_id = (config.get("site_level_device_id") or asset_code).strip() or asset_code

    # Provider restriction: no simultaneous access, and 1 request per 10 minutes per API.
    # For now we keep a simple minimum interval; production scheduling should enforce larger windows.
    min_seconds_between_calls = float(config.get("min_seconds_between_calls") or 0.0)
    last_call: List[float] = []

    if mode == "xml":
        # For now: discovery only; do not write all tags unless explicitly enabled.
        nodes, err = fetch_nodes_xml(
            base_url=xml_root or csv_root,
            username=username,
            password=password,
            groupid=str(config.get("groupid") or "1"),
            time_param=str(config.get("time") or "now"),
            aliases=bool(config.get("aliases", True)),
            api_path=str(config.get("xml_api") or "instant.php"),
            min_seconds_between_calls=min_seconds_between_calls,
        )
        if err:
            return {"success": False, "error": err}
        return {"success": True, "mode": "xml", "nodes": nodes}

    # CSV mode
    csv_api = str(config.get("csv_api") or "").strip()
    unit = str(config.get("unit") or "").strip()
    groupid = str(config.get("groupid") or "1").strip() or "1"
    data_kind = str(config.get("data") or "measuringdata").strip() or "measuringdata"
    csv_type = str(config.get("type") or "pcs").strip() or "pcs"
    fmt = str(config.get("format") or "csv").strip() or "csv"
    summarize = config.get("summarize")

    # Default unit/time based on acquisition interval
    interval_minutes = int(config.get("acquisition_interval_minutes") or 5)
    if not unit:
        # Schedule-driven defaults for Laplace:
        # - 30-min run (WH): unit=halfhour
        # - 60-min run (1-min points): unit=minute
        # - daily: hour/day style aggregates
        if interval_minutes == 30:
            unit = "halfhour"
        elif interval_minutes == 60:
            unit = "minute"
        elif interval_minutes >= 1440:
            unit = "day"
        else:
            unit = "minute"
    if not csv_api:
        # Endpoint default follows selected unit.
        csv_api = "hourly.php" if unit == "minute" else "daily.php"

    time_param = str(config.get("time") or "").strip()
    from_param = str(config.get("from") or "").strip()
    to_param = str(config.get("to") or "").strip()
    now = timezone.now()
    if not time_param:
        asset_tz_obj = None
        try:
            from main.models import AssetList

            row = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
            asset_tz_obj = _parse_asset_timezone_offset(getattr(row, "timezone", None)) if row else None
        except Exception:
            asset_tz_obj = None
        local_now = now.astimezone(asset_tz_obj or dt_timezone.utc)

        if unit == "minute":
            asset_tz = None
            try:
                from main.models import AssetList

                row = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
                if row and str(row.timezone or "").strip():
                    asset_tz = str(row.timezone).strip()
            except Exception:
                asset_tz = None
            from data_collection.services.laplace_request_time import laplace_time_yyyymmddhh_previous_local_hour

            time_param = laplace_time_yyyymmddhh_previous_local_hour(asset_timezone_offset=asset_tz)
        elif unit in ("halfhour", "hour"):
            # daily.php half-hour/hour queries use site-local day
            time_param = local_now.strftime("%Y%m%d")
        elif unit == "month":
            time_param = local_now.strftime("%Y%m")
        else:
            time_param = local_now.strftime("%Y%m%d")

    params: Dict[str, Any] = {
        "unit": unit,
        "groupid": groupid,
        "data": data_kind,
        "format": fmt,
        "type": csv_type,
    }
    # span.php uses from/to instead of time.
    if csv_api == "span.php":
        if from_param:
            params["from"] = from_param
        if to_param:
            params["to"] = to_param
    else:
        params["time"] = time_param
    if summarize is not None:
        params["summarize"] = "true" if bool(summarize) else "false"

    _sleep_if_needed(last_call, min_seconds_between_calls)
    resp = _request_get(csv_root, csv_api, params, username, password, timeout_s=120)
    if resp.status_code != 200:
        return {"success": False, "error": f"Laplace CSV HTTP {resp.status_code}"}

    csv_text = _decode_csv_bytes(resp.content)
    rows, min_ts, max_ts, stats = _rows_from_csv_text(
        asset_code=asset_code,
        csv_text=csv_text,
        mapping_asset_code=mapping_asset_code,
        site_level_device_id=site_level_device_id,
    )
    if stats.get("error"):
        return {"success": False, "error": stats["error"]}

    # Optional "replace all day data" mode (for 30-min WH runs / daily.php):
    # delete full queried local day for incoming oem_metrics, then insert staged rows.
    delete_start_ts = None
    delete_end_ts = None
    try:
        if bool(config.get("replace_all_day_data")):
            tstr = str(time_param or "").strip()
            if len(tstr) >= 8 and tstr[:8].isdigit():
                q_date = datetime.strptime(tstr[:8], "%Y%m%d").date()
                from main.models import AssetList

                asset_row = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
                tz_obj = _parse_asset_timezone_offset(getattr(asset_row, "timezone", None)) if asset_row else None
                tz_obj = tz_obj or dt_timezone.utc
                delete_start_ts = datetime(q_date.year, q_date.month, q_date.day, 0, 0, 0, tzinfo=tz_obj)
                delete_end_ts = delete_start_ts + timedelta(days=1)
    except Exception:
        delete_start_ts = None
        delete_end_ts = None

    written = _write_rows_staging_overwrite(rows, delete_start_ts=delete_start_ts, delete_end_ts=delete_end_ts)
    return {
        "success": True,
        "mode": "csv",
        "points_written": written,
        "min_ts": min_ts.isoformat() if min_ts else None,
        "max_ts": max_ts.isoformat() if max_ts else None,
        "stats": stats,
    }

