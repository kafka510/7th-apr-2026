"""
Build PDF from sdm_array_model_equations.tex using pdflatex.

You must have a LaTeX engine installed:
- Windows: MiKTeX (https://miktex.org/download) or TeX Live
- macOS: MacTeX or brew install --cask mactex
- Linux: texlive-full or texlive-base

This script only invokes the engine; it does not compile LaTeX by itself.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

DOC_DIR = Path(__file__).resolve().parent
TEX_FILE = DOC_DIR / "sdm_array_model_equations.tex"


def find_pdflatex() -> Optional[str]:
    """Return path to pdflatex if available."""
    try:
        out = subprocess.run(
            ["pdflatex", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return "pdflatex"
    except FileNotFoundError:
        pass
    return None


def main() -> int:
    if not TEX_FILE.exists():
        print(f"Error: {TEX_FILE} not found.", file=sys.stderr)
        return 1

    pdflatex = find_pdflatex()
    if not pdflatex:
        print(
            "pdflatex not found. You need to install a LaTeX distribution:\n"
            "  - Windows: MiKTeX  https://miktex.org/download\n"
            "  - macOS:   MacTeX   https://tug.org/mactex/\n"
            "  - Linux:   TeX Live (e.g. sudo apt install texlive-full)\n"
            "Then add the LaTeX bin folder to your PATH and run this script again.",
            file=sys.stderr,
        )
        return 1

    print(f"Using: {pdflatex}")
    print(f"Building: {TEX_FILE.name}")

    # Run twice so table of contents and refs are correct
    for run in (1, 2):
        print(f"  Run {run}/2...")
        result = subprocess.run(
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", TEX_FILE.name],
            cwd=DOC_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(result.stdout, file=sys.stdout)
            print(result.stderr, file=sys.stderr)
            print("Build failed.", file=sys.stderr)
            return 1

    pdf = TEX_FILE.with_suffix(".pdf")
    if pdf.exists():
        print(f"Done: {pdf}")
        return 0
    print("Build completed but PDF not found.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
