from __future__ import annotations

from unittest.mock import patch

import pytest
import typer

from sdd_cli.commands import lint

pytestmark = pytest.mark.unit


def test_run_executes_architecture_checks_before_mypy_and_bandit() -> None:
    calls: list[str] = []

    def _fake_run_step(label: str, cmd: list[str], *, fix: bool) -> int:
        calls.append(label)
        return 0

    with (
        patch("sdd_cli.commands.lint._run_ruff", return_value=False),
        patch("sdd_cli.commands.lint._run_step", side_effect=_fake_run_step),
        patch("sdd_cli.commands.lint.spec"),
    ):
        lint.run(fix=False, skip_mypy=False, skip_bandit=False, skip_spec=False)

    assert calls[:6] == [
        "architecture imports",
        "architecture cycles",
        "architecture class-size",
        "cognitive governance",
        "mypy",
        "bandit",
    ]


def test_run_exits_nonzero_when_architecture_check_fails() -> None:
    with (
        patch("sdd_cli.commands.lint._run_ruff", return_value=False),
        patch(
            "sdd_cli.commands.lint._run_step",
            side_effect=[1, 0, 0, 0, 0],
        ),
        patch("sdd_cli.commands.lint.spec"),
        pytest.raises(typer.Exit) as exc,
    ):
        lint.run(fix=False, skip_mypy=False, skip_bandit=False, skip_spec=False)

    assert exc.value.exit_code == 1
