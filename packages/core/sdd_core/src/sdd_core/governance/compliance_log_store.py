"""Compliance Log Store - Event persistence, rotation, and ASK-specific logging.

Handles reading/writing compliance events to JSONL log files with rotation.
"""

import json
import os
from pathlib import Path
from typing import Any

from sdd_core.governance.compliance_constants import default_log_path
from sdd_core.governance.compliance_mode_policy import ComplianceModePolicy
from sdd_core.governance.compliance_record_validator import ComplianceRecordValidator

# Log rotation defaults
DEFAULT_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MiB
DEFAULT_MAX_BACKUPS = 3


class ComplianceLogStore:
    """Static class for compliance event log storage operations."""

    DEFAULT_MAX_LOG_BYTES = DEFAULT_MAX_LOG_BYTES
    DEFAULT_MAX_BACKUPS = DEFAULT_MAX_BACKUPS

    @staticmethod
    def _resolve_env() -> str:
        """Detect environment: CI, dev, or prod.

        Returns:
            One of: 'ci', 'dev', 'prod'
        """
        if os.environ.get("CI") in {"1", "true", "True"}:
            return "ci"

        env = os.environ.get("SDD_ENV", "").strip().lower()
        if env:
            return env

        return "dev"

    @staticmethod
    def rotate(
        log_path: Path,
        *,
        max_bytes: int = DEFAULT_MAX_LOG_BYTES,
        max_backups: int = DEFAULT_MAX_BACKUPS,
    ) -> bool:
        """Rotate compliance log file if it exceeds max size.

        Backs up to .N suffix and keeps max_backups versions.

        Args:
            log_path: Path to compliance log file
            max_bytes: Max size before rotation (default 10 MiB)
            max_backups: Max backup files to keep (default 3)

        Returns:
            True if rotation occurred, False if no rotation was needed or on error
        """
        if not log_path.exists():
            return False

        if log_path.stat().st_size < max_bytes:
            return False

        try:
            # Shift existing backups: .3 -> .4, .2 -> .3, .1 -> .2
            for i in range(max_backups - 1, 0, -1):
                old = log_path.with_name(f"{log_path.name}.{i}")
                new = log_path.with_name(f"{log_path.name}.{i + 1}")
                if old.exists():
                    old.rename(new)

            # Move current log to .1
            backup_1 = log_path.with_name(f"{log_path.name}.1")
            log_path.rename(backup_1)

            # Create new empty primary file
            log_path.touch()

            return True
        except Exception:
            return False

    @staticmethod
    def append(
        event: str,
        *,
        command: str,
        profile: str,
        state: str,
        details: dict[str, Any],
        agent_id: str = "",
        workspace_root: Path | None = None,
        log_path: Path | None = None,
        level: str = "info",
        service: str = "sdd",
        message: str = "",
        status: str = "ok",
    ) -> None:
        """Append event to compliance log (JSONL format).

        Respects logging mode (passive/active/strict) and redacts sensitive fields.

        Args:
            event: Event name (e.g., 'ask_command', 'violation')
            command: Command that triggered event
            profile: SDD profile ('client' or 'master')
            state: Handshake state at time of event
            details: Event-specific details dict
            agent_id: Agent/CLI identity. Falls back to SDD_AGENT_ID env var.
            workspace_root: Root directory for log path resolution
            log_path: Explicit log file path (overrides default)
            level: Log level ('info', 'warn', 'error')
            service: Service name (default 'sdd')
            message: Human-readable message
            status: Event status ('ok', 'warn', 'error')
        """
        from datetime import datetime, timezone

        # Resolve paths
        if workspace_root is None:
            from sdd_core.utils.environment import find_workspace_root

            workspace_root = find_workspace_root() or Path.cwd()

        if log_path is None:
            log_path = default_log_path(workspace_root)

        if log_path is None:
            return

        # Determine logging mode
        logging_mode = ComplianceModePolicy.resolve_logging_mode(profile)

        # Check if event should be persisted
        if not ComplianceModePolicy.should_persist_event(event, logging_mode):
            return

        # Resolve agent identity: param > env var > empty (unknown)
        resolved_agent_id = agent_id or os.environ.get("SDD_AGENT_ID", "")

        # Build record
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "command": command,
            "profile": profile,
            "state": state,
            "agent_id": resolved_agent_id,
            "details": ComplianceRecordValidator.redact_sensitive(details),
            "level": level,
            "service": service,
            "message": message,
            "status": status,
        }

        # Validate record
        valid, missing = ComplianceRecordValidator.validate_record(record)
        if not valid:
            import logging

            logging.warning(f"Invalid compliance record, missing fields: {missing}")
            return

        # Rotate if needed
        ComplianceLogStore.rotate(
            log_path, max_bytes=DEFAULT_MAX_LOG_BYTES, max_backups=DEFAULT_MAX_BACKUPS
        )

        # Write to log
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            import logging

            logging.error(f"Failed to write compliance event: {e}")

    @staticmethod
    def read(
        n: int = 50, *, workspace_root: Path | None = None, log_path: Path | None = None
    ) -> list[dict[str, Any]]:
        """Read last N events from compliance log (JSONL format).

        Tolerates JSON parse errors by skipping malformed lines.

        Args:
            n: Number of events to read (default 50, use 0 for all)
            workspace_root: Root directory for log path resolution
            log_path: Explicit log file path (overrides default)

        Returns:
            List of event dicts (up to N entries)
        """
        # Resolve path
        if workspace_root is None:
            from sdd_core.utils.environment import find_workspace_root

            workspace_root = find_workspace_root() or Path.cwd()

        if log_path is None:
            log_path = default_log_path(workspace_root)

        if log_path is None or not log_path.exists():
            return []

        events = []
        try:
            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue

            # Return last N
            if n > 0:
                return events[-n:]
            return events
        except Exception:
            return []

    @staticmethod
    def log_ask(
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

        Wraps append() with ASK-specific context.

        Args:
            event: Event type (ASK_COMMAND or ASK_FULL_COMMAND)
            command: 'ask' or 'ask-full'
            profile: SDD profile
            state: Handshake state
            agent_id: Agent ID executing the ask
            details: Event details (will have agent_id added)
            workspace_root: Root directory for log resolution
            log_path: Explicit log file path
        """
        ComplianceLogStore.append(
            event,
            command=command,
            profile=profile,
            state=state,
            agent_id=agent_id,
            details=details,
            workspace_root=workspace_root,
            log_path=log_path,
            level="info",
            service="sdd",
            message=f"Agent {agent_id} executed {command}",
            status="ok",
        )
