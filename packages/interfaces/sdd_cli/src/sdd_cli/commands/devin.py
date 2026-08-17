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
        help="Bundle output directory (default: <workspace>/dist/devin-plugin). Ignored with --standalone.",
    ),
    # bool | None (not a plain bool) so we can tell "user didn't pass either
    # flag" (None) apart from "user explicitly passed --skills" (True) — the
    # latter is a usage error together with --standalone, the former is not.
    skills: bool | None = typer.Option(
        None,
        "--skills/--no-skills",
        help=(
            "Include the SDD skill catalog (skills/*.md). Each skill's allowed CLI "
            "assumes the sdd CLI is installed in the Devin environment; use "
            "--no-skills for a governance-only bundle (AGENTS.md + rules/) with no "
            "such dependency. Not allowed together with --standalone. Default: "
            "included, unless --standalone is set."
        ),
    ),
    standalone: bool = typer.Option(
        False,
        "--standalone",
        help=(
            "Build a zero-SDD-mention project configuration at the repo root "
            "(AGENTS.md + .devin/config.json + .devin/hooks.v1.json + "
            ".devin/rules/*.md) instead of the SDD-branded plugin bundle. "
            "Refuses if AGENTS.md or .devin/ already exist."
        ),
    ),
) -> None:
    """Build a Devin governance surface: the SDD-branded plugin bundle (default) or a zero-SDD-mention standalone project config (--standalone)."""
    from sdd_adapters.devin import DevinPluginGenerator

    ws_root = resolve_workspace_root()

    if standalone:
        if skills:
            console.print(
                "[red]--standalone and --skills cannot be used together[/red] — "
                "skills are SDD-branded content (sourced from .sdd/skills/, "
                "documenting sdd-prefixed CLI commands), which contradicts "
                "--standalone's zero-SDD-mention guarantee."
            )
            raise typer.Exit(1)
        if dest is not None:
            console.print(
                "[red]--dest is not supported with --standalone[/red] — "
                "standalone mode always writes to the project root."
            )
            raise typer.Exit(1)

        result = DevinPluginGenerator().generate_standalone(output_dir=ws_root)

        if not result.success:
            console.print(
                f"[red]Devin standalone build failed:[/red] {'; '.join(result.errors)}"
            )
            raise typer.Exit(1)

        console.print(
            f"[green]Devin standalone config built[/green] ({len(result.files_written)} files)"
        )
        return

    include_skills = True if skills is None else skills
    result = DevinPluginGenerator().generate(
        output_dir=ws_root, dest=dest, include_skills=include_skills
    )

    if not result.success:
        console.print(
            f"[red]Devin plugin build failed:[/red] {'; '.join(result.errors)}"
        )
        raise typer.Exit(1)

    console.print(
        f"[green]Devin plugin built[/green] ({len(result.files_written)} files, "
        f"policy_digest=sha256:{result.policy_digest[:12]}...)"
    )
