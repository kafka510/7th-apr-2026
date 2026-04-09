"""
Write policy: inside solar window → write all; outside → write only when value changed.

Used by 5-min/30-min asset adapters to avoid duplicate idle readings at night.
SolarGIS (daily) does not use this; it writes all fetched data.

Adapters that participate: before writing a reading, call should_write_reading().
If True, write and then call record_written_reading(). If False, skip the DB write
but still return success (acquisition ran, we chose not to store).
"""
import logging
from datetime import datetime
from typing import Any, Optional, Tuple

from django.utils import timezone

from data_collection.services.solar_window import is_asset_inside_solar_window

logger = logging.getLogger(__name__)


def get_last_written(
    asset_code: str,
    adapter_id: str,
    series_key: str = "default",
    interval_minutes: int = 5,
) -> Optional[Tuple[str, datetime]]:
    """
    Return (value, ts) of the last written reading for this series, or None.
    """
    from data_collection.models import LastWrittenReading

    try:
        row = LastWrittenReading.objects.get(
            asset_code=asset_code,
            adapter_id=adapter_id,
            series_key=series_key,
            interval_minutes=interval_minutes,
        )
        return (row.value, row.ts)
    except LastWrittenReading.DoesNotExist:
        return None


def record_written_reading(
    asset_code: str,
    adapter_id: str,
    value: str,
    ts: datetime,
    series_key: str = "default",
    interval_minutes: int = 5,
) -> None:
    """
    Record that a reading was written. Call after a successful DB write.
    value will be stored as string (max 512 chars) for comparison.
    """
    from data_collection.models import LastWrittenReading

    if not isinstance(value, str):
        value = str(value)
    if len(value) > 512:
        value = value[:512]
    if ts.tzinfo is None:
        ts = timezone.make_aware(ts, timezone.utc)
    LastWrittenReading.objects.update_or_create(
        asset_code=asset_code,
        adapter_id=adapter_id,
        series_key=series_key,
        interval_minutes=interval_minutes,
        defaults={"value": value, "ts": ts},
    )


def should_write_reading(
    asset_code: str,
    adapter_id: str,
    current_value: Any,
    interval_minutes: int = 5,
    series_key: str = "default",
    now: Optional[datetime] = None,
) -> Tuple[bool, str]:
    """
    Whether to write this reading under the solar-window write policy.

    - Inside solar window (day): always write → (True, "inside_solar_window").
    - Outside solar window (night): write only if value changed or no previous reading
      → (True, "outside_value_changed" | "outside_first_reading") or
      → (False, "outside_unchanged").

    Adapters that do not use write policy (e.g. Solargis daily) should not call this.

    Returns:
        (should_write: bool, reason: str)
    """
    now = now or timezone.now()
    if now.tzinfo is None:
        now = timezone.make_aware(now, timezone.utc)

    if is_asset_inside_solar_window(asset_code, now=now):
        return (True, "inside_solar_window")

    current_str = str(current_value)
    if len(current_str) > 512:
        current_str = current_str[:512]

    last = get_last_written(
        asset_code=asset_code,
        adapter_id=adapter_id,
        series_key=series_key,
        interval_minutes=interval_minutes,
    )
    if last is None:
        return (True, "outside_first_reading")
    last_value, _ = last
    if last_value != current_str:
        return (True, "outside_value_changed")
    return (False, "outside_unchanged")
