"""
Centralized KPI aggregation for billing: device-day energy then asset totals.

Rule per device-day: use ``daily_max_min`` when > 0; otherwise ``oem_daily_product_kwh``; else 0.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from main.models import device_list, kpis


def daily_kwh_from_kpi_row(row: Any) -> Decimal:
    """Prefer ``daily_max_min`` when positive; else OEM-reported energy; else zero."""
    dmm = getattr(row, "daily_max_min", None)
    if dmm is not None:
        v = Decimal(str(dmm))
        if v > 0:
            return v
    oem = getattr(row, "oem_daily_product_kwh", None)
    if oem is not None:
        return Decimal(str(oem))
    return Decimal("0")


def aggregate_asset_kwh(asset_code: str, date_from: date, date_to: date) -> Decimal:
    """
    Sum kWh for all devices under ``asset_code`` (``device_list.parent_code``) over
    ``day_date`` in [date_from, date_to] inclusive.
    """
    device_ids = list(
        device_list.objects.filter(parent_code=asset_code).values_list("device_id", flat=True)
    )
    if not device_ids:
        return Decimal("0")
    total = Decimal("0")
    qs = kpis.objects.filter(
        device_id__in=device_ids,
        day_date__gte=date_from,
        day_date__lte=date_to,
    )
    for row in qs.iterator():
        total += daily_kwh_from_kpi_row(row)
    return total
