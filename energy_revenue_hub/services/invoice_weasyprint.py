"""
Render ERH invoice PDFs from Django HTML templates using WeasyPrint (sg_ppa_maiora).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.template import engines

from energy_revenue_hub.models import BillingSession

logger = logging.getLogger(__name__)

HTML_TEMPLATE_BY_KEY: dict[str, str] = {
    "maiora_escalated": "energy_revenue_hub/invoice_templates/sg_ppa_maiora/invoice_maiora_escalated.html",
}


def render_invoice_html_pdf(
    file_path: str,
    template_key: str,
    snapshot: dict[str, Any],
    session: BillingSession,
) -> None:
    """
    Write a PDF to ``file_path`` using WeasyPrint.

    Raises ImportError if WeasyPrint is not installed.
    """
    template_rel_path = HTML_TEMPLATE_BY_KEY.get(template_key)
    if not template_rel_path:
        raise ValueError(f"No HTML template registered for key={template_key!r}")

    try:
        from weasyprint import HTML
    except ImportError as e:
        raise ImportError(
            "WeasyPrint is required for Maiora HTML invoices. Install with: pip install weasyprint"
        ) from e

    context = {
        "snapshot": snapshot,
        "session": session,
    }
    template_path = Path(settings.BASE_DIR) / template_rel_path
    if not template_path.exists():
        raise FileNotFoundError(f"Invoice template file not found: {template_path}")
    template_text = template_path.read_text(encoding="utf-8")
    template = engines["django"].from_string(template_text)
    html_string = template.render(context)
    base_url = Path(settings.BASE_DIR).as_uri() + "/"
    HTML(string=html_string, base_url=base_url).write_pdf(file_path)
    logger.info("WeasyPrint PDF written: %s (template=%s)", file_path, template_key)
