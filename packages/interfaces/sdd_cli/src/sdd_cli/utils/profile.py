"""Profile-aware policy adapters for SDD CLI commands.

Provides MasterAdapter and ClientAdapter that encode which operations are
permitted in each workspace context, along with helpers to retrieve the
active profile from Click context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import click


@dataclass(frozen=True)
class ProfilePolicy:
    """Defines which CLI operations are permitted for a given profile."""

    profile: str
    # Commands fully available in this profile
    allowed_commands: frozenset[str] = field(default_factory=frozenset)
    # Commands available but with a warning message
    warned_commands: dict[str, str] = field(default_factory=dict)
    # Commands blocked with an actionable error
    blocked_commands: dict[str, str] = field(default_factory=dict)


MasterAdapter = ProfilePolicy(
    profile="master",
    allowed_commands=frozenset(
        {
            "bootstrap",
            "governance",
            "doctor",
            "docs",
            "lint",
            "setup",
            "test",
            "release",
            "runtime",
            "version",
            "ask",
        }
    ),
    warned_commands={
        "wizard": "wizard is primarily a client operation; running in master workspace.",
    },
    blocked_commands={},
)

ClientAdapter = ProfilePolicy(
    profile="client",
    allowed_commands=frozenset(
        {
            "bootstrap",
            "governance",
            "doctor",
            "docs",
            "lint",
            "setup",
            "test",
            "wizard",
            "runtime",
            "version",
            "ask",
        }
    ),
    warned_commands={},
    blocked_commands={
        "release": "release is a master-only operation. Switch to the framework repository.",
    },
)

_ADAPTERS: dict[str, ProfilePolicy] = {
    "master": MasterAdapter,
    "client": ClientAdapter,
}


def get_adapter(profile: str) -> ProfilePolicy:
    """Return the policy adapter for the given profile (defaults to client)."""
    return _ADAPTERS.get(profile, ClientAdapter)


def get_active_profile(ctx: click.Context | None = None) -> str:
    """Resolve active profile from Click context or environment."""
    if ctx is not None and isinstance(ctx.obj, dict):
        return str(ctx.obj.get("profile", "client"))
    try:
        from sdd_core.utils.environment import detect_profile

        return detect_profile()
    except Exception:
        return "client"


def enforce_profile_policy(command_name: str, ctx: click.Context | None = None) -> None:
    """Check profile policy for a command; print warnings or raise Exit if blocked.

    Call at the start of command callbacks that should be profile-aware.
    """
    profile = get_active_profile(ctx)
    adapter = get_adapter(profile)

    if command_name in adapter.blocked_commands:
        msg = adapter.blocked_commands[command_name]
        click.echo(
            f"ERROR [{profile}]: command '{command_name}' is not available in this context.",
            err=True,
        )
        click.echo(f"  → {msg}", err=True)
        raise click.exceptions.Exit(1)

    if command_name in adapter.warned_commands:
        msg = adapter.warned_commands[command_name]
        click.echo(f"WARN [{profile}]: {msg}")


def profile_context_display(obj: Any) -> str:
    """Format profile context for display in command output."""
    if not isinstance(obj, dict):
        return ""
    profile = obj.get("profile", "client")
    icon = "🏗️ " if profile == "master" else "📦"
    return f"{icon} profile={profile}"


# Commands that are exempt from governance gate (run before workspace init or to fix governance).
_GATE_EXEMPT_COMMANDS = frozenset(
    {"init", "bootstrap", "version", "help", "governance", "runtime"}
)


def _extract_invocation(ctx: click.Context) -> tuple[str, str]:
    """Best-effort extraction of command and subcommand names."""
    import warnings

    raw_tokens: list[str] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        protected_args = getattr(ctx, "protected_args", []) or []
    raw_tokens.extend(str(t) for t in protected_args)
    if isinstance(ctx.args, list):
        raw_tokens.extend(str(t) for t in ctx.args)
    tokens = [t for t in raw_tokens if t and not t.startswith("-")]
    cmd = tokens[0] if tokens else ""
    subcmd = tokens[1] if len(tokens) > 1 else ""
    return cmd, subcmd


def _is_sensitive_command(cmd: str, subcmd: str) -> bool:
    """Commands that require stronger SOFT governance directives."""
    if cmd in {"release", "wizard", "ask"}:
        return True
    return bool(cmd == "governance" and subcmd in {"compile", "generate"})


def _collect_gate_directives(
    invoked: str,
    subcommand: str,
    profile: str,
    state: str,
    sensitive: bool,
) -> list[tuple[str, str, str]]:
    """Collect governance SOFT/HARD directives for the current invocation context.

    Returns a list of (message, next_step, reason) tuples.
    """
    directives: list[tuple[str, str, str]] = []

    # Profile-scoped SOFT directives.
    if invoked == "release" and profile == "client":
        directives.append(
            (
                "SOFT [governance]: 'release' em workspace client exige contexto master.",
                "use 'sdd --profile master release build'",
                "profile-release-client",
            )
        )
    if invoked == "wizard" and profile == "master":
        directives.append(
            (
                "SOFT [governance]: 'wizard' e primario para workspace client.",
                "confirme escopo ou rode em workspace client",
                "profile-wizard-master",
            )
        )
    if invoked == "ask" and state == "NOT_INITIALIZED":
        directives.append(
            (
                "HARD [governance]: 'ask' requires compiled governance. Workspace NOT_INITIALIZED.",
                "sdd governance compile && sdd runtime status --force",
                "ask-not-initialized",
            )
        )
    elif invoked == "ask" and state == "PARTIAL":
        directives.append(
            (
                "SOFT [governance]: governanca PARTIAL — precisao do ask pode ser reduzida.",
                "sdd governance compile",
                "ask-partial",
            )
        )

    # State-scoped HARD directives (Fail-Closed Governance Enforcement).
    if state == "MISCONFIGURED":
        directives.append(
            (
                "HARD [governance]: workspace MISCONFIGURED. Operacao abortada por seguranca.",
                "run 'sdd doctor run' para diagnostico e conserte a governanca",
                "state-misconfigured",
            )
        )
    elif state == "NOT_INITIALIZED" and invoked != "wizard" and sensitive:
        directives.append(
            (
                "SOFT [governance]: governanca nao inicializada. Operacao pode ser limitada.",
                "run 'sdd governance validate' ou compile a governanca",
                "state-not-initialized",
            )
        )
    elif state == "PARTIAL" and sensitive:
        directives.append(
            (
                "SOFT [governance]: comando sensivel em estado PARTIAL.",
                "run 'sdd runtime status --force' e 'sdd governance compile'",
                "state-partial-sensitive",
            )
        )

    return directives


def governance_gate(ctx: click.Context) -> None:
    """Validate workspace governance state before command execution.

    Runs the AHP check (cached — fast on re-runs) and:
    - HEALTHY / PARTIAL  → proceed silently
    - NOT_INITIALIZED    → warn once, then proceed (setup may still be in progress)
    - MISCONFIGURED      → warn with actionable message, then proceed
    - NOT_CONNECTED      → skip silently (not an SDD workspace)

    Exempt commands (init, version) bypass this gate entirely.
    """
    invoked, subcommand = _extract_invocation(ctx)
    if invoked in _GATE_EXEMPT_COMMANDS:
        return

    try:
        import os
        import uuid

        from sdd_runtime.telemetry import RuntimeEvent, TelemetrySink

        from sdd_cli.services.ask_telemetry import enqueue_flush

        root = ctx.obj.get("root") if isinstance(ctx.obj, dict) else None
        profile = ctx.obj.get("profile", "") if isinstance(ctx.obj, dict) else ""
        cached_ahp = ctx.obj.get("_ahp") if isinstance(ctx.obj, dict) else None
        if isinstance(cached_ahp, dict):
            state = str(cached_ahp.get("state", "UNKNOWN"))
        else:
            from pathlib import Path

            from sdd_core.governance.handshake import AgentHandshakeProtocol

            ahp = AgentHandshakeProtocol(project_root=Path(root) if root else None)
            state, _report = ahp.validate(output_mode="silent")

        # Determine logging mode based on profile (active for master, passive for client)
        logging_mode = "active" if profile == "master" else "passive"
        sink = TelemetrySink(logging_mode=logging_mode)

        sink.emit(
            RuntimeEvent(
                event="governance.checked",
                command=invoked,
                status="ok",
                trace_id=str(uuid.uuid4()),
                agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
                details={"state": state, "profile": profile},
            )
        )

        directives = _collect_gate_directives(
            invoked,
            subcommand,
            profile,
            state,
            _is_sensitive_command(invoked, subcommand),
        )

        from sdd_cli.utils.output import is_json_mode

        json_mode = is_json_mode(ctx)
        for msg, next_step, reason in directives:
            is_hard = "HARD [governance]" in msg
            # Suppress SOFT warnings in JSON mode — they would corrupt machine-parseable output.
            if is_hard or not json_mode:
                click.echo(f"{msg} Next: {next_step}", err=True)
            sink.emit(
                RuntimeEvent(
                    event="governance.violation",
                    command=invoked,
                    status="fail" if is_hard else "warn",
                    trace_id=str(uuid.uuid4()),
                    agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
                    details={
                        "state": state,
                        "profile": profile,
                        "action": "block" if is_hard else "warn",
                        "required_next_step": next_step,
                        "reason": reason,
                        "subcommand": subcommand,
                    },
                )
            )
            enqueue_flush(sink)
            if is_hard:
                raise click.exceptions.Exit(1)

        enqueue_flush(sink)
        # HEALTHY / NOT_CONNECTED with no profile directive → silent
    except click.exceptions.Exit:
        raise
    except Exception as _exc:  # nosec B110
        # typer.Exit (and typer._click.exceptions.Exit) must propagate — hard-block exits
        # must not be silenced even when the broader exception handler is active.
        if type(_exc).__name__ == "Exit" and hasattr(_exc, "exit_code"):
            raise
        # Gate must never block legitimate commands due to import errors.
        pass
