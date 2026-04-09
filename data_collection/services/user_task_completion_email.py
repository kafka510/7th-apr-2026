"""
Email the user when a manually queued background task finishes.

Triggered from Celery task_postrun when the message includes the custom header
notify_completion_email (set by Background Jobs / Fusion wizard APIs).
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional, Tuple

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

# Celery message header (must match api send_task headers)
NOTIFY_COMPLETION_HEADER = "notify_completion_email"

_MAX_BODY = 12000


def parse_header_recipients(raw: Any) -> List[str]:
    """Normalize header value to a list of email addresses."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        out = [str(x).strip() for x in raw if x is not None and str(x).strip()]
        return [x for x in out if "@" in x]
    s = str(raw).strip()
    if not s or "@" not in s:
        return []
    if "," in s:
        return [p.strip() for p in s.split(",") if p.strip() and "@" in p.strip()]
    return [s]


def _truncate(s: str, max_len: int = _MAX_BODY) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 20] + "\n…(truncated)…"


def _fmt_dict_summary(d: dict, keys: Tuple[str, ...]) -> str:
    lines: List[str] = []
    for k in keys:
        if k in d and d[k] is not None:
            try:
                lines.append(f"{k}: {json.dumps(d[k], default=str)[:4000]}")
            except Exception:
                lines.append(f"{k}: {str(d[k])[:2000]}")
    return "\n".join(lines) if lines else json.dumps(d, default=str)[:4000]


def classify_outcome(task_name: str, state: str, retval: Any) -> Tuple[str, str]:
    """
    Returns (kind, detail) where kind is success | partial | failure.
    """
    st = (state or "").upper()
    if st != "SUCCESS":
        if isinstance(retval, Exception):
            detail = f"{type(retval).__name__}: {retval}"
        else:
            detail = str(retval) if retval is not None else st
        return "failure", _truncate(detail)

    if not isinstance(retval, dict):
        return "success", _truncate(repr(retval))

    if task_name == "data_collection.tasks.run_fusion_solar_oem_daily_kpi":
        if retval.get("success") is False:
            err = retval.get("error")
            if err:
                return "failure", _truncate(str(err))
            return "failure", _truncate(_fmt_dict_summary(retval, ("error", "errors", "message")))
        detail = _fmt_dict_summary(
            retval,
            (
                "date_from",
                "date_to",
                "oem_daily_kpi_rows_updated_total",
                "oem_daily_kpi_assets_with_api_errors",
                "errors",
            ),
        )
        if retval.get("oem_daily_kpi_assets_with_api_errors"):
            return "partial", _truncate(detail)
        results = retval.get("results") or []
        if isinstance(results, list):
            for r in results:
                if isinstance(r, dict) and (
                    r.get("oem_daily_kpi_had_api_errors") or r.get("success") is False
                ):
                    return "partial", _truncate(detail)
        return "success", _truncate(detail)

    if task_name == "data_collection.tasks.run_fusion_solar_backfill":
        detail = _fmt_dict_summary(
            retval,
            (
                "date_from",
                "date_to",
                "success",
                "quota_deferred",
                "deferred_task_id",
                "written",
                "failed_or_missed",
                "errors",
            ),
        )
        if retval.get("quota_deferred"):
            return "partial", _truncate(detail)
        if retval.get("failed_or_missed"):
            return "partial", _truncate(detail)
        if retval.get("errors"):
            return "partial", _truncate(detail)
        if retval.get("success") is False:
            return "failure", _truncate(detail)
        return "success", _truncate(detail)

    if retval.get("success") is False:
        err = retval.get("error")
        if err:
            return "failure", _truncate(str(err))
        return "failure", _truncate(_fmt_dict_summary(retval, ("error", "errors", "message")))

    # Generic: explicit errors list
    errs = retval.get("errors")
    if isinstance(errs, list) and len(errs) > 0:
        keys = tuple(list(retval.keys())[:15])
        return "partial", _truncate(_fmt_dict_summary(retval, keys))

    return "success", _truncate(json.dumps(retval, default=str)[:8000])


def send_completion_email(
    *,
    recipients: List[str],
    task_name: str,
    task_id: Optional[str],
    outcome: str,
    detail: str,
) -> None:
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@localhost"
    subject_map = {
        "success": "Completed successfully",
        "partial": "Completed with warnings",
        "failure": "Failed",
    }
    subject = f"[Background task] {subject_map.get(outcome, 'Finished')}: {task_name}"
    lines = [
        f"Task: {task_name}",
        f"Celery task id: {task_id or 'unknown'}",
        f"Outcome: {outcome.upper()}",
        "",
        "Details:",
        detail,
        "",
        f"— {getattr(settings, 'SITE_NAME', None) or 'Background jobs'}",
    ]
    body = "\n".join(lines)
    try:
        send_mail(subject, body, from_email, recipients, fail_silently=False)
    except Exception:
        logger.exception(
            "Could not send task completion email task=%s recipients=%s",
            task_name,
            recipients,
        )


def maybe_notify_from_postrun(
    *,
    task_name: str,
    task_id: Optional[str],
    task: Any,
    state: Optional[str],
    retval: Any,
) -> None:
    """Read notify header from task.request and send one email if set."""
    req = getattr(task, "request", None)
    if req is None:
        return
    headers = getattr(req, "headers", None)
    if not isinstance(headers, dict):
        return
    raw = headers.get(NOTIFY_COMPLETION_HEADER)
    recipients = parse_header_recipients(raw)
    if not recipients:
        return
    outcome, detail = classify_outcome(task_name, state or "", retval)
    send_completion_email(
        recipients=recipients,
        task_name=task_name,
        task_id=task_id,
        outcome=outcome,
        detail=detail,
    )
