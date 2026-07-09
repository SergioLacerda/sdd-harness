"""Tests for the ask-pipeline phase timer helper."""

from __future__ import annotations

import time

import pytest
from sdd_cli.commands._ask_backend._phase_timer import PhaseRecord, PhaseTimer


def test_phase_timer_records_single_phase():
    timer = PhaseTimer()
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        time.sleep(0.01)

    records = timer.records()
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, PhaseRecord)
    assert record.phase_id == "ask.workspace.resolve"
    assert record.latency_domain == "local_fs"
    assert record.duration_ms >= 10
    assert record.start_ts < record.end_ts
    assert record.measurement_quality == "measured"
    assert record.observed_by == "sdd_cli"
    assert record.failed is False


def test_phase_timer_records_multiple_phases_in_order():
    timer = PhaseTimer()
    with timer.phase("ask.cli.entry", latency_domain="local_cli"):
        pass
    with timer.phase("ask.response.render", latency_domain="rendering"):
        pass

    ids = [r.phase_id for r in timer.records()]
    assert ids == ["ask.cli.entry", "ask.response.render"]


def test_phase_timer_marks_failed_phase_and_reraises():
    timer = PhaseTimer()
    with pytest.raises(ValueError):
        with timer.phase("ask.governance.snapshot", latency_domain="governance"):
            raise ValueError("boom")

    records = timer.records()
    assert len(records) == 1
    assert records[0].failed is True


def test_phase_timer_total_and_unattributed_ms():
    timer = PhaseTimer()
    with timer.phase("ask.cli.entry", latency_domain="local_cli"):
        time.sleep(0.01)

    total_ms = timer.phase_total_ms()
    assert total_ms >= 10

    unattributed = timer.unattributed_ms(session_duration_ms=total_ms + 50)
    assert unattributed == 50
