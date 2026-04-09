"""
Power calculation service using pluggable models

This service provides a high-level interface for calculating expected power
using different calculation models (SDM, ML, etc.).
"""
from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime

from .models import model_registry, PowerModelInput, PowerModelOutput
from .models.base_model import BasePowerModel

logger = logging.getLogger(__name__)


class PowerCalculationService:
    """
    Service layer for power calculations using pluggable models
    
    This service:
    - Selects the appropriate model based on device configuration
    - Handles model fallback on errors
    - Provides consistent interface regardless of model used
    - Tracks model performance
    """
    
    def calculate_expected_power(
        self,
        device,
        irradiance: float,
        module_temp: Optional[float] = None,
        ambient_temp: Optional[float] = None,
        wind_speed: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        model_code: Optional[str] = None,
        fallback_on_error: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PowerModelOutput:
        """
        Calculate expected power for a device

        Args:
            device: device_list instance
            irradiance: POA irradiance (W/m²)
            module_temp: Module temperature (°C), optional
            ambient_temp: Ambient temperature (°C), optional
            wind_speed: Wind speed (m/s), optional
            timestamp: Timestamp of measurement (defaults to now)
            model_code: Model to use (overrides device configuration)
            fallback_on_error: Use default model if configured model fails
            metadata: Optional dict passed to PowerModelInput (e.g. temp_coeff_pmax, noct for PR model)

        Returns:
            PowerModelOutput with expected power and details

        Raises:
            ValueError: If calculation fails and fallback is disabled
        """
        # Determine which model to use
        selected_model_code = self._select_model(device, model_code)
        model_config = self._get_model_config(device, selected_model_code)
        
        # Only log model selection once per device (use a simple cache)
        if not hasattr(self, '_logged_models'):
            self._logged_models = set()
        device_model_key = f"{device.device_id}:{selected_model_code}"
        if device_model_key not in self._logged_models:
            logger.info(f"Using power model '{selected_model_code}' for device {device.device_id}")
            self._logged_models.add(device_model_key)
        
        # Get model instance
        try:
            model = model_registry.get_model(selected_model_code, config=model_config)
        except ValueError as e:
            if fallback_on_error:
                logger.warning(
                    f"Model '{selected_model_code}' not available, using default: {e}"
                )
                model = model_registry.get_model()  # Get default
                selected_model_code = model.MODEL_CODE
            else:
                raise
        
        # Validate device configuration for this model
        is_valid, error_msg = model.validate_configuration(device)
        if not is_valid:
            should_fallback = fallback_on_error and getattr(
                device, 'model_fallback_enabled', True
            )
            
            if should_fallback:
                logger.warning(
                    f"Device {device.device_id} configuration invalid for "
                    f"{selected_model_code}: {error_msg}. Falling back to default model."
                )
                model = model_registry.get_model()  # Get default
                
                # Validate again with default model
                is_valid, error_msg = model.validate_configuration(device)
                if not is_valid:
                    raise ValueError(
                        f"Device configuration invalid even for default model: {error_msg}"
                    )
            else:
                raise ValueError(f"Device configuration invalid: {error_msg}")
        
        # Prepare input data
        input_data = PowerModelInput(
            device_id=device.device_id,
            device=device,
            irradiance=irradiance,
            module_temp=module_temp,
            ambient_temp=ambient_temp,
            wind_speed=wind_speed,
            timestamp=timestamp or datetime.now(),
            metadata=metadata or {},
        )
        
        # Calculate expected power
        try:
            result = model.calculate_expected_power(input_data)
            # Avoid per-timestamp spam in production logs; keep details on debug only.
            # If you ever need this again, enable DEBUG level for this logger.
            logger.debug(
                "Expected power calculated for device %s using %s (%.2f ms)",
                device.device_id,
                getattr(result, "model_code", None),
                getattr(result, "execution_time_ms", 0.0) or 0.0,
            )
            return result
            
        except Exception as e:
            should_fallback = fallback_on_error and getattr(
                device, 'model_fallback_enabled', True
            )
            
            if should_fallback and selected_model_code != model_registry.get_default_model_code():
                logger.error(
                    f"Model {selected_model_code} failed for device {device.device_id}: {e}. "
                    f"Falling back to default model.",
                    exc_info=True
                )
                # Retry with default model
                default_model = model_registry.get_model()
                return default_model.calculate_expected_power(input_data)
            else:
                logger.error(
                    f"Power calculation failed for device {device.device_id}: {e}",
                    exc_info=True
                )
                raise
    
    def _select_model(
        self,
        device,
        model_code_override: Optional[str] = None
    ) -> str:
        """
        Determine which model to use for calculation
        
        Priority:
        1. Explicit override (model_code parameter)
        2. Device configuration (device.power_model)
        3. Default model from registry
        
        Args:
            device: device_list instance
            model_code_override: Optional model code override
            
        Returns:
            Model code to use
        """
        # Priority 1: Explicit override
        if model_code_override:
            return model_code_override
        
        # Priority 2: Device configuration
        # Try to get power model from device using get_power_model() method
        power_model_obj = None
        if hasattr(device, 'get_power_model'):
            power_model_obj = device.get_power_model()
        # Fallback: try direct attribute access
        elif hasattr(device, 'power_model') and device.power_model:
            power_model_obj = device.power_model
        # Also try power_model_id directly
        elif hasattr(device, 'power_model_id') and device.power_model_id:
            try:
                from main.models import PowerModelRegistry
                power_model_obj = PowerModelRegistry.objects.get(id=device.power_model_id)
            except Exception:
                pass
        
        if power_model_obj and hasattr(power_model_obj, 'model_code'):
            logger.debug(f"Device {device.device_id} configured with power model '{power_model_obj.model_code}' (power_model_id={getattr(device, 'power_model_id', None)})")
            return power_model_obj.model_code
        
        # Priority 3: Default model
        default_model = model_registry.get_default_model_code()
        logger.debug(f"Device {device.device_id} using default power model '{default_model}' (no device-specific model configured)")
        return default_model
    
    def _get_model_config(
        self,
        device,
        model_code: str
    ) -> Optional[Dict]:
        """
        Get model-specific configuration for device
        
        Args:
            device: device_list instance
            model_code: Model code
            
        Returns:
            Model configuration dict or None
        """
        # Check if device has model-specific configuration
        if hasattr(device, 'power_model_config') and device.power_model_config:
            # power_model_config is a JSONB field
            return device.power_model_config
        
        return None
    
    def list_available_models(self) -> List[Dict]:
        """
        List all available power calculation models
        
        Returns:
            List of model information dictionaries
        """
        return model_registry.list_models()
    
    def get_recommended_model(self, device) -> str:
        """
        Get recommended model code for a device
        
        Args:
            device: device_list instance
            
        Returns:
            Recommended model code
        """
        # If device has model configured, use it
        if hasattr(device, 'power_model') and device.power_model:
            return device.power_model.model_code
        
        # Otherwise, recommend default
        return model_registry.get_default_model_code()
    
    def validate_device_for_model(
        self,
        device,
        model_code: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if device can use a specific model
        
        Args:
            device: device_list instance
            model_code: Model code (uses device's model if None)
            
        Returns:
            (is_valid, error_message)
        """
        if model_code is None:
            model_code = self._select_model(device)
        
        try:
            model = model_registry.get_model(model_code)
            return model.validate_configuration(device)
        except ValueError as e:
            return False, str(e)

