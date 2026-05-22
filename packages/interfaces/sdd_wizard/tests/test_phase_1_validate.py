"""Tests for Phase 1 validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sdd_wizard.orchestration.phase_1_validate import phase_1_validate_source


class TestPhase1ValidateSource:
    """Test Phase 1 source validation."""

    def test_success_returns_true_and_report(self, tmp_path: Path) -> None:
        """phase_1_validate_source should return success and report on valid pipeline."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": True,
                "phase_1": {
                    "core_item_count": 5,
                    "core_fingerprint": "fp-core-123",
                    "client_item_count": 3,
                    "client_fingerprint": "fp-client-456",
                    "error": None,
                },
            }

            success, report = phase_1_validate_source(tmp_path)

            assert success is True
            assert report["status"] == "SUCCESS"
            assert report["phase"] == "PHASE_1_VALIDATE_SOURCE"
            assert report["errors"] == []
            assert report["data"]["mandate"]["mandate_count"] == 5
            assert report["data"]["mandate"]["fingerprint"] == "fp-core-123"
            assert report["data"]["guidelines"]["guideline_count"] == 3
            assert report["data"]["guidelines"]["fingerprint"] == "fp-client-456"

    def test_failure_returns_false_and_error(self, tmp_path: Path) -> None:
        """phase_1_validate_source should return False and error on failure."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            error_msg = "Mandate spec not found"
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": False,
                "phase_1": {
                    "error": error_msg,
                },
            }

            success, report = phase_1_validate_source(tmp_path)

            assert success is False
            assert report["status"] == "FAILED"
            assert error_msg in report["errors"]

    def test_spec_path_override(self, tmp_path: Path) -> None:
        """phase_1_validate_source should pass spec_path override to orchestrator."""
        spec_path = tmp_path / "custom_spec"

        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": True,
                "phase_1": {
                    "core_item_count": 0,
                    "client_item_count": 0,
                },
            }

            phase_1_validate_source(tmp_path, spec_path=spec_path)

            # Verify orchestrator was initialized with spec_path
            mock_orchestrator_cls.assert_called_once()
            call_kwargs = mock_orchestrator_cls.call_args[1]
            assert call_kwargs["spec_path"] == str(spec_path)

    def test_no_spec_path_uses_none(self, tmp_path: Path) -> None:
        """phase_1_validate_source should pass None when spec_path not provided."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": True,
                "phase_1": {
                    "core_item_count": 0,
                    "client_item_count": 0,
                },
            }

            phase_1_validate_source(tmp_path)

            call_kwargs = mock_orchestrator_cls.call_args[1]
            assert call_kwargs["spec_path"] is None

    def test_report_structure_on_success(self, tmp_path: Path) -> None:
        """phase_1_validate_source report should have correct structure on success."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": True,
                "phase_1": {
                    "core_item_count": 10,
                    "core_fingerprint": "abc123",
                    "client_item_count": 5,
                    "client_fingerprint": "xyz789",
                    "error": None,
                },
            }

            _, report = phase_1_validate_source(tmp_path)

            # Verify report structure
            assert "phase" in report
            assert "status" in report
            assert "errors" in report
            assert "checks" in report
            assert "data" in report

            # Verify checks
            assert "mandate_spec_exists" in report["checks"]
            assert "guidelines_dsl_exists" in report["checks"]
            assert "mandate_spec_valid" in report["checks"]
            assert "guidelines_dsl_valid" in report["checks"]

            # Verify data
            assert "mandate" in report["data"]
            assert "guidelines" in report["data"]
            assert "mandate_count" in report["data"]["mandate"]
            assert "guideline_count" in report["data"]["guidelines"]

    def test_zero_counts_on_empty_phase_1(self, tmp_path: Path) -> None:
        """phase_1_validate_source should handle missing counts with defaults."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": False,
                "phase_1": {},  # Empty phase_1 data
            }

            success, report = phase_1_validate_source(tmp_path)

            assert success is False
            assert report["data"]["mandate"]["mandate_count"] == 0
            assert report["data"]["guidelines"]["guideline_count"] == 0

    def test_multiple_errors_concatenated(self, tmp_path: Path) -> None:
        """phase_1_validate_source should include error when present."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            error_msg = "Multiple validation errors"
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": False,
                "phase_1": {
                    "error": error_msg,
                },
            }

            _, report = phase_1_validate_source(tmp_path)

            assert len(report["errors"]) == 1
            assert report["errors"][0] == error_msg

    def test_no_error_on_success(self, tmp_path: Path) -> None:
        """phase_1_validate_source should have empty errors on success."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.GovernanceOrchestrator"
        ) as mock_orchestrator_cls:
            mock_orchestrator = MagicMock()
            mock_orchestrator_cls.return_value = mock_orchestrator
            mock_orchestrator.run_full_pipeline.return_value = {
                "full_pipeline_success": True,
                "phase_1": {
                    "core_item_count": 5,
                    "core_fingerprint": "abc",
                    "client_item_count": 3,
                    "client_fingerprint": "xyz",
                    "error": None,
                },
            }

            _, report = phase_1_validate_source(tmp_path)

            assert report["errors"] == []
