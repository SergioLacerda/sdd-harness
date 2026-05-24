#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path

PROTOCOL = Path("docs/guides/operations/RUNBOOK_HARDENING_PROTOCOL.md")
REQUIRED_FIELDS = [
    "approved",
    "decision-owner",
    "decision-date",
    "review-cadence",
]
REQUIRED_SNIPPETS = [
    "## Drill Cadence",
    "## Drill Record Template",
    "## SLO Verification",
    "## Postmortem Feedback Loop",
    "mttr_minutes",
    "FAILURE_LEDGER.md",
    "PLAYBOOKS.md",
]


def _parse_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip().lower()] = v.strip()
    return out


def _is_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def main() -> int:
    if not PROTOCOL.exists():
        print(f"FAIL: RUNBOOK_HARDENING_VIOLATION: missing file {PROTOCOL}")
        return 1

    content = PROTOCOL.read_text(encoding="utf-8")
    data = _parse_kv(PROTOCOL)

    missing_fields = [f for f in REQUIRED_FIELDS if not data.get(f, "")]
    if missing_fields:
        print(
            "FAIL: RUNBOOK_HARDENING_VIOLATION: missing required fields: "
            + ", ".join(missing_fields)
        )
        return 1

    if data["approved"].strip().lower() not in {"yes", "true", "approved"}:
        print("FAIL: RUNBOOK_HARDENING_VIOLATION: Approved must be yes/true/approved")
        return 1
    if not _is_iso_date(data["decision-date"]):
        print(
            "FAIL: RUNBOOK_HARDENING_VIOLATION: Decision-Date must be ISO date YYYY-MM-DD"
        )
        return 1

    missing_snippets = [s for s in REQUIRED_SNIPPETS if s not in content]
    if missing_snippets:
        print("FAIL: RUNBOOK_HARDENING_VIOLATION: missing required protocol snippets")
        for s in missing_snippets:
            print(f"  - {s}")
        return 1

    print("PASS: RUNBOOK_HARDENING_PROTOCOL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
