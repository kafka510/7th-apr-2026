"""
Persist ERH hybrid parser output to ParsedInvoice + UtilityInvoice, then SharePoint uploads.

Parse and SharePoint are separate phases: all PDFs are parsed and persisted first; uploads run
afterward; local temp files are removed only after the upload phase completes.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from energy_revenue_hub.models import BillingAuditLog, BillingInvoicePdf, BillingSession, ParsedInvoice, UtilityInvoice
from main.models import assets_contracts
from energy_revenue_hub.services.utility_invoice_rates import (
    build_anomaly_flag_json,
    compute_calculated_unit_rate,
    compute_net_unit_rate,
)
from energy_revenue_hub.services.sharepoint_service import (
    build_utility_invoice_remote_path,
    upload_file_to_sharepoint,
)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _parse_invoice_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def parser_result_to_json_snapshot(r: dict[str, Any]) -> dict[str, Any]:
    """Full parser dict in JSONField-safe form (for audit / reprocessing)."""
    return {str(k): _json_safe_value(v) for k, v in r.items()}


def _asset_code_from_result(r: dict[str, Any]) -> str:
    """
    Prefer ``assets_contracts`` row matched by SP ``account_number`` ↔ ``sp_account_no`` (same link as billing).
    Fallback: parser ``asset_name`` / ``site_address`` (legacy / noisy OCR).
    """
    acct = str(r.get("account_number") or "").strip()
    if acct:
        row = assets_contracts.objects.filter(sp_account_no=acct).only("asset_code").first()
        if row and (getattr(row, "asset_code", None) or "").strip():
            return str(row.asset_code).strip()[:255]
    v = r.get("asset_name") or r.get("site_address") or ""
    s = str(v).strip()
    return s[:255] if s else ""


def invoice_number_date_upsert_key(
    raw_invoice_number: Any,
    invoice_date: date | None,
) -> tuple[str, date] | None:
    """
    Global upsert identity: stripped invoice number + invoice date (no billing_session scope).

    Invoice numbers may be numeric-only or alphanumeric; matching uses the stripped string
    (max 100 chars, case-sensitive). If either part is missing, returns None (always insert).

    On match, the existing row's ``billing_session`` is updated to the session for the
    current upload.
    """
    num = str(raw_invoice_number or "").strip()[:100]
    if not num or invoice_date is None:
        return None
    return (num, invoice_date)


def _utility_invoice_values_from_parser(session: BillingSession | None, r: dict[str, Any]) -> dict[str, Any]:
    """Field values for UtilityInvoice create/update from parser output."""
    export_energy = r.get("export_energy_kwh") or r.get("export_energy")
    export_energy_dec = _decimal_or_none(export_energy)
    export_energy_cost_dec = _decimal_or_none(r.get("export_energy_cost"))
    unit_rate_dec = _decimal_or_none(r.get("unit_rate"))
    calculated_unit_rate = compute_calculated_unit_rate(export_energy_dec, export_energy_cost_dec)
    anomaly_flag = build_anomaly_flag_json(unit_rate_dec, calculated_unit_rate)
    recurring_dec = _decimal_or_none(r.get("recurring_charges"))
    net_unit_rate = compute_net_unit_rate(export_energy_dec, export_energy_cost_dec, recurring_dec)
    current_charges_excl = _decimal_or_none(r.get("current_charges_excl_gst"))
    page_scores = r.get("page_scores")
    block_conf = r.get("block_confidence")
    if not isinstance(page_scores, dict):
        page_scores = {}
    if not isinstance(block_conf, dict):
        block_conf = {}
    snapshot = parser_result_to_json_snapshot(r)
    merged_blocks: dict[str, Any] = {**block_conf, "full_parse_result": snapshot}
    return {
        "invoice_record_type": "utility_parsed",
        "billing_session": session,
        "account_no": str(r.get("account_number") or "")[:64],
        "asset_code": _asset_code_from_result(r),
        "invoice_number": str(r.get("invoice_number") or "").strip()[:100],
        "vendor_key": str(r.get("vendor") or "")[:100],
        "invoice_date": _parse_invoice_date(r.get("invoice_date")),
        "period_start": _parse_invoice_date(r.get("period_start")),
        "period_end": _parse_invoice_date(r.get("period_end")),
        "currency_code": str(r.get("currency_code") or "")[:8],
        "total_amount": _decimal_or_none(r.get("total_amount")),
        "export_energy": export_energy_dec,
        "export_energy_cost": export_energy_cost_dec,
        "recurring_charges_dollars": recurring_dec,
        "unit_rate": unit_rate_dec,
        "calculated_unit_rate": calculated_unit_rate,
        "anomaly_flag": anomaly_flag,
        "current_charges_excl_gst": current_charges_excl,
        "net_unit_rate": net_unit_rate,
        "gst_rate": _decimal_or_none(r.get("gst_rate")),
        "raw_text": str(r.get("raw_text") or ""),
        "parse_extraction_path": str(r.get("extraction_path") or "")[:16],
        "parse_document_confidence_score": _decimal_or_none(r.get("confidence_score")),
        "parse_document_confidence_level": str(r.get("confidence_flag") or "")[:16],
        "parse_page_scores_json": page_scores,
        "parse_block_confidence_json": merged_blocks,
    }


def _values_equal(a: Any, b: Any) -> bool:
    return _json_safe_value(a) == _json_safe_value(b)


def _build_pending_patch(util: UtilityInvoice, proposed: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for k, v in proposed.items():
        if k in {"billing_session"}:
            continue
        current = getattr(util, k, None)
        if _values_equal(current, v):
            continue
        patch[k] = _json_safe_value(v)
    return patch


def persist_parsed_and_utility_for_session(
    session: BillingSession,
    results: list[dict[str, Any]],
    *,
    billing_invoice_pdf_ids: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Upsert ParsedInvoice (subset) + UtilityInvoice (full row) per parser result.

    Same invoice = same (stripped invoice number, invoice date) globally—not scoped to
    billing_session. If a row already exists, it is updated and ``billing_session`` is set
    to this upload's session.

    If invoice number is blank or invoice_date could not be parsed, always inserts a new row.
    """
    batch_keys: set[tuple[str, date]] = set()
    for r in results:
        idate = _parse_invoice_date(r.get("invoice_date"))
        bk = invoice_number_date_upsert_key(r.get("invoice_number"), idate)
        if bk:
            batch_keys.add(bk)

    dates = {k[1] for k in batch_keys}
    parsed_by_key: dict[tuple[str, date], ParsedInvoice] = {}
    if dates:
        for pi in ParsedInvoice.objects.filter(invoice_date__in=dates).order_by("created_at"):
            k = invoice_number_date_upsert_key(pi.invoice_number, pi.invoice_date)
            if k in batch_keys:
                parsed_by_key[k] = pi

    utility_by_key: dict[tuple[str, date], UtilityInvoice] = {}
    if dates:
        for ui in UtilityInvoice.objects.filter(
            invoice_record_type="utility_parsed",
            invoice_date__in=dates,
        ).order_by("created_at"):
            k = invoice_number_date_upsert_key(ui.invoice_number, ui.invoice_date)
            if k in batch_keys:
                utility_by_key[k] = ui

    created_parsed: list[str] = []
    created_utility: list[str] = []
    billing_pdf_rows: list[BillingInvoicePdf | None] = []
    if billing_invoice_pdf_ids:
        for rid in billing_invoice_pdf_ids:
            billing_pdf_rows.append(BillingInvoicePdf.objects.filter(id=rid).first())

    for r in results:
        idx = len(created_parsed)
        billing_pdf_row = billing_pdf_rows[idx] if idx < len(billing_pdf_rows) else None
        invoice_number_display = str(r.get("invoice_number") or "").strip()[:100]
        invoice_date = _parse_invoice_date(r.get("invoice_date"))
        export_energy = r.get("export_energy_kwh") or r.get("export_energy")
        try:
            export_energy_decimal = Decimal(str(export_energy)) if export_energy not in (None, "") else None
        except Exception:
            export_energy_decimal = None
        raw_text = str(r.get("raw_text") or "")[:20000]

        match_key = invoice_number_date_upsert_key(r.get("invoice_number"), invoice_date)
        if match_key and match_key in parsed_by_key:
            parsed = parsed_by_key[match_key]
            parsed.billing_session = session
            parsed.invoice_number = invoice_number_display
            parsed.invoice_date = invoice_date
            parsed.export_energy = export_energy_decimal
            parsed.raw_text = raw_text
            parsed.save(
                update_fields=[
                    "billing_session",
                    "invoice_number",
                    "invoice_date",
                    "export_energy",
                    "raw_text",
                ]
            )
        else:
            parsed = ParsedInvoice.objects.create(
                billing_session=session,
                invoice_number=invoice_number_display,
                invoice_date=invoice_date,
                export_energy=export_energy_decimal,
                raw_text=raw_text,
            )
            if match_key:
                parsed_by_key[match_key] = parsed

        created_parsed.append(str(parsed.id))

        uvals = _utility_invoice_values_from_parser(session, r)
        if match_key and match_key in utility_by_key:
            util = utility_by_key[match_key]
            patch = _build_pending_patch(util, uvals)
            if patch:
                util.has_pending_merge = True
                # Always attach this upload to the current session so the session detail API lists the row.
                util.billing_session = session
                util.save(update_fields=["has_pending_merge", "billing_session"])
                if billing_pdf_row is not None:
                    generation_impact_fields = {
                        "invoice_number",
                        "invoice_date",
                        "period_start",
                        "period_end",
                        "total_amount",
                        "export_energy",
                        "export_energy_cost",
                        "unit_rate",
                        "gst_rate",
                        "current_charges_excl_gst",
                        "recurring_charges_dollars",
                        "net_unit_rate",
                        "calculated_unit_rate",
                        "asset_code",
                        "vendor_key",
                        "account_no",
                    }
                    billing_pdf_row.pending_utility_patch_json = {
                        "utility_invoice_id": str(util.id),
                        **patch,
                    }
                    billing_pdf_row.frozen_data_changed = any(k in generation_impact_fields for k in patch.keys())
                    billing_pdf_row.save(update_fields=["pending_utility_patch_json", "frozen_data_changed"])
            else:
                util.has_pending_merge = False
                util.billing_session = session
                util.billing_invoice_pdf = billing_pdf_row or util.billing_invoice_pdf
                util.parsed_invoice = parsed
                util.save(update_fields=["has_pending_merge", "billing_session", "billing_invoice_pdf", "parsed_invoice"])
                if billing_pdf_row is not None:
                    billing_pdf_row.pending_utility_patch_json = {}
                    billing_pdf_row.frozen_data_changed = False
                    billing_pdf_row.save(update_fields=["pending_utility_patch_json", "frozen_data_changed"])
        else:
            util = UtilityInvoice.objects.create(
                billing_invoice_pdf=billing_pdf_row,
                has_pending_merge=False,
                parsed_invoice=parsed,
                **uvals,
            )
            if match_key:
                utility_by_key[match_key] = util
            if billing_pdf_row is not None:
                billing_pdf_row.pending_utility_patch_json = {}
                billing_pdf_row.frozen_data_changed = False
                billing_pdf_row.save(update_fields=["pending_utility_patch_json", "frozen_data_changed"])

        created_utility.append(str(util.id))

    return created_parsed, created_utility


