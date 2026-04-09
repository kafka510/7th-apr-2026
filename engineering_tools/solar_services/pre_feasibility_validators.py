"""Validation helpers for pre-feasibility blocks (site orientation, module, string)."""

TILT_MIN = 5
TILT_MAX = 40
AZIMUTH_MIN = 0
AZIMUTH_MAX = 360
SOILING_MIN = 0
SOILING_MAX = 10


class PreFeasibilityValidationError(ValueError):
    pass


def validate_tilt_deg(value: float) -> float:
    if not (TILT_MIN <= value <= TILT_MAX):
        raise PreFeasibilityValidationError(f"Tilt must be between {TILT_MIN}° and {TILT_MAX}°")
    return value


def validate_azimuth_deg(value: float) -> float:
    if not (AZIMUTH_MIN <= value <= AZIMUTH_MAX):
        raise PreFeasibilityValidationError(f"Azimuth must be between {AZIMUTH_MIN}° and {AZIMUTH_MAX}°")
    return value


def validate_structure_height_m(value: float | None) -> float | None:
    if value is not None and value < 0:
        raise PreFeasibilityValidationError("Structure height cannot be negative")
    return value


def validate_soiling_rate_pct(value: float) -> float:
    if not (SOILING_MIN <= value <= SOILING_MAX):
        raise PreFeasibilityValidationError(f"Soiling rate must be between {SOILING_MIN}–{SOILING_MAX}%")
    return value


def validate_module_wp(value: int) -> int:
    if value <= 0 or value > 1000:
        raise PreFeasibilityValidationError("Module power must be realistic (1–1000 Wp)")
    return value


def validate_degradation_pct_per_year(value: float) -> float:
    if not (0 <= value <= 2):
        raise PreFeasibilityValidationError("Degradation should be between 0–2% per year")
    return value


def validate_module_dimensions(length_mm: int, width_mm: int) -> None:
    if length_mm <= 0 or width_mm <= 0:
        raise PreFeasibilityValidationError("Module dimensions must be positive")


def validate_strings_per_inverter(value: int) -> int:
    if value <= 0:
        raise PreFeasibilityValidationError("Strings per inverter must be > 0")
    return value
