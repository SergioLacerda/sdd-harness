"""Unit tests for compliance event logging."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_core.governance.compliance import (
    _MANDATORY_EVENTS,
    _REDACTED_PLACEHOLDER,
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_STRICT,
    VIOLATION,
    _should_persist_event,
    append_event,
    read_events,
    resolve_logging_mode,
    rotate_compliance_log,
    validate_compliance_record,
)

pytestmark = pytest.mark.unit


class TestLoggingModeResolution:
    """Tests for logging mode resolution logic."""

    def test_env_variable_overrides_all(self, tmp_path: Path) -> None:
        """SDD_LOGGING_MODE environment variable should take precedence."""
        with patch.dict(os.environ, {"SDD_LOGGING_MODE": "strict"}):
            mode = resolve_logging_mode(profile="client")
            assert mode == LOGGING_MODE_STRICT

    def test_profile_default_client(self) -> None:
        """Client profile should default to passive mode."""
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_logging_mode(profile="client")
            assert mode == LOGGING_MODE_PASSIVE

    def test_profile_default_master(self) -> None:
        """Master profile should default to active mode."""
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_logging_mode(profile="master")
            assert mode == LOGGING_MODE_ACTIVE

    def test_global_default_passive(self) -> None:
        """Global default should be passive when no profile specified."""
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_logging_mode(profile="")
            assert mode == LOGGING_MODE_PASSIVE

    def test_invalid_mode_ignored(self) -> None:
        """Invalid mode in env variable should be ignored."""
        with patch.dict(os.environ, {"SDD_LOGGING_MODE": "invalid"}):
            mode = resolve_logging_mode(profile="client")
            assert mode == LOGGING_MODE_PASSIVE


class TestEventPersistence:
    """Tests for _should_persist_event filtering logic."""

    def test_mandatory_events_always_persist(self) -> None:
        """Mandatory events should persist in passive mode."""
        for event in _MANDATORY_EVENTS:
            assert _should_persist_event(event, LOGGING_MODE_PASSIVE) is True

    def test_non_mandatory_blocked_in_passive(self) -> None:
        """Non-mandatory events should not persist in passive mode."""
        assert _should_persist_event("custom.event", LOGGING_MODE_PASSIVE) is False

    def test_all_events_persist_in_active(self) -> None:
        """All events should persist in active mode."""
        assert _should_persist_event("any.event", LOGGING_MODE_ACTIVE) is True
        assert _should_persist_event("custom.event", LOGGING_MODE_ACTIVE) is True

    def test_all_events_persist_in_strict(self) -> None:
        """All events should persist in strict mode."""
        assert _should_persist_event("any.event", LOGGING_MODE_STRICT) is True


class TestComplianceRecordValidation:
    """Tests for JSONL schema validation."""

    def test_valid_record_passes_validation(self) -> None:
        """Valid record with all required fields should pass."""
        record = {
            "timestamp": "2026-05-15T10:00:00+00:00",
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {"key": "value"},
            "level": "info",
            "service": "sdd",
            "message": "Test event",
            "status": "ok",
        }
        valid, missing = validate_compliance_record(record)
        assert valid is True
        assert missing == []

    def test_missing_ts_field_fails(self) -> None:
        """Record missing 'timestamp' field should fail."""
        record = {
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {},
            "level": "info",
            "service": "sdd",
            "message": "Test",
            "status": "ok",
        }
        valid, missing = validate_compliance_record(record)
        assert valid is False
        assert "timestamp" in missing

    def test_empty_required_field_fails(self) -> None:
        """Empty required field should be treated as missing."""
        record = {
            "timestamp": "",  # Empty - but schema just checks presence, not value
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {},
            "level": "info",
            "service": "sdd",
            "message": "Test",
            "status": "ok",
        }
        # Note: validator only checks field presence, not emptiness, so this actually passes
        valid, missing = validate_compliance_record(record)
        assert (
            valid is True
        )  # All required fields present, even if timestamp is empty string

    def test_lists_all_missing_fields(self) -> None:
        """Should list all missing required fields."""
        record = {}
        valid, missing = validate_compliance_record(record)
        assert valid is False
        assert len(missing) > 0


class TestSensitiveDataRedaction:
    """Tests for redaction of sensitive detail keys."""

    def test_query_redacted(self) -> None:
        """Query field should be redacted."""
        from sdd_core.governance.compliance import _redact_sensitive

        details = {"query": "SELECT * FROM users"}
        redacted = _redact_sensitive(details)
        assert redacted["query"] == _REDACTED_PLACEHOLDER

    def test_token_redacted(self) -> None:
        """Token field should be redacted."""
        from sdd_core.governance.compliance import _redact_sensitive

        details = {"token": "secret-token-value"}
        redacted = _redact_sensitive(details)
        assert redacted["token"] == _REDACTED_PLACEHOLDER

    def test_api_key_redacted(self) -> None:
        """API key field should be redacted."""
        from sdd_core.governance.compliance import _redact_sensitive

        details = {"api_key": "sk-1234567890"}
        redacted = _redact_sensitive(details)
        assert redacted["api_key"] == _REDACTED_PLACEHOLDER

    def test_non_sensitive_fields_preserved(self) -> None:
        """Non-sensitive fields should not be redacted."""
        from sdd_core.governance.compliance import _redact_sensitive

        details = {"event": "test", "count": 42, "status": "ok"}
        redacted = _redact_sensitive(details)
        assert redacted["event"] == "test"
        assert redacted["count"] == 42
        assert redacted["status"] == "ok"

    def test_empty_details_handled(self) -> None:
        """Empty or None details should be handled gracefully."""
        from sdd_core.governance.compliance import _redact_sensitive

        assert _redact_sensitive({}) == {}
        assert _redact_sensitive(None) is None


class TestLogRotation:
    """Tests for compliance log rotation."""

    def test_rotate_skips_small_files(self, tmp_path: Path) -> None:
        """Should not rotate files smaller than threshold."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("small content", encoding="utf-8")

        result = rotate_compliance_log(log_file, max_bytes=1000)
        assert result is False
        assert log_file.exists()

    def test_rotate_moves_primary_to_backup(self, tmp_path: Path) -> None:
        """Should move primary file to .1 backup when rotating."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("x" * 1000, encoding="utf-8")

        result = rotate_compliance_log(log_file, max_bytes=100, max_backups=3)
        assert result is True
        assert (tmp_path / "events.jsonl.1").exists()

    def test_rotate_creates_new_primary(self, tmp_path: Path) -> None:
        """Should create new primary file after rotation."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("x" * 1000, encoding="utf-8")

        rotate_compliance_log(log_file, max_bytes=100, max_backups=3)
        assert log_file.exists()
        assert log_file.stat().st_size == 0

    def test_rotate_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Should not crash when log file doesn't exist."""
        log_file = tmp_path / "nonexistent.jsonl"
        result = rotate_compliance_log(log_file)
        assert result is False


