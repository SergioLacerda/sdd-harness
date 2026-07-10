"""Setup."""

import sys

import typer

from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.utils.environment import (
    detect_repo_root,
    resolve_venv_python,
    resolve_venv_sdd,
)

app = typer.Typer(invoke_without_command=True)
_REPO_ROOT = detect_repo_root()


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List setup commands."),
) -> None:
    """Setup environment."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Setup", ["run"])
        raise typer.Exit(0)


def _run(cmd: list[str]) -> None:
    from sdd_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()
    result = runner.run(cmd, capture_output=False)
    if not result.success:
        typer.echo(f"ERROR: Failed: {' '.join(cmd)}")
        raise typer.Exit(1)


def _validate_module_import(venv_python: str, module: str) -> bool:
    """Validate module import in venv without python -c (blocked by governance policy)."""
    from sdd_core.utils.process import check_module_available

    return check_module_available(venv_python, module)


def _ensure_phase_0_marker() -> None:
    """Create AHP phase-0 marker used by runtime validation."""
    runtime_dir = _REPO_ROOT / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / ".phase-0-complete").touch(exist_ok=True)


@app.command(name="run")
def run_setup() -> None:  # noqa: C901
    """Setup SDD workspace."""

    typer.echo("SDD Workspace Setup")
    typer.echo("======================")

    python = sys.executable
    typer.echo(f"OK: Using Python: {python}")
    venv_dir = _REPO_ROOT / ".venv"
    if not venv_dir.exists():
        typer.echo("OK: Creating virtual environment...")
        _run([python, "-m", "venv", str(venv_dir)])
    try:
        venv_python = resolve_venv_python(venv_dir)
    except RuntimeError:
        typer.echo("ERROR: Could not find venv python")
        raise typer.Exit(1) from None
    typer.echo("OK: Virtualenv ready")
    if not _validate_module_import(str(venv_python), "pip"):
        typer.echo("OK: Bootstrapping pip (venv created without pip)...")
        _run([str(venv_python), "-m", "ensurepip", "--upgrade"])
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "-q"])
    typer.echo("\nInstalling SDD packages...")
    ordered_packages = [
        "packages/core/sdd_core",
        "packages/core/sdd_telemetry",
        "packages/core/sdd_runtime",
        "packages/features/sdd_integration",
        "packages/interfaces/sdd_wizard",
        "packages/interfaces/sdd_cli",
    ]
    for pkg in ordered_packages:
        pkg_path = _REPO_ROOT / pkg
        if (pkg_path / "pyproject.toml").exists():
            typer.echo(f"  Installing {pkg}")
            _run([str(venv_python), "-m", "pip", "install", "-e", str(pkg_path)])
        else:
            typer.echo(f"  WARN: Skipping {pkg} (no pyproject.toml)")
    for pkg_path in sorted(_REPO_ROOT.glob("packages/*/*")):
        if not (pkg_path / "pyproject.toml").exists():
            continue
        relative = str(pkg_path.relative_to(_REPO_ROOT))
        if relative not in ordered_packages:
            typer.echo(f"  Installing (extra) {relative}")
            _run([str(venv_python), "-m", "pip", "install", "-e", str(pkg_path)])
    if (_REPO_ROOT / "pyproject.toml").exists():
        typer.echo("\nInstalling dev dependencies...")
        _run(
            [str(venv_python), "-m", "pip", "install", "-e", f"{_REPO_ROOT}[dev]", "-q"]
        )
    typer.echo("\nValidating Python imports...")
    for module in ("sdd_core", "sdd_wizard", "sdd_cli"):
        if _validate_module_import(str(venv_python), module):
            typer.echo(f"  OK: {module} OK")
        else:
            typer.echo(f"  ERROR: {module} FAILED")
            raise typer.Exit(1)
    typer.echo("\nValidating CLI...")
    try:
        venv_sdd = resolve_venv_sdd(venv_dir)
    except RuntimeError:
        typer.echo("  ERROR: sdd CLI not found in venv")
        raise typer.Exit(1) from None
    typer.echo("  OK: sdd command available")

    from sdd_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()
    result = runner.run([str(venv_sdd), "--help"], capture_output=True)
    if not result.success:
        typer.echo("  ERROR: CLI not responding")
        raise typer.Exit(1)
    typer.echo("  OK: CLI responding")

    typer.echo("\nChecking sdd-compile (Go governance compiler)...")
    compile_bin = _REPO_ROOT / "tools" / "sdd-compile" / "bin" / "sdd-compile"
    if compile_bin.exists():
        typer.echo("  OK: sdd-compile binary found")
    else:
        typer.echo("  WARN: sdd-compile binary not found — run 'make build-compiler'")

    _ensure_phase_0_marker()
    typer.echo("  OK: Runtime phase-0 marker initialized")
    typer.echo("\nSetup completed!")
