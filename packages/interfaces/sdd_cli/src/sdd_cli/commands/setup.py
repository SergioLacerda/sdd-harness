"""Setup."""

import sys
from pathlib import Path

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
    from sdd_core.utils.process import check_module_available

    return check_module_available(venv_python, module)


def _ensure_phase_0_marker() -> None:
    """Create AHP phase-0 marker used by runtime validation."""
    runtime_dir = _REPO_ROOT / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / ".phase-0-complete").touch(exist_ok=True)


def _uninstall_git_hooks(hooks_src: Path, git_hooks_dest: Path) -> None:
    """Remove previously installed SDD git hooks."""
    typer.echo("Uninstalling SDD Internal Hooks...")
    for hook_file in hooks_src.iterdir():
        if hook_file.is_dir() or hook_file.name.startswith("."):
            continue
        target = git_hooks_dest / hook_file.name
        if target.is_symlink() or target.exists():
            target.unlink()
            typer.echo(f"  Removed: {hook_file.name}")


def _install_git_hook(hook_file: Path, git_hooks_dest: Path) -> bool:
    """Install a single git hook, returns True if copied instead of symlinked."""
    import os
    import shutil

    target = git_hooks_dest / hook_file.name
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        os.symlink(hook_file.absolute(), target)
        hook_file.chmod(0o755)
        typer.echo(f"  OK: Linked {hook_file.name}")
        return False
    except OSError:
        shutil.copy2(hook_file, target)
        target.chmod(0o755)
        typer.echo(
            f"  OK: Copied {hook_file.name} (symlink unavailable on this platform)"
        )
        return True


@app.command(name="git-hooks")
def setup_git_hooks(
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove SDD git hooks"),
) -> None:
    """Install or uninstall SDD git hooks."""
    hooks_src = _REPO_ROOT / "tools" / "scripts" / "git-hooks"
    git_hooks_dest = _REPO_ROOT / ".git" / "hooks"

    if not git_hooks_dest.exists():
        typer.echo(f"ERROR: .git/hooks directory not found at {git_hooks_dest}")
        raise typer.Exit(1)

    if uninstall:
        _uninstall_git_hooks(hooks_src, git_hooks_dest)
        return

    typer.echo(f"Installing SDD World-Class Hooks from {hooks_src}...")
    any_copied = False
    for hook_file in hooks_src.iterdir():
        if hook_file.is_dir() or hook_file.name.startswith("."):
            continue
        if _install_git_hook(hook_file, git_hooks_dest):
            any_copied = True
    if any_copied:
        typer.echo(
            "\nNote: hooks were copied (not linked) because symlinks are unavailable on this platform. Re-run 'sdd setup git-hooks' after pulling changes to tools/scripts/git-hooks/."
        )
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
        typer.echo(
            "  WARN: sdd-compile binary not found — run 'make build-compiler'"
        )

    _ensure_phase_0_marker()
    typer.echo("  OK: Runtime phase-0 marker initialized")
    if hooks:
        typer.echo("")
        setup_git_hooks()
    typer.echo("\nSetup completed!")
