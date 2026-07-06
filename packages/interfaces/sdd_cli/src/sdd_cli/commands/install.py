"""Install — canonical single entrypoint for activating SDD governance.

`sdd install --wizard` delegates to the same wizard callable used by the
legacy `sdd wizard run` entrypoint (kept as a documented alias, unchanged).

`--direct-root` is an opt-in Workstream 3 addition: after the wizard finishes
writing its usual final-template output, additionally deploy that output
directly into the project root. The final-template default path is
unaffected unless this flag is passed (see
`.analysis/refined/wizard-items-refinement-20260704/sq-003-final-template-audit.md`
for why the default is not flipped this release).
"""

from pathlib import Path

import typer

from sdd_cli.commands.wizard import run as run_wizard_command
from sdd_cli.services.command_group_output import show_command_group
from sdd_wizard.orchestration.wizard._direct_root_deploy import deploy_to_root

app = typer.Typer()


def _resolve_final_template_dir(output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir.expanduser().resolve()
    from sdd_core.utils.environment import get_sdd_paths

    return get_sdd_paths()["client_build"] / "final-template"


@app.callback(invoke_without_command=True)
def install(
    ctx: typer.Context,
    wizard: bool = typer.Option(
        False,
        "--wizard",
        help="Run the interactive SDD governance wizard.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for the final generated project template. Defaults to ./generated/client/build/final-template/.",
        show_default=False,
    ),
    direct_root: bool = typer.Option(
        False,
        "--direct-root",
        help=(
            "Opt-in: also deploy the generated final-template output directly "
            "into the project root (idempotent; never overwrites unmanaged files)."
        ),
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
    list_commands: bool = typer.Option(False, "--list", help="List install commands."),
) -> None:
    """Install SDD governance (canonical entrypoint)."""
    if ctx.invoked_subcommand is not None:
        return

    if list_commands:
        show_command_group("Install", ["--wizard"])
        raise typer.Exit(0)

    if not wizard:
        if from_file is not None or non_interactive:
            typer.echo("ERROR: --from-file/--non-interactive require --wizard")
            typer.echo("Run: sdd install --wizard --from-file <path>")
            raise typer.Exit(1)
        typer.echo("ERROR: no install target specified")
        typer.echo("Run: sdd install --wizard")
        raise typer.Exit(1)

    run_wizard_command(
        output_dir=output_dir,
        from_file=from_file,
        non_interactive=non_interactive,
    )

    if direct_root:
        final_template_dir = _resolve_final_template_dir(output_dir)
        result = deploy_to_root(
            target_root=Path.cwd(), final_template_dir=final_template_dir
        )
        typer.echo(
            "Direct-root deploy: "
            f"created={len(result.created)} updated={len(result.updated)} "
            f"unchanged={len(result.unchanged)} skipped={len(result.skipped)} "
            f"removed={len(result.removed)}"
        )
        if result.skipped:
            typer.echo(
                "  Skipped (unmanaged, not overwritten): " + ", ".join(result.skipped)
            )
