"""Unit tests for sdd_cli.services.audit_runner analytics and summary."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sdd_cli.services.audit_runner import (
    _compute_base_summary,
    _default_events_path,
    _window_classification,
    _window_confidence,
)


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
