"""Unit tests for sdd_cli.services.audit_runner."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_cli.services.audit_runner import (
    _as_score,
    _compute_base_summary,
    _default_events_path,
    _drift_cause,
    _drift_type,
    _event_ts,
    _has_quality_signals,
    _is_drift_event,
    _load_events,
    _parse_int,
    _parse_ts,
    _quality_score,
    _ts_sort_key,
    _window_classification,
    _window_confidence,
    _window_events,
)


class TestParseInt:
    def test_returns_none_for_bool(self) -> None:
        assert _parse_int(True) is None
        assert _parse_int(False) is None

    def test_returns_int_from_float(self) -> None:
        assert _parse_int(3.7) == 3

    def test_returns_none_for_non_digit_string(self) -> None:
        assert _parse_int("abc") is None
        assert _parse_int("1.5") is None

    def test_returns_int_from_digit_string(self) -> None:
        assert _parse_int("42") == 42

    def test_returns_none_for_other_types(self) -> None:
        assert _parse_int(None) is None
        assert _parse_int([]) is None


class TestEventTs:
    def test_returns_empty_string_when_no_ts_fields(self) -> None:
        assert _event_ts({}) == ""
        assert _event_ts({"command": "ask"}) == ""


class TestParseTs:
    def test_returns_none_for_empty_string(self) -> None:
        assert _parse_ts("") is None

    def test_returns_none_for_invalid_iso(self) -> None:
        assert _parse_ts("not-a-date") is None

    def test_handles_naive_datetime(self) -> None:
        result = _parse_ts("2026-01-15T10:00:00")
        assert result is not None
        assert result.tzinfo == timezone.utc


class TestTsSortKey:
    def test_empty_string_returns_zero_key(self) -> None:
        assert _ts_sort_key("") == (0, "")

    def test_invalid_ts_returns_one_with_original(self) -> None:
        key = _ts_sort_key("garbage")
        assert key[0] == 1
        assert key[1] == "garbage"


class TestLoadEvents:
    def test_returns_empty_list_for_missing_file(self, tmp_path: Path) -> None:
        assert _load_events(tmp_path / "nonexistent.jsonl") == []

    def test_skips_invalid_json_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\nnot-json\n{"ok": 2}\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 2

    def test_skips_non_dict_json_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\n[1,2,3]\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 1

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\n\n{"ok": 2}\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 2


class TestIsDriftEvent:
    def test_detects_drift_type_not_none(self) -> None:
        event = {"event": "x", "details": {"drift_type": "profile_drift"}}
        assert _is_drift_event(event) is True

    def test_ignores_drift_type_none(self) -> None:
        event = {"event": "x", "details": {"drift_type": "none"}}
        assert _is_drift_event(event) is False


class TestDriftType:
    def test_returns_missing_when_no_drift_type(self) -> None:
        assert _drift_type({"details": {}}) == "missing_drift_type"
        assert _drift_type({}) == "missing_drift_type"

    def test_returns_drift_type_when_present(self) -> None:
        assert (
            _drift_type({"details": {"drift_type": "profile_drift"}}) == "profile_drift"
        )


class TestDriftCause:
    def test_returns_found_cause(self) -> None:
        event = {"details": {"drift_cause": "config mismatch"}}
        assert _drift_cause(event) == "config mismatch"

    def test_returns_empty_when_no_cause(self) -> None:
        assert _drift_cause({}) == ""


class TestWindowEvents:
    def test_excludes_events_with_unparseable_timestamps(self) -> None:
        from datetime import datetime, timezone

        events = [
            {"event": "x", "start_ts": "not-a-date"},
            {"event": "y", "start_ts": "2026-05-20T10:00:00Z"},
        ]
        now = datetime.now(timezone.utc)
        result = _window_events(events, now_utc=now, days=30)
        assert len(result) == 1


class TestHasQualitySignals:
    def test_returns_true_when_tests_passed_present(self) -> None:
        events = [{"details": {"tests_passed": True}}]
        assert _has_quality_signals(events) is True

    def test_returns_false_when_non_dict_details(self) -> None:
        events = [{"details": "string_details"}, {"no_details": True}]
        assert _has_quality_signals(events) is False


class TestWindowConfidence:
    def test_returns_high_when_both_thresholds_met(self) -> None:
        assert _window_confidence(0.8, 0.9) == "HIGH"

    def test_returns_medium_when_one_threshold_met(self) -> None:
        assert _window_confidence(0.8, 0.5) == "MEDIUM"
        assert _window_confidence(0.5, 0.9) == "MEDIUM"

    def test_returns_low_when_neither_threshold_met(self) -> None:
        assert _window_confidence(0.3, 0.5) == "LOW"


class TestWindowClassification:
    def test_inconclusive_when_no_asks(self) -> None:
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
        assert _as_score(True) == 1.0
        assert _as_score(False) == 0.0

    def test_numeric_clamped(self) -> None:
        assert _as_score(0.5) == 0.5
        assert _as_score(2.0) == 1.0
        assert _as_score(-1.0) == 0.0

    def test_string_truthy(self) -> None:
        for val in ("true", "pass", "passed", "ok", "accepted", "yes"):
            assert _as_score(val) == 1.0

    def test_string_falsy(self) -> None:
        for val in ("false", "fail", "failed", "rejected", "no"):
            assert _as_score(val) == 0.0

    def test_unknown_string_returns_zero(self) -> None:
        assert _as_score("maybe") == 0.0


class TestQualityScore:
    def test_returns_none_when_no_signals(self) -> None:
        assert _quality_score([]) is None
        assert _quality_score([{"details": {}}]) is None

    def test_skips_non_dict_details(self) -> None:
        events = [{"details": "not-a-dict"}, {"details": {"tests_passed": True}}]
        result = _quality_score(events)
        assert result is not None

    def test_uses_tests_passed(self) -> None:
        events = [{"details": {"tests_passed": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(60.0)

    def test_uses_human_accepted(self) -> None:
        events = [{"details": {"human_accepted": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(40.0)

    def test_combines_both_signals(self) -> None:
        events = [{"details": {"tests_passed": True, "human_accepted": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(100.0)


class TestComputeBaseSummaryUnclassified:
    def test_counts_unclassified_drifts(self) -> None:
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
        with (
            patch(
                "sdd_cli.services.audit_runner.resolve_workspace_root",
                side_effect=Exception("no workspace"),
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            result = _default_events_path()

        assert result == tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
