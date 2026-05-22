"""Compliance event logger — append-only JSONL audit trail (backward-compatible shim).

Events are written to .sdd/runtime/compliance-events.jsonl.
Each line is a self-contained JSON object (newline-delimited JSON).
The file is NEVER truncated or rewritten — only appended.

This module is now a shim that delegates to:
- ComplianceModePolicy (mode resolution and event filtering)
- ComplianceRecordValidator (schema validation and redaction)
- ComplianceLogStore (I/O operations)
- GovernanceAdherenceScorer (adherence computation)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Re-export constants
from sdd_core.governance.compliance_constants import (
    ASK_COMMAND,
    ASK_FULL_COMMAND,
    COMMAND_INVOKED,
    COMPILE_COMPLETE,
    GOVERNANCE_CHECKED,
    VIOLATION,
    WORKSPACE_INIT,
)

# Re-export log store
from sdd_core.governance.compliance_log_store import (
    DEFAULT_MAX_BACKUPS,
    DEFAULT_MAX_LOG_BYTES,
    ComplianceLogStore,
)

# Re-export mode policy
from sdd_core.governance.compliance_mode_policy import (
    _MANDATORY_EVENTS,
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_STRICT,
    ComplianceModePolicy,
)

# Re-export record validator
from sdd_core.governance.compliance_record_validator import (
    _REDACTED_PLACEHOLDER,
    _REQUIRED_RECORD_FIELDS,
    ComplianceRecordValidator,
)

# Publicly exported for backward compatibility
__all__ = [
    "ASK_COMMAND",
    "ASK_FULL_COMMAND",
    "COMMAND_INVOKED",
    "COMPILE_COMPLETE",
    "GOVERNANCE_CHECKED",
    "VIOLATION",
    "WORKSPACE_INIT",
    "append_event",
    "read_events",
    "log_ask_event",
    "compute_governance_adherence",
    "validate_compliance_record",
    "resolve_logging_mode",
    "rotate_compliance_log",
    "LOGGING_MODE_PASSIVE",
    "LOGGING_MODE_ACTIVE",
    "LOGGING_MODE_STRICT",
    "_REDACTED_PLACEHOLDER",
    "_REQUIRED_RECORD_FIELDS",
    "_MANDATORY_EVENTS",
    "_redact_sensitive",
    "DEFAULT_MAX_LOG_BYTES",
]


# ==============================================================================
# Backward-compatibility shim functions
# ==============================================================================


def resolve_logging_mode(profile: str = "") -> str:
    """Resolve logging mode from environment, profile, or default.

    **Shim for backward compatibility.** Delegates to ComplianceModePolicy.
    """
    return ComplianceModePolicy.resolve_logging_mode(profile)


def _should_persist_event(event: str, logging_mode: str) -> bool:
    """Determine if event should be persisted based on logging mode.

    **Shim for backward compatibility.** Delegates to ComplianceModePolicy.
    """
    return ComplianceModePolicy.should_persist_event(event, logging_mode)


def _resolve_env() -> str:
    """Detect environment: CI, dev, or prod.

    **Shim for backward compatibility.** Delegates to ComplianceLogStore.
    """
    return ComplianceLogStore._resolve_env()


def validate_compliance_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate compliance record against Phase B schema.

    **Shim for backward compatibility.** Delegates to ComplianceRecordValidator.
    """
    return ComplianceRecordValidator.validate_record(record)


def _redact_sensitive(details: dict[str, Any] | None) -> dict[str, Any] | None:
    """Redact sensitive fields from details dict.

    **Shim for backward compatibility.** Delegates to ComplianceRecordValidator.
    """
    return ComplianceRecordValidator.redact_sensitive(details)


def rotate_compliance_log(
    log_path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    max_backups: int = DEFAULT_MAX_BACKUPS,
) -> bool:
    """Rotate compliance log file if it exceeds max size.

    **Shim for backward compatibility.** Delegates to ComplianceLogStore.
    """
    return ComplianceLogStore.rotate(
        log_path, max_bytes=max_bytes, max_backups=max_backups
    )


def append_event(
    event: str,
    *,
    command: str,
    profile: str,
    state: str | None = None,
    details: dict[str, Any] | None = None,
    workspace_root: Path | None = None,
    log_path: Path | None = None,
    level: str = "info",
    service: str = "sdd",
    message: str = "",
    status: str = "ok",
) -> None:
    """Append event to compliance log (JSONL format).

    **Shim for backward compatibility.** Delegates to ComplianceLogStore.
    """
    return ComplianceLogStore.append(
        event,
        command=command,
        profile=profile,
        state=state or "UNKNOWN",
        details=details or {},
        workspace_root=workspace_root,
        log_path=log_path,
        level=level,
        service=service,
        message=message,
        status=status,
    )


def read_events(
    n: int = 50, *, workspace_root: Path | None = None, log_path: Path | None = None
) -> list[dict[str, Any]]:
    """Read last N events from compliance log (JSONL format).

    **Shim for backward compatibility.** Delegates to ComplianceLogStore.
    """
    return ComplianceLogStore.read(n, workspace_root=workspace_root, log_path=log_path)


def log_ask_event(
    *,
    event: str,
    command: str,
    profile: str,
    state: str,
    agent_id: str,
    details: dict[str, Any],
    workspace_root: Path | None = None,
    log_path: Path | None = None,
) -> None:
    """Log an ASK-specific event (ask or ask-full command).

    **Shim for backward compatibility.** Delegates to ComplianceLogStore.
    """
    return ComplianceLogStore.log_ask(
        event=event,
        command=command,
        profile=profile,
        state=state,
        agent_id=agent_id,
        details=details,
        workspace_root=workspace_root,
        log_path=log_path,
    )


def compute_governance_adherence(
    *,
    workspace_root: Path | None = None,
    log_path: Path | None = None,
    state_path: Path | None = None,
    window_hours: int = 24,
) -> dict[str, Any]:
    """Compute governance adherence score (backward-compatibility shim).

    **Shim for backward compatibility.** Delegates to GovernanceAdherenceScorer.
    """
    from sdd_core.governance.adherence_scorer import GovernanceAdherenceScorer

    return GovernanceAdherenceScorer.compute(
        workspace_root=workspace_root,
        log_path=log_path,
        state_path=state_path,
        window_hours=window_hours,
    )
