from __future__ import annotations

"""
Minimal base parser primitives for Energy Revenue Hub.

These are intentionally lightweight so vendor parsers (SP, KEPCO, Japan,
Taipower, generic) can share a common result shape without pulling in the
original complex implementation.
"""

from datetime import datetime
from typing import Any, Dict, Optional


def parse_number(v: str) -> Optional[float]:
    try:
        s = str(v).replace(",", "").replace("$", "").strip()
        return float(s) if s else None
    except Exception:
        return None


def parse_date(v: str) -> Optional[str]:
    formats = [
        "%d %B %Y",
        "%d %b %Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]
    for f in formats:
        try:
            return datetime.strptime(v.strip(), f).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None


def normalize_invoice_number(v: str) -> str:
    """Strip spaces and keep only digits for invoice numbers."""
    if not v:
        return ""
    s = "".join(ch for ch in str(v) if ch.isdigit())
    return s or str(v).strip()


def empty_result() -> Dict[str, Any]:
    """Common result skeleton used by all vendor parsers."""
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
        "errors": [],
    }


class BaseInvoiceParser:
    """Abstract base class for vendor-specific parsers."""

    vendor_key: str = "GENERIC"
    template_version: str = "1.0"

    def parse(self, text: str, words=None, tables=None, pdf_path=None, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

