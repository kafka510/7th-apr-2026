from __future__ import annotations

"""
Hybrid invoice parsing engine for Energy Revenue Hub.

This module provides the interface expected by the API layer:
  - run_hybrid_engine(file)
  - parse_multiple_invoices(files, max_workers=4)

Internally it delegates to the deterministic in‑house orchestrator
(`run_invoice_parser_from_file`), without introducing any external AI
dependencies.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Tuple

from energy_revenue_hub.orchestrator import run_invoice_parser_from_file


def _run_single(file_obj) -> Dict[str, Any]:
    """
    Helper to run the core parser on a single file‑like object or path.
    """
    # run_invoice_parser_from_file already accepts file‑like objects or paths,
    # so we can delegate directly.
    return run_invoice_parser_from_file(file_obj)


def run_hybrid_engine(file_obj) -> Dict[str, Any]:
    """
    Parse a single uploaded invoice PDF.

    This is the entrypoint used by the `/parse-invoice-pdf/` endpoint when a
    single file is uploaded (form field ``file``).
    """
    return _run_single(file_obj)


def parse_multiple_invoices(files: Iterable, max_workers: int = 4) -> List[Dict[str, Any]]:
    """
    Parse multiple uploaded invoice PDFs in parallel.

    Used by the batch mode of `/parse-invoice-pdf/` when the client uploads
    multiple PDFs via the ``files`` field.
    """
    results: List[Dict[str, Any]] = []
    file_list = list(files)
    if not file_list:
        return results

    # ThreadPool is sufficient here since the heavy work is I/O bound PDF
    # parsing rather than pure Python CPU.
    with ThreadPoolExecutor(max_workers=max_workers or 1) as executor:
        future_to_idx: Dict[Any, int] = {
            executor.submit(_run_single, f): idx for idx, f in enumerate(file_list)
        }
        tmp: List[Tuple[int, Dict[str, Any]]] = []
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                res = future.result()
            except Exception as e:
                res = {"errors": [f"Parser failed: {e}"]}
            tmp.append((idx, res))

    # Preserve original file order
    for _, res in sorted(tmp, key=lambda t: t[0]):
        results.append(res)

    return results

