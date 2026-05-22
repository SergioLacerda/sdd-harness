"""Coverage tests for SDDIntegrator compile and metadata methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sdd_compiler.integrate import SDDIntegrator


def _make_integrator(tmp_path: Path) -> SDDIntegrator:
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
        return SDDIntegrator(repo_root=tmp_path)


def _write_sources(tmp_path: Path) -> tuple[Path, Path]:
    source_core = tmp_path / "docs" / "spec"
    source_core.mkdir(parents=True)
    mandate = source_core / "mandate.spec"
    guidelines = source_core / "guidelines.dsl"
    mandate.write_text("- [M001] **T** desc\n", encoding="utf-8")
    guidelines.write_text(
        "guideline G01 {\n  type: SOFT\n  title: x\n}\n", encoding="utf-8"
    )
    return mandate, guidelines


def _mock_runner_success(output_file: Path) -> MagicMock:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(b"\x53\x44\x44\x03" + b"\x00" * 20)
    result = MagicMock()
    result.success = True
    result.stdout = ""
    result.stderr = ""
    runner = MagicMock()
    runner.run.return_value = result
    return runner


def _mock_runner_failure() -> MagicMock:
    result = MagicMock()
    result.success = False
    result.stdout = ""
    result.stderr = "compilation error"
    runner = MagicMock()
    runner.run.return_value = result
    return runner


class TestCompileMandate:
    def test_success_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        output_file = (
            tmp_path / ".sdd" / "compiled" / "governance-core.compiled.msgpack"
        )
        with patch(
            "sdd_core.utils.process.SafeProcessRunner",
            return_value=_mock_runner_success(output_file),
        ):
            result = integrator.compile_mandate(force=True)
        assert result is True

    def test_failure_runner_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner",
            return_value=_mock_runner_failure(),
        ):
            result = integrator.compile_mandate(force=True)
        assert result is False

    def test_output_not_created_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.stderr = ""
        runner = MagicMock()
        runner.run.return_value = result_mock
        with patch("sdd_core.utils.process.SafeProcessRunner", return_value=runner):
            result = integrator.compile_mandate(force=True)
        assert result is False

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", side_effect=RuntimeError("boom")
        ):
            result = integrator.compile_mandate(force=True)
        assert result is False

    def test_cache_hit_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        with patch.object(
            integrator,
            "check_incremental_compilation",
            return_value={"mandate": False, "guidelines": False},
        ):
            result = integrator.compile_mandate(force=False)
        assert result is True


class TestCompileGuidelines:
    def test_success_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        output_file = (
            tmp_path
            / ".sdd"
            / "compiled"
            / "governance-client-template.compiled.msgpack"
        )
        with patch(
            "sdd_core.utils.process.SafeProcessRunner",
            return_value=_mock_runner_success(output_file),
        ):
            result = integrator.compile_guidelines(force=True)
        assert result is True

    def test_failure_runner_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner",
            return_value=_mock_runner_failure(),
        ):
            result = integrator.compile_guidelines(force=True)
        assert result is False

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", side_effect=RuntimeError("err")
        ):
            result = integrator.compile_guidelines(force=True)
        assert result is False

    def test_cache_hit_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        with patch.object(
            integrator,
            "check_incremental_compilation",
            return_value={"mandate": False, "guidelines": False},
        ):
            result = integrator.compile_guidelines(force=False)
        assert result is True


class TestGenerateMetadata:
    def test_success_creates_metadata_files(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        (tmp_path / ".sdd" / "compiled").mkdir(parents=True)
        result = integrator.generate_metadata()
        assert result is True
        assert (
            tmp_path / ".sdd" / "compiled" / "audit" / "metadata-core.json"
        ).exists()

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_integrator(tmp_path)
        # No source files → _resolve_source_file raises
        result = integrator.generate_metadata()
        assert result is False


class TestCheckIncrementalSuccess:
    def test_returns_needs_recompilation_when_artifacts_missing(
        self, tmp_path: Path
    ) -> None:
        integrator = _make_integrator(tmp_path)
        _write_sources(tmp_path)
        result = integrator.check_incremental_compilation()
        assert result["mandate"] is True  # artifacts don't exist yet
        assert result["guidelines"] is True
