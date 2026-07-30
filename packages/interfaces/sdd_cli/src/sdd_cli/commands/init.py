"""sdd init — initialize an SDD workspace."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn, cast

import typer

from sdd_cli.commands.init_steps import _emit_workspace_init_telemetry
from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.services.onboarding import OnboardingOrchestrator
from sdd_cli.utils.operational_errors import (
    OperationalCliError,
    operational_error_from_exception,
    render_operational_error,
)
from sdd_cli.utils.sdd_console import format_sdd_line
from sdd_core.utils.environment import (
    ProfileContext,
    SddProfile,
    write_profile,
)

app = typer.Typer()

_PROJECT_BOUNDARY_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Makefile",
)


def _raise_init_operational_error(
    exc: BaseException,
    *,
    headline: str,
    step: str,
    operation: str,
    path: Path,
    next_hint: str = "check folder permissions, then retry: sdd init --force",
) -> NoReturn:
    operational_error = operational_error_from_exception(
        exc,
        headline=headline,
        command="sdd init",
        step=step,
        operation=operation,
        path=path,
        next_hint=next_hint,
    )
    if operational_error is None:
        raise exc
    _exit_init_operational_error(operational_error)


def _exit_init_operational_error(error: OperationalCliError) -> NoReturn:
    render_operational_error(error)
    raise typer.Exit(error.exit_code) from None


def _write_profile_or_exit(
    cwd: Path, profile_type: SddProfile, effective_name: str
) -> ProfileContext:
    try:
        return write_profile(cwd, profile_type, effective_name)
    except OSError as exc:
        _raise_init_operational_error(
            exc,
            headline="Could not write SDD workspace profile.",
            step="profile",
            operation="write profile",
            path=cwd / ".sdd" / "profile",
        )
        raise


def _resolve_default_flags(
    ctx: typer.Context, type_: str, name: str | None, force: bool
) -> tuple[str, str | None, bool]:
    """Apply --default fallbacks for any options left at their CLI defaults."""
    type_source = ctx.get_parameter_source("type")
    if type_source is not None and type_source.name == "DEFAULT":
        type_ = "client"
    name_source = ctx.get_parameter_source("name")
    if name_source is not None and name_source.name == "DEFAULT":
        name = "local-dev"
    force_source = ctx.get_parameter_source("force")
    if force_source is not None and force_source.name == "DEFAULT":
        force = True
    return type_, name, force


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _find_project_boundary(cwd: Path) -> Path | None:
    for candidate in [cwd, *cwd.parents]:
        if any((candidate / marker).exists() for marker in _PROJECT_BOUNDARY_MARKERS):
            return candidate
    return None


def _find_parent_workspace_with_profile(start: Path) -> Path | None:
    """Nearest ancestor that is a real workspace (`.sdd/profile` present).

    A bare `.sdd/` directory without a profile — e.g. the `~/.sdd/bin`
    compiler-binary cache — is not a workspace and must not block `sdd init`.
    """
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".sdd" / "profile").is_file():
            return candidate
    return None


def _find_blocking_parent_workspace(cwd: Path) -> Path | None:
    parent_workspace = _find_parent_workspace_with_profile(cwd.parent)
    if parent_workspace is None:
        return None
    if not (parent_workspace / ".sdd" / "profile").exists():
        # A bare `.sdd/` with no profile is a global CLI cache (toolchain
        # binaries, runtime state), not an initialized project workspace.
        return None
    project_boundary = _find_project_boundary(cwd)
    if project_boundary is not None and not _is_relative_to(
        parent_workspace, project_boundary
    ):
        return None
    return parent_workspace


@app.callback(invoke_without_command=True)
def init(  # noqa: C901
    ctx: typer.Context,
    type: str = typer.Option(  # noqa: A002
        "client",
        "--type",
        "-t",
        help="Workspace type: master (framework) or client (project instance).",
    ),
    name: str | None = typer.Option(  # noqa: UP045
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
    no_bootstrap: bool = typer.Option(
        False,
        "--no-bootstrap",
        help="Skip governance and skills bootstrap (profile only). Default for --type master.",
    ),
    default: bool = typer.Option(
        False,
        "--default",
        help="One-command bootstrap: defaults --type to 'client', --name to 'local-dev', and --force, for any of those not explicitly set.",
    ),
    list_commands: bool = typer.Option(False, "--list", help="List init commands."),
) -> None:
    """Initialize an SDD workspace in the current directory.

    Creates `.sdd/profile` and refuses nested workspaces.
    """
    cwd = Path.cwd()

    if list_commands:
        show_command_group("Init", ["--type client", "--type master", "--default"])
        raise typer.Exit(0)

    if default:
        type, name, force = _resolve_default_flags(ctx, type, name, force)  # noqa: A001
    parent_workspace = _find_blocking_parent_workspace(cwd)
    if parent_workspace is not None:
        typer.echo(
            f"[SDD] ERROR: A workspace already exists at '{parent_workspace}'.\nNested workspaces are not supported. Run 'sdd init' from a directory outside the existing workspace.",
            err=True,
        )
        raise typer.Exit(1)

    profile_path = cwd / ".sdd" / "profile"
    overwriting_existing = profile_path.exists() and force

    if profile_path.exists() and not force:
        _show_existing_profile(profile_path, cwd)
        typer.echo(
            "\n[SDD] Workspace already initialized.\nUse --force to overwrite, or edit .sdd/profile directly.",
            err=True,
        )
        raise typer.Exit(1)

    normalized_type = type.strip().lower()
    if normalized_type not in ("master", "client"):
        typer.echo("[SDD] ERROR: --type must be 'master' or 'client'.", err=True)
        raise typer.Exit(2)

    profile_type = cast(SddProfile, normalized_type)
    effective_name = name or profile_type
    profile_ctx = _write_profile_or_exit(cwd, profile_type, effective_name)

    runtime_dir = cwd / ".sdd" / "runtime"
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / ".phase-0-complete").touch(exist_ok=True)
    except OSError as exc:
        _raise_init_operational_error(
            exc,
            headline="Could not initialize SDD runtime marker.",
            step="profile",
            operation="create runtime marker",
            path=runtime_dir / ".phase-0-complete",
        )

    _emit_workspace_init_telemetry(
        profile_ctx=profile_ctx,
        effective_name=effective_name,
        force=force,
        profile_type=profile_type,
    )

    typer.echo(format_sdd_line(f"Workspace initialized at '{cwd}'"))
    typer.echo(f"  type:         {profile_ctx.type}")
    typer.echo(f"  name:         {profile_ctx.name}")
    typer.echo(f"  workspace_id: {profile_ctx.workspace_id}")
    typer.echo("  core_hash:    (empty — run 'sdd governance compile' to populate)")
    typer.echo("  phase_0:      completed")
    run_bootstrap = (profile_type == "client") and not no_bootstrap
    if run_bootstrap:
        typer.echo("")
        typer.echo("[1/4] Workspace profile created ✓")
        orc = OnboardingOrchestrator(cwd)
        try:
            bootstrap_result = orc.run(force=bool(force))
        except OperationalCliError as exc:
            _exit_init_operational_error(exc)
        except OSError as exc:
            operational_error = operational_error_from_exception(
                exc,
                headline="Governance activation failed because file access was denied.",
                command="sdd init",
                step="bootstrap",
                operation="run onboarding",
                next_hint="close programs that may be locking .sdd, then retry: sdd init --force",
            )
            if operational_error is None:
                raise
            _exit_init_operational_error(operational_error)
        if bootstrap_result.success:
            typer.echo("\n🟢 Onboarding complete — workspace is HEALTHY")
        else:
            if bootstrap_result.failed_step:
                typer.echo(f"  Step: {bootstrap_result.failed_step}", err=True)
            for msg in bootstrap_result.messages:
                typer.echo(f"  ERROR: {msg}", err=True)
            raise typer.Exit(bootstrap_result.exit_code)
    else:
        typer.echo("")
        typer.echo("Next steps:")
        typer.echo("  sdd governance generate --full-bootstrap")
        typer.echo("  sdd skills --full-bootstrap --regenerate-seeds")
        typer.echo("  sdd runtime status")
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
