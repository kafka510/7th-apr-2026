"""
Resolve weather data (irradiance, temperature, wind) and apply defaults from
loss_analytics.defaults when sensor data is missing.
"""
from typing import Dict, Optional, Any

from loss_analytics import defaults as loss_defaults


def get_weather_with_defaults(
    asset_code: str,
    timestamp,
    weather_device_config: Optional[Dict[str, Any]] = None,
    tolerance_minutes: int = 15,
) -> Dict[str, Optional[float]]:
    """
    Get weather data (irradiance, temperature, wind) for the asset at the given
    timestamp. When temperature or wind is missing, apply defaults from
    loss_analytics.defaults.

    Returns dict with keys: irradiance, temperature, module_temp, ambient_temp, wind_speed.
    """
    from loss_analytics.calculations import TimeseriesReader

    reader = TimeseriesReader()
    result = reader.get_weather_data(
        asset_code=asset_code,
        timestamp=timestamp,
        tolerance_minutes=tolerance_minutes,
        weather_device_config=weather_device_config,
    )

    # Apply defaults when missing
    if result.get("ambient_temp") is None and result.get("module_temp") is None and result.get("temperature") is None:
        result["ambient_temp"] = loss_defaults.get_default_ambient_temp_c()
        result["temperature"] = result["ambient_temp"]
    if result.get("wind_speed") is None:
        result["wind_speed"] = loss_defaults.get_default_wind_speed_ms()

    return result
