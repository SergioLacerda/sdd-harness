"""SDD CLI entrypoint with lazy command loading.

This keeps `sdd --help` available even when optional command dependencies
are not installed yet (for example during minimal bootstrap in CI).
"""

from __future__ import annotations

import importlib
import logging
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import click
import typer
from dotenv import load_dotenv
from typer.main import get_command as typer_get_command

from sdd_cli.utils.cli_callbacks import (
    json_option_callback,
    profile_option_callback,
    verbose_option_callback,
)

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class CommandSpec:
    """Configuration for a lazily loaded CLI command group."""

    module_path: str
    help_text: str


COMMAND_SPECS: dict[str, CommandSpec] = {
    "init": CommandSpec("sdd_cli.commands.init", "Initialize an SDD workspace"),
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

# Only these commands require an initialized workspace profile at entrypoint.
_WORKSPACE_REQUIRED_COMMANDS = frozenset(
    {"ask", "organize", "runtime", "wizard", "release"}
)


def _requested_top_level_command(ctx: click.Context) -> str:
    """Return the first positional token that looks like a command name."""
    raw_tokens: list[str] = []

    # Click 8 stores pending subcommand tokens in protected_args.
    # Click 9 deprecates it in favor of args; keep backwards compatibility.
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


class LazyCommandGroup(click.Group):
    """Click group that imports each subcommand module only on demand."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List Commands."""
        del ctx
        # Keep command list deterministic in help output.
        return sorted(COMMAND_SPECS.keys())

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get Command."""
        del ctx
        spec = COMMAND_SPECS.get(cmd_name)
        if spec is None:
            return None

        try:
            module = importlib.import_module(spec.module_path)
            module_app = module.app
            if not isinstance(module_app, typer.Typer):
                raise TypeError(f"{spec.module_path}.app is not a typer.Typer instance")
            return cast(click.Command, typer_get_command(module_app))
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via CLI integration tests.
            return _build_unavailable_command(cmd_name, spec.module_path, exc)

    def invoke(self, ctx: click.Context) -> object:
        """Inject profile context before command execution."""
        requested_command = _requested_top_level_command(ctx)

        if ctx.obj is None:
            if requested_command in _WORKSPACE_REQUIRED_COMMANDS:
                try:
                    from sdd_core.utils.environment import (
                        WorkspaceNotInitializedError,
                        resolve_profile,
                    )

                    explicit_profile: str | None = ctx.params.get("profile")
                    profile_ctx = resolve_profile(override=explicit_profile)
                    ctx.obj = profile_ctx.as_dict()
                except WorkspaceNotInitializedError as exc:
                    # Propagate with a clear, actionable message (D16 — no silent fallback).
                    raise click.UsageError(str(exc)) from exc
            else:
                ctx.obj = {}

        if requested_command in _WORKSPACE_REQUIRED_COMMANDS and isinstance(
            ctx.obj, dict
        ):
            try:
                from sdd_core.governance.handshake import AgentHandshakeProtocol

                workspace_root = ctx.obj.get("root")
                ahp = AgentHandshakeProtocol(
                    project_root=Path(workspace_root) if workspace_root else None
                )
                state, report = ahp.validate(output_mode="silent")
                ctx.obj["_ahp"] = {
                    "state": state,
                    "report": report,
                    "valid": ahp.is_handshake_valid(),
                }
            except Exception:
                ctx.obj["_ahp"] = {
                    "state": "UNKNOWN",
                    "report": None,
                    "valid": False,
                }

        from sdd_cli.utils.profile import governance_gate

        governance_gate(ctx)
        try:
            return super().invoke(ctx)
        except click.exceptions.Exit as exc:
            raise click.exceptions.Exit(int(exc.exit_code)) from None
        except typer.Exit as exc:
            raise click.exceptions.Exit(exc.exit_code) from None


_profile_option_callback = profile_option_callback
_json_option_callback = json_option_callback
_verbose_option_callback = verbose_option_callback


app = LazyCommandGroup(
    name="sdd",
    help="SDD CLI - Spec Driven Development Toolkit",
    params=[
        click.Option(
            ["--profile"],
            type=click.Choice(["master", "client"], case_sensitive=False),
            default=None,
            is_eager=True,
            expose_value=True,
            callback=_profile_option_callback,
            help="Override active profile (master|client). Default: auto-detected.",
        ),
        click.Option(
            ["--json"],
            is_flag=True,
            default=False,
            expose_value=True,
            is_eager=True,
            callback=_json_option_callback,
            help="Emit JSON output for commands supporting structured output.",
        ),
        click.Option(
            ["--verbose", "-v"],
            is_flag=True,
            default=False,
            expose_value=True,
            is_eager=True,
            callback=_verbose_option_callback,
            help="Enable verbose output for commands supporting detailed mode.",
        ),
    ],
)


def main() -> int:
    """Main."""
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        from sdd_core.log_config import configure_logging

        configure_logging()
    except ImportError:
        logging.debug(
            "sdd_core.log_config not available; using stdlib logging defaults."
        )
    try:
        app(standalone_mode=False)
    except (click.exceptions.Exit, typer.Exit) as exc:
        return int(exc.exit_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
