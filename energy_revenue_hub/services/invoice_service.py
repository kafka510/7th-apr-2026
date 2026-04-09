from __future__ import annotations

import os
import re
import traceback
import logging
from datetime import datetime
from typing import Any, Dict, Tuple

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

from energy_revenue_hub.models import (
    BillingAuditLog,
    BillingLineItem,
    BillingSession,
    GeneratedInvoice,
    UtilityInvoice,
)
from energy_revenue_hub.services.invoice_snapshot import build_invoice_snapshot_json
from energy_revenue_hub.services.invoice_numbering import (
    compute_invoice_dates,
    get_or_allocate_output_invoice_number,
)
from energy_revenue_hub.services.invoice_template_router import get_invoice_pdf_elements, resolve_invoice_template_id
from energy_revenue_hub.services.invoice_weasyprint import HTML_TEMPLATE_BY_KEY, render_invoice_html_pdf
from energy_revenue_hub.services.sharepoint_service import (
    build_generated_invoice_remote_path,
    upload_file_to_sharepoint,
)
from energy_revenue_hub.workflow import transition_to
from main.models import AssetList

logger = logging.getLogger(__name__)


def _err(code: str, message: str) -> Dict[str, str]:
    return {"error_code": code, "message": message}


def _get_invoice_storage_dir() -> str:
    base = getattr(settings, "MEDIA_ROOT", None) or os.path.join(settings.BASE_DIR, "media")
    subdir = os.path.join(base, "invoices")
    os.makedirs(subdir, exist_ok=True)
    return subdir


def _safe_filename_part(value: str, fallback: str) -> str:
    s = (value or "").strip()
    if not s:
        s = fallback
    s = re.sub(r"[^\w\-]+", "_", s)
    return s[:80] or fallback


def _fmt_date_d_mon_yyyy(value: str) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s).strftime("%d %b %Y").lstrip("0")
    except Exception:
        return s


def _line_asset_key(line_item: BillingLineItem) -> str:
    return (line_item.asset_code or "").strip() or (line_item.asset_name or "").strip() or "asset"


def resolve_billing_invoice_pdf_id_for_line_row(session: BillingSession, row: dict[str, Any]) -> str:
    """
    Best-effort utility ``billing_invoice_pdf_id`` for a billing line dict (session detail payload).
    Prefers a utility row where both asset_code and account match the line when possible.
    """
    asset_code = str(row.get("asset_code") or "").strip()
    extras = row.get("line_extras_json") or {}
    extras = extras if isinstance(extras, dict) else {}
    acct = str(extras.get("account_key") or "").strip()
    if not asset_code and not acct:
        return ""

    uq = UtilityInvoice.objects.filter(billing_session=session)
    if asset_code and acct:
        uis = list(uq.filter(Q(asset_code=asset_code) | Q(account_no=acct)).order_by("-created_at"))
    elif asset_code:
        uis = list(uq.filter(asset_code=asset_code).order_by("-created_at"))
    else:
        uis = list(uq.filter(account_no=acct).order_by("-created_at"))

    if not uis:
        return ""

    for ui in uis:
        ua = str(ui.asset_code or "").strip()
        un = str(ui.account_no or "").strip()
        if asset_code and acct and ua == asset_code and un == acct and ui.billing_invoice_pdf_id:
            return str(ui.billing_invoice_pdf_id).strip()

    if asset_code:
        for ui in uis:
            if str(ui.asset_code or "").strip() == asset_code and ui.billing_invoice_pdf_id:
                return str(ui.billing_invoice_pdf_id).strip()

    if acct:
        for ui in uis:
            if str(ui.account_no or "").strip() == acct and ui.billing_invoice_pdf_id:
                return str(ui.billing_invoice_pdf_id).strip()

    for ui in uis:
        if ui.billing_invoice_pdf_id:
            return str(ui.billing_invoice_pdf_id).strip()
    return ""


