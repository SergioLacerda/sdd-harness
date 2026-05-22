"""SDD Wizard public entry point — consumed by sdd_cli wizard command."""

from __future__ import annotations

from pathlib import Path


def run_wizard(repo_root: Path | None = None) -> None:
    """Launch the interactive SDD wizard."""
    from sdd_wizard.src.wizard import WizardOrchestrator

    root = repo_root or Path.cwd()

    try:
        from sdd_wizard.src.interactive_mode import run_interactive_wizard

        success = run_interactive_wizard(root)
    except ImportError:
        orchestrator = WizardOrchestrator(repo_root=root, verbose=True)
        success = orchestrator.run_full_pipeline()

    if not success:
        import sys

        sys.exit(1)
