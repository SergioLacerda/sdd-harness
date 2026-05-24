#!/usr/bin/env python3
"""Validate IA-first PATH runtime docs schema."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

EXPECTED_SECTIONS = [
    "## Context Budget",
    "## Scope",
    "## Entry Checklist",
    "## MUST",
    "## MUST NOT",
    "## Escalation",
]

PATH_FILES = [
    "docs/runtime/paths/PATH_A_BUGFIX.md",
    "docs/runtime/paths/PATH_B_SIMPLE_FEATURE.md",
    "docs/runtime/paths/PATH_C_COMPLEX_FEATURE.md",
    "docs/runtime/paths/PATH_D_PARALLEL_WORK.md",
    "docs/runtime/paths/PATH_E_HOTFIX.md",
    "docs/runtime/paths/PATH_F_REFACTOR.md",
]


@dataclass(frozen=True)
class ValidationError:
    file: str
    message: str


def _extract_sections(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip().startswith("## ")]


def _count_bullets_in_section(lines: list[str], section: str) -> int:
    start = None
    for i, line in enumerate(lines):
        if line.strip() == section:
            start = i + 1
            break
    if start is None:
        return 0
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].strip().startswith("## "):
            end = i
            break
    return sum(1 for line in lines[start:end] if line.strip().startswith("- "))


def _section_body(lines: list[str], section: str) -> str:
    start = None
    for i, line in enumerate(lines):
        if line.strip() == section:
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].strip().startswith("## "):
            end = i
            break
    body = [line.strip() for line in lines[start:end] if line.strip()]
    return "\n".join(body)


def validate_path_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = lines[0].strip() if lines else ""
    if not title.startswith("# PATH "):
        errors.append(
            ValidationError(path.as_posix(), "Title must start with '# PATH '")
        )

    sections = _extract_sections(lines)
    if sections != EXPECTED_SECTIONS:
        errors.append(
            ValidationError(
                path.as_posix(),
                f"Section order mismatch. Expected {EXPECTED_SECTIONS}, found {sections}",
            )
        )
        return errors

    for section in EXPECTED_SECTIONS:
        bullets = _count_bullets_in_section(lines, section)
        if bullets > 5:
            errors.append(
                ValidationError(
                    path.as_posix(),
                    f"Section '{section}' has {bullets} bullets (max 5).",
                )
            )
    return errors


def validate_ia_first(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    text = path.read_text(encoding="utf-8")
    for section in EXPECTED_SECTIONS:
        if section not in text:
            errors.append(
                ValidationError(
                    path.as_posix(), f"Missing required schema section: {section}"
                )
            )
    if "## PATH Family Schema" not in text:
        errors.append(
            ValidationError(path.as_posix(), "Missing '## PATH Family Schema' section.")
        )
    return errors


def validate_distinctive_content(repo_root: Path) -> list[ValidationError]:
    signatures: dict[str, str] = {}
    errors: list[ValidationError] = []
    for rel in PATH_FILES:
        path = repo_root / rel
        lines = path.read_text(encoding="utf-8").splitlines()
        signature = "\n--\n".join(
            [
                _section_body(lines, "## MUST"),
                _section_body(lines, "## MUST NOT"),
                _section_body(lines, "## Escalation"),
            ]
        )
        if signature in signatures:
            other = signatures[signature]
            errors.append(
                ValidationError(
                    rel,
                    f"MUST/MUST NOT/Escalation content duplicates {other}.",
                )
            )
        else:
            signatures[signature] = rel
    return errors


def run_validation(repo_root: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    ia_first = repo_root / "docs/runtime/IA_FIRST.md"
    if not ia_first.exists():
        errors.append(ValidationError(ia_first.as_posix(), "File not found."))
    else:
        errors.extend(validate_ia_first(ia_first))

    for rel in PATH_FILES:
        path = repo_root / rel
        if not path.exists():
            errors.append(ValidationError(rel, "File not found."))
            continue
        errors.extend(validate_path_file(path))

    errors.extend(validate_distinctive_content(repo_root))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate PATH IA-first runtime docs schema."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    errors = run_validation(repo_root)
    if errors:
        for err in errors:
            print(f"ERROR: {err.file}: {err.message}")
        return 1
    print("Runtime PATH IA-first schema validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
