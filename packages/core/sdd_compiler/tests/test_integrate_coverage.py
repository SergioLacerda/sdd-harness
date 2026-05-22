"""Coverage tests for SDDIntegrator missing branches."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sdd_compiler.integrate import SDDIntegrator


def _make_integrator(tmp_path: Path) -> SDDIntegrator:
    messages: list[str] = []
    with patch("sdd_compiler.integrate.get_sdd_paths") as mp:
        mp.return_value = {
            "root": tmp_path,
            "source_spec": tmp_path / "docs" / "spec",
            "packages": tmp_path / "packages",
            "master_compiled": tmp_path / ".sdd" / "compiled",
            "master_build": tmp_path / ".sdd" / "build",
            "client_compiled": tmp_path / ".sdd" / "client",
            "client_build": tmp_path / ".sdd" / "client_build",
        }
        return SDDIntegrator(repo_root=tmp_path, emitter=messages.append)


class TestCheckIncrementalCompilation:
    def test_exception_returns_both_true(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        # No source files → _resolve_source_file raises FileNotFoundError
        result = integrator.check_incremental_compilation()
        assert result == {"mandate": True, "guidelines": True}


class TestAnalyzeSources:
    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        result = integrator.analyze_sources()
        assert result is False

    def test_success_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        # source_core = paths["source_spec"] = tmp_path / "docs" / "spec"
        source_core = tmp_path / "docs" / "spec"
        source_core.mkdir(parents=True)
        (source_core / "mandate.spec").write_text(
            "- [M001] **T** desc\n", encoding="utf-8"
        )
        (source_core / "guidelines.dsl").write_text(
            "guideline G01 { type: SOFT\n  title: x\n}\n", encoding="utf-8"
        )
        result = integrator.analyze_sources()
        assert result is True


class TestVerifyDeployment:
    def test_all_present_false_when_files_missing(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        result = integrator.verify_deployment()
        assert result["all_present"] is False

    def test_all_present_true_when_files_exist(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.compiled.msgpack").write_bytes(b"x")
        (compiled / "governance-client-template.compiled.msgpack").write_bytes(b"x")
        result = integrator.verify_deployment()
        assert result["all_present"] is True
        assert result["critical_count"] == 2


class TestRunDetailed:
    def test_run_detailed_fails_on_validate_paths(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        with patch.object(integrator, "validate_paths", return_value=False):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "validate_paths"

    def test_run_detailed_fails_on_analyze_sources(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        with (
            patch.object(integrator, "validate_paths", return_value=True),
            patch.object(integrator, "analyze_sources", return_value=False),
        ):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "analyze_sources"

    def test_run_detailed_fails_on_compile(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        with (
            patch.object(integrator, "validate_paths", return_value=True),
            patch.object(integrator, "analyze_sources", return_value=True),
            patch.object(integrator, "compile_mandate", return_value=False),
            patch.object(integrator, "compile_guidelines", return_value=False),
        ):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "compile"

    def test_run_detailed_fails_on_metadata(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        with (
            patch.object(integrator, "validate_paths", return_value=True),
            patch.object(integrator, "analyze_sources", return_value=True),
            patch.object(integrator, "compile_mandate", return_value=True),
            patch.object(integrator, "compile_guidelines", return_value=True),
            patch.object(integrator, "generate_metadata", return_value=False),
        ):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "metadata"

    def test_run_detailed_fails_on_verify_deployment(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        with (
            patch.object(integrator, "validate_paths", return_value=True),
            patch.object(integrator, "analyze_sources", return_value=True),
            patch.object(integrator, "compile_mandate", return_value=True),
            patch.object(integrator, "compile_guidelines", return_value=True),
            patch.object(integrator, "generate_metadata", return_value=True),
            patch.object(
                integrator,
                "verify_deployment",
                return_value={
                    "all_present": False,
                    "manifest": [],
                    "critical_count": 0,
                    "critical_required": 2,
                },
            ),
        ):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "verify_deployment"

    def test_run_detailed_success(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        verification = {
            "all_present": True,
            "manifest": [],
            "critical_count": 2,
            "critical_required": 2,
        }
        with (
            patch.object(integrator, "validate_paths", return_value=True),
            patch.object(integrator, "analyze_sources", return_value=True),
            patch.object(integrator, "compile_mandate", return_value=True),
            patch.object(integrator, "compile_guidelines", return_value=True),
            patch.object(integrator, "generate_metadata", return_value=True),
            patch.object(integrator, "verify_deployment", return_value=verification),
        ):
            result = integrator.run_detailed()
        assert result["ok"] is True
        assert result["phase"] == "completed"

    def test_run_returns_bool(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        with patch.object(
            integrator,
            "run_detailed",
            return_value={
                "ok": True,
                "phase": "done",
                "verification": None,
                "metrics": {},
            },
        ):
            assert integrator.run() is True
