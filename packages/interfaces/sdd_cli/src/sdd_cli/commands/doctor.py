"""Doctor."""

from pathlib import Path

import typer

from sdd_cli.commands.doctor_gates import _apply_adherence_gate, _apply_score_gate
from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.utils.command_errors import handle_cli_errors
from sdd_cli.utils.environment import detect_repo_root
from sdd_cli.utils.sdd_authority import enforce_path_policy, resolve_workspace_root

app = typer.Typer(invoke_without_command=True)


def _get_default_spec() -> Path:
    """Resolve default spec path relative to repo root."""
    root = detect_repo_root()
    return (
        root
        / "packages"
        / "features"
        / "sdd_integration"
        / "src"
        / "sdd_integration"
        / "protocol"
        / "integration_flow.yaml"
    )


@app.callback()
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List doctor commands."),
    spec: Path = typer.Option(None, help="Path to integration flow spec"),  # noqa: B008
) -> None:
    """Run diagnostics."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Doctor", ["run", "compiler"])
        raise typer.Exit(0)


@app.command()
@handle_cli_errors(command_name="doctor compiler")
def compiler(
    prune: bool = typer.Option(
        False,
        "--prune",
        help="Remove stale ~/.sdd/bin cache entries (keeps the versions the "
        "installed CLI resolves and the packaged digest in use).",
    ),
) -> None:
    """Print sdd-compile toolchain diagnostics as stable JSON (read-only by default)."""
    import json

    from sdd_cli.services.doctor_compiler import (
        _probe_cache,
        build_compiler_report,
        run_prune,
    )

    report = build_compiler_report()
    if prune:
        from sdd_core.utils.compiler_runner import _cache_dir

        report["prune"] = run_prune()
        report["cache"] = _probe_cache(_cache_dir())
    typer.echo(json.dumps(report, indent=2))


@app.command()
@handle_cli_errors(
    command_name="doctor run",
    next_hint="run 'sdd setup run' to ensure dependencies are installed",
)
def run(
    spec: Path = typer.Option(None, help="Path to integration flow spec"),  # noqa: B008
    mode: str = typer.Option("isolated", help="Execution mode for doctor checks"),
    score_threshold: int = typer.Option(
        0,
        "--score-threshold",
        help="Minimum governance score (0-100). 0 disables the gate.",
    ),
    adherence_threshold: int = typer.Option(
        0,
        "--adherence-threshold",
        help="Minimum governance adherence score (0-100). 0 disables the gate.",
    ),
) -> None:
    """Run SDD diagnostics (integration flow)"""
    mode = mode.strip().lower()
    if mode not in {"isolated", "real"}:
        raise typer.BadParameter("mode must be 'isolated' or 'real'.")

    try:
        from sdd_integration.engine.integration_engine import IntegrationEngine
    except ImportError:
        typer.echo(
            "Command 'doctor' is unavailable because optional dependency 'sdd_integration' could not be loaded.\nRun `sdd setup run` or install the missing package dependencies.",
            err=True,
        )
        raise typer.Exit(1) from None

    workspace_root = resolve_workspace_root()
    enforce_path_policy(workspace_root, workspace_root=workspace_root, mode="normal")

    _apply_score_gate(score_threshold)
    _apply_adherence_gate(adherence_threshold)

    target_spec = spec or _get_default_spec()

    if not target_spec.exists():
        typer.echo(f"[red]ERROR: Spec file not found at {target_spec}[/red]", err=True)
        typer.echo(
            "  Next: run 'sdd setup run' to ensure all packages are installed", err=True
        )
        raise typer.Exit(1)

    typer.echo(f"Running SDD Doctor (Spec: {target_spec.name}, Mode: {mode})...\n")

    context_overrides = None
    if mode == "real":
        context_overrides = {"working_dir": str(detect_repo_root()), "isolation": False}

    engine = IntegrationEngine(str(target_spec), context_overrides=context_overrides)
    report = engine.run()

    typer.echo(report.pretty())

    if report.score() < 100:
        typer.echo(
            "  Next: review failing checks above and run 'sdd runtime status'", err=True
        )
        raise typer.Exit(1)
