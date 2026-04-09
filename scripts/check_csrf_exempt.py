#!/usr/bin/env python3
"""
Guardrail check: fail if @csrf_exempt appears in protected modules.

Scope:
- main/**/*.py
- api/**/*.py

By default, legacy files can be allowlisted in docs/security/csrf_exempt_allowlist.txt
with one entry per line:
  relative/path.py
or
  relative/path.py:LINE_NUMBER
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = ROOT / "docs" / "security" / "csrf_exempt_allowlist.txt"
SCAN_DIRS = [ROOT / "main", ROOT / "api"]
DECORATOR_RE = re.compile(r"^\s*@csrf_exempt\b")


def load_allowlist() -> tuple[set[str], set[str]]:
    allowed_files: set[str] = set()
    allowed_locations: set[str] = set()

    if not ALLOWLIST_PATH.exists():
        return allowed_files, allowed_locations

    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            allowed_locations.add(line)
        else:
            allowed_files.add(line)
    return allowed_files, allowed_locations


def main() -> int:
    allowed_files, allowed_locations = load_allowlist()
    violations: list[str] = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            rel = py_file.relative_to(ROOT).as_posix()
            content = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, line in enumerate(content, start=1):
                if not DECORATOR_RE.match(line):
                    continue
                location = f"{rel}:{i}"
                if rel in allowed_files or location in allowed_locations:
                    continue
                violations.append(location)

    if violations:
        print("ERROR: disallowed @csrf_exempt usage found:")
        for v in violations:
            print(f"  - {v}")
        print("\nIf intentional, add an exception in docs/security/csrf_exempt_allowlist.txt")
        return 1

    print("OK: no disallowed @csrf_exempt usage found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

