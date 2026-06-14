"""Telemetry constants — logging modes, economy event types, and budget tables."""

from __future__ import annotations

__all__ = [
    "_MANDATORY_EVENTS",
    "_PATH_BUDGET_BYTES",
    "_ZONE_BREACH_PCT",
    "_ZONE_RED_PCT",
    "MODE_PASSIVE",
    "MODE_ACTIVE",
    "MODE_STRICT",
    "ECONOMY_BUDGET_WARN",
    "ECONOMY_COMPRESSION_SKIP",
    "ECONOMY_RETRY_CAP_REACHED",
]

# ---- Logging modes (SOFT governance parameter §13.5) ------------------------
MODE_PASSIVE = "passive"
MODE_ACTIVE = "active"
MODE_STRICT = "strict"

# ---- Economy event types (§economy/metrics.md) ------------------------------
ECONOMY_BUDGET_WARN = "economy.budget.warn"
ECONOMY_BUDGET_BREACH = "economy.budget.breach"
ECONOMY_COMPRESSION_SKIP = "economy.compression.skip"
ECONOMY_RETRY_CAP_REACHED = "economy.retry.cap.reached"

# ---- Budget zone thresholds (§economy/execution-budget.md) ------------------
_ZONE_RED_PCT: float = 90.0  # > this → RED (emit warn; MUST compress)
_ZONE_BREACH_PCT: float = 100.0  # >= this → BREACH (emit breach; block loading)

# ---- PATH context budget ceilings (§economy/execution-budget.md) ------------
# A=40 KB, B=45 KB, C=85 KB, D=35 KB/thread
_PATH_BUDGET_BYTES: dict[str, int] = {
    "A": 40 * 1024,
    "B": 45 * 1024,
    "C": 85 * 1024,
    "D": 35 * 1024,
}

# ---- Mandatory minimum events (always emitted regardless of logging_mode) ---
_MANDATORY_EVENTS = frozenset(
    {
        "governance.violation",
        "runtime.drift.detected",
        "policy.validation.fail",
        "runtime.session.start",
        "governance.ask",
        "governance.ask.full",
        ECONOMY_BUDGET_BREACH,
    }
)
