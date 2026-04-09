"""
Default values for loss analytics pipeline.

Single source of truth for defaults when sensor data (temperature, wind, etc.)
is missing. Pipeline code (e.g. weather_resolver) reads from here.
Override via Django settings or a DB model in a later phase if needed.
"""

# Temperature (°C) when no ambient or module temperature sensor is available
DEFAULT_AMBIENT_TEMP_C = 25.0

# Wind speed (m/s) when no wind sensor is available (e.g. for Faiman cell temperature)
DEFAULT_WIND_SPEED_MS = 2.0

# Default albedo (0–1) for transposition when asset.albedo is not set
DEFAULT_ALBEDO = 0.2

# Default altitude (m) for transposition when asset.altitude_m is not set
DEFAULT_ALTITUDE_M = 0.0

# Module temperature: when only ambient is available, models derive cell temp
# (e.g. Faiman). When neither module nor ambient is available, use default ambient
# and default wind for derivation (already covered by the two defaults above).


def get_default_ambient_temp_c():
    """Return default ambient temperature in °C (for use when sensor missing)."""
    try:
        from django.conf import settings
        return getattr(settings, "LOSS_ANALYTICS_DEFAULT_AMBIENT_TEMP_C", DEFAULT_AMBIENT_TEMP_C)
    except Exception:
        return DEFAULT_AMBIENT_TEMP_C


def get_default_wind_speed_ms():
    """Return default wind speed in m/s (for use when sensor missing)."""
    try:
        from django.conf import settings
        return getattr(settings, "LOSS_ANALYTICS_DEFAULT_WIND_SPEED_MS", DEFAULT_WIND_SPEED_MS)
    except Exception:
        return DEFAULT_WIND_SPEED_MS


def get_default_albedo():
    """Return default ground albedo for transposition."""
    try:
        from django.conf import settings
        return getattr(settings, "LOSS_ANALYTICS_DEFAULT_ALBEDO", DEFAULT_ALBEDO)
    except Exception:
        return DEFAULT_ALBEDO


def get_default_altitude_m():
    """Return default altitude in m for transposition."""
    try:
        from django.conf import settings
        return getattr(settings, "LOSS_ANALYTICS_DEFAULT_ALTITUDE_M", DEFAULT_ALTITUDE_M)
    except Exception:
        return DEFAULT_ALTITUDE_M
