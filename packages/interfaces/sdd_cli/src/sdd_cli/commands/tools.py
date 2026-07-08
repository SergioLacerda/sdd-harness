"""Tools."""

from pathlib import Path

import click
import typer

from sdd_cli.services.command_group_output import show_command_group

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List tool commands."),
) -> None:
    """Developer and maintenance tools."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Tools", ["list", "run"])
        raise typer.Exit(0)


def _find_repo_root() -> Path:
    from sdd_cli.utils.environment import detect_repo_root

    return detect_repo_root()


@app.command("list")
def list_tools() -> None:
    """List available developer and maintenance tools."""
    root = _find_repo_root()
    tools_dir = root / "tools"

    if not tools_dir.is_dir():
        typer.echo(f"Error: tools directory not found at {tools_dir}", err=True)
        raise click.exceptions.Exit(1)

    typer.echo("Available tools in tools/:")
    for script in sorted(tools_dir.rglob("*.py")):
        if script.name.startswith("__"):
            continue
        rel_path = script.relative_to(tools_dir)
        typer.echo(f"  - {rel_path}")


@app.command()
def run(
    name: str = typer.Argument(
        ...,
        help="Path to the tool script relative to tools/ (e.g. health/health_check.py)",
    ),
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments to pass to the tool"
    ),
) -> None:
    """Run a tool script using 'uv run'."""
    from sdd_core.utils.process import (
        ProcessAuthorizationError,
        ProcessSpawnError,
        SafeProcessRunner,
    )

    root = _find_repo_root()
    script_path = root / "tools" / name

    if not script_path.exists() and not name.endswith(".py"):
        # Try adding .py extension if missing
        script_path = root / "tools" / f"{name}.py"

    if not script_path.exists():
        typer.echo(f"Error: tool '{name}' not found at {script_path}", err=True)
        raise click.exceptions.Exit(1)

    cmd = ["uv", "run", str(script_path)]
    if args:
        cmd.extend(args)

    typer.echo(f"Running: {' '.join(cmd)}")
    try:
        # Stream tool output directly to the terminal/CI logs for debuggability.
        result = SafeProcessRunner().run(cmd, check=False, capture_output=False)
        raise click.exceptions.Exit(result.returncode)
    except ProcessAuthorizationError as exc:
        typer.echo(f"Error: execution blocked by policy: {exc}", err=True)
        raise click.exceptions.Exit(2) from None
    except ProcessSpawnError:
        typer.echo(
            "Error: 'uv' not found in path. Please install uv (https://github.com/astral-sh/uv).",
            err=True,
        )
        raise click.exceptions.Exit(127) from None
