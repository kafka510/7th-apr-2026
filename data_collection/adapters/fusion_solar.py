"""
Fusion Solar (Huawei) data collection adapter.

Uses the Huawei FusionSolar Northbound API:
- Login: POST /thirdData/login (userName, systemCode) -> xsrf-token in response header
- Plant list: POST /thirdData/getStationList
- Device list: POST /thirdData/getDevList (stationCodes)
- Real-time device data: POST /thirdData/getDevRealKpi (devIds, devTypeId)

Token: we cache the xsrf-token and reuse it while valid. When a request returns 401/403 or a JSON
body with failCode 305 / USER_MUST_RELOGIN (session expired while HTTP stays 200), we fetch a new
token and retry once. This reduces login calls and handles expiry.

Writes to timeseries_data via staging (DELETE range + INSERT). Respects rate limits.
plant_id comes from config or asset_list.provider_asset_id when available.

Multi-asset in a single query:
- getDevList: stationCodes accepts comma-separated station codes (e.g. "code1,code2");
  one call can return devices for multiple plants; response items typically include
  stationCode so devices can be attributed to the correct asset.
- getDevRealKpi: devIds is comma-separated device IDs; device IDs are global in the API,
  so one call can include devices from multiple assets. Response includes devId per
  record; map back to asset via device_list (device_code=devId, parent_code=asset_code).
  The adapter currently runs per-asset; a batched runner could group by devTypeId across
  assets and issue one getDevRealKpi per type for all assets to reduce API calls.
"""
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import io
import logging
import time
from datetime import date, datetime, timedelta, time as dt_time, timezone as dt_timezone
from datetime import timezone as py_timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from data_collection.adapters import register
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Token cache: reuse xsrf-token while valid; refresh on 401/403 or JSON failCode 305 (see _needs_fusion_token_refresh)
# TTL chosen so we refresh before typical API expiry (e.g. 30–60 min)
FUSION_SOLAR_TOKEN_CACHE_TTL_SECONDS = 20 * 60  # 20 minutes
FUSION_SOLAR_TOKEN_CACHE_KEY_PREFIX = "fusion_solar_xsrf:"

# Staging: same pattern as Solargis (temp table per connection)
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

# Default rate limit: calls per minute (Fusion Solar may throttle)
DEFAULT_RATE_LIMIT_CALLS_PER_MINUTE = 30
# Minimum seconds between API calls
MIN_SECONDS_BETWEEN_CALLS = 2.0
# HTTP 429 Too Many Requests: retries and exponential backoff (9.2)
MAX_429_RETRIES = 3
INITIAL_429_BACKOFF_SECONDS = 2.0
# Max device IDs per getDevRealKpi request if API has a limit (9.3); 0 = no chunking
DEFAULT_MAX_DEVICES_PER_REQUEST = 0
# Provider hard limit for getDevRealKpi: max 100 devices per request (failCode 20016/20017).
PROVIDER_MAX_DEVICES_PER_REQUEST = 100
# Device types to skip for real-time acquisition (known unsupported/non-required).
REALTIME_EXCLUDED_DEV_TYPE_IDS = {"63"}  # datalogger
# Historical interface safeguards (provider-friendly conservative defaults).
# Can be overridden from adapter config but never beyond provider limits.
DEFAULT_HISTORY_MAX_DAYS_PER_REQUEST = 3
DEFAULT_HISTORY_MAX_DEVICES_PER_REQUEST = 10
HISTORICAL_SUPPORTED_DEV_TYPE_IDS = {"1", "10", "17", "38", "39", "41", "47"}
# thirdData/getDevKpiDay for OEM daily product: only string inverters (Huawei devTypeId = 1).
FUSION_SOLAR_DEV_KPI_DAY_DEVICE_TYPE_ID = "1"
# getDevKpiDay collectTime (ms) is midnight on the provider's calendar day; Huawei uses UTC+8 boundaries.
# When asset_list.timezone is unset, use this for ms → date so rows align with the Fusion portal.
FUSION_SOLAR_DEFAULT_OEM_DAILY_TZ = dt_timezone(timedelta(hours=8))


def _parse_asset_timezone_offset(asset_tz: Any) -> Optional[dt_timezone]:
    """Parse asset_list.timezone '+HH:MM'/'-HH:MM' to fixed-offset tz."""
    s = ("" if asset_tz is None else str(asset_tz)).strip()
    if not s or len(s) < 6 or s[0] not in "+-":
        return None
    try:
        sign = 1 if s[0] == "+" else -1
        hh, mm = s[1:].split(":")
        return dt_timezone(timedelta(hours=int(hh) * sign, minutes=int(mm) * sign))
    except Exception:
        return None


def _rate_limit(last_call_time: List[float], calls_per_minute: int) -> None:
    """Sleep if needed to respect rate limit. Mutates last_call_time in place (list with one float)."""
    if calls_per_minute <= 0:
        return
    interval = 60.0 / calls_per_minute
    interval = max(interval, MIN_SECONDS_BETWEEN_CALLS)
    now = time.monotonic()
    if last_call_time:
        elapsed = now - last_call_time[0]
        if elapsed < interval:
            time.sleep(interval - elapsed)
    if last_call_time:
        last_call_time[0] = now
    else:
        last_call_time.append(now)


def _normalize_fusion_api_dev_id(raw: Any) -> str:
    """
    Normalize devId from Fusion JSON (may be int, float, or string).
    Large numeric JSON values can arrive as float; avoid losing precision for huge integers.
    """
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return ""
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return ""
        # Whole floats only (e.g. 1e16); otherwise fall through to Decimal
        if raw.is_integer():
            return str(int(raw))
    return _normalize_fusion_solar_dev_id(raw)


def _unwrap_fusion_kpi_day_data(data: Any) -> Any:
    """getDevKpiDay sometimes returns { data: [...] } or { data: { list: [...] } }."""
    if isinstance(data, dict):
        inner = data.get("list")
        if isinstance(inner, list):
            return inner
    return data


