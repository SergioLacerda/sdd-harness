"""Version command for SDD CLI."""

import typer

from sdd_cli.services.command_group_output import show_command_group

__version__ = "1.0.0"

app = typer.Typer()


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List version commands."),
) -> None:
    """Show version information."""
    if list_commands:
        show_command_group("Version", ["show"])
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(f"SDD Version: {__version__}")


@app.command()
def show() -> None:
    """Show SDD version."""
    typer.echo(f"SDD Version: {__version__}")
