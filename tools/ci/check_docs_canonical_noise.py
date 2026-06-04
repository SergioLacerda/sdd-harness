#!/usr/bin/env python3
"""Fail CI when canonical docs contain placeholder noise or unresolved draft markers."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_ROOTS = (
    Path("docs/spec/canonical"),
    Path("docs/adr"),
)

FORBIDDEN_MARKERS = ("TODO", "TBD", "FIXME", "WIP", "placeholder")
CODE_FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    marker: str
    text: str


def _iter_markdown_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root in FORBIDDEN_ROOTS:
        abs_root = repo_root / root
        if abs_root.exists():
            files.extend(abs_root.rglob("*.md"))
    return sorted(set(files))


def _scan_file(path: Path, repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    in_code_block = False
    for line_no, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if CODE_FENCE_RE.match(raw_line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        lowered = raw_line.lower()
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in lowered:
                violations.append(
                    Violation(
                        path=path.relative_to(repo_root),
                        line=line_no,
                        marker=marker,
                        text=raw_line.strip(),
                    )
                )
                break
    return violations


def collect_violations(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for file_path in _iter_markdown_files(repo_root):
        violations.extend(_scan_file(file_path, repo_root))
    return violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Block canonical docs noise in docs/spec/canonical and docs/adr."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.root).resolve()
    violations = collect_violations(repo_root)

    if violations:
        print("FAIL: DOCS_CANONICAL_NOISE")
        for violation in violations:
            print(
                f"  - {violation.path}:{violation.line} "
                f"contains `{violation.marker}` -> {violation.text}"
            )
        return 1

    print("PASS: DOCS_CANONICAL_NOISE_CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
