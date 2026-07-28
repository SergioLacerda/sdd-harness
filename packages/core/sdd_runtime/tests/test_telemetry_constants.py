"""Tests for telemetry constants — mandatory event allowlist."""

from sdd_runtime.telemetry._constants import _MANDATORY_EVENTS


def test_governance_ask_phase_is_mandatory():
    assert "governance.ask.phase" in _MANDATORY_EVENTS


def test_existing_mandatory_events_unchanged():
    assert "governance.ask" in _MANDATORY_EVENTS
    assert "governance.violation" in _MANDATORY_EVENTS
