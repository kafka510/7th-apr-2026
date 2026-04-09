"""
State-aware inverter loss event generation.

Reads:
- expected power (metric='expected_power', kW) written by inverter_expected_power_service
- actual power (adapter/OEM dependent)
- inverter operating state (metric='inv_state', raw value string) from timeseries_data

Resolves raw states via loss_analytics.state_resolver (DB-backed, no cache) and writes
LossEvent rows for continuous non-normal/unknown segments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from loss_analytics.models import LossEvent
from loss_analytics.state_resolver import resolve_state_for_inverter
from main.models import timeseries_data

from .timeseries_writer import TimeseriesWriter

logger = logging.getLogger(__name__)


@dataclass
class InverterLossEventRunResult:
    inverter_id: str
    start_ts: datetime
    end_ts: datetime
    deleted_existing_events: int
    events_created: int
    points_used: int
    warnings: List[str]
    loss_metric: Optional[str] = None  # e.g. pvsyst_pr_v1_loss
    loss_points_written: int = 0


def _parse_float(value: object) -> Optional[float]:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _load_numeric_series(
    *,
    device_id: str,
    start_ts: datetime,
    end_ts: datetime,
    candidates: List[str],
) -> Dict[datetime, float]:
    """
    Load numeric series for any metric/oem_metric in candidates.
    Returns dict(ts -> float(value)).
    """
    if not candidates:
        return {}
    rows = (
        timeseries_data.objects.filter(device_id=device_id, ts__gte=start_ts, ts__lte=end_ts)
        .filter(Q(metric__in=candidates) | Q(oem_metric__in=candidates))
        .values("ts", "value")
        .order_by("ts")
    )
    out: Dict[datetime, float] = {}
    for r in rows:
        v = _parse_float(r.get("value"))
        if v is None:
            continue
        out[r["ts"]] = v
    return out


def _load_text_series(
    *,
    device_id: str,
    start_ts: datetime,
    end_ts: datetime,
    metric: str,
) -> Dict[datetime, str]:
    rows = (
        timeseries_data.objects.filter(device_id=device_id, ts__gte=start_ts, ts__lte=end_ts)
        .filter(Q(metric=metric) | Q(oem_metric=metric))
        .values("ts", "value")
        .order_by("ts")
    )
    out: Dict[datetime, str] = {}
    for r in rows:
        val = r.get("value")
        if val is None:
            continue
        s = str(val).strip()
        if not s:
            continue
        out[r["ts"]] = s
    return out


def _coalesce_actual_power_candidates() -> List[str]:
    """
    Actual power metric names vary by adapter and historical config.

    We try a small set of common candidates. You can extend this list as needed.
    """
    return [
        "actual_power",
        "active_power",
        "inv_ac_ap",
        "inverter_actual_power",
        "inverter_active_power",
        "power",
    ]


def _integrate_loss_kwh(
    *,
    timestamps: List[datetime],
    expected_kw_by_ts: Dict[datetime, float],
    actual_kw_by_ts: Dict[datetime, float],
) -> Tuple[Decimal, int]:
    """
    Integrate max(expected-actual, 0) over time using left-rectangle rule in kW.
    Returns (loss_kwh, intervals_used).
    """
    loss_kwh = Decimal("0")
    intervals_used = 0
    for i in range(len(timestamps) - 1):
        t0 = timestamps[i]
        t1 = timestamps[i + 1]
        exp = expected_kw_by_ts.get(t0)
        # If actual is missing at a timestamp, treat it as 0 (full expected is lost),
        # but only used for segments that are non-normal or missing state.
        act = actual_kw_by_ts.get(t0, 0.0)
        if exp is None:
            continue
        dt_hours = Decimal(str((t1 - t0).total_seconds())) / Decimal("3600")
        if dt_hours <= 0:
            continue
        diff_kw = Decimal(str(exp - act))
        if diff_kw <= 0:
            intervals_used += 1
            continue
        loss_kwh += diff_kw * dt_hours
        intervals_used += 1
    return loss_kwh, intervals_used


def _align_expected_actual_with_tolerance(
    *,
    expected: Dict[datetime, float],
    actual: Dict[datetime, float],
    max_delta: timedelta = timedelta(minutes=5),
) -> List[datetime]:
    """
    Align expected and actual series.

    - Fast path: if there are already >=2 exact-matching timestamps, use those (no extra work).
    - Fallback: for each expected ts, find nearest actual ts within max_delta and use the expected ts
      as the alignment point, as long as we get at least 2 aligned timestamps.
    """
    if not expected or not actual:
        return []

    exact_common = sorted(set(expected.keys()) & set(actual.keys()))
    if len(exact_common) >= 2:
        return exact_common

    exp_ts = sorted(expected.keys())
    act_ts = sorted(actual.keys())
    if not exp_ts or not act_ts:
        return []

    aligned: List[datetime] = []
    j = 0
    for t_exp in exp_ts:
        # Move pointer j to the closest actual timestamp around t_exp
        best_j = j
        best_delta = abs(act_ts[best_j] - t_exp)
        while j + 1 < len(act_ts):
            next_delta = abs(act_ts[j + 1] - t_exp)
            if next_delta <= best_delta:
                j += 1
                best_j = j
                best_delta = next_delta
            else:
                break
        if best_delta <= max_delta:
            aligned.append(t_exp)

    # Deduplicate and sort
    aligned = sorted(set(aligned))
    if len(aligned) < 2:
        return []
    return aligned


def _build_actual_at_aligned_ts(
    *,
    aligned_ts: List[datetime],
    actual: Dict[datetime, float],
    max_delta: timedelta,
) -> Dict[datetime, float]:
    """
    For each timestamp in aligned_ts, provide the actual power value.
    Uses exact match if present, else nearest actual timestamp within max_delta.
    """
    if not actual:
        return {}
    act_ts_list = sorted(actual.keys())
    result: Dict[datetime, float] = {}
    j = 0
    for t in aligned_ts:
        if t in actual:
            result[t] = actual[t]
            continue
        best_j = j
        best_delta = abs(act_ts_list[best_j] - t)
        while j + 1 < len(act_ts_list):
            next_delta = abs(act_ts_list[j + 1] - t)
            if next_delta <= best_delta:
                j += 1
                best_j = j
                best_delta = next_delta
            else:
                break
        if best_delta <= max_delta:
            result[t] = actual[act_ts_list[best_j]]
    return result


def compute_and_persist_inverter_loss_events(
    *,
    asset_code: str,
    inverter_id: str,
    start_ts: datetime,
    end_ts: datetime,
    power_model_name: Optional[str] = None,
    expected_series: Optional[Dict[datetime, float]] = None,
) -> InverterLossEventRunResult:
    """
    Create LossEvent rows for inverter_id over [start_ts, end_ts].

    Strategy:
    - Load expected_power (kW) series and actual power series.
    - Align by timestamp intersection (expected ∩ actual).
    - Read inv_state at timestamps; resolve to internal_state/is_normal.
    - Segment consecutive points by (is_normal, internal_state, oem_state_label).
    - Only persist segments where is_normal is False OR state is unknown.
    - Replace existing LossEvent rows fully contained in [start_ts, end_ts] for this inverter.
    - Write point-in-time loss (expected - actual) kW to timeseries_data as <power_model_name>_loss
      using the same staging replace-for-duration pattern as transposition.
    """
    loss_metric_name = (power_model_name or "sdm").strip() or "sdm"
    loss_metric_name = f"{loss_metric_name}_loss"
    warnings: List[str] = []
    if timezone.is_naive(start_ts):
        start_ts = timezone.make_aware(start_ts)
    if timezone.is_naive(end_ts):
        end_ts = timezone.make_aware(end_ts)
    if start_ts >= end_ts:
        raise ValueError("start_ts must be before end_ts")

    logger.info(
        "LossEvent compute start: asset_code=%s inverter_id=%s start_ts=%s end_ts=%s",
        asset_code,
        inverter_id,
        start_ts.isoformat() if start_ts else None,
        end_ts.isoformat() if end_ts else None,
    )

    if expected_series:
        expected = expected_series
    else:
        expected = _load_numeric_series(
            device_id=inverter_id,
            start_ts=start_ts,
            end_ts=end_ts,
            candidates=["expected_power"],
        )
    if not expected:
        warnings.append("No expected_power data found; skipping loss event generation.")
        return InverterLossEventRunResult(
            inverter_id=inverter_id,
            start_ts=start_ts,
            end_ts=end_ts,
            deleted_existing_events=0,
            events_created=0,
            points_used=0,
            warnings=warnings,
            loss_metric=None,
            loss_points_written=0,
        )

    actual_candidates = _coalesce_actual_power_candidates()
    actual = _load_numeric_series(
        device_id=inverter_id,
        start_ts=start_ts,
        end_ts=end_ts,
        candidates=actual_candidates,
    )
    # NOTE: actual may be missing for some or all timestamps. We still compute loss:
    # when actual is missing we treat it as 0 (expected is fully lost), but ONLY for
    # non-normal or missing state periods.

    exp_ts_sorted = sorted(expected.keys())
    act_ts_sorted = sorted(actual.keys())
    logger.info(
        "LossEvent data loaded: expected_points=%s (range %s to %s) actual_points=%s (range %s to %s)",
        len(expected),
        exp_ts_sorted[0].isoformat() if exp_ts_sorted else None,
        exp_ts_sorted[-1].isoformat() if exp_ts_sorted else None,
        len(actual),
        act_ts_sorted[0].isoformat() if act_ts_sorted else None,
        act_ts_sorted[-1].isoformat() if act_ts_sorted else None,
    )

    inv_state = _load_text_series(
        device_id=inverter_id,
        start_ts=start_ts,
        end_ts=end_ts,
        metric="inv_state",
    )

    # Base timeline for loss is expected_power timestamps.
    # This ensures we still compute loss when actual power is missing (treated as 0).
    aligned_ts = sorted(expected.keys())
    if len(aligned_ts) < 2:
        warnings.append("Not enough expected_power points to integrate loss.")
        return InverterLossEventRunResult(
            inverter_id=inverter_id,
            start_ts=start_ts,
            end_ts=end_ts,
            deleted_existing_events=0,
            events_created=0,
            points_used=len(aligned_ts),
            warnings=warnings,
            loss_metric=None,
            loss_points_written=0,
        )

    # Actual power at each expected timestamp (exact/nearest). Missing actual is treated as 0.
    actual_at_aligned = _build_actual_at_aligned_ts(
        aligned_ts=aligned_ts,
        actual=actual,
        max_delta=timedelta(minutes=5),
    )

    # Build point-wise resolved state info, aligning inv_state to expected/actual timestamps.
    # We treat inverter state as a nearest-neighbour signal with a small tolerance window.
    point_state: Dict[datetime, Tuple[bool, Optional[str], Optional[str]]] = {}
    if inv_state:
        state_ts_sorted = sorted(inv_state.keys())
    else:
        state_ts_sorted = []

    def _lookup_raw_state(ts: datetime) -> Optional[str]:
        """
        Return nearest raw inv_state around ts within a small tolerance.

        This mirrors the nearest-neighbour behaviour we use for actual power,
        so that slight acquisition offsets between state and power do not
        suppress loss detection.
        """
        if not state_ts_sorted:
            return None
        # Fast path: if exact match
        if ts in inv_state:
            return inv_state[ts]

        # Nearest-neighbour search over sorted timestamps
        lo = 0
        hi = len(state_ts_sorted) - 1
        best_idx = 0
        best_delta = abs(state_ts_sorted[0] - ts)
        while lo <= hi:
            mid = (lo + hi) // 2
            mid_ts = state_ts_sorted[mid]
            delta = abs(mid_ts - ts)
            if delta <= best_delta:
                best_delta = delta
                best_idx = mid
            if mid_ts < ts:
                lo = mid + 1
            elif mid_ts > ts:
                hi = mid - 1
            else:
                # Exact match already handled above, but keep for clarity
                best_idx = mid
                best_delta = delta
                break

        # Require state sample to be reasonably close in time (e.g. <= 5 minutes)
        if best_delta > timedelta(minutes=5):
            return None
        return inv_state[state_ts_sorted[best_idx]]

    # Cache state resolution per raw code to avoid repeated DB lookups.
    state_cache: Dict[Optional[str], Tuple[bool, Optional[str], Optional[str]]] = {}

    for ts in aligned_ts:
        raw = _lookup_raw_state(ts)
        if raw not in state_cache:
            resolved = resolve_state_for_inverter(inverter_id=inverter_id, state_value=raw) if raw else None
            if resolved is None:
                # Unknown/missing → treat as non-normal (loss should be computed)
                state_cache[raw] = (False, None, None)
            else:
                state_cache[raw] = (
                    bool(resolved.is_normal),
                    resolved.internal_state,
                    resolved.oem_state_label,
                )
        point_state[ts] = state_cache[raw]

    # Segment consecutive timestamps by state tuple
    segments: List[Tuple[int, int, bool, Optional[str], Optional[str]]] = []
    seg_start_idx = 0
    cur_key = point_state[aligned_ts[0]]
    for i in range(1, len(aligned_ts)):
        k = point_state[aligned_ts[i]]
        if k != cur_key:
            segments.append((seg_start_idx, i - 1, cur_key[0], cur_key[1], cur_key[2]))
            seg_start_idx = i
            cur_key = k
    segments.append((seg_start_idx, len(aligned_ts) - 1, cur_key[0], cur_key[1], cur_key[2]))

    events_to_create: List[LossEvent] = []
    loss_ts_rows: List[Tuple[datetime, Dict[str, float]]] = []  # (ts, {metric: loss_kw}) for timeseries_data
    for seg_idx, (start_i, end_i, is_normal, internal_state, oem_label) in enumerate(segments):
        seg_ts = aligned_ts[start_i : end_i + 1]
        seg_len = len(seg_ts)
        if is_normal:
            continue
        if seg_len < 2:
            continue
        loss_kwh, intervals_used = _integrate_loss_kwh(
            timestamps=seg_ts,
            expected_kw_by_ts=expected,
            actual_kw_by_ts=actual_at_aligned,
        )
        ev_start = seg_ts[0]
        ev_end = seg_ts[-1]
        if intervals_used == 0:
            continue
        if loss_kwh <= 0:
            continue
        events_to_create.append(
            LossEvent(
                asset_code=asset_code,
                device_id=inverter_id,
                start_ts=ev_start,
                end_ts=ev_end,
                internal_state=internal_state,
                oem_state_label=oem_label,
                loss_kwh=loss_kwh,
                is_legitimate=None,
            )
        )
        # Point-in-time loss (kW) for timeseries_data: expected - actual at each ts in this segment
        for ts in seg_ts:
            exp_kw = expected.get(ts)
            act_kw = actual_at_aligned.get(ts)
            if exp_kw is not None:
                loss_kw = max((exp_kw or 0.0) - (act_kw or 0.0), 0.0)
                loss_ts_rows.append((ts, {loss_metric_name: float(loss_kw)}))

    overlap_count = LossEvent.objects.filter(
        device_id=inverter_id,
        start_ts__lt=end_ts,
        end_ts__gt=start_ts,
    ).count()
    logger.info(
        "LossEvent persist: overlapping_existing=%s events_to_create=%s",
        overlap_count,
        len(events_to_create),
    )

    with transaction.atomic():
        # Delete any existing events for this inverter that OVERLAP [start_ts, end_ts].
        # Overlap condition: existing.start_ts < end_ts AND existing.end_ts > start_ts
        deleted, _ = LossEvent.objects.filter(
            device_id=inverter_id,
            start_ts__lt=end_ts,
            end_ts__gt=start_ts,
        ).delete()
        if events_to_create:
            LossEvent.objects.bulk_create(events_to_create, batch_size=1000)

    # Write point-in-time loss (kW) to timeseries_data using staging replace-for-duration (same as transposition)
    loss_points_written = 0
    if loss_ts_rows:
        writer = TimeseriesWriter()
        ok = writer.write_loss_range_with_staging(
            device_id=inverter_id,
            rows=loss_ts_rows,
            start_ts=start_ts,
            end_ts=end_ts,
            device_type="inverter",
            delete_existing=True,
        )
        if ok:
            loss_points_written = len(loss_ts_rows)
            logger.info(
                "Loss values written to timeseries_data: device_id=%s metric=%s points=%s start_ts=%s end_ts=%s",
                inverter_id,
                loss_metric_name,
                loss_points_written,
                start_ts.isoformat(),
                end_ts.isoformat(),
            )
        else:
            warnings.append(f"Failed to persist {loss_metric_name} to timeseries_data via staging")

    logger.info(
        "LossEvent compute done: asset_code=%s inverter_id=%s start_ts=%s end_ts=%s deleted=%s created=%s points_used=%s loss_metric=%s loss_points_written=%s",
        asset_code,
        inverter_id,
        start_ts.isoformat(),
        end_ts.isoformat(),
        int(deleted),
        len(events_to_create),
        len(aligned_ts),
        loss_metric_name,
        loss_points_written,
    )

    return InverterLossEventRunResult(
        inverter_id=inverter_id,
        start_ts=start_ts,
        end_ts=end_ts,
        deleted_existing_events=int(deleted),
        events_created=len(events_to_create),
        points_used=len(aligned_ts),
        warnings=warnings,
        loss_metric=loss_metric_name,
        loss_points_written=loss_points_written,
    )

