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
) -> None:
    """Install SDD governance (canonical entrypoint)."""
    if ctx.invoked_subcommand is not None:
        return

    if not wizard:
        typer.echo("ERROR: no install target specified")
        typer.echo("Run: sdd install --wizard")
        raise typer.Exit(1)

    run_wizard_command(output_dir=output_dir)

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
