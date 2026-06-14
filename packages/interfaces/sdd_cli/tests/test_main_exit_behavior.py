from __future__ import annotations

import sys
from unittest.mock import MagicMock

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
