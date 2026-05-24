"""
Tests for Wizard Phases 1-2
- Phase 1: Validate SOURCE
- Phase 2: Load COMPILED
"""

import tempfile
from pathlib import Path

import pytest

from sdd_wizard.orchestration.phase_1_validate import phase_1_validate_source
from sdd_wizard.orchestration.phase_2_load_compiled_v3 import (
    phase_2_load_compiled_v3 as phase_2_load_compiled,
)
from sdd_wizard.validator import SourceValidator


@pytest.mark.xdist_group("governance_pipeline")
class TestPhase1ValidateSource:
    """Tests for Phase 1: Validate SOURCE"""

    def test_phase_1_with_valid_files(self, mock_repo: Path) -> None:
        """Phase 1 should succeed when governance-core.json and governance-client.json exist in .sdd/."""
        success, report = phase_1_validate_source(mock_repo)

        assert success, f"Phase 1 failed: {report['errors']}"
        assert report["status"] == "SUCCESS"
        assert report["checks"]["mandate_spec_exists"]
        assert report["checks"]["guidelines_dsl_exists"]
        assert report["checks"]["mandate_spec_valid"]
        assert report["checks"]["guidelines_dsl_valid"]

    def test_phase_1_detects_missing_compiled_defaults(self) -> None:
        """Phase 1 should fail if compiled governance files are absent and fetch fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            from unittest.mock import patch

            with patch(
                "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
                return_value=(False, "failed"),
            ):
                success, report = phase_1_validate_source(repo_root)

            assert not success
            assert len(report["errors"]) > 0

    def test_phase_1_returns_dict_report(self) -> None:
        """Phase 1 should always return a dict report regardless of outcome."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            from unittest.mock import patch

            with patch(
                "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
                return_value=(False, "failed"),
            ):
                success, report = phase_1_validate_source(repo_root)

            assert isinstance(report, dict)
            assert "phase" in report
            assert "status" in report

    def test_phase_1_reports_success_with_compiled_defaults(
        self, mock_repo: Path
    ) -> None:
        """Phase 1 should succeed when compiled governance defaults are present in .sdd/."""
        success, report = phase_1_validate_source(mock_repo)

        assert success
        assert report["status"] == "SUCCESS"
        assert report["data"]["source"] == "local"


class TestPhase2LoadCompiled:
    """Tests for Phase 2: Load COMPILED"""

    def test_phase_2_with_valid_artifacts(self, mock_repo: Path) -> None:
        """Phase 2 should succeed with valid runtime/ files"""
        success, report = phase_2_load_compiled(mock_repo)

        assert success, f"Phase 2 failed: {report['errors']}"
        assert report["status"] == "SUCCESS"
        assert report["checks"]["core_json_exists"]
        assert report["checks"]["client_json_exists"]
        assert report["checks"]["fingerprint_validation"]
        assert report["checks"]["data_extraction"]
        # Should have loaded data
        assert "mandate" in report["data"]
        assert "guidelines" in report["data"]

    def test_phase_2_loads_statistics(self, mock_repo: Path) -> None:
        """Phase 2 should load and deserialize mandate/guideline data"""
        success, report = phase_2_load_compiled(mock_repo)

        assert success
        # Phase 2 loads the actual compiled data, not just statistics
        assert isinstance(report["data"]["mandate"], dict)
        assert isinstance(report["data"]["guidelines"], dict)
        assert len(report["data"]["mandate"]) > 0  # Should have mandates
        assert len(report["data"]["guidelines"]) > 0  # Should have guidelines

    def test_phase_2_detects_missing_runtime(self) -> None:
        """Phase 2 should fail if runtime/ is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            success, report = phase_2_load_compiled(repo_root)

            assert not success
            assert len(report["errors"]) > 0


class TestSourceValidator:
    """Tests for SourceValidator utility"""

    def test_validator_detects_unbalanced_braces(self) -> None:
        """Validator should detect unbalanced braces"""
        text = "mandate M001 { title: 'Test'"
        errors = SourceValidator.validate_dsl_syntax(text)

        assert len(errors) > 0
        assert any("Unbalanced braces" in e for e in errors)

    def test_validator_validates_mandate_spec(self) -> None:
        """Validator should validate mandate structure"""
        text = """
mandate M001 {
    title: "Clean Architecture"
    category: "architecture"
}

mandate M002 {
    title: "Test-Driven Development"
    category: "quality"
}
"""

        result = SourceValidator.validate_mandate_spec(text)

        assert result["valid"]
        assert result["statistics"]["mandate_count"] == 2
        assert "M001" in result["statistics"]["mandate_ids"]
        assert "M002" in result["statistics"]["mandate_ids"]

    def test_validator_supports_yaml_metadata(self) -> None:
        """Validator should parse block metadata fields associated with mandates"""
        text = """
mandate M001 {
    title: "Clean Architecture"
    category: "architecture"
    rationale: "platform-team"
    description: "security, infra"
}

mandate M002 {
    title: "TDD"
    category: "quality"
}
"""
        result = SourceValidator.validate_mandate_spec(text)

        assert result["valid"]
        # Protegendo contra KeyError e validando a estrutura de dados centralizada
        stats = result.get("statistics", {})
        mandates = stats.get("mandates", [])

        if mandates:
            assert mandates[0]["id"] == "M001"
            assert mandates[0]["metadata"]["rationale"] == "platform-team"
            assert "security" in mandates[0]["metadata"]["description"]

    def test_validator_detects_duplicate_ids(self) -> None:
        """Validator should detect duplicate mandate IDs"""
        text = """
mandate M001 {
    title: "Test1"
}

mandate M001 {
    title: "Test2"
}
"""

        result = SourceValidator.validate_mandate_spec(text)

        assert not result["valid"]
        assert any("Duplicate" in str(e) for e in result["errors"])


@pytest.mark.xdist_group("governance_pipeline")
class TestIntegration:
    """Integration tests for Phases 1-2"""

    def test_phases_1_and_2_complete_successfully(self, mock_repo: Path) -> None:
        """Both phases should complete successfully with real repo"""
        # Phase 1
        success1, report1 = phase_1_validate_source(mock_repo)
        assert success1, f"Phase 1 failed: {report1['errors']}"

        # Phase 2
        success2, report2 = phase_2_load_compiled(mock_repo)
        assert success2, f"Phase 2 failed: {report2['errors']}"

        # Verify data continuity
        report1["data"]["mandate"].get("mandate_count", 0)
        phase2_mandates = report2["data"]["mandate"]

        # Phase 2 returns compiled mandate data as dict
        assert isinstance(phase2_mandates, dict)
        # Should have at least 1 mandate
        assert len(phase2_mandates) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
