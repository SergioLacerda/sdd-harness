"""Compliance Mode Policy - Event persistence policies for governance events.

Determines which events should be persisted based on logging mode (passive/active/strict).
"""

# Logging mode constants
LOGGING_MODE_PASSIVE = "passive"
LOGGING_MODE_ACTIVE = "active"
LOGGING_MODE_STRICT = "strict"

_VALID_LOGGING_MODES = {LOGGING_MODE_PASSIVE, LOGGING_MODE_ACTIVE, LOGGING_MODE_STRICT}

# Events that bypass passive filter
_MANDATORY_EVENTS = {
    "violation",
    "workspace_init",
    "compile_complete",
    "governance_checked",
}


class ComplianceModePolicy:
    """Static class for compliance event mode policies."""

    LOGGING_MODE_PASSIVE = LOGGING_MODE_PASSIVE
    LOGGING_MODE_ACTIVE = LOGGING_MODE_ACTIVE
    LOGGING_MODE_STRICT = LOGGING_MODE_STRICT
    _VALID_LOGGING_MODES = _VALID_LOGGING_MODES
    _MANDATORY_EVENTS = _MANDATORY_EVENTS

    @staticmethod
    def resolve_logging_mode(profile: str = "") -> str:
        """Resolve logging mode from environment, profile, or default.

        Resolution order:
        1. SDD_LOGGING_MODE environment variable (if set and valid)
        2. Profile-specific default (client→passive, master→active)
        3. Global default (passive)

        Args:
            profile: SDD profile ('client', 'master', or empty)

        Returns:
            One of: 'passive', 'active', 'strict'
        """
        import os

        # Check environment override
        env_mode = os.environ.get("SDD_LOGGING_MODE", "").strip().lower()
        if env_mode in _VALID_LOGGING_MODES:
            return env_mode

        # Profile-specific defaults
        if profile == "client":
            return LOGGING_MODE_PASSIVE
        if profile == "master":
            return LOGGING_MODE_ACTIVE

        # Global default
        return LOGGING_MODE_PASSIVE

    @staticmethod
    def should_persist_event(event: str, logging_mode: str) -> bool:
        """Determine if event should be persisted based on logging mode.

        - passive: only mandatory events (violation, workspace_init, compile_complete, governance_checked)
        - active: all events
        - strict: all events (same as active, reserved for future stricter filtering)

        Args:
            event: Event name (e.g., 'ask_command', 'violation')
            logging_mode: One of 'passive', 'active', 'strict'

        Returns:
            True if event should be written to log, False otherwise
        """
        if logging_mode in {LOGGING_MODE_ACTIVE, LOGGING_MODE_STRICT}:
            return True

        # Passive mode: only mandatory events
        return event.lower() in _MANDATORY_EVENTS
