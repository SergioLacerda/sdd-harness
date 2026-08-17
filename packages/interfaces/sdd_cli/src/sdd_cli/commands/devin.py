"""Devin governance plugin build commands (Soft/Standalone profile)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(
    help="Devin governance plugin generation", invoke_without_command=True
)
console = Console()


@app.callback(invoke_without_command=True)
def devin_default(ctx: typer.Context) -> None:
    """Devin plugin operations."""
    if ctx.invoked_subcommand is None:
        show_command_group("Devin", ["build"])
        raise typer.Exit(0)


@app.command("build")
def build(
    dest: Path | None = typer.Option(
        None,
        "--dest",
        help="Bundle output directory (default: <workspace>/dist/devin-plugin).",
    ),
) -> None:
    """Build the Soft/Standalone Devin governance plugin bundle from .sdd/skills/."""
    from sdd_adapters.devin import DevinPluginGenerator

    ws_root = resolve_workspace_root()
    result = DevinPluginGenerator().generate(output_dir=ws_root, dest=dest)

    if not result.success:
        console.print(
            f"[red]Devin plugin build failed:[/red] {'; '.join(result.errors)}"
        )
        raise typer.Exit(1)

    console.print(
        f"[green]Devin plugin built[/green] ({len(result.files_written)} files, "
        f"policy_digest=sha256:{result.policy_digest[:12]}...)"
    )
