from __future__ import annotations

"""
Placeholder Japan utility parser.

Currently delegates to GenericParser; can be specialized later.
"""

from typing import Any, Dict

from .base_parser import BaseInvoiceParser
from .generic_parser import GenericParser


class JapanUtilityParser(BaseInvoiceParser):
    vendor_key = "JAPAN_UTILITY"

    def parse(self, text: str, words=None, tables=None, pdf_path=None, **kwargs) -> Dict[str, Any]:
        generic = GenericParser()
        result = generic.parse(text, words=words, tables=tables, pdf_path=pdf_path, **kwargs)
        result["vendor"] = self.vendor_key
        return result

