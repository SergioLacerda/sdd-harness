from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "tools" / "docs" / "check_runtime_path_schema.py"
    spec = importlib.util.spec_from_file_location(
        "check_runtime_path_schema", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_count_bullets_in_section() -> None:
    m = _load_module()
    lines = [
        "# PATH X - Example",
        "## Context Budget",
        "- a",
        "- b",
        "## Scope",
        "- c",
    ]
    assert m._count_bullets_in_section(lines, "## Context Budget") == 2
    assert m._count_bullets_in_section(lines, "## Scope") == 1


def test_validate_path_file_section_order_failure(tmp_path: Path) -> None:
    m = _load_module()
    p = tmp_path / "PATH_X.md"
    p.write_text(
        "\n".join(
            [
                "# PATH X - Example",
                "## Scope",
                "- x",
                "## Context Budget",
                "- y",
            ]
        ),
        encoding="utf-8",
    )
    errors = m.validate_path_file(p)
    assert errors
    assert any("Section order mismatch" in e.message for e in errors)


def test_validate_distinctive_content_detects_duplicate(tmp_path: Path) -> None:
    m = _load_module()
    paths_root = tmp_path / "docs/runtime/paths"
    paths_root.mkdir(parents=True)
    shared = "\n".join(
        [
            "## MUST",
            "- m1",
            "## MUST NOT",
            "- n1",
            "## Escalation",
            "- e1",
        ]
    )
    header = "\n".join(
        [
            "# PATH A - X",
            "## Context Budget",
            "- x",
            "## Scope",
            "- y",
            "## Entry Checklist",
            "- z",
        ]
    )
    for rel in m.PATH_FILES:
        file_path = tmp_path / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f"{header}\n{shared}\n", encoding="utf-8")
    errors = m.validate_distinctive_content(tmp_path)
    assert errors
    assert any("duplicates" in e.message for e in errors)
