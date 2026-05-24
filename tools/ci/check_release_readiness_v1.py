#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path

CHECKLIST = Path("docs/guides/release/RELEASE_READINESS_V1.md")
REQUIRED_FIELDS = [
    "approved",
    "decision-owner",
    "decision-date",
    "target-version",
]
REQUIRED_SNIPPETS = [
    "## Pre-Release Criteria",
    "## Gate Points",
    "## Rollback Contract",
    "strict golden policy",
    "release.yml",
    "release-dry-run.yml",
]


def _parse_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip().lower()] = value.strip()
    return out


def _is_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def main() -> int:
    if not CHECKLIST.exists():
        print(f"FAIL: RELEASE_READINESS_V1_VIOLATION: missing file {CHECKLIST}")
        return 1

    content = CHECKLIST.read_text(encoding="utf-8")
    data = _parse_kv(CHECKLIST)

    missing = [f for f in REQUIRED_FIELDS if not data.get(f, "")]
    if missing:
        print(
            "FAIL: RELEASE_READINESS_V1_VIOLATION: missing required fields: "
            + ", ".join(missing)
        )
        return 1

    if data["approved"].strip().lower() not in {"yes", "true", "approved"}:
        print(
            "FAIL: RELEASE_READINESS_V1_VIOLATION: Approved must be yes/true/approved"
        )
        return 1
    if not _is_iso_date(data["decision-date"]):
        print(
            "FAIL: RELEASE_READINESS_V1_VIOLATION: Decision-Date must be ISO date YYYY-MM-DD"
        )
        return 1

    missing_snippets = [s for s in REQUIRED_SNIPPETS if s not in content]
    if missing_snippets:
        print(
            "FAIL: RELEASE_READINESS_V1_VIOLATION: missing required checklist snippets"
        )
        for s in missing_snippets:
            print(f"  - {s}")
        return 1

    print("PASS: RELEASE_READINESS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
