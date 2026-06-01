"""Tests for sdd init command — including --full-bootstrap (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sdd_cli.commands.init import _run_cli_step

# ---------------------------------------------------------------------------
# _run_cli_step helper
# ---------------------------------------------------------------------------


class TestRunCliStep:
    def test_returns_true_on_zero_exit(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _run_cli_step(
                "governance compile", ["governance", "compile"], tmp_path
            )
        assert result is True

    def test_returns_false_on_nonzero_exit(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = _run_cli_step("runtime status", ["runtime", "status"], tmp_path)
        assert result is False

    def test_invokes_sdd_cli_module(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _run_cli_step("test", ["governance", "compile"], tmp_path)
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "sdd"
        assert cmd[1:] == ["governance", "compile"]

    def test_sets_pythonutf8_env(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _run_cli_step("test", ["arg"], tmp_path)
        env = mock_run.call_args[1]["env"]
        assert env.get("PYTHONUTF8") == "1"


# ---------------------------------------------------------------------------
# init --full-bootstrap
# ---------------------------------------------------------------------------


def _invoke_init(tmp_path: Path, extra_args: list[str], step_side_effect=None):
    """Helper: invoke `sdd init` with cwd mocked to tmp_path."""
    from typer.testing import CliRunner

    from sdd_cli.commands.init import app

    runner = CliRunner()

    def _fake_cwd():
        return tmp_path

    mock_profile_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")

    patches: list = [
        patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
        patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        patch("sdd_cli.commands.init.write_profile", return_value=mock_profile_ctx),
    ]

    step_mock = None
    if step_side_effect is not None:
        step_mock = MagicMock(side_effect=step_side_effect)
        patches.append(patch("sdd_cli.commands.init._run_cli_step", step_mock))

    with (
        patch.multiple(
            "sdd_cli.commands.init",
            find_workspace_root=MagicMock(return_value=None),
            write_profile=MagicMock(return_value=mock_profile_ctx),
        ),
        patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
    ):
        if step_mock is not None:
            with patch("sdd_cli.commands.init._run_cli_step", step_mock):
                result = runner.invoke(app, extra_args)
        else:
            result = runner.invoke(app, extra_args)

    return result, step_mock


class TestInitEdgeCases:
    """Cover error branches in the init command."""

    def test_exits_1_when_parent_workspace_exists(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from sdd_cli.commands.init import app

        runner = CliRunner()
        parent_root = tmp_path / "parent"

        def _fake_cwd():
            return tmp_path / "parent" / "child"

        with (
            patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "sdd_cli.commands.init.find_workspace_root", return_value=parent_root
            ),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_exits_1_when_profile_exists_and_no_force(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from sdd_cli.commands.init import app

        runner = CliRunner()
        profile_path = tmp_path / ".sdd" / "profile"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "[sdd]\ntype = client\nname = client\nworkspace_id = ws-old\n",
            encoding="utf-8",
        )

        def _fake_cwd():
            return tmp_path

        with (
            patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "already initialized" in result.output

    def test_exits_2_when_type_invalid(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from sdd_cli.commands.init import app

        runner = CliRunner()

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")
        with (
            patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
            patch("sdd_cli.commands.init.write_profile", return_value=mock_ctx),
        ):
            result = runner.invoke(app, ["--type", "invalid"])
        assert result.exit_code == 2

    def test_prints_overwrite_soft_warning_when_force(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from sdd_cli.commands.init import app

        runner = CliRunner()
        profile_path = tmp_path / ".sdd" / "profile"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "[sdd]\ntype = client\nname = client\nworkspace_id = ws-old\n",
            encoding="utf-8",
        )

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-new")
        with (
            patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
            patch("sdd_cli.commands.init.write_profile", return_value=mock_ctx),
        ):
            result = runner.invoke(app, ["--force", "--no-bootstrap"])
        assert result.exit_code == 0
        assert "profile overwritten" in result.output

    def test_telemetry_failure_does_not_abort_init(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from sdd_cli.commands.init import app

        runner = CliRunner()

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")
        with (
            patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
            patch("sdd_cli.commands.init.write_profile", return_value=mock_ctx),
            patch(
                "sdd_runtime.telemetry.TelemetrySink",
                side_effect=Exception("telemetry down"),
            ),
        ):
            result = runner.invoke(app, ["--no-bootstrap"])
        assert result.exit_code == 0
        assert "Workspace initialized" in result.output


class TestShowExistingProfile:
    def test_prints_profile_fields(self, tmp_path: Path, capsys) -> None:
        import configparser

        from sdd_cli.commands.init import _show_existing_profile

        profile = tmp_path / ".sdd" / "profile"
        profile.parent.mkdir(parents=True, exist_ok=True)
        cfg = configparser.ConfigParser()
        cfg["sdd"] = {"type": "client", "name": "my-project", "workspace_id": "ws-1"}
        with open(profile, "w", encoding="utf-8") as f:
            cfg.write(f)

        _show_existing_profile(profile, tmp_path)
        out = capsys.readouterr().out
        assert "type" in out
        assert "client" in out


class TestInitFullBootstrap:
    """--type client runs OnboardingOrchestrator by default (opt-out via --no-bootstrap)."""

    def _invoke_with_orchestrator(
        self, tmp_path: Path, args: list[str], orchestrator_result=None
    ):
        from typer.testing import CliRunner

        from sdd_cli.commands.init import app
        from sdd_cli.services.onboarding import OnboardingResult

        runner = CliRunner()

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")

        if orchestrator_result is None:
            orchestrator_result = OnboardingResult(success=True, exit_code=0)

        with (
            patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
            patch("sdd_cli.commands.init.write_profile", return_value=mock_ctx),
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_instance = MagicMock()
            mock_instance.run.return_value = orchestrator_result
            MockOrch.return_value = mock_instance
            result = runner.invoke(app, args)
        return result, MockOrch

    def test_client_type_runs_orchestrator_by_default(self, tmp_path: Path) -> None:
        """--type client invokes OnboardingOrchestrator without any extra flag."""
        result, MockOrch = self._invoke_with_orchestrator(
            tmp_path, ["--type", "client"]
        )
        assert result.exit_code == 0, result.output
        MockOrch.return_value.run.assert_called_once_with(force=False)

    def test_bootstrap_success_prints_onboarding_complete(self, tmp_path: Path) -> None:
        result, _ = self._invoke_with_orchestrator(tmp_path, ["--type", "client"])
        assert result.exit_code == 0
        assert "Onboarding complete" in result.output

    def test_bootstrap_failure_exits_with_orchestrator_exit_code(
        self, tmp_path: Path
    ) -> None:
        from sdd_cli.services.onboarding import OnboardingResult

        result, _ = self._invoke_with_orchestrator(
            tmp_path,
            ["--type", "client"],
            orchestrator_result=OnboardingResult(
                success=False,
                failed_step="governance",
                exit_code=1,
                messages=["failed"],
            ),
        )
        assert result.exit_code == 1

    def test_no_bootstrap_prints_next_steps(self, tmp_path: Path) -> None:
        """--no-bootstrap skips orchestrator and shows manual next-steps block."""
        result, _ = _invoke_init(tmp_path, ["--no-bootstrap"])
        assert result.exit_code == 0
        assert "sdd governance generate" in result.output
        assert "sdd runtime status" in result.output


class TestBootstrapDefault:
    """--type client runs OnboardingOrchestrator by default; --no-bootstrap skips it."""

    def _invoke(self, tmp_path: Path, args: list[str], orchestrator_result=None):
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from sdd_cli.commands.init import app
        from sdd_cli.services.onboarding import OnboardingResult

        runner = CliRunner()
        mock_ctx = MagicMock()
        mock_ctx.type = "client"
        mock_ctx.name = args[args.index("--name") + 1] if "--name" in args else "test"
        mock_ctx.workspace_id = "test-id"

        if orchestrator_result is None:
            orchestrator_result = OnboardingResult(success=True, exit_code=0)

        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "sdd_core.utils.environment.find_workspace_root",
                side_effect=lambda p=None: None,
            ),
            patch(
                "sdd_core.utils.environment.write_profile",
                return_value=mock_ctx,
            ),
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_instance = MagicMock()
            mock_instance.run.return_value = orchestrator_result
            MockOrch.return_value = mock_instance
            result = runner.invoke(app, args)
        return result, MockOrch

    def test_client_type_runs_orchestrator_by_default(self, tmp_path: Path) -> None:
        result, MockOrch = self._invoke(
            tmp_path, ["--type", "client", "--name", "test", "--force"]
        )
        MockOrch.return_value.run.assert_called_once_with(force=True)
        assert result.exit_code == 0

    def test_no_bootstrap_skips_orchestrator(self, tmp_path: Path) -> None:
        result, MockOrch = self._invoke(
            tmp_path,
            ["--type", "client", "--name", "test", "--no-bootstrap", "--force"],
        )
        MockOrch.assert_not_called()
        assert result.exit_code == 0

    def test_master_type_does_not_bootstrap(self, tmp_path: Path) -> None:
        result, MockOrch = self._invoke(tmp_path, ["--type", "master", "--force"])
        MockOrch.assert_not_called()
        assert result.exit_code == 0

    def test_orchestrator_failure_exits_with_its_exit_code(
        self, tmp_path: Path
    ) -> None:
        from sdd_cli.services.onboarding import OnboardingResult

        result, _ = self._invoke(
            tmp_path,
            ["--type", "client", "--force"],
            orchestrator_result=OnboardingResult(
                success=False,
                failed_step="governance",
                exit_code=2,
                messages=["governance generate failed"],
            ),
        )
        assert result.exit_code == 2
