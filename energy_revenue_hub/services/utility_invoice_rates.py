from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP, localcontext


RATE_COMPARE_SCALE = Decimal("0.0001")


def compute_calculated_unit_rate(
    export_energy_kwh: Decimal | None,
    export_energy_cost: Decimal | None,
) -> str:
    """Calculate export_energy_cost / export_energy_kwh without fixed decimal cap."""
    if export_energy_kwh in (None, Decimal("0")) or export_energy_cost is None:
        return ""
    if export_energy_kwh <= 0:
        return ""
    with localcontext() as ctx:
        # Keep enough precision for business review without imposing a fixed decimal cap.
        ctx.prec = 64
        value = export_energy_cost / export_energy_kwh
    return format(value, "f")


def compute_net_unit_rate(
    export_energy_kwh: Decimal | None,
    export_energy_cost: Decimal | None,
    recurring_charges: Decimal | None,
) -> str:
    """
    Calculate (export_energy_cost - recurring_charges) / export_energy_kwh
    without fixed decimal cap.
    """
    if export_energy_kwh in (None, Decimal("0")):
        return ""
    if export_energy_kwh <= 0:
        return ""
    cost = export_energy_cost if export_energy_cost is not None else Decimal("0")
    rec = recurring_charges if recurring_charges is not None else Decimal("0")
    with localcontext() as ctx:
        ctx.prec = 64
        value = (cost - rec) / export_energy_kwh
    return format(value, "f")


def build_anomaly_flag_json(
    parsed_unit_rate: Decimal | None,
    calculated_unit_rate: str,
) -> str:
    """
    Return JSON string for anomaly flags so future checks can share one field.
    """
    flags: dict[str, bool] = {}
    if parsed_unit_rate is None or not calculated_unit_rate:
        return json.dumps(flags)

    try:
        calc_dec = Decimal(calculated_unit_rate)
    except Exception:
        flags["calculated_unit_rate_invalid"] = True
        return json.dumps(flags)

    exponent = parsed_unit_rate.as_tuple().exponent
    parsed_scale = -exponent if exponent < 0 else 0
    if parsed_scale != 4:
        return json.dumps(flags)

    mismatch = (
        parsed_unit_rate.quantize(RATE_COMPARE_SCALE, rounding=ROUND_HALF_UP)
        != calc_dec.quantize(RATE_COMPARE_SCALE, rounding=ROUND_HALF_UP)
    )
    if mismatch:
        flags["unit_rate_4dp_mismatch"] = True
    return json.dumps(flags)

