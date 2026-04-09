"""
Manual DC Mode yield engine — no KMZ/layout.
Formulas from JP_Project Name_Pre-Feasibility Yield Tool_V0 1.xlsm (Summary of Simulation sheet).
- POA: H74 = C74*((1-Albedo)*beam_geom + Albedo*(1+cos(Tilt))/2 + E74*(1-cos(Tilt))/2)
- Energy: I74 = ((H74*B50*(B18/100))*(B26/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86))*(1+B55)*(1+B56)/1000
- B56 (temp): IF lat<=20 then (B21/100)*(D86+46-25) else (B21/100)*((D86+C86*0.032)-25) [annual avg temp, annual total GHI]
"""
import logging
import math
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class MonthlySolarData:
    """One month: GHI (kWh/m²), diffuse (fraction 0-1 or kWh/m²), temperature (°C)."""
    month: str
    ghi: float
    diffuse: float
    temperature: float


@dataclass
class ManualDCInput:
    """Inputs for Manual DC yield calculation (no layout)."""
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    albedo: float
    dc_capacity_kwp: float
    performance_ratio: float
    inverter_efficiency: float
    temp_coefficient: float
    mismatch_loss: float
    wiring_loss: float
    soiling_loss: float
    snow_loss: float
    degradation: float
    additional_loss: float
    monthly_data: List[MonthlySolarData]
    # Optional: for Summary Output (Excel B48–B65)
    module_wp: float = 0.0
    module_length_m: float = 0.0
    module_width_m: float = 0.0
    modules_in_series: int = 0
    inverter_capacity_kw: float = 0.0
    gcr_default_pct: float = 58.78
    shadow_loss_pct: float = 0.0
    bifacial_gain_pct: float = 0.0


@dataclass
class ManualDCOutput:
    """Output of Manual DC yield calculation (Excel Summary of Simulation)."""
    monthly_energy_mwh: List[float]
    annual_energy_mwh: float
    specific_yield_kwh_per_kwp: float
    capacity_factor_percent: float
    # Summary Output Data (Excel B48–B65, image reference)
    total_modules: int = 0
    total_strings: int = 0
    pv_area_m2: float = 0.0
    land_area_m2: float = 0.0
    land_area_ha: float = 0.0
    gcr_pct: float = 0.0
    shadow_loss_pct: float = 0.0
    bifacial_gain_pct: float = 0.0
    temperature_loss_pct: float = 0.0
    ac_capacity_kw: float = 0.0
    num_inverters: int = 0
    dc_ac_ratio: float = 0.0
    performance_ratio_pct: float = 0.0


def calculate_poa(
    ghi: float,
    diffuse: float,
    lat: float,
    tilt: float,
    azimuth: float,
    albedo: float,
) -> float:
    """
    POA irradiance (kWh/m²) — from Excel H74.
    POA = GHI * ( (1-Albedo)*beam_geom + Albedo*(1+cos(Tilt))/2 + diffuse_term*(1-cos(Tilt))/2 ).
    diffuse: fraction 0–1 (diffuse fraction of GHI); diffuse_term = diffuse for the tilted diffuse part.
    """
    lat_r = math.radians(lat)
    tilt_r = math.radians(tilt)
    az_r = math.radians(azimuth)
    cos_lat = math.cos(lat_r)
    cos_tilt = math.cos(tilt_r)
    if cos_lat == 0:
        cos_lat = 1e-10
    beam_geom = (math.cos(lat_r - tilt_r) * math.cos(az_r)) / cos_lat
    # Excel: (1-Albedo)*beam_geom (applied to GHI)
    beam_component = (1 - albedo) * beam_geom
    ground_reflected = albedo * (1 + cos_tilt) / 2
    # Excel: E74*(((1-COS(RADIANS($B$8)))/2))
    diffuse_component = diffuse * (1 - cos_tilt) / 2
    poa = ghi * (beam_component + ground_reflected + diffuse_component)
    return max(0.0, poa)


def calculate_temp_loss_excel(
    lat: float,
    annual_avg_temp: float,
    annual_total_ghi: float,
    temp_coeff: float,
) -> float:
    """
    Single temperature loss factor (1+B56) applied to all months — from Excel B56.
    B56 = IF(ROUNDUP($B$4,0)<=20, (B21/100)*(D86+46-25), (B21/100)*((D86+C86*0.032)-25))
    D86 = AVERAGE(D74:D85), C86 = SUM(C74:C85). So one value for the year.
    """
    if lat <= 20:
        return (temp_coeff / 100) * (annual_avg_temp + 46 - 25)
    return (temp_coeff / 100) * ((annual_avg_temp + annual_total_ghi * 0.032) - 25)


def calculate_temp_loss(
    lat: float,
    temp: float,
    ghi: float,
    temp_coeff: float,
) -> float:
    """
    Per-month temperature loss (alternative; Excel uses annual D86/C86 in B56).
    Lat <= 20: (TC/100) * (Temp + 46 - 25)
    Else: (TC/100) * ((Temp + GHI*0.032) - 25)
    """
    if lat <= 20:
        return (temp_coeff / 100) * (temp + 46 - 25)
    return (temp_coeff / 100) * ((temp + ghi * 0.032) - 25)


