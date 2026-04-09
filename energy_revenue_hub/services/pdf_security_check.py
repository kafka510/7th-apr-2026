"""
Best-effort PDF upload validation for Energy Revenue Hub (structure + risky feature heuristics).

Uses raw-byte scans (not full PDF parsing). Structured regex checks reduce false positives from
innocuous substrings (e.g. ``/js`` inside compressed streams or unrelated tokens).
"""
from __future__ import annotations

import os
import re

from django.conf import settings

# First N bytes scanned for patterns (encrypted streams may hide content deeper; this is heuristic).
_DEFAULT_SCAN_BYTES = 8 * 1024 * 1024

# JavaScript action: ``<< ... /S /JavaScript ... >>`` (bounded window to avoid pathological matches).
_JS_ACTION_PATTERN = re.compile(
    rb"<<[\s\S]{0,2048}?/S\s*/JavaScript\b[\s\S]{0,2048}?>>",
    re.IGNORECASE,
)

# OpenAction dictionary reference: ``/OpenAction n n R``
_OPEN_ACTION_REF_PATTERN = re.compile(rb"/OpenAction\s+\d+\s+\d+\s+R\b", re.IGNORECASE)

# Encryption dictionary reference in trailer
_ENCRYPT_REF_PATTERN = re.compile(rb"/Encrypt\s+\d+\s+\d+\s+R\b", re.IGNORECASE)

# Link annotations: ``/URI (http...)`` or ``/URI <...>`` — stricter than bare ``/uri`` substring.
_URI_ANNOTATION_PATTERN = re.compile(rb"/URI\s*[\(<]", re.IGNORECASE)

# Embedded file / attachment name trees (common attack surface)
_EMBEDDED_PATTERN = re.compile(
    rb"/(?:EmbeddedFiles|FileAttachment)\b",
    re.IGNORECASE,
)

# Launch / executable actions
_LAUNCH_ACTION_PATTERN = re.compile(rb"<<[\s\S]{0,1024}?/S\s*/Launch\b[\s\S]{0,1024}?>>", re.IGNORECASE)


def validate_pdf_security(file_name: str, raw: bytes) -> tuple[bool, str, str]:
    """
    Return (ok, error_code, user_message). When ok is True, error fields are empty strings.
    """
    base = os.path.basename(file_name or "").strip()
    if not base or not re.fullmatch(r"[A-Za-z0-9._()\-\s+]+", base):
        return False, "SECURITY_FILENAME_INVALID", "Filename failed sanitization rules."
    if not base.lower().endswith(".pdf"):
        return False, "SECURITY_INVALID_EXTENSION", "Only PDF files are accepted."

    max_bytes = int(getattr(settings, "ERH_MAX_UPLOAD_PDF_BYTES", 25 * 1024 * 1024) or (25 * 1024 * 1024))
    if len(raw) > max_bytes:
        return False, "SECURITY_FILE_TOO_LARGE", f"PDF exceeds max allowed size ({max_bytes} bytes)."

    head = raw[:1024]
    if b"%PDF" not in head:
        return False, "SECURITY_INVALID_PDF_HEADER", "Missing PDF header."
    if b"%%EOF" not in raw[-4096:]:
        return False, "SECURITY_MALFORMED_PDF", "Malformed PDF (missing EOF marker)."

    scan_n = min(len(raw), _DEFAULT_SCAN_BYTES)
    scan = raw[:scan_n]

    if _ENCRYPT_REF_PATTERN.search(scan):
        return False, "SECURITY_ENCRYPTED_PDF", "Encrypted/password-protected PDF is not supported."

    if _JS_ACTION_PATTERN.search(scan):
        return False, "SECURITY_EMBEDDED_JS", "PDF contains JavaScript actions."

    if _OPEN_ACTION_REF_PATTERN.search(scan):
        return False, "SECURITY_OPEN_ACTION", "PDF contains OpenAction triggers."

    if _EMBEDDED_PATTERN.search(scan):
        return False, "SECURITY_EMBEDDED_FILES", "PDF contains embedded files/attachments."

    if _LAUNCH_ACTION_PATTERN.search(scan):
        return False, "SECURITY_LAUNCH_ACTION", "PDF contains launch/execute action."

    if _URI_ANNOTATION_PATTERN.search(scan):
        return False, "SECURITY_EMBEDDED_LINKS", "PDF contains embedded link (URI) annotations."

    return True, "", ""
