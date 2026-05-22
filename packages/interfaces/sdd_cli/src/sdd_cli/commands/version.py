"""Version command for SDD CLI."""

import typer

__version__ = "1.0.0"

app = typer.Typer()


@app.callback(invoke_without_command=True)
def _(ctx: typer.Context) -> None:
    """Show version information."""
    if ctx.invoked_subcommand is None:
        typer.echo(f"SDD Version: {__version__}")


@app.command()
def show() -> None:
    """Show SDD version."""
    typer.echo(f"SDD Version: {__version__}")
