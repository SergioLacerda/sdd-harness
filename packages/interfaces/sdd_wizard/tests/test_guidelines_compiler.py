"""Tests for GuidelinesCompiler."""

from __future__ import annotations

from pathlib import Path

from sdd_wizard.orchestration.wizard.guidelines_compiler import GuidelinesCompiler


def _make_compiler(tmp_path: Path) -> GuidelinesCompiler:
    return GuidelinesCompiler(tmp_path, emitter=lambda _: None)


def test_write_creates_category_file(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [
        {
            "id": "G001",
            "title": "Code Style",
            "category": "testing",
            "description": "Desc.",
        }
    ]
    assert compiler.write(guidelines) is True
    out = tmp_path / "source" / "guidelines" / "testing.md"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "G001" in content
    assert "Code Style" in content


def test_write_groups_by_category(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [
        {"id": "G001", "title": "A", "category": "alpha", "description": ""},
        {"id": "G002", "title": "B", "category": "beta", "description": ""},
    ]
    assert compiler.write(guidelines) is True
    assert (tmp_path / "source" / "guidelines" / "alpha.md").exists()
    assert (tmp_path / "source" / "guidelines" / "beta.md").exists()


def test_write_uses_general_category_when_missing(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [{"id": "G001", "title": "X", "description": ""}]
    assert compiler.write(guidelines) is True
    assert (tmp_path / "source" / "guidelines" / "general.md").exists()


def test_write_empty_guidelines_returns_true(tmp_path: Path) -> None:
    assert _make_compiler(tmp_path).write([]) is True
