import re
from io import StringIO
from typing import Any, Dict

import pandas as pd

from .validators import ValidationError


def _normalize(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _find_column(df: pd.DataFrame, *candidates: str) -> str | None:
    for col in df.columns:
        n = _normalize(col)
        for c in candidates:
            if c in n or n in c:
                return col
    return None


def _find_column_regex(df: pd.DataFrame, pattern: str) -> str | None:
    for col in df.columns:
        if re.search(pattern, _normalize(col)):
            return col
    return None


def _safe_float(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def map_solargis_csv(csv_content: bytes) -> Dict[str, float]:
    try:
        text = csv_content.decode("utf-8", errors="replace")
    except Exception as e:
        raise ValidationError(f"SolarGIS CSV: could not decode file: {e}") from e

    lines = text.splitlines()
    data_start_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("Month;") or stripped.startswith("Month,") or stripped == "Month":
            data_start_idx = idx
            break
    data_text = "\n".join(lines[data_start_idx:]) if data_start_idx is not None else text

    df = None
    last_exc = None
    for sep in (";", ","):
        try:
            candidate = pd.read_csv(StringIO(data_text), sep=sep, engine="python", on_bad_lines="warn")
            if not candidate.empty and (data_start_idx is None or len(candidate.columns) > 1):
                df = candidate
                break
        except Exception as e:
            last_exc = e
            continue
    if df is None or df.empty:
        raise ValidationError(
            f"SolarGIS CSV: could not parse CSV: {last_exc or 'unexpected format'}"
        ) from last_exc

    ref_yield_col = (
        _find_column(
            df,
            "yr",
            "y_r",
            "reference_yield",
            "reference yield",
            "yield_ref",
            "h(i)_y",
        )
        or _find_column_regex(df, r"y[r_]?$|reference.*yield|yield.*ref")
    )

    reference_yield_kwh_kwp: float | None = None
    if ref_yield_col:
        vals = df[ref_yield_col].apply(_safe_float).dropna()
        reference_yield_kwh_kwp = float(vals.iloc[-1]) if len(vals) > 0 else None
        if reference_yield_kwh_kwp is None and len(df) > 0:
            reference_yield_kwh_kwp = _safe_float(df[ref_yield_col].iloc[-1])
    elif (
        poa_col := _find_column(
            df, "h(i)_m", "h(i)_y", "hi_m", "hi_y", "poa", "globinc", "gti", "inclined"
        )
        or _find_column_regex(df, r"poa|globinc|gti|inclined|irradiance")
    ):
        vals = df[poa_col].apply(_safe_float).dropna()
        reference_yield_kwh_kwp = float(vals.sum()) if len(vals) > 0 else None
    else:
        ghi_col = (
            _find_column(df, "ghi", "global_hor", "globhor", "global horizontal")
            or _find_column_regex(df, r"ghi|global.*hor|glob.*hor")
        )
        if ghi_col:
            vals = df[ghi_col].apply(_safe_float).dropna()
            reference_yield_kwh_kwp = float(vals.sum()) if len(vals) > 0 else None

    if reference_yield_kwh_kwp is None or reference_yield_kwh_kwp <= 0:
        raise ValidationError(
            "SolarGIS CSV: reference yield (kWh/kWp) could not be detected. "
            "Expected column names: Yr, Reference Yield, H(i)_y, POA, GlobInc, GTI, GHI or similar."
        )

    loss_col = (
        _find_column(
            df,
            "lc",
            "lc_tot",
            "total_loss",
            "total loss",
            "loss",
            "losses",
        )
        or _find_column_regex(df, r"^lc|total.*loss|loss.*total")
    )
    total_loss_percent = 0.0
    if loss_col:
        vals = df[loss_col].apply(_safe_float).dropna()
        if len(vals) > 0:
            total_loss_percent = float(vals.iloc[-1])
        else:
            v = _safe_float(df[loss_col].iloc[-1])
            total_loss_percent = v if v is not None else 0.0
    if total_loss_percent is None or total_loss_percent < 0:
        total_loss_percent = 0.0
    if total_loss_percent > 100:
        total_loss_percent = 100.0

    pr_col = _find_column(df, "pr", "pr_percent", "performance_ratio") or _find_column_regex(
        df, r"^pr\b|performance.*ratio"
    )
    pr_percent_from_csv: float | None = None
    if pr_col:
        vals = df[pr_col].apply(_safe_float).dropna()
        if len(vals) > 0:
            pr_percent_from_csv = float(vals.iloc[-1])

    return {
        "reference_yield_kwh_kwp": reference_yield_kwh_kwp,
        "total_loss_percent": total_loss_percent,
        "pr_percent_from_csv": pr_percent_from_csv,
    }