def calculate_net_pr(
    pr: float,
    mismatch: float,
    wiring: float,
    soiling: float,
    snow: float,
    degradation: float,
) -> float:
    """
    Loss stack from Excel I74: (B18/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86).
    PR_net = (PR/100) × (1−Degradation) × (1−Mismatch) × (1−Wiring) × (1−Soiling) × (1−Snow).
    B55 (other) and B56 (temp) applied separately as (1+B55)*(1+B56).
    All loss inputs in % (0–100).
    """
    return (
        (pr / 100)
        * (1 - degradation / 100)
        * (1 - mismatch / 100)
        * (1 - wiring / 100)
        * (1 - soiling / 100)
        * (1 - snow / 100)
    )


def calculate_yield(input_data: ManualDCInput) -> ManualDCOutput:
    """
    Manual DC yield — matches Excel I74:I85 and B56.
    Energy = ((H74*B50*(B18/100))*(B26/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86))*(1+B55)*(1+B56)/1000
    B56 uses annual avg temp (D86) and annual total GHI (C86).
    Summary Output (B48–B65): total modules, strings, PV area, land, GCR, AC, inverters, DC/AC, PR.
    """
    monthly_results: List[float] = []

    net_pr = calculate_net_pr(
        input_data.performance_ratio,
        input_data.mismatch_loss,
        input_data.wiring_loss,
        input_data.soiling_loss,
        input_data.snow_loss,
        input_data.degradation,
    )

    inv_eff = input_data.inverter_efficiency / 100

    # Excel B56: single temp loss from annual avg temp and annual total GHI
    annual_avg_temp = sum(m.temperature for m in input_data.monthly_data) / max(len(input_data.monthly_data), 1)
    annual_total_ghi = sum(m.ghi for m in input_data.monthly_data)
    temp_loss_b56 = calculate_temp_loss_excel(
        input_data.latitude,
        annual_avg_temp,
        annual_total_ghi,
        input_data.temp_coefficient,
    )
    # B55 = other adjustment (Data_Input D55)
    other_adj_b55 = input_data.additional_loss / 100

    annual_poa = 0.0
    for m in input_data.monthly_data:
        poa = calculate_poa(
            m.ghi,
            m.diffuse,
            input_data.latitude,
            input_data.tilt,
            input_data.azimuth,
            input_data.albedo,
        )
        annual_poa += poa

        # I74: ((H74*B50*(B18/100))*(B26/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86))*(1+B55)*(1+B56)/1000
        energy = (
            poa
            * input_data.dc_capacity_kwp
            * net_pr
            * inv_eff
            * (1 + other_adj_b55)
            * (1 + temp_loss_b56)
        ) / 1000

        monthly_results.append(max(0.0, energy))

    annual = sum(monthly_results)
    dc_kwp = input_data.dc_capacity_kwp
    specific_yield = (annual * 1000) / dc_kwp if dc_kwp > 0 else 0.0

    # Excel B59 = ROUNDUP(B58/1.25,1), B60 = ROUNDDOWN(B59/B25,0), B61 = B60*B25, B62 = B58/B61
    ac_target = math.ceil(dc_kwp / 1.25 * 10) / 10 if dc_kwp > 0 else 0.0
    inverter_cap = input_data.inverter_capacity_kw
    if inverter_cap > 0:
        num_inverters = max(1, int(ac_target // inverter_cap))
        ac_capacity_kw = num_inverters * inverter_cap
    else:
        num_inverters = 0
        ac_capacity_kw = ac_target

    dc_ac_ratio = dc_kwp / ac_capacity_kw if ac_capacity_kw > 0 else 0.0
    capacity_factor = (
        (annual * 1000) / (ac_capacity_kw * 8760) * 100
        if ac_capacity_kw > 0
        else 0.0
    )

    # Summary: B48 total modules, B49 strings, B50 PV area, B51/B52 land, B53 GCR
    total_modules = 0
    total_strings = 0
    pv_area_m2 = 0.0
    land_area_m2 = 0.0
    land_area_ha = 0.0
    gcr_pct = input_data.gcr_default_pct
    if (
        input_data.module_wp > 0
        and input_data.module_length_m > 0
        and input_data.module_width_m > 0
    ):
        # B58 = (B48*B15)/1000 => B48 = B58*1000/B15
        total_modules = max(1, int(round(dc_kwp * 1000 / input_data.module_wp)))
        if input_data.modules_in_series > 0:
            total_strings = total_modules // input_data.modules_in_series
        # B50 = B48*B16*B17
        pv_area_m2 = total_modules * input_data.module_length_m * input_data.module_width_m
        # B51/B52: land = pv_area / GCR
        if gcr_pct > 0:
            land_area_m2 = pv_area_m2 / (gcr_pct / 100.0)
            land_area_ha = land_area_m2 / 10000.0

    # B65: Performance Ratio % (net PR as percentage for summary)
    performance_ratio_pct = net_pr * 100.0

    return ManualDCOutput(
        monthly_energy_mwh=monthly_results,
        annual_energy_mwh=annual,
        specific_yield_kwh_per_kwp=specific_yield,
        capacity_factor_percent=capacity_factor,
        total_modules=total_modules,
        total_strings=total_strings,
        pv_area_m2=round(pv_area_m2, 2),
        land_area_m2=round(land_area_m2, 2),
        land_area_ha=round(land_area_ha, 2),
        gcr_pct=gcr_pct,
        shadow_loss_pct=input_data.shadow_loss_pct,
        bifacial_gain_pct=input_data.bifacial_gain_pct,
        temperature_loss_pct=round(temp_loss_b56 * 100, 2),
        ac_capacity_kw=round(ac_capacity_kw, 1),
        num_inverters=num_inverters,
        dc_ac_ratio=round(dc_ac_ratio, 2),
        performance_ratio_pct=round(performance_ratio_pct, 2),
    )
