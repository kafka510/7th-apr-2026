import os
from typing import Tuple

ALLOWED_CSV_EXTENSIONS = (".csv",)
ALLOWED_KML_EXTENSIONS = (".kml",)
LAT_MIN = -90.0
LAT_MAX = 90.0
LON_MIN = -180.0
LON_MAX = 180.0


class ValidationError(ValueError):
    pass


def validate_file_extension(filename: str, allowed: Tuple[str, ...], label: str) -> None:
    if not filename:
        raise ValidationError(f"{label}: filename is empty")
    _, ext = os.path.splitext(filename.lower())
    if ext not in allowed:
        raise ValidationError(
            f"{label}: invalid file type '{ext}'. Allowed: {', '.join(allowed)}"
        )


def validate_csv_file(filename: str) -> None:
    validate_file_extension(filename, ALLOWED_CSV_EXTENSIONS, "solargis_csv")


def validate_kml_file(filename: str) -> None:
    validate_file_extension(filename, ALLOWED_KML_EXTENSIONS, "plant_kml")


def validate_location(latitude: float, longitude: float) -> None:
    if not (LAT_MIN <= latitude <= LAT_MAX):
        raise ValidationError(
            f"latitude must be between {LAT_MIN} and {LAT_MAX}, got {latitude}"
        )
    if not (LON_MIN <= longitude <= LON_MAX):
        raise ValidationError(
            f"longitude must be between {LON_MIN} and {LON_MAX}, got {longitude}"
        )


def validate_positive(value: float, name: str) -> None:
    if value is None:
        raise ValidationError(f"{name} is required")
    if value <= 0:
        raise ValidationError(f"{name} must be positive, got {value}")


def validate_assumptions(
    module_wattage_wp: float,
    module_area_m2: float,
    land_usage_factor: float,
    dc_ac_ratio: float,
    inverter_efficiency_percent: float,
    inverter_capacity_kw: float = 0.0,
    soil_loss_percent: float = 0.0,
    temperature_loss_percent: float = 0.0,
    irradiance_loss_percent: float = 0.0,
    dc_loss_percent: float = 0.0,
    ac_loss_percent: float = 0.0,
) -> None:
    validate_positive(module_wattage_wp, "module_wattage_wp")
    validate_positive(module_area_m2, "module_area_m2")
    if not (0 < land_usage_factor <= 1):
        raise ValidationError(
            f"land_usage_factor must be in (0, 1], got {land_usage_factor}"
        )
    validate_positive(dc_ac_ratio, "dc_ac_ratio")
    if not (0 < inverter_efficiency_percent <= 100):
        raise ValidationError(
            f"inverter_efficiency_percent must be in (0, 100], got {inverter_efficiency_percent}"
        )
    if inverter_capacity_kw < 0:
        raise ValidationError("inverter_capacity_kw must be >= 0")
    for name, val in [
        ("soil_loss_percent", soil_loss_percent),
        ("temperature_loss_percent", temperature_loss_percent),
        ("irradiance_loss_percent", irradiance_loss_percent),
        ("dc_loss_percent", dc_loss_percent),
        ("ac_loss_percent", ac_loss_percent),
    ]:
        if not (0 <= val <= 100):
            raise ValidationError(f"{name} must be in [0, 100], got {val}")


def validate_area_m2(area_m2: float) -> None:
    validate_positive(area_m2, "plant area (m²)")


def validate_energy_positive(annual_energy_mwh: float) -> None:
    if annual_energy_mwh is None:
        raise ValidationError("annual_energy_mwh is required")
    if annual_energy_mwh <= 0:
        raise ValidationError(
            f"annual_energy_mwh must be positive, got {annual_energy_mwh}"
        )
