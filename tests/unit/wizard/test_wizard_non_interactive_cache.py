"""Tests for non-interactive wizard M003 context cache behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def test_run_phase_7_ensures_context_cache(tmp_path: Path) -> None:
    from sdd_wizard.src import wizard as wizard_module

    paths = {
        "root": tmp_path,
        "client_build": tmp_path / "generated" / "client" / "build",
        "client_compiled": tmp_path / "generated" / "client" / "compiled",
        "master_compiled": tmp_path / "generated" / "master" / "compiled",
        "client_context": tmp_path / "generated" / "client" / "context",
    }

    project_dir = tmp_path / "generated" / "client" / "build" / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=paths),
        patch(
            "sdd_wizard.src.wizard.phase_7_validate_output",
            return_value=(
                True,
                {
                    "status": "SUCCESS",
                    "phase": "PHASE 7: VALIDATE OUTPUT",
                    "data": {},
                    "warnings": [],
                    "errors": [],
                },
            ),
        ),
    ):
        orchestrator = wizard_module.WizardOrchestrator(repo_root=tmp_path)
        ok = orchestrator.run_phase_7(project_dir)

    assert ok is True
    assert (project_dir / ".sdd" / "runtime" / ".sdd-cache.md").exists()
