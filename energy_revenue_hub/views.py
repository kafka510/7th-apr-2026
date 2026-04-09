"""
Energy Revenue Hub views and lightweight API endpoints.
"""

from __future__ import annotations

import base64
import io
import json
import uuid
import os
import re
import tempfile
from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal
from typing import Any
import logging

from accounts.decorators import feature_required
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from celery.result import AsyncResult
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

from energy_revenue_hub.models import (
    Adjustment,
    AssetGeneration,
    BillingAuditLog,
    BillingInvoicePdf,
    BillingLineItem,
    BillingSession,
    GeneratedInvoice,
    InvoiceFieldCorrection,
    MeterReading,
    ParsedInvoice,
    Payment,
    Penalty,
    UtilityInvoice,
)
from energy_revenue_hub.services.billing_service import (
    effective_session_asset_codes,
    generate_billing_table,
    unfreeze_billing_lines,
    validate_and_create_session,
)
from energy_revenue_hub.services.hybrid_engine import parse_multiple_invoices, run_hybrid_engine
from energy_revenue_hub.services.invoice_parse_persistence import (
    persist_parsed_and_utility_for_session,
    sharepoint_upload_utility_batch,
)
from energy_revenue_hub.services.utility_invoice_rates import (
    build_anomaly_flag_json,
    compute_calculated_unit_rate,
    compute_net_unit_rate,
)
from energy_revenue_hub.services.sharepoint_service import (
    build_utility_invoice_remote_path,
    download_file_from_sharepoint_graph,
    get_sharepoint_mirror_root,
    upload_file_to_sharepoint,
)
from energy_revenue_hub.tasks import (
    erh_generate_billing_table_task,
    erh_generate_invoice_task,
    erh_generate_line_item_invoice_task,
    erh_parse_invoice_files_task,
)
from energy_revenue_hub.workflow import transition_to
from energy_revenue_hub.services.billing_cycle import (
    contract_covers_billing_month,
    warning_message_for_line,
)
from energy_revenue_hub.services.pdf_security_check import validate_pdf_security
from energy_revenue_hub.contract_profiles import get_registered_profile_keys, normalize_contract_type_key
from main.models import AssetList, assets_contracts, log_loss_task_completed, log_loss_task_enqueued, log_loss_task_started
from main.permissions import user_has_capability

logger = logging.getLogger(__name__)


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


# Session list + utility-invoices list omit large OCR / parse JSON blobs; GET ``/api/utility-invoices/<id>/`` returns full fields.
_UTILITY_INVOICE_BLOB_FIELD_NAMES = frozenset({"raw_text", "parse_page_scores_json", "parse_block_confidence_json"})
_UTILITY_INVOICE_VALUES_FULL = (
    "id",
    "invoice_record_type",
    "billing_session_id",
    "billing_invoice_pdf_id",
    "parsed_invoice_id",
    "invoice_number",
    "account_no",
    "asset_code",
    "vendor_key",
    "invoice_date",
    "period_start",
    "period_end",
    "currency_code",
    "total_amount",
    "export_energy",
    "export_energy_cost",
    "recurring_charges_dollars",
    "unit_rate",
    "calculated_unit_rate",
    "anomaly_flag",
    "current_charges_excl_gst",
    "net_unit_rate",
    "gst_rate",
    "raw_text",
    "parse_extraction_path",
    "parse_document_confidence_score",
    "parse_document_confidence_level",
    "parse_page_scores_json",
    "parse_block_confidence_json",
    "loss_calculation_task_id",
    "has_pending_merge",
    "is_frozen",
    "frozen_at",
    "frozen_by",
    "parse_review_status",
    "parse_review_passed_at",
    "parse_review_passed_by",
    "created_at",
    "updated_at",
)
_UTILITY_INVOICE_VALUES_LEAN = tuple(f for f in _UTILITY_INVOICE_VALUES_FULL if f not in _UTILITY_INVOICE_BLOB_FIELD_NAMES)


def _json_safe(value: Any) -> Any:
    """Make nested structures JSON-serializable (e.g. audit ``details``)."""
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return value


