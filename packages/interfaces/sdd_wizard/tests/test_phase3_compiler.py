from __future__ import annotations

from pathlib import Path

from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler


def _make_compiler(tmp_path: Path, language: str = "Go") -> Phase3Compiler:
    compiler = Phase3Compiler(
        markdown_input_path=tmp_path / "build" / "phase-2-input",
        output_path=tmp_path / "compiled",
        repo_root=tmp_path,
        verbose=False,
        emitter=lambda _msg: None,
    )
    compiler.language = language
    return compiler


def test_validate_template_root_returns_false_with_explicit_error(
    tmp_path: Path,
) -> None:
    compiler = _make_compiler(tmp_path)
    assert compiler.validate_template_root() is False
    assert compiler.last_error is not None
    assert "Template root not found" in compiler.last_error


def test_resolve_language_template_dir_returns_go_directory(tmp_path: Path) -> None:
    template_dir = (
        tmp_path
        / "packages"
        / "interfaces"
        / "sdd_wizard"
        / "src"
        / "sdd_wizard"
        / "templates"
        / "languages"
        / "go"
    )
    template_dir.mkdir(parents=True)
    (template_dir / "go.mod").write_text("module demo\n", encoding="utf-8")
    compiler = _make_compiler(tmp_path, language="Go")
    resolved = compiler.resolve_language_template_dir()
    assert resolved == template_dir
