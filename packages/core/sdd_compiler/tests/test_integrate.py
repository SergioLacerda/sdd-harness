"""Unit tests for SDDIntegrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_compiler.integrate import SDDIntegrator

pytestmark = pytest.mark.unit


class TestSDDIntegratorInit:
    """Tests for SDDIntegrator initialization."""

    def test_init_with_default_paths(self) -> None:
        """Should initialize with default SDD paths."""
        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp/root"),
                "source_spec": Path("/tmp/root/docs/spec"),
                "packages": Path("/tmp/root/packages"),
                "master_compiled": Path("/tmp/root/.sdd/compiled"),
            }
            integrator = SDDIntegrator()
            assert integrator.repo == Path("/tmp/root")
            assert integrator.source_core == Path("/tmp/root/docs/spec")

    def test_init_with_custom_repo_root(self) -> None:
        """Should accept custom repository root."""
        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/default"),
                "source_spec": Path("/default/docs/spec"),
                "packages": Path("/default/packages"),
                "master_compiled": Path("/default/.sdd/compiled"),
            }
            integrator = SDDIntegrator(repo_root=Path("/custom"))
            assert integrator.repo == Path("/custom")

    def test_init_with_custom_emitter(self) -> None:
        """Should accept custom emitter callback."""
        emitter = MagicMock()
        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "source_spec": Path("/tmp/docs/spec"),
                "packages": Path("/tmp/packages"),
                "master_compiled": Path("/tmp/.sdd/compiled"),
            }
            integrator = SDDIntegrator(emitter=emitter)
            assert integrator._emitter == emitter

    def test_init_metrics_structure(self) -> None:
        """Should initialize with proper metrics structure."""
        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "source_spec": Path("/tmp/docs/spec"),
                "packages": Path("/tmp/packages"),
                "master_compiled": Path("/tmp/.sdd/compiled"),
            }
            integrator = SDDIntegrator()
            assert "source" in integrator.metrics
            assert "compilation" in integrator.metrics
            assert "deployment" in integrator.metrics


class TestSDDIntegratorEmit:
    """Tests for emit functionality."""

    def test_emit_calls_emitter_when_provided(self) -> None:
        """_emit() should call the emitter callback."""
        emitter = MagicMock()
        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "source_spec": Path("/tmp/docs/spec"),
                "packages": Path("/tmp/packages"),
                "master_compiled": Path("/tmp/.sdd/compiled"),
            }
            integrator = SDDIntegrator(emitter=emitter)
            integrator._emit("test message")
            emitter.assert_called_once_with("test message")

    def test_emit_uses_print_by_default(self) -> None:
        """_emit() should use print by default."""
        with (
            patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths,
            patch("builtins.print"),
        ):
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "source_spec": Path("/tmp/docs/spec"),
                "packages": Path("/tmp/packages"),
                "master_compiled": Path("/tmp/.sdd/compiled"),
            }
            integrator = SDDIntegrator(emitter=None)
            integrator._emit("test message")
            # When emitter is None, it defaults to print
            assert integrator._emitter is not None


class TestSDDIntegratorFileHash:
    """Tests for file hashing utility."""

    def test_file_hash_returns_hash(self, tmp_path: Path) -> None:
        """_file_hash() should return file hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        hash_val = SDDIntegrator._file_hash(test_file)
        assert isinstance(hash_val, str)
        assert len(hash_val) > 0

    def test_file_hash_different_for_different_files(self, tmp_path: Path) -> None:
        """Different files should have different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1", encoding="utf-8")
        file2.write_text("content2", encoding="utf-8")

        hash1 = SDDIntegrator._file_hash(file1)
        hash2 = SDDIntegrator._file_hash(file2)
        assert hash1 != hash2

    def test_file_hash_truncation(self, tmp_path: Path) -> None:
        """_file_hash() should truncate to specified length."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        hash_val = SDDIntegrator._file_hash(test_file, truncate=4)
        assert len(hash_val) == 4


class TestSDDIntegratorCountItems:
    """Tests for item counting utility."""

    def test_count_items_finds_patterns(self) -> None:
        """_count_items() should count matching patterns."""
        text = "mandate M001 {}\nmandate M002 {}\nmandate M003 {}"
        pattern = r"mandate\s+M\d+"
        count = SDDIntegrator._count_items(text, pattern)
        assert count == 3

    def test_count_items_empty_text(self) -> None:
        """_count_items() should return 0 for empty text."""
        count = SDDIntegrator._count_items("", r"mandate")
        assert count == 0

    def test_count_items_no_matches(self) -> None:
        """_count_items() should return 0 when pattern not found."""
        text = "some text without mandates"
        count = SDDIntegrator._count_items(text, r"mandate\s+M\d+")
        assert count == 0


class TestSDDIntegratorResolveSourceFile:
    """Tests for source file resolution."""

    def test_resolve_source_file_first_extension(self, tmp_path: Path) -> None:
        """Should resolve file with first matching extension."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        mandate_file = source_dir / "mandate.spec"
        mandate_file.write_text("test", encoding="utf-8")

        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": source_dir,
                "packages": tmp_path / "packages",
                "master_compiled": tmp_path / "compiled",
            }
            integrator = SDDIntegrator()
            resolved = integrator._resolve_source_file("mandate", (".spec", ".md"))
            assert resolved == mandate_file

    def test_resolve_source_file_fallback_extension(self, tmp_path: Path) -> None:
        """Should fallback to next extension if first doesn't exist."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        mandate_file = source_dir / "mandate.md"
        mandate_file.write_text("test", encoding="utf-8")

        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": source_dir,
                "packages": tmp_path / "packages",
                "master_compiled": tmp_path / "compiled",
            }
            integrator = SDDIntegrator()
            resolved = integrator._resolve_source_file("mandate", (".spec", ".md"))
            assert resolved == mandate_file

    def test_resolve_source_file_not_found(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError when file not found."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": source_dir,
                "packages": tmp_path / "packages",
                "master_compiled": tmp_path / "compiled",
            }
            integrator = SDDIntegrator()
            with pytest.raises(FileNotFoundError):
                integrator._resolve_source_file("nonexistent", (".spec", ".md"))


