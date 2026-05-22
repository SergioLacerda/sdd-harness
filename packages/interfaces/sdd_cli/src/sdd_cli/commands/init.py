"""sdd init — initialize an SDD workspace."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import cast

import typer

from sdd_core.utils.environment import (
    SddProfile,
    find_workspace_root,
    write_profile,
)

app = typer.Typer()
logger = logging.getLogger(__name__)


def _run_cli_step(label: str, args: list[str], cwd: Path) -> bool:
    """Run a CLI subcommand as a subprocess step. Returns True on success."""
    from sdd_core.utils.process import SafeProcessRunner

    typer.echo(f"\n[bootstrap] {label}...")
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run(
        ["sdd"] + args,
        cwd=cwd,
        env=env,
        capture_output=False,
    )
    ok = result.success
    typer.echo(f"  {'OK' if ok else 'FAIL'}: {label}")
    return ok


@app.callback(invoke_without_command=True)
def init(
    type: str = typer.Option(  # noqa: A002
        "client",
        "--type",
        "-t",
        help="Workspace type: master (framework) or client (project instance).",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Human-readable workspace name (e.g. prod-client, dev-master). Defaults to type.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .sdd/profile without prompting (safe in CI).",
    ),
    full_bootstrap: bool = typer.Option(
        False,
        "--full-bootstrap",
        help="Run governance compile + runtime status after init (zero-touch setup).",
    ),
) -> None:
    """Initialize an SDD workspace in the current directory.

    Creates .sdd/profile with a versioned schema (v1).
    Refuses nested workspaces (detects .sdd/ in parent directories).
    """
    cwd = Path.cwd()

    # Block nested workspace init: check parents (not cwd itself)
    parent_workspace = find_workspace_root(cwd.parent)
    if parent_workspace is not None:
        typer.echo(
            f"[SDD] ERROR: A workspace already exists at '{parent_workspace}'.\n"
            "Nested workspaces are not supported. Run 'sdd init' from a directory "
            "outside the existing workspace.",
            err=True,
        )
        raise typer.Exit(1)

    profile_path = cwd / ".sdd" / "profile"
    overwriting_existing = profile_path.exists() and force

    # Handle existing profile
    if profile_path.exists() and not force:
        _show_existing_profile(profile_path, cwd)
        typer.echo(
            "\n[SDD] Workspace already initialized.\n"
            "Use --force to overwrite, or edit .sdd/profile directly.",
            err=True,
        )
        raise typer.Exit(1)

    normalized_type = type.strip().lower()
    if normalized_type not in ("master", "client"):
        typer.echo("[SDD] ERROR: --type must be 'master' or 'client'.", err=True)
        raise typer.Exit(2)

    profile_type = cast(SddProfile, normalized_type)
    effective_name = name or profile_type
    ctx = write_profile(cwd, profile_type, effective_name)

    # Initialize runtime marker expected by AHP layer 3.
    runtime_dir = cwd / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / ".phase-0-complete").touch(exist_ok=True)

    try:
        import uuid

        from sdd_runtime.telemetry import RuntimeEvent, TelemetrySink

        sink = TelemetrySink()
        sink.emit(
            RuntimeEvent(
                event="workspace.init",
                command="init",
                status="ok",
                trace_id=str(uuid.uuid4()),
                details={
                    "workspace_id": ctx.workspace_id,
                    "name": effective_name,
                    "forced": bool(force),
                    "phase_0_origin": "bootstrap_init",
                    "profile_type": profile_type,
                },
            )
        )
        sink.flush()
    except Exception:
        logger.debug("Failed to emit workspace init event", exc_info=True)

    typer.echo(f"[SDD] Workspace initialized at '{cwd}'")
    typer.echo(f"  type:         {ctx.type}")
    typer.echo(f"  name:         {ctx.name}")
    typer.echo(f"  workspace_id: {ctx.workspace_id}")
    typer.echo("  core_hash:    (empty — run 'sdd governance compile' to populate)")
    typer.echo("  phase_0:      completed")

    if full_bootstrap:
        typer.echo("")
        typer.echo("=== Full Bootstrap ===")
        compile_ok = _run_cli_step("governance compile", ["governance", "compile"], cwd)
        status_ok = _run_cli_step(
            "runtime status", ["runtime", "status", "--force"], cwd
        )
        if compile_ok and status_ok:
            typer.echo("\n[bootstrap] Workspace ready.")
        else:
            typer.echo(
                "\n[bootstrap] Some steps failed. "
                "Run 'sdd governance compile' and 'sdd runtime status' manually.",
                err=True,
            )
            raise typer.Exit(1)
    else:
        typer.echo("")
        typer.echo("Next steps:")
        typer.echo("  sdd governance compile   # build governance artifacts")
        typer.echo("  sdd runtime status       # verify workspace state")

    if overwriting_existing:
        typer.echo(
            "  [SOFT] profile overwritten: re-run 'sdd governance compile' to sync core_hash"
        )


def _show_existing_profile(profile_path: Path, root: Path) -> None:
    """Display the current .sdd/profile contents."""
    import configparser

    parser = configparser.ConfigParser()
    parser.read(profile_path)

    typer.echo(f"[SDD] Existing workspace at '{root}':")
    for key, value in parser.items("sdd"):
        typer.echo(f"  {key:15} = {value}")
