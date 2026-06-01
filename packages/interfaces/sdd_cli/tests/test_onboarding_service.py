"""Tests for OnboardingOrchestrator service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestOnboardingOrchestrator:
    def test_step_governance_skipped_when_artifacts_exist_no_force(
        self, tmp_path: Path
    ) -> None:
        """governance generate is skipped if governance-core.json already exists."""
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=False)
        mock_run.assert_not_called()
        assert result is True

    def test_step_governance_runs_when_force(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=True)
        mock_run.assert_called_once()
        assert result is True

    def test_step_governance_runs_when_no_artifacts(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=False)
        mock_run.assert_called_once()
        assert result is True

    def test_run_stops_on_governance_failure(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=False),
            patch.object(orc, "step_skills") as mock_skills,
            patch.object(orc, "step_validate") as mock_validate,
        ):
            result = orc.run(force=False)
        mock_skills.assert_not_called()
        mock_validate.assert_not_called()
        assert result.success is False
        assert result.failed_step == "governance"

    def test_run_stops_on_skills_failure(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=False),
            patch.object(orc, "step_validate") as mock_validate,
        ):
            result = orc.run(force=False)
        mock_validate.assert_not_called()
        assert result.success is False
        assert result.failed_step == "skills"

    def test_run_returns_success_when_all_pass(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
        ):
            result = orc.run(force=False)
        assert result.success is True
        assert result.failed_step is None

    def test_run_validate_failure_gives_exit_code_4(self, tmp_path: Path) -> None:
        from sdd_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=False),
        ):
            result = orc.run(force=False)
        assert result.success is False
        assert result.failed_step == "validate"
        assert result.exit_code == 4
