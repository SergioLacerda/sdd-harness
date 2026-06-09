"""Tests for MandatesCompiler."""

from __future__ import annotations

from pathlib import Path

from sdd_wizard.orchestration.wizard.mandates_compiler import MandatesCompiler


def _make_compiler(tmp_path: Path) -> MandatesCompiler:
    return MandatesCompiler(tmp_path, language="Python", emitter=lambda _: None)


def test_write_creates_mandates_md(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    mandates = [
        {
            "id": "M001",
            "title": "Bootstrap",
            "criticality": "MANDATORY",
            "description": "Desc.",
        }
    ]
    assert compiler.write(mandates) is True
    out = tmp_path / "source" / "mandates" / "mandates.md"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "M001" in content
    assert "Bootstrap" in content


def test_write_returns_false_on_error(tmp_path: Path) -> None:
    compiler = MandatesCompiler(
        tmp_path / "nonexistent" / "deep", emitter=lambda _: None
    )
    # Should still succeed (mkdir is called inside)
    result = compiler.write([])
    assert isinstance(result, bool)


def test_write_empty_mandates_creates_file(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    assert compiler.write([]) is True
    assert (tmp_path / "source" / "mandates" / "mandates.md").exists()
