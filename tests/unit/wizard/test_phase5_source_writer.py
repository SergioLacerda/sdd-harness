"""Unit tests for sdd_wizard.orchestration.phase5_source_writer.SddSourceWriter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _make_writer(
    tmp_path: Path,
    mandates: list[Any] | None = None,
    guidelines: dict[str, dict[str, Any]] | None = None,
    guidelines_by_category: dict[str, list[Any]] | None = None,
    config: dict[str, Any] | None = None,
) -> Any:
    from sdd_wizard.orchestration.phase5_source_writer import SddSourceWriter

    output_base = tmp_path / "output"
    source_dir = output_base / ".sdd" / "source"
    runtime_dir = output_base / ".sdd" / "runtime"
    mandates_dir = source_dir / "mandates"
    guidelines_dir = source_dir / "guidelines"

    return SddSourceWriter(
        output_base=output_base,
        source_dir=source_dir,
        runtime_dir=runtime_dir,
        mandates_dir=mandates_dir,
        guidelines_dir=guidelines_dir,
        mandates=mandates or [],
        guidelines=guidelines or {},
        guidelines_by_category=guidelines_by_category or {},
        config=config or {"language": "Python", "adoption_level": "FULL"},
        verbose=False,
    )


SAMPLE_MANDATES = [
    {
        "id": "M001",
        "title": "Use Type Hints",
        "criticality": "OBRIGATÓRIO",
        "content": "All code must use type hints.",
    },
    {
        "id": "M002",
        "title": "Write Tests",
        "criticality": "RECOMENDADO",
        "content": "All code must have unit tests.",
    },
]

SAMPLE_GUIDELINES = {
    "G001": {
        "id": "G001",
        "title": "Use conventional commits",
        "type": "GUIDELINE",
        "category": "git",
    },
    "G002": {
        "id": "G002",
        "title": "100% test coverage",
        "type": "GUIDELINE",
        "category": "testing",
    },
}

SAMPLE_BY_CATEGORY = {
    "git": [SAMPLE_GUIDELINES["G001"]],
    "testing": [SAMPLE_GUIDELINES["G002"]],
}


class TestSddSourceWriterInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        assert writer is not None

    def test_verbose_default_false(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        assert writer.verbose is False


class TestCreateDirectories:
    def test_creates_dirs(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        result = writer.create_directories()
        assert result is True
        assert (tmp_path / "output" / ".sdd" / "runtime").exists()

    def test_creates_mandates_dir(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        assert (tmp_path / "output" / ".sdd" / "source" / "mandates").exists()

    def test_creates_guidelines_dir(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        assert (tmp_path / "output" / ".sdd" / "source" / "guidelines").exists()

    def test_creates_workflows_dir(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        assert (tmp_path / "output" / ".github" / "workflows").exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.create_directories()
        assert result is True


class TestGenerateMandatesFile:
    def test_creates_mandates_md(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, mandates=SAMPLE_MANDATES)
        writer.create_directories()
        result = writer.generate_mandates_file()
        assert result is True
        assert (
            tmp_path / "output" / ".sdd" / "source" / "mandates" / "mandates.md"
        ).exists()

    def test_mandates_file_contains_mandate_id(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, mandates=SAMPLE_MANDATES)
        writer.create_directories()
        writer.generate_mandates_file()
        content = (
            tmp_path / "output" / ".sdd" / "source" / "mandates" / "mandates.md"
        ).read_text(encoding="utf-8")
        assert "M001" in content

    def test_mandates_file_contains_title(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, mandates=SAMPLE_MANDATES)
        writer.create_directories()
        writer.generate_mandates_file()
        content = (
            tmp_path / "output" / ".sdd" / "source" / "mandates" / "mandates.md"
        ).read_text(encoding="utf-8")
        assert "Use Type Hints" in content

    def test_empty_mandates_still_creates_file(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, mandates=[])
        writer.create_directories()
        result = writer.generate_mandates_file()
        assert result is True

    def test_mandate_without_title_uses_id(self, tmp_path: Path) -> None:
        writer = _make_writer(
            tmp_path, mandates=[{"id": "M009", "content": "some content"}]
        )
        writer.create_directories()
        writer.generate_mandates_file()
        content = (
            tmp_path / "output" / ".sdd" / "source" / "mandates" / "mandates.md"
        ).read_text(encoding="utf-8")
        assert "M009" in content


class TestGenerateGuidelinesFiles:
    def test_creates_category_files(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, guidelines_by_category=SAMPLE_BY_CATEGORY)
        writer.create_directories()
        result = writer.generate_guidelines_files()
        assert result is True
        assert (
            tmp_path / "output" / ".sdd" / "source" / "guidelines" / "git.md"
        ).exists()
        assert (
            tmp_path / "output" / ".sdd" / "source" / "guidelines" / "testing.md"
        ).exists()

    def test_empty_categories_succeeds(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, guidelines_by_category={})
        writer.create_directories()
        result = writer.generate_guidelines_files()
        assert result is True

    def test_category_file_contains_guideline_id(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, guidelines_by_category=SAMPLE_BY_CATEGORY)
        writer.create_directories()
        writer.generate_guidelines_files()
        content = (
            tmp_path / "output" / ".sdd" / "source" / "guidelines" / "git.md"
        ).read_text(encoding="utf-8")
        assert "G001" in content


class TestGenerateSourceReadme:
    def test_creates_readme(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.generate_source_readme()
        assert result is True
        assert (tmp_path / "output" / ".sdd" / "source" / "README.md").exists()

    def test_readme_contains_agent_instructions(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_source_readme()
        content = (tmp_path / "output" / ".sdd" / "source" / "README.md").read_text(
            encoding="utf-8"
        )
        assert "AI Agents" in content

    def test_readme_contains_language(self, tmp_path: Path) -> None:
        writer = _make_writer(
            tmp_path, config={"language": "TypeScript", "adoption_level": "FULL"}
        )
        writer.create_directories()
        writer.generate_source_readme()
        content = (tmp_path / "output" / ".sdd" / "source" / "README.md").read_text(
            encoding="utf-8"
        )
        assert "TypeScript" in content


class TestGenerateRuntimeReadme:
    def test_creates_runtime_readme(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.generate_runtime_readme()
        assert result is True
        assert (tmp_path / "output" / ".sdd" / "runtime" / "README.md").exists()

    def test_runtime_readme_contains_pre_cache(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_runtime_readme()
        content = (tmp_path / "output" / ".sdd" / "runtime" / "README.md").read_text(
            encoding="utf-8"
        )
        assert "Pre-Cache" in content or "pre-cache" in content

    def test_verbose_logs(self, tmp_path: Path, capsys: Any) -> None:
        from sdd_wizard.orchestration.phase5_source_writer import SddSourceWriter

        output_base = tmp_path / "output"
        source_dir = output_base / ".sdd" / "source"
        runtime_dir = output_base / ".sdd" / "runtime"
        writer = SddSourceWriter(
            output_base=output_base,
            source_dir=source_dir,
            runtime_dir=runtime_dir,
            mandates_dir=source_dir / "mandates",
            guidelines_dir=source_dir / "guidelines",
            mandates=[],
            guidelines={},
            guidelines_by_category={},
            config={},
            verbose=True,
        )
        writer.create_directories()
        writer.generate_mandates_file()
        captured = capsys.readouterr()
        assert "mandates" in captured.out.lower()
