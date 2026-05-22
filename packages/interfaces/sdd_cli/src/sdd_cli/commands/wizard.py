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

    run_wizard()
