"""
Shared ReportLab helpers for invoice templates.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, List

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from energy_revenue_hub.models import BillingSession


def float_num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def session_header_paragraph(session: BillingSession, styles) -> Paragraph:
    return Paragraph(
        f"<b>Billing Session:</b> {session.id} | <b>Country:</b> {session.country} | <b>Portfolio:</b> {session.portfolio}",
        styles["Normal"],
    )


def table_and_totals_from_snapshot(snapshot: dict[str, Any], styles) -> List[Any]:
    lines = snapshot.get("lines") or []
    totals = snapshot.get("totals") or {}
    tr = float_num(totals.get("revenue"))
    ti = float_num(totals.get("invoice_kwh"))
    te = float_num(totals.get("export_kwh"))

    data = [["Asset", "Actual (kWh)", "Export (kWh)", "Invoice (kWh)", "PPA Rate", "Revenue"]]
    for row in lines:
        data.append(
            [
                row.get("asset_name") or row.get("asset_code") or "-",
                f"{float_num(row.get('actual_kwh')):,.2f}",
                f"{float_num(row.get('export_kwh')):,.2f}" if row.get("export_kwh") not in (None, "") else "-",
                f"{float_num(row.get('invoice_kwh')):,.2f}",
                f"{float_num(row.get('ppa_rate')):,.4f}" if row.get("ppa_rate") not in (None, "") else "-",
                f"{float_num(row.get('revenue')):,.2f}" if row.get("revenue") not in (None, "") else "-",
            ]
        )
    data.append(["Total", "-", f"{te:,.2f}", f"{ti:,.2f}", "-", f"{tr:,.2f}"])

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    out: List[Any] = [table, Spacer(1, 0.2 * inch), Paragraph(f"<b>Total Revenue:</b> {tr:,.2f}", styles["Heading2"])]
    extras = snapshot.get("extras") or {}
    notes = extras.get("notes") if isinstance(extras, dict) else None
    if notes:
        out.extend([Spacer(1, 0.15 * inch), Paragraph(f"<i>{notes}</i>", styles["Normal"])])
    return out


def gst_paragraph_from_extras(snapshot: dict[str, Any], styles) -> Paragraph | None:
    extras = snapshot.get("extras") or {}
    if not isinstance(extras, dict):
        return None
    gst_rate = extras.get("gst_rate")
    if gst_rate is None:
        return None
    try:
        rate = Decimal(str(gst_rate))
        totals = snapshot.get("totals") or {}
        rev = Decimal(str(totals.get("revenue", 0)))
        gst_amt = (rev * rate / Decimal("100")).quantize(Decimal("0.01"))
        return Paragraph(f"<b>GST ({rate}%):</b> {float(gst_amt):,.2f}", styles["Normal"])
    except Exception:
        return None

