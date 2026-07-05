#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    path: str
    pattern: str
    description: str


RULES = [
    Rule(
        path="tools/maintenance/make_tasks.py",
        pattern='"tools/ci/check_golden_policy.py", "--mode", "warn"',
        description="Local `make check` must run WARN mode",
    ),
    Rule(
        path=".github/workflows/reusable-test.yml",
        pattern="tools/ci/check_golden_policy.py --mode block",
        description="Test CI artifact gate must run BLOCK mode",
    ),
    Rule(
        path=".github/workflows/release-dry-run.yml",
        pattern="tools/ci/check_golden_policy.py --mode strict",
        description="Release dry-run must run STRICT mode",
    ),
    Rule(
        path=".github/workflows/release.yml",
        pattern="tools/ci/check_golden_policy.py --mode strict",
        description="Release workflow must run STRICT mode",
    ),
    Rule(
        path="docs/adr/ADR-009-progressive-enforcement-ladder.md",
        pattern="| strict |",
        description="Policy matrix must document STRICT lane",
    ),
]


def _contains(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    return pattern in path.read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    for rule in RULES:
        p = Path(rule.path)
        if not _contains(p, rule.pattern):
            failures.append(
                f"{rule.path}: missing pattern `{rule.pattern}` ({rule.description})"
            )

    if failures:
        print("FAIL: ENFORCEMENT_LADDER_DRIFT")
        for line in failures:
            print(f"  - {line}")
        return 1

    print("PASS: ENFORCEMENT_LADDER_IN_SYNC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
