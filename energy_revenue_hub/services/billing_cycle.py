"""
Billing-cycle helpers for ERH (uses ``assets_contracts.contract_billing_cycle_end_day``).
"""

from __future__ import annotations

import calendar
from datetime import date

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from main.models import assets_contracts


def billing_month_first_day(billing_month: date | None) -> date | None:
    if billing_month is None:
        return None
    return date(billing_month.year, billing_month.month, 1)


def contract_billing_cycle_end_date(billing_month_first: date, end_day: int | None) -> date:
    """
    Calendar end date of the contract billing cycle within ``billing_month_first``'s month.

    If ``end_day`` is missing, uses the last calendar day of that month.
    """
    y, m = billing_month_first.year, billing_month_first.month
    _, last = calendar.monthrange(y, m)
    if end_day is None:
        return date(y, m, last)
    try:
        d = int(end_day)
    except (TypeError, ValueError):
        return date(y, m, last)
    d = max(1, min(d, last))
    return date(y, m, d)


def contract_row_for_asset(asset_code: str, session_contract_type: str) -> assets_contracts | None:
    """Pick the ``assets_contracts`` row for this asset, preferring a contract_type match."""
    code = (asset_code or "").strip()
    if not code:
        return None
    qs = list(assets_contracts.objects.filter(asset_code=code))
    if not qs:
        return None
    nk = normalize_contract_type_key(session_contract_type)
    if nk:
        for row in qs:
            if normalize_contract_type_key(getattr(row, "contract_type", None)) == nk:
                return row
    return qs[0]


def billing_cycle_still_open(
    *,
    billing_month_first: date | None,
    contract_end_day: int | None,
    as_of: date,
) -> bool:
    """
    True when ``as_of`` is strictly before the computed cycle end date for the billing month.

    Used to warn when invoicing before the configured billing cycle has closed.
    """
    bm = billing_month_first_day(billing_month_first)
    if bm is None:
        return False
    cycle_end = contract_billing_cycle_end_date(bm, contract_end_day)
    return as_of < cycle_end


def warning_message_for_line(
    *,
    asset_code: str,
    session_contract_type: str,
    billing_month_first: date | None,
    as_of: date,
) -> str:
    row = contract_row_for_asset(asset_code, session_contract_type)
    if row is None:
        return ""
    end_day = getattr(row, "contract_billing_cycle_end_day", None)
    if billing_cycle_still_open(
        billing_month_first=billing_month_first,
        contract_end_day=end_day,
        as_of=as_of,
    ):
        bm = billing_month_first_day(billing_month_first)
        if bm is None:
            return ""
        cend = contract_billing_cycle_end_date(bm, end_day)
        return (
            f"Billing cycle end ({cend.isoformat()}) is after today ({as_of.isoformat()}); "
            "invoice may be premature."
        )
    return ""


def contract_covers_billing_month(contract: assets_contracts, billing_month_first: date) -> bool:
    """Whether the contract date range overlaps the calendar month of ``billing_month_first``."""
    _, last = calendar.monthrange(billing_month_first.year, billing_month_first.month)
    month_start = date(billing_month_first.year, billing_month_first.month, 1)
    month_end = date(billing_month_first.year, billing_month_first.month, last)
    start = getattr(contract, "contract_start_date", None)
    end = getattr(contract, "contract_end_date", None)
    if start and start > month_end:
        return False
    if end and end < month_start:
        return False
    return True
