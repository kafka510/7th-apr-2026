"""
Solargis daily ingest schedule: when operational solar data for local DAY-1 is available per region.
Used to filter which assets to run at each Beat schedule time.
"""
import re
from typing import Any, Dict, Optional, Tuple

# Solargis satellite region -> (UTC hour, UTC minute) when daily data is available
# Ref: Solargis "When operational solar data for local DAY-1 is available"
SOLARGIS_REGION_UTC: Dict[str, Tuple[int, int]] = {
    "GOES_WEST": (9, 0),           # 09:00 UTC
    "GOES_EAST": (5, 0),          # 05:00 UTC
    "GOES_EAST_PATAGONIA": (5, 0), # 05:00 UTC
    "METEOSAT_PRIME": (0, 30),    # 00:30 UTC
    "METEOSAT_PRIME_SCANDINAVIA": (0, 30),  # 00:30 UTC
    "METEOSAT_IODC": (19, 0),     # 19:00 UTC
    "HIMAWARI": (16, 0),          # 16:00 UTC
    "IODC_HIMAWARI": (16, 0),     # 16:00 UTC
}

# Default when no region or time set (legacy)
DEFAULT_DAILY_RUN_UTC = (2, 0)  # 02:00 UTC


def _parse_timezone_offset(tz_str: str) -> Optional[int]:
    """
    Parse timezone string to offset in minutes from UTC.
    Examples: "UTC", "+00:00", "+5:30", "+05:30", "-05:00", "+8", "+08" -> minutes.
    Returns None if invalid.
    """
    if not tz_str or not isinstance(tz_str, str):
        return None
    s = tz_str.strip().upper()
    if s in ("UTC", "Z", ""):
        return 0
    # +5:30, +05:30, +8, -05:00
    m = re.match(r"([+-]?)(\d{1,2})(?::(\d{2}))?$", s.replace(" ", ""))
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    hours = int(m.group(2))
    minutes = int(m.group(3) or 0)
    total_minutes = sign * (hours * 60 + minutes)
    if total_minutes < -24 * 60 or total_minutes > 24 * 60:
        return None
    return total_minutes


def _parse_local_time(time_str: str) -> Optional[Tuple[int, int]]:
    """Parse 'HH:MM' or 'HHMM' to (hour, minute). Returns None if invalid."""
    if not time_str or not isinstance(time_str, str):
        return None
    s = time_str.strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        h, m_min = int(m.group(1)), int(m.group(2))
    else:
        m = re.match(r"^(\d{2})(\d{2})$", s)
        if m:
            h, m_min = int(m.group(1)), int(m.group(2))
        else:
            return None
    if 0 <= h <= 23 and 0 <= m_min <= 59:
        return (h, m_min)
    return None


def local_time_timezone_to_utc(
    local_time_str: str,
    timezone_str: str,
) -> Optional[Tuple[int, int]]:
    """
    Convert local time (HH:MM) + timezone to (hour_utc, minute_utc).
    timezone_str: e.g. "UTC", "+05:30", "-05:00", "+8".
    Returns None if inputs are invalid.
    """
    parsed_time = _parse_local_time(local_time_str)
    offset_minutes = _parse_timezone_offset(timezone_str)
    if parsed_time is None or offset_minutes is None:
        return None
    hour, minute = parsed_time
    total_minutes = hour * 60 + minute - offset_minutes
    total_minutes = total_minutes % (24 * 60)
    if total_minutes < 0:
        total_minutes += 24 * 60
    h_utc = total_minutes // 60
    m_utc = total_minutes % 60
    return (h_utc % 24, m_utc)


def get_daily_run_utc(config: Dict[str, Any]) -> Tuple[int, int]:
    """
    Return (hour, minute) UTC when this asset's daily Solargis ingest should run.
    Priority: daily_run_local_time + daily_run_timezone -> daily_run_utc_hour/minute
    -> solargis_region -> default.
    """
    if not config:
        return DEFAULT_DAILY_RUN_UTC
    local_time = config.get("daily_run_local_time")
    tz = config.get("daily_run_timezone")
    if local_time and tz is not None and str(tz).strip():
        result = local_time_timezone_to_utc(str(local_time).strip(), str(tz).strip())
        if result is not None:
            return result
    h = config.get("daily_run_utc_hour")
    m = config.get("daily_run_utc_minute")
    if h is not None and m is not None:
        try:
            return (int(h) % 24, int(m) % 60)
        except (TypeError, ValueError):
            pass
    region = config.get("solargis_region")
    if region and isinstance(region, str):
        key = str(region).strip().upper().replace("-", "_")
        if key in SOLARGIS_REGION_UTC:
            return SOLARGIS_REGION_UTC[key]
    return DEFAULT_DAILY_RUN_UTC


def all_daily_run_times() -> list:
    """All (hour, minute) at which we need to run the daily ingest (for Beat schedule)."""
    times = set(SOLARGIS_REGION_UTC.values())
    times.add(DEFAULT_DAILY_RUN_UTC)
    return sorted(times)
