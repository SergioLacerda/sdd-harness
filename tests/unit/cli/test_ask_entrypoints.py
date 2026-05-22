"""Regression tests for top-level ask/ask-full entrypoints."""

from __future__ import annotations

from dataclasses import dataclass

from click.testing import CliRunner

from sdd_cli.main import app


@dataclass
class _FakeProfileContext:
    def as_dict(self) -> dict[str, object]:
        return {"profile": "client", "is_master": False, "is_client": True}


def _patch_profile_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_core.utils.environment.resolve_profile",
        lambda override=None: _FakeProfileContext(),
    )
    monkeypatch.setattr("sdd_cli.utils.profile.governance_gate", lambda _ctx: None)


def test_ask_top_level_invocation_without_duplication(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    called: dict[str, object] = {}

    def _fake_ask_cmd(
        query: str,
        dossier: bool = False,
        skill: str | None = None,
        budget: int | None = None,
    ) -> None:
        called["query"] = query
        called["dossier"] = dossier
        called["skill"] = skill
        called["budget"] = budget

    monkeypatch.setattr("sdd_cli.commands._ask_backend.ask_cmd", _fake_ask_cmd)

    result = CliRunner().invoke(app, ["ask", "prompt"])
    assert result.exit_code == 0, result.output
    assert called["query"] == "prompt"


def test_ask_top_level_noop_when_query_is_empty_or_null(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    called = {"count": 0}

    def _fake_ask_cmd(
        query: str,
        dossier: bool = False,
        skill: str | None = None,
        budget: int | None = None,
    ) -> None:
        called["count"] += 1

    monkeypatch.setattr("sdd_cli.commands._ask_backend.ask_cmd", _fake_ask_cmd)
    runner = CliRunner()

    for raw_query in ("", "   ", "null", "NULL", "nula", "NULA"):
        result = runner.invoke(app, ["ask", raw_query])
        assert result.exit_code == 0, result.output

    assert called["count"] == 0


def test_ask_full_top_level_invocation_without_duplication(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    called: dict[str, object] = {}

    def _fake_ask_full_cmd(
        query: str,
        log_path: str | None = None,
        log_format: str = "jsonl",
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        json_output: bool = False,
    ) -> None:
        called["query"] = query
        called["log_path"] = log_path
        called["log_format"] = log_format
        called["tokens_input"] = tokens_input
        called["tokens_output"] = tokens_output
        called["json_output"] = json_output

    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend.ask_full_cmd", _fake_ask_full_cmd
    )

    result = CliRunner().invoke(app, ["ask-full", "prompt"])
    assert result.exit_code == 0, result.output
    assert called["query"] == "prompt"


def test_ask_full_help_shows_canonical_usage(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    result = CliRunner().invoke(app, ["ask-full", "--help"])
    assert result.exit_code == 0, result.output
    assert "ask-full [OPTIONS] QUERY" in result.output
    assert "ask-full ask-full" not in result.output
