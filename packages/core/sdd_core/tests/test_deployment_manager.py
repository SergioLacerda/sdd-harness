"""Unit tests for DeploymentManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_core.deployment_manager import (
    GOVERNANCE_ARTIFACTS,
    DeploymentManager,
)

pytestmark = pytest.mark.unit


class TestDeploymentManagerInit:
    """Tests for DeploymentManager initialization."""

    def test_init_with_default_paths(self) -> None:
        """Should initialize with default SDD paths."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp/root"),
                "client_compiled": Path("/tmp/client/compiled"),
                "master_compiled": Path("/tmp/master/compiled"),
            }
            manager = DeploymentManager()
            assert manager.repo_root == Path("/tmp/root")
            assert manager.compiled_dir == Path("/tmp/client/compiled")

    def test_init_with_custom_repo_root(self) -> None:
        """Should accept custom repo root path."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/default"),
                "client_compiled": Path("/default/client/compiled"),
                "master_compiled": Path("/default/master/compiled"),
            }
            manager = DeploymentManager(repo_root="/custom/root")
            assert manager.repo_root == Path("/custom/root")

    def test_init_with_emit_callback(self) -> None:
        """Should accept optional emit callback for logging."""
        emit_fn = MagicMock()
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager(emit=emit_fn)
            assert manager._emit == emit_fn

    def test_runtime_compiled_path_set_correctly(self) -> None:
        """Should set runtime_compiled to .sdd/compiled/."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/project"),
                "client_compiled": Path("/project/client/compiled"),
                "master_compiled": Path("/project/master/compiled"),
            }
            manager = DeploymentManager()
            assert manager.runtime_compiled == Path("/project/.sdd/compiled")
            assert manager.runtime_audit == Path("/project/.sdd/compiled/audit")


class TestDeploymentManagerOut:
    """Tests for output messaging."""

    def test_out_calls_emit_when_provided(self) -> None:
        """_out() should call emit callback when provided."""
        emit_fn = MagicMock()
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager(emit=emit_fn)
            manager._out("test message")
            emit_fn.assert_called_once_with("test message")

    def test_out_silent_when_no_emit(self) -> None:
        """_out() should silently do nothing when emit is None."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager(emit=None)
            # Should not raise
            manager._out("test message")


class TestDeploymentManagerPathStr:
    """Tests for path string normalization."""

    def test_path_str_returns_posix_path(self) -> None:
        """_path_str() should return POSIX-style path string."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            result = manager._path_str(Path("/tmp/foo/bar"))
            assert result == "/tmp/foo/bar"
            assert isinstance(result, str)

    def test_path_str_normalizes_windows_paths(self) -> None:
        """_path_str() should normalize Windows-style paths to POSIX."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            # Even on Windows, as_posix() returns forward slashes
            path = Path("foo") / "bar" / "baz"
            result = manager._path_str(path)
            assert "\\" not in result


class TestDeploymentManagerFailedResult:
    """Tests for failed deployment result generation."""

    def test_failed_result_structure(self) -> None:
        """_failed_result() should return properly structured result."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            result = manager._failed_result()

            assert isinstance(result, dict)
            assert result["success"] is False
            assert "deployed_files" in result
            assert "deployment_location" in result
            assert "checklist" in result
            assert "manifest" in result
            assert "next_steps" in result

    def test_failed_result_has_empty_deployed_files(self) -> None:
        """Failed result should have empty deployed_files."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            result = manager._failed_result()
            assert result["deployed_files"] == {}


class TestGovernanceArtifacts:
    """Tests for governance artifacts constants."""

    def test_governance_artifacts_is_tuple(self) -> None:
        """GOVERNANCE_ARTIFACTS should be a tuple."""
        assert isinstance(GOVERNANCE_ARTIFACTS, tuple)

    def test_governance_artifacts_contains_required_files(self) -> None:
        """Should contain all required artifact filenames."""
        assert "governance-core.compiled.msgpack" in GOVERNANCE_ARTIFACTS
        assert "governance-client-template.compiled.msgpack" in GOVERNANCE_ARTIFACTS
        assert "metadata-core.json" in GOVERNANCE_ARTIFACTS
        assert "metadata-client-template.json" in GOVERNANCE_ARTIFACTS

    def test_governance_artifacts_not_empty(self) -> None:
        """GOVERNANCE_ARTIFACTS should not be empty."""
        assert len(GOVERNANCE_ARTIFACTS) > 0


class TestDeploymentManagerIntegration:
    """Integration tests for deployment workflow."""

    def test_deploy_with_missing_compiled_files(self, tmp_path: Path) -> None:
        """deploy() should return failed result when compiled files missing."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))
            result = manager.deploy()

            assert result["success"] is False
            assert result["deployed_files"] == {}

    def test_deploy_returns_deployment_result_structure(self, tmp_path: Path) -> None:
        """deploy() should return properly structured DeploymentResult."""
        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))
            result = manager.deploy()

            assert isinstance(result, dict)
            assert "success" in result
            assert "deployed_files" in result
            assert "deployment_location" in result
            assert "checklist" in result
            assert "manifest" in result
            assert "next_steps" in result

    @patch.object(DeploymentManager, "_cleanup_legacy_manifests")
    @patch.object(DeploymentManager, "_get_next_steps")
    @patch.object(DeploymentManager, "_generate_manifest")
    @patch.object(DeploymentManager, "_generate_checklist")
    @patch.object(DeploymentManager, "_validate_compiled_files")
    @patch.object(DeploymentManager, "_verify_deployment")
    @patch.object(DeploymentManager, "_copy_files_transactional")
    @patch.object(DeploymentManager, "_create_runtime_structure")
    def test_deploy_success_with_valid_files(
        self,
        mock_create_runtime: MagicMock,  # noqa: F841
        mock_copy: MagicMock,
        mock_verify: MagicMock,
        mock_validate: MagicMock,
        mock_checklist: MagicMock,
        mock_manifest: MagicMock,
        mock_next_steps: MagicMock,
        mock_cleanup: MagicMock,  # noqa: F841
        tmp_path: Path,
    ) -> None:
        """deploy() should return success when all validations pass."""
        mock_validate.return_value = True
        mock_verify.return_value = True
        mock_copy.return_value = {"file1": "dest1"}  # Non-empty dict for success
        mock_checklist.return_value = {"step1": True}
        mock_manifest.return_value = {"deployed": True}
        mock_next_steps.return_value = ["step1", "step2"]

        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))
            result = manager.deploy()

            assert result["success"] is True
            assert result["deployed_files"] == {"file1": "dest1"}
            assert result["checklist"] == {"step1": True}
            assert result["manifest"] == {"deployed": True}
            assert result["next_steps"] == ["step1", "step2"]
            mock_validate.assert_called()
            mock_copy.assert_called()
            mock_verify.assert_called()


class TestDeploymentManagerEmitMessages:
    """Tests for output messages during deployment."""

    def test_deploy_emits_messages(self, tmp_path: Path) -> None:
        """deploy() should emit messages during execution."""
        emit_fn = MagicMock()

        with patch("sdd_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path), emit=emit_fn)
            manager.deploy()

            # Should have called emit at least once
            assert emit_fn.called
