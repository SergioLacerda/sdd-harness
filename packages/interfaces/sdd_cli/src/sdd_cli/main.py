"""SDD CLI entrypoint with lazy command loading.

This keeps `sdd --help` available even when optional command dependencies
are not installed yet (for example during minimal bootstrap in CI).
"""

from __future__ import annotations

import logging
import sys

import click
import typer
from dotenv import load_dotenv

from sdd_cli._command_group import (
    _WORKSPACE_REQUIRED_COMMANDS,
    COMMAND_SPECS,
    CommandSpec,
    LazyCommandGroup,
    _build_unavailable_command,
    _requested_top_level_command,
    typer_get_command,
)
from sdd_cli.utils.cli_callbacks import (
    json_option_callback,
    profile_option_callback,
    verbose_option_callback,
)

__all__ = [
    "COMMAND_SPECS",
    "CommandSpec",
    "LazyCommandGroup",
    "_build_unavailable_command",
    "_requested_top_level_command",
    "_WORKSPACE_REQUIRED_COMMANDS",
    "typer_get_command",
    "app",
    "main",
]

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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
