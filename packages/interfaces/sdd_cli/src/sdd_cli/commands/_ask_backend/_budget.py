"""Budget circuit breaker guards for the ``sdd ask`` command pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import typer

from sdd_cli.commands._ask_backend._helpers import _get_cached_ahp, _signature_mode
from sdd_cli.commands._ask_backend._helpers_signals import _json_mode
from sdd_cli.shared.constants import BREACH_EXIT_CODE as _BREACH_EXIT_CODE

logger = logging.getLogger(__name__)


def _guard_budget_breach() -> None:
    """Block context loading if the session budget is in BREACH state.

    Reads ``SDD_BUDGET_UTILIZATION_PCT`` from the environment (set by the
    agent after each context load).  When utilization is ≥ 100 the command
    is aborted with exit code 3 and a human checkpoint message is displayed.

    This enforces §economy/execution-budget.md Circuit Breaker Rule 3:
    "Agent MUST NOT load additional context once BREACH is reached."
    """
    pct_str = os.environ.get("SDD_BUDGET_UTILIZATION_PCT", "").strip()
    if not pct_str:
        return
    try:
        pct = float(pct_str)
    except ValueError:
        return
    if pct < 100.0:
        return

    typer.echo(
        f"\n[SDD] BUDGET BREACH: context utilization at {pct:.1f}% (>= 100%).\n"
        "Further context loading is blocked (§economy/execution-budget.md).\n"
        "Human checkpoint required. Options:\n"
        "  1. Decompose the task into smaller PATH A/B units\n"
        "  2. Clear session context and restart\n"
        "  3. Run: sdd runtime status  (inspect workspace state)\n",
        err=True,
    )
    raise typer.Exit(_BREACH_EXIT_CODE)


def _guard_handshake(workspace_root: Path) -> None:
    """Enforce handshake requirement (M015) based on signature mode."""
    try:
        sig_mode = _signature_mode()
        cached_ahp = _get_cached_ahp()
        is_valid = (
            bool(cached_ahp.get("valid")) if isinstance(cached_ahp, dict) else None
        )
        if is_valid is None:
            from sdd_core.governance.handshake import AgentHandshakeProtocol

            ahp = AgentHandshakeProtocol(project_root=workspace_root)
            is_valid = ahp.is_handshake_valid(strict=sig_mode == "strict")
        if not is_valid:
            if sig_mode == "strict":
                typer.echo(
                    "BLOCK [ask]: Missing or incomplete handshake. "
                    "Run 'sdd governance validate' to establish a session contract first.",
                    err=True,
                )
                raise typer.Exit(3)
            else:
                if not _json_mode():
                    typer.echo(
                        "SOFT [ask]: No active handshake. "
                        "Run 'sdd governance handshake --init' to formalize your session.",
                        err=True,
                    )
    except Exception as exc:
        logger.debug("Handshake guard skipped: %s", exc)
