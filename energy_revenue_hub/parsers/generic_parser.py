from __future__ import annotations

"""
Very simple generic fallback parser.

Used when vendor detection cannot confidently map to a specific template.
"""

import re
from typing import Any, Dict, Optional

from .base_parser import BaseInvoiceParser, empty_result, parse_date


class GenericParser(BaseInvoiceParser):
    vendor_key = "GENERIC"

    def parse(self, text: str, words=None, tables=None, pdf_path=None, **kwargs) -> Dict[str, Any]:
        result = empty_result()
        result["vendor"] = self.vendor_key
        if not text:
            return result

        t = text or ""

        # Very lightweight heuristics for account/invoice/date.
        m = re.search(r"Account\s*No\.?\s*[:\-]?\s*\n?\s*([0-9]{6,})", t, re.I)
        if m:
            result["account_number"] = m.group(1).strip()

        m = re.search(r"Invoice\s*(?:No)?\.?\s*[:\-]?\s*\n?\s*([0-9]{6,})", t, re.I)
        if m:
            result["invoice_number"] = m.group(1).strip()

        m = re.search(r"Bill\s+Dated\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", t, re.I)
        if m:
            result["invoice_date"] = parse_date(m.group(1))

        result["raw_text"] = t[:2000]
        return result

