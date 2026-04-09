"""
State resolver for inverter operating states.

This module provides small, DB-backed helpers (no cache) to resolve raw OEM
state values into normalized internal_state / is_normal flags using the
device_operating_state table and AssetAdapterConfig.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from data_collection.models import AssetAdapterConfig, DeviceOperatingState
from main.models import device_list

import logging

logger = logging.getLogger(__name__)


@dataclass
class ResolvedState:
    adapter_id: str
    device_type: str
    state_value: str
    internal_state: Optional[str]
    is_normal: bool
    oem_state_label: Optional[str]
    fault_code: Optional[str]


def _normalize_state_value(value: object) -> str:
    """
    Normalize raw state value to the string form stored in DeviceOperatingState.

    Many OEMs send numeric state codes as floats (e.g. 512.0). Our mappings are
    typically configured as plain strings like "512". To make this robust we:
    - Treat int-like floats/decimals as integers ("512.0" → "512")
    - Otherwise, fall back to the stripped string representation.
    """
    if value is None:
        return ""

    # Try numeric normalization first (also for string inputs):
    # - "512.0" -> "512"
    # - 512.0   -> "512"
    # - "40960" -> "40960"
    try:
        as_float = float(value)  # type: ignore[arg-type]
        if as_float.is_integer():
            return str(int(as_float))
    except (TypeError, ValueError):
        # Not a numeric-looking value; fall back to string conversion
        pass

    # Fallback: plain stripped string
    return str(value).strip()


def resolve_state_for_adapter(
    *,
    adapter_id: str,
    device_type: str,
    state_value: object,
) -> Optional[ResolvedState]:
    """
    Resolve (adapter_id, device_type, state_value) to a DeviceOperatingState row.

    Returns ResolvedState or None when no mapping exists.
    """
    state_str = _normalize_state_value(state_value)
    if not adapter_id or not device_type or not state_str:
        return None

    # First try an exact (adapter_id, device_type, state_value) match.
    try:
        row = DeviceOperatingState.objects.get(
            adapter_id=adapter_id,
            device_type=device_type,
            state_value=state_str,
        )
    except DeviceOperatingState.DoesNotExist:
        # Fallback: allow shared mappings per adapter when device_type-specific
        # row is not configured (e.g. only 'string_inv' rows exist but we are
        # resolving an inverter-level state).
        row = (
            DeviceOperatingState.objects.filter(
                adapter_id=adapter_id,
                state_value=state_str,
            )
            .order_by("device_type", "id")
            .first()
        )
        if row is None:
            return None

    return ResolvedState(
        adapter_id=row.adapter_id,
        device_type=row.device_type,
        state_value=row.state_value,
        internal_state=row.internal_state,
        is_normal=bool(row.is_normal),
        oem_state_label=row.oem_state_label,
        fault_code=row.fault_code,
    )


def resolve_state_for_inverter(
    *,
    inverter_id: str,
    state_value: object,
) -> Optional[ResolvedState]:
    """
    Resolve raw state for a specific inverter to internal_state / is_normal.

    Looks up:
    - inverter in device_list
    - asset's adapter via AssetAdapterConfig
    - mapping in DeviceOperatingState
    """
    inverter = device_list.objects.filter(device_id=inverter_id).first()
    if not inverter:
        return None

    asset_code = inverter.parent_code
    if not asset_code:
        return None

    adapter_cfg = (
        AssetAdapterConfig.objects.filter(asset_code=asset_code, enabled=True)
        .order_by("id")
        .first()
    )
    if not adapter_cfg:
        return None

    adapter_id = adapter_cfg.adapter_id
    device_type = inverter.device_type or ""

    state_str = _normalize_state_value(state_value)
    return resolve_state_for_adapter(
        adapter_id=adapter_id,
        device_type=device_type,
        state_value=state_str,
    )

