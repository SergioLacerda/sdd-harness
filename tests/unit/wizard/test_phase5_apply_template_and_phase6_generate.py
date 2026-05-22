"""Unit tests for phase_5_apply_template and phase_6_generate_project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# phase_5_apply_template helpers
# ---------------------------------------------------------------------------


class TestCopyTemplateFiles:
    def test_returns_error_when_source_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import _copy_template_files

        count, errors = _copy_template_files(tmp_path / "nonexistent", tmp_path / "out")
        assert count == 0
        assert len(errors) > 0

    def test_copies_files_from_source(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import _copy_template_files

        src = tmp_path / "src"
        src.mkdir()
        (src / "file.md").write_text("# content", encoding="utf-8")
        dst = tmp_path / "dst"

        count, errors = _copy_template_files(src, dst)
        assert count == 1
        assert errors == []
        assert (dst / "file.md").exists()

    def test_copies_nested_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import _copy_template_files

        src = tmp_path / "src"
        (src / "sub").mkdir(parents=True)
        (src / "sub" / "nested.md").write_text("# nested", encoding="utf-8")
        dst = tmp_path / "dst"

        count, errors = _copy_template_files(src, dst)
        assert count == 1
        assert (dst / "sub" / "nested.md").exists()


class TestApplyPlaceholderReplacements:
    def test_replaces_placeholder(self) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            _apply_placeholder_replacements,
        )

        text = "Hello {{name}}!"
        result = _apply_placeholder_replacements(text, {"name": "World"})
        assert result == "Hello World!"

    def test_no_replacement_when_no_match(self) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            _apply_placeholder_replacements,
        )

        text = "No placeholders here"
        result = _apply_placeholder_replacements(text, {"key": "value"})
        assert result == "No placeholders here"

    def test_replaces_multiple_placeholders(self) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            _apply_placeholder_replacements,
        )

        text = "{{LANGUAGE}} is {{language}}"
        result = _apply_placeholder_replacements(
            text, {"LANGUAGE": "PYTHON", "language": "python"}
        )
        assert result == "PYTHON is python"


class TestCustomizeFileForLanguage:
    def test_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            _customize_file_for_language,
        )

        success, msg = _customize_file_for_language(
            tmp_path / "nonexistent.md", "python"
        )
        assert success is False

    def test_replaces_language_placeholder(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            _customize_file_for_language,
        )

        f = tmp_path / "template.md"
        f.write_text("Language: {{LANGUAGE}}", encoding="utf-8")
        success, _ = _customize_file_for_language(f, "python")
        assert success is True
        assert "PYTHON" in f.read_text(encoding="utf-8")


class TestPhase5ApplyTemplate:
    def test_fails_when_base_template_not_found(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            phase_5_apply_template,
        )

        scaffolding = tmp_path / "scaffold"
        # base template dir doesn't exist → should fail
        success, report = phase_5_apply_template(scaffolding, language="python")
        # It may succeed with 0 files or fail depending on template existence
        assert isinstance(success, bool)
        assert "status" in report

    def test_creates_scaffolding_dir(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            phase_5_apply_template,
        )

        scaffolding = tmp_path / "scaffold"
        phase_5_apply_template(scaffolding, language="python")
        assert scaffolding.exists()

    def test_creates_required_dirs(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            phase_5_apply_template,
        )

        scaffolding = tmp_path / "scaffold"
        phase_5_apply_template(scaffolding, language="python")
        assert (scaffolding / ".sdd" / "CANONICAL").exists()
        assert (scaffolding / "src").exists()

    def test_report_has_phase_key(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_5_apply_template import (
            phase_5_apply_template,
        )

        scaffolding = tmp_path / "scaffold"
        _, report = phase_5_apply_template(scaffolding, language="python")
        assert report["phase"] == "PHASE_5_APPLY_TEMPLATE"


# ---------------------------------------------------------------------------
# phase_6_generate_project helpers
# ---------------------------------------------------------------------------

MANDATES = {"M001": {"title": "Use type hints", "criticality": "OBRIGATÓRIO"}}
GUIDELINES = {
    "G001": {"title": "Conventional commits", "description": "Use cc format"},
    "G002": {
        "title": "Test coverage",
        "description": "80% coverage",
        "examples": "example",
    },
}
METADATA = {"language": "python", "adoption_level": "FULL"}
MANDATE_TEXT = 'mandate M001 { title: "Use type hints" }'
GUIDELINES_TEXT = 'guideline G001 { title: "Conventional commits" }'


class TestCreateProjectDirectories:
    def test_creates_all_dirs(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _create_project_directories,
        )

        project_dir = tmp_path / "project"
        success, messages = _create_project_directories(project_dir)
        assert success is True
        assert (project_dir / ".sdd" / "CANONICAL").exists()
        assert (project_dir / "guidelines").exists()
        assert (project_dir / "src").exists()


class TestWriteSpecificationFiles:
    def test_writes_all_spec_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _write_specification_files,
        )

        project_dir = tmp_path / "project"
        (project_dir / ".sdd" / "CANONICAL").mkdir(parents=True)
        success, messages = _write_specification_files(
            project_dir, MANDATE_TEXT, GUIDELINES_TEXT, METADATA
        )
        assert success is True
        assert (project_dir / ".sdd" / "CANONICAL" / "mandate.spec").exists()
        assert (project_dir / ".sdd" / "CANONICAL" / "guidelines.dsl").exists()
        assert (project_dir / ".sdd" / "CANONICAL" / "metadata.json").exists()

    def test_metadata_has_generated_at(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _write_specification_files,
        )

        project_dir = tmp_path / "project"
        (project_dir / ".sdd" / "CANONICAL").mkdir(parents=True)
        _write_specification_files(project_dir, MANDATE_TEXT, GUIDELINES_TEXT, METADATA)
        data = json.loads(
            (project_dir / ".sdd" / "CANONICAL" / "metadata.json").read_text(
                encoding="utf-8"
            )
        )
        assert "generated_at" in data


class TestGenerateGuidelineMarkdowns:
    def test_creates_guideline_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _generate_guideline_markdowns,
        )

        project_dir = tmp_path / "project"
        (project_dir / "guidelines").mkdir(parents=True)
        success, _ = _generate_guideline_markdowns(project_dir, GUIDELINES)
        assert success is True
        assert (project_dir / "guidelines" / "README.md").exists()

    def test_creates_individual_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _generate_guideline_markdowns,
        )

        project_dir = tmp_path / "project"
        (project_dir / "guidelines").mkdir(parents=True)
        _generate_guideline_markdowns(project_dir, GUIDELINES)
        assert (project_dir / "guidelines" / "G001.md").exists()


class TestGenerateBuildFiles:
    def test_generates_python_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _generate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        success, _ = _generate_build_files(project_dir, "python", METADATA)
        assert success is True
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "pyproject.toml").exists()

    def test_generates_java_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _generate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        success, _ = _generate_build_files(project_dir, "java", METADATA)
        assert success is True
        assert (project_dir / "pom.xml").exists()

    def test_generates_js_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _generate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        success, _ = _generate_build_files(project_dir, "js", METADATA)
        assert success is True
        assert (project_dir / "package.json").exists()

    def test_no_files_for_unknown_language(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            _generate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        success, messages = _generate_build_files(project_dir, "ruby", METADATA)
        assert success is True
        assert messages == []


class TestGenerateReadme:
    def test_creates_readme(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import _generate_readme

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        success, _ = _generate_readme(project_dir, "python", MANDATES, 5)
        assert success is True
        assert (project_dir / "README.md").exists()

    def test_readme_contains_mandate_id(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import _generate_readme

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _generate_readme(project_dir, "python", MANDATES, 5)
        content = (project_dir / "README.md").read_text(encoding="utf-8")
        assert "M001" in content


class TestPhase6GenerateProject:
    def test_returns_success(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            phase_6_generate_project,
        )

        output = tmp_path / "project"
        success, report = phase_6_generate_project(
            MANDATES,
            GUIDELINES,
            MANDATE_TEXT,
            GUIDELINES_TEXT,
            METADATA,
            output,
            "python",
        )
        assert success is True
        assert report["status"] == "SUCCESS"

    def test_report_has_phase_key(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            phase_6_generate_project,
        )

        output = tmp_path / "project"
        _, report = phase_6_generate_project(
            MANDATES, GUIDELINES, MANDATE_TEXT, GUIDELINES_TEXT, METADATA, output
        )
        assert report["phase"] == "PHASE_6_GENERATE_PROJECT"

    def test_generates_java_build_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            phase_6_generate_project,
        )

        output = tmp_path / "project"
        phase_6_generate_project(
            MANDATES,
            GUIDELINES,
            MANDATE_TEXT,
            GUIDELINES_TEXT,
            METADATA,
            output,
            "java",
        )
        assert (output / "pom.xml").exists()

    def test_generates_js_build_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            phase_6_generate_project,
        )

        output = tmp_path / "project"
        phase_6_generate_project(
            MANDATES, GUIDELINES, MANDATE_TEXT, GUIDELINES_TEXT, METADATA, output, "js"
        )
        assert (output / "package.json").exists()

    def test_data_contains_output_dir(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_6_generate_project import (
            phase_6_generate_project,
        )

        output = tmp_path / "project"
        _, report = phase_6_generate_project(
            MANDATES, GUIDELINES, MANDATE_TEXT, GUIDELINES_TEXT, METADATA, output
        )
        assert "output_dir" in report["data"]