def resolve_billing_invoice_pdf_id_for_line(session: BillingSession, line: BillingLineItem) -> str:
    row = {
        "asset_code": line.asset_code,
        "asset_name": line.asset_name,
        "line_extras_json": line.line_extras_json,
    }
    return resolve_billing_invoice_pdf_id_for_line_row(session, row)


def line_items_sharing_utility_pdf_with(session: BillingSession, row: BillingLineItem) -> list[BillingLineItem]:
    """
    Billing lines for the same asset key that resolve to the same utility PDF as ``row``.
    One "Generate row PDF" run includes every segment / year line for that asset + PDF only.
    """
    anchor_key = _line_asset_key(row)
    anchor_pdf = resolve_billing_invoice_pdf_id_for_line(session, row)
    out: list[BillingLineItem] = []
    for li in session.line_items.all().order_by("sort_order", "asset_name", "id"):
        if _line_asset_key(li) != anchor_key:
            continue
        if resolve_billing_invoice_pdf_id_for_line(session, li) != anchor_pdf:
            continue
        out.append(li)
    return out if out else [row]


def generate_invoice_pdf(
    session: BillingSession,
    performed_by: str = "",
    *,
    target_asset_keys: list[str] | None = None,
    target_line_item_ids: list[str] | None = None,
) -> Tuple[list[GeneratedInvoice] | None, list[Dict[str, Any]], Dict[str, str]]:
    """
    Generate a simple PDF invoice summarizing billing line items.

    Returns (generated_invoices, failures, error).
    - `error` is only for hard failures (invalid state / no lines / etc.).
    - Per-asset PDF or SharePoint failures are returned in `failures` and do not abort other assets.
    - Freeze rules apply **per asset**: mixed frozen/unfrozen under the same asset key still fails
      for that asset only; different assets can have different freeze states in one session run.
    """
    line_items = list(session.line_items.all().order_by("asset_name", "sort_order", "id"))
    if not line_items:
        return None, [], _err("NO_LINE_ITEMS", "No line items to generate invoice.")

    run_line_items = line_items
    if target_line_item_ids:
        wanted = {str(x).strip() for x in target_line_item_ids if str(x).strip()}
        run_line_items = [li for li in line_items if str(li.id) in wanted]
        if not run_line_items:
            return None, [], _err("LINE_ITEMS_NOT_FOUND", "No matching billing line items for PDF generation.")
    elif target_asset_keys:
        wanted = {str(k).strip() for k in target_asset_keys if str(k).strip()}
        run_line_items = [li for li in line_items if _line_asset_key(li) in wanted]
        if not run_line_items:
            return None, [], _err("ASSET_NOT_FOUND", "No matching line-item asset found for PDF generation.")

    storage_dir = _get_invoice_storage_dir()
    base_version = session.generated_invoices.count() + 1
    utility_rows = list(UtilityInvoice.objects.filter(billing_session=session).order_by("-created_at"))
    template_key = resolve_invoice_template_id(session)
    # Final invoice output is one PDF per asset.
    by_asset: dict[str, list[BillingLineItem]] = {}
    for li in run_line_items:
        by_asset.setdefault(_line_asset_key(li), []).append(li)

    generated_batch: list[GeneratedInvoice] = []
    failures: list[Dict[str, Any]] = []
    lines_to_freeze_ids: list = []
    for idx, (asset_code, asset_lines) in enumerate(by_asset.items()):
        version = base_version + idx
        asset_name = (asset_lines[0].asset_name or asset_code) if asset_lines else asset_code
        frozen_flags = [bool(li.is_frozen) for li in asset_lines]
        if any(frozen_flags) and not all(frozen_flags):
            frozen_rows = [li for li in asset_lines if bool(li.is_frozen)]
            unfrozen_rows = [li for li in asset_lines if not bool(li.is_frozen)]
            failures.append(
                {
                    "asset_code": asset_code,
                    "asset_name": str(asset_name),
                    "error": "INCONSISTENT_FREEZE",
                    "message": (
                        f"Inconsistent frozen state for this asset (frozen={len(frozen_rows)}, "
                        f"unfrozen={len(unfrozen_rows)}). Unify freeze state for all lines of this asset, then retry."
                    ),
                    "stage": "precheck",
                }
            )
            continue
        if all(frozen_flags):
            failures.append(
                {
                    "asset_code": asset_code,
                    "asset_name": str(asset_name),
                    "error": "LINES_FROZEN",
                    "message": "All billing lines for this asset are frozen. Unfreeze to regenerate PDFs.",
                    "stage": "precheck",
                }
            )
            continue
        try:
            snapshot = build_invoice_snapshot_json(session, asset_lines, version=version, utility_rows=utility_rows)
        except Exception as e:
            msg = str(e)
            tb = traceback.format_exc()
            logger.exception(
                "Invoice snapshot build failed for session=%s asset=%s",
                str(session.id),
                asset_code,
            )
            failures.append(
                {
                    "asset_code": asset_code,
                    "asset_name": str(asset_name),
                    "error": msg,
                    "stage": "snapshot",
                }
            )
            BillingAuditLog.objects.create(
                billing_session=session,
                action="INVOICE_SNAPSHOT_BUILD_FAILED",
                performed_by=performed_by,
                details={"error": msg, "traceback": tb, "asset_code": asset_code, "asset_name": str(asset_name)},
            )
            continue
        snapshot["asset_code"] = asset_code
        snapshot["asset_name"] = str(asset_name)
        asset_row = AssetList.objects.filter(asset_code=asset_code).only("country").first()
        invoice_country = (getattr(asset_row, "country", "") or session.country or "").strip().upper() or "NA"
        invoice_yyyymm = datetime.utcnow().strftime("%Y%m")
        try:
            output_invoice_number, invoice_ledger, contract_type_key = get_or_allocate_output_invoice_number(
                session=session,
                asset_code=asset_code,
                country=invoice_country,
                yyyymm=invoice_yyyymm,
            )
        except ValueError as e:
            failures.append(
                {
                    "asset_code": asset_code,
                    "asset_name": str(asset_name),
                    "error": str(e),
                    "stage": "numbering",
                }
            )
            continue

        invoice_date_iso, due_date_iso, date_warnings = compute_invoice_dates(asset_code, contract_type_key)
        snapshot.setdefault("header", {})
        snapshot["header"]["invoice_no"] = output_invoice_number
        snapshot["header"]["invoice_date"] = invoice_date_iso
        snapshot["header"]["payment_due_date"] = due_date_iso
        snapshot["header"]["invoice_date_display"] = _fmt_date_d_mon_yyyy(invoice_date_iso)
        snapshot["header"]["payment_due_date_display"] = _fmt_date_d_mon_yyyy(due_date_iso)
        snapshot.setdefault("summary_of_charges", {})
        snapshot["summary_of_charges"]["current_charges_due_on"] = _fmt_date_d_mon_yyyy(due_date_iso)
        if date_warnings:
            snapshot.setdefault("warnings", [])
            snapshot["warnings"].extend(date_warnings)

        invoice_no = output_invoice_number
        filename = f"{_safe_filename_part(asset_name, asset_code)}+{invoice_no}_v{version}.pdf"
        file_path = os.path.join(storage_dir, filename)

        try:
            if template_key in HTML_TEMPLATE_BY_KEY:
                render_invoice_html_pdf(file_path, template_key, snapshot, session)
            else:
                doc = SimpleDocTemplate(
                    file_path,
                    pagesize=A4,
                    rightMargin=inch,
                    leftMargin=inch,
                    topMargin=inch,
                    bottomMargin=inch,
                )
                elements = get_invoice_pdf_elements(template_key, snapshot, session)
                doc.build(elements)
        except Exception as e:
            msg = str(e)
            failures.append({"asset_code": asset_code, "asset_name": str(asset_name), "error": msg, "stage": "pdf"})
            BillingAuditLog.objects.create(
                billing_session=session,
                action="INVOICE_PDF_GENERATION_FAILED",
                performed_by=performed_by,
                details={"error": msg, "asset_code": asset_code, "asset_name": str(asset_name)},
            )
            continue

        rel_path = os.path.join("invoices", filename)
        with transaction.atomic():
            gen_inv = GeneratedInvoice.objects.create(
                billing_session=session,
                file_path=rel_path,
                version=version,
                output_invoice_number=output_invoice_number,
                invoice_asset_code=asset_code,
                billing_contract_type=contract_type_key,
                invoice_sequence_ledger=invoice_ledger,
                sharepoint_upload_status="pending_local",
                invoice_snapshot_json=snapshot,
            )
        generated_batch.append(gen_inv)
        lines_to_freeze_ids.extend([li.id for li in asset_lines])

        try:
            remote_path = build_generated_invoice_remote_path(
                country=session.country,
                start_date=session.start_date,
                end_date=session.end_date,
                asset_name=str(asset_name),
                invoice_number=invoice_no,
                file_name=filename,
            )
            transfer_meta = upload_file_to_sharepoint(file_path, remote_path)
            gen_inv.sharepoint_remote_path = str(transfer_meta.get("sharepoint_remote_path", ""))
            gen_inv.sharepoint_item_id = str(transfer_meta.get("sharepoint_item_id", ""))
            gen_inv.sharepoint_web_url = str(transfer_meta.get("web_url", ""))
            gen_inv.sharepoint_upload_status = "on_sharepoint"
            gen_inv.sharepoint_upload_error = ""
            gen_inv.save(
                update_fields=[
                    "sharepoint_remote_path",
                    "sharepoint_item_id",
                    "sharepoint_web_url",
                    "sharepoint_upload_status",
                    "sharepoint_upload_error",
                ]
            )
            BillingAuditLog.objects.create(
                billing_session=session,
                action="SHAREPOINT_UPLOAD_GENERATED_INVOICE",
                performed_by=performed_by,
                details={**transfer_meta, "asset_code": asset_code},
            )
        except Exception as exc:
            gen_inv.sharepoint_upload_status = "failed"
            gen_inv.sharepoint_upload_error = str(exc)
            gen_inv.save(update_fields=["sharepoint_upload_status", "sharepoint_upload_error"])
            failures.append(
                {
                    "asset_code": asset_code,
                    "asset_name": str(asset_name),
                    "error": str(exc),
                    "stage": "sharepoint",
                    "generated_invoice_id": str(gen_inv.id),
                }
            )
            BillingAuditLog.objects.create(
                billing_session=session,
                action="SHAREPOINT_UPLOAD_GENERATED_INVOICE_FAILED",
                performed_by=performed_by,
                details={"error": str(exc), "file_path": rel_path, "asset_code": asset_code},
            )

    if lines_to_freeze_ids:
        now = timezone.now()
        BillingLineItem.objects.filter(id__in=lines_to_freeze_ids).update(
            is_frozen=True,
            frozen_at=now,
            frozen_by=performed_by or "",
        )
        BillingAuditLog.objects.create(
            billing_session=session,
            action="FREEZE_BILLING_LINES",
            performed_by=performed_by,
            details={
                "version_start": base_version,
                "line_count": len(lines_to_freeze_ids),
                "template_id": template_key,
                "generated_count": len(generated_batch),
            },
        )

    # Move workflow state to GENERATED and log (skip transition when re‑issuing PDF on already‑GENERATED session).
    if session.status != BillingSession.Status.GENERATED:
        transition_to(session, BillingSession.Status.GENERATED)
    BillingAuditLog.objects.create(
        billing_session=session,
        action="GENERATE_INVOICE",
        performed_by=performed_by,
        details={
            "generated_count": len(generated_batch),
            "file_paths": [g.file_path for g in generated_batch],
            "versions": [g.version for g in generated_batch],
            "invoice_snapshot_version": (generated_batch[0].invoice_snapshot_json or {}).get("schema_version")
            if generated_batch
            else None,
        },
    )
    return generated_batch, failures, {}

