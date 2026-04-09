#!/usr/bin/env python3
"""
Guardrail check: detect risky direct JSON parsing patterns in frontend feature API files.

Targets:
- frontend/src/features/**/api.ts

Flags patterns that commonly cause "Unexpected token '<'" when HTML is returned:
- .then((response) => response.json())
- return response.json();
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "frontend" / "src" / "features"
ALLOWLIST_PATH = ROOT / "docs" / "security" / "frontend_api_parsing_allowlist.txt"

PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\.then\(\(response\)\s*=>\s*response\.json\(\)\)"),
    re.compile(r"^\s*return\s+response\.json\(\);\s*$"),
]


def load_allowlist() -> set[str]:
    allowed: set[str] = set()
    if not ALLOWLIST_PATH.exists():
        return allowed
    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        allowed.add(line)
    return allowed


def main() -> int:
    allowed = load_allowlist()
    violations: list[str] = []

    if not TARGET.exists():
        print("OK: frontend features directory not found; skipping.")
        return 0

    for api_file in TARGET.rglob("api.ts"):
        rel = api_file.relative_to(ROOT).as_posix()
        lines = api_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(lines, start=1):
            for pattern in PATTERNS:
                if not pattern.search(line):
                    continue
                location = f"{rel}:{i}"
                if location in allowed:
                    continue
                violations.append(location)

    if violations:
        print("ERROR: risky direct JSON parsing patterns found:")
        for v in violations:
            print(f"  - {v}")
        print("\nRefactor to content-type-safe parsing or explicitly allowlist a line.")
        return 1

    print("OK: no risky direct JSON parsing patterns found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

