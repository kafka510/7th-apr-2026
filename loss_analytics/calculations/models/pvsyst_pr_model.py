"""
PVsyst PR Expected Power Model

Expected power = PR × (G_eff / 1000) × P_dc_stc, with optional temperature
correction of PR using PV module temp_coeff_pmax (γ).
Used at inverter level with tilt-weighted effective irradiance.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import logging

from .base_model import BasePowerModel, PowerModelInput, PowerModelOutput

logger = logging.getLogger(__name__)

# Default NOCT for Faiman when module not available
_DEFAULT_NOCT = 45.0

# dc_cap from device_list is stored in kW; convert to W for formula
_DC_CAP_KW_TO_W = 1000.0


def _faiman_tcell(G_poa: float, T_amb: float, wind_ms: float, noct: float) -> float:
    """Cell temperature from Faiman model (G in W/m², T in °C, wind in m/s)."""
    u_sum = 800.0 / max(noct - 20.0, 1e-6)
    u0, u1 = 0.8 * u_sum, 0.2 * u_sum
    return T_amb + G_poa / (u0 + u1 * max(wind_ms, 0.0))


class PvsystPRPowerModel(BasePowerModel):
    """
    PVsyst-style Performance Ratio expected power model.

    Formula: P_expected = PR_corrected × (G_eff / 1000) × P_dc_stc_W
    - PR from asset (pv_syst_pr)
    - G_eff = effective irradiance (W/m²), passed as input_data.irradiance
    - P_dc_stc from device (dc_cap, assumed kW → W)
    - Optional: PR_corrected = PR × (1 + (γ/100)×(T_cell - 25)); γ from PV module temp_coeff_pmax
    """

    MODEL_CODE = "pvsyst_pr_v1"
    MODEL_NAME = "PVsyst PR"
    MODEL_VERSION = "1.0.0"
    MODEL_TYPE = "physics_based"

    REQUIRES_WEATHER_DATA = True
    REQUIRES_MODULE_DATASHEET = False  # Optional for temperature correction
    REQUIRES_HISTORICAL_DATA = False
    SUPPORTS_DEGRADATION = False
    SUPPORTS_SOILING = False
    SUPPORTS_BIFACIAL = False
    SUPPORTS_SHADING = False

    def calculate_expected_power(self, input_data: PowerModelInput) -> PowerModelOutput:
        start_time = time.time()
        device = input_data.device
        G_eff = input_data.irradiance
        if G_eff < 0:
            G_eff = 0.0

        # Resolve asset and PR
        try:
            from main.models import AssetList
            asset = AssetList.objects.get(asset_code=device.parent_code)
        except Exception as e:
            raise ValueError(
                f"Asset not found for device {device.device_id} (parent_code={getattr(device, 'parent_code', None)}): {e}"
            )
        pr = getattr(asset, "pv_syst_pr", None)
        if pr is None:
            raise ValueError(
                f"Asset {asset.asset_code} has no pv_syst_pr; required for PVsyst PR model."
            )
        pr = float(pr)
        if pr <= 0 or pr > 1:
            logger.warning(f"pv_syst_pr={pr} outside typical range (0, 1]; using as-is.")

        # DC capacity: device_list.dc_cap in kW → W
        dc_cap_kw = getattr(device, "dc_cap", None)
        if dc_cap_kw is None:
            raise ValueError(f"Device {device.device_id} has no dc_cap.")
        try:
            dc_cap_kw = float(dc_cap_kw)
        except (TypeError, ValueError):
            raise ValueError(f"Device {device.device_id} dc_cap is not a valid number.")
        if dc_cap_kw <= 0:
            raise ValueError(f"Device {device.device_id} dc_cap must be positive.")
        P_dc_stc_W = dc_cap_kw * _DC_CAP_KW_TO_W

        # Temperature coefficient from PV module (optional)
        # May be passed in metadata by caller (e.g. from representative string's module)
        gamma_per_c = None
        if isinstance(input_data.metadata, dict):
            gamma_per_c = input_data.metadata.get("temp_coeff_pmax") or input_data.metadata.get("gamma")
            if gamma_per_c is not None:
                gamma_per_c = float(gamma_per_c)
        module = None
        if gamma_per_c is None and hasattr(device, "get_module_datasheet") and callable(getattr(device, "get_module_datasheet", None)):
            module = device.get_module_datasheet()
            if module is not None and getattr(module, "temp_coeff_pmax", None) is not None:
                gamma_per_c = float(module.temp_coeff_pmax)  # %/°C

        # Cell temperature
        T_cell = None
        module_temp = input_data.module_temp
        ambient_temp = input_data.ambient_temp
        wind_speed = input_data.wind_speed or 0.0

        if module_temp is not None:
            T_cell = float(module_temp)
        elif ambient_temp is not None:
            noct = _DEFAULT_NOCT
            if isinstance(input_data.metadata, dict) and input_data.metadata.get("noct") is not None:
                noct = float(input_data.metadata["noct"])
            elif module is not None and getattr(module, "noct", None) is not None:
                noct = float(module.noct)
            T_cell = _faiman_tcell(G_eff, float(ambient_temp), float(wind_speed), noct)

        # PR corrected for temperature
        if T_cell is not None and gamma_per_c is not None:
            pr_corrected = pr * (1.0 + (gamma_per_c / 100.0) * (T_cell - 25.0))
        else:
            pr_corrected = pr

        # Expected DC power (W)
        P_dc = pr_corrected * (G_eff / 1000.0) * P_dc_stc_W
        if P_dc < 0:
            P_dc = 0.0
        # Optional cap at STC capacity
        if P_dc > P_dc_stc_W:
            P_dc = P_dc_stc_W

        execution_time_ms = (time.time() - start_time) * 1000
        details = {
            "pr_nominal": pr,
            "pr_corrected": pr_corrected,
            "G_eff_W_m2": G_eff,
            "P_dc_stc_W": P_dc_stc_W,
            "dc_cap_kw": dc_cap_kw,
        }
        if T_cell is not None:
            details["T_cell_C"] = T_cell
        if gamma_per_c is not None:
            details["gamma_per_c"] = gamma_per_c

        return PowerModelOutput(
            expected_power=P_dc,
            expected_voltage=None,
            expected_current=None,
            degradation_factor=None,
            soiling_factor=None,
            temperature_factor=pr_corrected / pr if pr and pr != 0 else None,
            low_irradiance_factor=None,
            shading_factor=None,
            model_code=self.MODEL_CODE,
            model_version=self.MODEL_VERSION,
            confidence=1.0,
            execution_time_ms=execution_time_ms,
            details=details,
        )

    def validate_configuration(self, device: Any) -> tuple[bool, Optional[str]]:
        if not getattr(device, "parent_code", None):
            return False, "Device has no parent_code (asset required for PR)."
        try:
            from main.models import AssetList
            asset = AssetList.objects.get(asset_code=device.parent_code)
        except AssetList.DoesNotExist:
            return False, f"Asset {device.parent_code} not found."
        except Exception as e:
            return False, str(e)
        pr = getattr(asset, "pv_syst_pr", None)
        if pr is None:
            return False, f"Asset {asset.asset_code} has no pv_syst_pr; set it for PVsyst PR model."
        try:
            if float(pr) <= 0 or float(pr) > 1:
                pass  # allow but warn elsewhere
        except (TypeError, ValueError):
            return False, "Asset pv_syst_pr must be a number between 0 and 1."
        dc_cap = getattr(device, "dc_cap", None)
        if dc_cap is None:
            return False, "Device has no dc_cap; required for PVsyst PR model."
        try:
            if float(dc_cap) <= 0:
                return False, "Device dc_cap must be positive."
        except (TypeError, ValueError):
            return False, "Device dc_cap must be a valid positive number."
        return True, None

    def get_required_inputs(self) -> List[str]:
        return [
            "device (with parent_code and dc_cap)",
            "asset with pv_syst_pr set",
            "irradiance (G_eff in W/m², tilt-weighted)",
            "ambient_temp or module_temp (°C, optional for PR correction)",
            "PV module (optional, for temp_coeff_pmax temperature correction)",
        ]
