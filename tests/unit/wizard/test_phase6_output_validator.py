"""Unit tests for sdd_wizard.orchestration.phase6_output_validator.OutputValidator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _make_validator(
    tmp_path: Path, guidelines_by_category: dict[str, list[Any]] | None = None
) -> Any:
    from sdd_wizard.orchestration.phase6_output_validator import OutputValidator

    output_base = tmp_path / "output"
    sdd_dir = output_base / ".sdd"
    source_dir = output_base / ".sdd" / "source"
    runtime_dir = output_base / ".sdd" / "runtime"
    mandates_dir = output_base / ".sdd" / "source" / "mandates"
    guidelines_dir = output_base / ".sdd" / "source" / "guidelines"

    return OutputValidator(
        output_base=output_base,
        sdd_dir=sdd_dir,
        source_dir=source_dir,
        runtime_dir=runtime_dir,
        mandates_dir=mandates_dir,
        guidelines_dir=guidelines_dir,
        guidelines_by_category=guidelines_by_category or {},
        verbose=False,
    )


def _create_all_required_files(tmp_path: Path) -> None:
    """Create all required files for a passing validation."""
    output_base = tmp_path / "output"

    # Required dirs
    (output_base / ".sdd" / "source" / "mandates").mkdir(parents=True)
    (output_base / ".sdd" / "source" / "guidelines").mkdir(parents=True)
    (output_base / ".sdd" / "runtime").mkdir(parents=True)
    (output_base / ".github" / "workflows").mkdir(parents=True)

    # Required files
    (output_base / ".sdd" / "source" / "mandates" / "mandates.md").write_text(
        "# Mandates", encoding="utf-8"
    )
    (output_base / ".sdd" / "runtime" / "README.md").write_text(
        "# Runtime", encoding="utf-8"
    )
    (output_base / ".sdd" / "source" / "README.md").write_text(
        "# Source", encoding="utf-8"
    )
    (output_base / ".sdd" / "metadata.json").write_text(
        json.dumps({}), encoding="utf-8"
    )
    (output_base / ".pre-commit-config.yaml").write_text("repos: []", encoding="utf-8")
    (output_base / ".github" / "setup-precommit-hook.sh").write_text(
        "#!/bin/sh", encoding="utf-8"
    )
    (output_base / ".github" / "copilot-instructions.md").write_text(
        "# Copilot", encoding="utf-8"
    )
    (output_base / ".vscode").mkdir(parents=True)
    (output_base / ".vscode" / "ai-rules.md").write_text("# VS Code", encoding="utf-8")
    (output_base / ".cursor" / "rules").mkdir(parents=True)
    (output_base / ".cursor" / "rules" / "spec.mdc").write_text(
        "# Cursor", encoding="utf-8"
    )
    (output_base / ".claude").mkdir(parents=True)
    (output_base / ".claude" / "claude-instructions.md").write_text(
        "# Claude", encoding="utf-8"
    )
    (output_base / ".gemini").mkdir(parents=True)
    (output_base / ".gemini" / "gemini-instructions.md").write_text(
        "# Gemini", encoding="utf-8"
    )


class TestOutputValidatorInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        assert v is not None

    def test_verbose_default_false(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        assert v.verbose is False


class TestOutputValidatorValidate:
    def test_fails_when_nothing_created(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        is_valid, result = v.validate()
        assert is_valid is False
        assert len(result["errors"]) > 0

    def test_result_has_valid_key(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        _, result = v.validate()
        assert "valid" in result

    def test_result_has_checks_dict(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        _, result = v.validate()
        assert "checks" in result
        assert isinstance(result["checks"], dict)

    def test_result_has_errors_list(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        _, result = v.validate()
        assert "errors" in result

    def test_passes_when_all_files_present(self, tmp_path: Path) -> None:
        _create_all_required_files(tmp_path)
        v = _make_validator(tmp_path)
        is_valid, result = v.validate()
        assert is_valid is True
        assert result["errors"] == []

    def test_missing_directory_listed_in_errors(self, tmp_path: Path) -> None:
        _create_all_required_files(tmp_path)
        # Remove one required dir
        import shutil

        shutil.rmtree(tmp_path / "output" / ".sdd" / "runtime")
        v = _make_validator(tmp_path)
        is_valid, result = v.validate()
        assert is_valid is False
        assert any("runtime" in e for e in result["errors"])

    def test_guideline_category_file_checked(self, tmp_path: Path) -> None:
        _create_all_required_files(tmp_path)
        # Add a guideline category that has no file
        v = _make_validator(tmp_path, guidelines_by_category={"quality": []})
        is_valid, result = v.validate()
        # quality.md doesn't exist → should fail
        assert is_valid is False
        assert any("quality" in e for e in result["errors"])

    def test_guideline_category_file_passes_when_present(self, tmp_path: Path) -> None:
        _create_all_required_files(tmp_path)
        # Create the guideline file
        guidelines_dir = tmp_path / "output" / ".sdd" / "source" / "guidelines"
        (guidelines_dir / "quality.md").write_text("# Quality", encoding="utf-8")
        v = _make_validator(tmp_path, guidelines_by_category={"quality": []})
        is_valid, result = v.validate()
        assert is_valid is True

    def test_verbose_log_called(self, tmp_path: Path, capsys: Any) -> None:
        from sdd_wizard.orchestration.phase6_output_validator import OutputValidator

        output_base = tmp_path / "output"
        v = OutputValidator(
            output_base=output_base,
            sdd_dir=output_base / ".sdd",
            source_dir=output_base / ".sdd" / "source",
            runtime_dir=output_base / ".sdd" / "runtime",
            mandates_dir=output_base / ".sdd" / "source" / "mandates",
            guidelines_dir=output_base / ".sdd" / "source" / "guidelines",
            guidelines_by_category={},
            verbose=True,
        )
        v.validate()
        captured = capsys.readouterr()
        assert "Validating" in captured.out
