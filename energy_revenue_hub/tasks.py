from __future__ import annotations

import base64
import logging
import os
import tempfile
import time
import traceback
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from energy_revenue_hub.models import BillingInvoicePdf, BillingLineItem, BillingSession
from energy_revenue_hub.services.billing_cycle import contract_covers_billing_month
from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from main.models import AssetList, assets_contracts
from energy_revenue_hub.services.billing_service import effective_session_asset_codes, generate_billing_table
from energy_revenue_hub.services.hybrid_engine import parse_multiple_invoices, run_hybrid_engine
from energy_revenue_hub.services.invoice_parse_persistence import (
    persist_parsed_and_utility_for_session,
    sharepoint_upload_utility_batch,
)
from main.models import log_loss_task_completed, log_loss_task_started
from main.permissions import user_has_capability

logger = logging.getLogger(__name__)


def _forbidden_task_result(task_id: str, message: str = "Forbidden") -> dict[str, Any]:
    log_loss_task_completed(task_id=task_id, success=False, error_message=message)
    return {"success": False, "error": {"message": message, "error_code": "FORBIDDEN"}}


def _require_task_user_capability(task_id: str, user_id: int | None, capability: str) -> dict[str, Any] | None:
    if not user_id:
        return _forbidden_task_result(task_id, "Missing user context for this task.")
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user or not user_has_capability(user, capability):
        return _forbidden_task_result(task_id, "Forbidden")
    return None


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


