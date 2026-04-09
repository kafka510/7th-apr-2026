"""
Per-asset solar window: whether a given time (UTC) falls inside the asset's
"sun up" window in asset local time, for use by write policy when asset adapters
are added later.

Window definition: [sunrise - 1.5h, sunset + 1.5h] in asset local time, with
sunrise/sunset computed from asset latitude, longitude, and date (seasonal).

Uses a simple astronomical formula (no pvlib/ephem). AssetList provides
latitude, longitude, and timezone (offset e.g. "+05:30").
"""
import logging
import math
import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from django.utils import timezone

logger = logging.getLogger(__name__)

# Buffer (hours) before sunrise and after sunset
SUNRISE_BUFFER_HOURS = 1.5
SUNSET_BUFFER_HOURS = 1.5

# Extra buffer (hours) after sunset before considering "night" for scheduled expected power
# (run expected power for the day only after sunset + this buffer)
NIGHT_WINDOW_SUNSET_BUFFER_HOURS = 1.5


def _parse_timezone_offset_minutes(tz_str: Optional[str]) -> Optional[int]:
    """
    Parse timezone string to offset in minutes from UTC.
    Supports: "+05:30", "-08:00", "UTC", "+00:00".
    Returns None if invalid or missing.
    """
    if not tz_str or not isinstance(tz_str, str):
        return None
    s = tz_str.strip().upper()
    if s in ("UTC", "Z", ""):
        return 0
    # +05:30, -08:00 (AssetList validator: [+-](0[0-9]|1[0-2]):[0-5][0-9])
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


def _day_of_year(d: date) -> int:
    """Return day of year 1-366."""
    return (d - date(d.year, 1, 1)).days + 1


def _solar_declination_rad(day_of_year: int) -> float:
    """Approximate solar declination in radians (simplified formula)."""
    # δ ≈ 23.44° * sin(360/365 * (284 + n))
    deg = 23.44 * math.sin(math.radians(360.0 / 365.0 * (284 + day_of_year)))
    return math.radians(deg)


def _hour_angle_sunrise_sunset_rad(lat_rad: float, decl_rad: float) -> Optional[float]:
    """
    Hour angle (radians) at geometric sunrise/sunset.
    cos(ω) = -tan(φ)*tan(δ). Returns None if no sunrise/sunset (polar day/night).
    """
    cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)
    if cos_omega <= -1:
        return None  # polar night
    if cos_omega >= 1:
        return None  # polar day
    return math.acos(cos_omega)


def get_sunrise_sunset_hours_local(
    latitude: float,
    longitude: float,
    d: date,
) -> Optional[Tuple[float, float]]:
    """
    Compute sunrise and sunset as local solar time (hours 0-24) for the given
    date at the given latitude/longitude. Uses geometric sunrise/sunset
    (no atmospheric refraction).

    Returns (sunrise_hour, sunset_hour) or None if no sunrise/sunset (polar).
    Longitude is used only if we add equation-of-time / solar noon correction;
    for simplicity we use 12 as solar noon here.
    """
    try:
        lat_rad = math.radians(float(latitude))
    except (TypeError, ValueError):
        return None
    n = _day_of_year(d)
    decl_rad = _solar_declination_rad(n)
    omega_rad = _hour_angle_sunrise_sunset_rad(lat_rad, decl_rad)
    if omega_rad is None:
        return None
    # Half-day length in hours (solar time)
    half_day_hours = math.degrees(omega_rad) / 15.0
    sunrise_hour = 12.0 - half_day_hours
    sunset_hour = 12.0 + half_day_hours
    return (sunrise_hour, sunset_hour)


def is_time_in_solar_window(
    local_hour: float,
    sunrise_hour: float,
    sunset_hour: float,
    sunrise_buffer_hours: float = SUNRISE_BUFFER_HOURS,
    sunset_buffer_hours: float = SUNSET_BUFFER_HOURS,
) -> bool:
    """
    Return True if local_hour (0-24) is inside [sunrise - buffer, sunset + buffer].
    Handles overnight window (e.g. polar) by checking window_start > window_end.
    """
    window_start = sunrise_hour - sunrise_buffer_hours
    window_end = sunset_hour + sunset_buffer_hours
    if window_start <= window_end:
        return window_start <= local_hour <= window_end
    return local_hour >= window_start or local_hour <= window_end


def utc_to_local_hour(utc_dt: datetime, timezone_offset_minutes: int) -> float:
    """Convert UTC datetime to local time and return hour of day as float (0-24)."""
    local = utc_dt + timedelta(minutes=timezone_offset_minutes)
    return local.hour + local.minute / 60.0 + local.second / 3600.0


