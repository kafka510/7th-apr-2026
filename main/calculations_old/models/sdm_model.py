"""
Single Diode Model (SDM) implementation as a plugin

This module implements the physics-based Single Diode Model for calculating
expected PV power output.
"""
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from datetime import datetime, date
import time
import logging

from .base_model import BasePowerModel, PowerModelInput, PowerModelOutput

logger = logging.getLogger(__name__)


class SDMPowerModel(BasePowerModel):
    """
    Single Diode Model (5-parameter) for PV power calculation
    
    This is a physics-based model using the single diode equivalent circuit
    representation of a PV module. It accounts for:
    - Irradiance effects
    - Temperature effects
    - Degradation
    - Soiling and shading losses
    - Low irradiance performance
    """
    
    # Model metadata
    MODEL_CODE = 'sdm_v1'
    MODEL_NAME = 'Single Diode Model'
    MODEL_VERSION = '1.0.0'
    MODEL_TYPE = 'physics_based'
    
    # Model capabilities
    REQUIRES_WEATHER_DATA = True
    REQUIRES_MODULE_DATASHEET = True
    REQUIRES_HISTORICAL_DATA = False
    SUPPORTS_DEGRADATION = True
    SUPPORTS_SOILING = True
    SUPPORTS_BIFACIAL = True
    SUPPORTS_SHADING = True
    
    # Physical constants
    K = 1.381e-23  # Boltzmann constant (J/K)
    Q = 1.602e-19  # Elementary charge (C)
    
    def calculate_expected_power(
        self,
        input_data: PowerModelInput
    ) -> PowerModelOutput:
        """
        Calculate expected power using Single Diode Model
        
        Args:
            input_data: StandardizedInput data
            
        Returns:
            PowerModelOutput with expected power and detailed breakdown
        """
        start_time = time.time()
        
        # Validate device has module datasheet
        device = input_data.device
        module = device.get_module_datasheet()
        if not module:
            raise ValueError(
                f"Device {device.device_id} has no module datasheet configured"
            )
        
        # Get weather inputs
        irradiance = input_data.irradiance
        ambient_temp = input_data.ambient_temp
        module_temp = input_data.module_temp
        wind_speed = input_data.wind_speed
        
        # Estimate module temperature if not provided
        if module_temp is None:
            if ambient_temp is None:
                raise ValueError(
                    "Either module_temp or ambient_temp must be provided"
                )
            module_temp = self.estimate_module_temperature(
                irradiance, ambient_temp, wind_speed, module.noct
            )
        
        # Calculate base expected power with SDM
        sdm_result = self._calculate_sdm_power(
            module=module,
            device=device,
            irradiance=irradiance,
            module_temp=module_temp
        )
        
        expected_power = sdm_result['expected_power']
        
        # Apply degradation
        degradation_factor = self._calculate_degradation_factor(device)
        expected_power *= degradation_factor
        
        # Apply soiling loss
        soiling_loss_pct = device.expected_soiling_loss or 0
        soiling_factor = 1 - (soiling_loss_pct / 100)
        expected_power *= soiling_factor
        
        # Apply shading loss
        shading_loss_pct = device.shading_factor or 0
        shading_factor = 1 - (shading_loss_pct / 100)
        expected_power *= shading_factor
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Return standardized output
        return PowerModelOutput(
            expected_power=expected_power,
            expected_voltage=sdm_result.get('expected_voltage'),
            expected_current=sdm_result.get('expected_current'),
            degradation_factor=degradation_factor,
            soiling_factor=soiling_factor,
            temperature_factor=sdm_result.get('temperature_factor'),
            low_irradiance_factor=sdm_result.get('low_irr_factor'),
            shading_factor=shading_factor,
            model_code=self.MODEL_CODE,
            model_version=self.MODEL_VERSION,
            confidence=1.0,  # Physics-based model always has 100% confidence
            execution_time_ms=execution_time_ms,
            details={
                'fill_factor': sdm_result.get('fill_factor'),
                'efficiency': sdm_result.get('efficiency'),
                'module_temp': module_temp,
                'voc_corrected': sdm_result.get('voc_corrected'),
                'isc_corrected': sdm_result.get('isc_corrected'),
            }
        )
    
    def _calculate_sdm_power(
        self,
        module,
        device,
        irradiance: float,
        module_temp: float
    ) -> Dict[str, float]:
        """
        Core SDM calculation logic
        
        Applies temperature and irradiance corrections to module parameters
        and calculates expected power.
        
        Args:
            module: PVModuleDatasheet instance
            device: device_list instance
            irradiance: POA irradiance (W/m²)
            module_temp: Module temperature (°C)
            
        Returns:
            Dictionary with calculation results
        """
        # Temperature difference from STC
        delta_t = module_temp - 25.0
        
        # ==========================================
        # VOLTAGE CORRECTIONS
        # ==========================================
        
        if module.temp_coeff_type_voc == 'absolute':
            # Absolute coefficient (V/°C)
            voc_corrected = (
                module.voc_stc + module.temp_coeff_voc * delta_t
            ) * device.modules_in_series
            
            # Estimate Vmp coefficient if not provided
            vmp_temp_coeff = getattr(module, 'temp_coeff_vmp', None)
            if vmp_temp_coeff is None:
                vmp_temp_coeff = module.temp_coeff_voc * 0.85
            
            vmp_corrected = (
                module.vmp_stc + vmp_temp_coeff * delta_t
            ) * device.modules_in_series
        else:
            # Percentage coefficient (%/°C)
            voc_corrected = (
                module.voc_stc * (1 + module.temp_coeff_voc / 100 * delta_t)
            ) * device.modules_in_series
            
            vmp_corrected = (
                module.vmp_stc * (1 + module.temp_coeff_voc / 100 * delta_t * 0.85)
            ) * device.modules_in_series
        
        # ==========================================
        # CURRENT CORRECTIONS
        # ==========================================
        
        if module.temp_coeff_type_isc == 'absolute':
            # Absolute coefficient (A/°C)
            isc_corrected = (
                module.isc_stc * (irradiance / 1000) +
                module.temp_coeff_isc * delta_t
            )
            
            # Estimate Imp coefficient if not provided
            imp_temp_coeff = getattr(module, 'temp_coeff_imp', None)
            if imp_temp_coeff is None:
                imp_temp_coeff = module.temp_coeff_isc * 0.95
            
            imp_corrected = (
                module.imp_stc * (irradiance / 1000) +
                imp_temp_coeff * delta_t
            )
        else:
            # Percentage coefficient (%/°C)
            isc_corrected = (
                module.isc_stc * (irradiance / 1000) *
                (1 + module.temp_coeff_isc / 100 * delta_t)
            )
            
            imp_corrected = (
                module.imp_stc * (irradiance / 1000) *
                (1 + module.temp_coeff_isc / 100 * delta_t)
            )
        
        # ==========================================
        # LOW IRRADIANCE CORRECTION
        # ==========================================
        
        low_irr_factor = self._get_low_irradiance_factor(module, irradiance)
        
        # ==========================================
        # POWER CALCULATION
        # ==========================================
        
        # Method 1: From temperature coefficient
        temperature_factor = 1 + module.temp_coeff_pmax / 100 * delta_t
        pmax_method1 = (
            module.pmax_stc * 
            (irradiance / 1000) *
            temperature_factor *
            low_irr_factor *
            device.modules_in_series
        )
        
        # Method 2: From IV curve (Vmp × Imp)
        pmax_method2 = vmp_corrected * imp_corrected
        
        # Use average of both methods for better accuracy
        expected_power = (pmax_method1 + pmax_method2) / 2
        
        # ==========================================
        # ADDITIONAL METRICS
        # ==========================================
        
        # Calculate fill factor
        fill_factor = 0
        if voc_corrected > 0 and isc_corrected > 0:
            fill_factor = expected_power / (voc_corrected * isc_corrected)
        
        # Calculate efficiency
        efficiency = 0
        if irradiance > 0:
            total_area = module.area * device.modules_in_series
            if total_area > 0:
                efficiency = (expected_power / (irradiance * total_area)) * 100
        
        return {
            'expected_power': expected_power,
            'expected_voltage': vmp_corrected,
            'expected_current': imp_corrected,
            'voc_corrected': voc_corrected,
            'isc_corrected': isc_corrected,
            'temperature_factor': temperature_factor,
            'low_irr_factor': low_irr_factor,
            'fill_factor': fill_factor,
            'efficiency': efficiency,
        }
    
    def _get_low_irradiance_factor(
        self,
        module,
        irradiance: float
    ) -> float:
        """
        Get low irradiance performance factor from datasheet
        
        Uses linear interpolation between datasheet test points.
        
        Args:
            module: PVModuleDatasheet instance
            irradiance: POA irradiance (W/m²)
            
        Returns:
            Performance factor (0-1)
        """
        if irradiance >= 1000:
            return 1.0
        
        # Build interpolation points from datasheet
        # Use datasheet values if available, otherwise use typical values
        # Handle None values properly - if attribute exists but is None, use default
        def get_low_irr_value(attr_name, default):
            value = getattr(module, attr_name, None)
            if value is None:
                return default
            return value
        
        points = [
            (1000, 1.0),
            (800, get_low_irr_value('low_irr_800', 99.5) / 100),
            (600, get_low_irr_value('low_irr_600', 99.0) / 100),
            (400, get_low_irr_value('low_irr_400', 98.0) / 100),
            (200, get_low_irr_value('low_irr_200', 96.0) / 100),
        ]
        
        # Linear interpolation
        for i in range(len(points) - 1):
            irr_high, factor_high = points[i]
            irr_low, factor_low = points[i + 1]
            
            if irr_high >= irradiance >= irr_low:
                # Interpolate
                factor = factor_high + (factor_low - factor_high) * \
                         (irradiance - irr_high) / (irr_low - irr_high)
                return factor
        
        # Below 200 W/m² - use conservative estimate
        return 0.90
    
    def _calculate_degradation_factor(self, device) -> float:
        """
        Calculate degradation factor based on installation age
        
        Uses measured degradation if available, otherwise uses warranty-based
        estimation from module datasheet.
        
        Args:
            device: device_list instance
            
        Returns:
            Degradation factor (0-1), where 1.0 = no degradation
        """
        if not device.installation_date:
            # No installation date - assume no degradation
            logger.debug(
                f"Device {device.device_id} has no installation_date, "
                f"assuming no degradation"
            )
            return 1.0
        
        # Calculate age in years
        age_days = (date.today() - device.installation_date).days
        age_years = age_days / 365.25
        
        if age_years <= 0:
            return 1.0
        
        module = device.get_module_datasheet()
        if not module:
            logger.debug(
                f"Device {device.device_id} has no module datasheet, "
                f"assuming no degradation"
            )
            return 1.0
        
        # Use measured degradation rate if available (most accurate)
        if device.measured_degradation_rate:
            total_degradation_pct = device.measured_degradation_rate * age_years
            logger.debug(
                f"Using measured degradation: {device.measured_degradation_rate}%/year, "
                f"age {age_years:.1f}years = {total_degradation_pct:.2f}% total"
            )
        else:
            # Use warranty-based estimation
            if age_years <= 1:
                # First year - use first year degradation
                total_degradation_pct = module.estimated_degradation_year1
            else:
                # Subsequent years - use linear degradation
                year1_deg = module.estimated_degradation_year1
                annual_deg = module.estimated_annual_degradation
                total_degradation_pct = year1_deg + (age_years - 1) * annual_deg
            
            logger.debug(
                f"Using warranty-based degradation: age {age_years:.1f}years "
                f"= {total_degradation_pct:.2f}% total"
            )
        
        # Convert to factor (0-1)
        degradation_factor = max(0, 1 - (total_degradation_pct / 100))
        
        return degradation_factor
    
    def validate_configuration(
        self,
        device: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that device has required configuration for SDM
        
        Args:
            device: device_list instance
            
        Returns:
            (is_valid, error_message)
        """
        # Check if device has module datasheet
        module = device.get_module_datasheet()
        if not module:
            return False, "Device has no module datasheet configured"
        
        # Check if modules_in_series is set
        if not device.modules_in_series:
            return False, "modules_in_series not configured"
        
        # Check required module datasheet fields
        required_fields = {
            'pmax_stc': 'Maximum power at STC',
            'voc_stc': 'Open-circuit voltage at STC',
            'isc_stc': 'Short-circuit current at STC',
            'vmp_stc': 'MPP voltage at STC',
            'imp_stc': 'MPP current at STC',
            'temp_coeff_pmax': 'Temperature coefficient of Pmax',
            'temp_coeff_voc': 'Temperature coefficient of Voc',
            'temp_coeff_isc': 'Temperature coefficient of Isc',
            'area': 'Module area',
        }
        
        # Optional fields (won't fail validation if missing)
        optional_fields = {
            'cells_per_module': 'Cells per module',  # Optional - can estimate from other parameters
            'noct': 'NOCT (Nominal Operating Cell Temperature)',  # Optional - can estimate
        }
        
        for field, description in required_fields.items():
            value = getattr(module, field, None)
            if value is None or value == 0:
                return False, f"Module datasheet missing required field: {description} ({field})"
        
        # Warn about missing optional fields but don't fail validation
        for field, description in optional_fields.items():
            value = getattr(module, field, None)
            if value is None or value == 0:
                logger.debug(
                    f"Module datasheet missing optional field: {description} ({field}). "
                    f"Some calculations may use default values."
                )
        
        return True, None
    
    def get_required_inputs(self) -> List[str]:
        """
        Get list of required input fields for SDM
        
        Returns:
            List of required field names
        """
        return [
            'device (with module_datasheet configured)',
            'irradiance (W/m²)',
            'ambient_temp or module_temp (°C)',
            'modules_in_series',
            'installation_date (for degradation)',
        ]