class TestSDDIntegratorValidatePaths:
    """Tests for path validation."""

    def test_validate_paths_missing_mandate_source(self, tmp_path: Path) -> None:
        """validate_paths() should fail when mandate source missing."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": source_dir,
                "packages": tmp_path / "packages",
                "master_compiled": tmp_path / "compiled",
            }
            integrator = SDDIntegrator()
            result = integrator.validate_paths()
            assert result is False

    def test_validate_paths_with_all_required_files(self, tmp_path: Path) -> None:
        """validate_paths() should succeed with all required files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "mandate.spec").write_text("test", encoding="utf-8")
        (source_dir / "guidelines.dsl").write_text("test", encoding="utf-8")

        compiler_dir = (
            tmp_path / "packages" / "core" / "sdd_compiler" / "src" / "sdd_compiler"
        )
        compiler_dir.mkdir(parents=True)
        (compiler_dir / "dsl_compiler.py").write_text("test", encoding="utf-8")

        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)

        with patch("sdd_compiler.integrate.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": source_dir,
                "packages": tmp_path / "packages",
                "master_compiled": compiled_dir,
            }
            integrator = SDDIntegrator()
            result = integrator.validate_paths()
            assert result is True


# ---------------------------------------------------------------------------
# Self-sufficiency: all coverage needed when this file runs in isolation
# ---------------------------------------------------------------------------


def _make_int(tmp_path: Path) -> SDDIntegrator:
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


class TestValidatePathsMissingRequired:
    def test_missing_dsl_compiler_returns_false(self, tmp_path: Path) -> None:
        """validate_paths returns False when sources exist but dsl_compiler.py is absent."""
        integrator = _make_int(tmp_path)
        source_core = tmp_path / "docs" / "spec"
        source_core.mkdir(parents=True)
        (source_core / "mandate.spec").write_text("x", encoding="utf-8")
        (source_core / "guidelines.dsl").write_text("x", encoding="utf-8")
        # compiled dir exists but dsl_compiler.py does NOT → missing list populated
        (tmp_path / ".sdd" / "compiled").mkdir(parents=True)
        result = integrator.validate_paths()
        assert result is False


class TestCheckIncrementalCompilation:
    def test_exception_returns_both_true(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        result = integrator.check_incremental_compilation()
        assert result == {"mandate": True, "guidelines": True}

    def test_returns_needs_recompilation_when_artifacts_missing(
        self, tmp_path: Path
    ) -> None:
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        result = integrator.check_incremental_compilation()
        assert result["mandate"] is True
        assert result["guidelines"] is True


class TestAnalyzeSources:
    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        result = integrator.analyze_sources()
        assert result is False

    def test_success_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        result = integrator.analyze_sources()
        assert result is True


class TestCompileMandate:
    def test_success_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner",
            return_value=_mock_runner_failure(),
        ):
            result = integrator.compile_mandate(force=True)
        assert result is False

    def test_output_not_created_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", side_effect=RuntimeError("boom")
        ):
            result = integrator.compile_mandate(force=True)
        assert result is False

    def test_cache_hit_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner",
            return_value=_mock_runner_failure(),
        ):
            result = integrator.compile_guidelines(force=True)
        assert result is False

    def test_output_not_created_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.stderr = ""
        runner = MagicMock()
        runner.run.return_value = result_mock
        with patch("sdd_core.utils.process.SafeProcessRunner", return_value=runner):
            result = integrator.compile_guidelines(force=True)
        assert result is False

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", side_effect=RuntimeError("err")
        ):
            result = integrator.compile_guidelines(force=True)
        assert result is False

    def test_cache_hit_returns_true(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
        _write_sources(tmp_path)
        (tmp_path / ".sdd" / "compiled").mkdir(parents=True)
        result = integrator.generate_metadata()
        assert result is True
        assert (
            tmp_path / ".sdd" / "compiled" / "audit" / "metadata-core.json"
        ).exists()

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        result = integrator.generate_metadata()
        assert result is False


class TestVerifyDeployment:
    def test_all_present_false_when_files_missing(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        result = integrator.verify_deployment()
        assert result["all_present"] is False

    def test_all_present_true_when_files_exist(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.compiled.msgpack").write_bytes(b"x")
        (compiled / "governance-client-template.compiled.msgpack").write_bytes(b"x")
        result = integrator.verify_deployment()
        assert result["all_present"] is True
        assert result["critical_count"] == 2


class TestRunDetailed:
    def test_run_detailed_fails_on_validate_paths(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        with patch.object(integrator, "validate_paths", return_value=False):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "validate_paths"

    def test_run_detailed_fails_on_analyze_sources(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
        with (
            patch.object(integrator, "validate_paths", return_value=True),
            patch.object(integrator, "analyze_sources", return_value=False),
        ):
            result = integrator.run_detailed()
        assert result["ok"] is False
        assert result["phase"] == "analyze_sources"

    def test_run_detailed_fails_on_compile(self, tmp_path: Path) -> None:
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
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
        integrator = _make_int(tmp_path)
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
