"""SDD Wizard public entry point — consumed by sdd_cli wizard command."""

from __future__ import annotations

from pathlib import Path


def run_wizard(repo_root: Path | None = None, output_dir: Path | None = None) -> None:
    """Launch the interactive SDD wizard."""
    from sdd_wizard.src.interactive_mode import run_interactive_wizard

    root = repo_root or Path.cwd()
    success = run_interactive_wizard(root, output_dir=output_dir)

    if not success:
        import sys

        sys.exit(1)
