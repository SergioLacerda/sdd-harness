"""Tests for `_ask_backend._budget` guard functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from sdd_cli.commands._ask_backend._budget import (
    _BREACH_EXIT_CODE,
    _guard_budget_breach,
    _guard_handshake,
)


def test_guard_budget_breach_noop_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_BUDGET_UTILIZATION_PCT", raising=False)

    _guard_budget_breach()


def test_guard_budget_breach_noop_when_env_not_a_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_BUDGET_UTILIZATION_PCT", "not-a-number")

    _guard_budget_breach()


def test_guard_budget_breach_noop_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_BUDGET_UTILIZATION_PCT", "99.9")

    _guard_budget_breach()


def test_guard_budget_breach_blocks_at_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_BUDGET_UTILIZATION_PCT", "100")

    with pytest.raises(typer.Exit) as exc_info:
        _guard_budget_breach()

    assert exc_info.value.exit_code == _BREACH_EXIT_CODE


def test_guard_handshake_strict_invalid_prints_block_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # _guard_handshake wraps its body in `except Exception`, so the
    # internal `typer.Exit(3)` is swallowed; only the BLOCK message surfaces.
    with (
        patch(
            "sdd_cli.commands._ask_backend._budget._signature_mode",
            return_value="strict",
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._get_cached_ahp",
            return_value={"valid": False},
        ),
    ):
        _guard_handshake(Path("/tmp"))

    captured = capsys.readouterr()
    assert "BLOCK [ask]: Missing or incomplete handshake" in captured.err


def test_guard_handshake_soft_invalid_warns(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch(
            "sdd_cli.commands._ask_backend._budget._signature_mode",
            return_value="soft",
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._get_cached_ahp",
            return_value={"valid": False},
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._json_mode",
            return_value=False,
        ),
    ):
        _guard_handshake(Path("/tmp"))

    captured = capsys.readouterr()
    assert "No active handshake" in captured.err


def test_guard_handshake_soft_invalid_json_mode_is_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch(
            "sdd_cli.commands._ask_backend._budget._signature_mode",
            return_value="soft",
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._get_cached_ahp",
            return_value={"valid": False},
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._json_mode",
            return_value=True,
        ),
    ):
        _guard_handshake(Path("/tmp"))

    captured = capsys.readouterr()
    assert "No active handshake" not in captured.err


def test_guard_handshake_falls_back_to_protocol_when_no_cached_ahp(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_ahp = type(
        "FakeAhp",
        (),
        {"is_handshake_valid": lambda self, strict: False},
    )()

    with (
        patch(
            "sdd_cli.commands._ask_backend._budget._signature_mode",
            return_value="soft",
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._get_cached_ahp",
            return_value=None,
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._json_mode",
            return_value=False,
        ),
        patch(
            "sdd_core.governance.handshake.AgentHandshakeProtocol",
            return_value=fake_ahp,
        ),
    ):
        _guard_handshake(Path("/tmp"))

    captured = capsys.readouterr()
    assert "No active handshake" in captured.err


def test_guard_handshake_valid_is_noop() -> None:
    with (
        patch(
            "sdd_cli.commands._ask_backend._budget._signature_mode",
            return_value="soft",
        ),
        patch(
            "sdd_cli.commands._ask_backend._budget._get_cached_ahp",
            return_value={"valid": True},
        ),
    ):
        _guard_handshake(Path("/tmp"))
