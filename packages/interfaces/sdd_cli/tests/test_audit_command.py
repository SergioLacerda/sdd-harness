from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


def _write_events(path: Path) -> None:
    events = [
        {
            "event": "governance.ask",
            "command": "ask",
            "status": "ok",
            "start_ts": "2026-05-20T10:00:00Z",
            "artifact_fingerprint": "aaaaaaaa11111111",
            "tokens_input": 120,
            "tokens_output": 60,
            "details": {"drift_detected": False},
        },
        {
            "event": "runtime.drift.detected",
            "command": "runtime status",
            "status": "warn",
            "start_ts": "2026-05-20T10:05:00Z",
            "artifact_fingerprint": "bbbbbbbb22222222",
            "details": {
                "drift_type": "profile_drift",
                "reason": "profile mismatch",
                "remediation_command": "sdd runtime status --force",
            },
        },
        {
            "event": "governance.ask",
            "command": "ask",
            "status": "warn",
            "start_ts": "2026-05-20T10:10:00Z",
            "artifact_fingerprint": "cccccccc33333333",
            "tokens_input": 80,
            "tokens_output": 40,
            "details": {"drift_detected": True, "drift_type": "session_drift"},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")


def test_audit_default_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    assert "SDD Audit Summary" in result.output
    assert "- total events: 3" in result.output
    assert "- total drifts: 2" in result.output
    assert "Correlation Windows (7/14/30)" in result.output
    assert "Top 10 Drift Events" in result.output
    assert "profile_drift" in result.output


def test_audit_json_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["--json", "audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["command"] == "audit"
    assert payload["ok"] is True
    assert payload["data"]["total_events"] == 3
    assert payload["data"]["total_drifts"] == 2
    assert payload["data"]["token_comparison"]["total_input_tokens"] == 200
    assert payload["data"]["token_comparison"]["total_output_tokens"] == 100
    assert "drift_unclassified_total" in payload["data"]
    assert "correlation_windows" in payload["data"]
    assert [w["window_days"] for w in payload["data"]["correlation_windows"]] == [
        7,
        14,
        30,
    ]
    assert len(payload["data"]["top_drifts"]) == 2


def test_audit_json_output_uses_canonical_data_payload(
    tmp_path: Path, monkeypatch
) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["--json", "audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["command"] == "audit"
    assert payload["data"]["total_events"] == 3
    assert "total_events" not in payload


def test_audit_include_non_drift_flag(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(
        app,
        ["--json", "audit", "--events-file", str(events_file), "--include-non-drift"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert "non_drift_events" in payload["data"]


def test_audit_no_drift_events_text_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.write_text(
        json.dumps(
            {
                "event": "governance.ask",
                "command": "ask",
                "start_ts": "2026-05-20T10:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert result.exit_code == 0
    assert "no drift events found" in result.output


class TestParseInt:
    def test_returns_none_for_bool(self) -> None:
        from sdd_cli.commands.audit import _parse_int

        assert _parse_int(True) is None
        assert _parse_int(False) is None

    def test_returns_int_from_float(self) -> None:
        from sdd_cli.commands.audit import _parse_int

        assert _parse_int(3.7) == 3

    def test_returns_none_for_non_digit_string(self) -> None:
        from sdd_cli.commands.audit import _parse_int

        assert _parse_int("abc") is None
        assert _parse_int("1.5") is None

    def test_returns_int_from_digit_string(self) -> None:
        from sdd_cli.commands.audit import _parse_int

        assert _parse_int("42") == 42

    def test_returns_none_for_other_types(self) -> None:
        from sdd_cli.commands.audit import _parse_int

        assert _parse_int(None) is None
        assert _parse_int([]) is None


class TestEventTs:
    def test_returns_empty_string_when_no_ts_fields(self) -> None:
        from sdd_cli.commands.audit import _event_ts

        assert _event_ts({}) == ""
        assert _event_ts({"command": "ask"}) == ""


class TestParseTs:
    def test_returns_none_for_empty_string(self) -> None:
        from sdd_cli.commands.audit import _parse_ts

        assert _parse_ts("") is None

    def test_returns_none_for_invalid_iso(self) -> None:
        from sdd_cli.commands.audit import _parse_ts

        assert _parse_ts("not-a-date") is None

    def test_handles_naive_datetime(self) -> None:
        from datetime import timezone

        from sdd_cli.commands.audit import _parse_ts

        result = _parse_ts("2026-01-15T10:00:00")
        assert result is not None
        assert result.tzinfo == timezone.utc


class TestTsSortKey:
    def test_empty_string_returns_zero_key(self) -> None:
        from sdd_cli.commands.audit import _ts_sort_key

        assert _ts_sort_key("") == (0, "")

    def test_invalid_ts_returns_one_with_original(self) -> None:
        from sdd_cli.commands.audit import _ts_sort_key

        key = _ts_sort_key("garbage")
        assert key[0] == 1
        assert key[1] == "garbage"


class TestLoadEvents:
    def test_returns_empty_list_for_missing_file(self, tmp_path: Path) -> None:
        from sdd_cli.commands.audit import _load_events

        assert _load_events(tmp_path / "nonexistent.jsonl") == []

    def test_skips_invalid_json_lines(self, tmp_path: Path) -> None:
        from sdd_cli.commands.audit import _load_events

        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\nnot-json\n{"ok": 2}\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 2

    def test_skips_non_dict_json_lines(self, tmp_path: Path) -> None:
        from sdd_cli.commands.audit import _load_events

        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\n[1,2,3]\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 1

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        from sdd_cli.commands.audit import _load_events

        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\n\n{"ok": 2}\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 2


class TestIsDriftEvent:
    def test_detects_drift_type_not_none(self) -> None:
        from sdd_cli.commands.audit import _is_drift_event

        event = {"event": "x", "details": {"drift_type": "profile_drift"}}
        assert _is_drift_event(event) is True

    def test_ignores_drift_type_none(self) -> None:
        from sdd_cli.commands.audit import _is_drift_event

        event = {"event": "x", "details": {"drift_type": "none"}}
        assert _is_drift_event(event) is False


class TestDriftType:
    def test_returns_missing_when_no_drift_type(self) -> None:
        from sdd_cli.commands.audit import _drift_type

        assert _drift_type({"details": {}}) == "missing_drift_type"
        assert _drift_type({}) == "missing_drift_type"

    def test_returns_drift_type_when_present(self) -> None:
        from sdd_cli.commands.audit import _drift_type

        assert (
            _drift_type({"details": {"drift_type": "profile_drift"}}) == "profile_drift"
        )


class TestDriftCause:
    def test_returns_found_cause(self) -> None:
        from sdd_cli.commands.audit import _drift_cause

        event = {"details": {"drift_cause": "config mismatch"}}
        assert _drift_cause(event) == "config mismatch"

    def test_returns_empty_when_no_cause(self) -> None:
        from sdd_cli.commands.audit import _drift_cause

        assert _drift_cause({}) == ""


class TestWindowEvents:
    def test_excludes_events_with_unparseable_timestamps(self) -> None:
        from datetime import datetime, timezone

        from sdd_cli.commands.audit import _window_events

        events = [
            {"event": "x", "start_ts": "not-a-date"},
            {"event": "y", "start_ts": "2026-05-20T10:00:00Z"},
        ]
        now = datetime.now(timezone.utc)
        result = _window_events(events, now_utc=now, days=30)
        assert len(result) == 1


class TestHasQualitySignals:
    def test_returns_true_when_tests_passed_present(self) -> None:
        from sdd_cli.commands.audit import _has_quality_signals

        events = [{"details": {"tests_passed": True}}]
        assert _has_quality_signals(events) is True

    def test_returns_false_when_non_dict_details(self) -> None:
        from sdd_cli.commands.audit import _has_quality_signals

        events = [{"details": "string_details"}, {"no_details": True}]
        assert _has_quality_signals(events) is False


class TestWindowConfidence:
    def test_returns_high_when_both_thresholds_met(self) -> None:
        from sdd_cli.commands.audit import _window_confidence

        assert _window_confidence(0.8, 0.9) == "HIGH"

    def test_returns_medium_when_one_threshold_met(self) -> None:
        from sdd_cli.commands.audit import _window_confidence

        assert _window_confidence(0.8, 0.5) == "MEDIUM"
        assert _window_confidence(0.5, 0.9) == "MEDIUM"

    def test_returns_low_when_neither_threshold_met(self) -> None:
        from sdd_cli.commands.audit import _window_confidence

        assert _window_confidence(0.3, 0.5) == "LOW"


class TestWindowClassification:
    def test_inconclusive_when_no_asks(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=0,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=None,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"

    def test_inconclusive_when_no_quality_signals(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=False,
            quality_delta=None,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"

    def test_inconclusive_when_low_token_coverage(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.5,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"

    def test_inconclusive_when_low_drift_coverage(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.5,
        )
        assert cls == "INCONCLUSIVO"

    def test_enriquecimento_positivo(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=10.0,
            drift_delta=1.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "ENRIQUECIMENTO_POSITIVO"

    def test_economia_saudavel(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=-1.0,
            drift_delta=1.0,
            ratio_delta=-0.5,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "ECONOMIA_SAUDAVEL"

    def test_economia_falsa(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=-10.0,
            drift_delta=5.0,
            ratio_delta=-0.5,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "ECONOMIA_FALSA"

    def test_inflacao_improdutiva(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=1.0,
            ratio_delta=0.5,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INFLACAO_IMPRODUTIVA"


class TestAsScore:
    def test_bool_true(self) -> None:
        from sdd_cli.commands.audit import _as_score

        assert _as_score(True) == 1.0
        assert _as_score(False) == 0.0

    def test_numeric_clamped(self) -> None:
        from sdd_cli.commands.audit import _as_score

        assert _as_score(0.5) == 0.5
        assert _as_score(2.0) == 1.0
        assert _as_score(-1.0) == 0.0

    def test_string_truthy(self) -> None:
        from sdd_cli.commands.audit import _as_score

        for val in ("true", "pass", "passed", "ok", "accepted", "yes"):
            assert _as_score(val) == 1.0

    def test_string_falsy(self) -> None:
        from sdd_cli.commands.audit import _as_score

        for val in ("false", "fail", "failed", "rejected", "no"):
            assert _as_score(val) == 0.0

    def test_unknown_string_returns_zero(self) -> None:
        from sdd_cli.commands.audit import _as_score

        assert _as_score("maybe") == 0.0


class TestQualityScore:
    def test_returns_none_when_no_signals(self) -> None:
        from sdd_cli.commands.audit import _quality_score

        assert _quality_score([]) is None
        assert _quality_score([{"details": {}}]) is None

    def test_skips_non_dict_details(self) -> None:
        from sdd_cli.commands.audit import _quality_score

        events = [{"details": "not-a-dict"}, {"details": {"tests_passed": True}}]
        result = _quality_score(events)
        assert result is not None

    def test_uses_tests_passed(self) -> None:
        from sdd_cli.commands.audit import _quality_score

        events = [{"details": {"tests_passed": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(60.0)

    def test_uses_human_accepted(self) -> None:
        from sdd_cli.commands.audit import _quality_score

        events = [{"details": {"human_accepted": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(40.0)

    def test_combines_both_signals(self) -> None:
        from sdd_cli.commands.audit import _quality_score

        events = [{"details": {"tests_passed": True, "human_accepted": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(100.0)


class TestComputeBaseSummaryUnclassified:
    def test_counts_unclassified_drifts(self) -> None:
        from sdd_cli.commands.audit import _compute_base_summary

        events = [
            {
                "event": "runtime.drift.detected",
                "command": "runtime status",
                "start_ts": "2026-05-20T10:00:00Z",
                "artifact_fingerprint": "fp-1",
                "details": {},
            }
        ]
        result = _compute_base_summary(events, top=10)
        assert result["unclassified_drifts"] == 1


class TestWindowClassificationDefault:
    def test_returns_inconclusive_when_no_delta_pattern(self) -> None:
        from sdd_cli.commands.audit import _window_classification

        cls, msg = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=0.5,
            ratio_delta=0.05,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"
        assert "No significant delta" in msg


class TestDefaultEventsPath:
    def test_falls_back_to_cwd_on_exception(self, tmp_path: Path) -> None:
        from sdd_cli.commands.audit import _default_events_path

        with (
            patch(
                "sdd_cli.commands.audit.resolve_workspace_root",
                side_effect=Exception("no workspace"),
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            result = _default_events_path()

        assert result == tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
