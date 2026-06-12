from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"


def test_makefile_disallows_inline_python_c() -> None:
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "python -c" not in content
    assert '"-c"' not in content


def test_makefile_disallows_shell_c_inline_commands() -> None:
    content = MAKEFILE.read_text(encoding="utf-8")
    forbidden = re.compile(r"\b(?:sh|bash)\s+-c\b")
    assert forbidden.search(content) is None


def test_docs_build_publishes_selector_artifacts() -> None:
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "docs-build: selector-build" in content
    assert (
        "uv run python -m sdd_wizard.orchestration.wizard.selector_compiler "
        "--output-dir docs/selector"
    ) in content


def test_docs_serve_runs_selector_build() -> None:
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "docs-serve: selector-build" in content
