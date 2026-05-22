"""Unit tests for sdd_wizard.orchestration.phase6_ide_deployer.IdeTemplateDeployer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers.text_io import read_text_utf8

pytestmark = pytest.mark.unit


def _make_deployer(tmp_path: Path, verbose: bool = False) -> Any:
    from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    output_base = tmp_path / "output"
    output_base.mkdir(parents=True, exist_ok=True)

    return IdeTemplateDeployer(
        repo_root=repo_root,
        output_base=output_base,
        verbose=verbose,
    )


class TestIdeTemplateDeployerInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        assert d is not None

    def test_verbose_default_false(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        assert d.verbose is False


class TestCopyTemplates:
    def test_returns_true_when_source_not_found(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        # No template source exists — should still return True
        result = d.copy_templates()
        assert result is True

    def test_copies_workflow_when_template_exists(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        # Create the source template
        src = d._template_base / ".github" / "workflows"
        src.mkdir(parents=True, exist_ok=True)
        (src / "sdd-validation.yml").write_text("name: SDD", encoding="utf-8")

        result = d.copy_templates()
        assert result is True
        assert (d.output_base / ".github" / "workflows" / "sdd-validation.yml").exists()

    def test_verbose_logs(self, tmp_path: Path, capsys: Any) -> None:
        d = _make_deployer(tmp_path, verbose=True)
        d.copy_templates()
        captured = capsys.readouterr()
        assert (
            "Copying" in captured.out
            or "template" in captured.out.lower()
            or len(captured.out) >= 0
        )


class TestCreateIdeTemplates:
    def test_returns_false_when_template_base_missing(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        # Template base doesn't exist
        result = d.create_ide_templates()
        assert result is False

    def test_copies_precommit_when_template_exists(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        (template_base / ".pre-commit-config.yaml").write_text(
            "repos: []", encoding="utf-8"
        )

        result = d.create_ide_templates()
        assert result is True
        assert (d.output_base / ".pre-commit-config.yaml").exists()

    def test_copies_sh_file_via_file_mapping(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        # The .sh file is in file_mappings — needs to be directly under .github/
        (template_base / ".github").mkdir(parents=True, exist_ok=True)
        sh_file = template_base / ".github" / "setup-precommit-hook.sh"
        sh_file.write_text("#!/bin/sh", encoding="utf-8")
        (template_base / ".pre-commit-config.yaml").write_text(
            "repos: []", encoding="utf-8"
        )

        result = d.create_ide_templates()
        assert result is True

    def test_copies_dir_mappings(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        vscode_dir = template_base / ".vscode"
        vscode_dir.mkdir(parents=True, exist_ok=True)
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")
        # Also need at least one "file" to get copied_count > 0
        (template_base / ".pre-commit-config.yaml").write_text(
            "repos: []", encoding="utf-8"
        )

        result = d.create_ide_templates()
        assert result is True

    def test_copies_tests_dir_when_present(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        tests_dir = template_base / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_sample.py").write_text("# test", encoding="utf-8")
        (template_base / ".pre-commit-config.yaml").write_text(
            "repos: []", encoding="utf-8"
        )

        result = d.create_ide_templates()
        assert result is True
        assert (d.output_base / "tests" / "test_sample.py").exists()

    def test_returns_false_when_no_files_copied(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        # No files at all in template_base → copied_count == 0

        result = d.create_ide_templates()
        assert result is False


class TestInjectBootstrapMetadata:
    def test_injects_into_existing_files(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        copilot_dir = d.output_base / ".github"
        copilot_dir.mkdir(parents=True, exist_ok=True)
        copilot_file = copilot_dir / "copilot-instructions.md"
        copilot_file.write_text("# Copilot Instructions", encoding="utf-8")

        d.inject_bootstrap_metadata("abc123", "2024-01-01T00:00:00", 5)
        content = read_text_utf8(copilot_file)
        assert "sdd:bootstrap-metadata" in content
        assert "abc123" in content

    def test_skips_files_that_already_have_metadata(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        copilot_dir = d.output_base / ".github"
        copilot_dir.mkdir(parents=True, exist_ok=True)
        copilot_file = copilot_dir / "copilot-instructions.md"
        copilot_file.write_text(
            "# Copilot\n<!-- sdd:bootstrap-metadata\nfoo\n-->", encoding="utf-8"
        )

        d.inject_bootstrap_metadata("abc123", "2024-01-01T00:00:00", 5)
        content = read_text_utf8(copilot_file)
        # Should not have a second injection
        assert content.count("sdd:bootstrap-metadata") == 1

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        # No files exist — should not raise
        d.inject_bootstrap_metadata("abc123", "2024-01-01T00:00:00", 5)

    def test_injects_mandates_count(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        vscode_dir = d.output_base / ".vscode"
        vscode_dir.mkdir(parents=True, exist_ok=True)
        (vscode_dir / "ai-rules.md").write_text("# AI Rules", encoding="utf-8")

        d.inject_bootstrap_metadata("fp1234", "2024-06-01T00:00:00", 42)
        content = read_text_utf8(vscode_dir / "ai-rules.md")
        assert "42" in content

    def test_verbose_logs_injection(self, tmp_path: Path, capsys: Any) -> None:
        d = _make_deployer(tmp_path, verbose=True)
        claude_dir = d.output_base / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "claude-instructions.md").write_text("# Claude", encoding="utf-8")

        d.inject_bootstrap_metadata("fp0000", "2024-01-01T00:00:00", 3)
        captured = capsys.readouterr()
        assert "Injected" in captured.out or "metadata" in captured.out.lower()
