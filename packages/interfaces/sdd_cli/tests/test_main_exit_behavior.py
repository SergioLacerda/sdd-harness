from __future__ import annotations

import errno
import runpy
import sys
from unittest.mock import MagicMock

import pytest

from sdd_cli import main as cli_main
from sdd_cli.main import (
    _json_option_callback,
    _profile_option_callback,
    _verbose_option_callback,
)


def test_main_returns_click_exit_code(monkeypatch) -> None:
    import click

    def _raise_exit(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise click.exceptions.Exit(3)

    monkeypatch.setattr(cli_main, "app", _raise_exit)
    assert cli_main.main() == 3


def test_main_renders_click_usage_errors_without_traceback(
    monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import click

    def _raise_usage_error(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise click.UsageError("bad usage")

    monkeypatch.setattr(cli_main, "app", _raise_usage_error)

    assert cli_main.main() == 2

    captured = capsys.readouterr()
    assert "Error: bad usage" in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_permission_errors_without_traceback(
    monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _raise_permission(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise PermissionError("denied")

    monkeypatch.setattr(cli_main, "app", _raise_permission)

    assert cli_main.main() == 1

    captured = capsys.readouterr()
    assert "ERROR: Permission denied" in captured.err
    assert "Cause: denied" in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_busy_os_errors_without_traceback(
    monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _raise_busy(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError(errno.EBUSY, "file busy")

    monkeypatch.setattr(cli_main, "app", _raise_busy)

    assert cli_main.main() == 1

    captured = capsys.readouterr()
    assert "environment error" in captured.err
    assert "file busy" in captured.err
    assert "Traceback" not in captured.err


def test_main_does_not_swallow_unclassified_os_errors(monkeypatch) -> None:
    def _raise_invalid(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError(errno.EINVAL, "bad value")

    monkeypatch.setattr(cli_main, "app", _raise_invalid)

    with pytest.raises(OSError, match="bad value"):
        cli_main.main()


def test_module_entrypoint_delegates_to_main(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "main", lambda: 7)
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("sdd_cli", run_name="__main__")
    assert exc_info.value.code == 7


@pytest.mark.parametrize(
    ("argv", "expected_error"),
    [
        (["python -m sdd_cli", "ask"], "Missing argument"),
        (["python -m sdd_cli", "does-not-exist"], "No such command"),
    ],
)
def test_module_entrypoint_renders_usage_errors_without_traceback(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    expected_error: str,
) -> None:
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("sdd_cli", run_name="__main__")

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert expected_error in captured.err
    assert "Traceback" not in captured.err


# ---------------------------------------------------------------------------
# Option callbacks
# ---------------------------------------------------------------------------


def test_profile_option_callback_with_value() -> None:
    import click

    ctx = MagicMock(spec=click.Context)
    ctx.obj = None
    result = _profile_option_callback(ctx, MagicMock(), "master")
    assert result == "master"
    assert ctx.obj["is_master"] is True
    assert ctx.obj["is_client"] is False


def test_profile_option_callback_without_value() -> None:
    import click

    ctx = MagicMock(spec=click.Context)
    ctx.obj = {}
    result = _profile_option_callback(ctx, MagicMock(), None)
    assert result is None
    assert "profile" not in ctx.obj


def test_json_option_callback_sets_output_json() -> None:
    import click

    ctx = MagicMock(spec=click.Context)
    ctx.obj = None
    result = _json_option_callback(ctx, MagicMock(), True)
    assert result is True
    assert ctx.obj["output_json"] is True


def test_verbose_option_callback_sets_verbose() -> None:
    import click

    ctx = MagicMock(spec=click.Context)
    ctx.obj = None
    result = _verbose_option_callback(ctx, MagicMock(), True)
    assert result is True
    assert ctx.obj["verbose"] is True


# ---------------------------------------------------------------------------
# main() — ImportError path + normal return
# ---------------------------------------------------------------------------


def test_main_configure_logging_import_error(monkeypatch) -> None:
    from unittest.mock import patch

    monkeypatch.setattr(cli_main, "app", lambda **kw: None)
    with patch.dict(sys.modules, {"sdd_core.log_config": None}):
        code = cli_main.main()
    assert code == 0


def test_main_returns_zero_when_app_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "app", lambda **kw: None)
    assert cli_main.main() == 0
