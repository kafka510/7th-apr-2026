"""
Singapore PPA–style utility billing profile (``contract_type=sg_ppa``).

Maps ``utility_invoice.account_no`` → ``assets_contracts.sp_account_no``, DC-weighted
split of ``export_energy``, KPI totals, and PPA revenue (``generation_based_ppa_rate``,
or ``virtual_ppa_rate`` if generation rate is unset).
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from energy_revenue_hub.models import UtilityInvoice
from energy_revenue_hub.services.dc_capacity import resolve_dc_capacity_kw
from energy_revenue_hub.services.kpi_billing_aggregate import aggregate_asset_kwh
from main.models import assets_contracts

from energy_revenue_hub.contract_profiles.base import ContractBillingProfile

logger = logging.getLogger(__name__)


def _norm_account(value: str) -> str:
    """Normalize SP account strings so OCR / DB formatting differences still match."""
    s = (value or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    # Spreadsheet imports may store account numbers as floats (e.g. "9311761309.0").
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s


def _invoice_ppa_rate(contract: assets_contracts) -> Any:
    """Prefer generation-based PPA; fall back to virtual PPA when the former is unset."""
    for attr in ("generation_based_ppa_rate", "virtual_ppa_rate"):
        v = getattr(contract, attr, None)
        if v is not None:
            return v
    return None


def _split_export_by_weights(total: Decimal, weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Return per-asset export kWh; last key absorbs rounding remainder."""
    tw = sum(weights.values())
    if tw <= 0:
        raise ValueError("total DC weight must be positive")
    keys = list(weights.keys())
    out: Dict[str, Decimal] = {}
    allocated = Decimal("0")
    for i, k in enumerate(keys):
        if i == len(keys) - 1:
            share = total - allocated
        else:
            share = (total * weights[k] / tw).quantize(Decimal("0.01"))
            allocated += share
        out[k] = share
    return out


