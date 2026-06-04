"""Coverage tests for DeploymentManager failure paths."""

from __future__ import annotations

import builtins
import io
from pathlib import Path
from unittest.mock import patch

import pytest

import sdd_core.deployment_manager as deployment_manager
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


def _run_main_block(
    monkeypatch: pytest.MonkeyPatch, deploy_result: dict[str, object]
) -> str:
    source_path = Path("packages/core/sdd_core/src/sdd_core/deployment_manager.py")
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    prefix = "\n".join(source_lines[:216])
    suffix = "\n".join(source_lines[216:])

    namespace: dict[str, object] = {
        "__name__": "__main__",
        "__file__": str(source_path),
        "__builtins__": builtins.__dict__,
    }
    exec(compile(prefix, str(source_path), "exec"), namespace)

    class _FakeDeploymentManager:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def deploy(self) -> dict[str, object]:
            return deploy_result

    captured: list[str] = []

    def _capture_print(*args: object, **kwargs: object) -> None:
        del kwargs
        captured.append(" ".join(str(arg) for arg in args))

    monkeypatch.setitem(namespace, "DeploymentManager", _FakeDeploymentManager)
    monkeypatch.setitem(namespace, "print", _capture_print)
    exec(
        compile("\n" * 216 + suffix, str(source_path), "exec"),
        namespace,
    )
    return "\n".join(captured)


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

    def test_main_block_success_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = _run_main_block(
            monkeypatch,
            {
                "success": True,
                "checklist": {"step": True},
                "deployment_location": "/tmp/location",
                "manifest": {"artifacts": {"core": "/tmp/core"}, "status": "ok"},
                "next_steps": ["next"],
            },
        )
        assert "PHASE 4: DEPLOYMENT COMPLETE" in output
        assert "Status: OK" in output

    def test_main_block_failure_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = _run_main_block(
            monkeypatch,
            {
                "success": False,
                "checklist": {},
                "deployment_location": "/tmp/location",
                "manifest": {},
                "next_steps": [],
            },
        )
        assert "Deployment failed" in output

    def test_deploy_success_path(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        messages: list[str] = []

        with (
            patch(
                "sdd_core.deployment_manager.DeploymentValidator.validate_compiled_files",
                return_value=True,
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentFileSystem.create_runtime_structure"
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentFileSystem.copy_files_transactional",
                return_value={"core": "/tmp/core"},
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentValidator.verify_deployment",
                return_value=True,
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.generate_checklist",
                return_value={"check": True},
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.generate_manifest",
                return_value={"artifacts": {"core": "/tmp/core"}, "status": "ok"},
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.get_next_steps",
                return_value=["next"],
            ),
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.cleanup_legacy_manifests"
            ),
        ):
            manager._emit = messages.append
            result = manager.deploy()

        assert result["success"] is True
        assert result["deployed_files"] == {"core": "/tmp/core"}
        assert result["manifest"]["status"] == "ok"
        assert any("Deployment" in message for message in messages)

    def test_manager_delegates_all_helpers(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        audit_file = manager.compiled_dir / "audit"
        audit_file.mkdir(parents=True, exist_ok=True)
        preferred_path = audit_file / "metadata.json"
        preferred_path.write_text("{}", encoding="utf-8")

        with (
            patch.object(manager, "_emit"),
            patch(
                "sdd_core.deployment_manager.DeploymentValidator.validate_compiled_files",
                return_value=True,
            ) as mock_validate,
            patch(
                "sdd_core.deployment_manager.DeploymentFileSystem.create_runtime_structure"
            ) as mock_create,
            patch(
                "sdd_core.deployment_manager.DeploymentFileSystem.copy_files_transactional",
                return_value={"core": "/tmp/core"},
            ) as mock_copy,
            patch(
                "sdd_core.deployment_manager.DeploymentValidator.verify_deployment",
                return_value=True,
            ) as mock_verify,
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.generate_checklist",
                return_value={"check": True},
            ) as mock_checklist,
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.generate_manifest",
                return_value={"artifacts": {}, "status": "ok"},
            ) as mock_manifest,
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.get_next_steps",
                return_value=["next"],
            ) as mock_steps,
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.cleanup_legacy_manifests"
            ) as mock_cleanup,
            patch(
                "sdd_core.deployment_manager.DeploymentReporter.get_deployment_status",
                return_value={"status": "ok"},
            ) as mock_status,
        ):
            assert manager._metadata_source("metadata.json") == preferred_path
            preferred_path.unlink()
            assert (
                manager._metadata_source("metadata.json")
                == manager.compiled_dir / "metadata.json"
            )
            manager._out("hello")
            assert manager._validate_compiled_files() is True
            manager._create_runtime_structure()
            assert manager._copy_files_transactional() == {"core": "/tmp/core"}
            assert manager._verify_deployment() is True
            assert manager._generate_checklist() == {"check": True}
            assert manager._generate_manifest() == {"artifacts": {}, "status": "ok"}
            assert manager._get_next_steps() == ["next"]
            manager._cleanup_legacy_manifests()
            assert manager.get_deployment_status() == {"status": "ok"}

        mock_validate.assert_called_once()
        mock_create.assert_called_once()
        mock_copy.assert_called_once()
        mock_verify.assert_called_once()
        mock_checklist.assert_called_once()
        mock_manifest.assert_called_once()
        mock_steps.assert_called_once()
        mock_cleanup.assert_called_once()
        mock_status.assert_called_once()

    def test_full_module_main_block_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = io.StringIO()
        original_print = builtins.print

        class _FakeDeploymentManager:
            def __init__(self, *args: object, **kwargs: object) -> None:
                del args, kwargs

            def deploy(self) -> dict[str, object]:
                return {
                    "success": True,
                    "checklist": {"step": True},
                    "deployment_location": "/tmp/location",
                    "manifest": {"artifacts": {"core": "/tmp/core"}, "status": "ok"},
                    "next_steps": ["next"],
                }

        monkeypatch.setattr(
            deployment_manager, "DeploymentManager", _FakeDeploymentManager
        )
        monkeypatch.setattr(
            builtins,
            "print",
            lambda *args, **kwargs: original_print(*args, file=captured, **kwargs),
        )
        deployment_manager.main()
        output = captured.getvalue()
        assert "PHASE 4: DEPLOYMENT COMPLETE" in output
        assert "Status: OK" in output

    def test_full_module_main_block_unknown_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = io.StringIO()
        original_print = builtins.print

        class _FakeDeploymentManager:
            def __init__(self, *args: object, **kwargs: object) -> None:
                del args, kwargs

            def deploy(self) -> dict[str, object]:
                return {
                    "success": True,
                    "checklist": {"step": True},
                    "deployment_location": "/tmp/location",
                    "manifest": {"artifacts": {"core": "/tmp/core"}, "status": None},
                    "next_steps": ["next"],
                }

        monkeypatch.setattr(
            deployment_manager, "DeploymentManager", _FakeDeploymentManager
        )
        monkeypatch.setattr(
            builtins,
            "print",
            lambda *args, **kwargs: original_print(*args, file=captured, **kwargs),
        )
        deployment_manager.main()
        output = captured.getvalue()
        assert "Status: UNKNOWN" in output

    def test_full_module_main_block_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = io.StringIO()
        original_print = builtins.print

        class _FakeDeploymentManager:
            def __init__(self, *args: object, **kwargs: object) -> None:
                del args, kwargs

            def deploy(self) -> dict[str, object]:
                return {
                    "success": False,
                    "checklist": {},
                    "deployment_location": "/tmp/location",
                    "manifest": {},
                    "next_steps": [],
                }

        monkeypatch.setattr(
            deployment_manager, "DeploymentManager", _FakeDeploymentManager
        )
        monkeypatch.setattr(
            builtins,
            "print",
            lambda *args, **kwargs: original_print(*args, file=captured, **kwargs),
        )
        deployment_manager.main()
        output = captured.getvalue()
        assert "Deployment failed" in output

    def test_module_entrypoint_executes_main_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = io.StringIO()
        original_print = builtins.print
        original_build_class = builtins.__build_class__
        source_path = Path("packages/core/sdd_core/src/sdd_core/deployment_manager.py")
        source = source_path.read_text(encoding="utf-8")

        def _build_class(func, name, *args, **kwargs):
            built_class = original_build_class(func, name, *args, **kwargs)
            if name != "DeploymentManager":
                return built_class

            def _fake_init(self, *init_args: object, **init_kwargs: object) -> None:
                del self, init_args, init_kwargs

            def _fake_deploy(self) -> dict[str, object]:
                del self
                return {
                    "success": False,
                    "checklist": {},
                    "deployment_location": "/tmp/location",
                    "manifest": {},
                    "next_steps": [],
                }

            return type(
                "DeploymentManager",
                (),
                {"__init__": _fake_init, "deploy": _fake_deploy},
            )

        monkeypatch.setattr(builtins, "__build_class__", _build_class)
        monkeypatch.setattr(
            builtins,
            "print",
            lambda *args, **kwargs: original_print(*args, file=captured, **kwargs),
        )
        exec(
            compile(source, str(source_path), "exec"),
            {
                "__name__": "__main__",
                "__file__": str(source_path),
                "__builtins__": builtins.__dict__,
            },
        )
        output = captured.getvalue()
        assert "Deployment failed" in output
