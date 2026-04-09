from __future__ import annotations

"""
Placeholder Taipower Taiwan parser.

Currently delegates to GenericParser; can be specialized later.
"""

from typing import Any, Dict

from .base_parser import BaseInvoiceParser
from .generic_parser import GenericParser


class TaipowerParser(BaseInvoiceParser):
    vendor_key = "TAIPOWER_TAIWAN"

    def parse(self, text: str, words=None, tables=None, pdf_path=None, **kwargs) -> Dict[str, Any]:
        generic = GenericParser()
        result = generic.parse(text, words=words, tables=tables, pdf_path=pdf_path, **kwargs)
        result["vendor"] = self.vendor_key
        return result