@shared_task(bind=True)
def erh_generate_billing_table_task(
    self,
    session_id: str,
    export_kwh: float = 0,
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    task_id = self.request.id
    log_loss_task_started(task_id=task_id)
    try:
        deny = _require_task_user_capability(task_id, user_id, "erh.generate.billing_table")
        if deny:
            return deny
        session = BillingSession.objects.get(id=session_id)
        username = ""
        if user_id:
            User = get_user_model()
            u = User.objects.filter(id=user_id).first()
            if u:
                username = (getattr(u, "username", None) or "") or ""
        items, error, write_stats = generate_billing_table(
            session, export_kwh=export_kwh, performed_by=username
        )
        if error:
            log_loss_task_completed(task_id=task_id, success=False, error_message=error.get("message", "Failed to generate billing table"))
            return {"success": False, "error": error}
        log_loss_task_completed(task_id=task_id, success=True)
        session.refresh_from_db()
        included = sorted(
            {
                str(r.get("asset_code") or "").strip()
                for r in (items or [])
                if str(r.get("asset_code") or "").strip()
            }
        )
        scope = effective_session_asset_codes(session)
        skipped = [c for c in scope if c and c not in set(included)]
        logger.info(
            "erh_generate_billing_table_task_ok session_id=%s billing_table_write=%s included=%s skipped=%s",
            session_id,
            write_stats,
            len(included),
            len(skipped),
        )
        return {
            "success": True,
            "line_items": items or [],
            "status": session.status,
            "billing_table_write": write_stats or {},
            "included_asset_codes": included,
            "skipped_asset_codes": skipped,
            "included_assets_count": len(included),
            "skipped_assets_count": len(skipped),
        }
    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("erh_generate_invoice_task failed for session_id=%s", session_id)
        log_loss_task_completed(task_id=task_id, success=False, error_message=str(exc))
        return {"success": False, "error": {"message": str(exc), "error_code": "TASK_FAILED", "traceback": tb}}


@shared_task(bind=True)
def erh_generate_invoice_task(self, session_id: str, performed_by: str = "", *, user_id: int | None = None) -> dict[str, Any]:
    task_id = self.request.id
    log_loss_task_started(task_id=task_id)
    try:
        from energy_revenue_hub.services.invoice_service import generate_invoice_pdf

        deny = _require_task_user_capability(task_id, user_id, "erh.generate.pdf")
        if deny:
            return deny
        session = BillingSession.objects.get(id=session_id)
        generated_batch, failures, error = generate_invoice_pdf(session, performed_by=performed_by)
        if error:
            log_loss_task_completed(task_id=task_id, success=False, error_message=error.get("message", "Invoice generation failed"))
            return {"success": False, "error": error}
        log_loss_task_completed(task_id=task_id, success=True)
        # Helpful UX: included vs skipped assets for this session run.
        def _effective_codes() -> list[str]:
            bm = getattr(session, "billing_month", None) or getattr(session, "start_date", None)
            if bm is None:
                return []
            bm_first = date(bm.year, bm.month, 1)
            ct = normalize_contract_type_key(getattr(session, "billing_contract_type", "") or "")
            country = (getattr(session, "country", "") or "").strip()
            codes: list[str] = []
            if ct:
                for ac in assets_contracts.objects.all():
                    if normalize_contract_type_key(getattr(ac, "contract_type", None)) != ct:
                        continue
                    if not contract_covers_billing_month(ac, bm_first):
                        continue
                    code = (getattr(ac, "asset_code", None) or "").strip()
                    if not code:
                        continue
                    al = AssetList.objects.filter(asset_code=code).only("country").first()
                    if country and al and (al.country or "").strip() and (al.country or "").strip() != country:
                        continue
                    codes.append(code)
            for raw in (session.asset_list or []):
                if isinstance(raw, str):
                    code = raw.strip()
                elif isinstance(raw, dict):
                    code = str(raw.get("asset_code") or raw.get("code") or "").strip()
                else:
                    code = str(raw or "").strip()
                if code:
                    codes.append(code)
            return sorted(set(c for c in codes if c))

        attempted = sorted(
            set(
                [str(g.invoice_snapshot_json.get("asset_code") or "").strip() for g in (generated_batch or []) if getattr(g, "invoice_snapshot_json", None)]
                + [str(f.get("asset_code") or "").strip() for f in (failures or []) if str(f.get("asset_code") or "").strip()]
            )
        )
        scope = _effective_codes()
        skipped = [c for c in scope if c and c not in set(attempted)]

        first = (generated_batch or [None])[0]
        return {
            "success": True,
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
        }
    except Exception as exc:
        log_loss_task_completed(task_id=task_id, success=False, error_message=str(exc))
        return {"success": False, "error": {"message": str(exc), "error_code": "TASK_FAILED"}}


@shared_task(bind=True)
def erh_generate_line_item_invoice_task(
    self,
    line_item_id: str,
    performed_by: str = "",
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Generate PDF(s) for the billing line group sharing the same asset + utility PDF as the anchor line.
    Runs on a Celery worker so the web process does not block during render / SharePoint.
    """
    task_id = self.request.id
    log_loss_task_started(task_id=task_id)
    try:
        from energy_revenue_hub.services.invoice_service import generate_invoice_pdf, line_items_sharing_utility_pdf_with

        deny = _require_task_user_capability(task_id, user_id, "erh.generate.pdf")
        if deny:
            return deny

        try:
            row = BillingLineItem.objects.select_related("billing_session").get(id=line_item_id)
        except BillingLineItem.DoesNotExist:
            log_loss_task_completed(task_id=task_id, success=False, error_message="Billing line not found")
            return {"success": False, "error": {"message": "Billing line not found", "error_code": "NOT_FOUND"}}

        session = row.billing_session
        from energy_revenue_hub.views import _line_item_invoice_hard_blockers

        line_hard = _line_item_invoice_hard_blockers(session, row)
        if line_hard:
            msgs = " | ".join(str(b.get("message") or b.get("code") or "") for b in line_hard).strip()
            log_loss_task_completed(task_id=task_id, success=False, error_message=msgs or "GENERATION_BLOCKED")
            return {"success": False, "error": {"message": msgs or "Invoice generation blocked.", "error_code": "GENERATION_BLOCKED"}}

        expanded = line_items_sharing_utility_pdf_with(session, row)
        expanded_ids = [str(li.id) for li in expanded]
        logger.info(
            "erh_generate_line_item_invoice_task start line_item_id=%s session_id=%s expanded_count=%s",
            line_item_id,
            str(session.id),
            len(expanded_ids),
        )
        generated_batch, failures, error = generate_invoice_pdf(
            session,
            performed_by=performed_by,
            target_line_item_ids=expanded_ids,
        )
        if error:
            log_loss_task_completed(task_id=task_id, success=False, error_message=error.get("message", "Invoice generation failed"))
            return {"success": False, "error": error}

        for finfo in failures or []:
            logger.warning(
                "erh_generate_line_item_invoice_task asset_failure session_id=%s anchor=%s asset=%s error=%s message=%s",
                str(session.id),
                line_item_id,
                finfo.get("asset_code") or finfo.get("asset_name"),
                finfo.get("error"),
                finfo.get("message"),
            )
        log_loss_task_completed(task_id=task_id, success=True)
        return {
            "success": True,
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
        }
    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("erh_generate_line_item_invoice_task failed line_item_id=%s", line_item_id)
        log_loss_task_completed(task_id=task_id, success=False, error_message=str(exc))
        return {"success": False, "error": {"message": str(exc), "error_code": "TASK_FAILED", "traceback": tb}}


@shared_task(bind=True)
def erh_parse_invoice_files_task(
    self,
    temp_file_paths: list[str] | None = None,
    session_id: str | None = None,
    *,
    pdf_b64_list: list[str] | None = None,
    original_filenames: list[str] | None = None,
    billing_invoice_pdf_ids: list[str] | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Parse utility invoice PDF(s) on the Celery worker.

    Phases:
      1. Parse all PDFs and persist ParsedInvoice + UtilityInvoice (when session_id is set).
      2. Upload all local PDFs to SharePoint (after every file has been parsed).
      3. Remove worker temp files (phase 3 runs in ``finally``).

    Prefer **pdf_b64_list** so the worker does not rely on a shared filesystem with the web process.

    Legacy **temp_file_paths** is still supported when web and worker share MEDIA_ROOT.
    """
    task_id = self.request.id
    log_loss_task_started(task_id=task_id)
    opened = []
    worker_created_paths: list[str] = []
    paths_for_parse: list[str] = []
    display_names: list[str] = []
    billing_pdf_rows: list[BillingInvoicePdf] = []
    started_at = time.monotonic()
    parse_seconds = 0.0
    persist_seconds = 0.0
    upload_seconds = 0.0

    def _mark_rows_failed(message: str) -> None:
        for row in billing_pdf_rows:
            try:
                row.parse_status = "failed"
                row.parse_summary_status = "failed"
                row.parse_error = str(message)[:2000]
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
    try:
        deny = _require_task_user_capability(task_id, user_id, "erh.parse.run")
        if deny:
            return deny
        if billing_invoice_pdf_ids:
            for rid in billing_invoice_pdf_ids:
                row = BillingInvoicePdf.objects.filter(id=rid).first()
                if row:
                    billing_pdf_rows.append(row)
            for row in billing_pdf_rows:
                row.parse_status = "parsing"
                row.transfer_status = BillingInvoicePdf.TransferStatus.PARSING
                row.parse_task_id = task_id or ""
                row.parse_started_at = timezone.now()
                row.parse_completed_at = None
                row.parse_elapsed_seconds = None
                row.save(
                    update_fields=[
                        "parse_status",
                        "transfer_status",
                        "parse_task_id",
                        "parse_started_at",
                        "parse_completed_at",
                        "parse_elapsed_seconds",
                    ]
                )

        if pdf_b64_list:
            for idx, b64 in enumerate(pdf_b64_list):
                try:
                    raw = base64.b64decode(b64)
                except Exception as dec_err:
                    _mark_rows_failed(f"Invalid base64 PDF payload: {dec_err}")
                    log_loss_task_completed(task_id=task_id, success=False, error_message=str(dec_err))
                    return {
                        "success": False,
                        "error": {"message": f"Invalid base64 PDF payload at index {idx}: {dec_err}", "error_code": "INVALID_PAYLOAD"},
                    }
                fd, path = tempfile.mkstemp(prefix="erh_parse_", suffix=".pdf")
                try:
                    os.write(fd, raw)
                finally:
                    os.close(fd)
                worker_created_paths.append(path)
                paths_for_parse.append(path)
                names = original_filenames or []
                display_names.append(
                    os.path.basename(names[idx]) if idx < len(names) and names[idx] else f"upload_{idx + 1}.pdf"
                )
        elif temp_file_paths:
            paths_for_parse = list(temp_file_paths)
            display_names = [os.path.basename(p) for p in paths_for_parse]
        else:
            _mark_rows_failed("No PDF input: provide pdf_b64_list or temp_file_paths.")
            log_loss_task_completed(task_id=task_id, success=False, error_message="No PDF input (pdf_b64_list or temp_file_paths)")
            return {
                "success": False,
                "error": {"message": "No PDF input: provide pdf_b64_list or temp_file_paths.", "error_code": "INVALID_PAYLOAD"},
            }

        files = []
        for p in paths_for_parse:
            f = open(p, "rb")
            opened.append(f)
            files.append(f)

        parse_started = time.monotonic()
        if len(files) == 1:
            results = [run_hybrid_engine(files[0])]
        else:
            results = parse_multiple_invoices(files, max_workers=4)
        parse_seconds = max(0.0, time.monotonic() - parse_started)

        for f in opened:
            try:
                f.close()
            except Exception:
                pass
        opened.clear()

        session = BillingSession.objects.get(id=session_id) if session_id else None
        created_ids: list[str] = []
        created_utility_ids: list[str] = []
        if session_id and session:
            persist_started = time.monotonic()
            created_ids, created_utility_ids = persist_parsed_and_utility_for_session(
                session,
                results,
                billing_invoice_pdf_ids=[str(r.id) for r in billing_pdf_rows],
            )
            persist_seconds = max(0.0, time.monotonic() - persist_started)

        upload_started = time.monotonic()
        uploaded_paths = sharepoint_upload_utility_batch(
            session,
            paths_for_parse,
            display_names,
            results,
            performed_by="system",
        )
        upload_seconds = max(0.0, time.monotonic() - upload_started)

        for idx, row in enumerate(billing_pdf_rows):
            remote_path = uploaded_paths[idx] if idx < len(uploaded_paths) else ""
            parsed_result = results[idx] if idx < len(results) and isinstance(results[idx], dict) else {}
            period_end = parsed_result.get("period_end")
            billing_cycle_aligned = True
            billing_cycle_warning_message = ""
            if session is not None and period_end:
                bm = getattr(session, "billing_month", None) or getattr(session, "start_date", None)
                if bm is not None:
                    from calendar import monthrange
                    from datetime import date as _date

                    try:
                        if isinstance(period_end, str):
                            p_end = datetime.fromisoformat(period_end).date()
                        elif isinstance(period_end, datetime):
                            p_end = period_end.date()
                        elif isinstance(period_end, _date):
                            p_end = period_end
                        else:
                            p_end = None
                    except Exception:
                        p_end = None
                    if p_end is not None:
                        ws = _date(bm.year, bm.month, 1)
                        _, ld = monthrange(bm.year, bm.month)
                        we = _date(bm.year, bm.month, ld)
                        billing_cycle_aligned = ws <= p_end <= we
                        if not billing_cycle_aligned:
                            billing_cycle_warning_message = (
                                f"Invoice period ends {p_end.isoformat()}; this session is for "
                                f"{ws.isoformat()} to {we.isoformat()}."
                            )

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

        log_loss_task_completed(task_id=task_id, success=True)
        total_seconds = max(0.0, time.monotonic() - started_at)
        logger.info(
            "ERH parse task timings task_id=%s files=%s parse_s=%.3f persist_s=%.3f upload_s=%.3f total_s=%.3f",
            task_id,
            len(paths_for_parse),
            parse_seconds,
            persist_seconds,
            upload_seconds,
            total_seconds,
        )
        return {
            "success": True,
            "results": results,
            "created_parsed_invoice_ids": created_ids,
            "created_utility_invoice_ids": created_utility_ids,
            "sharepoint_remote_paths": uploaded_paths,
            "timings": {
                "parse_seconds": round(parse_seconds, 3),
                "persist_seconds": round(persist_seconds, 3),
                "sharepoint_upload_seconds": round(upload_seconds, 3),
                "total_seconds": round(total_seconds, 3),
                "file_count": len(paths_for_parse),
            },
        }
    except Exception as exc:
        _mark_rows_failed(str(exc))
        log_loss_task_completed(task_id=task_id, success=False, error_message=str(exc))
        return {"success": False, "error": {"message": str(exc), "error_code": "TASK_FAILED"}}
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass
        for p in worker_created_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        if temp_file_paths and not pdf_b64_list:
            for p in temp_file_paths:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
