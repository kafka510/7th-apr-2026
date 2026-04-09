# pdf_service.py - PV Layout summary PDF (ReportLab).
# Copied from solar-insight backend/services/pdf_service.py for Engineering Tools.

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def generate_layout_pdf(job_id: str, summary: dict, payload: dict, output_path: str) -> None:
    """
    Generate a simple PV Layout summary PDF using ReportLab.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
    )

    story = []

    story.append(Paragraph("PV Layout Summary", title_style))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Site", styles["Heading2"]))
    site = payload.get("site", {})
    story.append(
        Paragraph(
            f"Latitude: {site.get('latitude', '—')} | Longitude: {site.get('longitude', '—')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Layout Summary", styles["Heading2"]))
    data = [
        ["Metric", "Value"],
        ["MMS tables", str(summary.get("tables", 0))],
        ["Modules", str(summary.get("modules", 0))],
        ["Inverters", str(summary.get("inverters", 0))],
        ["Row-to-row pitch (m)", str(summary.get("pitch", "—"))],
    ]
    t = Table(data, colWidths=[80 * mm, 60 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), (0.9, 0.9, 0.9)),
                ("GRID", (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Configuration (request)", styles["Heading2"]))
    mod = payload.get("modules", {})
    mms = payload.get("mms", {})
    el = payload.get("electrical", {})
    config_data = [
        ["Parameter", "Value"],
        ["Module power (Wp)", str(mod.get("power", "—"))],
        ["Module length (m)", str(mod.get("length", "—"))],
        ["Module width (m)", str(mod.get("width", "—"))],
        ["Modules per row", str(mms.get("modules_per_row", "—"))],
        ["Rows per table", str(mms.get("rows", "—"))],
        ["Columns per table", str(mms.get("columns", "—"))],
        ["Number of tables", str(mms.get("tables", "—"))],
        ["Modules per string", str(el.get("modules_per_string", "—"))],
        ["Inverters", str(el.get("inverters", "—"))],
    ]
    t2 = Table(config_data, colWidths=[80 * mm, 60 * mm])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), (0.9, 0.9, 0.9)),
                ("GRID", (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t2)

    doc.build(story)
