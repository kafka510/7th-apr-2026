"""
Solar leasing year, period splitting, and MRE (rooftop self-consumption) escalation for sg_ppa_maiora.

See docs/SG_PPA_MAIORA_INVOICE_PLAN.md §3.2.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple

from dateutil.relativedelta import relativedelta

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from main.models import assets_contracts


def inclusive_days(start: date, end: date) -> int:
    if start > end:
        return 0
    return (end - start).days + 1


def leasing_year_index(cod: date, on_date: date) -> int:
    """1-based solar leasing year: year 1 is [cod, cod+1y)."""
    if on_date < cod:
        return 1
    y = 1
    upper = cod + relativedelta(years=1)
    while on_date >= upper:
        y += 1
        upper = upper + relativedelta(years=1)
    return y


def split_period_by_anniversaries(cod: date, period_start: date, period_end: date) -> List[Tuple[date, date]]:
    """
    Split [period_start, period_end] at each leasing anniversary (COD month/day) that falls inside the period.
    """
    if period_start > period_end:
        return []
    splits = [period_start]
    ann = date(cod.year, cod.month, cod.day)
    while ann < period_start:
        ann = ann + relativedelta(years=1)
    while ann <= period_end:
        if ann > period_start:
            splits.append(ann)
        ann = ann + relativedelta(years=1)
    splits = sorted(set(splits))
    out: List[Tuple[date, date]] = []
    for i in range(len(splits)):
        seg_start = splits[i]
        if i + 1 < len(splits):
            seg_end = splits[i + 1] - timedelta(days=1)
        else:
            seg_end = period_end
        seg_end = min(seg_end, period_end)
        if seg_start <= seg_end:
            out.append((seg_start, seg_end))
    return out


def _truthy_escalation(raw: str | None) -> bool:
    s = (raw or "").strip().lower()
    return s in ("yes", "true", "1", "y")


def _escalation_type_key(raw: str | None) -> str:
    s = normalize_contract_type_key(raw or "")
    if s in ("multiplicative", "multiplication"):
        return "multiplicative"
    if s in ("additive", "addition"):
        return "additive"
    return s or ""


def compute_mre_rate(contract: assets_contracts, leasing_year_y: int) -> Decimal | None:
    """
    MRE rate from rooftop_self_consumption_rate (sc_rate) and escalation fields.
    Y = leasing_year_y (1-based).
    """
    sc = getattr(contract, "rooftop_self_consumption_rate", None)
    if sc is None:
        return None
    sc_rate = Decimal(str(sc))
    if not _truthy_escalation(getattr(contract, "escalation_condition", None)):
        return sc_rate

    et = _escalation_type_key(getattr(contract, "escalation_type", None))
    grace = int(getattr(contract, "escalation_grace_years", None) or 0)
    period = int(getattr(contract, "escalation_period", None) or 0)
    er = getattr(contract, "escalation_rate", None)
    if er is None or period <= 0:
        return sc_rate
    esc_rate = Decimal(str(er))

    steps = max(0, leasing_year_y - grace) // period
    if et == "multiplicative":
        base = Decimal("1") + esc_rate
        return (sc_rate * (base**steps)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if et == "additive":
        return (sc_rate + esc_rate * Decimal(steps)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return sc_rate
