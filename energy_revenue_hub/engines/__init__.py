"""
Lightweight extraction/validation engines for Energy Revenue Hub.

These implementations are intentionally simple so the Django app can run
end‑to‑end without the original heavy OCR / layout stack. The SP Singapore
parser already contains robust text/coordinate logic, so these helpers only
need to provide basic text, words, and tables.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Tuple

# One EasyOCR Reader per process (Celery prefork worker); avoids reloading weights on every PDF.
_EASYOCR_LOCK = threading.Lock()
_easyocr_reader = None


def _easyocr_model_dir() -> str | None:
    d = (os.environ.get("EASYOCR_MODEL_DIR") or "").strip()
    return d or None


def _easyocr_download_enabled() -> bool:
    """
    Default EASYOCR_DOWNLOAD=1 so EasyOCR can fetch weights if they are missing (avoids hard failure).

    Set EASYOCR_DOWNLOAD=0 only for air-gapped / strict no-network workers after you are sure
    models exist under EASYOCR_MODEL_DIR.
    """
    flag = (os.environ.get("EASYOCR_DOWNLOAD", "1") or "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return True


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    with _EASYOCR_LOCK:
        if _easyocr_reader is not None:
            return _easyocr_reader
        import easyocr  # type: ignore

        model_dir = _easyocr_model_dir()
        download = _easyocr_download_enabled()
        kwargs: dict[str, Any] = {
            "gpu": False,
            "verbose": False,
            "download_enabled": download,
        }
        if model_dir:
            kwargs["model_storage_directory"] = model_dir
        _easyocr_reader = easyocr.Reader(["en"], **kwargs)
        return _easyocr_reader


def extract_text(pdf_bytes: bytes) -> str:
    """
    Extract plain text from PDF bytes.

    Tries pdfplumber if available, otherwise falls back to PyPDF2.
    If the text is corrupted by embedded CID fonts (e.g., "(cid:48)"),
    discards the gibberish and falls back to EasyOCR (PyMuPDF pixel scraping).
    """
    if not pdf_bytes:
        return ""

    text = ""

    # 1) pdfplumber
    try:
        import io
        import pdfplumber  # type: ignore

        parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
    except Exception:
        text = ""

    # 2) PyPDF2 fallback if still empty
    if not text:
        try:
            import io
            from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(io.BytesIO(pdf_bytes))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).strip()
        except Exception:
            text = ""

    # Check for CID font corruption (unreadable text like '(cid:48)(cid:52)')
    if text and "(cid:" in text:
        # If more than 5% of the string is (cid, it's basically unreadable
        if text.count("(cid:") > len(text) * 0.05:
            text = "" # Wipe it to force OCR

    # 3) OCR fallback for image‑only OR CID-corrupted PDFs (PyMuPDF + EasyOCR)
    if not text:
        missing: list[str] = []
        try:
            import fitz  # type: ignore  # PyMuPDF (pip package: pymupdf)
        except ImportError:
            missing.append("pymupdf")
        try:
            import easyocr  # type: ignore
        except ImportError:
            missing.append("easyocr")
        if missing:
            print(
                "OCR fallback skipped: missing optional packages "
                + ", ".join(missing)
                + " (pip install pymupdf easyocr). Required for scanned/image-only PDFs."
            )
        else:
            try:
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    reader = _get_easyocr_reader()

                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                parts = []
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")
                    result = reader.readtext(img_bytes, detail=0)
                    if result:
                        parts.append(" ".join(result))
                text = "\n".join(parts).strip()
            except Exception as e:
                print("OCR fallback failed:", e)
                text = ""

    return text


def extract_words(pdf_bytes: bytes) -> List[Tuple[float, float, float, float, str]]:
    """
    Return a list of (x0, y0, x1, y1, text) words.

    For now this returns an empty list so that parsers relying purely on text
    (like SP Singapore text fallback) still function. Coordinate‑based parsing
    can be activated later by wiring in a proper layout engine.
    """
    return []


def extract_tables(pdf_bytes: bytes) -> List[Any]:
    """
    Return a list of table structures.

    Current implementation returns an empty list; SP Singapore and other
    parsers already have robust text fallbacks for export and recurring
    detection.
    """
    return []


def detect_vendor(text: str) -> str:
    """
    Very simple vendor detection based on key phrases in the text.

    This mirrors the original intent (SP, KEPCO, Japan, Taipower, generic)
    without any ML dependency.
    """
    t = (text or "").upper()
    if "EXPORT OF ELECTRICITY" in t or "SP SERVICES" in t:
        return "SP_SINGAPORE"
    if "KEPCO" in t or "KOREA ELECTRIC POWER" in t:
        return "KEPCO_KOREA"
    if "TAIPOWER" in t or "TAIWAN POWER" in t:
        return "TAIPOWER_TAIWAN"
    if any(k in t for k in ["TOKYO ELECTRIC", "KANSASAI ELECTRIC", "CHUBU ELECTRIC", "JAPAN"]):
        return "JAPAN_UTILITY"
    return "GENERIC"


def validate_invoice(result: Dict[str, Any]) -> None:
    """
    Placeholder invoice‑level validation hook.

    The SP Singapore parser already performs field‑level validation (rate band,
    export kWh ranges, etc.). This hook can be extended later if needed.
    """
    return None

