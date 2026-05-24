#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

CONTRACT_PATH = Path("docs/guides/OBSERVABILITY_CONTRACT.md")
REQUIRED_SNIPPETS = [
    "trace_id",
    "event",
    "command",
    "profile",
    "sdd metrics summary",
    "to_otel_attributes",
    "Operator Query Path (MVP)",
]


def main() -> int:
    if not CONTRACT_PATH.exists():
        print(f"FAIL: OBSERVABILITY_CONTRACT_VIOLATION: missing file {CONTRACT_PATH}")
        return 1

    content = CONTRACT_PATH.read_text(encoding="utf-8")
    missing = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in content]
    if missing:
        print("FAIL: OBSERVABILITY_CONTRACT_VIOLATION: missing required snippets")
        for snippet in missing:
            print(f"  - {snippet}")
        return 1

    print("PASS: OBSERVABILITY_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
