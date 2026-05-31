from __future__ import annotations

import click

from sdd_cli import main as cli_main


def test_main_returns_click_exit_code(monkeypatch) -> None:
    def _raise_exit(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise click.exceptions.Exit(3)

    monkeypatch.setattr(cli_main, "app", _raise_exit)
    assert cli_main.main() == 3
