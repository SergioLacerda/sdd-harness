"""Setup."""

import sys
import tempfile

import typer

from sdd_cli.utils.environment import (
    detect_repo_root,
    resolve_venv_python,
    resolve_venv_sdd,
)

app = typer.Typer()
_REPO_ROOT = detect_repo_root()


@app.callback()
def _() -> None:
    """Setup environment."""


def _run(cmd: list[str]) -> None:
    from sdd_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()
    result = runner.run(cmd, capture_output=False)
    if not result.success:
        typer.echo(f"ERROR: Failed: {' '.join(cmd)}")
        raise typer.Exit(1)


def _validate_module_import(venv_python: str, module: str) -> bool:
    """Validate module import in venv without python -c (blocked by governance policy)."""
    script = f"import {module}\nprint('ok')\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_sdd_import_check.py", delete=True
    ) as handle:
        handle.write(script)
        handle.flush()
        from sdd_core.utils.process import SafeProcessRunner

        runner = SafeProcessRunner()
        result = runner.run([venv_python, handle.name], capture_output=True)
        return result.success


def _ensure_phase_0_marker() -> None:
    """Create AHP phase-0 marker used by runtime validation."""
    runtime_dir = _REPO_ROOT / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / ".phase-0-complete").touch(exist_ok=True)


@app.command(name="git-hooks")
def setup_git_hooks(
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove SDD git hooks"),
) -> None:
    """Install or uninstall SDD git hooks."""
    import os

    hooks_src = _REPO_ROOT / "tools" / "scripts" / "git-hooks"
    git_hooks_dest = _REPO_ROOT / ".git" / "hooks"

    if not git_hooks_dest.exists():
        typer.echo(f"ERROR: .git/hooks directory not found at {git_hooks_dest}")
        raise typer.Exit(1)

    if uninstall:
        typer.echo("Uninstalling SDD Internal Hooks...")
        for hook_file in hooks_src.iterdir():
            target = git_hooks_dest / hook_file.name
            if target.is_symlink():
                target.unlink()
                typer.echo(f"  Removed link: {hook_file.name}")
        return

    typer.echo(f"Installing SDD World-Class Hooks from {hooks_src}...")
    for hook_file in hooks_src.iterdir():
        if hook_file.is_dir() or hook_file.name.startswith("."):
            continue

        target = git_hooks_dest / hook_file.name

        # Remove existing
        if target.exists() or target.is_symlink():
            target.unlink()

        # Create symlink
        try:
            os.symlink(hook_file.absolute(), target)
            # Ensure executable
            hook_file.chmod(0o755)
            typer.echo(f"  OK: Linked {hook_file.name}")
        except OSError as e:
            typer.echo(f"  FAILED: Could not link {hook_file.name}: {e}")
            raise typer.Exit(1) from e

    typer.echo("\n✅ SDD Internal Hooks Installed.")


@app.command(name="run")
def run_setup(  # noqa: C901
    hooks: bool = typer.Option(True, help="Install git hooks after setup"),
) -> None:
    """Setup SDD workspace."""

    typer.echo("SDD Workspace Setup")
    typer.echo("======================")

    python = sys.executable
    typer.echo(f"OK: Using Python: {python}")

    # Create venv
    venv_dir = _REPO_ROOT / ".venv"
    if not venv_dir.exists():
        typer.echo("OK: Creating virtual environment...")
        _run([python, "-m", "venv", str(venv_dir)])

    # Locate venv python (Linux/Mac or Windows)
    try:
        venv_python = resolve_venv_python(venv_dir)
    except RuntimeError:
        typer.echo("ERROR: Could not find venv python")
        raise typer.Exit(1) from None

    typer.echo("OK: Virtualenv ready")

    # Upgrade pip (quiet)
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "-q"])

    # Install ordered packages
    typer.echo("\nInstalling SDD packages...")
    ordered_packages = [
        "packages/core/sdd_core",
        "packages/core/sdd_telemetry",
        "packages/core/sdd_runtime",
        "packages/core/sdd_compiler",
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

    # Install any extra packages not in the ordered list
    for pkg_path in sorted(_REPO_ROOT.glob("packages/*/*")):
        if not (pkg_path / "pyproject.toml").exists():
            continue
        relative = str(pkg_path.relative_to(_REPO_ROOT))
        if relative not in ordered_packages:
            typer.echo(f"  Installing (extra) {relative}")
            _run([str(venv_python), "-m", "pip", "install", "-e", str(pkg_path)])

    # Install dev dependencies from root
    if (_REPO_ROOT / "pyproject.toml").exists():
        typer.echo("\nInstalling dev dependencies...")
        _run(
            [str(venv_python), "-m", "pip", "install", "-e", f"{_REPO_ROOT}[dev]", "-q"]
        )

    # Validate imports
    typer.echo("\nValidating Python imports...")
    for module in ("sdd_core", "sdd_wizard", "sdd_cli"):
        if _validate_module_import(str(venv_python), module):
            typer.echo(f"  OK: {module} OK")
        else:
            typer.echo(f"  ERROR: {module} FAILED")
            raise typer.Exit(1)

    # Validate CLI
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

    _ensure_phase_0_marker()
    typer.echo("  OK: Runtime phase-0 marker initialized")

    if hooks:
        typer.echo("")
        setup_git_hooks()

    typer.echo("\nSetup completed!")