def _ok(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    return JsonResponse({"success": True, **payload}, status=status)


def _err(message: str, status: int = 400, code: str = "BAD_REQUEST") -> JsonResponse:
    return JsonResponse({"success": False, "error": code, "message": message}, status=status)


def _require_capability(request: HttpRequest, capability: str) -> JsonResponse | None:
    if not user_has_capability(getattr(request, "user", None), capability):
        return _err("Restricted access. Contact your administrator.", status=403, code="FORBIDDEN")
    return None


def _json_body(request: HttpRequest) -> dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _require_superuser(request: HttpRequest) -> JsonResponse | None:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_superuser", False):
        return _err("Only superusers can perform this action.", status=403, code="FORBIDDEN")
    return None


def _upload_summary_rows(session: BillingSession) -> list[dict[str, Any]]:
    rows = list(
        BillingInvoicePdf.objects.filter(billing_session=session)
        .order_by("uploaded_at", "display_order")
        .values(
            "id",
            "original_filename",
            "transfer_status",
            "parse_status",
            "parse_error",
            "parse_started_at",
            "parse_completed_at",
            "parse_elapsed_seconds",
            "parse_summary_status",
            "billing_cycle_aligned",
            "billing_cycle_warning_message",
            "pending_utility_patch_json",
            "frozen_data_changed",
            "local_file_exists",
            "local_file_size_bytes",
            "security_status",
            "security_reason_code",
            "security_reason_message",
            "sharepoint_remote_path",
            "uploaded_at",
        )
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        row = {k: _to_primitive(v) for k, v in r.items()}
        row["billing_invoice_pdf_id"] = str(row.pop("id"))
        row["download_original"] = f"/energy-revenue-hub/api/billing-invoice-pdfs/{row['billing_invoice_pdf_id']}/download-original/"
        out.append(row)
    return out


def _pdf_ids_referenced_by_session_utilities(session: BillingSession) -> set[str]:
    """Billing PDF ids that back at least one utility row for this session."""
    out: set[str] = set()
    for x in UtilityInvoice.objects.filter(billing_session=session).values_list("billing_invoice_pdf_id", flat=True):
        if x:
            out.add(str(x))
    return out


_BAD_SECURITY_STATUSES = frozenset({"failed", "rejected", "quarantine", "quarantined"})


def _session_generation_blockers(session: BillingSession, upload_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    pdf_ids_used = _pdf_ids_referenced_by_session_utilities(session)
    pending_merge_count = UtilityInvoice.objects.filter(billing_session=session, has_pending_merge=True).count()
    if pending_merge_count:
        blockers.append(
            {
                "code": "PENDING_MERGE",
                "count": pending_merge_count,
                "message": f"{pending_merge_count} utility invoice(s) pending merge review.",
            }
        )
    cycle_mismatch_count = sum(
        1
        for r in upload_summary
        if str(r.get("billing_invoice_pdf_id") or "") in pdf_ids_used
        and not bool(r.get("billing_cycle_aligned", True))
    )
    if cycle_mismatch_count:
        blockers.append(
            {
                "code": "BILLING_CYCLE_MISMATCH",
                "count": cycle_mismatch_count,
                "message": f"{cycle_mismatch_count} utility-linked upload(s) do not match billing cycle.",
            }
        )
    pending_assets_count = _expected_pending_utility_assets_payload(session)["coverage_summary"]["pending_assets_count"]
    if pending_assets_count:
        blockers.append(
            {
                "code": "PENDING_UTILITY_ASSETS",
                "count": pending_assets_count,
                "message": f"{pending_assets_count} asset(s) pending utility data.",
            }
        )
    security_block_count = sum(
        1
        for r in upload_summary
        if str(r.get("billing_invoice_pdf_id") or "") in pdf_ids_used
        and str(r.get("security_status") or "").strip().lower() in _BAD_SECURITY_STATUSES
    )
    if security_block_count:
        blockers.append(
            {
                "code": "SECURITY_BLOCK",
                "count": security_block_count,
                "message": f"{security_block_count} utility-linked file(s) blocked by security validation.",
            }
        )
    return blockers


# Session-level warnings (e.g. missing utility for some assets) must not block PDF generation for ready assets (ERH plan §4.6).
_INVOICE_HARD_BLOCKER_CODES = frozenset({"PENDING_MERGE", "BILLING_CYCLE_MISMATCH", "SECURITY_BLOCK"})


def _generation_readiness_from_upload(session: BillingSession, upload_summary: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = _session_generation_blockers(session, upload_summary)
    invoice_hard = [b for b in blockers if b.get("code") in _INVOICE_HARD_BLOCKER_CODES]
    return {
        "ready": not blockers,
        "blockers": blockers,
        "invoice_generation_allowed": not invoice_hard,
        "invoice_generation_blockers": invoice_hard,
    }


def _line_item_invoice_hard_blockers(session: BillingSession, row: BillingLineItem) -> list[dict[str, Any]]:
    """
    Hard gates for generating a PDF for one billing line. Uses only utility rows and PDFs
    tied to that line (asset_code and/or line_extras_json.account_key), so unrelated
    session uploads do not block row-level generation.
    """
    blockers: list[dict[str, Any]] = []
    asset_code = str(row.asset_code or "").strip()
    extras = row.line_extras_json if isinstance(row.line_extras_json, dict) else {}
    acct = str(extras.get("account_key") or "").strip()
    if not asset_code and not acct:
        blockers.append(
            {
                "code": "NO_LINE_SCOPE",
                "message": "This billing line has no asset code or account_key to match utility data.",
            }
        )
        return blockers

    uq = UtilityInvoice.objects.filter(billing_session=session)
    if asset_code and acct:
        uis = list(uq.filter(Q(asset_code=asset_code) | Q(account_no=acct)))
    elif asset_code:
        uis = list(uq.filter(asset_code=asset_code))
    else:
        uis = list(uq.filter(account_no=acct))

    if not uis:
        blockers.append(
            {
                "code": "NO_UTILITY_FOR_LINE",
                "message": "No utility invoice row matches this billing line (asset/account).",
            }
        )
        return blockers

    if any(ui.has_pending_merge for ui in uis):
        blockers.append(
            {
                "code": "PENDING_MERGE",
                "message": "Utility invoice for this line is pending merge review.",
            }
        )

    upload_summary = _upload_summary_rows(session)
    summary_by_pdf = {
        str(r.get("billing_invoice_pdf_id") or ""): r
        for r in upload_summary
        if str(r.get("billing_invoice_pdf_id") or "").strip()
    }
    pdf_ids = {str(ui.billing_invoice_pdf_id) for ui in uis if ui.billing_invoice_pdf_id}
    for pid in pdf_ids:
        r = summary_by_pdf.get(pid)
        if r and not bool(r.get("billing_cycle_aligned", True)):
            blockers.append(
                {
                    "code": "BILLING_CYCLE_MISMATCH",
                    "message": "Source utility PDF for this line does not match the billing cycle.",
                }
            )
            break

    for pid in pdf_ids:
        r = summary_by_pdf.get(pid)
        if r and str(r.get("security_status") or "").strip().lower() in _BAD_SECURITY_STATUSES:
            blockers.append(
                {
                    "code": "SECURITY_BLOCK",
                    "message": "Source utility PDF for this line failed security validation.",
                }
            )
            break

    return blockers


_UTILITY_INVOICE_CORRECTION_FIELDS: tuple[str, ...] = (
    "invoice_number",
    "account_no",
    "asset_code",
    "vendor_key",
    "currency_code",
    "invoice_date",
    "period_start",
    "period_end",
    "total_amount",
    "export_energy",
    "export_energy_cost",
    "recurring_charges_dollars",
    "unit_rate",
    "current_charges_excl_gst",
    "gst_rate",
    "net_unit_rate",
)


def _field_value_for_correction(v: Any) -> str:
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return str(v.isoformat())
    if isinstance(v, Decimal):
        return str(v)
    return str(v)


def _persist_utility_invoice_field_corrections(ui: UtilityInvoice, previous: dict[str, Any]) -> None:
    pid = getattr(ui, "parsed_invoice_id", None)
    if not pid:
        return
    vendor = (getattr(ui, "vendor_key", None) or "unknown")[:100]
    for fn in _UTILITY_INVOICE_CORRECTION_FIELDS:
        if fn not in previous:
            continue
        old_v = _field_value_for_correction(previous.get(fn))
        new_v = _field_value_for_correction(getattr(ui, fn, None))
        if old_v == new_v:
            continue
        InvoiceFieldCorrection.objects.create(
            invoice_id=pid,
            field_name=fn[:100],
            original_value=old_v[:4000],
            corrected_value=new_v[:4000],
            vendor=vendor,
        )


def _expected_pending_utility_assets_payload(session: BillingSession) -> dict[str, Any]:
    bm = getattr(session, "billing_month", None) or getattr(session, "start_date", None)
    if bm is None:
        return {"pending_assets": [], "coverage_summary": {"expected_utility_assets_count": 0, "ready_assets_count": 0, "pending_assets_count": 0}}
    bm_first = date(bm.year, bm.month, 1)
    session_ct = normalize_contract_type_key(getattr(session, "billing_contract_type", "") or "")
    session_country = (getattr(session, "country", "") or "").strip()

    # Derive expected assets from current assets_contracts scope (dynamic) and include any superuser overrides
    # stored on session.asset_list.
    expected_codes: list[str] = []
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
            expected_codes.append(code)

    # Superuser override list: union with derived.
    for raw in (session.asset_list or []):
        code = ""
        if isinstance(raw, str):
            code = raw.strip()
        elif isinstance(raw, dict):
            code = str(raw.get("asset_code") or raw.get("code") or "").strip()
        if code:
            expected_codes.append(code)

    expected_codes = sorted(set(c for c in expected_codes if c))
    ready_codes = set(
        str(v).strip()
        for v in UtilityInvoice.objects.filter(billing_session=session).values_list("asset_code", flat=True)
        if str(v or "").strip()
    )
    pending_assets = [
        {
            "asset_code": code,
            "asset_name": code,
            "coverage_status": "pending_utility",
            "reason_code": "MISSING_UTILITY_INVOICE",
            "reason_message": f"Expected utility data missing for asset {code}",
        }
        for code in expected_codes
        if code not in ready_codes
    ]
    coverage_summary = {
        "expected_utility_assets_count": len(expected_codes),
        "ready_assets_count": sum(1 for code in expected_codes if code in ready_codes),
        "pending_assets_count": len(pending_assets),
    }
    return {"pending_assets": pending_assets, "coverage_summary": coverage_summary}


def _generation_readiness_payload(session: BillingSession) -> dict[str, Any]:
    upload_summary = _upload_summary_rows(session)
    return _generation_readiness_from_upload(session, upload_summary)


def _serialize_session(session: BillingSession) -> dict[str, Any]:
    return {
        "id": str(session.id),
        "country": session.country,
        "portfolio": session.portfolio,
        "asset_list": session.asset_list,
        "invoice_template_id": getattr(session, "invoice_template_id", "") or "",
        "billing_extras_json": _json_safe(getattr(session, "billing_extras_json", None) or {}),
        "billing_contract_type": getattr(session, "billing_contract_type", "") or "",
        "billing_month": _to_primitive(getattr(session, "billing_month", None)),
        "session_label": getattr(session, "session_label", "") or "",
        "start_date": _to_primitive(session.start_date),
        "end_date": _to_primitive(session.end_date),
        "status": session.status,
        "created_by": session.created_by,
        "created_at": _to_primitive(session.created_at),
        "updated_at": _to_primitive(session.updated_at),
    }


def _parse_date(v: Any) -> date | None:
    if not v:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v).date()
        except ValueError:
            return None
    return None


def _parse_decimal(v: Any) -> Decimal | None:
    if v in (None, ""):
        return None


def _resolve_target_utility_invoice_for_pdf(row: BillingInvoicePdf, patch: dict[str, Any]) -> UtilityInvoice | None:
    util_id = str(patch.get("utility_invoice_id") or "").strip()
    if util_id:
        ui = UtilityInvoice.objects.filter(id=util_id).first()
        if ui:
            return ui
    ui = (
        UtilityInvoice.objects.filter(billing_invoice_pdf=row, has_pending_merge=True)
        .order_by("-updated_at")
        .first()
    )
    if ui:
        return ui
    return UtilityInvoice.objects.filter(billing_invoice_pdf=row).order_by("-updated_at").first()


def _apply_patch_to_utility_invoice(ui: UtilityInvoice, patch: dict[str, Any]) -> None:
    decimal_fields = {
        "total_amount",
        "export_energy",
        "export_energy_cost",
        "recurring_charges_dollars",
        "unit_rate",
        "current_charges_excl_gst",
        "gst_rate",
        "parse_document_confidence_score",
    }
    date_fields = {"invoice_date", "period_start", "period_end"}
    passthrough_fields = {"parse_page_scores_json", "parse_block_confidence_json", "anomaly_flag"}
    str_fields = {
        "invoice_number",
        "account_no",
        "asset_code",
        "vendor_key",
        "currency_code",
        "raw_text",
        "parse_extraction_path",
        "parse_document_confidence_level",
    }
    for key, value in patch.items():
        if key in decimal_fields:
            setattr(ui, key, _parse_decimal(value))
        elif key in date_fields:
            setattr(ui, key, _parse_date(value))
        elif key in passthrough_fields:
            setattr(ui, key, value if isinstance(value, (dict, list)) else {})
        elif key in str_fields:
            setattr(ui, key, str(value or ""))


def _compute_billing_cycle_alignment(session: BillingSession | None, parsed_result: dict[str, Any]) -> tuple[bool, str]:
    if session is None:
        return True, ""
    period_end = _parse_date(parsed_result.get("period_end"))
    bm = getattr(session, "billing_month", None) or getattr(session, "start_date", None)
    if period_end is None or bm is None:
        return True, ""
    window_start = date(bm.year, bm.month, 1)
    _, last_day = monthrange(bm.year, bm.month)
    window_end = date(bm.year, bm.month, last_day)
    if window_start <= period_end <= window_end:
        return True, ""
    msg = (
        f"Invoice period ends {period_end.isoformat()}; this session is for "
        f"{window_start.isoformat()} to {window_end.isoformat()}."
    )
    return False, msg


def _line_item_asset_key(line_item_row: dict[str, Any]) -> str:
    return str(line_item_row.get("asset_code") or "").strip() or str(line_item_row.get("asset_name") or "").strip() or "asset"


def _generated_asset_key(generated_row: dict[str, Any]) -> str:
    snap = generated_row.get("invoice_snapshot_json") or {}
    if isinstance(snap, dict):
        return str(snap.get("asset_code") or "").strip() or str(snap.get("asset_name") or "").strip()
    return ""


@login_required
@feature_required("energy_revenue_hub")
def index_view(request: HttpRequest) -> HttpResponse:
    """Main Energy Revenue Hub page - React app."""
    return render(request, "energy_revenue_hub/index_react.html")


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def eligible_billing_assets_api(request: HttpRequest) -> JsonResponse:
    """
    Assets from ``assets_contracts`` whose normalized ``contract_type`` matches the request,
    restricted to ``AssetList.country`` and optionally overlapping ``billing_month`` (YYYY-MM).
    """
    deny = _require_capability(request, "erh.session.create")
    if deny:
        return deny
    country = (request.GET.get("country") or "").strip()
    ct_raw = (request.GET.get("contract_type") or "").strip()
    bm_raw = (request.GET.get("billing_month") or "").strip()
    if not country or not ct_raw:
        return _err("country and contract_type are required.", status=400, code="INVALID_QUERY")
    ct_norm = normalize_contract_type_key(ct_raw)
    if not ct_norm:
        return _err("contract_type is invalid.", status=400, code="INVALID_QUERY")

    bm: date | None = None
    if bm_raw:
        if len(bm_raw) >= 7 and bm_raw[4] == "-":
            try:
                y, m = int(bm_raw[:4]), int(bm_raw[5:7])
                bm = date(y, m, 1)
            except ValueError:
                bm = None
        if bm is None:
            bm = _parse_date(bm_raw)
            if bm is not None:
                bm = date(bm.year, bm.month, 1)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    country_l = country.strip().lower()

    for ac in assets_contracts.objects.only(
        "asset_code",
        "asset_name",
        "contract_type",
        "contract_start_date",
        "contract_end_date",
    ).iterator(chunk_size=2000):
        if normalize_contract_type_key(getattr(ac, "contract_type", None)) != ct_norm:
            continue
        if bm is not None and not contract_covers_billing_month(ac, bm):
            continue
        code = (getattr(ac, "asset_code", None) or "").strip()
        if not code or code in seen:
            continue
        al = AssetList.objects.filter(asset_code=code).only("country", "portfolio", "asset_name").first()
        if al is None:
            continue
        if (al.country or "").strip().lower() != country_l:
            continue
        seen.add(code)
        out.append(
            {
                "asset_code": code,
                "asset_name": (al.asset_name or ac.asset_name or code).strip(),
                "portfolio": (al.portfolio or "").strip(),
                "country": (al.country or "").strip(),
                "contract_type": (ac.contract_type or "").strip(),
            }
        )

    out.sort(key=lambda r: (r.get("asset_name") or r.get("asset_code") or "").lower())
    return _ok({"assets": out})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def contract_profile_keys_api(request: HttpRequest) -> JsonResponse:
    """Registered billing contract profile keys (``assets_contracts.contract_type`` normalization targets)."""
    deny = _require_capability(request, "erh.session.view")
    if deny:
        return deny
    return _ok({"contract_profile_keys": get_registered_profile_keys()})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def sessions_list_api(request: HttpRequest) -> JsonResponse:
    deny = _require_capability(request, "erh.session.view")
    if deny:
        return deny
    qs = BillingSession.objects.all()
    ct = (request.GET.get("billing_contract_type") or "").strip()
    if ct:
        qs = qs.filter(billing_contract_type=normalize_contract_type_key(ct))
    bm = (request.GET.get("billing_month") or "").strip()
    if bm:
        d0: date | None = None
        if len(bm) == 7 and bm[4] == "-":
            try:
                y, m = int(bm[:4]), int(bm[5:7])
                d0 = date(y, m, 1)
            except ValueError:
                d0 = None
        else:
            d0 = _parse_date(bm)
            if d0 is not None:
                d0 = date(d0.year, d0.month, 1)
        if d0 is not None:
            qs = qs.filter(billing_month=d0)
    country = (request.GET.get("country") or "").strip()
    if country:
        qs = qs.filter(country=country)
    portfolio = (request.GET.get("portfolio") or "").strip()
    if portfolio:
        qs = qs.filter(portfolio=portfolio)
    st = (request.GET.get("status") or "").strip()
    if st:
        qs = qs.filter(status=st)
    q = (request.GET.get("q") or "").strip()
    if q:
        from django.db.models import Q

        qs = qs.filter(
            Q(session_label__icontains=q)
            | Q(portfolio__icontains=q)
            | Q(country__icontains=q)
            | Q(id__icontains=q)
        )
    limit = 200
    try:
        limit = min(int(request.GET.get("limit") or 200), 500)
    except ValueError:
        limit = 200
    sessions = list(qs.order_by("-billing_month", "-updated_at")[:limit])
    return _ok({"sessions": [_serialize_session(s) for s in sessions]})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def sessions_create_api(request: HttpRequest) -> JsonResponse:
    deny = _require_capability(request, "erh.session.create")
    if deny:
        return deny
    payload = _json_body(request)
    session, error = validate_and_create_session(request, payload)
    if error:
        if error.get("error_code") == "SESSION_EXISTS":
            return JsonResponse(
                {
                    "success": False,
                    "error": "SESSION_EXISTS",
                    "message": error.get("message", "Billing session already exists."),
                    "existing_session_id": error.get("existing_session_id", ""),
                },
                status=409,
            )
        return _err(error.get("message", "Failed to create session"), status=400, code=error.get("error_code", "INVALID_PAYLOAD"))
    return _ok({"session": _serialize_session(session)}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def session_add_asset_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    session = get_object_or_404(BillingSession, id=session_id)
    payload = _json_body(request)
    asset_code = str(payload.get("asset_code") or "").strip()
    if not asset_code:
        return _err("asset_code is required.", status=400, code="INVALID_PAYLOAD")
    asset_name = str(payload.get("asset_name") or "").strip() or asset_code
    current = session.asset_list or []
    normalized = []
    seen: set[str] = set()
    for raw in current:
        if isinstance(raw, dict):
            code = str(raw.get("asset_code") or raw.get("code") or "").strip()
            name = str(raw.get("asset_name") or raw.get("name") or code or "").strip()
        else:
            code = str(raw or "").strip()
            name = code
        if not code:
            continue
        if code in seen:
            continue
        seen.add(code)
        normalized.append({"asset_code": code, "asset_name": name or code})
    if asset_code not in seen:
        normalized.append({"asset_code": asset_code, "asset_name": asset_name})
    session.asset_list = normalized
    session.save(update_fields=["asset_list", "updated_at"])
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    BillingAuditLog.objects.create(
        billing_session=session,
        action="ADD_SESSION_ASSET",
        performed_by=performed_by,
        details={"asset_code": asset_code, "asset_name": asset_name},
    )
    return _ok({"session": _serialize_session(session), "added": asset_code})


def _session_patch_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.session.edit")
    if deny:
        return deny
    from energy_revenue_hub.contract_profiles import normalize_contract_type_key

    session = get_object_or_404(BillingSession, id=session_id)
    payload = _json_body(request)
    updated_fields: list[str] = []
    if "invoice_template_id" in payload:
        session.invoice_template_id = str(payload.get("invoice_template_id") or "")[:64]
        updated_fields.append("invoice_template_id")
    if "billing_extras_json" in payload:
        ex = payload.get("billing_extras_json")
        if ex is not None and not isinstance(ex, dict):
            return _err("billing_extras_json must be a JSON object.", status=400, code="INVALID_PAYLOAD")
        session.billing_extras_json = ex if ex is not None else {}
        updated_fields.append("billing_extras_json")
    if "billing_contract_type" in payload:
        raw = str(payload.get("billing_contract_type") or "").strip()
        session.billing_contract_type = normalize_contract_type_key(raw) if raw else ""
        updated_fields.append("billing_contract_type")
    if "billing_month" in payload:
        bm = payload.get("billing_month")
        if bm is None or bm == "":
            session.billing_month = None
        else:
            s = str(bm).strip()
            if len(s) == 7 and s[4] == "-":
                try:
                    y, m = int(s[:4]), int(s[5:7])
                    session.billing_month = date(y, m, 1)
                except ValueError:
                    return _err("Invalid billing_month (use YYYY-MM).", status=400, code="INVALID_PAYLOAD")
            else:
                d = _parse_date(s)
                if d is None:
                    return _err("Invalid billing_month.", status=400, code="INVALID_PAYLOAD")
                session.billing_month = date(d.year, d.month, 1)
        updated_fields.append("billing_month")
    if "session_label" in payload:
        session.session_label = str(payload.get("session_label") or "")[:200]
        updated_fields.append("session_label")
    if not updated_fields:
        return _err(
            "Provide invoice_template_id, billing_extras_json, billing_contract_type, billing_month, and/or session_label.",
            status=400,
            code="NO_CHANGES",
        )
    session.save(update_fields=updated_fields + ["updated_at"])
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    BillingAuditLog.objects.create(
        billing_session=session,
        action="UPDATE_BILLING_SESSION",
        performed_by=performed_by,
        details={"fields": updated_fields},
    )
    return _ok({"session": _serialize_session(session)})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "PATCH"])
def session_detail_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.session.view")
    if deny:
        return deny
    if request.method == "PATCH":
        return _session_patch_api(request, session_id)
    session = get_object_or_404(BillingSession, id=session_id)
    effective_assets = effective_session_asset_codes(session)
    line_items = list(
        session.line_items.values(
            "id",
            "asset_name",
            "asset_code",
            "actual_kwh",
            "export_kwh",
            "invoice_kwh",
            "ppa_rate",
            "revenue",
            "is_frozen",
            "frozen_at",
            "frozen_by",
            "sort_order",
            "line_kind",
            "segment_index",
            "period_start",
            "period_end",
            "leasing_year_label",
            "line_extras_json",
            "amount_excl_gst",
        )
    )
    parsed = list(
        session.parsed_invoices.values(
            "id",
            "invoice_number",
            "invoice_date",
            "export_energy",
            "created_at",
        )
    )
    generated = list(
        session.generated_invoices.values(
            "id",
            "file_path",
            "version",
            "generated_at",
            "sharepoint_upload_status",
            "sharepoint_upload_error",
            "invoice_snapshot_json",
        )
    )
    utility_invoices = list(
        UtilityInvoice.objects.filter(billing_session=session).values(*_UTILITY_INVOICE_VALUES_LEAN)
    )
    pdf_name_by_id: dict[str, str] = {
        str(r["id"]): str(r.get("original_filename") or "").strip()
        for r in BillingInvoicePdf.objects.filter(billing_session=session).values("id", "original_filename")
    }
    for row in utility_invoices:
        pdf_id = str(row.get("billing_invoice_pdf_id") or "").strip()
        row["source_original_filename"] = pdf_name_by_id.get(pdf_id, "")
        row["is_unresolved"] = not bool(str(row.get("invoice_number") or "").strip()) or not bool(
            row.get("invoice_date")
        )
        row["download_original"] = (
            f"/energy-revenue-hub/api/billing-invoice-pdfs/{pdf_id}/download-original/" if pdf_id else ""
        )
    payments = list(
        Payment.objects.filter(invoice__billing_session=session).values(
            "payment_id",
            "asset_number",
            "invoice_id",
            "payment_due",
            "payment_date",
            "payment_paid",
            "payment_pending",
            "payment_status",
        )
    )
    meter_readings = list(
        MeterReading.objects.filter(device_id__in=effective_assets).order_by("-read_at").values(
            "id",
            "device_id",
            "read_at",
            "cumulative_value",
            "source",
            "data_quality",
            "reading_role",
            "period_label",
            "delta_kwh_for_period",
            "notes",
            "created_at",
        )
    )
    asset_generation = list(
        AssetGeneration.objects.filter(asset_number__in=effective_assets).order_by("-month").values(
            "id",
            "asset_number",
            "month",
            "grid_export_kwh",
            "pv_generation_kwh",
            "rooftop_self_consumption_kwh",
            "bess_dispatch_kwh",
        )
    )
    penalties = list(
        Penalty.objects.filter(asset_number__in=effective_assets).values(
            "id", "asset_number", "penalty_type", "penalty_rate", "penalty_charges"
        )
    )
    adjustments = list(
        Adjustment.objects.filter(asset_number__in=effective_assets).values(
            "id", "asset_number", "adjustment_type", "adjustment_amount", "adjustment_reason"
        )
    )
    audit_logs = list(
        BillingAuditLog.objects.filter(billing_session=session).order_by("-timestamp").values(
            "id",
            "action",
            "performed_by",
            "timestamp",
            "details",
        )
    )

    for collection in (line_items, parsed, generated, utility_invoices, payments, meter_readings, asset_generation, penalties, adjustments):
        for row in collection:
            for key, val in list(row.items()):
                row[key] = _to_primitive(val)
            if "id" in row and row["id"] is not None:
                row["id"] = str(row["id"])
            if "invoice_id" in row and row["invoice_id"] is not None:
                row["invoice_id"] = str(row["invoice_id"])

    for row in generated:
        if "invoice_snapshot_json" in row and row["invoice_snapshot_json"] is not None:
            row["invoice_snapshot_json"] = _json_safe(row["invoice_snapshot_json"])
        row["download"] = f"/energy-revenue-hub/api/generated-invoices/{row.get('id')}/download/"

    upload_summary = _upload_summary_rows(session)
    readiness = _generation_readiness_from_upload(session, upload_summary)
    conflicts: list[dict[str, Any]] = []
    for r in upload_summary:
        patch = r.get("pending_utility_patch_json")
        has_patch = isinstance(patch, dict) and bool(patch)
        is_frozen_change = bool(r.get("frozen_data_changed"))
        if not has_patch and not is_frozen_change:
            continue
        conflicts.append(
            {
                "billing_invoice_pdf_id": r.get("billing_invoice_pdf_id"),
                "conflict_type": "frozen_data_changed" if is_frozen_change else "pending_merge",
                "source_original_filename": r.get("original_filename") or "",
                "pending_utility_patch_json": patch if has_patch else {},
                "frozen_data_changed": is_frozen_change,
            }
        )
    expected_payload = _expected_pending_utility_assets_payload(session)
    pending_assets = expected_payload["pending_assets"]
    coverage_summary = expected_payload["coverage_summary"]

    for row in audit_logs:
        for key, val in list(row.items()):
            row[key] = _to_primitive(val)
        if row.get("id") is not None:
            row["id"] = str(row["id"])
        if "details" in row:
            row["details"] = _json_safe(row.get("details"))

    latest_generated_by_asset: dict[str, dict[str, Any]] = {}
    for g in generated:
        key = _generated_asset_key(g)
        if key and key not in latest_generated_by_asset:
            latest_generated_by_asset[key] = g

    latest_failed_by_asset: dict[str, str] = {}
    for log in audit_logs:
        if str(log.get("action") or "") != "INVOICE_PDF_GENERATION_FAILED":
            continue
        details = log.get("details") or {}
        if not isinstance(details, dict):
            continue
        key = str(details.get("asset_code") or "").strip() or str(details.get("asset_name") or "").strip()
        msg = str(details.get("error") or "").strip()
        if key and msg and key not in latest_failed_by_asset:
            latest_failed_by_asset[key] = msg

    for row in line_items:
        asset_key = _line_item_asset_key(row)
        latest_generated = latest_generated_by_asset.get(asset_key)
        latest_failed = latest_failed_by_asset.get(asset_key, "")
        if latest_generated:
            row["invoice_generation_status"] = "generated"
            row["invoice_generation_error"] = ""
            row["latest_generated_invoice_id"] = str(latest_generated.get("id") or "")
            row["latest_generated_invoice_download"] = latest_generated.get("download") or ""
        elif latest_failed:
            row["invoice_generation_status"] = "failed"
            row["invoice_generation_error"] = latest_failed
            row["latest_generated_invoice_id"] = ""
            row["latest_generated_invoice_download"] = ""
        else:
            row["invoice_generation_status"] = "pending"
            row["invoice_generation_error"] = ""
            row["latest_generated_invoice_id"] = ""
            row["latest_generated_invoice_download"] = ""

    # For sg_ppa_maiora UX, merge matching export_excess metrics onto each consumption row for
    # convenience, but still return every billing line from the DB (including export_excess rows).
    # Hiding export rows made PDF generation / freeze checks look inconsistent (e.g. 4 lines in DB
    # vs 2 visible rows for the same asset + utility PDF).
    if str(getattr(session, "billing_contract_type", "") or "").strip() == "sg_ppa_maiora":
        export_rows = [r for r in line_items if str(r.get("line_kind") or "") == "export_excess"]
        export_by_key: dict[tuple[str, Any], dict[str, Any]] = {}
        for ex in export_rows:
            k = (
                str(ex.get("asset_code") or ex.get("asset_name") or "").strip(),
                ex.get("segment_index"),
            )
            export_by_key[k] = ex
        merged_display: list[dict[str, Any]] = []
        for row in line_items:
            lk = str(row.get("line_kind") or "")
            r = dict(row)
            if lk == "consumption":
                k = (
                    str(r.get("asset_code") or r.get("asset_name") or "").strip(),
                    r.get("segment_index"),
                )
                ex = export_by_key.get(k)
                r["export_invoice_kwh"] = ex.get("invoice_kwh") if ex else None
                r["export_rate"] = ex.get("ppa_rate") if ex else None
                r["export_amount"] = ex.get("revenue") if ex else None
            merged_display.append(r)
        line_items = merged_display

    as_of = timezone.now().date()
    bm_sess = getattr(session, "billing_month", None)
    ct_sess = getattr(session, "billing_contract_type", "") or ""
    for row in line_items:
        ac = str(row.get("asset_code") or "").strip()
        lk = str(row.get("line_kind") or "").strip()
        row["billing_cycle_warning"] = (
            warning_message_for_line(
                asset_code=ac,
                session_contract_type=ct_sess,
                billing_month_first=bm_sess,
                as_of=as_of,
            )
            if ac and (not lk or lk == "consumption")
            else ""
        )

    from energy_revenue_hub.services.invoice_service import resolve_billing_invoice_pdf_id_for_line_row

    for row in line_items:
        pdf_id = resolve_billing_invoice_pdf_id_for_line_row(session, row)
        row["utility_billing_invoice_pdf_id"] = pdf_id
        ac = str(row.get("asset_code") or "").strip() or str(row.get("asset_name") or "").strip() or "asset"
        row["line_group_key"] = f"{ac}|{pdf_id or 'none'}"

    def _line_item_display_sort_key(r: dict[str, Any]) -> tuple:
        gk = str(r.get("line_group_key") or "")
        so = r.get("sort_order")
        seg = r.get("segment_index")
        ly = str(r.get("leasing_year_label") or "")
        rid = str(r.get("id") or "")
        try:
            so_n = int(so) if so is not None and str(so).strip() != "" else 0
        except (TypeError, ValueError):
            so_n = 0
        try:
            seg_n = int(seg) if seg is not None and str(seg).strip() != "" else 0
        except (TypeError, ValueError):
            seg_n = 0
        return (gk, so_n, seg_n, ly, rid)

    line_items.sort(key=_line_item_display_sort_key)

    return _ok(
        {
            "session": _serialize_session(session),
            "line_items": line_items,
            "parsed_invoices": parsed,
            "generated_invoices": generated,
            "utility_invoices": utility_invoices,
            "payments": payments,
            "meter_readings": meter_readings,
            "asset_generation": asset_generation,
            "penalties": penalties,
            "adjustments": adjustments,
            "billing_audit_logs": audit_logs,
            "upload_summary": upload_summary,
            "conflicts": conflicts,
            "generation_blockers": readiness["blockers"],
            "invoice_generation_allowed": readiness["invoice_generation_allowed"],
            "invoice_generation_blockers": readiness["invoice_generation_blockers"],
            "coverage_summary": coverage_summary,
            "pending_assets": pending_assets,
            "can_delete": bool(getattr(request.user, "is_superuser", False)) if hasattr(request, "user") else False,
            "can_unfreeze_billing_lines": user_has_capability(getattr(request, "user", None), "erh.workflow.unfreeze"),
        }
    )


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def generate_billing_table_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.generate.billing_table")
    if deny:
        return deny
    session = get_object_or_404(BillingSession, id=session_id)
    payload = _json_body(request)
    export_kwh = payload.get("export_kwh", 0)
    run_async = bool(payload.get("async"))
    if run_async:
        async_result = erh_generate_billing_table_task.delay(
            str(session.id),
            float(export_kwh or 0),
            user_id=getattr(request.user, "id", None),
        )
        log_loss_task_enqueued(
            task_id=async_result.id,
            task_name="erh_generate_billing_table",
            user=getattr(request, "user", None),
        )
        return _ok({"task_id": async_result.id, "status": "queued"}, status=202)

    task_id = f"erh-billing-table-{uuid.uuid4()}"
    log_loss_task_enqueued(
        task_id=task_id,
        task_name="erh_generate_billing_table",
        user=getattr(request, "user", None),
    )
    log_loss_task_started(task_id=task_id)
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    items, error, write_stats = generate_billing_table(
        session, export_kwh=export_kwh, performed_by=performed_by
    )
    if error:
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=error.get("message", "Failed to generate billing table"),
        )
        err_body: dict[str, Any] = {
            "success": False,
            "error": error.get("error_code", "BILLING_TABLE_FAILED"),
            "message": error.get("message", "Failed to generate billing table"),
        }
        return JsonResponse(err_body, status=400)
    log_loss_task_completed(task_id=task_id, success=True)
    session.refresh_from_db()
    # Helpful UX metadata: which assets were included vs skipped (pending utility data).
    included = sorted({str(r.get("asset_code") or "").strip() for r in (items or []) if str(r.get("asset_code") or "").strip()})
    # If session scope is larger than included, treat remainder as skipped for this run.
    scope = effective_session_asset_codes(session)
    skipped = [c for c in scope if c and c not in set(included)]
    ok_payload: dict[str, Any] = {
        "line_items": items or [],
        "status": session.status,
        "task_id": task_id,
        "included_asset_codes": included,
        "skipped_asset_codes": skipped,
        "included_assets_count": len(included),
        "skipped_assets_count": len(skipped),
        "billing_table_write": write_stats or {},
    }
    return _ok(ok_payload)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def recalculate_lines_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.generate.billing_table")
    if deny:
        return deny
    """Same inputs and behaviour as generate-table; distinct route for UX after config/metadata changes."""
    session = get_object_or_404(BillingSession, id=session_id)
    payload = _json_body(request)
    export_kwh = payload.get("export_kwh", 0)
    run_async = bool(payload.get("async"))
    if run_async:
        async_result = erh_generate_billing_table_task.delay(
            str(session.id),
            float(export_kwh or 0),
            user_id=getattr(request.user, "id", None),
        )
        log_loss_task_enqueued(
            task_id=async_result.id,
            task_name="erh_recalculate_billing_lines",
            user=getattr(request, "user", None),
        )
        return _ok({"task_id": async_result.id, "status": "queued"}, status=202)

    task_id = f"erh-recalculate-lines-{uuid.uuid4()}"
    log_loss_task_enqueued(
        task_id=task_id,
        task_name="erh_recalculate_billing_lines",
        user=getattr(request, "user", None),
    )
    log_loss_task_started(task_id=task_id)
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    items, error, write_stats = generate_billing_table(
        session, export_kwh=export_kwh, performed_by=performed_by
    )
    if error:
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=error.get("message", "Failed to recalculate billing lines"),
        )
        err_body2: dict[str, Any] = {
            "success": False,
            "error": error.get("error_code", "BILLING_TABLE_FAILED"),
            "message": error.get("message", "Failed to recalculate billing lines"),
        }
        return JsonResponse(err_body2, status=400)
    log_loss_task_completed(task_id=task_id, success=True)
    session.refresh_from_db()
    included = sorted({str(r.get("asset_code") or "").strip() for r in (items or []) if str(r.get("asset_code") or "").strip()})
    scope = effective_session_asset_codes(session)
    skipped = [c for c in scope if c and c not in set(included)]
    rec_ok: dict[str, Any] = {
        "line_items": items or [],
        "status": session.status,
        "task_id": task_id,
        "included_asset_codes": included,
        "skipped_asset_codes": skipped,
        "included_assets_count": len(included),
        "skipped_assets_count": len(skipped),
        "billing_table_write": write_stats or {},
    }
    return _ok(rec_ok)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def generate_invoice_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.generate.pdf")
    if deny:
        return deny
    session = get_object_or_404(BillingSession, id=session_id)
    readiness = _generation_readiness_payload(session)
    if not readiness.get("invoice_generation_allowed", True):
        hard = readiness.get("invoice_generation_blockers") or []
        msgs = " | ".join(str(b.get("message") or b.get("code") or "") for b in hard).strip()
        return _err(
            msgs or "Invoice generation blocked: resolve pending blockers first.",
            status=400,
            code="GENERATION_BLOCKED",
        )
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    payload = _json_body(request)
    run_async = bool(payload.get("async"))
    if run_async:
        async_result = erh_generate_invoice_task.delay(
            str(session.id),
            performed_by,
            user_id=getattr(request.user, "id", None),
        )
        log_loss_task_enqueued(
            task_id=async_result.id,
            task_name="erh_generate_invoice",
            user=getattr(request, "user", None),
        )
        return _ok({"task_id": async_result.id, "status": "queued"}, status=202)

    task_id = f"erh-generate-invoice-{uuid.uuid4()}"
    log_loss_task_enqueued(
        task_id=task_id,
        task_name="erh_generate_invoice",
        user=getattr(request, "user", None),
    )
    log_loss_task_started(task_id=task_id)
    try:
        from energy_revenue_hub.services.invoice_service import generate_invoice_pdf
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", "dependency")
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=f"Missing dependency: {missing}",
        )
        return _err(
            f"Missing dependency: {missing}. Install reportlab to enable PDF generation.",
            status=500,
            code="MISSING_DEPENDENCY",
        )

    generated_batch, failures, error = generate_invoice_pdf(session, performed_by=performed_by)
    if error:
        log_loss_task_completed(
            task_id=task_id,
            success=False,
            error_message=error.get("message", "Invoice generation failed"),
        )
        return _err(error.get("message", "Invoice generation failed"), status=400, code=error.get("error_code", "INVOICE_GENERATION_FAILED"))
    log_loss_task_completed(task_id=task_id, success=True)

    first = (generated_batch or [None])[0]
    attempted = sorted(
        set(
            [str(g.invoice_snapshot_json.get("asset_code") or "").strip() for g in (generated_batch or []) if getattr(g, "invoice_snapshot_json", None)]
            + [str(f.get("asset_code") or "").strip() for f in (failures or []) if str(f.get("asset_code") or "").strip()]
        )
    )
    scope = effective_session_asset_codes(session)
    skipped = [c for c in scope if c and c not in set(attempted)]
    return _ok(
        {
            "generated_invoice": {
                "id": str(first.id) if first else "",
                "file_path": first.file_path if first else "",
                "version": first.version if first else 0,
                "generated_at": _to_primitive(first.generated_at) if first else None,
            },
            "generated_invoices": [
                {
                    "id": str(g.id),
                    "file_path": g.file_path,
                    "version": g.version,
                    "generated_at": _to_primitive(g.generated_at),
                }
                for g in (generated_batch or [])
            ],
            "failed_invoices": failures or [],
            "included_asset_codes": attempted,
            "skipped_asset_codes": skipped,
            "included_assets_count": len(attempted),
            "skipped_assets_count": len(skipped),
            "status": session.status,
            "task_id": task_id,
            "generation_blockers": readiness["blockers"],
        }
    )


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def generation_readiness_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.session.view")
    if deny:
        return deny
    session = get_object_or_404(BillingSession, id=session_id)
    payload = _generation_readiness_payload(session)
    return _ok(payload)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def download_original_billing_invoice_pdf_api(request: HttpRequest, billing_invoice_pdf_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.download.source_pdf")
    if deny:
        return deny
    row = get_object_or_404(BillingInvoicePdf, id=billing_invoice_pdf_id)
    filename = os.path.basename(str(row.original_filename or "").strip()) or f"{row.id}.pdf"

    # Prefer local path if still present.
    local_path = str(row.local_temp_path or "").strip()
    if local_path and os.path.exists(local_path):
        return FileResponse(open(local_path, "rb"), as_attachment=True, filename=filename)

    # Fallback to SharePoint mirror path in mirror mode.
    remote_rel = str(row.sharepoint_remote_path or "").strip().replace("\\", "/").lstrip("/")
    if remote_rel:
        mirror_abs = os.path.join(get_sharepoint_mirror_root(), remote_rel.replace("/", os.sep))
        if os.path.exists(mirror_abs):
            return FileResponse(open(mirror_abs, "rb"), as_attachment=True, filename=filename)

    return _err("Original invoice file not available for download.", status=404, code="NOT_FOUND")


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def resolve_billing_invoice_pdf_merge_api(request: HttpRequest, billing_invoice_pdf_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.utility_invoice.edit")
    if deny:
        return deny
    row = get_object_or_404(BillingInvoicePdf, id=billing_invoice_pdf_id)
    payload = _json_body(request)
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"apply", "reject"}:
        return _err("action must be 'apply' or 'reject'.", status=400, code="INVALID_PAYLOAD")
    patch = row.pending_utility_patch_json if isinstance(row.pending_utility_patch_json, dict) else {}

    ui = _resolve_target_utility_invoice_for_pdf(row, patch)
    if action == "apply":
        if not patch:
            return _err("No pending merge patch found for this file.", status=400, code="NO_PENDING_PATCH")
        if not ui:
            return _err("Linked utility invoice not found for merge apply.", status=404, code="UTILITY_NOT_FOUND")
        _apply_patch_to_utility_invoice(ui, patch)
        ui.has_pending_merge = False
        ui.billing_invoice_pdf = row
        ui.save()

    if ui:
        ui.has_pending_merge = False
        ui.save(update_fields=["has_pending_merge"])
    row.pending_utility_patch_json = {}
    row.frozen_data_changed = False
    row.save(update_fields=["pending_utility_patch_json", "frozen_data_changed"])

    if row.billing_session_id:
        BillingAuditLog.objects.create(
            billing_session_id=row.billing_session_id,
            action="UTILITY_INVOICE_MERGE_RESOLVED",
            performed_by=getattr(request.user, "username", "") if hasattr(request, "user") else "",
            details={
                "billing_invoice_pdf_id": str(row.id),
                "action": action,
                "utility_invoice_id": str(ui.id) if ui else "",
            },
        )
    return _ok({"status": "resolved", "action": action, "billing_invoice_pdf_id": str(row.id), "utility_invoice_id": str(ui.id) if ui else ""})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def generate_line_item_invoice_api(request: HttpRequest, line_item_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.generate.pdf")
    if deny:
        return deny
    row = get_object_or_404(BillingLineItem, id=line_item_id)
    session = row.billing_session
    line_hard = _line_item_invoice_hard_blockers(session, row)
    if line_hard:
        msgs = " | ".join(str(b.get("message") or b.get("code") or "") for b in line_hard).strip()
        return _err(msgs or "Invoice generation blocked.", status=400, code="GENERATION_BLOCKED")
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    payload = _json_body(request)
    run_async = bool(payload.get("async", True))
    if run_async:
        async_result = erh_generate_line_item_invoice_task.delay(
            str(line_item_id),
            performed_by,
            user_id=getattr(request.user, "id", None),
        )
        log_loss_task_enqueued(
            task_id=async_result.id,
            task_name="erh_generate_line_item_invoice",
            user=getattr(request, "user", None),
        )
        return _ok({"task_id": async_result.id, "status": "queued"}, status=202)

    task_id = f"erh-generate-line-invoice-{uuid.uuid4()}"
    log_loss_task_enqueued(
        task_id=task_id,
        task_name="erh_generate_line_item_invoice",
        user=getattr(request, "user", None),
    )
    log_loss_task_started(task_id=task_id)
    try:
        from energy_revenue_hub.services.invoice_service import generate_invoice_pdf, line_items_sharing_utility_pdf_with
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", "dependency")
        log_loss_task_completed(task_id=task_id, success=False, error_message=f"Missing dependency: {missing}")
        return _err(
            f"Missing dependency: {missing}. Install reportlab to enable PDF generation.",
            status=500,
            code="MISSING_DEPENDENCY",
        )

    expanded = line_items_sharing_utility_pdf_with(session, row)
    expanded_ids = [str(li.id) for li in expanded]
    logger.info(
        "erh_generate_line_item_invoice start line_item_id=%s session_id=%s expanded_count=%s expanded_ids=%s",
        line_item_id,
        str(session.id),
        len(expanded_ids),
        expanded_ids,
    )
    generated_batch, failures, error = generate_invoice_pdf(
        session,
        performed_by=performed_by,
        target_line_item_ids=expanded_ids,
    )
    if error:
        log_loss_task_completed(task_id=task_id, success=False, error_message=error.get("message", "Invoice generation failed"))
        logger.warning(
            "erh_generate_line_item_invoice hard_error line_item_id=%s session_id=%s error=%s",
            line_item_id,
            str(session.id),
            error,
        )
        return _err(error.get("message", "Invoice generation failed"), status=400, code=error.get("error_code", "INVOICE_GENERATION_FAILED"))

    for finfo in failures or []:
        logger.warning(
            "erh_generate_line_item_invoice asset_failure session_id=%s anchor_line=%s asset=%s error=%s message=%s",
            str(session.id),
            line_item_id,
            finfo.get("asset_code") or finfo.get("asset_name"),
            finfo.get("error"),
            finfo.get("message"),
        )
    logger.info(
        "erh_generate_line_item_invoice done line_item_id=%s session_id=%s generated=%s failures=%s",
        line_item_id,
        str(session.id),
        len(generated_batch or []),
        len(failures or []),
    )

    log_loss_task_completed(task_id=task_id, success=True)
    return _ok(
        {
            "line_item_id": str(row.id),
            "generated_invoices": [
                {
                    "id": str(g.id),
                    "file_path": g.file_path,
                    "version": g.version,
                    "generated_at": _to_primitive(g.generated_at),
                }
                for g in (generated_batch or [])
            ],
            "failed_invoices": failures or [],
            "status": session.status,
            "task_id": task_id,
        }
    )


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def post_invoice_api(request: HttpRequest, session_id: str) -> JsonResponse:
    """
    Mark a generated invoice session as POSTED (business finalization step).
    """
    deny = _require_capability(request, "erh.workflow.post")
    if deny:
        return deny
    session = get_object_or_404(BillingSession, id=session_id)
    if session.status != BillingSession.Status.POSTED:
        ok = transition_to(session, BillingSession.Status.POSTED)
        if not ok:
            return _err(
                f"Cannot post invoice from status {session.status}. Generate invoice first.",
                status=400,
                code="INVALID_STATUS_TRANSITION",
            )

    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    BillingAuditLog.objects.create(
        billing_session=session,
        action="POST_INVOICE",
        performed_by=performed_by,
        details={"status": session.status},
    )
    return _ok({"status": session.status})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def unfreeze_billing_lines_api(request: HttpRequest, session_id: str) -> JsonResponse:
    """Clear frozen flags on billing lines so sources can be fixed and the table recomputed."""
    denied = _require_capability(request, "erh.workflow.unfreeze")
    if denied:
        return denied
    session = get_object_or_404(BillingSession, id=session_id)
    body = _json_body(request)
    reason = (body.get("reason") or "").strip()
    raw_line = body.get("line_item_id") or body.get("lineItemId")
    line_item_id = (str(raw_line).strip() if raw_line not in (None, "") else None)
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    ok, err = unfreeze_billing_lines(
        session,
        performed_by=performed_by,
        reason=reason,
        line_item_id=line_item_id,
    )
    if not ok or err:
        return _err(
            (err or {}).get("message", "Unfreeze failed"),
            status=400,
            code=(err or {}).get("error_code", "UNFREEZE_FAILED"),
        )
    session.refresh_from_db()
    return _ok({"status": session.status})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def download_generated_invoice_api(request: HttpRequest, generated_invoice_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.download.generated_pdf")
    if deny:
        return deny
    generated = GeneratedInvoice.objects.filter(id=generated_invoice_id).first()
    if generated is None:
        # Backward-compat fallback: some older UI paths may send a billing-line id.
        line = BillingLineItem.objects.select_related("billing_session").filter(id=generated_invoice_id).first()
        if line is not None and line.billing_session_id:
            candidates = list(line.billing_session.generated_invoices.all())
            if line.asset_code:
                for c in candidates:
                    snap = c.invoice_snapshot_json if isinstance(c.invoice_snapshot_json, dict) else {}
                    if str(snap.get("asset_code") or "").strip() == str(line.asset_code).strip():
                        generated = c
                        break
            if generated is None and line.asset_name:
                for c in candidates:
                    snap = c.invoice_snapshot_json if isinstance(c.invoice_snapshot_json, dict) else {}
                    if str(snap.get("asset_name") or "").strip() == str(line.asset_name).strip():
                        generated = c
                        break
            if generated is None and candidates:
                generated = candidates[0]
        if generated is None:
            return _err("Generated invoice row not found", status=404, code="NOT_FOUND")
    filename = os.path.basename(str(generated.file_path or "").strip()) or f"{generated.id}.pdf"
    # Backward compatibility: older rows may not include _v{version} in stored file_path.
    # Ensure download names are versioned for regenerated invoices.
    if (
        generated.version
        and str(generated.version).strip()
        and "_v" not in filename.lower()
        and filename.lower().endswith(".pdf")
    ):
        stem, ext = os.path.splitext(filename)
        filename = f"{stem}_v{generated.version}{ext}"

    # Resolve local path robustly for old/new rows:
    # - absolute paths
    # - MEDIA_ROOT-relative paths
    # - legacy values with leading slash
    media_root = getattr(settings, "MEDIA_ROOT", os.path.join(settings.BASE_DIR, "media"))
    raw_path = str(generated.file_path or "").strip()
    candidate_paths: list[str] = []
    if raw_path:
        if os.path.isabs(raw_path):
            candidate_paths.append(raw_path)
        candidate_paths.append(os.path.join(media_root, raw_path))
        candidate_paths.append(os.path.join(media_root, raw_path.lstrip("/\\").replace("/", os.sep)))
    for p in candidate_paths:
        if p and os.path.exists(p):
            return FileResponse(open(p, "rb"), as_attachment=True, filename=filename)

    # Fallback to SharePoint mirror mode path when local invoice file is unavailable.
    remote_rel = str(generated.sharepoint_remote_path or "").strip().replace("\\", "/").lstrip("/")
    if remote_rel:
        mirror_abs = os.path.join(get_sharepoint_mirror_root(), remote_rel.replace("/", os.sep))
        if os.path.exists(mirror_abs):
            return FileResponse(open(mirror_abs, "rb"), as_attachment=True, filename=filename)

    # Final fallback for historical rows: fetch directly from SharePoint Graph
    # using stored item-id/drive-id/path metadata.
    try:
        drive_id = str(getattr(generated, "sharepoint_drive_id", "") or "").strip()
        item_id = str(getattr(generated, "sharepoint_item_id", "") or "").strip()
        if str(generated.sharepoint_item_id or "").strip() or remote_rel:
            content = download_file_from_sharepoint_graph(
                sharepoint_item_id=item_id,
                sharepoint_drive_id=drive_id,
                remote_rel_path=remote_rel,
            )
            return FileResponse(io.BytesIO(content), as_attachment=True, filename=filename)
    except Exception:
        pass
    return _err("Generated invoice file not found", status=404, code="NOT_FOUND")


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def parse_invoice_pdf_api(request: HttpRequest) -> JsonResponse:
    deny = _require_capability(request, "erh.parse.run")
    if deny:
        return deny
    # Supports either `file` (single) or `files` (multi)
    files = request.FILES.getlist("files")
    single = request.FILES.get("file")
    if files or single:
        deny_upload = _require_capability(request, "erh.pdf.upload")
        if deny_upload:
            return deny_upload
    session_id = request.POST.get("session_id")
    run_async = str(request.POST.get("async", "")).lower() in ("1", "true", "yes")

    if run_async:
        incoming = files or ([single] if single else [])
        if not incoming:
            return _err("No uploaded file(s). Send multipart with 'file' or 'files'.")
        file_count = len(incoming)
        session = get_object_or_404(BillingSession, id=session_id) if session_id else None
        # Pass PDFs as base64 in the Celery message so the worker does not depend on sharing
        # MEDIA_ROOT with the web container (Docker web vs celery file-not-found).
        b64_list: list[str] = []
        orig_names: list[str] = []
        billing_pdf_ids: list[str] = []
        security_rejections: list[dict[str, Any]] = []
        for f in incoming:
            raw = b"".join(f.chunks())
            original_name = os.path.basename(getattr(f, "name", "upload.pdf"))
            ok_pdf, sec_code, sec_msg = validate_pdf_security(original_name, raw)
            if not ok_pdf:
                security_rejections.append(
                    {
                        "original_filename": original_name,
                        "security_reason_code": sec_code,
                        "security_reason_message": sec_msg,
                    }
                )
                if session:
                    BillingInvoicePdf.objects.create(
                        billing_session=session,
                        original_filename=original_name,
                        transfer_status=BillingInvoicePdf.TransferStatus.FAILED,
                        parse_status="failed",
                        parse_summary_status="failed",
                        parse_error=sec_msg,
                        parse_started_at=None,
                        parse_completed_at=timezone.now(),
                        parse_elapsed_seconds=None,
                        local_file_exists=False,
                        local_file_size_bytes=None,
                        security_status="rejected",
                        security_reason_code=sec_code,
                        security_reason_message=sec_msg,
                    )
                continue
            orig_names.append(original_name)
            b64_list.append(base64.b64encode(raw).decode("ascii"))
            if session:
                row = BillingInvoicePdf.objects.create(
                    billing_session=session,
                    original_filename=original_name,
                    transfer_status=BillingInvoicePdf.TransferStatus.PENDING_LOCAL,
                    parse_status="pending",
                        parse_summary_status="pending",
                    parse_started_at=None,
                    parse_completed_at=None,
                    parse_elapsed_seconds=None,
                    local_file_exists=False,
                    local_file_size_bytes=None,
                    security_status="passed",
                    security_reason_code="",
                    security_reason_message="",
                )
                billing_pdf_ids.append(str(row.id))
        if not b64_list:
            return _err(
                "All uploaded files were rejected by security validation.",
                status=400,
                code="SECURITY_REJECTED_ALL",
            )
        async_results = []
        for idx, b64 in enumerate(b64_list):
            row_ids = [billing_pdf_ids[idx]] if idx < len(billing_pdf_ids) else None
            ar = erh_parse_invoice_files_task.delay(
                None,
                session_id or None,
                pdf_b64_list=[b64],
                original_filenames=[orig_names[idx]],
                billing_invoice_pdf_ids=row_ids,
                user_id=getattr(request.user, "id", None),
            )
            async_results.append(ar)
            log_loss_task_enqueued(
                task_id=ar.id,
                task_name="erh_parse_invoice_pdf",
                user=getattr(request, "user", None),
            )
        est_per_file_seconds = int(getattr(settings, "ERH_PARSE_EST_SECONDS_PER_FILE", 12) or 12)
        est_workers = int(getattr(settings, "ERH_PARSE_EST_WORKERS", 4) or 4)
        effective_workers = max(1, min(est_workers, max(1, file_count)))
        estimated_seconds = max(1, int((file_count * est_per_file_seconds) / effective_workers))
        return _ok(
            {
                "task_id": async_results[0].id if async_results else "",
                "task_ids": [ar.id for ar in async_results],
                "status": "queued",
                "estimated_seconds": estimated_seconds,
                "estimated_seconds_min": max(1, int(estimated_seconds * 0.8)),
                "estimated_seconds_max": max(2, int(estimated_seconds * 1.2)),
                "estimated_workers_used": effective_workers,
                "estimated_seconds_per_file": est_per_file_seconds,
                "file_count": file_count,
                "accepted_file_count": len(orig_names),
                "rejected_file_count": len(security_rejections),
                "security_rejections": security_rejections,
            },
            status=202,
        )

    task_id = f"erh-parse-invoice-{uuid.uuid4()}"
    log_loss_task_enqueued(
        task_id=task_id,
        task_name="erh_parse_invoice_pdf",
        user=getattr(request, "user", None),
    )
    log_loss_task_started(task_id=task_id)
    incoming_sync_all = files or ([single] if single else [])
    valid_files: list[Any] = []
    security_rejections_sync: list[dict[str, Any]] = []
    session = get_object_or_404(BillingSession, id=session_id) if session_id else None
    for f in incoming_sync_all:
        original_name = os.path.basename(getattr(f, "name", "upload.pdf"))
        raw = b"".join(f.chunks())
        try:
            if hasattr(f, "seek"):
                f.seek(0)
        except Exception:
            pass
        ok_pdf, sec_code, sec_msg = validate_pdf_security(original_name, raw)
        if not ok_pdf:
            security_rejections_sync.append(
                {
                    "original_filename": original_name,
                    "security_reason_code": sec_code,
                    "security_reason_message": sec_msg,
                }
            )
            if session:
                BillingInvoicePdf.objects.create(
                    billing_session=session,
                    original_filename=original_name,
                    transfer_status=BillingInvoicePdf.TransferStatus.FAILED,
                    parse_status="failed",
                    parse_summary_status="failed",
                    parse_error=sec_msg,
                    parse_started_at=None,
                    parse_completed_at=timezone.now(),
                    parse_elapsed_seconds=None,
                    local_file_exists=False,
                    local_file_size_bytes=None,
                    security_status="rejected",
                    security_reason_code=sec_code,
                    security_reason_message=sec_msg,
                )
            continue
        valid_files.append(f)

    if not valid_files:
        log_loss_task_completed(task_id=task_id, success=False, error_message="All uploaded files rejected by security validation.")
        return _err("All uploaded files were rejected by security validation.", status=400, code="SECURITY_REJECTED_ALL")

    try:
        if len(valid_files) == 1:
            results = [run_hybrid_engine(valid_files[0])]
        else:
            results = parse_multiple_invoices(valid_files, max_workers=4)
    except Exception as exc:
        log_loss_task_completed(task_id=task_id, success=False, error_message=str(exc))
        return _err(f"Failed to parse invoice PDF(s): {exc}", status=500, code="PARSE_FAILED")

    created_ids: list[str] = []
    created_utility_ids: list[str] = []
    uploaded_paths: list[str] = []
    created_pdf_rows: list[BillingInvoicePdf] = []

    incoming_sync = valid_files
    sync_temp_paths: list[str] = []
    display_names: list[str] = []
    sync_error: Exception | None = None
    try:
        for f in incoming_sync:
            if hasattr(f, "seek"):
                try:
                    f.seek(0)
                except Exception:
                    pass
            name = os.path.basename(getattr(f, "name", "upload.pdf"))
            display_names.append(name)
            if session:
                created_pdf_rows.append(
                    BillingInvoicePdf.objects.create(
                        billing_session=session,
                        original_filename=name,
                        transfer_status=BillingInvoicePdf.TransferStatus.PARSING,
                        parse_status="parsing",
                        parse_summary_status="pending",
                        parse_started_at=timezone.now(),
                        parse_completed_at=None,
                        parse_elapsed_seconds=None,
                        local_file_exists=True,
                        security_status="passed",
                        security_reason_code="",
                        security_reason_message="",
                    )
                )
            fd, path = tempfile.mkstemp(prefix="erh_sync_", suffix=".pdf")
            try:
                for chunk in f.chunks():
                    os.write(fd, chunk)
            finally:
                os.close(fd)
            sync_temp_paths.append(path)
            if created_pdf_rows:
                row = created_pdf_rows[-1]
                try:
                    row.local_file_size_bytes = os.path.getsize(path)
                except OSError:
                    row.local_file_size_bytes = None
                row.local_temp_path = path
                row.save(update_fields=["local_file_size_bytes", "local_temp_path"])

        if session_id and session:
            created_ids, created_utility_ids = persist_parsed_and_utility_for_session(
                session,
                results,
                billing_invoice_pdf_ids=[str(r.id) for r in created_pdf_rows],
            )

        performed_by = (
            getattr(request.user, "username", "")
            if hasattr(request, "user") and getattr(request.user, "is_authenticated", False)
            else "system"
        )
        uploaded_paths = sharepoint_upload_utility_batch(
            session,
            sync_temp_paths,
            display_names,
            results,
            performed_by=performed_by or "system",
        )
        for idx, row in enumerate(created_pdf_rows):
            remote_path = uploaded_paths[idx] if idx < len(uploaded_paths) else ""
            parsed_result = results[idx] if idx < len(results) and isinstance(results[idx], dict) else {}
            billing_cycle_aligned, billing_cycle_warning_message = _compute_billing_cycle_alignment(session, parsed_result)
            row.parse_status = "parsed"
            row.parse_error = ""
            row.billing_cycle_aligned = billing_cycle_aligned
            row.billing_cycle_warning_message = billing_cycle_warning_message
            row.parse_summary_status = (
                "pending_merge"
                if bool(row.pending_utility_patch_json)
                else ("parsed_with_warnings" if not billing_cycle_aligned else "ok")
            )
            row.parse_completed_at = timezone.now()
            if row.parse_started_at and row.parse_completed_at:
                row.parse_elapsed_seconds = max(
                    0.0,
                    round((row.parse_completed_at - row.parse_started_at).total_seconds(), 3),
                )
            row.transfer_status = BillingInvoicePdf.TransferStatus.ON_SHAREPOINT if remote_path else BillingInvoicePdf.TransferStatus.FAILED
            row.local_file_exists = False
            row.local_file_size_bytes = None
            row.local_temp_path = ""
            if remote_path:
                row.sharepoint_remote_path = remote_path
            else:
                row.parse_error = "Parse completed, but SharePoint upload path was not returned."
            row.save(
                update_fields=[
                    "parse_status",
                    "parse_error",
                    "parse_summary_status",
                    "billing_cycle_aligned",
                    "billing_cycle_warning_message",
                    "parse_completed_at",
                    "parse_elapsed_seconds",
                    "transfer_status",
                    "local_file_exists",
                    "local_file_size_bytes",
                    "local_temp_path",
                    "sharepoint_remote_path",
                ]
            )
    except Exception as exc:
        sync_error = exc
        for row in created_pdf_rows:
            try:
                row.parse_status = "failed"
                row.parse_summary_status = "failed"
                row.parse_error = str(exc)[:2000]
                row.parse_completed_at = timezone.now()
                if row.parse_started_at and row.parse_completed_at:
                    row.parse_elapsed_seconds = max(
                        0.0,
                        round((row.parse_completed_at - row.parse_started_at).total_seconds(), 3),
                    )
                row.transfer_status = BillingInvoicePdf.TransferStatus.FAILED
                row.local_file_exists = False
                row.local_file_size_bytes = None
                row.local_temp_path = ""
                row.save(
                    update_fields=[
                        "parse_status",
                        "parse_summary_status",
                        "parse_error",
                        "parse_completed_at",
                        "parse_elapsed_seconds",
                        "transfer_status",
                        "local_file_exists",
                        "local_file_size_bytes",
                        "local_temp_path",
                    ]
                )
            except Exception:
                pass
    finally:
        for p in sync_temp_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    if sync_error is not None:
        log_loss_task_completed(task_id=task_id, success=False, error_message=str(sync_error))
        return _err(f"Failed to process/upload invoice PDF(s): {sync_error}", status=500, code="PARSE_UPLOAD_FAILED")

    log_loss_task_completed(task_id=task_id, success=True)
    return _ok(
        {
            "results": results,
            "created_parsed_invoice_ids": created_ids,
            "created_utility_invoice_ids": created_utility_ids,
            "sharepoint_remote_paths": uploaded_paths,
            "task_id": task_id,
            "rejected_file_count": len(security_rejections_sync),
            "security_rejections": security_rejections_sync,
        }
    )


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def task_status_api(request: HttpRequest, task_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.session.view")
    if deny:
        return deny
    result = AsyncResult(task_id)
    payload: dict[str, Any] = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else False,
    }
    if result.ready():
        try:
            task_result = result.result
            payload["result"] = task_result if isinstance(task_result, dict) else {"value": str(task_result)}
        except Exception as exc:
            payload["result"] = {"error": str(exc)}
    return _ok(payload)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def sharepoint_connectivity_test_api(request: HttpRequest) -> JsonResponse:
    deny = _require_capability(request, "erh.session.edit")
    if deny:
        return deny
    payload = _json_body(request)
    country = payload.get("country") or "SG"
    asset_name = payload.get("asset_name") or "ERH_TEST_ASSET"
    invoice_number = payload.get("invoice_number") or f"health-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().date()
    remote_path = build_utility_invoice_remote_path(
        country=str(country),
        start_date=now,
        end_date=now,
        asset_name=str(asset_name),
        invoice_number=str(invoice_number),
        file_name="connectivity_test.pdf",
    )
    temp_dir = os.path.join(getattr(settings, "MEDIA_ROOT", os.path.join(settings.BASE_DIR, "media")), "erh_tmp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"sp_test_{uuid.uuid4().hex}.pdf")
    try:
        with open(temp_path, "wb") as fh:
            fh.write(b"%PDF-1.4\n% ERH connectivity test\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n")
        transfer_meta = upload_file_to_sharepoint(temp_path, remote_path)
        return _ok(
            {
                "message": "SharePoint connectivity test upload succeeded.",
                "upload_mode": transfer_meta.get("upload_mode"),
                "sharepoint_remote_path": transfer_meta.get("sharepoint_remote_path"),
                "details": transfer_meta,
            }
        )
    except Exception as exc:
        return _err(f"SharePoint connectivity test failed: {exc}", status=500, code="SHAREPOINT_TEST_FAILED")
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET"])
def upload_health_api(request: HttpRequest) -> JsonResponse:
    deny = _require_capability(request, "erh.session.view")
    if deny:
        return deny
    generated_total = GeneratedInvoice.objects.count()
    generated_ok = GeneratedInvoice.objects.filter(sharepoint_upload_status="on_sharepoint").count()
    generated_failed = GeneratedInvoice.objects.filter(sharepoint_upload_status="failed").count()
    utility_ok = 0
    utility_failed = 0
    from energy_revenue_hub.models import BillingAuditLog
    utility_ok = BillingAuditLog.objects.filter(action="SHAREPOINT_UPLOAD_UTILITY_INVOICE").count()
    utility_failed = BillingAuditLog.objects.filter(action="SHAREPOINT_UPLOAD_UTILITY_INVOICE_FAILED").count()
    return _ok(
        {
            "generated": {
                "total": generated_total,
                "on_sharepoint": generated_ok,
                "failed": generated_failed,
            },
            "utility": {
                "uploaded": utility_ok,
                "failed": utility_failed,
            },
        }
    )


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "POST"])
def utility_invoices_api(request: HttpRequest, session_id: str) -> JsonResponse:
    session = get_object_or_404(BillingSession, id=session_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.utility_invoice.view")
        if deny:
            return deny
        rows = list(
            UtilityInvoice.objects.filter(billing_session=session)
            .order_by("-created_at")
            .values(*_UTILITY_INVOICE_VALUES_LEAN)
        )
        for r in rows:
            r["id"] = str(r["id"])
            for k, v in list(r.items()):
                r[k] = _to_primitive(v)
        return _ok({"utility_invoices": rows})

    payload = _json_body(request)
    deny = _require_capability(request, "erh.utility_invoice.edit")
    if deny:
        return deny
    export_energy = _parse_decimal(payload.get("export_energy"))
    export_energy_cost = _parse_decimal(payload.get("export_energy_cost"))
    recurring_charges = _parse_decimal(payload.get("recurring_charges_dollars"))
    unit_rate = _parse_decimal(payload.get("unit_rate"))
    calculated_unit_rate = compute_calculated_unit_rate(export_energy, export_energy_cost)
    anomaly_flag = build_anomaly_flag_json(unit_rate, calculated_unit_rate)
    net_unit_rate = compute_net_unit_rate(export_energy, export_energy_cost, recurring_charges)

    created = UtilityInvoice.objects.create(
        billing_session=session,
        invoice_record_type=str(payload.get("invoice_record_type") or "utility_manual"),
        invoice_number=str(payload.get("invoice_number") or ""),
        account_no=str(payload.get("account_no") or ""),
        asset_code=str(payload.get("asset_code") or ""),
        vendor_key=str(payload.get("vendor_key") or ""),
        invoice_date=_parse_date(payload.get("invoice_date")),
        period_start=_parse_date(payload.get("period_start")),
        period_end=_parse_date(payload.get("period_end")),
        currency_code=str(payload.get("currency_code") or ""),
        total_amount=_parse_decimal(payload.get("total_amount")),
        export_energy=export_energy,
        export_energy_cost=export_energy_cost,
        recurring_charges_dollars=recurring_charges,
        unit_rate=unit_rate,
        calculated_unit_rate=calculated_unit_rate,
        anomaly_flag=anomaly_flag,
        current_charges_excl_gst=_parse_decimal(payload.get("current_charges_excl_gst")),
        net_unit_rate=net_unit_rate or str(payload.get("net_unit_rate") or ""),
        gst_rate=_parse_decimal(payload.get("gst_rate")),
        is_frozen=True,
        frozen_at=timezone.now(),
        frozen_by=getattr(request.user, "username", "") if hasattr(request, "user") else "",
    )
    return _ok({"utility_invoice_id": str(created.id)}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "PATCH"])
def utility_invoice_update_api(request: HttpRequest, invoice_id: str) -> JsonResponse:
    row = get_object_or_404(UtilityInvoice, id=invoice_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.utility_invoice.view")
        if deny:
            return deny
        pdf_name_by_id: dict[str, str] = {}
        if row.billing_session_id:
            pdf_name_by_id = {
                str(r["id"]): str(r.get("original_filename") or "").strip()
                for r in BillingInvoicePdf.objects.filter(billing_session_id=row.billing_session_id).values(
                    "id", "original_filename"
                )
            }
        else:
            pdf_one_id = str(row.billing_invoice_pdf_id or "").strip()
            if pdf_one_id:
                one = BillingInvoicePdf.objects.filter(pk=pdf_one_id).values("id", "original_filename").first()
                if one:
                    pdf_name_by_id[str(one["id"])] = str(one.get("original_filename") or "").strip()
        r = UtilityInvoice.objects.filter(pk=row.pk).values(*_UTILITY_INVOICE_VALUES_FULL).first()
        if not r:
            return _err("Not found.", status=404, code="NOT_FOUND")
        r["id"] = str(r["id"])
        for k, v in list(r.items()):
            r[k] = _to_primitive(v)
        pdf_id = str(r.get("billing_invoice_pdf_id") or "").strip()
        r["source_original_filename"] = pdf_name_by_id.get(pdf_id, "")
        r["is_unresolved"] = not bool(str(r.get("invoice_number") or "").strip()) or not bool(r.get("invoice_date"))
        r["download_original"] = (
            f"/energy-revenue-hub/api/billing-invoice-pdfs/{pdf_id}/download-original/" if pdf_id else ""
        )
        return _ok({"utility_invoice": r})

    deny = _require_capability(request, "erh.utility_invoice.edit")
    if deny:
        return deny
    payload = _json_body(request)
    action = str(payload.get("action") or "").strip().lower()
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""

    if action == "unfreeze":
        row.is_frozen = False
        row.frozen_at = None
        row.frozen_by = ""
        row.save(update_fields=["is_frozen", "frozen_at", "frozen_by", "updated_at"])
        return _ok({"utility_invoice_id": str(row.id), "is_frozen": row.is_frozen})

    # Any other mutation requires a reason string (plan decision locked).
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        return _err("reason is required for this action.", status=400, code="REASON_REQUIRED")

    if action == "relink":
        pdf_id = str(payload.get("billing_invoice_pdf_id") or "").strip()
        if not pdf_id:
            return _err("billing_invoice_pdf_id is required for relink.", status=400, code="INVALID_PAYLOAD")
        pdf_row = get_object_or_404(BillingInvoicePdf, id=pdf_id)
        if row.billing_session_id and str(row.billing_session_id) != str(pdf_row.billing_session_id):
            return _err(
                "Cannot relink across different billing sessions.",
                status=400,
                code="INVALID_RELINK",
            )
        row.billing_session_id = row.billing_session_id or pdf_row.billing_session_id
        row.billing_invoice_pdf = pdf_row
        row.invoice_record_type = "utility_relinked"
        row.is_frozen = False
        row.frozen_at = None
        row.frozen_by = ""
        row.save(
            update_fields=[
                "billing_session",
                "billing_invoice_pdf",
                "invoice_record_type",
                "is_frozen",
                "frozen_at",
                "frozen_by",
                "updated_at",
            ]
        )
        BillingAuditLog.objects.create(
            billing_session=row.billing_session,
            action="UTILITY_INVOICE_RELINKED",
            performed_by=performed_by,
            details={
                "utility_invoice_id": str(row.id),
                "billing_invoice_pdf_id": str(pdf_row.id),
                "original_filename": str(pdf_row.original_filename or ""),
                "reason": reason,
            },
        )
        return _ok(
            {
                "utility_invoice_id": str(row.id),
                "billing_invoice_pdf_id": str(pdf_row.id),
                "source_original_filename": str(pdf_row.original_filename or ""),
                "is_frozen": row.is_frozen,
            }
        )

    if action == "mark_failed":
        row.invoice_record_type = "utility_unresolved_failed"
        row.parse_document_confidence_level = "failed"
        row.parse_extraction_path = "manual"
        row.parse_review_status = "pending"
        row.parse_review_passed_at = None
        row.parse_review_passed_by = ""
        row.is_frozen = False
        row.frozen_at = None
        row.frozen_by = ""
        row.save(
            update_fields=[
                "invoice_record_type",
                "parse_document_confidence_level",
                "parse_extraction_path",
                "parse_review_status",
                "parse_review_passed_at",
                "parse_review_passed_by",
                "is_frozen",
                "frozen_at",
                "frozen_by",
                "updated_at",
            ]
        )
        BillingAuditLog.objects.create(
            billing_session=row.billing_session,
            action="UTILITY_INVOICE_MARKED_FAILED",
            performed_by=performed_by,
            details={
                "utility_invoice_id": str(row.id),
                "billing_invoice_pdf_id": str(row.billing_invoice_pdf_id or ""),
                "reason": reason,
            },
        )
        return _ok({"utility_invoice_id": str(row.id), "is_frozen": row.is_frozen, "status": "failed"})

    if row.is_frozen:
        return _err(
            "Utility invoice row is frozen. Unfreeze before editing.",
            status=400,
            code="UTILITY_ROW_FROZEN",
        )
    previous = {fn: getattr(row, fn) for fn in _UTILITY_INVOICE_CORRECTION_FIELDS}
    # Full manual entry allowed on unfrozen row.
    row.invoice_number = str(payload.get("invoice_number", row.invoice_number))
    row.account_no = str(payload.get("account_no", row.account_no))
    row.asset_code = str(payload.get("asset_code", row.asset_code))
    row.vendor_key = str(payload.get("vendor_key", row.vendor_key))
    row.currency_code = str(payload.get("currency_code", row.currency_code))
    row.invoice_date = _parse_date(payload.get("invoice_date")) if "invoice_date" in payload else row.invoice_date
    row.period_start = _parse_date(payload.get("period_start")) if "period_start" in payload else row.period_start
    row.period_end = _parse_date(payload.get("period_end")) if "period_end" in payload else row.period_end
    row.total_amount = _parse_decimal(payload.get("total_amount")) if "total_amount" in payload else row.total_amount
    row.export_energy = _parse_decimal(payload.get("export_energy")) if "export_energy" in payload else row.export_energy
    row.export_energy_cost = _parse_decimal(payload.get("export_energy_cost")) if "export_energy_cost" in payload else row.export_energy_cost
    if "recurring_charges_dollars" in payload:
        row.recurring_charges_dollars = _parse_decimal(payload.get("recurring_charges_dollars"))
    row.unit_rate = _parse_decimal(payload.get("unit_rate")) if "unit_rate" in payload else row.unit_rate
    if "current_charges_excl_gst" in payload:
        row.current_charges_excl_gst = _parse_decimal(payload.get("current_charges_excl_gst"))
    if "gst_rate" in payload:
        row.gst_rate = _parse_decimal(payload.get("gst_rate"))
    row.calculated_unit_rate = compute_calculated_unit_rate(row.export_energy, row.export_energy_cost)
    row.anomaly_flag = build_anomaly_flag_json(row.unit_rate, row.calculated_unit_rate)
    row.net_unit_rate = compute_net_unit_rate(row.export_energy, row.export_energy_cost, row.recurring_charges_dollars)
    if not row.net_unit_rate and "net_unit_rate" in payload:
        row.net_unit_rate = str(payload.get("net_unit_rate") or "")
    if action in ("save_and_freeze", "freeze"):
        row.is_frozen = True
        row.frozen_at = timezone.now()
        row.frozen_by = performed_by
    row.save()
    _persist_utility_invoice_field_corrections(row, previous)
    BillingAuditLog.objects.create(
        billing_session=row.billing_session,
        action="UTILITY_INVOICE_UPDATED",
        performed_by=performed_by,
        details={
            "utility_invoice_id": str(row.id),
            "billing_invoice_pdf_id": str(row.billing_invoice_pdf_id or ""),
            "reason": reason,
            "action": action or "edit",
        },
    )
    return _ok({"utility_invoice_id": str(row.id), "is_frozen": row.is_frozen})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def utility_invoices_freeze_all_api(request: HttpRequest, session_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.workflow.freeze")
    if deny:
        return deny
    session = get_object_or_404(BillingSession, id=session_id)
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    now = timezone.now()
    updated = UtilityInvoice.objects.filter(billing_session=session).exclude(is_frozen=True).update(
        is_frozen=True,
        frozen_at=now,
        frozen_by=performed_by,
    )
    return _ok({"frozen_rows": int(updated)})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "POST"])
def payments_api(request: HttpRequest, session_id: str) -> JsonResponse:
    session = get_object_or_404(BillingSession, id=session_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.session.view")
        if deny:
            return deny
        rows = list(
            Payment.objects.filter(invoice__billing_session=session).order_by("-payment_due").values(
                "payment_id",
                "asset_number",
                "invoice_id",
                "payment_due",
                "payment_date",
                "payment_paid",
                "payment_pending",
                "payment_status",
            )
        )
        for r in rows:
            if r.get("invoice_id"):
                r["invoice_id"] = str(r["invoice_id"])
            for k, v in list(r.items()):
                r[k] = _to_primitive(v)
        return _ok({"payments": rows})

    deny = _require_capability(request, "erh.session_data.payment.edit")
    if deny:
        return deny
    payload = _json_body(request)
    invoice_id = payload.get("invoice_id")
    invoice = get_object_or_404(UtilityInvoice, id=invoice_id, billing_session=session)
    payment_id = str(payload.get("payment_id") or f"pay-{uuid.uuid4().hex[:12]}")
    row = Payment.objects.create(
        payment_id=payment_id,
        invoice=invoice,
        asset_number=str(payload.get("asset_number") or invoice.asset_code or ""),
        invoice_date=_parse_date(payload.get("invoice_date")) or invoice.invoice_date,
        payment_due_condition=payload.get("payment_due_condition"),
        payment_due=_parse_date(payload.get("payment_due")),
        payment_date=_parse_date(payload.get("payment_date")),
        payment_paid=_parse_decimal(payload.get("payment_paid")),
        payment_reference=str(payload.get("payment_reference") or ""),
        payment_pending=_parse_decimal(payload.get("payment_pending")),
        payment_status=str(payload.get("payment_status") or ""),
    )
    return _ok({"payment_id": row.payment_id}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["PATCH"])
def payment_update_api(request: HttpRequest, payment_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.session_data.payment.edit")
    if deny:
        return deny
    row = get_object_or_404(Payment, payment_id=payment_id)
    payload = _json_body(request)
    if "payment_due" in payload:
        row.payment_due = _parse_date(payload.get("payment_due"))
    if "payment_date" in payload:
        row.payment_date = _parse_date(payload.get("payment_date"))
    if "payment_paid" in payload:
        row.payment_paid = _parse_decimal(payload.get("payment_paid"))
    if "payment_pending" in payload:
        row.payment_pending = _parse_decimal(payload.get("payment_pending"))
    if "payment_status" in payload:
        row.payment_status = str(payload.get("payment_status") or "")
    if "payment_reference" in payload:
        row.payment_reference = str(payload.get("payment_reference") or "")
    row.save()
    return _ok({"payment_id": row.payment_id})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def utility_invoice_delete_api(request: HttpRequest, invoice_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(UtilityInvoice, id=invoice_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["POST"])
def utility_invoice_parse_pass_api(request: HttpRequest, invoice_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.utility_invoice.review_pass")
    if deny:
        return deny
    row = get_object_or_404(UtilityInvoice, id=invoice_id)
    performed_by = getattr(request.user, "username", "") if hasattr(request, "user") else ""
    row.parse_review_status = "passed"
    row.parse_review_passed_at = timezone.now()
    row.parse_review_passed_by = performed_by
    row.save(update_fields=["parse_review_status", "parse_review_passed_at", "parse_review_passed_by", "updated_at"])
    BillingAuditLog.objects.create(
        billing_session=row.billing_session,
        action="UTILITY_INVOICE_PARSE_PASSED",
        performed_by=performed_by,
        details={"utility_invoice_id": str(row.id), "billing_invoice_pdf_id": str(row.billing_invoice_pdf_id or "")},
    )
    return _ok({"utility_invoice_id": str(row.id), "parse_review_status": row.parse_review_status})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def payment_delete_api(request: HttpRequest, payment_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(Payment, payment_id=payment_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "POST"])
def meter_readings_api(request: HttpRequest, session_id: str) -> JsonResponse:
    session = get_object_or_404(BillingSession, id=session_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.session.view")
        if deny:
            return deny
        effective_assets = effective_session_asset_codes(session)
        rows = list(
            MeterReading.objects.filter(device_id__in=effective_assets).order_by("-read_at").values(
                "id",
                "device_id",
                "read_at",
                "cumulative_value",
                "source",
                "data_quality",
                "reading_role",
                "period_label",
                "delta_kwh_for_period",
                "notes",
                "created_at",
            )
        )
        for r in rows:
            r["id"] = str(r["id"])
            for k, v in list(r.items()):
                r[k] = _to_primitive(v)
        return _ok({"meter_readings": rows})

    deny = _require_capability(request, "erh.session_data.meter_reading.edit")
    if deny:
        return deny
    payload = _json_body(request)
    reading = MeterReading.objects.create(
        device_id=str(payload.get("device_id") or ""),
        read_at=datetime.fromisoformat(str(payload.get("read_at"))) if payload.get("read_at") else datetime.utcnow(),
        cumulative_value=_parse_decimal(payload.get("cumulative_value")) or Decimal("0"),
        source=str(payload.get("source") or "manual"),
        data_quality=str(payload.get("data_quality") or "ok"),
        reading_role=str(payload.get("reading_role") or "intermediate"),
        period_label=str(payload.get("period_label") or ""),
        delta_kwh_for_period=_parse_decimal(payload.get("delta_kwh_for_period")),
        notes=str(payload.get("notes") or ""),
        calculation_notes=str(payload.get("calculation_notes") or ""),
    )
    return _ok({"meter_reading_id": str(reading.id)}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["PATCH"])
def meter_reading_update_api(request: HttpRequest, reading_id: str) -> JsonResponse:
    deny = _require_capability(request, "erh.session_data.meter_reading.edit")
    if deny:
        return deny
    reading = get_object_or_404(MeterReading, id=reading_id)
    payload = _json_body(request)
    if "read_at" in payload and payload.get("read_at"):
        try:
            reading.read_at = datetime.fromisoformat(str(payload.get("read_at")))
        except Exception:
            pass
    if "cumulative_value" in payload:
        reading.cumulative_value = _parse_decimal(payload.get("cumulative_value")) or reading.cumulative_value
    if "source" in payload:
        reading.source = str(payload.get("source") or "")
    if "data_quality" in payload:
        reading.data_quality = str(payload.get("data_quality") or "")
    if "reading_role" in payload:
        reading.reading_role = str(payload.get("reading_role") or "")
    if "period_label" in payload:
        reading.period_label = str(payload.get("period_label") or "")
    if "delta_kwh_for_period" in payload:
        reading.delta_kwh_for_period = _parse_decimal(payload.get("delta_kwh_for_period"))
    if "notes" in payload:
        reading.notes = str(payload.get("notes") or "")
    if "calculation_notes" in payload:
        reading.calculation_notes = str(payload.get("calculation_notes") or "")
    reading.save()
    return _ok({"meter_reading_id": str(reading.id)})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def meter_reading_delete_api(request: HttpRequest, reading_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(MeterReading, id=reading_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "POST"])
def asset_generation_api(request: HttpRequest, session_id: str) -> JsonResponse:
    session = get_object_or_404(BillingSession, id=session_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.session.view")
        if deny:
            return deny
        effective_assets = effective_session_asset_codes(session)
        rows = list(
            AssetGeneration.objects.filter(asset_number__in=effective_assets).order_by("-month").values(
                "id", "asset_number", "month", "grid_export_kwh", "pv_generation_kwh", "rooftop_self_consumption_kwh", "bess_dispatch_kwh"
            )
        )
        for r in rows:
            r["id"] = str(r["id"])
            for k, v in list(r.items()):
                r[k] = _to_primitive(v)
        return _ok({"asset_generation": rows})

    deny = _require_capability(request, "erh.session_data.asset_generation.edit")
    if deny:
        return deny
    payload = _json_body(request)
    row = AssetGeneration.objects.create(
        asset_number=str(payload.get("asset_number") or ""),
        month=str(payload.get("month") or ""),
        grid_export_kwh=_parse_decimal(payload.get("grid_export_kwh")),
        pv_generation_kwh=_parse_decimal(payload.get("pv_generation_kwh")),
        rooftop_self_consumption_kwh=_parse_decimal(payload.get("rooftop_self_consumption_kwh")),
        bess_dispatch_kwh=_parse_decimal(payload.get("bess_dispatch_kwh")),
    )
    return _ok({"asset_generation_id": str(row.id)}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "POST"])
def penalties_api(request: HttpRequest, session_id: str) -> JsonResponse:
    session = get_object_or_404(BillingSession, id=session_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.session.view")
        if deny:
            return deny
        effective_assets = effective_session_asset_codes(session)
        rows = list(Penalty.objects.filter(asset_number__in=effective_assets).values("id", "asset_number", "penalty_type", "penalty_rate", "penalty_charges"))
        for r in rows:
            r["id"] = str(r["id"])
            for k, v in list(r.items()):
                r[k] = _to_primitive(v)
        return _ok({"penalties": rows})

    deny = _require_capability(request, "erh.session_data.penalty.edit")
    if deny:
        return deny
    payload = _json_body(request)
    row = Penalty.objects.create(
        asset_number=str(payload.get("asset_number") or ""),
        penalty_type=str(payload.get("penalty_type") or ""),
        penalty_rate=_parse_decimal(payload.get("penalty_rate")),
        penalty_charges=_parse_decimal(payload.get("penalty_charges")),
    )
    return _ok({"penalty_id": str(row.id)}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["GET", "POST"])
def adjustments_api(request: HttpRequest, session_id: str) -> JsonResponse:
    session = get_object_or_404(BillingSession, id=session_id)
    if request.method == "GET":
        deny = _require_capability(request, "erh.session.view")
        if deny:
            return deny
        effective_assets = effective_session_asset_codes(session)
        rows = list(
            Adjustment.objects.filter(asset_number__in=effective_assets).values(
                "id", "asset_number", "adjustment_type", "adjustment_amount", "adjustment_reason"
            )
        )
        for r in rows:
            r["id"] = str(r["id"])
            for k, v in list(r.items()):
                r[k] = _to_primitive(v)
        return _ok({"adjustments": rows})

    deny = _require_capability(request, "erh.session_data.adjustment.edit")
    if deny:
        return deny
    payload = _json_body(request)
    row = Adjustment.objects.create(
        asset_number=str(payload.get("asset_number") or ""),
        adjustment_type=str(payload.get("adjustment_type") or ""),
        adjustment_amount=_parse_decimal(payload.get("adjustment_amount")),
        adjustment_reason=str(payload.get("adjustment_reason") or ""),
    )
    return _ok({"adjustment_id": str(row.id)}, status=201)


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def asset_generation_delete_api(request: HttpRequest, generation_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(AssetGeneration, id=generation_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def penalty_delete_api(request: HttpRequest, penalty_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(Penalty, id=penalty_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def adjustment_delete_api(request: HttpRequest, adjustment_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(Adjustment, id=adjustment_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def parsed_invoice_delete_api(request: HttpRequest, parsed_invoice_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(ParsedInvoice, id=parsed_invoice_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def billing_line_item_delete_api(request: HttpRequest, line_item_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(BillingLineItem, id=line_item_id)
    row.delete()
    return _ok({"deleted": True})


@login_required
@feature_required("energy_revenue_hub")
@require_http_methods(["DELETE"])
def generated_invoice_delete_api(request: HttpRequest, generated_invoice_id: str) -> JsonResponse:
    deny = _require_superuser(request)
    if deny:
        return deny
    row = get_object_or_404(GeneratedInvoice, id=generated_invoice_id)
    row.delete()
    return _ok({"deleted": True})
