"""Unit tests for sdd_wizard.orchestration.phase_7_validate_output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _create_valid_project(project_dir: Path) -> None:
    """Create a fully valid project directory structure."""
    (project_dir / ".sdd" / "CANONICAL").mkdir(parents=True)
    (project_dir / "guidelines").mkdir(parents=True)
    (project_dir / "src").mkdir(parents=True)
    (project_dir / "tests").mkdir(parents=True)
    (project_dir / "docs").mkdir(parents=True)

    (project_dir / ".sdd" / "CANONICAL" / "mandate.spec").write_text(
        'mandate M001 { title: "Test" }', encoding="utf-8"
    )
    (project_dir / ".sdd" / "CANONICAL" / "guidelines.dsl").write_text(
        'guideline G001 { title: "Test" }', encoding="utf-8"
    )
    (project_dir / ".sdd" / "CANONICAL" / "metadata.json").write_text(
        json.dumps({"generated_at": "2024-01-01T00:00:00"}), encoding="utf-8"
    )
    (project_dir / "guidelines" / "README.md").write_text(
        "# Guidelines Index\n\nSome content.", encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        "# Project README\n\nSome content.", encoding="utf-8"
    )


class TestValidateDirectoryStructure:
    def test_passes_with_all_dirs(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_directory_structure,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        valid, messages = _validate_directory_structure(project_dir)
        assert valid is True

    def test_fails_with_missing_dir(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_directory_structure,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        valid, messages = _validate_directory_structure(project_dir)
        assert valid is False
        assert any("Missing" in m for m in messages)


class TestValidateRequiredFiles:
    def test_passes_with_all_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_required_files,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        valid, messages = _validate_required_files(project_dir)
        assert valid is True

    def test_fails_with_missing_file(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_required_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        valid, messages = _validate_required_files(project_dir)
        assert valid is False


class TestValidateFileContents:
    def test_passes_with_content(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_file_contents,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        valid, messages = _validate_file_contents(project_dir)
        assert valid is True

    def test_fails_with_empty_file(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_file_contents,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        (project_dir / "README.md").write_text(
            "   ", encoding="utf-8"
        )  # whitespace only
        valid, messages = _validate_file_contents(project_dir)
        assert valid is False

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_file_contents,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        valid, messages = _validate_file_contents(project_dir)
        # No files → nothing checked → valid is True
        assert valid is True


class TestValidateMetadataIntegrity:
    def test_passes_with_valid_metadata(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_metadata_integrity,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        valid, messages = _validate_metadata_integrity(project_dir)
        assert valid is True

    def test_fails_when_no_metadata(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_metadata_integrity,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        valid, messages = _validate_metadata_integrity(project_dir)
        assert valid is False

    def test_fails_with_invalid_json(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_metadata_integrity,
        )

        project_dir = tmp_path / "project"
        (project_dir / ".sdd" / "CANONICAL").mkdir(parents=True)
        (project_dir / ".sdd" / "CANONICAL" / "metadata.json").write_text(
            "not-json{{{", encoding="utf-8"
        )
        valid, messages = _validate_metadata_integrity(project_dir)
        assert valid is False

    def test_fails_when_required_field_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_metadata_integrity,
        )

        project_dir = tmp_path / "project"
        (project_dir / ".sdd" / "CANONICAL").mkdir(parents=True)
        (project_dir / ".sdd" / "CANONICAL" / "metadata.json").write_text(
            json.dumps({"language": "Python"}),
            encoding="utf-8",  # missing generated_at
        )
        valid, messages = _validate_metadata_integrity(project_dir)
        assert valid is False


class TestValidateSpecifications:
    def test_passes_with_valid_specs(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_specifications,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        valid, messages = _validate_specifications(project_dir)
        assert valid is True

    def test_passes_when_spec_files_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_specifications,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        valid, messages = _validate_specifications(project_dir)
        # No specs to check → passes (returns True, no errors)
        assert valid is True


class TestValidateBuildFiles:
    def test_passes_with_no_build_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        valid, messages = _validate_build_files(project_dir)
        assert valid is True

    def test_detects_requirements_txt(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        _, messages = _validate_build_files(project_dir)
        assert any("requirements.txt" in m for m in messages)

    def test_detects_package_json(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "package.json").write_text(
            json.dumps({"name": "test"}), encoding="utf-8"
        )
        _, messages = _validate_build_files(project_dir)
        assert any("package.json" in m for m in messages)

    def test_detects_invalid_package_json(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _validate_build_files,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "package.json").write_text("not-json{{", encoding="utf-8")
        _, messages = _validate_build_files(project_dir)
        assert any("Invalid" in m for m in messages)


class TestCountGuidelineFiles:
    def test_returns_zero_when_no_dir(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _count_guideline_files,
        )

        count, expected = _count_guideline_files(tmp_path / "no-dir")
        assert count == 0

    def test_counts_md_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            _count_guideline_files,
        )

        guidelines_dir = tmp_path / "guidelines"
        guidelines_dir.mkdir()
        (guidelines_dir / "README.md").write_text("# x", encoding="utf-8")
        (guidelines_dir / "git.md").write_text("# y", encoding="utf-8")
        count, _ = _count_guideline_files(tmp_path)
        assert count == 2


class TestPhase7ValidateOutput:
    def test_returns_false_when_dir_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            phase_7_validate_output,
        )

        success, report = phase_7_validate_output(tmp_path / "nonexistent")
        assert success is False
        assert report["status"] == "FAILED"

    def test_returns_report_dict(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            phase_7_validate_output,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _, report = phase_7_validate_output(project_dir)
        assert "phase" in report
        assert "status" in report

    def test_fails_when_project_incomplete(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            phase_7_validate_output,
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        success, _ = phase_7_validate_output(project_dir)
        assert success is False

    def test_passes_with_valid_project(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            phase_7_validate_output,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        success, report = phase_7_validate_output(project_dir)
        assert success is True
        assert report["status"] == "SUCCESS"

    def test_report_has_checks_passed(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_7_validate_output import (
            phase_7_validate_output,
        )

        project_dir = tmp_path / "project"
        _create_valid_project(project_dir)
        _, report = phase_7_validate_output(project_dir)
        assert "checks_passed" in report
        assert report["checks_passed"] > 0
