"""Command registry specs and routing helpers for the SDD CLI entrypoint."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import click

__all__ = [
    "COMMAND_SPECS",
    "CommandSpec",
    "_WORKSPACE_REQUIRED_COMMANDS",
    "_build_unavailable_command",
    "_requested_top_level_command",
]


@dataclass(frozen=True)
class CommandSpec:
    """Configuration for a lazily loaded CLI command group."""

    module_path: str
    help_text: str


COMMAND_SPECS: dict[str, CommandSpec] = {
    "init": CommandSpec("sdd_cli.commands.init", "Initialize an SDD workspace"),
    "install": CommandSpec(
        "sdd_cli.commands.install", "Install SDD governance (canonical entrypoint)"
    ),
    "bootstrap": CommandSpec("sdd_cli.commands.bootstrap", "Bootstrap runtime state"),
    "runtime": CommandSpec("sdd_cli.commands.runtime", "Workspace runtime state"),
    "setup": CommandSpec("sdd_cli.commands.setup", "Setup environment"),
    "test": CommandSpec("sdd_cli.commands.test", "Run test pipeline"),
    "lint": CommandSpec("sdd_cli.commands.lint", "Run lint checks"),
    "wizard": CommandSpec("sdd_cli.commands.wizard", "Run wizard"),
    "governance": CommandSpec("sdd_cli.commands.governance", "Governance operations"),
    "skills": CommandSpec("sdd_cli.commands.skills", "Capability-oriented skills"),
    "doctor": CommandSpec("sdd_cli.commands.doctor", "Run diagnostics"),
    "docs": CommandSpec("sdd_cli.commands.docs", "Documentation operations"),
    "metrics": CommandSpec(
        "sdd_cli.commands.metrics", "Token economy metrics and Prometheus exposition"
    ),
    "release": CommandSpec("sdd_cli.commands.release", "Release operations"),
    "scaffold": CommandSpec(
        "sdd_cli.commands.scaffold", "Scaffold new skills and commands"
    ),
    "tools": CommandSpec("sdd_cli.commands.tools", "Developer and maintenance tools"),
    "audit": CommandSpec(
        "sdd_cli.commands.audit", "Governance drift and telemetry audit"
    ),
    "telemetry": CommandSpec(
        "sdd_cli.commands.telemetry", "Inspect and manage local telemetry events"
    ),
    "version": CommandSpec("sdd_cli.commands.version", "Show version"),
    "plugin": CommandSpec(
        "sdd_cli.commands.plugin",
        "Plugin registry management (list, validate)",
    ),
    "analysis": CommandSpec(
        "sdd_cli.commands.analysis",
        "Analysis workspace management (list, status, clean)",
    ),
    "ask": CommandSpec(
        "sdd_cli.commands.ask_entry",
        "Query SDD governance context (governed, minimal output)",
    ),
    "organize": CommandSpec(
        "sdd_cli.commands.organize",
        "Prepare and index large context blocks (sdd-organize)",
    ),
}

_WORKSPACE_REQUIRED_COMMANDS = frozenset(
    {"ask", "organize", "runtime", "wizard", "release", "install"}
)


def _requested_top_level_command(ctx: click.Context) -> str:
    """Return the first positional token that looks like a command name."""
    raw_tokens: list[str] = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        protected_args = getattr(ctx, "protected_args", []) or []

    raw_tokens.extend(str(token) for token in protected_args)
    raw_tokens.extend(str(token) for token in ctx.args)

    for token in raw_tokens:
        text = str(token).strip()
        if text and not text.startswith("-"):
            return text
    return ""


def _build_unavailable_command(
    name: str, module_path: str, exc: Exception
) -> click.Command:
    """Create a placeholder command shown when lazy import fails."""

    @click.command(
        name=name, help="Command temporarily unavailable in this environment."
    )
    def unavailable() -> None:
        click.echo(
            (
                f"Command '{name}' is unavailable because '{module_path}' could not be loaded.\n"
                f"Reason: {type(exc).__name__}: {exc}\n"
                "Run `sdd setup run` or install the missing package dependencies."
            ),
            err=True,
        )
        raise click.exceptions.Exit(1)

    return unavailable
