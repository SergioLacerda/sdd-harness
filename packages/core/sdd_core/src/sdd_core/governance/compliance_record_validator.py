"""Compliance Record Validator - Event schema validation and sensitive data redaction.

Validates JSONL event records conform to Phase B schema and redacts sensitive fields.
"""

from typing import Any

# Required fields in each compliance event record (Phase B schema)
_REQUIRED_RECORD_FIELDS = {
    "timestamp",
    "event",
    "command",
    "profile",
    "state",
    "details",
    "level",
    "service",
    "message",
    "status",
}

# Fields to redact when storing sensitive details
_SENSITIVE_DETAIL_KEYS = {
    "query",
    "token",
    "api_key",
    "password",
    "secret",
    "credential",
    "auth",
    "signature",
    "private_key",
}

_REDACTED_PLACEHOLDER = "[REDACTED]"


class ComplianceRecordValidator:
    """Static class for compliance record validation and redaction."""

    _REQUIRED_RECORD_FIELDS = _REQUIRED_RECORD_FIELDS
    _SENSITIVE_DETAIL_KEYS = _SENSITIVE_DETAIL_KEYS
    _REDACTED_PLACEHOLDER = _REDACTED_PLACEHOLDER

    @staticmethod
    def validate_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate compliance record against Phase B schema.

        Args:
            record: Compliance event record dict

        Returns:
            Tuple of (is_valid: bool, missing_fields: list[str])
        """
        if not isinstance(record, dict):
            return False, list(_REQUIRED_RECORD_FIELDS)

        missing = [f for f in _REQUIRED_RECORD_FIELDS if f not in record]
        return len(missing) == 0, missing

    @staticmethod
    def redact_sensitive(details: dict[str, Any] | None) -> dict[str, Any] | None:
        """Redact sensitive fields from details dict.

        Creates a shallow copy and replaces sensitive keys with [REDACTED].
        Non-sensitive keys and structure are preserved.

        Args:
            details: Event details dict (may be None)

        Returns:
            Copy of details with sensitive values replaced, or None if input is None
        """
        if details is None:
            return None

        if not isinstance(details, dict):
            return details

        redacted = details.copy()
        for key in _SENSITIVE_DETAIL_KEYS:
            if key in redacted:
                redacted[key] = _REDACTED_PLACEHOLDER

        return redacted
