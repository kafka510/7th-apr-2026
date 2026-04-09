"""
Singapore PPA Maiora — year-split escalated rooftop (MRE) + utility export (sg_ppa_maiora).

See docs/SG_PPA_MAIORA_INVOICE_PLAN.md.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from energy_revenue_hub.contract_profiles.sg_ppa import (
    SgPpaProfile,
    _norm_account,
    _split_export_by_weights,
)
from energy_revenue_hub.models import UtilityInvoice
from energy_revenue_hub.services.dc_capacity import resolve_dc_capacity_kw
from energy_revenue_hub.services.kpi_billing_aggregate import aggregate_asset_kwh
from energy_revenue_hub.services.maiora_escalation import (
    compute_mre_rate,
    inclusive_days,
    leasing_year_index,
    split_period_by_anniversaries,
)
from main.models import assets_contracts

from energy_revenue_hub.contract_profiles.base import ContractBillingProfile


def _d(v: Any) -> Decimal:
    if v in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _q2(v: Any) -> Decimal:
    return _d(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SgPpaMaioraProfile(ContractBillingProfile):
    contract_type_key = "sg_ppa_maiora"

    def compute_line_items(self, context: Dict[str, Any]) -> Dict[str, Any]:
        session = context.get("session")
        norm_assets: List[Dict[str, Any]] = context.get("norm_assets") or []
        export_fallback = Decimal(str(context.get("export_kwh_fallback") or 0))

        if session is None:
            return {"success": False, "error": "INVALID_CONTEXT", "message": "session is required."}

        asset_codes: List[str] = []
        seen: set[str] = set()
        for a in norm_assets:
            c = (a.get("asset_code") or "").strip()
            if c and c not in seen:
                seen.add(c)
                asset_codes.append(c)
        contracts: Dict[str, assets_contracts] = {}
        for code in asset_codes:
            contract = assets_contracts.objects.filter(asset_code=code).first()
            if not contract:
                return {"success": False, "error": "MISSING_CONTRACT", "message": f"No assets_contracts for {code}."}
            if normalize_contract_type_key(contract.contract_type) != "sg_ppa_maiora":
                return {
                    "success": False,
                    "error": "WRONG_CONTRACT_TYPE",
                    "message": f"Asset {code} must have contract_type sg_ppa_maiora.",
                }
            cod = getattr(contract, "asset_cod", None)
            if not isinstance(cod, date):
                return {
                    "success": False,
                    "error": "MISSING_COD",
                    "message": f"assets_contracts.asset_cod is required for {code}.",
                }
            contracts[code] = contract

        # Group assets by normalized SP account
        by_account: Dict[str, List[str]] = {}
        for code in asset_codes:
            acct_key = _norm_account(contracts[code].sp_account_no)
            if not acct_key:
                return {
                    "success": False,
                    "error": "MISSING_SP_ACCOUNT",
                    "message": f"assets_contracts.sp_account_no is required for {code}.",
                }
            by_account.setdefault(acct_key, []).append(code)

        sg = SgPpaProfile()
        utilities = list(UtilityInvoice.objects.filter(billing_session=session).order_by("-created_at"))
        single_sp_account = len(by_account) == 1

        line_items: List[Dict[str, Any]] = []
        sort_order = 0
        for acct_key, codes in by_account.items():
            utility = sg._pick_utility(utilities, acct_key, single_sp_account=single_sp_account)
            needs_utility = any(contracts[c].requires_utility_invoice for c in codes)
            if needs_utility and utility is None:
                return {
                    "success": False,
                    "error": "NO_UTILITY_INVOICE",
                    "message": f"No utility invoice found for account group assets: {', '.join(codes)}.",
                }

            if utility is not None and utility.export_energy is not None:
                export_total = _d(utility.export_energy)
            elif utility is None and not needs_utility:
                export_total = export_fallback
            else:
                export_total = export_fallback
            if export_total is None or export_total <= 0:
                return {
                    "success": False,
                    "error": "INVALID_EXPORT",
                    "message": f"export kWh must be positive for assets: {', '.join(codes)}.",
                }

            period_start, period_end, perr = sg._resolve_period(session, utility)
            if perr:
                return {"success": False, "error": "MISSING_PERIOD", "message": perr}

            # Split account export kWh across assets by DC capacity weights
            weights: Dict[str, Decimal] = {}
            for code in codes:
                w, werr = resolve_dc_capacity_kw(code)
                if werr or w is None:
                    return {"success": False, "error": "MISSING_DC", "message": werr or f"DC capacity missing for {code}."}
                weights[code] = w
            try:
                export_split = _split_export_by_weights(export_total, weights)
            except ValueError as exc:
                return {"success": False, "error": "INVALID_WEIGHTS", "message": str(exc)}

            cost_d = _d(getattr(utility, "export_energy_cost", None))
            rec_d = _d(getattr(utility, "recurring_charges_dollars", None))
            export_payment = _q2(cost_d - rec_d)
            net_rate = Decimal("0")
            if export_total > 0:
                net_rate = (export_payment / export_total).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

            for code in codes:
                contract = contracts[code]
                cod = contract.asset_cod
                meta = next((a for a in norm_assets if (a.get("asset_code") or "") == code), {})
                asset_name = meta.get("asset_name") or contract.asset_name or code

                asset_export = _q2(export_split.get(code, Decimal("0.00")))
                actual_total = _q2(aggregate_asset_kwh(code, period_start, period_end))
                consumption_total = _q2(actual_total - asset_export)
                if consumption_total < 0:
                    consumption_total = Decimal("0")

                days_total = Decimal(str(inclusive_days(period_start, period_end)))
                if days_total <= 0:
                    return {"success": False, "error": "INVALID_PERIOD", "message": "Billing period has no days."}
                segments = split_period_by_anniversaries(cod, period_start, period_end)
                if not segments:
                    return {"success": False, "error": "NO_SEGMENTS", "message": f"Could not split billing period for {code}."}

                n_seg = len(segments)
                cons_parts: List[Decimal] = []
                exp_parts: List[Decimal] = []
                act_parts: List[Decimal] = []
                for i, (seg_start, seg_end) in enumerate(segments):
                    dseg = Decimal(str(inclusive_days(seg_start, seg_end)))
                    share = dseg / days_total
                    if i < n_seg - 1:
                        cons_parts.append(_q2(consumption_total * share))
                        exp_parts.append(_q2(asset_export * share))
                        act_parts.append(_q2(actual_total * share))
                    else:
                        cons_parts.append(_q2(consumption_total - sum(cons_parts)))
                        exp_parts.append(_q2(asset_export - sum(exp_parts)))
                        act_parts.append(_q2(actual_total - sum(act_parts)))

                allocated_export_money = Decimal("0")
                for seg_idx, ((seg_start, seg_end), cons_seg, exp_seg, actual_seg) in enumerate(
                    zip(segments, cons_parts, exp_parts, act_parts)
                ):
                    y_idx = leasing_year_index(cod, seg_start)
                    yr_label = f"YR{y_idx}"
                    mre = compute_mre_rate(contract, y_idx)
                    if mre is None:
                        return {
                            "success": False,
                            "error": "MISSING_MRE",
                            "message": f"rooftop_self_consumption_rate is required for {code}.",
                        }

                    cons_amt = _q2(_d(cons_seg) * _d(mre))
                    if seg_idx < n_seg - 1:
                        exp_amt = _q2(_d(exp_seg) * _d(net_rate))
                        allocated_export_money += _d(exp_amt)
                    else:
                        exp_amt = _q2((_d(asset_export) * _d(net_rate)) - _d(allocated_export_money))

                    line_items.append(
                        {
                            "asset_name": asset_name,
                            "asset_code": code,
                            "actual_kwh": actual_seg,
                            "export_kwh": exp_seg,
                            "invoice_kwh": cons_seg,
                            "ppa_rate": mre,
                            "revenue": cons_amt,
                            "amount_excl_gst": cons_amt,
                            "line_kind": "consumption",
                            "segment_index": seg_idx,
                            "period_start": seg_start,
                            "period_end": seg_end,
                            "leasing_year_label": yr_label,
                            "sort_order": sort_order,
                            "line_extras_json": {"leasing_year_index": y_idx, "line": "consumption", "account_key": acct_key},
                        }
                    )
                    sort_order += 1

                    line_items.append(
                        {
                            "asset_name": asset_name,
                            "asset_code": code,
                            "actual_kwh": actual_seg,
                            "export_kwh": exp_seg,
                            "invoice_kwh": exp_seg,
                            "ppa_rate": net_rate,
                            "revenue": exp_amt,
                            "amount_excl_gst": exp_amt,
                            "line_kind": "export_excess",
                            "segment_index": seg_idx,
                            "period_start": seg_start,
                            "period_end": seg_end,
                            "leasing_year_label": yr_label,
                            "sort_order": sort_order,
                            "line_extras_json": {"leasing_year_index": y_idx, "line": "export_excess", "account_key": acct_key},
                        }
                    )
                    sort_order += 1

        return {"success": True, "line_items": line_items}
