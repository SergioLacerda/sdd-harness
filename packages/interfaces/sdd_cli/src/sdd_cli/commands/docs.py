"""Docs."""

import shutil

import click
import typer

from sdd_cli.services.command_group_output import show_command_group

app = typer.Typer(help="Documentation commands", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List docs commands."),
) -> None:
    """Documentation operations."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Documentation", ["deploy"])
        raise typer.Exit(0)


@app.command("deploy")
def deploy(force: bool = typer.Option(True, help="Force deploy to gh-pages")) -> None:
    """Deploy MkDocs documentation if mkdocs config exists."""
    config_files = ["mkdocs.yml", "mkdocs.yaml"]
    if not any(__import__("pathlib").Path(cfg).exists() for cfg in config_files):
        typer.echo(
            "No mkdocs config found (mkdocs.yml/mkdocs.yaml). Skipping docs deploy."
        )
        return

    if shutil.which("mkdocs") is None:
        typer.echo(
            "ERROR: mkdocs command not found. Install with: pip install mkdocs mkdocs-material"
        )
        raise click.exceptions.Exit(1)

    from sdd_core.utils.process import (
        AUTHORIZED_BINARIES,
        ProcessAuthorizationError,
        ProcessNonZeroExitError,
        ProcessSpawnError,
        ProcessTimeoutError,
        SafeProcessRunner,
    )

    cmd = ["mkdocs", "gh-deploy"]
    if force:
        cmd.append("--force")

    try:
        runner = SafeProcessRunner(authorized_binaries=AUTHORIZED_BINARIES | {"mkdocs"})
        runner.run(cmd, check=True, capture_output=False)
    except ProcessNonZeroExitError as err:
        typer.echo(f"ERROR: docs deploy failed: {err}", err=True)
        raise click.exceptions.Exit(1) from None
    except ProcessAuthorizationError as err:
        typer.echo(f"ERROR: execution blocked by policy: {err}", err=True)
        raise click.exceptions.Exit(2) from None
    except ProcessTimeoutError:
        typer.echo("ERROR: docs deploy timed out", err=True)
        raise click.exceptions.Exit(124) from None
    except ProcessSpawnError as err:
        typer.echo(f"ERROR: could not start docs deploy: {err}", err=True)
        raise click.exceptions.Exit(127) from None
