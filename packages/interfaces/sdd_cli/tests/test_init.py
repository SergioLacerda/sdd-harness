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
            result = runner.invoke(app, ["--force"])
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
            result = runner.invoke(app, [])
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
    """Phase 4: sdd init --full-bootstrap zero-touch flow."""

    def test_full_bootstrap_flag_triggers_compile_and_status(
        self, tmp_path: Path
    ) -> None:
        """--full-bootstrap runs governance compile then runtime status."""
        result, step_mock = _invoke_init(
            tmp_path,
            ["--type", "client", "--full-bootstrap"],
            step_side_effect=[True, True],
        )

        assert result.exit_code == 0, result.output
        calls = step_mock.call_args_list
        assert len(calls) == 2
        assert calls[0][0][1] == ["governance", "compile"]
        assert calls[1][0][1] == ["runtime", "status", "--force"]

    def test_full_bootstrap_success_prints_workspace_ready(
        self, tmp_path: Path
    ) -> None:
        result, _ = _invoke_init(
            tmp_path, ["--full-bootstrap"], step_side_effect=[True, True]
        )
        assert result.exit_code == 0
        assert "Workspace ready" in result.output

    def test_full_bootstrap_failure_exits_with_1(self, tmp_path: Path) -> None:
        # compile fails, status succeeds
        result, _ = _invoke_init(
            tmp_path, ["--full-bootstrap"], step_side_effect=[False, True]
        )
        assert result.exit_code == 1

    def test_without_full_bootstrap_prints_next_steps(self, tmp_path: Path) -> None:
        """Without --full-bootstrap, the classic next-steps block is shown."""
        result, _ = _invoke_init(tmp_path, [])
        assert result.exit_code == 0
        assert "sdd governance compile" in result.output
        assert "sdd runtime status" in result.output
