#!/usr/bin/env python3
"""
Pre-download EasyOCR English models into a fixed directory for Docker image bake-in.

Usage (build time):
  export EASYOCR_MODEL_DIR=/opt/easyocr/model   # default if unset
  python scripts/download_easyocr_models.py

Runtime (container):
  Set EASYOCR_MODEL_DIR to match the bake path. EASYOCR_DOWNLOAD defaults to 1 so missing weights
  can still be fetched (avoids startup failure). Use EASYOCR_DOWNLOAD=0 only when the network is blocked
  and models are fully baked under EASYOCR_MODEL_DIR.

Do not commit model binaries to git; keep them inside the built image layer instead.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    model_dir = os.environ.get("EASYOCR_MODEL_DIR", "/opt/easyocr/model").strip()
    os.makedirs(model_dir, exist_ok=True)

    import easyocr

    print(f"Downloading EasyOCR [en] models into {model_dir} …")
    easyocr.Reader(
        ["en"],
        gpu=False,
        model_storage_directory=model_dir,
        download_enabled=True,
        verbose=True,
    )
    print("EasyOCR model download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
