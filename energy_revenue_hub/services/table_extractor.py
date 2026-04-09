from __future__ import annotations

"""
Minimal PDF table extractor for Energy Revenue Hub.

The API calls `extract_tables_with_ai(pdf_bytes)` but for now we implement a
deterministic, pdfplumber‑only extractor that returns raw table rows without
any AI post‑processing.
"""

from typing import Any, Dict, List


def extract_tables_with_ai(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract tables from PDF bytes using pdfplumber (if installed).

    Return format:
      {
        "tables": [
          {
            "page": int,
            "rows": [[cell, ...], ...]
          },
          ...
        ]
      }
    """
    tables: List[Dict[str, Any]] = []

    try:
        import io
        import pdfplumber  # type: ignore

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                try:
                    page_tables = page.extract_tables() or []
                except Exception:
                    page_tables = []
                for tbl in page_tables:
                    rows = [[cell for cell in row] for row in tbl]
                    tables.append({"page": page_index, "rows": rows})
    except Exception:
        # If pdfplumber is missing or fails, just return an empty result.
        pass

    return {"tables": tables}

