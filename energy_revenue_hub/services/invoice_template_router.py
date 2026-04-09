"""
Route customer PDF layout by ``BillingSession.invoice_template_id`` (§10 Step 5).
"""

from __future__ import annotations

import re
from typing import Any, Callable, List

from energy_revenue_hub.models import BillingSession
from energy_revenue_hub.services.invoice_templates import (
    build_default_invoice_elements,
    build_matco_invoice_elements,
)
from main.models import assets_contracts

LayoutFn = Callable[[dict[str, Any], BillingSession], List[Any]]

_REGISTRY: dict[str, LayoutFn] = {
    "default": build_default_invoice_elements,
    "energy": build_default_invoice_elements,
    "matco": build_matco_invoice_elements,
    "matco_v1": build_matco_invoice_elements,
}

_CONTRACT_TO_TEMPLATE: dict[str, str] = {
    # Keep this explicit mapping easy to extend per contract type.
    "sg_ppa": "matco",
    "sg_ppa_maiora": "maiora_escalated",
}

# ReportLab layout keys (see invoice_templates/*.py builders).
# HTML / WeasyPrint keys (see invoice_weasyprint.HTML_TEMPLATE_BY_KEY).
_HTML_TEMPLATE_KEYS = frozenset({"maiora_escalated"})


def _norm_key(value: str | None) -> str:
    return re.sub(r"[\s\-]+", "_", (value or "").strip().lower())


def _session_asset_codes(session: BillingSession) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in session.asset_list or []:
        if isinstance(raw, dict):
            code = str(raw.get("asset_code") or raw.get("code") or "").strip()
        else:
            code = str(raw).strip()
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def _template_key_valid(key: str) -> bool:
    return key in _REGISTRY or key in _HTML_TEMPLATE_KEYS


def _resolve_from_contract_type(session: BillingSession) -> str:
    codes = _session_asset_codes(session)
    if not codes:
        return "default"
    rows = list(assets_contracts.objects.filter(asset_code__in=codes).values_list("contract_type", flat=True))
    if not rows:
        return "default"
    types = {_norm_key(v) for v in rows if (v or "").strip()}
    if len(types) != 1:
        return "default"
    ct = next(iter(types))
    candidate = _CONTRACT_TO_TEMPLATE.get(ct, ct)
    return candidate if _template_key_valid(candidate) else "default"


def resolve_invoice_template_id(session: BillingSession) -> str:
    # 1) Session override wins (UI/API controlled).
    tid = _norm_key(getattr(session, "invoice_template_id", None))
    if tid:
        return tid if _template_key_valid(tid) else "default"
    # 2) Otherwise derive from contract_type across session assets.
    return _resolve_from_contract_type(session)


def get_invoice_pdf_elements(template_id: str, snapshot: dict[str, Any], session: BillingSession) -> List[Any]:
    key = (template_id or "").strip().lower() or "default"
    fn = _REGISTRY.get(key, build_default_invoice_elements)
    return fn(snapshot, session)
