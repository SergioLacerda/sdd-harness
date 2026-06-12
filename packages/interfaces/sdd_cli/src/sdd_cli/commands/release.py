"""Release."""

import sys

import click
import typer

app = typer.Typer(help="Release commands")


@app.callback()
def _() -> None:
    """Release operations."""


@app.command("build")
def build() -> None:
    """Build release artifacts into dist/."""
    from sdd_cli.utils.dev_deps import require_dev_module
    from sdd_cli.utils.profile import enforce_profile_policy
    from sdd_core.utils.process import (
        ProcessAuthorizationError,
        ProcessNonZeroExitError,
        ProcessSpawnError,
        ProcessTimeoutError,
        SafeProcessRunner,
    )

    enforce_profile_policy("release", click.get_current_context(silent=True))

    require_dev_module("build")

    try:
        runner = SafeProcessRunner()
        runner.run([sys.executable, "-m", "build"], check=True, capture_output=False)
    except ProcessNonZeroExitError as err:
        typer.echo(f"ERROR: build failed: {err}", err=True)
        raise typer.Exit(1) from None
    except ProcessAuthorizationError as err:
        typer.echo(f"ERROR: execution blocked by policy: {err}", err=True)
        raise click.exceptions.Exit(2) from None
    except ProcessTimeoutError:
        typer.echo("ERROR: build timed out", err=True)
        raise click.exceptions.Exit(124) from None
    except ProcessSpawnError as err:
        typer.echo(f"ERROR: could not start build: {err}", err=True)
        raise click.exceptions.Exit(127) from None