class SgPpaProfile(ContractBillingProfile):
    contract_type_key = "sg_ppa"

    def compute_line_items(self, context: Dict[str, Any]) -> Dict[str, Any]:
        session = context.get("session")
        norm_assets: List[Dict[str, Any]] = context.get("norm_assets") or []
        export_fallback = Decimal(str(context.get("export_kwh_fallback") or 0))

        if session is None:
            return {"success": False, "error": "INVALID_CONTEXT", "message": "session is required."}

        raw_codes = [a.get("asset_code") or "" for a in norm_assets]
        asset_codes: List[str] = []
        seen: set[str] = set()
        for c in raw_codes:
            if c and c not in seen:
                seen.add(c)
                asset_codes.append(c)
        if not asset_codes:
            return {"success": False, "error": "NO_ASSET_CODES", "message": "Session assets need asset_code for sg_ppa billing."}

        contracts: Dict[str, assets_contracts] = {}
        for code in asset_codes:
            row = assets_contracts.objects.filter(asset_code=code).first()
            if not row:
                return {
                    "success": False,
                    "error": "MISSING_CONTRACT",
                    "message": f"No assets_contracts row for asset_code={code}.",
                }
            ct = normalize_contract_type_key(row.contract_type)
            if ct != "sg_ppa":
                return {
                    "success": False,
                    "error": "WRONG_CONTRACT_TYPE",
                    "message": f"Asset {code} is not sg_ppa (found {row.contract_type!r}).",
                }
            contracts[code] = row

        utilities = list(
            UtilityInvoice.objects.filter(billing_session=session).order_by("-created_at")
        )

        # Group assets by normalized SP account
        by_account: Dict[str, List[str]] = defaultdict(list)
        for code in asset_codes:
            acct = _norm_account(contracts[code].sp_account_no)
            if not acct:
                return {
                    "success": False,
                    "error": "MISSING_SP_ACCOUNT",
                    "message": f"assets_contracts.sp_account_no is required for sg_ppa asset {code}.",
                }
            by_account[acct].append(code)

        line_items: List[Dict[str, Any]] = []
        single_sp_account = len(by_account) == 1

        for acct_key, codes in by_account.items():
            utility = self._pick_utility(utilities, acct_key, single_sp_account=single_sp_account)

            needs_utility = any(contracts[c].requires_utility_invoice for c in codes)
            if needs_utility and utility is None:
                return {
                    "success": False,
                    "error": "NO_UTILITY_INVOICE",
                    "message": (
                        f"No utility_invoice row for billing session matching sp_account_no "
                        f"for assets: {', '.join(codes)}."
                    ),
                }

            export_total: Decimal | None = None
            if utility is not None and utility.export_energy is not None:
                export_total = Decimal(str(utility.export_energy))
            elif utility is None and not needs_utility:
                export_total = export_fallback
            elif utility is not None and utility.export_energy is None:
                if needs_utility:
                    return {
                        "success": False,
                        "error": "INVALID_UTILITY_EXPORT",
                        "message": "Utility invoice is missing export_energy for this period.",
                    }
                export_total = export_fallback
            else:
                export_total = export_fallback

            if export_total is None:
                return {
                    "success": False,
                    "error": "INVALID_EXPORT",
                    "message": "Could not determine export kWh (utility export and fallback missing).",
                }

            period_start, period_end, perr = self._resolve_period(session, utility)
            if perr:
                return {"success": False, "error": "MISSING_PERIOD", "message": perr}

            weights: Dict[str, Decimal] = {}
            for code in codes:
                w, werr = resolve_dc_capacity_kw(code)
                if werr or w is None:
                    return {"success": False, "error": "MISSING_DC", "message": werr or "DC capacity missing."}
                weights[code] = w

            try:
                export_split = _split_export_by_weights(export_total, weights)
            except ValueError as e:
                return {"success": False, "error": "INVALID_WEIGHTS", "message": str(e)}

            for code in codes:
                contract = contracts[code]
                meta = next((a for a in norm_assets if (a.get("asset_code") or "") == code), {})
                asset_name = meta.get("asset_name") or contract.asset_name or code
                export_kwh = export_split[code]
                actual_kwh = aggregate_asset_kwh(code, period_start, period_end).quantize(Decimal("0.01"))
                invoice_kwh = export_kwh
                ppa_rate = _invoice_ppa_rate(contract)
                revenue = None
                if ppa_rate is not None:
                    revenue = (invoice_kwh * Decimal(str(ppa_rate))).quantize(Decimal("0.01"))

                line_items.append(
                    {
                        "asset_name": asset_name,
                        "asset_code": code,
                        "actual_kwh": actual_kwh,
                        "export_kwh": export_kwh,
                        "invoice_kwh": invoice_kwh,
                        "ppa_rate": ppa_rate,
                        "revenue": revenue,
                    }
                )

        # Preserve session asset order
        order = {c: i for i, c in enumerate(asset_codes)}
        line_items.sort(key=lambda row: order.get(row["asset_code"], 999))

        return {"success": True, "line_items": line_items}

    def _pick_utility(
        self,
        utilities: List[UtilityInvoice],
        acct_key: str,
        *,
        single_sp_account: bool,
    ) -> UtilityInvoice | None:
        for u in utilities:
            if _norm_account(u.account_no) == acct_key:
                return u
        if len(utilities) == 1 and not (utilities[0].account_no or "").strip():
            return utilities[0]
        # One bill for the session but account_no does not match sp_account_no (OCR typo / formatting).
        if len(utilities) == 1 and single_sp_account:
            u = utilities[0]
            if _norm_account(u.account_no) != acct_key:
                logger.warning(
                    "Using single utility_invoice id=%s for session export; account_no %r did not match "
                    "assets_contracts sp_account key %r.",
                    u.id,
                    u.account_no,
                    acct_key,
                )
            return u
        return None

    def _resolve_period(
        self, session: Any, utility: UtilityInvoice | None
    ) -> Tuple[date | None, date | None, str | None]:
        ps = getattr(utility, "period_start", None) if utility else None
        pe = getattr(utility, "period_end", None) if utility else None
        if ps and pe:
            return ps, pe, None
        sd = getattr(session, "start_date", None)
        ed = getattr(session, "end_date", None)
        if sd and ed:
            return sd, ed, None
        return (
            None,
            None,
            "Set utility_invoice.period_start/end or billing session start_date/end_date.",
        )
