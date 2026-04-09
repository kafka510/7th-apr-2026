from typing import Dict

from .validators import ValidationError, validate_energy_positive


def compute_ac_capacity_mw(dc_capacity_mwp: float, dc_ac_ratio: float) -> float:
    return round(dc_capacity_mwp / dc_ac_ratio, 2)


def compute_annual_energy_mwh(
    dc_capacity_mwp: float,
    reference_yield_kwh_kwp: float,
    total_loss_percent: float,
    inverter_efficiency_percent: float,
    soil_loss_percent: float = 0.0,
    temperature_loss_percent: float = 0.0,
    irradiance_loss_percent: float = 0.0,
    dc_loss_percent: float = 0.0,
    ac_loss_percent: float = 0.0,
) -> float:
    """Compute annual energy with CSV total_loss plus user-specified losses."""
    user_loss_total = (
        soil_loss_percent
        + temperature_loss_percent
        + irradiance_loss_percent
        + dc_loss_percent
        + ac_loss_percent
    )
    effective_loss = min(100.0, total_loss_percent + user_loss_total)
    dc_kwp = dc_capacity_mwp * 1000.0
    energy_kwh = (
        dc_kwp
        * reference_yield_kwh_kwp
        * (1.0 - effective_loss / 100.0)
        * (inverter_efficiency_percent / 100.0)
    )
    return round(energy_kwh / 1000.0, 2)


def compute_specific_yield_kwh_kwp(
    annual_energy_mwh: float, dc_capacity_mwp: float
) -> float:
    if dc_capacity_mwp <= 0:
        return 0.0
    return round(
        (annual_energy_mwh * 1000.0) / (dc_capacity_mwp * 1000.0),
        2,
    )


def compute_cuf_percent(annual_energy_mwh: float, ac_capacity_mw: float) -> float:
    if ac_capacity_mw <= 0:
        return 0.0
    return round(
        (annual_energy_mwh / (ac_capacity_mw * 8760.0)) * 100.0,
        2,
    )


def compute_pr_percent(
    annual_energy_mwh: float,
    dc_capacity_mwp: float,
    reference_yield_kwh_kwp: float,
    pr_percent_from_csv: float | None,
) -> float:
    if pr_percent_from_csv is not None and 0 < pr_percent_from_csv <= 100:
        return round(pr_percent_from_csv, 2)
    theoretical_mwh = (dc_capacity_mwp * 1000.0 * reference_yield_kwh_kwp) / 1000.0
    if theoretical_mwh <= 0:
        return 0.0
    return round((annual_energy_mwh / theoretical_mwh) * 100.0, 2)


def compute_all_kpis(
    dc_capacity_mwp: float,
    solargis_data: Dict[str, float],
    dc_ac_ratio: float,
    inverter_efficiency_percent: float,
    inverter_capacity_kw: float = 0.0,
    soil_loss_percent: float = 0.0,
    temperature_loss_percent: float = 0.0,
    irradiance_loss_percent: float = 0.0,
    dc_loss_percent: float = 0.0,
    ac_loss_percent: float = 0.0,
) -> Dict[str, float]:
    ac_capacity_mw = compute_ac_capacity_mw(dc_capacity_mwp, dc_ac_ratio)

    annual_energy_mwh = compute_annual_energy_mwh(
        dc_capacity_mwp,
        solargis_data["reference_yield_kwh_kwp"],
        solargis_data["total_loss_percent"],
        inverter_efficiency_percent,
        soil_loss_percent,
        temperature_loss_percent,
        irradiance_loss_percent,
        dc_loss_percent,
        ac_loss_percent,
    )
    validate_energy_positive(annual_energy_mwh)

    specific_yield_kwh_kwp = compute_specific_yield_kwh_kwp(
        annual_energy_mwh, dc_capacity_mwp
    )
    cuf_percent = compute_cuf_percent(annual_energy_mwh, ac_capacity_mw)
    pr_percent = compute_pr_percent(
        annual_energy_mwh,
        dc_capacity_mwp,
        solargis_data["reference_yield_kwh_kwp"],
        solargis_data.get("pr_percent_from_csv"),
    )

    return {
        "dc_capacity_mwp": round(dc_capacity_mwp, 2),
        "ac_capacity_mw": ac_capacity_mw,
        "annual_energy_mwh": annual_energy_mwh,
        "specific_yield_kwh_kwp": specific_yield_kwh_kwp,
        "pr_percent": pr_percent,
        "cuf_percent": cuf_percent,
    }
