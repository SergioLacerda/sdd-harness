"""Wizard."""

from pathlib import Path

import click
import typer

from sdd_cli.services.command_group_output import show_command_group

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List wizard commands."),
) -> None:
    """Run wizard."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Wizard", ["run"])
        raise typer.Exit(0)


@app.command()
def run(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for the final generated project template. Defaults to ./generated/client/build/final-template/.",
        show_default=False,
    ),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        help="Path to a custom mandates/guidelines JSON file (Scenario B) — validated and used instead of generating a fresh governance set.",
        show_default=False,
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Resolve preferences/agent selection without prompting — reuses an existing wizard-config.json when present, else canonical defaults.",
    ),
) -> None:
    """Run SDD wizard"""
    from sdd_cli.utils.profile import enforce_profile_policy

    enforce_profile_policy("wizard", click.get_current_context(silent=True))

    try:
        from sdd_wizard.contracts import WizardInvocation, run_wizard
    except ImportError as err:
        typer.echo("ERROR: sdd-wizard not installed")
        typer.echo("Run: sdd setup run")
        raise typer.Exit(1) from err

    resolved_output = (
        output_dir.expanduser().resolve() if output_dir is not None else None
    )  # noqa: E501
    resolved_custom_governance_path = (
        from_file.expanduser().resolve() if from_file is not None else None
    )

    try:
        result = run_wizard(
            WizardInvocation(
                project_root=Path.cwd(),
                output_path=resolved_output,
                non_interactive=non_interactive,
                custom_governance_path=resolved_custom_governance_path,
            )
        )
        if not result.success:
            raise typer.Exit(1)
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