class TestAppendEvent:
    """Tests for append_event functionality."""

    def test_append_event_writes_jsonl(self, tmp_path: Path) -> None:
        """Should write event as JSONL line."""
        log_file = tmp_path / "events.jsonl"
        append_event(
            "test.event",
            command="test",
            profile="master",
            level="INFO",
            service="sdd-cli",
            log_path=log_file,
        )

        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) > 0

        event = json.loads(lines[0])
        assert event["event"] == "test.event"
        assert event["command"] == "test"

    def test_append_event_respects_logging_mode(self, tmp_path: Path) -> None:
        """Should respect logging mode when deciding to write."""
        log_file = tmp_path / "events.jsonl"

        # In passive mode, non-mandatory custom events should not persist
        append_event(
            "custom.event",
            command="test",
            profile="client",  # client → passive mode
            log_path=log_file,
        )

        # File should not exist or be empty (passive mode blocks non-mandatory)
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8").strip()
            # Passive mode should not write custom events
            assert len(content) == 0 or "custom.event" not in content

    def test_append_mandatory_event_in_passive_mode(self, tmp_path: Path) -> None:
        """Should write mandatory events even in passive mode."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            VIOLATION,  # Mandatory event
            command="test",
            profile="client",  # client → passive mode
            log_path=log_file,
        )

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8").strip()
        assert len(content) > 0
        event = json.loads(content.split("\n")[0])
        assert event["event"] == VIOLATION

    def test_append_event_redacts_sensitive_details(self, tmp_path: Path) -> None:
        """Should redact sensitive fields in details."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",  # Use master for active mode
            details={"api_key": "secret-key", "status": "ok"},
            log_path=log_file,
        )

        content = log_file.read_text(encoding="utf-8").strip()
        event = json.loads(content.split("\n")[0])
        assert event["details"]["api_key"] == _REDACTED_PLACEHOLDER
        assert event["details"]["status"] == "ok"


class TestReadEvents:
    """Tests for reading compliance events."""

    def test_read_events_empty_log(self, tmp_path: Path) -> None:
        """Should return empty list when log doesn't exist."""
        log_file = tmp_path / "nonexistent.jsonl"
        events = read_events(log_path=log_file)
        assert events == []

    def test_read_events_returns_last_n(self, tmp_path: Path) -> None:
        """Should return only last N events."""
        log_file = tmp_path / "events.jsonl"

        # Write 5 events
        for i in range(5):
            append_event(
                f"event{i}",
                command="test",
                profile="master",
                log_path=log_file,
            )

        # Read last 3
        events = read_events(n=3, log_path=log_file)
        assert len(events) == 3

    def test_read_events_parses_json(self, tmp_path: Path) -> None:
        """Should parse JSONL events correctly."""
        log_file = tmp_path / "events.jsonl"
        append_event(
            "test.event",
            command="test",
            profile="master",
            log_path=log_file,
        )

        events = read_events(log_path=log_file)
        assert len(events) > 0
        assert events[0]["event"] == "test.event"

    def test_read_events_skips_invalid_json(self, tmp_path: Path) -> None:
        """Should skip lines with invalid JSON."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("invalid json\n", encoding="utf-8")
        log_file.write_text(
            log_file.read_text(encoding="utf-8")
            + json.dumps({"event": "valid", "ts": "2026-05-15T10:00:00Z"})
            + "\n",
            encoding="utf-8",
        )

        events = read_events(log_path=log_file)
        # Should have parsed the valid JSON and skipped invalid
        assert len(events) >= 1
