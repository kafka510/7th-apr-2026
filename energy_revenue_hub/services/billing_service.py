from __future__ import annotations

import calendar
import logging
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from energy_revenue_hub.contract_profiles import get_profile, normalize_contract_type_key
from energy_revenue_hub.models import BillingAuditLog, BillingLineItem, BillingSession, UtilityInvoice
from energy_revenue_hub.services.billing_cycle import contract_covers_billing_month
from energy_revenue_hub.workflow import transition_to
from main.models import AssetList, assets_contracts

logger = logging.getLogger(__name__)


def _err(code: str, message: str) -> Dict[str, str]:
    return {"error_code": code, "message": message}


def effective_session_asset_codes(session: BillingSession) -> list[str]:
    """Asset codes in session scope: dynamic contract/month/country filter plus explicit asset_list entries."""
    bm = getattr(session, "billing_month", None) or getattr(session, "start_date", None)
    if bm is None:
        return []
    bm_first = date(bm.year, bm.month, 1)
    session_ct = normalize_contract_type_key(getattr(session, "billing_contract_type", "") or "")
    session_country = (getattr(session, "country", "") or "").strip()

    codes: list[str] = []
    if session_ct:
        for ac in assets_contracts.objects.all():
            if normalize_contract_type_key(getattr(ac, "contract_type", None)) != session_ct:
                continue
            if not contract_covers_billing_month(ac, bm_first):
                continue
            code = (getattr(ac, "asset_code", None) or "").strip()
            if not code:
                continue
            al = AssetList.objects.filter(asset_code=code).only("country").first()
            if session_country and al and (al.country or "").strip() and (al.country or "").strip() != session_country:
                continue
            codes.append(code)

    for raw in session.asset_list or []:
        if isinstance(raw, str):
            code = raw.strip()
        elif isinstance(raw, dict):
            code = str(raw.get("asset_code") or raw.get("code") or "").strip()
        else:
            code = str(raw or "").strip()
        if code:
            codes.append(code)

    return sorted(set(c for c in codes if c))


def _billing_line_identity_from_dict(li: Dict[str, Any]) -> tuple[str, str, int]:
    code = str(li.get("asset_code") or "").strip()
    kind = str(li.get("line_kind") or "").strip()[:32]
    seg = li.get("segment_index")
    seg_key = int(seg) if seg is not None else -1
    return (code, kind, seg_key)


def _billing_line_identity_from_row(row: BillingLineItem) -> tuple[str, str, int]:
    code = (row.asset_code or "").strip()
    kind = (row.line_kind or "").strip()
    seg_key = int(row.segment_index) if row.segment_index is not None else -1
    return (code, kind, seg_key)


def _serialize_billing_line_item(row: BillingLineItem) -> Dict[str, Any]:
    return {
        "asset_name": row.asset_name,
        "asset_code": row.asset_code,
        "actual_kwh": row.actual_kwh,
        "export_kwh": row.export_kwh,
        "invoice_kwh": row.invoice_kwh,
        "ppa_rate": row.ppa_rate,
        "revenue": row.revenue,
        "sort_order": row.sort_order,
        "line_kind": row.line_kind,
        "segment_index": row.segment_index,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "leasing_year_label": row.leasing_year_label,
        "amount_excl_gst": row.amount_excl_gst,
        "line_extras_json": row.line_extras_json,
    }


