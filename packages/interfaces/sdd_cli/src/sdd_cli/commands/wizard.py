"""Wizard."""

import click
import typer

app = typer.Typer()


@app.callback()
def _() -> None:
    """Run wizard."""


@app.command()
def run() -> None:
    """Run SDD wizard"""
    from sdd_cli.utils.profile import enforce_profile_policy

    enforce_profile_policy("wizard", click.get_current_context(silent=True))

    try:
        from sdd_wizard.main import run_wizard
    except ImportError as err:
        typer.echo("ERROR: sdd-wizard not installed")
        typer.echo("Run: sdd setup run")
        raise typer.Exit(1) from err

    try:
        run_wizard()
    except RuntimeError as err:
        message = str(err)
        if "SDD Project root not found" in message:
            typer.echo("ERROR: No SDD project context found in the current directory.")
            typer.echo(
                "Run from your project root (where you want .sdd/ to be created)."
            )
            typer.echo("Example:")
            typer.echo("  mkdir my-project && cd my-project")
            typer.echo("  sdd wizard run")
            raise typer.Exit(1) from err
        raise