def _collect_time_to_provider_date(
    value: Any,
    plant_tz: Optional[dt_timezone] = None,
) -> Optional[date]:
    """
    Map Fusion collectTime to the calendar day shown in the Fusion portal for that plant.

    String collectTime values are parsed as YYYY-MM-DD / Ymd as-is.

    Numeric collectTime is epoch milliseconds at the **start** of that calendar day in the
    plant timezone (Huawei uses UTC+8 when the station timezone is China). We convert the
    UTC instant to the plant offset (asset_list.timezone, else UTC+8) and take `.date()`.
    Using UTC-only `.date()` shifts rows by one day vs the portal for non-UTC plants.
    """
    if value is None:
        return None

    # Support explicit date strings first.
    s = str(value).strip()
    if s:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return datetime.strptime(s[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        if len(s) == 8 and s.isdigit():
            try:
                return datetime.strptime(s, "%Y%m%d").date()
            except ValueError:
                pass

    # Epoch milliseconds -> calendar date in plant timezone (Fusion portal day).
    tz = plant_tz if plant_tz is not None else FUSION_SOLAR_DEFAULT_OEM_DAILY_TZ
    try:
        sec = float(value) / 1000.0
    except (TypeError, ValueError):
        return None
    try:
        utc = datetime.fromtimestamp(sec, tz=py_timezone.utc)
        return utc.astimezone(tz).date()
    except (OSError, OverflowError, ValueError):
        return None


def _normalize_fusion_solar_dev_id(raw: Any) -> str:
    """
    Normalize Fusion Solar devId string to a plain integer string.

    Some environments/CSV imports may store large numeric IDs in scientific notation
    (e.g. "1.00E+15"). Fusion Solar expects the full integer string, e.g. "1000000000000000".
    """
    s = ("" if raw is None else str(raw)).strip()
    if not s:
        return ""
    # Already a plain integer
    if s.isdigit():
        return s
    # Try to normalize scientific notation (or floats) into an integer string
    try:
        d = Decimal(s)
        # If it is an integer value, format without exponent/decimal
        if d == d.to_integral_value():
            return format(d.to_integral_value(), "f")
    except (InvalidOperation, ValueError):
        pass
    return s


def _cache_key_for_credentials(base_url: str, username: str) -> str:
    """Cache key for token storage (one per base_url + username)."""
    raw = f"{base_url.strip()}|{username.strip()}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"{FUSION_SOLAR_TOKEN_CACHE_KEY_PREFIX}{h}"


def _get_or_refresh_token(
    base_url: str,
    username: str,
    password: str,
    force_refresh: bool = False,
) -> Optional[str]:
    """
    Return a valid xsrf-token: from cache if present and not force_refresh, else login and cache.
    When a request returns 401/403 or failCode 305 / USER_MUST_RELOGIN, call with force_refresh=True to get a new token.
    """
    key = _cache_key_for_credentials(base_url, username)
    if not force_refresh:
        token = cache.get(key)
        if token:
            return token
    if force_refresh:
        try:
            cache.delete(key)
        except Exception:
            pass
    token = _login(base_url, username, password)
    if token:
        try:
            cache.set(key, token, timeout=FUSION_SOLAR_TOKEN_CACHE_TTL_SECONDS)
        except Exception as e:
            logger.debug("Fusion Solar: could not cache token: %s", e)
    return token


def _login(
    base_url: str,
    username: str,
    password: str,
) -> Optional[str]:
    """
    POST /thirdData/login with userName, systemCode.
    Returns xsrf-token from response headers, or None on failure.
    """
    url = f"{base_url.rstrip('/')}/thirdData/login"
    payload = {"userName": username, "systemCode": password}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        token = resp.headers.get("xsrf-token") or resp.headers.get("XSRF-TOKEN")
        if not token:
            logger.warning("Fusion Solar login: no xsrf-token in response headers")
            return None
        return token.strip()
    except requests.RequestException as e:
        logger.warning(
            "Fusion Solar login failed base_url=%s (username present=%s): %s",
            base_url.rstrip("/"),
            bool(username),
            e,
        )
        logger.exception("Fusion Solar login failed")
        return None


def _request(
    base_url: str,
    path: str,
    data: Dict[str, Any],
    xsrf_token: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    """
    POST JSON to base_url + path with xsrf-token header.
    Returns (response body, status_code). On 401/403 or JSON failCode 305, caller should refresh token and retry.
    On HTTP 429 (Too Many Requests): retries up to MAX_429_RETRIES with exponential backoff (9.2).
    On success returns (json_body, 200). On exception returns (None, None).
    """
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    # Fusion Solar expects XSRF token header; keep both spellings for compatibility.
    headers = {
        "XSRF-TOKEN": xsrf_token,
        "xsrf-token": xsrf_token,
        "Content-Type": "application/json",
    }
    last_status: Optional[int] = None
    for attempt in range(MAX_429_RETRIES + 1):
        try:
            resp = requests.post(url, json=data, headers=headers, timeout=60)
            last_status = resp.status_code

            if resp.status_code == 200:
                return resp.json(), 200
            if resp.status_code == 429 and attempt < MAX_429_RETRIES:
                backoff = INITIAL_429_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "Fusion Solar API %s returned 429 (attempt %s/%s), retrying in %.1fs",
                    path,
                    attempt + 1,
                    MAX_429_RETRIES + 1,
                    backoff,
                )
                time.sleep(backoff)
                continue
            # Preserve provider payload on non-200 so callers can log failCode/message.
            try:
                body = resp.json()
                if isinstance(body, dict):
                    return body, last_status
                return {"success": False, "message": str(body), "http_status": last_status}, last_status
            except ValueError:
                text = (resp.text or "").strip()
                return {
                    "success": False,
                    "message": text[:500] if text else f"HTTP {last_status}",
                    "http_status": last_status,
                }, last_status
        except requests.RequestException as e:
            logger.warning("Fusion Solar API %s failed: %s", path, e)
            return None, None
    return None, last_status


def _is_relogin_required(out: Optional[Dict[str, Any]]) -> bool:
    """True if API indicates USER_MUST_RELOGIN (e.g. failCode 305 or message)."""
    if not out:
        return False
    fail_code = out.get("failCode") or out.get("fail_code")
    if fail_code is not None and str(fail_code).strip() != "":
        try:
            if int(fail_code) == 305:
                return True
        except (TypeError, ValueError):
            pass
    msg = (out.get("message") or out.get("msg") or "").upper()
    return "USER_MUST_RELOGIN" in msg or "MUST_RELOGIN" in msg or "RELOGIN" in msg


def _needs_fusion_token_refresh(status: Optional[int], out: Optional[Dict[str, Any]]) -> bool:
    """True if caller should force a new xsrf-token and retry the same request once."""
    return status in (401, 403) or _is_relogin_required(out)


def _provider_error_message(
    out: Optional[Dict[str, Any]],
    status: Optional[int],
    default: str = "provider request failed",
) -> str:
    """
    Build a stable, readable provider error message for logs and task results.
    Avoids opaque "None" messages by including status/failCode/message when present.
    """
    if not isinstance(out, dict):
        return f"{default} | status={status if status is not None else 'none'} | no response body"
    fail_code = out.get("failCode") or out.get("fail_code")
    msg = out.get("message") or out.get("msg") or out.get("error_description") or out.get("error")
    data = out.get("data")
    if not msg and isinstance(data, dict):
        msg = data.get("message") or data.get("msg") or data.get("error")
    if not msg:
        msg = default
    return f"{msg} | status={status if status is not None else 'none'} | failCode={fail_code if fail_code is not None else 'none'}"


def get_station_list(
    base_url: str,
    username: str,
    password: str,
) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Login and fetch station (plant) list. Returns (list of station dicts, error).

    Uses Fusion Solar /thirdData/stations endpoint, which returns richer fields like:
      plantCode, plantName, plantAddress, latitude, longitude, capacity, contactPerson, etc.

    On failCode 305 / USER_MUST_RELOGIN we force token refresh and retry once.
    """
    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return None, "Login failed"
    # Use the richer stations endpoint instead of getStationList so callers (including onboarding wizard)
    # can see coordinates and other metadata. This endpoint requires pagination params.
    payload: Dict[str, Any] = {
        "pageNo": 1,
        "pageSize": 500,
    }
    out, status = _request(base_url, "thirdData/stations", payload, token)
    if _needs_fusion_token_refresh(status, out):
        token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
        if token:
            out, status = _request(base_url, "thirdData/stations", payload, token)
    if not out or not out.get("success"):
        return None, out.get("message", "getStationList failed") if out else "No response"
    data = out.get("data")
    if data is None:
        return [], None
    # API can return either:
    # - {"data": [ {...}, {...} ]} or
    # - {"data": {"list": [ {...}, {...} ], ...}}.
    # Normalise to a simple list of station dicts so callers (including the onboarding wizard)
    # can see all plant fields such as latitude, longitude, plantAddress, etc.
    if isinstance(data, dict) and "list" in data:
        data = data.get("list")
    if isinstance(data, list):
        return data, None
    return None, "Unexpected getStationList data format"


def get_dev_list(
    base_url: str,
    username: str,
    password: str,
    station_code: str,
) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Fetch device list for a station. Returns (list of device dicts, error).
    Request: {"stationCodes": "NE=123456789"} (station_code format may vary).
    API device fields typically: devId -> device_code; devName -> device_name;
    devTypeId -> device_type_id; devTypeName -> device_type. parent_code is set
    to asset_code by the caller when mapping to device_list.
    """
    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return None, "Login failed"
    out, status = _request(
        base_url,
        "thirdData/getDevList",
        {"stationCodes": station_code},
        token,
    )
    if _needs_fusion_token_refresh(status, out):
        token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
        if token:
            out, status = _request(
                base_url,
                "thirdData/getDevList",
                {"stationCodes": station_code},
                token,
            )
    if not out or not out.get("success"):
        if isinstance(out, dict):
            provider_success = out.get("success")
            fail_code = out.get("failCode") or out.get("fail_code")
            message = out.get("message") or out.get("msg") or "getDevList failed"
            # Include compact provider payload for onboarding diagnostics.
            payload = {
                "success": provider_success,
                "failCode": fail_code,
                "message": message,
                "status": status,
                "stationCodes": station_code,
            }
            return None, f"{message} | provider={payload}"
        return None, f"No response | status={status} | stationCodes={station_code}"
    data = out.get("data")
    if data is None:
        return [], None
    if isinstance(data, list):
        return data, None
    return None, "Unexpected getDevList data format"


def get_dev_list_detailed(
    base_url: str,
    username: str,
    password: str,
    station_code: str,
) -> Tuple[Optional[List[Dict]], Optional[str], Dict[str, Any]]:
    """
    Detailed getDevList variant for debugging onboarding issues.
    Returns (devices, error, diagnostics) where diagnostics includes upstream
    response metadata to help identify provider-side failures.
    """
    diagnostics: Dict[str, Any] = {
        "endpoint": "thirdData/getDevList",
        "station_code": station_code,
    }
    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        diagnostics["token"] = "missing"
        return None, "Login failed", diagnostics
    diagnostics["token"] = "present"

    out, status = _request(
        base_url,
        "thirdData/getDevList",
        {"stationCodes": station_code},
        token,
    )
    diagnostics["status"] = status
    if isinstance(out, dict):
        diagnostics["provider_success"] = out.get("success")
        diagnostics["provider_failCode"] = out.get("failCode") or out.get("fail_code")
        diagnostics["provider_message"] = out.get("message") or out.get("msg")

    if _needs_fusion_token_refresh(status, out):
        diagnostics["relogin_retry"] = True
        token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
        if token:
            out, status = _request(
                base_url,
                "thirdData/getDevList",
                {"stationCodes": station_code},
                token,
            )
            diagnostics["status"] = status
            if isinstance(out, dict):
                diagnostics["provider_success"] = out.get("success")
                diagnostics["provider_failCode"] = out.get("failCode") or out.get("fail_code")
                diagnostics["provider_message"] = out.get("message") or out.get("msg")
        else:
            diagnostics["token_refresh"] = "failed"
            return None, "Login refresh failed", diagnostics

    if not out or not out.get("success"):
        message = out.get("message", "getDevList failed") if isinstance(out, dict) else "No response"
        return None, message, diagnostics

    data = out.get("data")
    if data is None:
        diagnostics["device_count"] = 0
        return [], None, diagnostics
    if isinstance(data, list):
        diagnostics["device_count"] = len(data)
        return data, None, diagnostics

    diagnostics["data_type"] = type(data).__name__
    return None, "Unexpected getDevList data format", diagnostics


def get_dev_real_kpi(
    base_url: str,
    xsrf_token: str,
    dev_ids: str,
    dev_type_id: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    """
    Real-time device KPIs. dev_ids can be comma-separated; dev_type_id e.g. 1 (inverter), 38 (meter).
    Returns (response dict, status_code). Caller should refresh token and retry on 401/403 or failCode 305.
    """
    return _request(
        base_url,
        "thirdData/getDevRealKpi",
        {"devIds": dev_ids, "devTypeId": dev_type_id},
        xsrf_token,
    )


def get_dev_history_kpi(
    base_url: str,
    xsrf_token: str,
    dev_ids: str,
    dev_type_id: str,
    start_time_ms: int,
    end_time_ms: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    """
    Historical 5-minute KPI interface.
    Uses getDevHistoryKpi with [start_time_ms, end_time_ms] window.
    Callers should retry after token refresh on HTTP 401/403 or failCode 305.
    """
    return _request(
        base_url,
        "thirdData/getDevHistoryKpi",
        {
            "devIds": dev_ids,
            "devTypeId": dev_type_id,
            "startTime": int(start_time_ms),
            "endTime": int(end_time_ms),
        },
        xsrf_token,
    )


def get_dev_kpi_day(
    base_url: str,
    xsrf_token: str,
    dev_ids: str,
    dev_type_id: str,
    collect_time: Union[str, int],
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    """
    Daily device KPI (Northbound thirdData/getDevKpiDay).
    collect_time: YYYYMMDD string, or epoch milliseconds (int) for month/day queries per Huawei Northbound.
    Callers should retry after token refresh on HTTP 401/403 or failCode 305.
    """
    return _request(
        base_url,
        "thirdData/getDevKpiDay",
        {
            "devIds": dev_ids,
            "devTypeId": int(dev_type_id) if str(dev_type_id).isdigit() else dev_type_id,
            "collectTime": collect_time,
        },
        xsrf_token,
    )


def _parse_oem_product_power_kwh(data_item_map: Any) -> Optional[float]:
    """Extract daily product energy from getDevKpiDay dataItemMap (kWh as float)."""
    if not isinstance(data_item_map, dict):
        return None
    raw = None
    for key in ("product_power", "productPower", "product_power_kwh"):
        if key in data_item_map and data_item_map[key] is not None:
            raw = data_item_map[key]
            break
    if raw is None:
        return None
    try:
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return None
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val != val:  # NaN
        return None
    return val


def _parse_oem_month_range(date_from: str, date_to: str) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Parse YYYY-MM or YYYY-MM-DD into (year, month) start/end inclusive."""

    def to_ym(s: str) -> Tuple[int, int]:
        s = (s or "").strip()
        if len(s) < 7 or s[4] != "-":
            raise ValueError("expected YYYY-MM or YYYY-MM-DD")
        y = int(s[:4])
        mo = int(s[5:7])
        if not (1 <= mo <= 12):
            raise ValueError("invalid month")
        return y, mo

    a = to_ym(date_from)
    b = to_ym(date_to)
    if (a[0], a[1]) > (b[0], b[1]):
        raise ValueError("date_from month cannot be after date_to month")
    return a, b


def _iter_year_months(y1: int, m1: int, y2: int, m2: int):
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def _month_start_epoch_ms(year: int, month: int, tz: Optional[dt_timezone]) -> int:
    """First instant of calendar month as epoch milliseconds (UTC month start if tz is None)."""
    if tz is None:
        dt = datetime(year, month, 1, 0, 0, 0, tzinfo=py_timezone.utc)
    else:
        dt = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    return int(dt.timestamp() * 1000)


def _representative_plant_tz(tz_by_parent: Dict[str, Optional[dt_timezone]]) -> Optional[dt_timezone]:
    """Use first non-null timezone from assets for month-boundary collectTime (multi-plant: best-effort)."""
    for _k in sorted(tz_by_parent.keys()):
        v = tz_by_parent.get(_k)
        if v is not None:
            return v
    return None


def _truncate_kpis_text(val: Any, max_len: int = 120) -> str:
    s = ("" if val is None else str(val)).strip()
    return s[:max_len] if len(s) > max_len else s


def _upsert_oem_daily_product_kwh(
    dev_id_local: str,
    day_date: date,
    kwh: float,
    parent_code: str,
) -> int:
    """
    Set kpis.oem_daily_product_kwh for (device_id, day_date). If no row exists, insert a minimal row:
    internal KPI columns use placeholders (0 kWh, start-of-day UTC timestamps) until compute_daily_kpis fills them.
    Independent from main.tasks.compute_daily_kpis_previous_day (different columns on update).
    Direct ORM writes — no staging (staging is only used for Fusion → timeseries_data).
    Returns 1 if a row was updated or inserted, 0 on failure.
    """
    from main.models import AssetList, device_list, kpis

    dev_id_local = (dev_id_local or "").strip()
    if not dev_id_local:
        return 0

    with transaction.atomic():
        n = kpis.objects.filter(device_id=dev_id_local, day_date=day_date).update(oem_daily_product_kwh=kwh)
        if n:
            return 1

        dev_row = (
            device_list.objects.filter(device_id=dev_id_local).values("device_name", "parent_code").first()
        )
        device_name = _truncate_kpis_text((dev_row or {}).get("device_name"))
        p = (parent_code or "").strip() or _truncate_kpis_text((dev_row or {}).get("parent_code"))
        asset = None
        if p:
            asset = AssetList.objects.filter(asset_code=p).only("asset_code", "asset_number", "asset_name").first()
        asset_code = _truncate_kpis_text(p)
        if not asset_code:
            asset_code = "unknown"
        asset_number = _truncate_kpis_text(
            getattr(asset, "asset_number", None) if asset else None
        ) or asset_code
        asset_name = _truncate_kpis_text(getattr(asset, "asset_name", None) if asset else None)

        placeholder_ts = datetime.combine(day_date, dt_time.min, tzinfo=py_timezone.utc)

        try:
            kpis.objects.create(
                device_id=dev_id_local,
                day_date=day_date,
                asset_code=asset_code,
                asset_number=asset_number,
                device_name=device_name,
                asset_name=asset_name,
                daily_min_read_time=placeholder_ts,
                daily_min_read_kwh=0.0,
                daily_max_read_time=placeholder_ts,
                daily_max_read_kwh=0.0,
                daily_max_min=0.0,
                daily_prod_rec=0.0,
                daily_prod_rec_time=placeholder_ts,
                day_1_max_read_time=placeholder_ts,
                day_1_max_read_kwh=0.0,
                oem_daily_product_kwh=kwh,
                generation_metric=None,
                has_anomaly=False,
                anomaly_flags=None,
                anomaly_notes=None,
            )
            return 1
        except IntegrityError:
            n2 = kpis.objects.filter(device_id=dev_id_local, day_date=day_date).update(oem_daily_product_kwh=kwh)
            return 1 if n2 else 0


def _match_oem_batch_device(batch: List[Dict[str, Any]], api_dev: str) -> Optional[Dict[str, Any]]:
    """Match Fusion devId to a row in the request batch (device_code is the OEM dev id for Fusion)."""
    if not api_dev:
        return None
    for d in batch:
        if _normalize_fusion_solar_dev_id(d.get("device_code")) == api_dev:
            return d
        if _normalize_fusion_solar_dev_id(d.get("device_id")) == api_dev:
            return d
    return None


def _apply_dev_kpi_day_payload_to_kpis(
    batch: List[Dict[str, Any]],
    data: Any,
    target_day_fallback: date,
    tz_by_parent: Dict[str, Optional[dt_timezone]],
) -> Tuple[int, Dict[str, int]]:
    """
    Upsert kpis.oem_daily_product_kwh per (device_id, day_date): update if row exists, else insert minimal row.
    Maps API devId to device_list rows; uses each record's collectTime (ms) for day_date when present.
    """
    data = _unwrap_fusion_kpi_day_data(data)
    if not isinstance(data, list):
        return 0, {}
    updated = 0
    per_parent: Dict[str, int] = defaultdict(int)
    for i, rec in enumerate(data):
        if not isinstance(rec, dict):
            continue
        api_dev = _normalize_fusion_api_dev_id(rec.get("devId"))
        matched: Optional[Dict[str, Any]] = None
        if api_dev:
            matched = _match_oem_batch_device(batch, api_dev)
        if not matched and i < len(batch):
            matched = batch[i]
        if not matched:
            continue
        dev_id_local = str(matched.get("device_id") or "").strip()
        row_for_parent = matched
        if not dev_id_local:
            continue
        parent = str(row_for_parent.get("parent_code") or "").strip()
        plant_tz = tz_by_parent.get(parent) if parent else None
        day_date = target_day_fallback
        ct = rec.get("collectTime")
        if ct is not None:
            parsed = _collect_time_to_provider_date(ct, plant_tz)
            if parsed is not None:
                day_date = parsed
        dim = rec.get("dataItemMap")
        if not isinstance(dim, dict):
            dim = {}
        kwh = _parse_oem_product_power_kwh(dim)
        if kwh is None:
            continue
        if logger.isEnabledFor(logging.DEBUG):
            utc_date_dbg = None
            try:
                sec = float(ct) / 1000.0
                utc_date_dbg = datetime.fromtimestamp(sec, tz=py_timezone.utc).date()
            except Exception:
                pass
            logger.debug(
                "Fusion OEM daily KPI row: parent=%s device_id=%s devId=%s collectTime=%s "
                "utc_calendar_date=%s day_date=%s oem_daily_product_kwh=%s plant_tz=%s",
                parent,
                dev_id_local,
                api_dev,
                ct,
                utc_date_dbg,
                day_date,
                kwh,
                plant_tz or FUSION_SOLAR_DEFAULT_OEM_DAILY_TZ,
            )
        n = _upsert_oem_daily_product_kwh(dev_id_local, day_date, kwh, parent)
        updated += n
        if parent:
            per_parent[parent] += n
    return updated, dict(per_parent)


def _sync_fusion_solar_oem_daily_kpis_for_months(
    sync_scope_label: str,
    devices: List[Dict[str, Any]],
    month_start: Tuple[int, int],
    month_end: Tuple[int, int],
    base_url: str,
    username: str,
    password: str,
    token_holder: List[Optional[str]],
    last_call: List[float],
    rate_limit_calls_per_minute: int,
) -> Dict[str, Any]:
    """
    Call getDevKpiDay once per calendar month per device batch (collectTime = month start as epoch ms).
    Response data lists daily points; each row's collectTime maps to kpis.day_date and oem_daily_product_kwh.
    Only Huawei devTypeId 1 (string inverters); batches up to 100 devIds per request.
    """
    if (month_start[0], month_start[1]) > (month_end[0], month_end[1]) or not devices or not token_holder or not token_holder[0]:
        return {
            "oem_daily_kpi_rows_updated": 0,
            "oem_daily_kpi_errors": [],
            "oem_daily_kpi_errors_by_asset": {},
            "oem_daily_kpi_rows_updated_by_asset": {},
        }

    inv_tid = FUSION_SOLAR_DEV_KPI_DAY_DEVICE_TYPE_ID
    inverters: List[Dict[str, Any]] = []
    for d in devices:
        raw_tid = d.get("device_type_id")
        if raw_tid is None:
            continue
        tid = str(raw_tid).strip()
        if not tid.isdigit() or tid != inv_tid:
            continue
        inverters.append(d)

    if not inverters:
        return {
            "oem_daily_kpi_rows_updated": 0,
            "oem_daily_kpi_errors": [],
            "oem_daily_kpi_errors_by_asset": {},
            "oem_daily_kpi_rows_updated_by_asset": {},
        }

    tz_by_parent: Dict[str, Optional[dt_timezone]] = {}
    parents = sorted(
        {str(d.get("parent_code") or "").strip() for d in inverters if (d.get("parent_code") or "").strip()}
    )
    if parents:
        try:
            from main.models import AssetList

            for row in AssetList.objects.filter(asset_code__in=parents).only("asset_code", "timezone"):
                ac = str(row.asset_code or "").strip()
                if ac:
                    tz_by_parent[ac] = _parse_asset_timezone_offset(getattr(row, "timezone", None))
        except Exception:
            logger.debug("Fusion Solar OEM: could not load AssetList timezones", exc_info=True)

    plant_tz = _representative_plant_tz(tz_by_parent)

    errors: List[str] = []
    errors_by_asset: Dict[str, List[str]] = defaultdict(list)
    total_updated = 0
    by_asset: Dict[str, int] = defaultdict(int)
    chunk_size = PROVIDER_MAX_DEVICES_PER_REQUEST
    dev_type_id = inv_tid
    y1, m1 = month_start
    y2, m2 = month_end
    for y, m in _iter_year_months(y1, m1, y2, m2):
        collect_ms = _month_start_epoch_ms(y, m, plant_tz)
        month_label = f"{y:04d}-{m:02d}"
        target_fallback = date(y, m, 1)
        batches = (
            [inverters[i : i + chunk_size] for i in range(0, len(inverters), chunk_size)]
            if chunk_size > 0
            else [inverters]
        )
        for batch in batches:
            _rate_limit(last_call, rate_limit_calls_per_minute)
            dev_ids_list = [
                _normalize_fusion_solar_dev_id(d.get("device_code") or d.get("device_id")) for d in batch
            ]
            dev_ids = ",".join([x for x in dev_ids_list if x])
            if not dev_ids:
                continue
            token = token_holder[0]
            out, status = get_dev_kpi_day(base_url, token, dev_ids, dev_type_id, collect_ms)
            if _needs_fusion_token_refresh(status, out):
                token_holder[0] = _get_or_refresh_token(base_url, username, password, force_refresh=True)
                if token_holder[0]:
                    out, status = get_dev_kpi_day(
                        base_url, token_holder[0], dev_ids, dev_type_id, collect_ms
                    )
            if not out or not out.get("success"):
                err_msg = _provider_error_message(out, status, default="getDevKpiDay failed")
                fc = out.get("failCode") if isinstance(out, dict) else None
                try:
                    fc_int = int(fc) if fc is not None and str(fc).strip() != "" else None
                except (TypeError, ValueError):
                    fc_int = None
                if fc_int == 20013:
                    logger.info(
                        "Fusion Solar getDevKpiDay skip devTypeId=%s (failCode 20013) scope=%s month=%s",
                        dev_type_id,
                        sync_scope_label,
                        month_label,
                    )
                    continue
                batch_parents = sorted(
                    {
                        str(d.get("parent_code") or "").strip()
                        for d in batch
                        if str(d.get("parent_code") or "").strip()
                    }
                )
                assets_in_batch = ",".join(batch_parents) if batch_parents else "unknown"
                err_detail = (
                    f"month={month_label} devTypeId={dev_type_id} "
                    f"assets_in_batch={assets_in_batch} error={err_msg}"
                )
                errors.append(err_detail)
                if batch_parents:
                    for ac in batch_parents:
                        errors_by_asset[ac].append(err_detail)
                else:
                    errors_by_asset["__unknown_parent__"].append(err_detail)
                log_assets = assets_in_batch if len(assets_in_batch) <= 400 else assets_in_batch[:397] + "..."
                logger.warning(
                    "Fusion Solar getDevKpiDay failed month=%s devTypeId=%s assets_in_batch=%s: %s",
                    month_label,
                    dev_type_id,
                    log_assets,
                    err_msg,
                )
                continue
            data = out.get("data")
            u, partial = _apply_dev_kpi_day_payload_to_kpis(batch, data, target_fallback, tz_by_parent)
            total_updated += u
            for pk, pv in partial.items():
                by_asset[pk] += pv

    if total_updated:
        logger.info(
            "Fusion Solar OEM daily KPI sync scope=%s months=%s..%s rows_updated=%s",
            sync_scope_label,
            f"{y1:04d}-{m1:02d}",
            f"{y2:04d}-{m2:02d}",
            total_updated,
        )
    return {
        "oem_daily_kpi_rows_updated": total_updated,
        "oem_daily_kpi_errors": errors,
        "oem_daily_kpi_errors_by_asset": {k: v for k, v in errors_by_asset.items() if v},
        "oem_daily_kpi_rows_updated_by_asset": dict(by_asset),
    }


def fusion_solar_sync_oem_daily_kpis_for_assets_bundle(
    asset_codes: List[str],
    config: Dict[str, Any],
    date_from: str,
    date_to: str,
) -> Dict[str, Any]:
    """
    getDevKpiDay for multiple assets sharing the same Fusion credentials: one login, batch devIds up to 100 per call.
    date_from/date_to: month range as YYYY-MM or YYYY-MM-DD (year-month taken from each); one API call per month
    with collectTime = first instant of that month (epoch ms, plant timezone when configured).
    Upserts kpis.oem_daily_product_kwh for devTypeId 1 (string inverters); creates minimal kpis rows when missing.
    """
    from main.models import device_list

    codes = sorted({str(c).strip() for c in (asset_codes or []) if c and str(c).strip()})
    if not codes:
        return {"success": False, "error": "no asset codes", "oem_daily_kpi_rows_updated_by_asset": {}}

    base_url = (config.get("api_base_url") or "").strip()
    username = (config.get("username") or "").strip()
    password = (config.get("password") or config.get("system_code") or "").strip()
    if not base_url or not username or not password:
        return {
            "success": False,
            "error": "api_base_url, username, and password are required",
            "asset_codes": codes,
            "oem_daily_kpi_rows_updated_by_asset": {},
        }

    df = (date_from or "").strip()
    dt = (date_to or "").strip()
    try:
        month_start, month_end = _parse_oem_month_range(df, dt)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e) or "date_from/date_to must be YYYY-MM or YYYY-MM-DD",
            "asset_codes": codes,
            "oem_daily_kpi_rows_updated_by_asset": {},
        }

    try:
        devices = list(
            device_list.objects.filter(parent_code__in=codes).values(
                "device_id",
                "device_code",
                "device_type_id",
                "device_type",
                "parent_code",
            )
        )
    except Exception as e:
        return {"success": False, "error": str(e), "asset_codes": codes, "oem_daily_kpi_rows_updated_by_asset": {}}

    if not devices:
        return {
            "success": True,
            "asset_codes": codes,
            "oem_daily_kpi_rows_updated": 0,
            "oem_daily_kpi_errors": [],
            "oem_daily_kpi_errors_by_asset": {},
            "oem_daily_kpi_rows_updated_by_asset": {ac: 0 for ac in codes},
            "message": "no devices under selected assets",
        }

    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return {
            "success": False,
            "error": "Fusion Solar login failed",
            "asset_codes": codes,
            "oem_daily_kpi_rows_updated_by_asset": {},
        }

    scope = ",".join(codes)
    if len(scope) > 200:
        scope = scope[:197] + "..."

    last_call: List[float] = []
    # Default 6/min (~10s spacing) to reduce wall time vs 1/min; cap to avoid failCode 407; override in adapter config.
    rl = int(config.get("oem_daily_rate_limit_calls_per_minute") or 6)
    rate_limit = max(1, min(rl, 30))
    token_holder: List[Optional[str]] = [token]
    sync_out = _sync_fusion_solar_oem_daily_kpis_for_months(
        scope,
        devices,
        month_start,
        month_end,
        base_url,
        username,
        password,
        token_holder,
        last_call,
        rate_limit,
    )
    return {"success": True, "asset_codes": codes, **sync_out}


def fusion_solar_sync_oem_daily_kpis_only(
    asset_code: str,
    config: Dict[str, Any],
    date_from: str,
    date_to: str,
) -> Dict[str, Any]:
    """
    getDevKpiDay only (devTypeId 1 / string inverters): upsert kpis.oem_daily_product_kwh (direct ORM, no staging).
    date_from/date_to: inclusive month range (YYYY-MM or YYYY-MM-DD). One API call per month.
    Does not write timeseries or call getDevHistoryKpi / getDevRealKpi.
    """
    ac = (asset_code or "").strip()
    out = fusion_solar_sync_oem_daily_kpis_for_assets_bundle([ac], config, date_from, date_to)
    out["asset_code"] = ac
    return out


# Adapter key used in device_mapping.asset_code for Fusion Solar metric mapping
DEVICE_MAPPING_ASSET_CODE = "fusion_solar"


def _load_fusion_solar_metric_map() -> Tuple[Dict[str, Dict[str, str]], Dict[str, str]]:
    """
    Load (device_type, oem_tag) -> metric from device_mapping where asset_code = 'fusion_solar'.

    We return:
    - mapping_by_device_type: { device_type: { oem_tag: metric } }
    - mapping_fallback: { oem_tag: metric } (first non-empty metric seen, used when device_type is missing)

    This avoids collisions where the same oem_tag exists for multiple device_types
    (e.g. "active_power" for string_inv vs gmt) with different metric targets.
    """
    from main.models import device_mapping

    mapping_by_device_type: Dict[str, Dict[str, str]] = {}
    mapping_fallback: Dict[str, str] = {}
    try:
        for row in device_mapping.objects.filter(asset_code=DEVICE_MAPPING_ASSET_CODE).values(
            "device_type",
            "oem_tag",
            "metric",
        ):
            device_type = (row.get("device_type") or "").strip()
            oem = (row.get("oem_tag") or "").strip()
            if not oem:
                continue
            metric = (row.get("metric") or "").strip()
            if device_type:
                mapping_by_device_type.setdefault(device_type, {})[oem] = metric
            # Fallback prefers first non-empty metric seen for this oem_tag
            if oem not in mapping_fallback or (not mapping_fallback.get(oem) and metric):
                mapping_fallback[oem] = metric
    except Exception as e:
        logger.warning("Fusion Solar: could not load device_mapping for %s: %s", DEVICE_MAPPING_ASSET_CODE, e)
    return mapping_by_device_type, mapping_fallback


def _parse_api_timestamp(ts_value: Any, default_tz: Optional[dt_timezone] = None) -> Optional[datetime]:
    """Parse API timestamp (ms/string). If naive, attach asset timezone (fallback UTC)."""
    if ts_value is None:
        return None
    try:
        # Fusion Solar collectTime can be provided as "local epoch" milliseconds.
        # When asset timezone is known, interpret the epoch-derived wall clock as local time
        # and convert to UTC for timestamptz storage.
        def _parse_epoch_localized(epoch_seconds: float) -> datetime:
            if default_tz is None:
                return datetime.fromtimestamp(epoch_seconds, tz=dt_timezone.utc)
            local_wall_clock = datetime.fromtimestamp(epoch_seconds, tz=dt_timezone.utc).replace(tzinfo=None)
            return local_wall_clock.replace(tzinfo=default_tz).astimezone(dt_timezone.utc)

        if isinstance(ts_value, (int, float)):
            v = float(ts_value)
            if v > 1e12:
                v = v / 1000.0
            return _parse_epoch_localized(v)
        if isinstance(ts_value, str):
            # ISO format or epoch string
            if ts_value.isdigit():
                v = int(ts_value)
                if v > 1e12:
                    v = v / 1000.0
                return _parse_epoch_localized(float(v))
            dt = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt, default_tz or dt_timezone.utc)
            return dt
    except Exception:
        pass
    return None


def _collect_device_rows(
    device_id: str,
    api_data: List[Dict],
    metric_map_by_type: Dict[str, Dict[str, str]],
    metric_map_fallback: Dict[str, str],
    base_ts: Optional[datetime],
    device_type: Optional[str] = None,
    default_tz: Optional[dt_timezone] = None,
) -> List[Tuple[str, datetime, str, str, str]]:
    """
    Convert API real-time KPI list to (device_id, ts, oem_metric, metric, value) rows.
    metric_map from device_mapping (asset_code=fusion_solar): oem_tag -> metric.
    If oem_tag not in map or metric is empty in DB, we write with metric='' (can be added later).
    """
    rows: List[Tuple[str, datetime, str, str, str]] = []
    ts = base_ts or timezone.now()
    for item in api_data if isinstance(api_data, list) else []:
        if not isinstance(item, dict):
            continue
        # Prefer explicit timestamps from payload record when available.
        t = _parse_api_timestamp(item.get("collectTime") or item.get("timestamp"), default_tz=default_tz)
        if t:
            ts = t
        code = item.get("dataItemCode") or item.get("dataItemCodeId")
        val = item.get("dataItemValue")
        if code is None:
            for k, v in item.items():
                if k in ("devId", "timestamp", "collectTime"):
                    if k == "collectTime" or k == "timestamp":
                        t = _parse_api_timestamp(v, default_tz=default_tz)
                        if t:
                            ts = t
                    continue
                if v is None or v == "":
                    continue
                # Use device_mapping metric if present; else fall back to oem metric key.
                # We must never drop data just because mapping is missing.
                metric = (
                    (metric_map_by_type.get((device_type or "").strip(), {}).get(k) if device_type else None)
                    or metric_map_fallback.get(k)
                    or str(k)
                )
                rows.append((device_id, ts, k, metric, str(v)))
            continue
        if val is None and "dataItemValue" in item:
            val = item["dataItemValue"]
        if val is None:
            continue
        oem = str(code)
        metric = (
            (metric_map_by_type.get((device_type or "").strip(), {}).get(oem) if device_type else None)
            or metric_map_fallback.get(oem)
            or oem
        )
        rows.append((device_id, ts, oem, metric, str(val)))
    return rows


def _collect_string_rows_from_inverter_payload(
    inverter_payload: Dict[str, Any],
    string_children_by_inverter: Dict[str, List[Dict[str, str]]],
    metric_map_by_type: Dict[str, Dict[str, str]],
    metric_map_fallback: Dict[str, str],
    fallback_ts: datetime,
    default_tz: Optional[dt_timezone] = None,
) -> List[Tuple[str, datetime, str, str, str]]:
    """
    Derive string metrics from inverter payload.

    For each configured string child device under an inverter:
    - {device_code}_i -> string_current
    - {device_code}_u -> string_voltage
    - string_power = current * voltage
    """
    out_rows: List[Tuple[str, datetime, str, str, str]] = []
    if not isinstance(inverter_payload, dict):
        return out_rows
    data_map = inverter_payload.get("dataItemMap")
    if not isinstance(data_map, dict):
        return out_rows

    dev_id = _normalize_fusion_solar_dev_id(inverter_payload.get("devId"))
    if not dev_id:
        return out_rows
    children = string_children_by_inverter.get(dev_id) or []
    if not children:
        return out_rows

    ts = _parse_api_timestamp(
        inverter_payload.get("collectTime") or inverter_payload.get("timestamp"),
        default_tz=default_tz,
    ) or fallback_ts
    metric_map_string = metric_map_by_type.get("string", {})
    for child in children:
        child_id = child.get("device_id") or ""
        code = (child.get("device_code") or "").strip()
        if not child_id or not code:
            continue
        i_key = f"{code}_i"
        u_key = f"{code}_u"
        i_val_raw = data_map.get(i_key)
        u_val_raw = data_map.get(u_key)

        i_val: Optional[Decimal] = None
        u_val: Optional[Decimal] = None
        if i_val_raw not in (None, ""):
            try:
                i_val = Decimal(str(i_val_raw))
            except (InvalidOperation, ValueError):
                i_val = None
        if u_val_raw not in (None, ""):
            try:
                u_val = Decimal(str(u_val_raw))
            except (InvalidOperation, ValueError):
                u_val = None

        if i_val is not None:
            metric_i = metric_map_string.get(i_key) or metric_map_fallback.get(i_key) or "string_current"
            out_rows.append((child_id, ts, i_key, metric_i, str(i_val)))
        if u_val is not None:
            metric_u = metric_map_string.get(u_key) or metric_map_fallback.get(u_key) or "string_voltage"
            out_rows.append((child_id, ts, u_key, metric_u, str(u_val)))
        if i_val is not None and u_val is not None:
            p_key = f"{code}_p"
            p_val = i_val * u_val
            metric_p = metric_map_string.get(p_key) or metric_map_fallback.get(p_key) or "string_power"
            out_rows.append((child_id, ts, p_key, metric_p, str(p_val)))
    return out_rows


# GHI device_source value for querying device_list (8.1)
DEFAULT_GHI_DEVICE_SOURCE = "ghi"


def _run_ghi_to_gii_for_asset(
    asset_code: str,
    start_ts: datetime,
    end_ts: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Run GHI→GII transposition for the asset if it has tilt_configs and a GHI device.
    Queries device_list for device_source='ghi' (8.1), fetches GHI from timeseries_data (8.2),
    calls ghi_to_gii per tilt_config (8.3), writes GII with device_id={asset_code}_gii_{tilt}_{azimuth} (8.4).
    Returns result dict from run_transpose or None if skipped (no tilt_configs or no GHI device).
    """
    from main.models import AssetList, device_list

    try:
        asset = AssetList.objects.filter(asset_code=asset_code).first()
        if not asset:
            return None
        tilt_configs = getattr(asset, "tilt_configs", None)
        if not tilt_configs or not isinstance(tilt_configs, list) or len(tilt_configs) == 0:
            return None
        # 8.1: query device_list for this asset with device_source = 'ghi'
        ghi_devices = list(
            device_list.objects.filter(
                parent_code=asset_code,
                device_source__iexact=DEFAULT_GHI_DEVICE_SOURCE,
            ).values_list("device_id", flat=True)[:1]
        )
        if not ghi_devices:
            return None
        irradiance_device_id = ghi_devices[0]
        from loss_analytics.pipeline.transpose_runner import run_transpose

        result = run_transpose(
            asset_code=asset_code,
            irradiance_device_id=irradiance_device_id,
            start_date_utc=start_ts,
            end_date_utc=end_ts,
            metric="ghi",
        )
        return result
    except Exception as e:
        logger.warning("Fusion Solar GHI→GII for %s: %s", asset_code, e)
        return {"success": False, "error": str(e)}


def _ensure_gii_devices_in_device_list(asset_code: str) -> None:
    """
    Ensure device_list contains rows for each GII synthetic device (8.6).
    One row per tilt_config: device_id = {asset_code}_gii_{tilt}_{azimuth}, parent_code = asset_code.
    """
    from main.models import AssetList, device_list
    from loss_analytics.pipeline.transposition import gii_device_id

    try:
        asset = AssetList.objects.filter(asset_code=asset_code).first()
        if not asset or not getattr(asset, "tilt_configs", None) or not isinstance(asset.tilt_configs, list):
            return
        country = (getattr(asset, "country", None) or "").strip() or "—"
        for cfg in asset.tilt_configs:
            if not isinstance(cfg, dict):
                continue
            try:
                tilt_deg = float(cfg.get("tilt_deg", 0))
                azimuth_deg = float(cfg.get("azimuth_deg", 0))
            except (TypeError, ValueError):
                continue
            dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
            device_name = f"GII {int(round(tilt_deg))}° {int(round(azimuth_deg))}°"
            # Provide all non-nullable fields for create; device_list has many required columns
            device_list.objects.update_or_create(
                device_id=dev_id,
                defaults={
                    "device_name": device_name[:40],
                    "device_code": (dev_id[:40] if len(dev_id) > 40 else dev_id),
                    "device_type_id": "gii",
                    "device_type": "GII",
                    "parent_code": asset_code[:40] if len(asset_code) > 40 else asset_code,
                    "country": country[:40] if len(country) > 40 else country,
                    "device_source": "gii",
                    "device_serial": "",
                    "device_model": "",
                    "device_make": "",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "optimizer_no": 0,
                    "software_version": "",
                    "string_no": "",
                    "connected_strings": "",
                    "device_sub_group": "",
                },
            )
    except Exception as e:
        logger.warning("Fusion Solar ensure GII devices in device_list for %s: %s", asset_code, e)


@register("fusion_solar")
def fusion_solar_fetch_and_store(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch Fusion Solar real-time data for the asset and write to timeseries_data.

    Config: api_base_url, username, password (or system_code), plant_id (optional;
    if not set, asset_code or provider_asset_id from asset_list used). Optional:
    rate_limit_calls_per_minute. For backfill, config may include date_from, date_to
    (YYYY-MM-DD); currently they are passed by the backfill task but this path
    performs a single real-time fetch. Full historical backfill would use
    getDevHistoryKpi in chunks when available.

    Devices: from device_list where parent_code=asset_code; device_code holds API device ID.
    Fetches getDevRealKpi per device type, maps to metrics, writes via staging.
    """
    from main.models import AssetList, device_list

    base_url = (config.get("api_base_url") or "").strip()
    username = (config.get("username") or "").strip()
    password = (config.get("password") or config.get("system_code") or "").strip()
    plant_id = (config.get("plant_id") or "").strip()

    if not base_url or not username or not password:
        return {"success": False, "error": "api_base_url, username, and password are required"}

    asset_tz_default: Optional[dt_timezone] = None
    try:
        asset_for_tz = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
        asset_tz_default = _parse_asset_timezone_offset(getattr(asset_for_tz, "timezone", None)) if asset_for_tz else None
    except Exception:
        asset_tz_default = None

    # Resolve plant_id: config first, then asset_list.provider_asset_id if we have it
    if not plant_id:
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
            plant_id = getattr(asset, "provider_asset_id", None) or ""
            plant_id = (plant_id or "").strip()
        except AssetList.DoesNotExist:
            return {"success": False, "error": f"Asset {asset_code} not found in asset_list"}
        if not plant_id:
            return {"success": False, "error": "plant_id not in config and asset has no provider_asset_id"}

    # Historical API supports only one concurrent request per minute.
    # Enforce strict pacing to avoid provider-side 407 throttling.
    rate_limit = 1
    configured_device_limit = int(config.get("max_devices_per_request") or DEFAULT_MAX_DEVICES_PER_REQUEST)
    max_devices_per_request = (
        PROVIDER_MAX_DEVICES_PER_REQUEST
        if configured_device_limit <= 0
        else max(1, min(configured_device_limit, PROVIDER_MAX_DEVICES_PER_REQUEST))
    )
    last_call: List[float] = []

    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return {"success": False, "error": "Fusion Solar login failed"}

    date_from = (config.get("date_from") or "").strip()
    date_to = (config.get("date_to") or "").strip()
    if date_from and date_to:
        return _fusion_solar_fetch_and_store_historical(asset_code, config)

    # Devices for this asset: device_list where parent_code=asset_code; device_code = API dev ID
    try:
        devices = list(
            device_list.objects.filter(parent_code=asset_code).values(
                "device_id",
                "device_code",
                "device_type_id",
                "device_type",
            )
        )
    except Exception as e:
        logger.exception("Fusion Solar: failed to load device_list for %s", asset_code)
        return {"success": False, "error": str(e)}

    if not devices:
        logger.info("Fusion Solar: no devices for asset %s", asset_code)
        return {"success": True, "points_written": 0, "asset_code": asset_code, "device_ids_with_no_data": []}

    # Single reference timestamp for this run so all devices use the same time when API does not provide one (7.1)
    run_ts = timezone.now()

    # Group by device_type_id for getDevRealKpi (devTypeId)
    by_type: Dict[str, List[Dict]] = {}
    for d in devices:
        tid = (d.get("device_type_id") or "1").strip() or "1"
        by_type.setdefault(tid, []).append(d)

    insert_rows: List[Tuple[str, datetime, str, str, str]] = []
    metric_map_by_type, metric_map_fallback = _load_fusion_solar_metric_map()
    string_children_by_inverter: Dict[str, List[Dict[str, str]]] = {}
    try:
        string_rows = list(
            device_list.objects.filter(parent_code=asset_code, device_type__iexact="string").values(
                "device_id", "device_code", "device_sub_group"
            )
        )
        for s in string_rows:
            subgroup = _normalize_fusion_solar_dev_id(s.get("device_sub_group"))
            if not subgroup:
                continue
            string_children_by_inverter.setdefault(subgroup, []).append(
                {
                    "device_id": str(s.get("device_id") or "").strip(),
                    "device_code": str(s.get("device_code") or "").strip(),
                }
            )
    except Exception:
        string_children_by_inverter = {}

    for dev_type_id, devs in by_type.items():
        dev_type_id = str(dev_type_id).strip()
        # Skip synthetic/non-OEM types (e.g. "gii") - these are handled via transposition (Phase 8)
        if not dev_type_id.isdigit():
            logger.debug("Fusion Solar: skipping non-numeric devTypeId=%s for asset=%s", dev_type_id, asset_code)
            continue
        if dev_type_id in REALTIME_EXCLUDED_DEV_TYPE_IDS:
            logger.info("Fusion Solar: skipping excluded devTypeId=%s for asset=%s", dev_type_id, asset_code)
            continue
        # Chunk by max_devices_per_request if set (9.3)
        chunk_size = max_devices_per_request if max_devices_per_request > 0 else len(devs)
        batches: List[List[Dict]] = (
            [devs[i : i + chunk_size] for i in range(0, len(devs), chunk_size)]
            if chunk_size > 0
            else [devs]
        )
        for batch in batches:
            _rate_limit(last_call, rate_limit)
            dev_ids_list = [
                _normalize_fusion_solar_dev_id(d.get("device_code") or d.get("device_id"))
                for d in batch
            ]
            dev_ids_list = [x for x in dev_ids_list if x]
            dev_ids = ",".join(dev_ids_list)
            if not dev_ids:
                continue
            out, status = get_dev_real_kpi(base_url, token, dev_ids, dev_type_id)
            if _needs_fusion_token_refresh(status, out):
                token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
                if token:
                    out, status = get_dev_real_kpi(base_url, token, dev_ids, dev_type_id)

            if not out or not out.get("success"):
                err_msg = _provider_error_message(out, status, default="getDevRealKpi failed")
                logger.warning(
                    "Fusion Solar getDevRealKpi failed for asset=%s devTypeId=%s: %s",
                    asset_code,
                    dev_type_id,
                    err_msg,
                )
                continue
            data = out.get("data")
            if not data:
                continue
            # API may return list of { devId, data: [ ... ] } or flat list; batch is the devs for this request
            if isinstance(data, list):
                for i, rec in enumerate(data):
                    dev_id_local = batch[i]["device_id"] if i < len(batch) else (batch[0]["device_id"] + f"_{i}")
                    if isinstance(rec, dict) and "devId" in rec:
                        dev_id_local = next(
                            (d["device_id"] for d in batch if (d.get("device_code") or d.get("device_id")) == str(rec.get("devId"))),
                            dev_id_local,
                        )
                    rows = _collect_device_rows(
                        dev_id_local,
                        (
                            [rec.get("dataItemMap")]
                            if isinstance(rec, dict) and isinstance(rec.get("dataItemMap"), dict)
                            else ([rec.get("data")] if isinstance(rec, dict) and isinstance(rec.get("data"), dict) else (rec.get("data") if isinstance(rec, dict) else None))
                        )
                        or ([rec] if isinstance(rec, dict) else [rec]),
                        metric_map_by_type,
                        metric_map_fallback,
                        run_ts,
                        device_type=(batch[i].get("device_type") if i < len(batch) else None),
                        default_tz=asset_tz_default,
                    )
                    insert_rows.extend(rows)
                    # Derived string metrics from inverter payload (pv*_i, pv*_u).
                    if str(dev_type_id).strip() == "1" and isinstance(rec, dict):
                        insert_rows.extend(
                            _collect_string_rows_from_inverter_payload(
                                inverter_payload=rec,
                                string_children_by_inverter=string_children_by_inverter,
                                metric_map_by_type=metric_map_by_type,
                                metric_map_fallback=metric_map_fallback,
                                fallback_ts=run_ts,
                                default_tz=asset_tz_default,
                            )
                        )
            else:
                rows = _collect_device_rows(
                    asset_code,
                    data if isinstance(data, list) else [data],
                    metric_map_by_type,
                    metric_map_fallback,
                    run_ts,
                    default_tz=asset_tz_default,
                )
                insert_rows.extend(rows)

    if not insert_rows:
        logger.info("Fusion Solar: no data rows for asset %s", asset_code)
        all_device_ids = [d["device_id"] for d in devices]
        return {"success": True, "points_written": 0, "asset_code": asset_code, "device_ids_with_no_data": all_device_ids}

    # Align ts to a common grid (nearest interval) - use 5 min for now
    interval_minutes = int(config.get("acquisition_interval_minutes") or 5)
    interval_seconds = interval_minutes * 60

    def _align_ts(dt: datetime) -> datetime:
        epoch = int(dt.timestamp())
        aligned = (epoch // interval_seconds) * interval_seconds
        return datetime.fromtimestamp(aligned, tz=dt_timezone.utc)

    aligned_rows: List[Tuple[str, datetime, str, str, str]] = []
    for r in insert_rows:
        aligned_rows.append((r[0], _align_ts(r[1]), r[2], r[3], r[4]))

    device_ids = list({r[0] for r in aligned_rows})
    start_ts = min(r[1] for r in aligned_rows)
    end_ts = max(r[1] for r in aligned_rows)

    with connection.cursor() as cursor:
        cursor.execute(CREATE_STAGING_TEMP_TABLE_SQL)
        buf = io.StringIO()
        writer = csv.writer(buf)
        for r in aligned_rows:
            writer.writerow([r[0], r[1].isoformat(), r[2], r[3], r[4]])
        buf.seek(0)
        cursor.copy_expert(
            f"""
            COPY {STAGING_TABLE} (device_id, ts, oem_metric, metric, value)
            FROM STDIN WITH (FORMAT csv)
            """,
            buf,
        )
        cursor.execute(f"SELECT COUNT(*) FROM {STAGING_TABLE}")
        if cursor.fetchone()[0] != len(aligned_rows):
            cursor.execute(f"TRUNCATE {STAGING_TABLE}")
            return {"success": False, "error": "Staging row count mismatch", "asset_code": asset_code}

        with transaction.atomic():
            # DELETE range for all affected devices
            for did in device_ids:
                cursor.execute(
                    """
                    DELETE FROM timeseries_data
                    WHERE device_id = %s AND ts >= %s AND ts <= %s
                    """,
                    [did, start_ts, end_ts],
                )
            cursor.execute(
                f"""
                INSERT INTO timeseries_data (device_id, ts, oem_metric, metric, value)
                SELECT device_id, ts, oem_metric, metric, value FROM {STAGING_TABLE}
                """
            )
        cursor.execute(f"TRUNCATE {STAGING_TABLE}")

    device_ids_with_data = {r[0] for r in aligned_rows}
    all_device_ids = {d["device_id"] for d in devices}
    device_ids_with_no_data = list(all_device_ids - device_ids_with_data)
    logger.info(
        "Fusion Solar adapter: asset_code=%s devices=%d points=%d no_data=%d",
        asset_code,
        len(device_ids),
        len(aligned_rows),
        len(device_ids_with_no_data),
    )

    # Phase 8: GHI→GII transposition when asset has tilt_configs and a GHI device (8.1–8.5)
    gii_result = _run_ghi_to_gii_for_asset(asset_code, start_ts, end_ts)
    if gii_result:
        if gii_result.get("success"):
            logger.info(
                "Fusion Solar GHI→GII: asset_code=%s records_written=%s device_ids=%s",
                asset_code,
                gii_result.get("records_written", 0),
                gii_result.get("device_ids_used", []),
            )
            _ensure_gii_devices_in_device_list(asset_code)
        else:
            logger.debug(
                "Fusion Solar GHI→GII skipped or failed for %s: %s",
                asset_code,
                gii_result.get("error", "unknown"),
            )

    return {
        "success": True,
        "points_written": len(aligned_rows),
        "asset_code": asset_code,
        "devices_written": len(device_ids),
        "device_ids_with_no_data": device_ids_with_no_data,
        "gii_records_written": gii_result.get("records_written", 0) if gii_result else 0,
    }


def _fusion_solar_fetch_and_store_historical(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Historical backfill using getDevHistoryKpi in provider-safe chunks.
    """
    from main.models import AssetList, device_list

    base_url = (config.get("api_base_url") or "").strip()
    username = (config.get("username") or "").strip()
    password = (config.get("password") or config.get("system_code") or "").strip()
    if not base_url or not username or not password:
        return {"success": False, "error": "api_base_url, username, and password are required"}

    date_from = (config.get("date_from") or "").strip()
    date_to = (config.get("date_to") or "").strip()
    try:
        from_d = datetime.strptime(date_from, "%Y-%m-%d").date()
        to_d = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError:
        return {"success": False, "error": "date_from/date_to must be YYYY-MM-DD"}
    if from_d > to_d:
        return {"success": False, "error": "date_from cannot be after date_to"}

    asset_tz_default: Optional[dt_timezone] = None
    try:
        asset_for_tz = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
        asset_tz_default = _parse_asset_timezone_offset(getattr(asset_for_tz, "timezone", None)) if asset_for_tz else None
    except Exception:
        asset_tz_default = None

    try:
        devices = list(
            device_list.objects.filter(parent_code=asset_code).values(
                "device_id",
                "device_code",
                "device_type_id",
                "device_type",
            )
        )
    except Exception as e:
        return {"success": False, "error": str(e)}
    if not devices:
        return {"success": True, "points_written": 0, "asset_code": asset_code, "device_ids_with_no_data": []}

    string_children_by_inverter: Dict[str, List[Dict[str, str]]] = {}
    try:
        string_rows = list(
            device_list.objects.filter(parent_code=asset_code, device_type__iexact="string").values(
                "device_id", "device_code", "device_sub_group"
            )
        )
        for s in string_rows:
            subgroup = _normalize_fusion_solar_dev_id(s.get("device_sub_group"))
            if not subgroup:
                continue
            string_children_by_inverter.setdefault(subgroup, []).append(
                {
                    "device_id": str(s.get("device_id") or "").strip(),
                    "device_code": str(s.get("device_code") or "").strip(),
                }
            )
    except Exception:
        string_children_by_inverter = {}

    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return {"success": False, "error": "Fusion Solar login failed"}

    # Provider rule for historical interface: only one concurrent request per minute.
    # Enforce strict pacing regardless of config to avoid failCode=407.
    rate_limit = 1
    # Enforce provider-safe hard limits regardless of config.
    configured_device_limit = int(config.get("history_max_devices_per_request") or DEFAULT_HISTORY_MAX_DEVICES_PER_REQUEST)
    configured_day_limit = int(config.get("history_max_days_per_request") or DEFAULT_HISTORY_MAX_DAYS_PER_REQUEST)
    max_devices_per_request = max(1, min(configured_device_limit, DEFAULT_HISTORY_MAX_DEVICES_PER_REQUEST))
    max_days_per_request = max(1, min(configured_day_limit, DEFAULT_HISTORY_MAX_DAYS_PER_REQUEST))
    last_call: List[float] = []
    metric_map_by_type, metric_map_fallback = _load_fusion_solar_metric_map()
    insert_rows: List[Tuple[str, datetime, str, str, str]] = []
    provider_failures: List[str] = []

    by_type: Dict[str, List[Dict]] = {}
    for d in devices:
        tid = (d.get("device_type_id") or "1").strip() or "1"
        by_type.setdefault(tid, []).append(d)

    cur = from_d
    while cur <= to_d:
        win_end = min(cur + timedelta(days=max_days_per_request - 1), to_d)
        asset_tz = asset_tz_default or dt_timezone.utc
        start_local = datetime(cur.year, cur.month, cur.day, 0, 0, 0, tzinfo=asset_tz)
        end_local = datetime(win_end.year, win_end.month, win_end.day, 23, 59, 59, tzinfo=asset_tz)
        # Provider uses local wall-clock milliseconds for history API boundaries.
        start_ms = int(start_local.replace(tzinfo=dt_timezone.utc).timestamp() * 1000)
        end_ms = int(end_local.replace(tzinfo=dt_timezone.utc).timestamp() * 1000)
        start_dt = start_local.astimezone(dt_timezone.utc)
        end_dt = end_local.astimezone(dt_timezone.utc)

        for dev_type_id, devs in by_type.items():
            dev_type_id = str(dev_type_id).strip()
            if not dev_type_id.isdigit():
                continue
            if dev_type_id not in HISTORICAL_SUPPORTED_DEV_TYPE_IDS:
                continue
            chunk_size = max_devices_per_request if max_devices_per_request > 0 else len(devs)
            batches = [devs[i : i + chunk_size] for i in range(0, len(devs), chunk_size)] if chunk_size > 0 else [devs]
            for batch in batches:
                _rate_limit(last_call, rate_limit)
                dev_ids_list = [_normalize_fusion_solar_dev_id(d.get("device_code") or d.get("device_id")) for d in batch]
                dev_ids = ",".join([x for x in dev_ids_list if x])
                if not dev_ids:
                    continue
                logger.debug(
                    "Fusion Solar historical request asset=%s url=%s devTypeId=%s startTime=%s endTime=%s devIds=%s",
                    asset_code,
                    f"{base_url.rstrip('/')}/thirdData/getDevHistoryKpi",
                    dev_type_id,
                    start_ms,
                    end_ms,
                    dev_ids,
                )
                out, status = get_dev_history_kpi(base_url, token, dev_ids, dev_type_id, start_ms, end_ms)
                if _needs_fusion_token_refresh(status, out):
                    token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
                    if token:
                        out, status = get_dev_history_kpi(base_url, token, dev_ids, dev_type_id, start_ms, end_ms)
                logger.debug(
                    "Fusion Solar historical response asset=%s devTypeId=%s status=%s success=%s data_len=%s failCode=%s message=%s",
                    asset_code,
                    dev_type_id,
                    status,
                    bool(out and out.get("success")),
                    (len(out.get("data")) if isinstance(out, dict) and isinstance(out.get("data"), list) else None),
                    (out.get("failCode") if isinstance(out, dict) else None),
                    (out.get("message") if isinstance(out, dict) else "no response"),
                )
                if not out or not out.get("success"):
                    err_msg = _provider_error_message(out, status, default="getDevHistoryKpi failed")
                    failure_msg = (
                        f"asset={asset_code} devTypeId={dev_type_id} "
                        f"window={cur.isoformat()}..{win_end.isoformat()} "
                        f"devices={len(batch)} error={err_msg}"
                    )
                    provider_failures.append(failure_msg)
                    logger.warning("Fusion Solar historical chunk failed: %s", failure_msg)
                    continue
                data = out.get("data")
                if not isinstance(data, list):
                    failure_msg = (
                        f"asset={asset_code} devTypeId={dev_type_id} "
                        f"window={cur.isoformat()}..{win_end.isoformat()} "
                        f"devices={len(batch)} error=Unexpected response data format"
                    )
                    provider_failures.append(failure_msg)
                    logger.warning("Fusion Solar historical chunk failed: %s", failure_msg)
                    continue
                for i, rec in enumerate(data):
                    dev_id_local = batch[i]["device_id"] if i < len(batch) else (batch[0]["device_id"] + f"_{i}")
                    if isinstance(rec, dict) and "devId" in rec:
                        api_id = _normalize_fusion_solar_dev_id(rec.get("devId"))
                        dev_id_local = next(
                            (
                                d["device_id"]
                                for d in batch
                                if _normalize_fusion_solar_dev_id(d.get("device_code") or d.get("device_id")) == api_id
                            ),
                            dev_id_local,
                        )
                    rows = _collect_device_rows(
                        dev_id_local,
                        (
                            [
                                {
                                    **rec.get("dataItemMap"),
                                    "collectTime": rec.get("collectTime"),
                                    "timestamp": rec.get("timestamp"),
                                }
                            ]
                            if isinstance(rec, dict) and isinstance(rec.get("dataItemMap"), dict)
                            else (
                                rec.get("data")
                                if isinstance(rec, dict) and isinstance(rec.get("data"), list)
                                else ([rec] if isinstance(rec, dict) else [])
                            )
                        ),
                        metric_map_by_type,
                        metric_map_fallback,
                        start_dt,
                        device_type=(batch[i].get("device_type") if i < len(batch) else None),
                        default_tz=asset_tz_default,
                    )
                    insert_rows.extend(rows)
                    if str(dev_type_id).strip() == "1" and isinstance(rec, dict):
                        insert_rows.extend(
                            _collect_string_rows_from_inverter_payload(
                                inverter_payload=rec,
                                string_children_by_inverter=string_children_by_inverter,
                                metric_map_by_type=metric_map_by_type,
                                metric_map_fallback=metric_map_fallback,
                                fallback_ts=start_dt,
                                default_tz=asset_tz_default,
                            )
                        )
        cur = win_end + timedelta(days=1)

    if not insert_rows:
        return {
            "success": True,
            "points_written": 0,
            "asset_code": asset_code,
            "device_ids_with_no_data": [d["device_id"] for d in devices],
            "provider_failures": provider_failures,
        }

    logger.info(
        "Fusion Solar historical write summary asset=%s raw_rows=%s devices=%s ts_start=%s ts_end=%s",
        asset_code,
        len(insert_rows),
        len({r[0] for r in insert_rows}),
        min(r[1] for r in insert_rows).isoformat() if insert_rows else None,
        max(r[1] for r in insert_rows).isoformat() if insert_rows else None,
    )

    with connection.cursor() as cursor:
        cursor.execute(CREATE_STAGING_TEMP_TABLE_SQL)
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
        device_ids = list({r[0] for r in insert_rows})
        start_ts = min(r[1] for r in insert_rows)
        end_ts = max(r[1] for r in insert_rows)
        with transaction.atomic():
            for did in device_ids:
                cursor.execute(
                    """
                    DELETE FROM timeseries_data
                    WHERE device_id = %s AND ts >= %s AND ts <= %s
                    """,
                    [did, start_ts, end_ts],
                )
            cursor.execute(
                f"""
                INSERT INTO timeseries_data (device_id, ts, oem_metric, metric, value)
                SELECT device_id, ts, oem_metric, metric, value FROM {STAGING_TABLE}
                """
            )
        cursor.execute(f"TRUNCATE {STAGING_TABLE}")

    gii_result = _run_ghi_to_gii_for_asset(asset_code, min(r[1] for r in insert_rows), max(r[1] for r in insert_rows))
    if gii_result and gii_result.get("success"):
        _ensure_gii_devices_in_device_list(asset_code)

    return {
        "success": True,
        "points_written": len(insert_rows),
        "asset_code": asset_code,
        "devices_written": len({r[0] for r in insert_rows}),
        "provider_failures": provider_failures,
    }


def fusion_solar_fetch_and_store_batch(
    asset_codes: List[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Fetch Fusion Solar real-time data for multiple assets under one account in batched API calls.

    One login; load all devices for asset_codes; group by devTypeId, call getDevRealKpi in chunks;
    write all to timeseries_data; run GHI→GII per asset that has tilt_configs.
    Reduces API calls when one account serves many assets.
    """
    from main.models import device_list

    if not asset_codes:
        return {"success": True, "points_written": 0, "asset_codes": [], "results": []}

    base_url = (config.get("api_base_url") or "").strip()
    username = (config.get("username") or "").strip()
    password = (config.get("password") or config.get("system_code") or "").strip()
    if not base_url or not username or not password:
        return {"success": False, "error": "api_base_url, username, and password are required", "asset_codes": asset_codes}

    rate_limit = int(config.get("rate_limit_calls_per_minute") or 60)
    configured_device_limit = int(config.get("max_devices_per_request") or DEFAULT_MAX_DEVICES_PER_REQUEST)
    max_devices_per_request = (
        PROVIDER_MAX_DEVICES_PER_REQUEST
        if configured_device_limit <= 0
        else max(1, min(configured_device_limit, PROVIDER_MAX_DEVICES_PER_REQUEST))
    )
    last_call: List[float] = []

    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return {"success": False, "error": "Fusion Solar login failed", "asset_codes": asset_codes}

    try:
        devices = list(
            device_list.objects.filter(parent_code__in=asset_codes).values(
                "device_id",
                "device_code",
                "device_type_id",
                "device_type",
                "parent_code",
            )
        )
    except Exception as e:
        logger.exception("Fusion Solar batch: failed to load device_list for %s", asset_codes)
        return {"success": False, "error": str(e), "asset_codes": asset_codes}

    if not devices:
        logger.info("Fusion Solar batch: no devices for assets %s", asset_codes)
        return {"success": True, "points_written": 0, "asset_codes": asset_codes, "results": []}

    run_ts = timezone.now()
    asset_points: Dict[str, int] = {ac: 0 for ac in asset_codes}
    asset_errors: Dict[str, List[str]] = {ac: [] for ac in asset_codes}
    by_type: Dict[str, List[Dict]] = {}
    for d in devices:
        tid = (d.get("device_type_id") or "1").strip() or "1"
        by_type.setdefault(tid, []).append(d)

    insert_rows: List[Tuple[str, datetime, str, str, str]] = []
    metric_map_by_type, metric_map_fallback = _load_fusion_solar_metric_map()
    chunk_size = max_devices_per_request if max_devices_per_request > 0 else len(devices)
    from main.models import AssetList
    tz_by_asset: Dict[str, Optional[dt_timezone]] = {}
    for a in AssetList.objects.filter(asset_code__in=asset_codes).only("asset_code", "timezone"):
        tz_by_asset[a.asset_code] = _parse_asset_timezone_offset(getattr(a, "timezone", None))

    for dev_type_id, devs in by_type.items():
        dev_type_id = str(dev_type_id).strip()
        # Skip synthetic/non-OEM types (e.g. "gii") - these are handled via transposition per asset
        if not dev_type_id.isdigit():
            logger.debug("Fusion Solar batch: skipping non-numeric devTypeId=%s", dev_type_id)
            continue
        if dev_type_id in REALTIME_EXCLUDED_DEV_TYPE_IDS:
            logger.info("Fusion Solar batch: skipping excluded devTypeId=%s", dev_type_id)
            continue
        batches: List[List[Dict]] = (
            [devs[i : i + chunk_size] for i in range(0, len(devs), chunk_size)]
            if chunk_size > 0
            else [devs]
        )
        for batch in batches:
            _rate_limit(last_call, rate_limit)
            batch_asset_codes = list({str((d.get("parent_code") or "")).strip() for d in batch if d.get("parent_code")})
            dev_ids_list = [
                _normalize_fusion_solar_dev_id(d.get("device_code") or d.get("device_id"))
                for d in batch
            ]
            dev_ids_list = [x for x in dev_ids_list if x]
            dev_ids = ",".join(dev_ids_list)
            if not dev_ids:
                continue
            out, status = get_dev_real_kpi(base_url, token, dev_ids, dev_type_id)
            if _needs_fusion_token_refresh(status, out):
                token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
                if token:
                    out, status = get_dev_real_kpi(base_url, token, dev_ids, dev_type_id)
            if not out or not out.get("success"):
                err_msg = _provider_error_message(out, status, default="getDevRealKpi failed")
                logger.warning(
                    "Fusion Solar batch getDevRealKpi failed devTypeId=%s: %s",
                    dev_type_id,
                    err_msg,
                )
                for ac in batch_asset_codes:
                    if ac in asset_errors:
                        asset_errors[ac].append(
                            f"Provider getDevRealKpi failed for devTypeId={dev_type_id}: {err_msg}"
                        )
                continue
            data = out.get("data")
            if not data:
                for ac in batch_asset_codes:
                    if ac in asset_errors:
                        asset_errors[ac].append(
                            f"Provider returned no data for devTypeId={dev_type_id}"
                        )
                continue
            code_to_device: Dict[str, Dict] = {str(d.get("device_code") or d.get("device_id")): d for d in batch}
            if isinstance(data, list):
                for i, rec in enumerate(data):
                    api_dev_id = str(rec.get("devId", "")) if isinstance(rec, dict) else ""
                    dev_info = code_to_device.get(api_dev_id) if api_dev_id else (batch[i] if i < len(batch) else None)
                    if dev_info:
                        device_id = dev_info.get("device_id") or dev_info.get("device_code") or ""
                    else:
                        device_id = (batch[i]["device_id"] if i < len(batch) else batch[0]["device_id"]) + f"_{i}"
                    rows = _collect_device_rows(
                        device_id,
                        (
                            [rec.get("dataItemMap")]
                            if isinstance(rec, dict) and isinstance(rec.get("dataItemMap"), dict)
                            else ([rec.get("data")] if isinstance(rec, dict) and isinstance(rec.get("data"), dict) else (rec.get("data") if isinstance(rec, dict) else None))
                        )
                        or ([rec] if isinstance(rec, dict) else [rec]),
                        metric_map_by_type,
                        metric_map_fallback,
                        run_ts,
                        device_type=(dev_info.get("device_type") if dev_info else None),
                        default_tz=tz_by_asset.get(((dev_info or {}).get("parent_code") or ""), None),
                    )
                    insert_rows.extend(rows)
                    parent_code = (dev_info or {}).get("parent_code")
                    if parent_code in asset_points:
                        asset_points[parent_code] += len(rows)

    if not insert_rows:
        logger.info("Fusion Solar batch: no data rows for assets %s", asset_codes)
        per_asset_results: List[Dict[str, Any]] = []
        for ac in asset_codes:
            errs = asset_errors.get(ac) or ["Provider returned no data for all requested devices"]
            # De-duplicate while preserving order for a cleaner error message.
            uniq_errs = list(dict.fromkeys(errs))
            per_asset_results.append(
                {
                    "asset_code": ac,
                    "success": False,
                    "points_written": 0,
                    "error": "; ".join(uniq_errs),
                }
            )
        return {
            "success": False,
            "points_written": 0,
            "asset_codes": asset_codes,
            "devices_written": 0,
            "results": per_asset_results,
        }

    interval_minutes = int(config.get("acquisition_interval_minutes") or 5)
    interval_seconds = interval_minutes * 60

    def _align_ts(dt: datetime) -> datetime:
        epoch = int(dt.timestamp())
        aligned = (epoch // interval_seconds) * interval_seconds
        return datetime.fromtimestamp(aligned, tz=dt_timezone.utc)

    aligned_rows: List[Tuple[str, datetime, str, str, str]] = []
    for r in insert_rows:
        aligned_rows.append((r[0], _align_ts(r[1]), r[2], r[3], r[4]))

    device_ids = list({r[0] for r in aligned_rows})
    start_ts = min(r[1] for r in aligned_rows)
    end_ts = max(r[1] for r in aligned_rows)

    with connection.cursor() as cursor:
        cursor.execute(CREATE_STAGING_TEMP_TABLE_SQL)
        buf = io.StringIO()
        writer = csv.writer(buf)
        for r in aligned_rows:
            writer.writerow([r[0], r[1].isoformat(), r[2], r[3], r[4]])
        buf.seek(0)
        cursor.copy_expert(
            f"""
            COPY {STAGING_TABLE} (device_id, ts, oem_metric, metric, value)
            FROM STDIN WITH (FORMAT csv)
            """,
            buf,
        )
        with transaction.atomic():
            for did in device_ids:
                cursor.execute(
                    """
                    DELETE FROM timeseries_data
                    WHERE device_id = %s AND ts >= %s AND ts <= %s
                    """,
                    [did, start_ts, end_ts],
                )
            cursor.execute(
                f"""
                INSERT INTO timeseries_data (device_id, ts, oem_metric, metric, value)
                SELECT device_id, ts, oem_metric, metric, value FROM {STAGING_TABLE}
                """
            )
        cursor.execute(f"TRUNCATE {STAGING_TABLE}")

    for ac in asset_codes:
        gii_result = _run_ghi_to_gii_for_asset(ac, start_ts, end_ts)
        if gii_result and gii_result.get("success"):
            _ensure_gii_devices_in_device_list(ac)

    logger.info(
        "Fusion Solar batch: asset_codes=%s devices=%d points=%d",
        asset_codes,
        len(device_ids),
        len(aligned_rows),
    )
    per_asset_results = []
    for ac in asset_codes:
        pts = int(asset_points.get(ac, 0) or 0)
        errs = list(dict.fromkeys(asset_errors.get(ac) or []))
        if pts > 0:
            item: Dict[str, Any] = {
                "asset_code": ac,
                "success": True,
                "points_written": pts,
            }
            if errs:
                item["warning"] = "; ".join(errs)
            per_asset_results.append(item)
        else:
            per_asset_results.append(
                {
                    "asset_code": ac,
                    "success": False,
                    "points_written": 0,
                    "error": "; ".join(errs) if errs else "Provider returned no data for this asset",
                }
            )
    all_ok = all(bool(r.get("success")) for r in per_asset_results)
    return {
        "success": all_ok,
        "points_written": len(aligned_rows),
        "asset_codes": asset_codes,
        "devices_written": len(device_ids),
        "results": per_asset_results,
    }
