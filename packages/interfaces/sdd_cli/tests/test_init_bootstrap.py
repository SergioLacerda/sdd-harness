"""Tests for sdd init command — --full-bootstrap orchestration (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


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
        patches.append(patch("sdd_cli.commands.init_steps._run_cli_step", step_mock))

    with (
        patch.multiple(
            "sdd_cli.commands.init",
            find_workspace_root=MagicMock(return_value=None),
            write_profile=MagicMock(return_value=mock_profile_ctx),
        ),
        patch("sdd_cli.commands.init.Path.cwd", _fake_cwd),
    ):
        if step_mock is not None:
            with patch("sdd_cli.commands.init_steps._run_cli_step", step_mock):
                result = runner.invoke(app, extra_args)
        else:
            result = runner.invoke(app, extra_args)

    return result, step_mock


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
                "sdd_cli.commands.init.find_workspace_root",
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


class TestInitDefaultFlag:
    """--default fills in type=client, name=local-dev, force=True when unset."""

    def _invoke(self, tmp_path: Path, args: list[str], orchestrator_result=None):
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from sdd_cli.commands.init import app
        from sdd_cli.services.onboarding import OnboardingResult

        runner = CliRunner()
        mock_ctx = MagicMock()
        mock_ctx.type = "client"
        mock_ctx.name = "local-dev"
        mock_ctx.workspace_id = "test-id"

        if orchestrator_result is None:
            orchestrator_result = OnboardingResult(success=True, exit_code=0)

        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
            patch(
                "sdd_cli.commands.init.write_profile",
                return_value=mock_ctx,
            ) as mock_write_profile,
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_instance = MagicMock()
            mock_instance.run.return_value = orchestrator_result
            MockOrch.return_value = mock_instance
            result = runner.invoke(app, args)
        return result, MockOrch, mock_write_profile

    def test_default_alone_resolves_client_local_dev_force(
        self, tmp_path: Path
    ) -> None:
        result, MockOrch, mock_write_profile = self._invoke(tmp_path, ["--default"])
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(tmp_path, "client", "local-dev")
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_default_does_not_override_explicit_type(self, tmp_path: Path) -> None:
        """--default still fills in --name (unset) even when --type is explicit."""
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--default", "--type", "master"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(tmp_path, "master", "local-dev")
        MockOrch.assert_not_called()

    def test_default_does_not_override_explicit_name(self, tmp_path: Path) -> None:
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--default", "--name", "custom-name"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(tmp_path, "client", "custom-name")
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_default_does_not_override_explicit_force_false(
        self, tmp_path: Path
    ) -> None:
        """--default sets force=True only when --force isn't explicitly passed.

        Typer/click has no way to pass an explicit "false" override for a
        store_true flag, so this documents that --default always wins for
        force unless a future --no-force flag is introduced.
        """
        result, MockOrch, _ = self._invoke(tmp_path, ["--default"])
        assert result.exit_code == 0, result.output
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_without_default_behavior_unchanged(self, tmp_path: Path) -> None:
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--type", "client", "--name", "test", "--force"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(tmp_path, "client", "test")
        MockOrch.return_value.run.assert_called_once_with(force=True)
