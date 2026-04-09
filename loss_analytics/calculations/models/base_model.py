"""
Base interface for all power calculation models

This module defines the standard interface that all power calculation models must implement.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PowerModelInput:
    """
    Standard input structure for all power calculation models
    
    This ensures consistent interface across different model implementations.
    """
    # Device information
    device_id: str
    device: Any  # device_list instance
    
    # Weather data
    irradiance: float  # POA irradiance (W/m²)
    module_temp: Optional[float] = None  # Module temperature (°C)
    ambient_temp: Optional[float] = None  # Ambient temperature (°C)
    wind_speed: Optional[float] = None  # Wind speed (m/s)
    
    # Electrical measurements (optional - for ML models or validation)
    measured_voltage: Optional[float] = None  # Measured string voltage (V)
    measured_current: Optional[float] = None  # Measured string current (A)
    
    # Timestamp
    timestamp: datetime = None
    
    # Additional context (model-specific data can go here)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate input data"""
        if self.irradiance < 0:
            raise ValueError("Irradiance cannot be negative")
        
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PowerModelOutput:
    """
    Standard output structure for all power calculation models
    
    This ensures consistent output format across different model implementations.
    """
    # Primary output
    expected_power: float  # Expected power output (W)
    
    # Optional electrical outputs
    expected_voltage: Optional[float] = None  # Expected voltage (V)
    expected_current: Optional[float] = None  # Expected current (A)
    
    # Detailed breakdown (optional)
    degradation_factor: Optional[float] = None  # 0-1
    soiling_factor: Optional[float] = None  # 0-1
    temperature_factor: Optional[float] = None  # Multiplier
    low_irradiance_factor: Optional[float] = None  # 0-1
    shading_factor: Optional[float] = None  # 0-1
    
    # Model metadata
    model_code: str = None  # Which model was used
    model_version: str = None  # Model version
    confidence: Optional[float] = None  # 0-1, for ML models
    execution_time_ms: Optional[float] = None  # Execution time in milliseconds
    
    # Additional details (model-specific outputs)
    details: Dict[str, Any] = field(default_factory=dict)


class BasePowerModel(ABC):
    """
    Abstract base class for all power calculation models
    
    All power calculation models must inherit from this class and implement
    the abstract methods. This ensures consistent interface and allows for
    pluggable model architecture.
    
    Example:
        class MyModel(BasePowerModel):
            MODEL_CODE = 'my_model_v1'
            MODEL_NAME = 'My Custom Model'
            MODEL_VERSION = '1.0.0'
            
            def calculate_expected_power(self, input_data):
                # Your calculation logic
                return PowerModelOutput(expected_power=7200, ...)
    """
    
    # Model metadata - MUST be overridden in subclass
    MODEL_CODE: str = None
    MODEL_NAME: str = None
    MODEL_VERSION: str = None
    MODEL_TYPE: str = None  # 'physics_based', 'ml', 'hybrid', 'empirical'
    
    # Model capabilities - override in subclass if different
    REQUIRES_WEATHER_DATA: bool = True
    REQUIRES_MODULE_DATASHEET: bool = True
    REQUIRES_HISTORICAL_DATA: bool = False
    SUPPORTS_DEGRADATION: bool = True
    SUPPORTS_SOILING: bool = True
    SUPPORTS_BIFACIAL: bool = False
    SUPPORTS_SHADING: bool = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize model with optional configuration
        
        Args:
            config: Model-specific configuration dictionary
        """
        self.config = config or {}
        self._validate_model_metadata()
        self._validate_config()
    
    def _validate_model_metadata(self):
        """Validate that model metadata is properly set"""
        if not self.MODEL_CODE:
            raise ValueError(f"{self.__class__.__name__} must define MODEL_CODE")
        if not self.MODEL_NAME:
            raise ValueError(f"{self.__class__.__name__} must define MODEL_NAME")
        if not self.MODEL_VERSION:
            raise ValueError(f"{self.__class__.__name__} must define MODEL_VERSION")
        if not self.MODEL_TYPE:
            raise ValueError(f"{self.__class__.__name__} must define MODEL_TYPE")
    
    @abstractmethod
    def calculate_expected_power(
        self,
        input_data: PowerModelInput
    ) -> PowerModelOutput:
        """
        Calculate expected power output for given conditions
        
        This is the core method that every model must implement.
        
        Args:
            input_data: Standardized input data (PowerModelInput)
            
        Returns:
            PowerModelOutput with expected power and optional details
            
        Raises:
            ValueError: If input data is invalid
            NotImplementedError: If required data is missing
        """
        pass
    
    @abstractmethod
    def validate_configuration(
        self,
        device: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that device has required configuration for this model
        
        Args:
            device: device_list instance
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if device can use this model
            - error_message: Explanation if not valid (None if valid)
        """
        pass
    
    @abstractmethod
    def get_required_inputs(self) -> List[str]:
        """
        Get list of required input fields for this model
        
        Returns:
            List of required field names (human-readable)
            
        Example:
            ['device', 'irradiance', 'ambient_temp or module_temp']
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model metadata and capabilities
        
        Returns:
            Dictionary with model information
        """
        return {
            'code': self.MODEL_CODE,
            'name': self.MODEL_NAME,
            'version': self.MODEL_VERSION,
            'type': self.MODEL_TYPE,
            'requires_weather_data': self.REQUIRES_WEATHER_DATA,
            'requires_module_datasheet': self.REQUIRES_MODULE_DATASHEET,
            'requires_historical_data': self.REQUIRES_HISTORICAL_DATA,
            'supports_degradation': self.SUPPORTS_DEGRADATION,
            'supports_soiling': self.SUPPORTS_SOILING,
            'supports_bifacial': self.SUPPORTS_BIFACIAL,
            'supports_shading': self.SUPPORTS_SHADING,
        }
    
    def _validate_config(self):
        """
        Validate model-specific configuration
        
        Override this method in subclass if model has specific
        configuration requirements.
        """
        pass
    
    # ==========================================
    # HELPER METHODS (Available to all models)
    # ==========================================
    
    def estimate_module_temperature(
        self,
        irradiance: float,
        ambient_temp: float,
        wind_speed: Optional[float] = None,
        noct: float = 45.0
    ) -> float:
        """
        Estimate module temperature from ambient temperature and irradiance
        
        Uses either simple NOCT model or Sandia model with wind speed.
        
        Args:
            irradiance: POA irradiance (W/m²)
            ambient_temp: Ambient temperature (°C)
            wind_speed: Wind speed (m/s), optional
            noct: Nominal Operating Cell Temperature (°C)
            
        Returns:
            Estimated module temperature (°C)
        """
        if irradiance < 0:
            irradiance = 0
        
        if wind_speed is not None and wind_speed > 0:
            # Sandia model (more accurate with wind speed)
            # T_module = T_ambient + (NOCT - 20) * (G / 800) / (1 + 0.2 * wind_speed)
            temp_rise = (noct - 20) * (irradiance / 800) / (1 + 0.2 * wind_speed)
        else:
            # Simple NOCT model
            # T_module = T_ambient + (NOCT - 20) * (G / 800)
            temp_rise = (noct - 20) * (irradiance / 800)
        
        return ambient_temp + temp_rise
    
    def __str__(self):
        """String representation of model"""
        return f"{self.MODEL_NAME} v{self.MODEL_VERSION} ({self.MODEL_CODE})"
    
    def __repr__(self):
        """Developer representation of model"""
        return f"<{self.__class__.__name__}: {self.MODEL_CODE} v{self.MODEL_VERSION}>"

