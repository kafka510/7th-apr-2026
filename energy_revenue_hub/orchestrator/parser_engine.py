"""
Master Parser Orchestrator – 100% in-house invoice parsing.

Pipeline:
  PDF → Text extraction → Vendor detection → Vendor template parser → Validation → Result

No OpenAI. Deterministic. Suitable for SP Singapore, KEPCO Korea, Japan utilities, Taipower Taiwan, generic.
"""

from typing import Any, Dict
import os
import re
import tempfile

from energy_revenue_hub.engines import (
    extract_text,
    extract_words,
    extract_tables,
    detect_vendor,
    validate_invoice,
)
from energy_revenue_hub.parsers import (
    GenericParser,
    SPSingaporeParser,
    KepcoKoreaParser,
    JapanUtilityParser,
    TaipowerParser,
)

# Vendor key -> parser class
PARSER_MAP = {
    "SP_SINGAPORE": SPSingaporeParser,
    "KEPCO_KOREA": KepcoKoreaParser,
    "JAPAN_UTILITY": JapanUtilityParser,
    "TAIPOWER_TAIWAN": TaipowerParser,
    "GENERIC": GenericParser,
}


def _get_parser(vendor: str):
    """Return parser instance for vendor key."""
    cls = PARSER_MAP.get(vendor) or GenericParser
    return cls()


def reconstruct_tables_from_text(text: str):
    """
    Rebuild a pseudo table from OCR text when PDF layout is missing.
    Special handling:
      - Attach numeric cells after the 'Export of Electricity' label so that
        the export row stays together.
      - Otherwise, group nearby numeric-ish lines into rows of 3 cells.
    """
    if not text:
        return []

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    table = []
    row: list[str] = []
    attach_next_numbers = False

    for line in lines:
        lower = line.lower()

        # Detect export label – start a new row anchored on the label.
        if "export of electricity" in lower:
            if row:
                table.append(row)
            row = [line]
            attach_next_numbers = True
            continue

        # Capture numbers immediately after the export label so that the
        # reconstructed row becomes:
        # ["Export of Electricity (Net kWh)", "<kWh>", "<rate>", "<amount>"]
        if attach_next_numbers and re.search(r"\d", line):
            row.append(line)
            # After 3 numeric-ish cells, we consider the export row complete.
            if len(row) >= 4:
                table.append(row)
                row = []
                attach_next_numbers = False
            continue

        # Normal numeric grouping when not in the export block.
        if re.search(r"\d", line):
            row.append(line)
            if len(row) >= 3:
                table.append(row)
                row = []
        else:
            if row:
                table.append(row)
                row = []

    if row:
        table.append(row)

    return [table] if table else []


def run_invoice_parser(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Parse invoice PDF bytes through the full in-house pipeline.

    Returns result dict with vendor, invoice_template_version, parser_version,
    and all standard fields (account_number, invoice_number, invoice_date, ...).
    Validation errors are appended to result["errors"]; parsing still returns.
    """
    result: Dict[str, Any] = {
        "vendor": None,
        "invoice_template_version": None,
        "parser_version": "1.0",
        "account_number": None,
        "invoice_number": None,
        "invoice_date": None,
        "invoice_period": None,
        "period_start": None,
        "period_end": None,
        "invoice_month": None,
        "bill_date": None,
        "export_energy_kwh": None,
        "export_energy_cost": None,
        "recurring_charges": None,
        "site_address": None,
        "raw_text": "",
        "errors": [],
    }

    # 1. Read bytes
    if not pdf_bytes:
        result["errors"].append("No PDF data provided.")
        return result

    # 2. Text extraction (pdfplumber + EasyOCR fallback)
    try:
        # print("ORCHESTRATOR STARTED")
        text = extract_text(pdf_bytes)
    except Exception as e:
        result["errors"].append(f"Text extraction failed: {e}")
        return result

    if not (text or "").strip():
        result["errors"].append(
            "No text extracted from PDF. If the file is scanned or image-only, install pymupdf and easyocr "
            "on the Celery worker (same image as requirements.txt) and rebuild."
        )
        return result

    result["raw_text"] = text[:2000]

    # 3. Layout (optional – for future layout-based parsing)
    try:
        words = extract_words(pdf_bytes)
    except Exception:
        words = None

    # 3b. Tables (optional – for table-aware parsing)
    try:
        tables = extract_tables(pdf_bytes)
    except Exception:
        tables = None

    # ------------------------------------------
    # OCR Layout Reconstruction Fallback
    # ------------------------------------------
    if not words and not tables:
        # print("[WARNING] No layout detected -- reconstructing table from OCR text")
        tables = reconstruct_tables_from_text(text)

    # print("\n================ ORCHESTRATOR DEBUG ================")
    # print("TEXT LENGTH:", len(text))
    # print("WORDS COUNT:", len(words) if words else 0)
    # print("TABLE COUNT:", len(tables) if tables else 0)
    # if tables:
    #     for i, t in enumerate(tables):
    #         print(f"\n--- TABLE {i+1} ---")
    #         for r in t:
    #             print(r)
    # print("====================================================\n")

    # 4. Vendor detection
    vendor = detect_vendor(text)

    # 5. Vendor template parser
    parser = _get_parser(vendor)

    # Some parsers (like SPSingaporeParser) can benefit from a temp PDF path for OCR fallbacks.
    pdf_tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            pdf_tmp_path = tmp.name

        parsed = parser.parse(text, words=words, tables=tables, pdf_path=pdf_tmp_path)

        # Merge into result (parsed has same keys + vendor/template/parser_version)
        for key, value in parsed.items():
            if value is not None and (value != "" or key in ("invoice_number", "raw_text")):
                result[key] = value
        result["vendor"] = result.get("vendor") or vendor
        result["invoice_template_version"] = result.get("invoice_template_version") or getattr(
            parser, "template_version", "1.0"
        )
        result["parser_version"] = result.get("parser_version") or "1.0"
    except Exception as e:
        result["errors"].append(f"Parser failed: {e}")
        return result
    finally:
        if pdf_tmp_path and os.path.exists(pdf_tmp_path):
            try:
                os.remove(pdf_tmp_path)
            except OSError:
                pass

    # 6. Validation (non-blocking: append to errors)
    try:
        validate_invoice(result)
    except ValueError as e:
        result["errors"].append(str(e))

    return result


def run_invoice_parser_from_file(file) -> Dict[str, Any]:
    """
    Same as run_invoice_parser but accepts a file-like object or path.
    Used by the API (multipart upload) and backward compatibility.
    """
    try:
        if hasattr(file, "read"):
            pdf_bytes = file.read()
            if hasattr(file, "seek"):
                file.seek(0)
        else:
            with open(file, "rb") as f:
                pdf_bytes = f.read()
    except Exception as e:
        return {
            "vendor": None,
            "invoice_template_version": None,
            "parser_version": "1.0",
            "account_number": None,
            "invoice_number": None,
            "invoice_date": None,
            "invoice_period": None,
            "period_start": None,
            "period_end": None,
            "invoice_month": None,
            "bill_date": None,
            "export_energy_kwh": None,
            "export_energy_cost": None,
            "recurring_charges": None,
            "site_address": None,
            "raw_text": "",
            "errors": [f"Failed to read PDF: {e}"],
        }

    return run_invoice_parser(pdf_bytes)
