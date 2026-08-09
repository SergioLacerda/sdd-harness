"""RetryBudget — retry/reflection ceilings per PATH for a single task."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sdd_runtime.exceptions import (
    ReflectionCapReachedError,
    RetryCapReachedError,
)

from ._token_budget import TokenBudget

# ---------------------------------------------------------------------------
# PATH ceilings (§economy/efficiency-policy.md)
# ---------------------------------------------------------------------------

_PATH_RETRY_CEILING: dict[str, int] = {
    "A": 2,
    "B": 3,
    "C": 3,
    "D": 2,
}

_PATH_REFLECTION_CEILING: dict[str, int] = {
    "A": 1,
    "B": 2,
    "C": 2,
    "D": 1,
}


@dataclass
class RetryBudget:
    """Tracks retry and reflection counts for a single task execution.

    Also optionally holds a :class:`TokenBudget` for economic enforcement.
    """

    path_id: str = ""
    emit_event: Callable[[Any], None] | None = field(
        default=None, compare=False, repr=False
    )
    token_budget: TokenBudget | None = None
    retry_count: int = field(default=0, init=False)
    reflection_count: int = field(default=0, init=False)

    @property
    def retry_ceiling(self) -> int:
        """The retry ceiling for the active PATH."""
        return _PATH_RETRY_CEILING.get(self.path_id, _PATH_RETRY_CEILING["A"])

    @property
    def reflection_ceiling(self) -> int:
        """The reflection ceiling for the active PATH."""
        return _PATH_REFLECTION_CEILING.get(self.path_id, _PATH_REFLECTION_CEILING["A"])

    def increment_retry(self) -> int:
        """Increment retry count and return the new value."""
        next_count = self.retry_count + 1
        if next_count > self.retry_ceiling:
            # Auto-emit telemetry event if callback is wired
            if self.emit_event is not None:
                import uuid

                from sdd_runtime.telemetry import (
                    ECONOMY_RETRY_CAP_REACHED,
                    RuntimeEvent,
                )

                event = RuntimeEvent(
                    event=ECONOMY_RETRY_CAP_REACHED,
                    command="retry.increment",
                    status="warn",
                    trace_id=str(uuid.uuid4()),
                    path_id=self.path_id,
                    retry_count=self.retry_count,
                    details={
                        "ceiling": self.retry_ceiling,
                        "would_be_count": next_count,
                    },
                )
                self.emit_event(event)
            raise RetryCapReachedError(
                retry_count=next_count,
                ceiling=self.retry_ceiling,
                path_id=self.path_id,
            )
        self.retry_count = next_count
        return self.retry_count

    def increment_reflection(self) -> int:
        """Increment reflection count and return the new value."""
        next_count = self.reflection_count + 1
        if next_count > self.reflection_ceiling:
            raise ReflectionCapReachedError(
                reflection_count=next_count,
                ceiling=self.reflection_ceiling,
                path_id=self.path_id,
            )
        self.reflection_count = next_count
        return self.reflection_count

    def at_retry_ceiling(self) -> bool:
        """Return True when the next retry would breach the ceiling."""
        return self.retry_count >= self.retry_ceiling

    def at_reflection_ceiling(self) -> bool:
        """Return True when the next reflection would breach the ceiling."""
        return self.reflection_count >= self.reflection_ceiling
