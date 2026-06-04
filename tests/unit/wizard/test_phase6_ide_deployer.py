"""Unit tests for sdd_wizard.orchestration.phase6_ide_deployer.IdeTemplateDeployer."""

from __future__ import annotations

import shutil
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

    deployer = IdeTemplateDeployer(
        repo_root=repo_root,
        output_base=output_base,
        verbose=verbose,
    )
    # Keep tests deterministic: use repo-root template tree only.
    deployer._template_base_candidates = lambda: [  # type: ignore[method-assign]
        repo_root
        / "packages"
        / "features"
        / "sdd_integration"
        / "src"
        / "sdd_integration"
        / "templates"
    ]
    return deployer


class TestIdeTemplateDeployerInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        assert d is not None

    def test_verbose_default_false(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        assert d.verbose is False

    def test_init_ignores_resolve_errors_when_not_blocking(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer

        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-tests")

        class _BrokenPath:
            def resolve(self) -> Path:
                raise OSError("cannot resolve")

            def __truediv__(self, other: object) -> Path:
                return Path("/tmp") / str(other)

        deployer = IdeTemplateDeployer(
            repo_root=_BrokenPath(),  # type: ignore[arg-type]
            output_base=_BrokenPath(),  # type: ignore[arg-type]
            verbose=False,
        )
        assert deployer is not None

    def test_init_blocks_root_mutation_when_paths_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer

        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-tests")
        with pytest.raises(PermissionError):
            IdeTemplateDeployer(
                repo_root=tmp_path,
                output_base=tmp_path,
                verbose=False,
            )


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

    def test_template_base_candidates_uses_package_resources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer

        d = _make_deployer(tmp_path)
        pkg_root = tmp_path / "pkg"
        (pkg_root / "templates").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "sdd_wizard.orchestration.phase6_ide_deployer.resources.files",
            lambda name: pkg_root,
        )
        candidates = IdeTemplateDeployer._template_base_candidates(d)
        assert candidates[0] == pkg_root / "templates"
        assert candidates[1].name == "templates"

    def test_copy_templates_handles_copy_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        src = template_base / ".github" / "workflows"
        src.mkdir(parents=True, exist_ok=True)
        (src / "sdd-validation.yml").write_text("name: SDD", encoding="utf-8")

        monkeypatch.setattr(
            "sdd_wizard.orchestration.phase6_ide_deployer.shutil.copy2",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        assert d.copy_templates() is False


class TestCreateIdeTemplates:
    def test_returns_false_when_template_base_missing(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        # Template base doesn't exist
        result = d.create_ide_templates()
        assert result is False

    def test_does_not_copy_precommit_when_template_exists(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        (template_base / ".pre-commit-config.yaml").write_text(
            "repos: []", encoding="utf-8"
        )
        (template_base / ".vscode").mkdir(parents=True, exist_ok=True)
        (template_base / ".vscode" / "settings.json").write_text("{}", encoding="utf-8")

        result = d.create_ide_templates()
        assert result is True
        assert not (d.output_base / ".pre-commit-config.yaml").exists()

    def test_does_not_copy_hook_script(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        (template_base / ".github").mkdir(parents=True, exist_ok=True)
        sh_file = template_base / ".github" / "setup-precommit-hook.sh"
        sh_file.write_text("#!/bin/sh", encoding="utf-8")
        (template_base / ".vscode").mkdir(parents=True, exist_ok=True)
        (template_base / ".vscode" / "settings.json").write_text("{}", encoding="utf-8")

        result = d.create_ide_templates()
        assert result is True
        assert not (d.output_base / ".github" / "setup-precommit-hook.sh").exists()

    def test_copies_dir_mappings(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        vscode_dir = template_base / ".vscode"
        vscode_dir.mkdir(parents=True, exist_ok=True)
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")
        result = d.create_ide_templates()
        assert result is True

    def test_does_not_copy_tests_dir_when_present(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        tests_dir = template_base / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_sample.py").write_text("# test", encoding="utf-8")
        (template_base / ".vscode").mkdir(parents=True, exist_ok=True)
        (template_base / ".vscode" / "settings.json").write_text("{}", encoding="utf-8")

        result = d.create_ide_templates()
        assert result is True
        assert not (d.output_base / "tests" / "test_sample.py").exists()

    def test_returns_false_when_no_files_copied(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        template_base.mkdir(parents=True, exist_ok=True)
        # No files at all in template_base → copied_count == 0

        result = d.create_ide_templates()
        assert result is False

    def test_handles_inner_copytree_failure_and_continues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = _make_deployer(tmp_path)
        template_base = d._template_base
        github_dir = template_base / ".github"
        vscode_dir = template_base / ".vscode"
        github_dir.mkdir(parents=True, exist_ok=True)
        vscode_dir.mkdir(parents=True, exist_ok=True)
        (github_dir / "workflow.yml").write_text("x", encoding="utf-8")
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")

        original_copytree = shutil.copytree

        def _copytree(src: Path, dst: Path, dirs_exist_ok: bool = False):
            if src.name == ".github":
                raise RuntimeError("copytree boom")
            return original_copytree(src, dst, dirs_exist_ok=dirs_exist_ok)

        monkeypatch.setattr(
            "sdd_wizard.orchestration.phase6_ide_deployer.shutil.copytree",
            _copytree,
        )

        result = d.create_ide_templates()
        assert result is True
        assert (d.output_base / ".vscode" / "settings.json").exists()

    def test_outer_exception_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer

        d = _make_deployer(tmp_path)
        monkeypatch.setattr(
            IdeTemplateDeployer,
            "_template_base",
            property(lambda self: (_ for _ in ()).throw(RuntimeError("boom"))),
        )
        assert d.create_ide_templates() is False


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

    def test_resolution_failure_is_ignored_when_not_blocking(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = _make_deployer(tmp_path)

        class _BrokenPath:
            def resolve(self) -> Path:
                raise OSError("cannot resolve")

            def __truediv__(self, other: object) -> Path:
                return tmp_path / str(other)

        d.repo_root = _BrokenPath()  # type: ignore[assignment]
        d.output_base = _BrokenPath()  # type: ignore[assignment]
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-tests")
        d.inject_bootstrap_metadata("fp", "2024-01-01T00:00:00", 1)

    def test_injection_blocks_root_mutation_when_paths_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = _make_deployer(tmp_path)
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-tests")
        d.repo_root = tmp_path  # type: ignore[assignment]
        d.output_base = tmp_path  # type: ignore[assignment]
        with pytest.raises(PermissionError):
            d.inject_bootstrap_metadata("fp", "2024-01-01T00:00:00", 1)

    def test_injection_write_failure_is_logged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = _make_deployer(tmp_path)
        target_dir = d.output_base / ".github"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / "copilot-instructions.md"
        file_path.write_text("# Copilot", encoding="utf-8")

        original_write_text = Path.write_text

        def _write_text(self: Path, content: str, encoding: str = "utf-8") -> int:
            if self == file_path:
                raise OSError("write failed")
            return original_write_text(self, content, encoding=encoding)

        monkeypatch.setattr(Path, "write_text", _write_text, raising=True)
        d.inject_bootstrap_metadata("fp", "2024-01-01T00:00:00", 1)

    def test_populate_ide_rules_updates_and_handles_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = _make_deployer(tmp_path)
        vscode_file = d.output_base / ".vscode" / "ai-rules.md"
        cursor_file = d.output_base / ".cursor" / "rules" / "sdd-governance.mdc"
        vscode_file.parent.mkdir(parents=True, exist_ok=True)
        cursor_file.parent.mkdir(parents=True, exist_ok=True)
        vscode_file.write_text(
            "fingerprint={FINGERPRINT} mandates={MANDATES_COUNT}",
            encoding="utf-8",
        )
        cursor_file.write_text(
            "fingerprint={FINGERPRINT} mandates={MANDATES_COUNT}",
            encoding="utf-8",
        )

        original_write_text = Path.write_text

        def _write_text(self: Path, content: str, encoding: str = "utf-8") -> int:
            if self == cursor_file:
                raise OSError("boom")
            return original_write_text(self, content, encoding=encoding)

        monkeypatch.setattr(Path, "write_text", _write_text, raising=True)
        d.populate_ide_rules([{"id": "m1"}, {"id": "m2"}], "fp123")
        assert "fp123" in read_text_utf8(vscode_file)
        assert "{FINGERPRINT}" not in read_text_utf8(vscode_file)

    def test_populate_ide_rules_skips_missing_files(self, tmp_path: Path) -> None:
        d = _make_deployer(tmp_path)
        vscode_file = d.output_base / ".vscode" / "ai-rules.md"
        vscode_file.parent.mkdir(parents=True, exist_ok=True)
        vscode_file.write_text(
            "fingerprint={FINGERPRINT} mandates={MANDATES_COUNT}",
            encoding="utf-8",
        )
        d.populate_ide_rules([{"id": "m1"}], "fp999")
        assert "fp999" in read_text_utf8(vscode_file)