def is_asset_inside_solar_window(
    asset_code: str,
    now: Optional[datetime] = None,
) -> bool:
    """
    Return True if the given time (UTC) falls inside the asset's solar window
    in asset local time. Uses AssetList for latitude, longitude, timezone.

    Window: [sunrise - 1.5h, sunset + 1.5h] in asset local time.
    If asset is missing or lat/lon/timezone invalid, returns True (allow write by default).
    """
    from main.models import AssetList

    now = now or timezone.now()
    if not now.tzinfo:
        now = timezone.make_aware(now, timezone.utc)

    try:
        asset = AssetList.objects.get(asset_code=asset_code)
    except AssetList.DoesNotExist:
        logger.warning("solar_window: asset %s not found, assuming inside window", asset_code)
        return True

    tz_offset = _parse_timezone_offset_minutes(getattr(asset, "timezone", None))
    if tz_offset is None:
        logger.warning("solar_window: asset %s has invalid timezone, assuming inside window", asset_code)
        return True

    try:
        lat = float(asset.latitude)
        lon = float(asset.longitude)
    except (TypeError, ValueError):
        logger.warning("solar_window: asset %s has invalid lat/lon, assuming inside window", asset_code)
        return True

    # Asset's local date and hour from now (UTC)
    local_dt = now + timedelta(minutes=tz_offset)
    local_date = local_dt.date()
    local_hour = utc_to_local_hour(now, tz_offset)

    sunrise_sunset = get_sunrise_sunset_hours_local(lat, lon, local_date)
    if sunrise_sunset is None:
        # Polar day or night: treat as inside window to be safe
        return True

    sunrise_hour, sunset_hour = sunrise_sunset
    return is_time_in_solar_window(local_hour, sunrise_hour, sunset_hour)


def get_solar_window_bounds(
    latitude: float,
    longitude: float,
    d: date,
    timezone_offset_minutes: int = 0,
) -> Optional[Tuple[float, float]]:
    """
    Return (window_start_hour, window_end_hour) in local time (0-24) for the given
    date, or None if no sunrise/sunset. Includes 1.5h buffer.
    Useful for adapters that need the bounds.
    """
    sr_ss = get_sunrise_sunset_hours_local(latitude, longitude, d)
    if sr_ss is None:
        return None
    sunrise_hour, sunset_hour = sr_ss
    start = sunrise_hour - SUNRISE_BUFFER_HOURS
    end = sunset_hour + SUNSET_BUFFER_HOURS
    return (start, end)


def is_asset_after_sunset(
    asset_code: str,
    now: Optional[datetime] = None,
    sunset_buffer_hours: float = NIGHT_WINDOW_SUNSET_BUFFER_HOURS,
) -> Optional[Tuple[bool, date]]:
    """
    Determine if the given time (UTC) is after sunset for the asset's current local date,
    using asset latitude, longitude, and timezone from AssetList.

    Used to decide when to run expected power for "the day that just ended" (after sun down).
    Returns (True, local_date) when current local time >= sunset + buffer for that local date;
    otherwise (False, local_date). local_date is the asset's local calendar date at `now`.
    Returns None if asset not found or lat/lon/timezone invalid.
    """
    from main.models import AssetList

    now = now or timezone.now()
    if not now.tzinfo:
        now = timezone.make_aware(now, timezone.utc)

    try:
        asset = AssetList.objects.get(asset_code=asset_code)
    except AssetList.DoesNotExist:
        logger.warning("solar_window: is_asset_after_sunset asset %s not found", asset_code)
        return None

    tz_offset = _parse_timezone_offset_minutes(getattr(asset, "timezone", None))
    if tz_offset is None:
        logger.warning("solar_window: asset %s has invalid timezone", asset_code)
        return None

    try:
        lat = float(asset.latitude)
        lon = float(asset.longitude)
    except (TypeError, ValueError):
        logger.warning("solar_window: asset %s has invalid lat/lon", asset_code)
        return None

    local_dt = now + timedelta(minutes=tz_offset)
    local_date = local_dt.date()
    local_hour = utc_to_local_hour(now, tz_offset)

    sunrise_sunset = get_sunrise_sunset_hours_local(lat, lon, local_date)
    if sunrise_sunset is None:
        # Polar day: no sunset → not "after sunset". Polar night: no sunrise → treat as night.
        # For polar night we have no sunrise/sunset; cos_omega <= -1 means polar night.
        # For simplicity, if no sunrise/sunset we return (False, local_date) to avoid running.
        return (False, local_date)

    _sunrise_hour, sunset_hour = sunrise_sunset
    night_start_hour = sunset_hour + sunset_buffer_hours
    # Normalize to 0-24 (sunset is always before midnight for mid-latitudes)
    if night_start_hour >= 24:
        night_start_hour -= 24
    after_sunset = local_hour >= night_start_hour
    return (after_sunset, local_date)
