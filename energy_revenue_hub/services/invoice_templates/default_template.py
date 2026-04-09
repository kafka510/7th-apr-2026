from __future__ import annotations

from typing import Any, List

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer

from energy_revenue_hub.models import BillingSession
from energy_revenue_hub.services.invoice_templates.base import (
    session_header_paragraph,
    table_and_totals_from_snapshot,
)


def build_default_invoice_elements(snapshot: dict[str, Any], session: BillingSession) -> List[Any]:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    elements: List[Any] = [Paragraph("Energy Invoice", title_style), session_header_paragraph(session, styles)]
    elements.append(Spacer(1, 0.3 * inch))
    elements.extend(table_and_totals_from_snapshot(snapshot, styles))
    return elements

