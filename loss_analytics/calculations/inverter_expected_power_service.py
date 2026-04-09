"""
Inverter expected power service (SDM-group based)
------------------------------------------------

Computes inverter-level expected power by:
1) Reading inverter tilt_configs (SDM groups: tilt/azimuth/string_count/modules_in_series)
2) Reading POA irradiance (GII) per group (synthetic device ids from transposition)
3) Running SDM expected power per group (array with Nser, Npar)
4) Summing group DC and applying inverter constraints to produce inverter AC expected power
5) Writing expected power back to timeseries_data with:
   - device_id = inverter_id
   - ts = same timestamp as GII used
   - metric = 'expected_power' (stored in kW)

Designed to be callable from both calculation-test HTTP views and Celery tasks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import logging

from django.db.models import Q

from main.models import device_list, timeseries_data, AssetList
from loss_analytics.pipeline.transposition import gii_device_id
from .power_calculation_service import PowerCalculationService
from .timeseries_writer import TimeseriesWriter
from loss_analytics.defaults import (
    get_default_ambient_temp_c,
    get_default_wind_speed_ms,
)

logger = logging.getLogger(__name__)


@dataclass
class InverterExpectedPowerResult:
    inverter_id: str
    start_ts: datetime
    end_ts: datetime
    points_written: int
    points_skipped_missing_gii: int
    groups_count: int
    group_device_ids: List[str]
    deleted_existing_points: int
    warnings: List[str]
    groups_summary: List[Dict[str, Any]]
    # When PVsyst PR model was used: DC capacity (kW) used in the formula
    dc_cap_used_kw: Optional[float] = None
    # When PVsyst PR model was used: PR (pv_syst_pr) from asset
    pr_used: Optional[float] = None
    # Power model used, e.g. 'pvsyst_pr_v1' or default SDM
    power_model_used: Optional[str] = None
    # Optional: in-memory expected power series (kW) keyed by timestamp
    expected_series: Optional[Dict[datetime, float]] = None


def _parse_group(cfg: Dict[str, Any]) -> Tuple[float, float, int, int, int, Optional[str]]:
    tilt_deg = float(cfg.get("tilt_deg"))
    azimuth_deg = float(cfg.get("azimuth_deg"))
    string_count = int(cfg.get("string_count"))
    modules_in_series = int(cfg.get("modules_in_series"))
    panel_count = int(cfg.get("panel_count"))
    orientation = cfg.get("orientation")
    return tilt_deg, azimuth_deg, string_count, modules_in_series, panel_count, orientation


def _load_timeseries(
    device_id: str,
    metric: str,
    start_ts: datetime,
    end_ts: datetime,
) -> Dict[datetime, float]:
    rows = (
        timeseries_data.objects.filter(
            device_id=device_id,
            ts__gte=start_ts,
            ts__lte=end_ts,
        )
        .filter(Q(metric=metric) | Q(oem_metric=metric))
        .values("ts", "value")
        .order_by("ts")
    )
    out: Dict[datetime, float] = {}
    for r in rows:
        try:
            out[r["ts"]] = float(r["value"])
        except (TypeError, ValueError):
            continue
    return out


def compute_and_persist_inverter_expected_power(
    *,
    asset_code: str,
    inverter_id: str,
    start_ts: datetime,
    end_ts: datetime,
    inverter_efficiency: float = 0.97,
) -> InverterExpectedPowerResult:
    """
    Compute inverter expected power and write to timeseries_data.

    Notes:
    - Uses transposed GII device ids configured via inverter.weather_device_config.irradiance_devices
      (device+metric pairs, typically synthetic ids like '<asset>_gii_<tilt>_<azimuth>' and metric='gii').
      Falls back to gii_device_id(asset_code, tilt, azimuth) per group if no irradiance_devices are configured.
    - Writes metric='expected_power' for device_id=inverter_id at the same timestamps as the base GII series.
      Values are stored in kW.
    """
    warnings: List[str] = []

    if start_ts >= end_ts:
        raise ValueError("start_ts must be before end_ts")

    inverter = device_list.objects.filter(device_id=inverter_id).first()
    if not inverter:
        raise ValueError(f"Inverter device_id '{inverter_id}' not found in device_list")

    tilt_configs = getattr(inverter, "tilt_configs", None)
    if not tilt_configs or not isinstance(tilt_configs, list):
        raise ValueError(f"Inverter '{inverter_id}' has no tilt_configs configured")

    # Pick a representative device to supply module datasheet & loss factors.
    # Preferred: a configured string under this inverter (per pv_hierarchy_views).
    rep_string = (
        device_list.objects.filter(
            parent_code=asset_code,
            device_type__icontains="string",
            device_sub_group=inverter_id,
        )
        .exclude(module_datasheet_id__isnull=True)
        .exclude(modules_in_series__isnull=True)
        .first()
    )
    if not rep_string:
        # Fallback: use inverter-level module_datasheet_id if configured, so we can still
        # run SDM even when there are no string rows available for this asset.
        if getattr(inverter, "module_datasheet_id", None) is not None:
            rep_string = inverter
            warnings.append(
                "No configured string found under inverter; falling back to inverter-level "
                "module_datasheet_id for SDM expected power."
            )
        else:
            warnings.append(
                "No configured string found under inverter and no inverter-level module_datasheet_id. "
                "Configure either at least one string with module_datasheet_id and modules_in_series, "
                "or select a PV module at inverter level."
            )
            raise ValueError(warnings[-1])

    # Weather config (irradiance/temperature/wind) is stored on inverter row (preferred).
    weather_config = getattr(inverter, "weather_device_config", None) or {}

    def _pick_first_metric(cfg_key: str) -> Optional[Tuple[str, str]]:
        items = weather_config.get(cfg_key) or []
        if not isinstance(items, list) or len(items) == 0:
            return None
        first = items[0]
        if isinstance(first, dict):
            dev = first.get("device_id")
            met = first.get("metric")
            if dev and met:
                return str(dev), str(met)
        elif isinstance(first, str):
            # Old format: device id only; metric unknown → cannot use for bulk series
            return (str(first), "")
        return None

    temp_pick = _pick_first_metric("temperature_devices")
    wind_pick = _pick_first_metric("wind_devices")

    # Prefer configured temperature/wind sensors; if unavailable or misconfigured,
    # fall back to global defaults from loss_analytics.defaults.
    temp_by_ts: Dict[datetime, float] = {}
    wind_by_ts: Dict[datetime, float] = {}

    if temp_pick and temp_pick[0] and temp_pick[1]:
        temp_device_id, temp_metric = temp_pick
        temp_by_ts = _load_timeseries(temp_device_id, temp_metric, start_ts, end_ts)
    else:
        warnings.append(
            f"Inverter '{inverter_id}' has no valid temperature_devices configured; "
            f"using default ambient temperature from loss_analytics.defaults."
        )

    if wind_pick and wind_pick[0] and wind_pick[1]:
        wind_device_id, wind_metric = wind_pick
        wind_by_ts = _load_timeseries(wind_device_id, wind_metric, start_ts, end_ts)
    elif wind_pick and wind_pick[0]:
        # Old-format string-only config; metric unknown, rely on default.
        warnings.append(
            f"Inverter '{inverter_id}' wind_devices configured in legacy format; "
            f"using default wind speed from loss_analytics.defaults."
        )

    # Parse irradiance devices (GII) configured on the inverter, order matters:
    # index i is expected to correspond to tilt_configs[i].
    irradiance_devices_cfg = weather_config.get("irradiance_devices") or []

    def _parse_device_metric_list(items: Any) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        if not isinstance(items, list):
            return out
        for entry in items:
            if isinstance(entry, dict):
                dev = entry.get("device_id")
                met = entry.get("metric")
                if dev and met:
                    out.append((str(dev), str(met)))
            elif isinstance(entry, str):
                # Old format: device id only, metric unknown → assume 'gii' for backward compatibility.
                out.append((str(entry), "gii"))
        return out

    irradiance_pairs: List[Tuple[str, str]] = _parse_device_metric_list(irradiance_devices_cfg)
    if irradiance_pairs and len(irradiance_pairs) != len(tilt_configs):
        warnings.append(
            "weather_device_config.irradiance_devices length does not match tilt_configs length; "
            "groups without an explicit irradiance device will fall back to synthetic gii_device_id(asset, tilt, azimuth)."
        )

    # Load GII per group
    groups: List[Tuple[float, float, int, int, int, Optional[str], str, Dict[datetime, float]]] = []
    group_device_ids: List[str] = []
    groups_summary: List[Dict[str, Any]] = []
    for idx, cfg in enumerate(tilt_configs):
        tilt_deg, azimuth_deg, string_count, modules_in_series, panel_count, orientation = _parse_group(cfg)
        if string_count <= 0 or modules_in_series <= 0:
            warnings.append(f"Skipping invalid group (string_count/modules_in_series must be >0): {cfg}")
            continue

        # Prefer explicit irradiance device+metric from inverter.weather_device_config.irradiance_devices
        if idx < len(irradiance_pairs):
            dev_id, metric = irradiance_pairs[idx]
            metric = metric or "gii"
            if metric.lower() != "gii":
                warnings.append(
                    f"Irradiance device {dev_id} for group {idx} uses metric='{metric}', not 'gii'; "
                    f"using it as-is for SDM input."
                )
        else:
            # Fallback: derive synthetic GII device id from asset/tilt/azimuth (legacy behavior).
            dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
            metric = "gii"

        gii_by_ts = _load_timeseries(dev_id, metric, start_ts, end_ts)
        if not gii_by_ts:
            warnings.append(
                f"No irradiance data found for group device_id={dev_id}, metric='{metric}' "
                f"(tilt={tilt_deg}, az={azimuth_deg})"
            )
        groups.append((tilt_deg, azimuth_deg, string_count, modules_in_series, panel_count, orientation, dev_id, gii_by_ts))
        group_device_ids.append(dev_id)
        groups_summary.append({
            "index": idx,
            "tilt_deg": tilt_deg,
            "azimuth_deg": azimuth_deg,
            "string_count": string_count,
            "modules_in_series": modules_in_series,
            "panel_count": panel_count,
            "orientation": orientation,
            "irradiance_device_id": dev_id,
            "irradiance_metric": metric,
            "gii_points": len(gii_by_ts),
        })

    if not groups:
        raise ValueError(f"Inverter '{inverter_id}' tilt_configs produced no valid groups")

    # Compute panel-based weights per group (for debugging / transparency)
    total_panels = sum(g[4] for g in groups if g[4] > 0)
    if total_panels > 0:
        for summary in groups_summary:
            pc = summary.get("panel_count") or 0
            summary["panel_weight"] = float(pc) / float(total_panels) if pc > 0 else 0.0
    else:
        for summary in groups_summary:
            summary["panel_weight"] = None

    # Log per-group configuration + weights for debugging/verification
    for summary in groups_summary:
        logger.info(
            "InverterExpectedPower group: inverter=%s index=%s tilt=%.2f azimuth=%.2f "
            "strings=%s modules_in_series=%s panels=%s weight=%s gii_device_id=%s metric=%s gii_points=%s",
            inverter_id,
            summary.get("index"),
            summary.get("tilt_deg"),
            summary.get("azimuth_deg"),
            summary.get("string_count"),
            summary.get("modules_in_series"),
            summary.get("panel_count"),
            summary.get("panel_weight"),
            summary.get("irradiance_device_id"),
            summary.get("irradiance_metric"),
            summary.get("gii_points"),
        )

    # Choose base timestamp set from first group that has data
    base_ts = None
    for _, _, _, _, _, _, _, gii_map in groups:
        if gii_map:
            base_ts = list(gii_map.keys())
            break
    if not base_ts:
        raise ValueError(f"No GII data available for any tilt_config group for inverter '{inverter_id}'")

    # Delete existing expected power in the window (idempotent overwrite)
    deleted_count, _ = timeseries_data.objects.filter(
        device_id=inverter_id,
        metric="expected_power",
        ts__gte=start_ts,
        ts__lte=end_ts,
    ).delete()

    power_service = PowerCalculationService()
    writer = TimeseriesWriter()
    rows_for_db: List[tuple] = []
    expected_series: Dict[datetime, float] = {}

    # Determine inverter-level power model (for PR path we use inverter as device)
    selected_model_code = power_service._select_model(inverter)
    use_pvsyst_pr = selected_model_code == "pvsyst_pr_v1"

    # If SDM would be used but rep_string is the inverter (no string with modules_in_series),
    # SDM validation can fail with "modules_in_series not configured". Prefer PR model when
    # asset has pv_syst_pr and inverter has dc_cap so the run can succeed without string config.
    if not use_pvsyst_pr and rep_string is inverter:
        inv_mis = getattr(inverter, "modules_in_series", None)
        if inv_mis is None or (isinstance(inv_mis, (int, float)) and inv_mis <= 0):
            try:
                asset = AssetList.objects.get(asset_code=asset_code)
                pr = getattr(asset, "pv_syst_pr", None)
                dc_cap = getattr(inverter, "dc_cap", None)
                if (
                    pr is not None
                    and dc_cap is not None
                    and float(pr) > 0
                    and float(dc_cap) > 0
                ):
                    use_pvsyst_pr = True
                    warnings.append(
                        "No string with modules_in_series; using PVsyst PR model (asset has "
                        "pv_syst_pr, inverter has dc_cap) instead of SDM."
                    )
            except AssetList.DoesNotExist:
                pass

    # Track DC capacity, PR, and model for PR runs (so UI and logs can display them)
    dc_cap_used_kw: Optional[float] = None
    pr_used: Optional[float] = None
    power_model_used: Optional[str] = None
    if use_pvsyst_pr:
        power_model_used = "pvsyst_pr_v1"
    else:
        power_model_used = selected_model_code or "sdm"
        dc_val = getattr(inverter, "dc_cap", None)
        if dc_val is not None:
            try:
                dc_cap_used_kw = float(dc_val)
            except (TypeError, ValueError):
                pass
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
            pr_val = getattr(asset, "pv_syst_pr", None)
            if pr_val is not None:
                pr_used = float(pr_val)
        except AssetList.DoesNotExist:
            pass
        logger.info(
            "PVsyst PR: inverter=%s dc_cap_used_kw=%s pr_used=%s",
            inverter_id, dc_cap_used_kw, pr_used,
        )

    # Panel weights for effective irradiance (PR model): weight_i = panel_count_i / total_panels
    panel_weights = []
    if use_pvsyst_pr and total_panels > 0:
        for g in groups:
            panel_count = g[4]
            panel_weights.append(float(panel_count) / float(total_panels))

    # Optional: pass representative string's module temp_coeff_pmax and noct for PR temperature correction
    pr_metadata = {}
    if use_pvsyst_pr and rep_string:
        rep_module = rep_string.get_module_datasheet() if hasattr(rep_string, "get_module_datasheet") and callable(getattr(rep_string, "get_module_datasheet", None)) else None
        if rep_module is not None:
            if getattr(rep_module, "temp_coeff_pmax", None) is not None:
                pr_metadata["temp_coeff_pmax"] = float(rep_module.temp_coeff_pmax)
            if getattr(rep_module, "noct", None) is not None:
                pr_metadata["noct"] = float(rep_module.noct)

    points_written = 0
    points_skipped_missing_gii = 0

    # Pre-resolve defaults for temperature and wind when sensor data is missing
    default_ambient = get_default_ambient_temp_c()
    default_wind = get_default_wind_speed_ms()

    # Iterate timestamps from base series.
    # SDM path requires a temperature value; when sensor data is missing, we fall back
    # to default ambient from loss_analytics.defaults. PR path can run without temp,
    # but still benefits from defaults when available.
    for ts in base_ts:
        ambient_temp = temp_by_ts.get(ts)
        if ambient_temp is None:
            ambient_temp = default_ambient

        wind_speed = wind_by_ts.get(ts) if wind_by_ts else None
        if wind_speed is None:
            wind_speed = default_wind

        if use_pvsyst_pr:
            # PVsyst PR model: one call per timestamp with effective irradiance G_eff = sum(w_i * GII_i)
            G_eff = 0.0
            any_gii = False
            for idx, (_, _, _, _, _, _, _, gii_map) in enumerate(groups):
                gii = gii_map.get(ts)
                if gii is None:
                    continue
                any_gii = True
                w = panel_weights[idx] if idx < len(panel_weights) else (1.0 / len(groups))
                G_eff += w * float(gii)
            if not any_gii:
                points_skipped_missing_gii += 1
                continue
            res = power_service.calculate_expected_power(
                device=inverter,
                irradiance=G_eff,
                ambient_temp=float(ambient_temp) if ambient_temp is not None else None,
                wind_speed=float(wind_speed) if wind_speed is not None else None,
                timestamp=ts,
                model_code="pvsyst_pr_v1",
                metadata=pr_metadata,
            )
            pdc_total = float(res.expected_power or 0.0)
            # PR model returns DC; apply inverter efficiency and AC cap
            pac = pdc_total * float(inverter_efficiency)
        else:
            # SDM (or other): per-group expected power, then sum
            pdc_total = 0.0
            any_gii = False

            for tilt_deg, azimuth_deg, string_count, modules_in_series, panel_count, orientation, dev_id, gii_map in groups:
                gii = gii_map.get(ts)
                if gii is None:
                    continue
                any_gii = True

                # Configure representative string as an "array" for SDM:
                rep_string.modules_in_series = modules_in_series
                setattr(rep_string, "strings_in_parallel", string_count)

                res = power_service.calculate_expected_power(
                    device=rep_string,
                    irradiance=float(gii),
                    ambient_temp=float(ambient_temp),
                    wind_speed=float(wind_speed) if wind_speed is not None else None,
                    timestamp=ts,
                )
                pdc_total += float(res.expected_power or 0.0)

            if not any_gii:
                points_skipped_missing_gii += 1
                continue

            pac = pdc_total * float(inverter_efficiency)

        # Apply AC capacity clipping
        ac_capacity = getattr(inverter, "ac_capacity", None)
        if ac_capacity is not None:
            try:
                pac = min(pac, float(ac_capacity) * 1000.0)  # assume ac_capacity stored in kW
            except (TypeError, ValueError):
                pass

        # Persist expected power in kW (single metric)
        exp_kw = float(pac) / 1000.0
        rows_for_db.append((ts, {"expected_power": exp_kw}))
        expected_series[ts] = exp_kw

    # Bulk persist via session-scoped TEMP staging table (one COPY)
    if rows_for_db:
        ok = writer.write_loss_range_with_staging(
            device_id=inverter_id,
            rows=rows_for_db,
            start_ts=start_ts,
            end_ts=end_ts,
            device_type="inverter",
            delete_existing=False,  # already deleted above; keep deleted_count accurate
        )
        if ok:
            points_written = len(rows_for_db)
        else:
            warnings.append("Failed to persist expected_power via staging write")

    return InverterExpectedPowerResult(
        inverter_id=inverter_id,
        start_ts=start_ts,
        end_ts=end_ts,
        points_written=points_written,
        points_skipped_missing_gii=points_skipped_missing_gii,
        groups_count=len(groups),
        group_device_ids=group_device_ids,
        deleted_existing_points=deleted_count,
        warnings=warnings,
        groups_summary=groups_summary,
        dc_cap_used_kw=dc_cap_used_kw,
        pr_used=pr_used,
        power_model_used=power_model_used,
        expected_series=expected_series or None,
    )

