"""Tests for ask telemetry token resolution and capture helpers."""

from __future__ import annotations

import pytest

from sdd_cli.commands._ask_backend import (
    _capture_effective_tokens,
    _normalize_typer_value,
    _resolve_tokens,
)


def test_tokens_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_TOKENS_INPUT", "100")
    monkeypatch.setenv("SDD_TOKENS_OUTPUT", "200")
    t_in, t_out, source = _resolve_tokens("hello", "world output")
    assert t_in == 100
    assert t_out == 200
    assert source == "env"


def test_tokens_estimated_from_lengths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    query = "a" * 40
    output = "b" * 80
    t_in, t_out, source = _resolve_tokens(query, output)
    assert t_in == 40 // 4
    assert t_out == 80 // 4
    assert source == "estimated"


def test_tokens_none_when_empty_and_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    t_in, t_out, source = _resolve_tokens("", "")
    assert t_in is None
    assert t_out is None
    assert source == "estimated"


def test_tokens_env_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_TOKENS_INPUT", "50")
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    output = "x" * 100
    t_in, t_out, source = _resolve_tokens("query", output)
    assert t_in == 50
    assert t_out == 100 // 4
    assert source == "env"


def test_normalize_typer_value_optioninfo() -> None:
    from typer import Option

    value = Option(None, "--skill")
    assert _normalize_typer_value(value, "fallback") == "fallback"
    assert _normalize_typer_value("ok", "fallback") == "ok"


def test_capture_effective_tokens_prefers_direct_values() -> None:
    t_in, t_out = _capture_effective_tokens(12, 34)
    assert (t_in, t_out) == (12, 34)


def test_capture_effective_tokens_env_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_TOKENS_INPUT", "56")
    monkeypatch.setenv("SDD_TOKENS_OUTPUT", "78")
    t_in, t_out = _capture_effective_tokens(None, None)
    assert (t_in, t_out) == (56, 78)
