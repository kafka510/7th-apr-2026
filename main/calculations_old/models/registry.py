"""
Model registry for power calculation models

This registry manages all available power calculation models and provides
a centralized way to access them.
"""
from typing import Dict, Optional, List, Type
import logging

from .base_model import BasePowerModel

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central registry for all power calculation models
    
    Implements singleton pattern to ensure single registry instance.
    Models register themselves on import.
    """
    
    _instance = None
    _models: Dict[str, Type[BasePowerModel]] = {}
    _default_model_code: Optional[str] = None
    
    def __new__(cls):
        """Singleton pattern - only one registry instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models = {}
            cls._instance._default_model_code = None
        return cls._instance
    
    def register_model(
        self,
        model_class: Type[BasePowerModel],
        is_default: bool = False
    ):
        """
        Register a power calculation model
        
        Args:
            model_class: Model class (must inherit from BasePowerModel)
            is_default: Set this as the default model
            
        Raises:
            ValueError: If model_class doesn't inherit from BasePowerModel
            ValueError: If model doesn't define MODEL_CODE
        """
        # Validate model class
        if not issubclass(model_class, BasePowerModel):
            raise ValueError(
                f"{model_class.__name__} must inherit from BasePowerModel"
            )
        
        # Validate MODEL_CODE is defined
        model_code = model_class.MODEL_CODE
        if not model_code:
            raise ValueError(
                f"{model_class.__name__} must define MODEL_CODE class attribute"
            )
        
        # Check if model already registered
        if model_code in self._models:
            logger.warning(
                f"Model '{model_code}' is already registered. "
                f"Replacing with {model_class.__name__}"
            )
        
        # Register the model
        self._models[model_code] = model_class
        
        # Set as default if specified or if no default exists
        if is_default or self._default_model_code is None:
            self._default_model_code = model_code
        
        # Use DEBUG level to avoid cluttering production logs during startup
        # This registration happens at import time for each worker
        logger.debug(
            f"Registered power model: {model_code} "
            f"({model_class.MODEL_NAME} v{model_class.MODEL_VERSION})"
            f"{' [DEFAULT]' if model_code == self._default_model_code else ''}"
        )
    
    def get_model(
        self,
        model_code: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> BasePowerModel:
        """
        Get model instance by code
        
        Args:
            model_code: Model code (uses default if None)
            config: Model-specific configuration
            
        Returns:
            Initialized model instance
            
        Raises:
            ValueError: If model not found
        """
        # Use default if no code specified
        if model_code is None:
            model_code = self._default_model_code
        
        # Check if model is registered
        if model_code not in self._models:
            available = ', '.join(self._models.keys())
            raise ValueError(
                f"Model '{model_code}' not registered. "
                f"Available models: {available}"
            )
        
        # Get model class and instantiate
        model_class = self._models[model_code]
        return model_class(config=config)
    
    def list_models(self) -> List[Dict]:
        """
        List all registered models with their metadata
        
        Returns:
            List of dictionaries containing model information
        """
        models = []
        for code, model_class in self._models.items():
            # Instantiate temporarily to get info
            try:
                instance = model_class()
                info = instance.get_model_info()
                info['is_default'] = (code == self._default_model_code)
                info['is_registered'] = True
                models.append(info)
            except Exception as e:
                logger.error(f"Error getting info for model {code}: {str(e)}")
                # Include basic info even if instantiation fails
                models.append({
                    'code': code,
                    'name': model_class.MODEL_NAME,
                    'version': model_class.MODEL_VERSION,
                    'type': model_class.MODEL_TYPE,
                    'is_default': (code == self._default_model_code),
                    'is_registered': True,
                    'error': str(e)
                })
        
        return models
    
    def is_registered(self, model_code: str) -> bool:
        """
        Check if a model is registered
        
        Args:
            model_code: Model code to check
            
        Returns:
            True if model is registered, False otherwise
        """
        return model_code in self._models
    
    def get_default_model_code(self) -> str:
        """
        Get the code of the default model
        
        Returns:
            Default model code
            
        Raises:
            RuntimeError: If no models are registered
        """
        if not self._default_model_code:
            raise RuntimeError("No models registered in registry")
        return self._default_model_code
    
    def set_default_model(self, model_code: str):
        """
        Set the default model
        
        Args:
            model_code: Code of model to set as default
            
        Raises:
            ValueError: If model not registered
        """
        if model_code not in self._models:
            raise ValueError(f"Model '{model_code}' not registered")
        
        old_default = self._default_model_code
        self._default_model_code = model_code
        
        logger.info(
            f"Default model changed from '{old_default}' to '{model_code}'"
        )
    
    def unregister_model(self, model_code: str):
        """
        Unregister a model (use with caution!)
        
        Args:
            model_code: Model code to unregister
            
        Raises:
            ValueError: If trying to unregister default model
            ValueError: If model not registered
        """
        if model_code not in self._models:
            raise ValueError(f"Model '{model_code}' not registered")
        
        if model_code == self._default_model_code:
            raise ValueError(
                f"Cannot unregister default model '{model_code}'. "
                f"Set a different default first."
            )
        
        del self._models[model_code]
        logger.warning(f"Unregistered model: {model_code}")
    
    def get_model_count(self) -> int:
        """Get number of registered models"""
        return len(self._models)
    
    def __len__(self):
        """Allow len(registry) to get model count"""
        return self.get_model_count()
    
    def __contains__(self, model_code):
        """Allow 'code' in registry syntax"""
        return self.is_registered(model_code)
    
    def __str__(self):
        """String representation of registry"""
        return (
            f"ModelRegistry: {len(self._models)} models registered, "
            f"default='{self._default_model_code}'"
        )


# Global registry instance (singleton)
model_registry = ModelRegistry()

