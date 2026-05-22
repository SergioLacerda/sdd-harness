#!/usr/bin/env python3
"""Validate cognitive governance documentation contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

ALLOWLIST_FILE = "tools/governance/cognitive_governance_allowlist.json"
REQUIRED_SECTIONS = (
    "## Objective",
    "## MUST",
    "## MUST NOT",
    "## INVALID",
    "## Escalation/Recovery",
)
CORE_CONTRACTS = (
    "docs/spec/canonical/core/cognition/CONVERGENCE_GOVERNANCE.md",
    "docs/spec/canonical/core/cognition/TEST_GOVERNANCE.md",
    "docs/spec/canonical/core/cognition/RETRIEVAL_BEFORE_REASONING.md",
    "docs/spec/canonical/core/cognition/BOUNDED_REASONING.md",
)
RUNTIME_REQUIRED = (
    "docs/runtime/protocols/AGENT_ENTRYPOINT.md",
    "docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md",
)
PATH_GLOB = "docs/runtime/paths/PATH_*.md"
LEGACY_STUBS = (
    "docs/runtime/AGENT_ENTRYPOINT.md",
    "docs/runtime/AGENT_RUNTIME_PROTOCOL.md",
)


class Violation(TypedDict):
    code: str
    file: str
    detail: str
    fix: str


def _repo_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "docs").exists():
            return candidate
    raise RuntimeError("Could not detect repository root. Use --root.")


def _load_allowlist(root: Path) -> set[tuple[str, str]]:
    path = root / ALLOWLIST_FILE
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("allowlist", [])
    if not isinstance(entries, list):
        return set()
    pairs: set[tuple[str, str]] = set()
    for item in entries:
        if isinstance(item, dict):
            code = str(item.get("code", "")).strip()
            file = str(item.get("file", "")).strip().replace("\\", "/")
            if code and file:
                pairs.add((code, file))
    return pairs


def _v(code: str, file: str, detail: str, fix: str) -> Violation:
    return {"code": code, "file": file, "detail": detail, "fix": fix}


def _check_exists(root: Path, rel_path: str) -> list[Violation]:
    if (root / rel_path).exists():
        return []
    return [
        _v(
            "missing-file",
            rel_path,
            "required cognitive artifact is missing",
            "create the required document in the canonical path",
        )
    ]


def _check_sections(root: Path, rel_path: str) -> list[Violation]:
    path = root / rel_path
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    violations: list[Violation] = []
    for section in REQUIRED_SECTIONS:
        if section not in content:
            violations.append(
                _v(
                    "missing-section",
                    rel_path,
                    f"required section not found: {section}",
                    f"add section '{section}' with normative statements",
                )
            )
    if "MUST" not in content or "MUST NOT" not in content or "INVALID" not in content:
        violations.append(
            _v(
                "weak-normative-language",
                rel_path,
                "normative keywords MUST/MUST NOT/INVALID are required",
                "replace advisory wording with normative contract language",
            )
        )
    return violations


def _check_stub_link(root: Path, rel_path: str) -> list[Violation]:
    path = root / rel_path
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    if (
        "compatibilidade" not in content.lower()
        and "compatibility" not in content.lower()
    ):
        return [
            _v(
                "invalid-stub",
                rel_path,
                "legacy runtime file must be an explicit compatibility stub",
                "replace legacy content with a stub that points to docs/runtime/protocols/",
            )
        ]
    if "runtime/protocols" not in content:
        return [
            _v(
                "stub-missing-canonical-link",
                rel_path,
                "stub does not point to canonical runtime/protocols path",
                "add canonical link to docs/runtime/protocols/...",
            )
        ]
    return []


def _check_links_exist(root: Path, rel_path: str) -> list[Violation]:
    path = root / rel_path
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    violations: list[Violation] = []
    for raw in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
        target = raw.split()[0]
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target_path = (path.parent / target.split("#", 1)[0]).resolve()
        if not target_path.exists():
            violations.append(
                _v(
                    "broken-link",
                    rel_path,
                    f"link target not found: {target}",
                    "update link to an existing canonical artifact",
                )
            )
    return violations


def _check_path_objective(root: Path, rel_path: str) -> list[Violation]:
    path = root / rel_path
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    if "## Cognitive Objective" not in content:
        return [
            _v(
                "missing-cognitive-objective",
                rel_path,
                "PATH file requires a Cognitive Objective section",
                "add '## Cognitive Objective' with scope and convergence constraints",
            )
        ]
    return []


def validate(root: Path) -> dict[str, Any]:
    allowlist = _load_allowlist(root)
    violations: list[Violation] = []

    for rel in CORE_CONTRACTS + RUNTIME_REQUIRED + LEGACY_STUBS:
        violations.extend(_check_exists(root, rel))

    for rel in CORE_CONTRACTS:
        violations.extend(_check_sections(root, rel))
        violations.extend(_check_links_exist(root, rel))

    for rel in RUNTIME_REQUIRED:
        violations.extend(_check_links_exist(root, rel))

    for rel in LEGACY_STUBS:
        violations.extend(_check_stub_link(root, rel))

    path_files = sorted(root.glob(PATH_GLOB))
    if not path_files:
        violations.append(
            _v(
                "missing-path-docs",
                PATH_GLOB,
                "no PATH files found under docs/runtime/paths",
                "create PATH_A..PATH_F docs with Cognitive Objective",
            )
        )
    for path_file in path_files:
        rel = path_file.relative_to(root).as_posix()
        violations.extend(_check_path_objective(root, rel))
        violations.extend(_check_links_exist(root, rel))

    effective = [
        v
        for v in violations
        if (v["code"], v["file"].replace("\\", "/")) not in allowlist
    ]

    return {
        "ok": len(effective) == 0,
        "violations": effective,
        "violations_count": len(effective),
        "allowlist_count": len(allowlist),
        "paths_checked": len(path_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cognitive governance docs")
    parser.add_argument("--root", type=Path, default=None, help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        root = _repo_root(args.root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    report = validate(root)
    if args.json:
        print(json.dumps(report, indent=2))
    elif report["ok"]:
        print(
            f"Cognitive governance OK: checked {report['paths_checked']} path docs with {report['allowlist_count']} allowlist exceptions."
        )
    else:
        print(
            f"ERROR: {report['violations_count']} cognitive governance violation(s):\n"
        )
        for item in report["violations"]:
            print(
                f"  - [{item['code']}] {item['file']}: {item['detail']} | fix: {item['fix']}"
            )

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
