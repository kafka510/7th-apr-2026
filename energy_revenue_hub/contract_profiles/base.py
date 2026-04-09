"""
Base protocol for contract-type-specific billing calculations.

Each implementation maps ``assets_contracts.contract_type`` (e.g. ``sg_ppa``) to
derived ``BillingLineItem`` rows from utilities, KPIs, and contract terms.
See ``energy_revenue_hub/contract_profiles/README.md``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class ContractBillingProfile(ABC):
    """
    One profile per ``assets_contracts.contract_type`` value.

    Implementations live in sibling modules (e.g. ``sg_ppa.py``); register in
    ``contract_profiles.__init__``.
    """

    contract_type_key: str = ""

    @abstractmethod
    def compute_line_items(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build derived billing rows for a session/run.

        Args:
            context: Session, utility rows, aggregated KPIs, assets_contracts rows — shape TBD.

        Returns:
            Dict with at least ``success`` (bool), optional ``error``, ``line_items`` list.
        """
        raise NotImplementedError
