"""
Deprecated: run-level sun-hours gate was removed. Acquisition runs 24/7.

This module is kept for backward compatibility. should_run_acquisition() and
is_within_sun_hours() always return True so any legacy caller does not gate runs.

For per-asset solar window (e.g. write policy when adding adapters), use
data_collection.services.solar_window instead:
  - is_asset_inside_solar_window(asset_code, now)
  - get_solar_window_bounds(...)

See docs/DATA_ACQUISITION_SUN_HOURS_PLAN.md.
"""
from datetime import time
from typing import Optional

from django.utils import timezone

# Kept for backward compatibility; no longer used for run gating.
DEFAULT_SUNRISE = time(6, 0, 0)
DEFAULT_SUNSET = time(18, 0, 0)


def is_within_sun_hours(
    now: Optional[timezone.datetime] = None,
    sunrise: Optional[time] = None,
    sunset: Optional[time] = None,
) -> bool:
    """
    Deprecated. Always returns True. Run gating was removed; acquisition runs 24/7.
    Use data_collection.services.solar_window for per-asset solar window.
    """
    return True


def should_run_acquisition(now: Optional[timezone.datetime] = None) -> bool:
    """
    Deprecated. Always returns True. Run-level sun-hours gate was removed.
    Use data_collection.services.solar_window for per-asset logic.
    """
    return True
