"""Canonical JSON envelope contracts for CLI commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CommandError:
    """Normalized CLI command error payload."""

    code: str
    message: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class CommandResult:
    """Canonical CLI command envelope."""

    status: str
    command: str
    ok: bool
    error: CommandError | None
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict, normalising a None error to an explicit null."""
        payload = asdict(self)
        if self.error is None:
            payload["error"] = None
        return payload


def build_ok_result(command: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return a successful CommandResult envelope as a plain dict."""
    return CommandResult(
        status="ok",
        command=command,
        ok=True,
        error=None,
        data=data,
    ).as_dict()


def build_error_result(
    command: str, data: dict[str, Any], *, code: str, message: str
) -> dict[str, Any]:
    """Return an error CommandResult envelope as a plain dict."""
    return CommandResult(
        status="error",
        command=command,
        ok=False,
        error=CommandError(code=code, message=message),
        data=data,
    ).as_dict()
