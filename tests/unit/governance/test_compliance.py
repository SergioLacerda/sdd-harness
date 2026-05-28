"""Unit tests for sdd_core.governance.compliance (append-only JSONL audit log)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from sdd_core.governance.compliance import (
    ASK_COMMAND,
    ASK_FULL_COMMAND,
    COMMAND_INVOKED,
    COMPILE_COMPLETE,
    GOVERNANCE_CHECKED,
    VIOLATION,
    WORKSPACE_INIT,
    append_event,
    compute_governance_adherence,
    log_ask_event,
    read_events,
)
from sdd_core.governance.compliance_constants import default_log_path
from tests.helpers.text_io import read_text_utf8, write_text_utf8

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(tmp_path: Path) -> Path:
    return tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAppendEvent:
    """append_event writes valid JSONL records."""

    def test_creates_parent_dirs_and_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        assert not log.exists()
        append_event(
            WORKSPACE_INIT,
            command="init",
            profile="client",
            state="NOT_INITIALIZED",
            log_path=log,
        )
        assert log.exists()

    def test_record_schema(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(
            GOVERNANCE_CHECKED,
            command="doctor",
            profile="master",
            state="PARTIAL",
            log_path=log,
        )
        record = json.loads(read_text_utf8(log).strip().splitlines()[-1])
        assert record["event"] == GOVERNANCE_CHECKED
        assert record["command"] == "doctor"
        assert record["profile"] == "master"
        assert record["state"] == "PARTIAL"
        assert "timestamp" in record

    def test_respects_sdd_agent_id_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(
            COMMAND_INVOKED,
            command="ask",
            profile="client",
            message="Agent copilot-agent-42 executed ask",
            log_path=log,
        )
        record = json.loads(read_text_utf8(log).strip().splitlines()[-1])
        assert "copilot-agent-42" in record["message"]

    def test_appends_multiple_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(WORKSPACE_INIT, command="init", profile="client", log_path=log)
        append_event(
            COMPILE_COMPLETE, command="compile", profile="master", log_path=log
        )
        append_event(VIOLATION, command="ask", profile="client", log_path=log)
        lines = [line for line in read_text_utf8(log).splitlines() if line.strip()]
        assert len(lines) == 3
        assert json.loads(lines[0])["event"] == WORKSPACE_INIT
        assert json.loads(lines[2])["event"] == VIOLATION

    def test_includes_details_when_provided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(
            WORKSPACE_INIT,
            command="init",
            profile="client",
            details={"workspace_id": "abc-123"},
            log_path=log,
        )
        record = json.loads(read_text_utf8(log).strip())
        assert record["details"]["workspace_id"] == "abc-123"

    def test_never_raises_on_unwritable_path(self, tmp_path: Path) -> None:
        # Point at a path that cannot be created (file exists where dir should be).
        blocker = tmp_path / "blocked"
        blocker.write_text("I am a file", encoding="utf-8")
        bad_log = blocker / "compliance-events.jsonl"
        # Should not raise — failures are swallowed as warnings.
        append_event(WORKSPACE_INIT, command="init", profile="client", log_path=bad_log)


class TestReadEvents:
    """read_events returns parsed records in chronological order."""

    def test_returns_empty_when_log_missing(self, tmp_path: Path) -> None:
        result = read_events(log_path=_log(tmp_path))
        assert result == []

    def test_returns_all_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        for event in (WORKSPACE_INIT, GOVERNANCE_CHECKED, COMPILE_COMPLETE):
            append_event(event, command="test", profile="client", log_path=log)
        result = read_events(n=10, log_path=log)
        assert len(result) == 3

    def test_n_cap_returns_last_n(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        events = [
            WORKSPACE_INIT,
            GOVERNANCE_CHECKED,
            COMPILE_COMPLETE,
            VIOLATION,
            COMMAND_INVOKED,
        ]
        for e in events:
            append_event(e, command="test", profile="client", log_path=log)
        result = read_events(n=2, log_path=log)
        assert len(result) == 2
        assert result[-1]["event"] == COMMAND_INVOKED

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        log.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(
            log,
            '{"event": "WORKSPACE_INIT"}\nnot-json\n{"event": "VIOLATION"}\n',
        )
        result = read_events(n=10, log_path=log)
        assert len(result) == 2
        assert result[0]["event"] == "WORKSPACE_INIT"
        assert result[1]["event"] == "VIOLATION"


class TestComputeGovernanceAdherence:
    """compute_governance_adherence returns a structured 0-100 score."""

    def _write_state(self, tmp_path: Path, **kwargs: object) -> Path:
        state_dir = tmp_path / ".sdd" / "runtime"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "governance-state.json"
        write_text_utf8(
            state_file, json.dumps({"last_check": datetime.now().isoformat(), **kwargs})
        )
        return state_file

    def test_returns_dict_with_required_keys(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert "score" in result
        assert "behavioral" in result
        assert "structural" in result
        assert "freshness" in result
        assert "details" in result

    def test_score_is_int_in_0_100_range(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert isinstance(result["score"], int)
        assert 0 <= result["score"] <= 100

    def test_empty_log_gives_full_behavioral_score(self, tmp_path: Path) -> None:
        """No events → assume perfect adherence (1.0 behavioral ratio)."""
        log = _log(tmp_path)
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert result["behavioral"] == 1.0
        assert result["details"]["behavioral_score"] == 50

    def test_all_allows_gives_full_behavioral_score(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        for _ in range(5):
            append_event(
                GOVERNANCE_CHECKED, command="test", profile="client", log_path=log
            )
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert result["behavioral"] == 1.0
        assert result["details"]["behavioral_score"] == 50

    def test_violations_reduce_behavioral_score(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        # 2 allows, 1 warn, 1 block → ratio = 2/4 = 0.5 → score = 25
        for _ in range(2):
            append_event(
                GOVERNANCE_CHECKED, command="test", profile="client", log_path=log
            )
        append_event(
            VIOLATION,
            command="test",
            profile="client",
            details={"action": "warn"},
            log_path=log,
        )
        append_event(
            VIOLATION,
            command="test",
            profile="client",
            details={"action": "block"},
            log_path=log,
        )
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert result["details"]["allows"] == 2
        assert result["details"]["warns"] == 1
        assert result["details"]["blocks"] == 1
        assert result["behavioral"] == 0.5
        assert result["details"]["behavioral_score"] == 25

    def test_events_outside_window_excluded(self, tmp_path: Path) -> None:
        """Events older than window_hours are not counted."""
        log = _log(tmp_path)
        log.parent.mkdir(parents=True, exist_ok=True)
        old_ts = (datetime.now() - timedelta(hours=48)).isoformat(timespec="seconds")
        old_record = json.dumps(
            {
                "timestamp": old_ts,
                "event": VIOLATION,
                "command": "ask",
                "profile": "client",
                "state": "ACTIVE",
                "details": {"action": "block"},
                "status": "error",
                "level": "error",
                "service": "sdd",
            }
        )
        log.write_text(old_record + "\n", encoding="utf-8")
        # window=24h — the old violation should not count
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path), window_hours=24
        )
        assert result["details"]["blocks"] == 0
        assert result["behavioral"] == 1.0

    def test_freshness_full_when_recent_check(self, tmp_path: Path) -> None:
        state = self._write_state(
            tmp_path, profile="client", last_check=datetime.now().isoformat()
        )
        result = compute_governance_adherence(log_path=_log(tmp_path), state_path=state)
        # Just checked → freshness close to 1.0
        assert result["freshness"] > 0.99
        assert result["details"]["freshness_score"] == 20

    def test_freshness_zero_when_stale(self, tmp_path: Path) -> None:
        old_ts = (datetime.now() - timedelta(hours=10)).isoformat()
        state = self._write_state(tmp_path, profile="client", last_check=old_ts)
        # client TTL = 1800s; 10h >> 30min
        result = compute_governance_adherence(log_path=_log(tmp_path), state_path=state)
        assert result["freshness"] == 0.0
        assert result["details"]["freshness_score"] == 0

    def test_structural_false_when_no_state_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent-state.json"
        result = compute_governance_adherence(
            log_path=_log(tmp_path), state_path=missing
        )
        assert result["structural"] is False
        assert result["details"]["structural_score"] == 0

    def test_structural_false_when_fingerprint_mismatch(self, tmp_path: Path) -> None:
        state = self._write_state(tmp_path, spec_fingerprint="aabbccddeeff0011")
        # No compiled artifact exists → structural mismatch
        result = compute_governance_adherence(
            log_path=_log(tmp_path), state_path=state, workspace_root=tmp_path
        )
        assert result["structural"] is False

    def test_structural_true_when_fingerprints_match(self, tmp_path: Path) -> None:
        # Create a fake compiled governance-core.json with a fingerprint
        artifact_dir = tmp_path / ".sdd" / "compiled"
        artifact_dir.mkdir(parents=True)
        fp = "499f7ce0da5ec85f"
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": fp, "items": []}), encoding="utf-8"
        )
        state = self._write_state(tmp_path, spec_fingerprint=fp)
        result = compute_governance_adherence(
            log_path=_log(tmp_path), state_path=state, workspace_root=tmp_path
        )
        assert result["structural"] is True
        assert result["details"]["structural_score"] == 30

    def test_score_is_sum_of_dimensions(self, tmp_path: Path) -> None:
        state = self._write_state(tmp_path)
        result = compute_governance_adherence(log_path=_log(tmp_path), state_path=state)
        d = result["details"]
        assert (
            result["score"]
            == d["behavioral_score"] + d["structural_score"] + d["freshness_score"]
        )


class TestLogAskEvent:
    """log_ask_event writes an event to the compliance log."""

    def test_log_ask_event_writes_record(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
        log_ask_event(
            event=ASK_COMMAND,
            command="ask",
            profile="client",
            state="HEALTHY",
            agent_id="test-agent",
            details={
                "query_hash": "abc123",
                "context_source": "compiled",
                "compiled_fingerprint_used": "fp",
                "mandates_loaded": 2,
            },
            log_path=log,
        )
        assert log.exists()
        record = json.loads(read_text_utf8(log).strip())
        assert record["event"] == ASK_COMMAND
        assert record["agent_id"] == "test-agent"
        assert record["details"]["query_hash"] == "abc123"

    def test_log_ask_full_event_with_trace_id(self, tmp_path: Path) -> None:
        log = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
        log_ask_event(
            event=ASK_FULL_COMMAND,
            command="ask-full",
            profile="master",
            state="ACTIVE",
            agent_id="agent-x",
            details={
                "query_hash": "xyz789",
                "context_source": "json",
                "compiled_fingerprint_used": "fp2",
                "mandates_loaded": 5,
                "trace_id": "trace-uuid",
                "steps": [],
            },
            log_path=log,
        )
        record = json.loads(read_text_utf8(log).strip())
        assert record["event"] == ASK_FULL_COMMAND
        assert record["details"]["trace_id"] == "trace-uuid"


class TestReadAllEvents:
    """_read_all_events returns all events without N cap."""

    def test_returns_all_events_no_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer
        from sdd_core.governance.compliance import (
            COMMAND_INVOKED,
            COMPILE_COMPLETE,
            GOVERNANCE_CHECKED,
            VIOLATION,
            WORKSPACE_INIT,
            append_event,
        )

        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        for event in [
            WORKSPACE_INIT,
            GOVERNANCE_CHECKED,
            COMPILE_COMPLETE,
            VIOLATION,
            COMMAND_INVOKED,
        ]:
            append_event(event, command="test", profile="client", log_path=log)

        result = GovernanceAdherenceScorer._read_all_events(log_path=log)
        assert len(result) == 5

    def test_returns_empty_when_log_missing(self, tmp_path: Path) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        result = GovernanceAdherenceScorer._read_all_events(log_path=_log(tmp_path))
        assert result == []

    def test_returns_empty_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        monkeypatch.setenv("SDD_COMPLIANCE_LOG", "disabled")
        result = GovernanceAdherenceScorer._read_all_events()
        assert result == []


class TestDefaultLogPath:
    def test_returns_none_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", "disabled")
        result = default_log_path()
        assert result is None

    def test_returns_override_when_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        custom_log = str(tmp_path / "custom.jsonl")
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", custom_log)
        result = default_log_path()
        assert result is not None
        assert str(result) == custom_log

    def test_returns_default_when_no_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_COMPLIANCE_LOG", raising=False)
        result = default_log_path(workspace_root=tmp_path)
        assert result is not None
        assert result.name == "compliance-events.jsonl"


class TestGetCompiledFingerprint:
    def test_returns_empty_when_no_artifacts(self, tmp_path: Path) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert result == ""

    def test_returns_fingerprint_from_artifact(self, tmp_path: Path) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        artifact_dir = tmp_path / ".sdd" / "compiled"
        artifact_dir.mkdir(parents=True)
        fp = "abc123def456"
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": fp, "items": []}), encoding="utf-8"
        )
        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert result == fp

    def test_computes_fallback_fingerprint_when_not_embedded(
        self, tmp_path: Path
    ) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        artifact_dir = tmp_path / ".sdd" / "compiled"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"items": [{"id": "M001"}]}),
            encoding="utf-8",  # no fingerprint field
        )
        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert len(result) == 64  # SHA256 hex


class TestDefaultLogPathFallbacks:
    def test_uses_find_workspace_root_when_no_workspace_arg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_COMPLIANCE_LOG", raising=False)
        with patch(
            "sdd_core.utils.environment.find_workspace_root", return_value=tmp_path
        ):
            result = default_log_path()
        assert result is not None
        assert "compliance-events.jsonl" in result.name

    def test_falls_back_to_cwd_when_find_workspace_root_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_COMPLIANCE_LOG", raising=False)
        with patch("sdd_core.utils.environment.find_workspace_root", return_value=None):
            result = default_log_path()
        assert result is not None
        assert result.name == "compliance-events.jsonl"

    def test_falls_back_when_find_workspace_root_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_COMPLIANCE_LOG", raising=False)
        with patch(
            "sdd_core.utils.environment.find_workspace_root",
            side_effect=RuntimeError("no ws"),
        ):
            result = default_log_path()
        # Falls back to cwd-based path
        assert result is not None
        assert result.name == "compliance-events.jsonl"


class TestAppendEventWhenTargetNone:
    def test_does_not_raise_when_log_path_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", "disabled")
        # Should silently do nothing (target is None)
        append_event(WORKSPACE_INIT, command="test", profile="client")


class TestReadAllEventsException:
    def test_returns_empty_on_read_exception(self, tmp_path: Path) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        log = _log(tmp_path)
        log.parent.mkdir(parents=True, exist_ok=True)
        # Write binary content that will cause a UTF-8 decode error
        log.write_bytes(b"\xff\xfe\x00\x01")
        result = GovernanceAdherenceScorer._read_all_events(log_path=log)
        # Must not raise — returns empty list on exception
        assert isinstance(result, list)


class TestComputeGovernanceAdherenceNoStatePath:
    def test_resolves_state_via_find_workspace_root(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".sdd" / "runtime"
        state_dir.mkdir(parents=True)
        (state_dir / "governance-state.json").write_text(
            json.dumps({"last_check": datetime.now().isoformat()}),
            encoding="utf-8",
        )

        with patch(
            "sdd_core.utils.environment.find_workspace_root", return_value=tmp_path
        ):
            result = compute_governance_adherence(log_path=_log(tmp_path))
        assert "score" in result

    def test_returns_score_when_find_workspace_root_returns_none(self) -> None:
        with patch("sdd_core.utils.environment.find_workspace_root", return_value=None):
            result = compute_governance_adherence()
        assert "score" in result
        assert isinstance(result["score"], int)


class TestGetCompiledFingerprintNoRoot:
    def test_returns_empty_when_find_workspace_root_returns_none(self) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        with patch("sdd_core.utils.environment.find_workspace_root", return_value=None):
            result = GovernanceAdherenceScorer._get_compiled_fingerprint()
        assert result == ""

    def test_returns_empty_when_artifact_raises(self, tmp_path: Path) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        artifact_dir = tmp_path / ".sdd" / "compiled"
        artifact_dir.mkdir(parents=True)
        # Write a binary file that can't be parsed as JSON
        (artifact_dir / "governance-core.json").write_bytes(b"\xff\xfe bad")

        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert result == ""


class TestComputeBehavioralBadTimestamp:
    def test_skips_events_with_invalid_timestamps(self) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        events: list[dict[str, Any]] = [
            {
                "timestamp": "not-a-datetime",
                "event": VIOLATION,
                "details": {"action": "block"},
            },
            {"timestamp": datetime.now().isoformat(), "event": GOVERNANCE_CHECKED},
        ]
        cutoff = datetime.now() - timedelta(hours=1)
        result = GovernanceAdherenceScorer._compute_behavioral(events, cutoff)
        # Bad timestamp is skipped; only GOVERNANCE_CHECKED counts
        assert result["allows"] == 1
        assert result["blocks"] == 0

    def test_handles_aware_timestamps(self) -> None:
        from datetime import timezone

        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        # Create an aware UTC timestamp
        now_utc = datetime.now(timezone.utc)
        events: list[dict[str, Any]] = [
            {"timestamp": now_utc.isoformat(), "event": GOVERNANCE_CHECKED},
        ]

        # Cutoff is local naive time
        cutoff = datetime.now() - timedelta(hours=1)
        result = GovernanceAdherenceScorer._compute_behavioral(events, cutoff)

        # Should successfully convert and count the aware event
        assert result["allows"] == 1
        assert result["window_events"] == 1


class TestComputeStructuralException:
    def test_returns_no_match_when_state_file_unreadable(self, tmp_path: Path) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        state = tmp_path / "state.json"
        state.write_bytes(b"\xff\xfe bad json")
        result = GovernanceAdherenceScorer._compute_structural(state, tmp_path)
        assert result["match"] is False
        assert "error" in result["detail"]


class TestComputeFreshnessException:
    def test_handles_invalid_last_check_format(self) -> None:
        from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

        state_data = {"last_check": "not-a-date", "profile": "client"}
        result = GovernanceAdherenceScorer._compute_freshness(
            state_data, datetime.now()
        )
        assert result["ratio"] == 0.0
        assert "error" in result["detail"]
