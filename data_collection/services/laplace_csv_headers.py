"""
Helpers for Laplace CSV header parsing (device-prefixed vs site-level columns).

Device columns: "{device_code} {oem_tag}" (space-separated).
Site / weather columns: no space (e.g. irradiance, temperature) — map to wst-style devices in onboarding.
"""
from __future__ import annotations

import hashlib
import re
from typing import List, Set, Tuple


def wst_column_device_slug(header: str) -> str:
    """Stable ASCII-ish slug for device_code; preserves mapping via device_type_id = full header."""
    h = (header or "").strip()
    if not h:
        return "wst_site"
    safe = re.sub(r"[^\w\.\-]+", "_", h, flags=re.UNICODE)
    safe = safe.strip("_")[:56]
    if safe:
        return safe
    return "wst_" + hashlib.sha256(h.encode("utf-8")).hexdigest()[:14]


def scan_laplace_csv_header_row(header_cells: List[str]) -> Tuple[Set[str], Set[str]]:
    """
    Parse one CSV header row.
    Returns (device_codes_from_prefixed_columns, site_level_column_headers).
    """
    device_codes: Set[str] = set()
    site_headers: Set[str] = set()
    for col in header_cells:
        s = (col or "").strip()
        if not s or s.lower() == "date":
            continue
        if " " in s:
            code = s.split(" ", 1)[0].strip()
            if code:
                device_codes.add(code)
        else:
            site_headers.add(s)
    return device_codes, site_headers
