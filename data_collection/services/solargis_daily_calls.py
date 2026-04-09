"""
Solargis daily API call count using data_collection_last_written_reading.

We reuse LastWrittenReading with a sentinel row per day so the count is
persistent and shared across all workers (no cache backend required).
Sentinel: asset_code="_daily", adapter_id="solargis", series_key="api_calls_YYYY-MM-DD", interval_minutes=0.
"""
from datetime import date
from typing import Optional

from django.utils import timezone

# Sentinel key for "daily API calls" in LastWrittenReading
SOLARGIS_DAILY_ASSET = "_daily"
SOLARGIS_DAILY_ADAPTER = "solargis"
SOLARGIS_DAILY_INTERVAL = 0


def _series_key_for_date(d: date) -> str:
    return f"api_calls_{d.isoformat()}"


def get_solargis_daily_api_calls(for_date: Optional[date] = None) -> int:
    """Return total Solargis API calls for the given date (default: today)."""
    from data_collection.models import LastWrittenReading

    for_date = for_date or timezone.now().date()
    series_key = _series_key_for_date(for_date)
    try:
        row = LastWrittenReading.objects.get(
            asset_code=SOLARGIS_DAILY_ASSET,
            adapter_id=SOLARGIS_DAILY_ADAPTER,
            series_key=series_key,
            interval_minutes=SOLARGIS_DAILY_INTERVAL,
        )
        return int(row.value) if row.value.isdigit() else 0
    except (LastWrittenReading.DoesNotExist, ValueError):
        return 0


def increment_solargis_daily_api_calls(for_date: Optional[date] = None) -> None:
    """Increment by 1 the Solargis API call count for the given date (default: today)."""
    from data_collection.models import LastWrittenReading

    for_date = for_date or timezone.now().date()
    series_key = _series_key_for_date(for_date)
    now = timezone.now()
    try:
        row = LastWrittenReading.objects.get(
            asset_code=SOLARGIS_DAILY_ASSET,
            adapter_id=SOLARGIS_DAILY_ADAPTER,
            series_key=series_key,
            interval_minutes=SOLARGIS_DAILY_INTERVAL,
        )
        count = int(row.value) + 1 if row.value.isdigit() else 1
        row.value = str(count)
        row.ts = now
        row.save(update_fields=["value", "ts", "updated_at"])
    except LastWrittenReading.DoesNotExist:
        LastWrittenReading.objects.create(
            asset_code=SOLARGIS_DAILY_ASSET,
            adapter_id=SOLARGIS_DAILY_ADAPTER,
            series_key=series_key,
            interval_minutes=SOLARGIS_DAILY_INTERVAL,
            value="1",
            ts=now,
        )
    except ValueError:
        LastWrittenReading.objects.update_or_create(
            asset_code=SOLARGIS_DAILY_ASSET,
            adapter_id=SOLARGIS_DAILY_ADAPTER,
            series_key=series_key,
            interval_minutes=SOLARGIS_DAILY_INTERVAL,
            defaults={"value": "1", "ts": now},
        )