def sharepoint_upload_utility_batch(
    session: BillingSession | None,
    paths_for_parse: list[str],
    display_names: list[str],
    results: list[dict[str, Any]],
    *,
    performed_by: str = "system",
) -> list[str]:
    """
    Upload each local PDF to SharePoint using the same path logic as before.
    Call only after parsing (and DB persistence) is complete. Does not delete local files.
    """
    uploaded_paths: list[str] = []
    for idx, p in enumerate(paths_for_parse):
        parsed_result = results[idx] if idx < len(results) else {}
        asset_hint = (
            (session.asset_list[0] if session and isinstance(session.asset_list, list) and session.asset_list else None)
            or parsed_result.get("asset_name")
            or parsed_result.get("site_address")
            or "asset"
        )
        invoice_hint = parsed_result.get("invoice_number") or f"inv_{idx + 1}"
        orig_name = display_names[idx] if idx < len(display_names) else os.path.basename(p)
        remote_path = build_utility_invoice_remote_path(
            country=(session.country if session else "SG"),
            start_date=(session.start_date if session else None),
            end_date=(session.end_date if session else None),
            asset_name=str(asset_hint),
            invoice_number=str(invoice_hint),
            file_name=orig_name,
        )
        try:
            transfer_meta = upload_file_to_sharepoint(p, remote_path)
            uploaded_paths.append(transfer_meta["sharepoint_remote_path"])
            if session:
                BillingAuditLog.objects.create(
                    billing_session=session,
                    action="SHAREPOINT_UPLOAD_UTILITY_INVOICE",
                    performed_by=performed_by,
                    details=transfer_meta,
                )
        except Exception as exc:
            if session:
                BillingAuditLog.objects.create(
                    billing_session=session,
                    action="SHAREPOINT_UPLOAD_UTILITY_INVOICE_FAILED",
                    performed_by=performed_by,
                    details={"error": str(exc), "local_path": p, "sharepoint_remote_path": remote_path},
                )
    return uploaded_paths
