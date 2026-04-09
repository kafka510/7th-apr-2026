"""
Registry for contract-type billing profiles (mirrors ``data_collection.adapters`` pattern).

Resolve ``assets_contracts.contract_type`` → ``ContractBillingProfile`` implementation.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Optional, Type

from energy_revenue_hub.contract_profiles.base import ContractBillingProfile

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, Type[ContractBillingProfile]] = {}


def normalize_contract_type_key(raw: str | None) -> str:
    """
    Map DB ``assets_contracts.contract_type`` labels to profile registry keys.

    Examples: ``"SG PPA"``, ``"sg-ppa"`` → ``"sg_ppa"`` (registered key).
    """
    s = (raw or "").strip().lower()
    if not s:
        return ""
    return re.sub(r"[\s\-]+", "_", s)


def register(key: str, cls: Type[ContractBillingProfile]) -> Type[ContractBillingProfile]:
    """Register a profile class under ``key`` (e.g. ``sg_ppa``)."""
    k = normalize_contract_type_key(key)
    if k in _REGISTRY:
        logger.warning("Overwriting contract profile key=%s", k)
    _REGISTRY[k] = cls
    return cls


def get_profile(contract_type: str) -> Optional[Type[ContractBillingProfile]]:
    """Return profile class for ``contract_type``, or None if unknown."""
    k = normalize_contract_type_key(contract_type)
    if not k:
        return None
    return _REGISTRY.get(k)


def get_registered_profile_keys() -> list[str]:
    return sorted(_REGISTRY.keys())


# Built-in registrations (import after classes defined to avoid cycles)
from energy_revenue_hub.contract_profiles.sg_ppa import SgPpaProfile  # noqa: E402
from energy_revenue_hub.contract_profiles.sg_ppa_maiora import SgPpaMaioraProfile  # noqa: E402

register("sg_ppa", SgPpaProfile)
register("sg_ppa_maiora", SgPpaMaioraProfile)
