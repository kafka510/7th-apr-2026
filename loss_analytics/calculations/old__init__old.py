"""
Loss analytics calculation facade.

This module centralizes access to all power/loss calculation primitives
so callers do NOT depend directly on `main.calculations.*` any more.

Implementation is still provided by the existing modules for now; the
plan is to physically move those modules under `loss_analytics` once
call sites are fully decoupled.
"""

from main.calculations.calculation_service import CalculationService
from main.calculations.metric_mapping_service import MetricMappingService
from main.calculations.timeseries_reader import TimeseriesReader
from main.calculations.timeseries_writer import TimeseriesWriter
from main.calculations.power_calculation_service import PowerCalculationService
from main.calculations.inverter_expected_power_service import (
    compute_and_persist_inverter_expected_power,
)
from main.calculations.satellite_ghi_temp_upload import upload_satellite_ghi_temp_csv

from main.calculations.models import (
    BasePowerModel,
    PowerModelInput,
    PowerModelOutput,
    model_registry,
    SDMPowerModel,
    SDMArrayPowerModel,
    PvsystPRPowerModel,
)

from loss_analytics.pipeline.transposition import ghi_to_gii, gii_device_id

__all__ = [
    "CalculationService",
    "MetricMappingService",
    "TimeseriesReader",
    "TimeseriesWriter",
    "PowerCalculationService",
    "compute_and_persist_inverter_expected_power",
    "upload_satellite_ghi_temp_csv",
    "BasePowerModel",
    "PowerModelInput",
    "PowerModelOutput",
    "model_registry",
    "SDMPowerModel",
    "SDMArrayPowerModel",
    "PvsystPRPowerModel",
    "ghi_to_gii",
    "gii_device_id",
]

