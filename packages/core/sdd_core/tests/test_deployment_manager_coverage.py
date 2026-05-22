"""Coverage tests for DeploymentManager failure paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_core.deployment_manager import DeploymentManager

pytestmark = pytest.mark.unit


def _make_manager(tmp_path: Path) -> DeploymentManager:
    with patch("sdd_core.deployment_manager.get_sdd_paths") as mp:
        mp.return_value = {
            "root": tmp_path,
            "client_compiled": tmp_path / "client",
            "master_compiled": tmp_path / "master",
        }
        return DeploymentManager()


class TestDeployFailurePaths:
    def test_copy_failure_returns_failed_result(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with (
            patch.object(manager, "_validate_compiled_files", return_value=True),
            patch.object(manager, "_create_runtime_structure"),
            patch.object(manager, "_copy_files_transactional", return_value={}),
        ):
            result = manager.deploy()
        assert result["success"] is False

    def test_verification_failure_returns_failed_result(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with (
            patch.object(manager, "_validate_compiled_files", return_value=True),
            patch.object(manager, "_create_runtime_structure"),
            patch.object(manager, "_copy_files_transactional", return_value={"f": "p"}),
            patch.object(manager, "_verify_deployment", return_value=False),
        ):
            result = manager.deploy()
        assert result["success"] is False

    def test_validation_failure_returns_failed_result(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch.object(manager, "_validate_compiled_files", return_value=False):
            result = manager.deploy()
        assert result["success"] is False

    def test_get_deployment_status_delegates_to_reporter(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "sdd_core.deployment_manager.DeploymentReporter.get_deployment_status",
            return_value={"status": "ok"},
        ) as mock_status:
            result = manager.get_deployment_status()
        assert result == {"status": "ok"}
        mock_status.assert_called_once()
