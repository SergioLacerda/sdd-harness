"""Budget enforcement — retry and reflection ceilings per PATH.

Implements the hard retry/reflection limits defined in
§economy/efficiency-policy.md.  Callers increment the budget tracker;
once the ceiling is reached the next increment raises an error.

When an ``emit_event`` callback is provided, the budget tracker automatically
emits ``economy.retry.cap.reached`` before raising the exception.

Usage example::

    from sdd_runtime.budget import RetryBudget, RetryCapReachedError

    budget = RetryBudget(path_id="A")
    try:
        budget.increment_retry()
    except RetryCapReachedError as exc:
        # If emit_event was wired, event already emitted automatically
        raise typer.Exit(3) from exc

With event emission::

    def on_event(evt):
        sink.emit(evt)

    budget = RetryBudget(path_id="A", emit_event=on_event)
    try:
        budget.increment_retry()  # auto-emits on ceiling breach
    except RetryCapReachedError:
        pass
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sdd_runtime.exceptions import (
    ReflectionCapReachedError as ReflectionCapReachedError,
)
from sdd_runtime.exceptions import (
    RetryCapReachedError as RetryCapReachedError,
)
from sdd_runtime.exceptions import (
    TokenBudgetBreachError as TokenBudgetBreachError,
)

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

# ---------------------------------------------------------------------------
# RetryBudget — stateful tracker for a single task execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenConsumption:
    """Record of a single LLM token transaction."""

    input_tokens: int
    output_tokens: int
    model: str
    category: str  # 'reasoning' | 'tool_call' | 'reflection' | 'other'
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cost_usd: float = 0.0


class TokenBudget:
    """
    Hybrid budget tracker for tokens and USD costs.

    Pricing is based on per-model registry.
    """

    # Default pricing: (input_price_per_1k, output_price_per_1k)
    PRICING_REGISTRY = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "claude-3-5-sonnet": (0.003, 0.015),
        "claude-3-7-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
        "gemini-2.0-flash": (0.0001, 0.0004),
        "gemini-2.0-pro": (0.00125, 0.005),
        "default": (0.01, 0.03),  # Conservative default
    }

    def __init__(
        self,
        max_tokens: int = 100000,
        max_cost_usd: float | None = None,
        emit_event: Callable[[Any], None] | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.emit_event = emit_event

        self.consumed_tokens = 0
        self.consumed_cost_usd = 0.0
        self.ledger: list[TokenConsumption] = []

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate USD cost for a given model and token count."""
        prices = self.PRICING_REGISTRY.get(model, self.PRICING_REGISTRY["default"])
        input_cost = (input_tokens / 1000.0) * prices[0]
        output_cost = (output_tokens / 1000.0) * prices[1]
        return input_cost + output_cost

    def consume(
        self, model: str, input_tokens: int, output_tokens: int, category: str = "other"
    ) -> TokenConsumption:
        """Record consumption and check against limits.

        Circuit breaker tiers:
        - 90%: WARN event, continues with degraded mode
        - 100%: HARD block via BudgetBreachError
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        consumption = TokenConsumption(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            category=category,
            cost_usd=cost,
        )

        # Check limits before committing
        total_tokens = self.consumed_tokens + input_tokens + output_tokens
        total_cost = self.consumed_cost_usd + cost

        # WARN_THRESHOLD = 90% — degrade gracefully
        warn_threshold_tokens = self.max_tokens * 0.9
        if total_tokens > warn_threshold_tokens and total_tokens <= self.max_tokens:
            self._emit_warning("tokens", total_tokens, self.max_tokens)

        warn_threshold_cost = (
            self.max_cost_usd * 0.9 if self.max_cost_usd else float("inf")
        )
        if (
            self.max_cost_usd
            and total_cost > warn_threshold_cost
            and total_cost <= self.max_cost_usd
        ):
            self._emit_warning("usd", total_cost, self.max_cost_usd)

        # HARD_LIMIT = 100% — block immediately
        if total_tokens > self.max_tokens:
            self._emit_breach("tokens", total_tokens, self.max_tokens)
            raise TokenBudgetBreachError(total_tokens, self.max_tokens, "tokens")

        if self.max_cost_usd and total_cost > self.max_cost_usd:
            self._emit_breach("usd", total_cost, self.max_cost_usd)
            raise TokenBudgetBreachError(total_cost, self.max_cost_usd, "usd")

        # Commit
        self.ledger.append(consumption)
        self.consumed_tokens = total_tokens
        self.consumed_cost_usd = total_cost

        # Phase 0 fix: Emit economy.token.consume event for audit trail
        self._emit_consumption(consumption, total_tokens, total_cost)

        return consumption

    def _emit_consumption(
        self, consumption: TokenConsumption, total_tokens: int, total_cost_usd: float
    ) -> None:
        """Emit economy.token.consume event for audit trail (Phase 0 fix)."""
        if self.emit_event:
            import uuid

            from sdd_runtime.telemetry import RuntimeEvent

            self.emit_event(
                RuntimeEvent(
                    event="economy.token.consume",
                    command="budget.consume",
                    status="ok",
                    trace_id=str(uuid.uuid4()),
                    tokens_input=consumption.input_tokens,
                    tokens_output=consumption.output_tokens,
                    tokens_total=consumption.input_tokens + consumption.output_tokens,
                    budget_utilization_pct=round(
                        (total_tokens / self.max_tokens) * 100, 2
                    )
                    if self.max_tokens > 0
                    else 0.0,
                    details={
                        "model": consumption.model,
                        "category": consumption.category,
                        "cost_usd": round(consumption.cost_usd, 4),
                        "total_cost_usd": round(total_cost_usd, 4),
                        "max_tokens": self.max_tokens,
                        "max_cost_usd": self.max_cost_usd,
                    },
                )
            )

    def _emit_warning(self, unit: str, consumed: float, limit: float) -> None:
        """Emit WARN event when budget utilization exceeds 90%."""
        if self.emit_event:
            import uuid

            from sdd_runtime.telemetry import RuntimeEvent

            self.emit_event(
                RuntimeEvent(
                    event=f"economy.budget.warn.{unit}",
                    command="budget.consume",
                    status="warn",
                    trace_id=str(uuid.uuid4()),
                    details={
                        "consumed": consumed,
                        "limit": limit,
                        "utilization_pct": round((consumed / limit) * 100, 2),
                    },
                )
            )

    def _emit_breach(self, unit: str, consumed: float, limit: float) -> None:
        if self.emit_event:
            import uuid

            from sdd_runtime.telemetry import RuntimeEvent

            self.emit_event(
                RuntimeEvent(
                    event=f"economy.budget.breach.{unit}",
                    command="budget.consume",
                    status="error",
                    trace_id=str(uuid.uuid4()),
                    details={"consumed": consumed, "limit": limit},
                )
            )

    def get_status(self) -> dict[str, Any]:
        """Return current budget status for telemetry or CLI."""
        return {
            "consumed_tokens": self.consumed_tokens,
            "max_tokens": self.max_tokens,
            "consumed_cost_usd": round(self.consumed_cost_usd, 4),
            "max_cost_usd": self.max_cost_usd,
            "usage_percent": round(
                (self.consumed_tokens / self.max_tokens) * 100
                if self.max_tokens > 0
                else 0,
                2,
            ),
            "transaction_count": len(self.ledger),
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
