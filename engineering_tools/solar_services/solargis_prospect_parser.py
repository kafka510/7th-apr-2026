from __future__ import annotations

from io import StringIO
from typing import Any, Dict, List

import pandas as pd

from .validators import ValidationError


REQUIRED_COLUMNS = ["month", "ghi", "dni", "dif", "temp"]


def _safe_float(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"SolarGIS CSV: non-numeric value '{value}' in numeric column"
        ) from exc
    return f


def _safe_float_optional(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        f = float(value)
        if pd.isna(f):
            return default
        return f
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    if not s or s.lower() in ("na", "n/a", "-", "--"):
        return default
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def _normalize_header(header: str) -> str:
    if not isinstance(header, str):
        return ""
    base = header
    if "[" in base:
        base = base.split("[", 1)[0]
    return base.strip().lower()


def _detect_required_columns(df: pd.DataFrame) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for col in df.columns:
        norm = _normalize_header(col)
        if ("month" in norm or norm in {"m", "mon"}) and "month" not in mapping:
            mapping["month"] = col
            continue
        if ("ghi" in norm or "global_hor" in norm or "globhor" in norm) and "ghi" not in mapping:
            mapping["ghi"] = col
            continue
        if "dni" in norm and "dni" not in mapping:
            mapping["dni"] = col
            continue
        if ("dif" in norm or "dhi" in norm or "diffuse" in norm) and "dif" not in mapping:
            mapping["dif"] = col
            continue
        if ("temp" in norm or "t24" in norm or "t_2m" in norm or "temperature" in norm) and "temp" not in mapping:
            mapping["temp"] = col
            continue
        if ("albm" in norm or "albedo" in norm) and "albedo" not in mapping:
            mapping["albedo"] = col
            continue
        if ("wsm" in norm or "wind" in norm) and "wind_speed_ms" not in mapping:
            mapping["wind_speed_ms"] = col
            continue
        if ("rhm" in norm or norm.startswith("rh") or "humidity" in norm) and "relative_humidity_percent" not in mapping:
            mapping["relative_humidity_percent"] = col
            continue
        if ("pwat" in norm or "pwatm" in norm) and "precipitable_water_kg_m2" not in mapping:
            mapping["precipitable_water_kg_m2"] = col
            continue
        if ("precm" in norm or "precip" in norm or "rain" in norm) and "precipitation_mm" not in mapping:
            mapping["precipitation_mm"] = col
            continue
        if ("cddm" in norm or "cooling_degree" in norm) and "cooling_degree_days" not in mapping:
            mapping["cooling_degree_days"] = col
            continue
        if ("hddm" in norm or "heating_degree" in norm) and "heating_degree_days" not in mapping:
            mapping["heating_degree_days"] = col
            continue
        if ("snow_days" in norm or "snowdays" in norm or ("snow" in norm and "free" not in norm)) and "snow_days" not in mapping:
            mapping["snow_days"] = col
            continue
    missing = [name for name in REQUIRED_COLUMNS if name not in mapping]
    if missing:
        raise ValidationError(
            "SolarGIS CSV: missing required columns. "
            f"Expected at least Month, GHI, DNI, DIF, TEMP. Missing: {', '.join(missing)}"
        )
    return mapping


def _validate_units(column_name: str, logical_name: str) -> None:
    _ = column_name, logical_name


def extract_solargis_metadata(csv_content: bytes) -> Dict[str, Any]:
    result: Dict[str, Any] = {"site_name": None, "file_lat": None, "file_lng": None}
    try:
        text = csv_content.decode("utf-8", errors="replace")
    except Exception:
        return result
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#Site name:"):
            result["site_name"] = line.replace("#Site name:", "").strip()
        elif line.startswith("#Latitude:"):
            try:
                result["file_lat"] = float(line.replace("#Latitude:", "").strip())
            except (TypeError, ValueError):
                pass
        elif line.startswith("#Longitude:"):
            try:
                result["file_lng"] = float(line.replace("#Longitude:", "").strip())
            except (TypeError, ValueError):
                pass
    return result


def parse_solargis_prospect_monthly(csv_content: bytes) -> List[Dict[str, Any]]:
    try:
        text = csv_content.decode("utf-8", errors="replace")
    except Exception as exc:
        raise ValidationError(f"SolarGIS CSV: could not decode file: {exc}") from exc
    lines = text.splitlines()
    data_start_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("Month;") or stripped.startswith("Month,") or stripped == "Month":
            data_start_idx = idx
            break
    if data_start_idx is None:
        raise ValidationError(
            "SolarGIS CSV: could not find header row starting with 'Month'. "
            "Please upload the monthly climate CSV exported from SolarGIS Prospect."
        )
    data_text = "\n".join(lines[data_start_idx:])
    df = None
    last_exc = None
    for sep in (";", ","):
        try:
            candidate = pd.read_csv(StringIO(data_text), sep=sep, engine="python", on_bad_lines="warn")
            if not candidate.empty and len(candidate.columns) > 1:
                df = candidate
                break
        except Exception as exc:
            last_exc = exc
            continue
    if df is None or df.empty:
        raise ValidationError(
            f"SolarGIS CSV: could not parse CSV: {last_exc or 'unexpected format'}. "
            "Ensure you upload the monthly climate CSV from SolarGIS Prospect."
        ) from last_exc
    column_map = _detect_required_columns(df)
    for logical_name, actual_name in column_map.items():
        if logical_name in {"ghi", "dni", "dif", "temp"}:
            _validate_units(actual_name, logical_name)
    records: List[Dict[str, Any]] = []
    month_col = column_map["month"]
    ghi_col = column_map["ghi"]
    dni_col = column_map["dni"]
    dif_col = column_map["dif"]
    temp_col = column_map["temp"]
    albedo_col = column_map.get("albedo")
    wind_col = column_map.get("wind_speed_ms")
    rh_col = column_map.get("relative_humidity_percent")
    pwat_col = column_map.get("precipitable_water_kg_m2")
    prec_col = column_map.get("precipitation_mm")
    cdd_col = column_map.get("cooling_degree_days")
    hdd_col = column_map.get("heating_degree_days")
    snow_col = column_map.get("snow_days")
    for _, row in df.iterrows():
        month_raw = row.get(month_col)
        if month_raw is None or (isinstance(month_raw, float) and pd.isna(month_raw)):
            continue
        month_str = str(month_raw).strip()
        if not month_str or month_str.lower() == "year":
            continue
        record: Dict[str, Any] = {
            "month": month_str,
            "ghi": _safe_float(row.get(ghi_col)),
            "dni": _safe_float(row.get(dni_col)),
            "dif": _safe_float(row.get(dif_col)),
            "temp": _safe_float(row.get(temp_col)),
        }
        if albedo_col:
            record["albedo"] = _safe_float(row.get(albedo_col))
        if wind_col:
            record["wind_speed_ms"] = _safe_float(row.get(wind_col))
        if rh_col:
            record["relative_humidity_percent"] = _safe_float(row.get(rh_col))
        if pwat_col:
            record["precipitable_water_kg_m2"] = _safe_float(row.get(pwat_col))
        if prec_col:
            record["precipitation_mm"] = _safe_float(row.get(prec_col))
        if cdd_col:
            record["cooling_degree_days"] = _safe_float(row.get(cdd_col))
        if hdd_col:
            record["heating_degree_days"] = _safe_float(row.get(hdd_col))
        if snow_col:
            record["snow_days"] = _safe_float_optional(row.get(snow_col))
        records.append(record)
    if not records:
        raise ValidationError(
            "SolarGIS CSV: no valid monthly records found. "
            "Ensure you are using the monthly LTA PVsyst CSV from SolarGIS Prospect."
        )
    return records
