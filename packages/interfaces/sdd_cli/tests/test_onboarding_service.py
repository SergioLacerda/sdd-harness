"""Tests for OnboardingOrchestrator service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestOnboardingOrchestrator:
    def test_run_step_uses_safe_process_runner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        seen: dict[str, object] = {}

        class _Runner:
            def run(self, cmd, cwd=None, env=None, capture_output=None):  # noqa: ANN001
                seen["cmd"] = cmd
                seen["cwd"] = cwd
                seen["env"] = env
                return type("R", (), {"success": True})()

        monkeypatch.setattr(
            "sdd_cli.services.onboarding.SafeProcessRunner", lambda: _Runner()
        )
        monkeypatch.setattr(
            "sdd_cli.services.onboarding.resolve_sdd_child_cmd", lambda: "sdd"
        )
        orc = OnboardingOrchestrator(tmp_path)
        assert orc._run_step("x", ["runtime", "status"]) is True
        assert seen["cmd"] == ["sdd", "runtime", "status"]
        assert seen["cwd"] == tmp_path
        assert seen["env"]["PYTHONUTF8"] == "1"

    def test_run_step_uses_resolved_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_run_step passes the resolved executable, not bare 'sdd'."""
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        seen: dict[str, object] = {}

        class _Runner:
            def run(self, cmd, **_kwargs):  # noqa: ANN001
                seen["cmd"] = cmd
                return type("R", (), {"success": True})()

        resolved = "/resolved/bin/sdd"
        monkeypatch.setattr(
            "sdd_cli.services.onboarding.SafeProcessRunner", lambda: _Runner()
        )
        monkeypatch.setattr(
            "sdd_cli.services.onboarding.resolve_sdd_child_cmd", lambda: resolved
        )
        orc = OnboardingOrchestrator(tmp_path)
        orc._run_step("x", ["setup", "git-hooks"])
        assert seen["cmd"] == [resolved, "setup", "git-hooks"]

    def test_step_governance_skipped_when_artifacts_exist_no_force(
        self, tmp_path: Path
    ) -> None:
        """governance generate is skipped if governance-core.json already exists."""
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=False)
        mock_run.assert_not_called()
        assert result is True

    def test_step_governance_runs_when_force(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=True)
        mock_run.assert_called_once()
        assert result is True

    def test_step_governance_runs_when_no_artifacts(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=False)
        mock_run.assert_called_once()
        assert result is True

    def test_step_skills_skips_when_seeded(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        seeds = tmp_path / ".sdd" / "skills"
        seeds.mkdir(parents=True)
        (seeds / "x").write_text("ok", encoding="utf-8")
        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            assert orc.step_skills(force=False) is True
        mock_run.assert_not_called()

    def test_step_validate_runs_runtime_status(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            assert orc.step_validate() is True
        mock_run.assert_called_once_with(
            "runtime status", ["runtime", "status", "--force"]
        )

    def test_run_stops_on_governance_failure(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=False),
            patch.object(orc, "step_skills") as mock_skills,
            patch.object(orc, "step_validate") as mock_validate,
        ):
            result = orc.run(force=False)
        mock_skills.assert_not_called()
        mock_validate.assert_not_called()
        assert result.success is False
        assert result.failed_step == "governance"

    def test_run_stops_on_skills_failure(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=False),
            patch.object(orc, "step_validate") as mock_validate,
        ):
            result = orc.run(force=False)
        mock_validate.assert_not_called()
        assert result.success is False
        assert result.failed_step == "skills"

    def test_run_returns_success_when_all_pass(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
            patch.object(orc, "step_hooks", return_value=True),
        ):
            result = orc.run(force=False)
        assert result.success is True
        assert result.failed_step is None

    def test_run_validate_failure_gives_exit_code_4(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=False),
            patch.object(orc, "step_hooks") as mock_hooks,
        ):
            result = orc.run(force=False)
        mock_hooks.assert_not_called()
        assert result.success is False
        assert result.failed_step == "validate"
        assert result.exit_code == 4

    def test_run_hooks_failure_gives_exit_code_5(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
            patch.object(orc, "step_hooks", return_value=False),
        ):
            result = orc.run(force=False)
        assert result.success is False
        assert result.failed_step == "hooks"
        assert result.exit_code == 5

    def test_step_hooks_skipped_when_not_a_git_repo(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_hooks(force=False)
        mock_run.assert_not_called()
        assert result is True

    def test_step_hooks_skipped_when_already_installed_no_force(
        self, tmp_path: Path
    ) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        target = hooks_dir / "pre-commit"
        source = tmp_path / "pre-commit-source"
        source.write_text("#!/bin/sh\n", encoding="utf-8")
        target.symlink_to(source)

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_hooks(force=False)
        mock_run.assert_not_called()
        assert result is True

    def test_step_hooks_runs_when_force(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        target = hooks_dir / "pre-commit"
        source = tmp_path / "pre-commit-source"
        source.write_text("#!/bin/sh\n", encoding="utf-8")
        target.symlink_to(source)

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_hooks(force=True)
        mock_run.assert_called_once()
        assert result is True

    def test_step_hooks_runs_when_git_repo_and_not_installed(
        self, tmp_path: Path
    ) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_hooks(force=False)
        mock_run.assert_called_once_with("setup git-hooks", ["setup", "git-hooks"])
        assert result is True

    def test_step_hooks_failure_emits_executable_in_diagnostics(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Hook failure message includes the resolved executable path."""
        import sdd_cli.services.onboarding as mod
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        monkeypatch.setattr(mod, "resolve_sdd_child_cmd", lambda: "/test/bin/sdd")
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=False):
            orc.step_hooks(force=False)

        captured = capsys.readouterr()
        assert "/test/bin/sdd" in captured.err

    def test_run_hooks_failure_message_includes_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OnboardingResult messages include the resolved executable on hook failure."""
        import sdd_cli.services.onboarding as mod
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        monkeypatch.setattr(mod, "resolve_sdd_child_cmd", lambda: "/test/bin/sdd")

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
            patch.object(orc, "step_hooks", return_value=False),
        ):
            result = orc.run(force=False)

        assert result.failed_step == "hooks"
        assert any("/test/bin/sdd" in m for m in result.messages)
