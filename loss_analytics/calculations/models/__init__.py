"""
Power calculation models package

All models are automatically registered on import.
"""
from .base_model import BasePowerModel, PowerModelInput, PowerModelOutput
from .registry import model_registry
from .sdm_model import SDMPowerModel
from .sdm_array_model import SDMArrayPowerModel
from .pvsyst_pr_model import PvsystPRPowerModel

# Auto-register SDM model as default
model_registry.register_model(SDMPowerModel, is_default=True)

# Register SDM Array model (more accurate physics-based SDM)
model_registry.register_model(SDMArrayPowerModel)

# Register PVsyst PR model (inverter-level: PR × irradiance × DC capacity)
model_registry.register_model(PvsystPRPowerModel)

__all__ = [
    'BasePowerModel',
    'PowerModelInput',
    'PowerModelOutput',
    'model_registry',
    'SDMPowerModel',
    'SDMArrayPowerModel',
    'PvsystPRPowerModel',
]






