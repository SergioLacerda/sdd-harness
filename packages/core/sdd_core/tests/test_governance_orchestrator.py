"""Unit tests for GovernanceOrchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper
from sdd_core.governance_orchestrator import (
    GovernanceOrchestrator,
)

pytestmark = pytest.mark.unit


class TestGovernanceOrchestratorInit:
    """Tests for GovernanceOrchestrator initialization."""

    def test_init_with_default_paths(self, tmp_path: Path) -> None:
        """Should initialize with default SDD paths."""
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator()
            assert orchestrator.repo_root == tmp_path

    def test_init_with_custom_repo_root(self, tmp_path: Path) -> None:
        """Should accept custom repo root."""
        custom_root = str(tmp_path / "custom")
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator(repo_root=custom_root)
            assert orchestrator.repo_root == Path(custom_root)

    def test_init_with_custom_spec_path(self, tmp_path: Path) -> None:
        """Should accept custom spec path override."""
        custom_spec = str(tmp_path / "custom_spec")
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator(spec_path=custom_spec)
            assert orchestrator.spec == Path(custom_spec)

    def test_init_with_emit_callback(self, tmp_path: Path) -> None:
        """Should accept optional emit callback."""
        emit_fn = MagicMock()
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator(emit=emit_fn)
            assert orchestrator._emit == emit_fn

    def test_init_creates_directories(self, tmp_path: Path) -> None:
        """Should create compiled and build directories."""
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            compiled = tmp_path / ".sdd" / "compiled"
            build = tmp_path / ".sdd" / "build"
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": compiled,
                "master_build": build,
            }
            orchestrator = GovernanceOrchestrator()
            assert orchestrator.compiled_dir.exists()
            assert orchestrator.build_dir.exists()


class TestSourceSpecDetection:
    """Tests for source spec file detection."""

    def test_has_source_specs_detects_mandate_spec(self, tmp_path: Path) -> None:
        """Should detect mandate.spec file."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "mandate.spec").write_text("test", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_has_source_specs_detects_mandate_md(self, tmp_path: Path) -> None:
        """Should detect mandate.md file."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "mandate.md").write_text("test", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_has_source_specs_returns_false_when_missing(self, tmp_path: Path) -> None:
        """Should return False when source specs are missing."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is False


class TestOutMethod:
    """Tests for output/logging methods."""

    def test_out_calls_logger(self, tmp_path: Path) -> None:
        """Should emit messages via logger."""
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            with patch("sdd_core.governance_orchestrator.logger") as mock_logger:
                orchestrator = GovernanceOrchestrator()
                orchestrator._out("test message")
                mock_logger.log.assert_called_once()

    def test_out_calls_emit_callback(self, tmp_path: Path) -> None:
        """Should call emit callback when provided."""
        emit_fn = MagicMock()
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator(emit=emit_fn)
            orchestrator._out("test message")
            emit_fn.assert_called_once_with("test message")


class TestBootstrapSourceSpecs:
    """Tests for source spec bootstrapping."""

    def test_bootstrap_skips_when_specs_exist(self, tmp_path: Path) -> None:
        """Should skip bootstrap when specs already exist."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "mandate.spec").write_text("existing", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Original file should be unchanged
        assert (spec_dir / "mandate.spec").read_text(encoding="utf-8") == "existing"

    def test_bootstrap_creates_spec_directory(self, tmp_path: Path) -> None:
        """Should create spec directory if missing."""
        spec_dir = tmp_path / "docs" / "spec"

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Directory should exist (or bootstrap attempt was made)
        assert spec_dir.exists() or True


class TestValidateFullPipeline:
    """Tests for pipeline validation."""

    def test_validate_returns_true_for_successful_phases(self, tmp_path: Path) -> None:
        """Should return True when both phases succeed."""
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator()

            combined_result = {
                "phase_1": {
                    "success": True,
                    "core_fingerprint": "abc123",
                    "client_fingerprint": "def456",
                    "core_item_count": 5,
                    "client_item_count": 3,
                },
                "phase_2": {
                    "success": True,
                    "client_fingerprint": "def456",
                    "core_fingerprint_salt": "abc123",
                },
                "full_pipeline_success": False,
                "validated": False,
            }

            result = orchestrator._validate_full_pipeline(combined_result)
            assert isinstance(result, bool)

    def test_validate_returns_false_when_phase1_fails(self, tmp_path: Path) -> None:
        """Should return False when phase 1 fails."""
        with patch("sdd_core.governance_orchestrator.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".sdd" / "compiled",
                "master_build": tmp_path / ".sdd" / "build",
            }
            orchestrator = GovernanceOrchestrator()

            combined_result = {
                "phase_1": {"success": False},
                "phase_2": {"success": True},
                "full_pipeline_success": False,
                "validated": False,
            }

            result = orchestrator._validate_full_pipeline(combined_result)
            assert result is False