def _merge_persist_billing_lines(
    session: BillingSession,
    raw_lines: List[Dict[str, Any]],
    *,
    mode: str,
    performed_by: str = "",
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Match computed lines to existing rows by (asset_code, line_kind, segment_index).
    Frozen matches: skip DB update. Unfrozen matches: update. Unmatched computed: create.
    Remaining existing unfrozen rows: delete. Remaining frozen rows: keep (not in computed set).

    Billing line items with ``is_frozen=True`` are never updated and never deleted here.
    """
    stats = {
        "frozen_skipped": 0,
        "updated": 0,
        "created": 0,
        "deleted_unfrozen": 0,
        "kept_frozen_unmatched": 0,
    }

    with transaction.atomic():
        buckets: dict[tuple[str, str, int], list[BillingLineItem]] = defaultdict(list)
        for row in session.line_items.all().order_by("sort_order", "asset_name", "id"):
            buckets[_billing_line_identity_from_row(row)].append(row)

        for li in raw_lines:
            key = _billing_line_identity_from_dict(li)
            pool = buckets[key]
            if pool:
                existing = pool.pop(0)
                if existing.is_frozen:
                    stats["frozen_skipped"] += 1
                    continue
                existing.asset_name = li["asset_name"]
                existing.asset_code = li.get("asset_code") or ""
                existing.actual_kwh = li["actual_kwh"]
                existing.export_kwh = li.get("export_kwh")
                existing.invoice_kwh = li["invoice_kwh"]
                existing.ppa_rate = li.get("ppa_rate")
                existing.revenue = li.get("revenue")
                existing.sort_order = int(li.get("sort_order") or 0)
                existing.line_kind = str(li.get("line_kind") or "")[:32]
                existing.segment_index = li.get("segment_index")
                existing.period_start = li.get("period_start")
                existing.period_end = li.get("period_end")
                existing.leasing_year_label = str(li.get("leasing_year_label") or "")[:16]
                existing.line_extras_json = (
                    li.get("line_extras_json") if isinstance(li.get("line_extras_json"), dict) else {}
                )
                existing.amount_excl_gst = li.get("amount_excl_gst")
                existing.save(
                    update_fields=[
                        "asset_name",
                        "asset_code",
                        "actual_kwh",
                        "export_kwh",
                        "invoice_kwh",
                        "ppa_rate",
                        "revenue",
                        "sort_order",
                        "line_kind",
                        "segment_index",
                        "period_start",
                        "period_end",
                        "leasing_year_label",
                        "line_extras_json",
                        "amount_excl_gst",
                    ]
                )
                stats["updated"] += 1
            else:
                BillingLineItem.objects.create(
                    billing_session=session,
                    asset_name=li["asset_name"],
                    asset_code=li.get("asset_code") or "",
                    actual_kwh=li["actual_kwh"],
                    export_kwh=li.get("export_kwh"),
                    invoice_kwh=li["invoice_kwh"],
                    ppa_rate=li.get("ppa_rate"),
                    revenue=li.get("revenue"),
                    sort_order=int(li.get("sort_order") or 0),
                    line_kind=str(li.get("line_kind") or "")[:32],
                    segment_index=li.get("segment_index"),
                    period_start=li.get("period_start"),
                    period_end=li.get("period_end"),
                    leasing_year_label=str(li.get("leasing_year_label") or "")[:16],
                    line_extras_json=li.get("line_extras_json") if isinstance(li.get("line_extras_json"), dict) else {},
                    amount_excl_gst=li.get("amount_excl_gst"),
                )
                stats["created"] += 1

        for pool in buckets.values():
            for leftover in pool:
                if leftover.is_frozen:
                    stats["kept_frozen_unmatched"] += 1
                else:
                    leftover.delete()
                    stats["deleted_unfrozen"] += 1

        transition_to(session, BillingSession.Status.REVIEWED)

    BillingAuditLog.objects.create(
        billing_session=session,
        action="GENERATE_BILLING_TABLE",
        performed_by=(performed_by or "")[:100],
        details={
            "mode": mode,
            "write": dict(stats),
            "computed_line_count": len(raw_lines),
        },
    )
    logger.info(
        "billing_table_persist_merged session_id=%s mode=%s frozen_skipped=%s updated=%s created=%s "
        "deleted_unfrozen=%s kept_frozen_unmatched=%s computed_lines=%s",
        session.id,
        mode,
        stats["frozen_skipped"],
        stats["updated"],
        stats["created"],
        stats["deleted_unfrozen"],
        stats["kept_frozen_unmatched"],
        len(raw_lines),
    )

    ordered = list(session.line_items.all().order_by("sort_order", "asset_name", "id"))
    return [_serialize_billing_line_item(r) for r in ordered], stats


def _norm_utility_account(value: str) -> str:
    """Align utility_invoice.account_no with assets_contracts.sp_account_no (OCR / formatting)."""
    s = (value or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s


def _first_day_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def _parse_billing_month_payload_only(data: Dict[str, Any]) -> date | None:
    """Parse ``billing_month`` from payload (YYYY-MM or ISO); no fallback."""
    raw = data.get("billing_month")
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        s = raw.strip()
        if len(s) >= 7 and s[4] == "-":
            try:
                y, m = int(s[:4]), int(s[5:7])
                return date(y, m, 1)
            except ValueError:
                pass
        try:
            d0 = datetime.fromisoformat(str(s)).date()
            return date(d0.year, d0.month, 1)
        except Exception:
            return None
    return None


def _parse_billing_month(data: Dict[str, Any], end_date: date) -> date:
    raw = data.get("billing_month")
    if raw is None or raw == "":
        return _first_day_of_month(end_date)
    if isinstance(raw, str):
        s = raw.strip()
        if len(s) >= 7 and s[4] == "-":
            try:
                y, m = int(s[:4]), int(s[5:7])
                return date(y, m, 1)
            except ValueError:
                pass
        try:
            d0 = datetime.fromisoformat(str(s)).date()
            return date(d0.year, d0.month, 1)
        except Exception:
            return _first_day_of_month(end_date)
    return _first_day_of_month(end_date)


def _first_asset_code_from_payload(assets: list) -> str:
    for a in assets:
        if isinstance(a, dict):
            c = (a.get("asset_code") or a.get("code") or "").strip()
            if c:
                return c
        else:
            s = str(a).strip()
            if s:
                return s
    return ""


def validate_and_create_session(request, data: Dict[str, Any]) -> Tuple[BillingSession | None, Dict[str, str] | None]:
    """
    Validate payload and create a BillingSession in FILTER_VALIDATED status.

    This is a pragmatic, minimal implementation so the billing workflow can run
    end‑to‑end without relying on external services.
    """
    country = (data.get("country") or "").strip()
    portfolio = (data.get("portfolio") or "").strip()
    assets = data.get("assets") or data.get("asset_list") or []
    start_date_raw = data.get("start_date")
    end_date_raw = data.get("end_date")

    if not country:
        return None, _err("INVALID_PAYLOAD", "country is required.")
    if not isinstance(assets, list):
        return None, _err("INVALID_PAYLOAD", "assets must be a list when provided.")

    norm_preview = _normalize_assets(assets) if assets else []
    codes_preview = _unique_asset_codes(norm_preview) if norm_preview else []

    start_date: date | None = None
    end_date: date | None = None
    if start_date_raw and end_date_raw:
        try:
            start_date = datetime.fromisoformat(str(start_date_raw)).date()
            end_date = datetime.fromisoformat(str(end_date_raw)).date()
        except Exception:
            return None, _err("INVALID_DATES", "start_date and end_date must be ISO dates (YYYY‑MM‑DD).")
        if start_date > end_date:
            return None, _err("INVALID_DATES", "start_date must be on or before end_date.")
    else:
        bm_only = _parse_billing_month_payload_only(data)
        if bm_only is None:
            return None, _err(
                "INVALID_PAYLOAD",
                "Provide start_date and end_date, or billing_month (YYYY-MM) to default period to that calendar month.",
            )
        _, last = calendar.monthrange(bm_only.year, bm_only.month)
        start_date = date(bm_only.year, bm_only.month, 1)
        end_date = date(bm_only.year, bm_only.month, last)

    assert start_date is not None and end_date is not None

    if not portfolio:
        portfolio = _portfolio_from_asset_codes(codes_preview)

    created_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""

    billing_month = _parse_billing_month(data, end_date)
    billing_contract_type = (data.get("billing_contract_type") or "").strip().lower()
    billing_contract_type = normalize_contract_type_key(billing_contract_type) if billing_contract_type else ""
    if not billing_contract_type:
        fac = _first_asset_code_from_payload(assets) or (codes_preview[0] if codes_preview else "")
        if fac:
            row = assets_contracts.objects.filter(asset_code=fac).first()
            if row and (row.contract_type or "").strip():
                billing_contract_type = normalize_contract_type_key(row.contract_type)

    # Dynamic session scope: derive assets from assets_contracts when not explicitly provided.
    if not codes_preview:
        if not billing_contract_type:
            return None, _err("INVALID_PAYLOAD", "billing_contract_type is required when assets are not provided.")
        derived: list[dict[str, Any]] = []
        for ac in assets_contracts.objects.all():
            ct = normalize_contract_type_key((getattr(ac, "contract_type", "") or "").strip().lower())
            if ct != billing_contract_type:
                continue
            if not contract_covers_billing_month(ac, billing_month):
                continue
            code = (getattr(ac, "asset_code", "") or "").strip()
            if not code:
                continue
            al = AssetList.objects.filter(asset_code=code).only("country", "asset_name").first()
            if al and (al.country or "").strip() and (al.country or "").strip() != country:
                continue
            derived.append(
                {
                    "asset_code": code,
                    "asset_name": (getattr(al, "asset_name", "") if al else "") or (getattr(ac, "asset_name", "") or code),
                }
            )
        seen: set[str] = set()
        assets = []
        for a in sorted(derived, key=lambda r: (str(r.get("asset_name") or ""), str(r.get("asset_code") or ""))):
            c = str(a.get("asset_code") or "").strip()
            if not c or c in seen:
                continue
            seen.add(c)
            assets.append(a)
        norm_preview = _normalize_assets(assets)
        codes_preview = _unique_asset_codes(norm_preview)

    if not codes_preview:
        return None, _err("NO_ASSETS", "No eligible assets found for the selected country/contract/month.")

    session_label = (data.get("session_label") or "").strip()[:200]
    if not session_label and billing_contract_type:
        session_label = f"{billing_contract_type} · {billing_month.strftime('%b %Y')}"[:200]

    if billing_contract_type:
        existing = (
            BillingSession.objects.filter(
                billing_contract_type=billing_contract_type,
                billing_month=billing_month,
            )
            .order_by("-updated_at")
            .first()
        )
        if existing:
            return (
                None,
                {
                    "error_code": "SESSION_EXISTS",
                    "message": (
                        f"A billing session already exists for contract_type={billing_contract_type} "
                        f"and billing_month={billing_month.isoformat()}."
                    ),
                    "existing_session_id": str(existing.id),
                },
            )

    session = BillingSession.objects.create(
        country=country,
        portfolio=portfolio,
        asset_list=assets,
        start_date=start_date,
        end_date=end_date,
        status=BillingSession.Status.FILTER_VALIDATED,
        created_by=created_by,
        billing_contract_type=billing_contract_type or "",
        billing_month=billing_month,
        session_label=session_label,
    )

    return session, None


def _resolve_asset_display_name(asset_code: str) -> str:
    """Prefer AssetList, then assets_contracts, for human-readable names when only a code was stored."""
    code = (asset_code or "").strip()
    if not code:
        return ""
    al = AssetList.objects.filter(asset_code=code).only("asset_name").first()
    if al and (al.asset_name or "").strip():
        return (al.asset_name or "").strip()
    ac = assets_contracts.objects.filter(asset_code=code).only("asset_name").first()
    if ac and (ac.asset_name or "").strip():
        return (ac.asset_name or "").strip()
    return ""


def _normalize_assets(asset_list: List[Any]) -> List[Dict[str, Any]]:
    """Coerce asset_list entries into dictionaries with name/code fields."""
    normalized: List[Dict[str, Any]] = []
    for a in asset_list:
        if isinstance(a, dict):
            code = str(a.get("code") or a.get("asset_code") or "").strip()
            name = str(
                a.get("name")
                or a.get("asset_name")
                or a.get("label")
                or ""
            ).strip()
            if not name:
                name = code or "Asset"
            if not code:
                code = str(a.get("asset_code") or a.get("code") or "").strip()
            if name == code or not name:
                resolved = _resolve_asset_display_name(code)
                if resolved:
                    name = resolved
        else:
            # Session create API and UI send a list of asset code strings; model JSON is "list of asset codes".
            s = str(a).strip()
            code = s
            name = _resolve_asset_display_name(s) or s or "Asset"
        normalized.append({"asset_name": name, "asset_code": code})
    return normalized


def _portfolio_from_asset_codes(codes: List[str]) -> str:
    for c in codes:
        code = str(c).strip()
        if not code:
            continue
        row = AssetList.objects.filter(asset_code=code).first()
        if row is not None and (row.portfolio or "").strip():
            return (row.portfolio or "").strip()
    return ""


def _unique_asset_codes(norm_assets: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for a in norm_assets:
        c = (a.get("asset_code") or "").strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _merge_norm_assets_from_session_utilities(
    session: BillingSession, norm_assets: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Add assets that appear on usable utility_invoice rows but are missing from the session
    scope (``asset_list`` / ``assets_contracts``-derived list). Otherwise a newly parsed PDF
    for an in-scope contract asset never participates in ``asset_code__in`` filtering.
    """
    existing = {str(a.get("asset_code") or "").strip() for a in norm_assets if str(a.get("asset_code") or "").strip()}
    extra_codes: set[str] = {
        str(x or "").strip()
        for x in UtilityInvoice.objects.filter(billing_session=session)
        .filter(Q(parse_review_status="passed") | Q(is_frozen=True))
        .exclude(invoice_number="")
        .exclude(invoice_date__isnull=True)
        .exclude(invoice_record_type="utility_unresolved_failed")
        .exclude(asset_code="")
        .values_list("asset_code", flat=True)
        if str(x or "").strip()
    }
    out = list(norm_assets)
    for code in sorted(extra_codes - existing):
        name = _resolve_asset_display_name(code) or code
        out.append({"asset_name": name, "asset_code": code})
    return out


def _generate_even_split(
    session: BillingSession,
    norm_assets: List[Dict[str, Any]],
    export_kwh: float,
    performed_by: str = "",
) -> Tuple[List[Dict[str, Any]] | None, Dict[str, str] | None, Dict[str, int] | None]:
    try:
        total_export = Decimal(str(export_kwh))
    except Exception:
        return None, _err("INVALID_EXPORT", "export_kwh must be numeric."), None

    count = len(norm_assets)
    if count <= 0:
        return None, _err("NO_ASSETS", "Billing session has no assets."), None

    per_asset = (total_export / Decimal(count)).quantize(Decimal("0.01"))
    raw_lines: List[Dict[str, Any]] = []
    for a in norm_assets:
        raw_lines.append(
            {
                "asset_name": a["asset_name"],
                "asset_code": a["asset_code"],
                "actual_kwh": per_asset,
                "export_kwh": per_asset,
                "invoice_kwh": per_asset,
                "ppa_rate": None,
                "revenue": None,
                "sort_order": 0,
                "line_kind": "",
                "segment_index": None,
                "period_start": None,
                "period_end": None,
                "leasing_year_label": "",
                "line_extras_json": {},
                "amount_excl_gst": None,
            }
        )
    items, stats = _merge_persist_billing_lines(session, raw_lines, mode="even_split", performed_by=performed_by)
    return items, None, stats


def unfreeze_billing_lines(
    session: BillingSession,
    performed_by: str = "",
    reason: str = "",
    line_item_id: Optional[str] = None,
) -> Tuple[bool, Dict[str, str] | None]:
    """
    Clear freeze flags on billing line items. With ``line_item_id``, only that row is
    unfrozen; otherwise all frozen rows in the session. Logs to ``BillingAuditLog``.
    Moves GENERATED → REVIEWED when no frozen lines remain (same as full unfreeze).
    """
    if line_item_id:
        try:
            lid = UUID(str(line_item_id).strip())
        except ValueError:
            return False, _err("BAD_LINE_ID", "Invalid line_item_id.")
        li = session.line_items.filter(id=lid).first()
        if not li:
            return False, _err("NOT_FOUND", "Billing line not found for this session.")
        if not li.is_frozen:
            return False, _err("NOT_FROZEN", "This billing line is not frozen.")

        with transaction.atomic():
            li.is_frozen = False
            li.frozen_at = None
            li.frozen_by = ""
            li.save(update_fields=["is_frozen", "frozen_at", "frozen_by"])
            if session.status == BillingSession.Status.GENERATED:
                if not session.line_items.filter(is_frozen=True).exists():
                    transition_to(session, BillingSession.Status.REVIEWED)

        BillingAuditLog.objects.create(
            billing_session=session,
            action="UNFREEZE_BILLING_LINE",
            performed_by=performed_by,
            details={"reason": reason or "", "line_item_id": str(lid)},
        )
        return True, None

    qs = session.line_items.filter(is_frozen=True)
    if not qs.exists():
        return False, _err("NOT_FROZEN", "No frozen billing lines for this session.")

    with transaction.atomic():
        session.line_items.update(is_frozen=False, frozen_at=None, frozen_by="")
        if session.status == BillingSession.Status.GENERATED:
            transition_to(session, BillingSession.Status.REVIEWED)

    BillingAuditLog.objects.create(
        billing_session=session,
        action="UNFREEZE_BILLING_LINES",
        performed_by=performed_by,
        details={"reason": reason or ""},
    )
    return True, None


def generate_billing_table(
    session: BillingSession,
    export_kwh: float,
    *,
    performed_by: str = "",
) -> Tuple[List[Dict[str, Any]] | None, Dict[str, str] | None, Dict[str, int] | None]:
    """
    Build billing line items from contract profiles when configured; otherwise
    distribute export_kwh evenly across assets (legacy).

    Persists with merge semantics: frozen rows are not overwritten; unfrozen rows are
    updated; new keys get new rows; unfrozen leftovers are removed. Returns
    ``(line_items, error, write_stats)`` where ``write_stats`` is None on error.
    """
    def fail(err: Dict[str, str]) -> Tuple[None, Dict[str, str], None]:
        code = err.get("error_code", "UNKNOWN")
        logger.info("generate_billing_table_failed session_id=%s error_code=%s", session.id, code)
        return None, err, None

    assets = session.asset_list or []
    if not assets:
        # Derive from current assets_contracts scope (dynamic).
        ct = normalize_contract_type_key((getattr(session, "billing_contract_type", "") or "").strip().lower())
        bm = getattr(session, "billing_month", None) or getattr(session, "start_date", None)
        country = (getattr(session, "country", "") or "").strip()
        derived: list[dict[str, Any]] = []
        if ct and bm:
            bm_first = date(bm.year, bm.month, 1)
            for ac in assets_contracts.objects.all():
                if normalize_contract_type_key((getattr(ac, "contract_type", "") or "").strip().lower()) != ct:
                    continue
                if not contract_covers_billing_month(ac, bm_first):
                    continue
                code = (getattr(ac, "asset_code", "") or "").strip()
                if not code:
                    continue
                al = AssetList.objects.filter(asset_code=code).only("country", "asset_name").first()
                if country and al and (al.country or "").strip() and (al.country or "").strip() != country:
                    continue
                derived.append({"asset_code": code, "asset_name": (al.asset_name if al else "") or (getattr(ac, "asset_name", "") or code)})
        assets = derived

    if not assets:
        return fail(_err("NO_ASSETS", "Billing session has no eligible assets."))

    norm_assets = _normalize_assets(assets)
    norm_assets = _merge_norm_assets_from_session_utilities(session, norm_assets)
    codes = _unique_asset_codes(norm_assets)
    if not codes:
        return fail(_err("NO_ASSETS", "Billing session assets must include asset_code for contract-based billing."))

    # Only include assets with usable utility invoice details for this session.
    usable_codes = set(
        UtilityInvoice.objects.filter(billing_session=session, asset_code__in=codes)
        .filter(Q(parse_review_status="passed") | Q(is_frozen=True))
        .exclude(invoice_number="")
        .exclude(invoice_date__isnull=True)
        .exclude(invoice_record_type="utility_unresolved_failed")
        .values_list("asset_code", flat=True)
    )

    acct_to_codes: dict[str, set[str]] = {}
    for code in codes:
        ac = assets_contracts.objects.filter(asset_code=code).only("sp_account_no").first()
        if not ac:
            continue
        sp = (getattr(ac, "sp_account_no", None) or "").strip()
        if not sp:
            continue
        acct_to_codes.setdefault(_norm_utility_account(sp), set()).add(code)

    for u in UtilityInvoice.objects.filter(billing_session=session).filter(
        Q(parse_review_status="passed") | Q(is_frozen=True)
    ).exclude(invoice_number="").exclude(invoice_date__isnull=True).exclude(
        invoice_record_type="utility_unresolved_failed"
    ):
        if (u.asset_code or "").strip():
            continue
        acct = (u.account_no or "").strip()
        if not acct:
            continue
        matched = acct_to_codes.get(_norm_utility_account(acct))
        if matched:
            usable_codes.update(matched)

    if not usable_codes:
        return fail(
            _err(
                "NO_UTILITY_DATA",
                "No usable utility invoice details for this session. For each asset you need a utility row with "
                "invoice number and date, review passed or frozen, and either asset_code set or account_no matching "
                "assets_contracts.sp_account_no for that asset.",
            )
        )
    norm_assets = [a for a in norm_assets if str(a.get("asset_code") or "").strip() in usable_codes]
    codes = _unique_asset_codes(norm_assets)

    contracts: Dict[str, assets_contracts] = {}
    for code in codes:
        row = assets_contracts.objects.filter(asset_code=code).first()
        if row:
            contracts[code] = row

    if len(contracts) != len(codes):
        missing = [c for c in codes if c not in contracts]
        return fail(
            _err(
                "MISSING_CONTRACT",
                "No assets_contracts row for: " + ", ".join(missing),
            )
        )

    contract_types = {normalize_contract_type_key(contracts[c].contract_type) for c in codes}
    if len(contract_types) > 1:
        return fail(
            _err(
                "MIXED_CONTRACT_TYPES",
                "All session assets must use the same contract_type for this billing run.",
            )
        )

    ct = next(iter(contract_types))
    if not ct:
        return fail(
            _err(
                "MISSING_CONTRACT_TYPE",
                "Set contract_type on assets_contracts for all assets in this session.",
            )
        )

    profile_cls = get_profile(ct)
    if profile_cls is None:
        logger.warning(
            "No billing profile for contract_type=%r (normalized=%r); using even split of export_kwh.",
            contracts[codes[0]].contract_type,
            ct,
        )
        es_items, es_err, es_stats = _generate_even_split(
            session, norm_assets, export_kwh, performed_by=performed_by
        )
        if es_err:
            return fail(es_err)
        try:
            logger.info(
                "generate_billing_table_ok session_id=%s mode=even_split line_count=%s write=%s",
                session.id,
                len(es_items or []),
                es_stats,
            )
        except Exception:
            pass
        return es_items, None, es_stats

    profile = profile_cls()
    result = profile.compute_line_items(
        {
            "session": session,
            "norm_assets": norm_assets,
            "export_kwh_fallback": Decimal(str(export_kwh)),
        }
    )

    if not result.get("success"):
        return fail(
            _err(
                result.get("error") or "BILLING_FAILED",
                result.get("message") or "Contract profile could not build billing lines.",
            )
        )

    raw_lines: List[Dict[str, Any]] = result.get("line_items") or []
    items, stats = _merge_persist_billing_lines(
        session, raw_lines, mode="profile", performed_by=performed_by
    )

    try:
        logger.info(
            "generate_billing_table_ok session_id=%s mode=profile line_count=%s write=%s",
            session.id,
            len(items),
            stats,
        )
    except Exception:
        pass
    return items, None, stats
