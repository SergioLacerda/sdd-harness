"""Unit tests for sdd_core.governance_orchestrator.GovernanceOrchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_orchestrator(tmp_path: Path) -> Any:
    """Create GovernanceOrchestrator with paths pointing to tmp_path."""
    from sdd_core.governance_orchestrator import GovernanceOrchestrator

    mock_paths = {
        "root": tmp_path,
        "source_spec": tmp_path / "docs_meta",
        "master_compiled": tmp_path / "master" / "compiled",
        "master_build": tmp_path / "master" / "build",
        "client_compiled": tmp_path / "client" / "compiled",
        "client_build": tmp_path / "client" / "build",
    }

    with patch(
        "sdd_core.governance_orchestrator.get_sdd_paths", return_value=mock_paths
    ):
        orchestrator = GovernanceOrchestrator(
            repo_root=str(tmp_path),
            spec_path=str(tmp_path / "docs_meta"),
            compiled_dir=str(tmp_path / "master" / "compiled"),
        )
    return orchestrator


class TestGovernanceOrchestratorInit:
    def test_directories_created_on_init(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        assert orch.compiled_dir.exists()
        assert orch.build_dir.exists()

    def test_spec_and_compiled_dir_set(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        assert orch.spec == tmp_path / "docs_meta"
        assert orch.compiled_dir == tmp_path / "master" / "compiled"


class TestHasSourceSpecs:
    def test_returns_false_when_no_spec_files(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        assert bootstrapper.has_source_specs() is False

    def test_returns_true_with_mandate_spec(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)
        (orch.spec / "mandate.md").write_text("mandate M001 {}", encoding="utf-8")
        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_returns_true_with_mandate_md(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)
        (orch.spec / "mandate.md").write_text("# mandates", encoding="utf-8")
        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        assert bootstrapper.has_source_specs() is True


class TestBootstrapSourceSpecsFromMarkdown:
    def test_no_docs_dir_does_nothing(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)
        # Should not raise even without docs/
        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()

    def test_creates_mandate_spec_from_markdown(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)

        # Canonical files with **ID:** declarations are the authoritative source
        canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "core" / "mandates"
        canonical_dir.mkdir(parents=True)
        (canonical_dir / "M001_ARCH.md").write_text(
            "# Mandate: Clean Architecture\n\n**ID:** M001\n", encoding="utf-8"
        )
        (canonical_dir / "M002_TDD.md").write_text(
            "# Mandate: Test-Driven Development\n\n**ID:** M002\n", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        mandate_file = orch.spec / "mandate.md"
        assert mandate_file.exists()
        content = mandate_file.read_text(encoding="utf-8")
        assert "M001" in content
        assert "M002" in content

    def test_does_not_overwrite_existing_mandate_spec(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)

        # Pre-existing mandate spec
        existing_content = "mandate M999 {}"
        (orch.spec / "mandate.md").write_text(existing_content, encoding="utf-8")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "doc.md").write_text("M001 M002", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        # Should not be overwritten
        assert (orch.spec / "mandate.md").read_text(
            encoding="utf-8"
        ) == existing_content


class TestGetDeploymentSummary:
    def test_returns_dict_with_expected_keys(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        summary = orch.get_deployment_summary()
        assert "status" in summary
        assert "artifacts" in summary
        assert "next_step" in summary

    def test_artifacts_contain_expected_files(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        summary = orch.get_deployment_summary()
        artifacts = summary["artifacts"]
        assert "core_msgpack" in artifacts
        assert "client_msgpack" in artifacts
        assert "core_metadata" in artifacts
        assert "client_metadata" in artifacts


class TestValidateFullPipeline:
    def test_all_checks_pass(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        combined: dict[str, Any] = {
            "phase_1": {
                "success": True,
                "core_fingerprint": "fp1_abc",
                "client_fingerprint": "fp2_def",
                "core_item_count": 3,
                "client_item_count": 1,
            },
            "phase_2": {
                "success": True,
                "client_fingerprint": "fp2_def",
                "core_fingerprint_salt": "fp1_abc",
            },
        }
        result = orch._validate_full_pipeline(combined)
        assert result is True

    def test_fails_when_phase1_not_success(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        combined: dict[str, Any] = {
            "phase_1": {"success": False, "core_item_count": 0, "client_item_count": 0},
            "phase_2": {"success": False},
        }
        result = orch._validate_full_pipeline(combined)
        assert result is False

    def test_fails_when_core_item_count_is_zero(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        combined: dict[str, Any] = {
            "phase_1": {
                "success": True,
                "core_fingerprint": "fp1",
                "client_fingerprint": "fp2",
                "core_item_count": 0,
                "client_item_count": 0,
            },
            "phase_2": {
                "success": True,
                "client_fingerprint": "fp2",
                "core_fingerprint_salt": "fp1",
            },
        }
        result = orch._validate_full_pipeline(combined)
        assert result is False


class TestRunPhase1:
    def test_returns_success_false_when_no_spec(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        # No spec files → PipelineBuilder will fail
        mock_builder = MagicMock()
        mock_builder.build.side_effect = RuntimeError("No spec found")

        with patch(
            "sdd_core.governance_orchestrator.PipelineBuilder",
            return_value=mock_builder,
        ):
            result = orch._run_phase_1()
        assert result["success"] is False


class TestBootstrapSourceSpecsFromMarkdown2:
    def test_creates_spec_from_markdown_ids(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        # orch.spec points to tmp_path / "docs_meta" — create it
        orch.spec.mkdir(parents=True, exist_ok=True)
        # Canonical files drive mandate discovery
        canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "core" / "mandates"
        canonical_dir.mkdir(parents=True)
        (canonical_dir / "M001_ARCH.md").write_text(
            "# Mandate: Architecture\n\n**ID:** M001\n", encoding="utf-8"
        )
        (canonical_dir / "M002_TDD.md").write_text(
            "# Mandate: TDD\n\n**ID:** M002\n", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        assert (orch.spec / "mandate.md").exists()

    def test_skips_when_no_docs_dir(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        # No docs/ dir → should return without error
        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        assert not (orch.spec / "mandate.md").exists()

    def test_skips_when_no_mandate_ids_found(self, tmp_path: Path) -> None:
        from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "no_ids.md").write_text(
            "No mandate IDs here, just text.", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        assert not (orch.spec / "mandate.md").exists()


class TestRunPhase2:
    def test_returns_false_when_validation_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {"success": True}
        mock_compiler.validate_compilation.return_value = False

        with patch(
            "sdd_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()
        assert result["success"] is False

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        mock_compiler = MagicMock()
        mock_compiler.compile.side_effect = RuntimeError("compile error")

        with patch(
            "sdd_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()
        assert result["success"] is False

    def test_publishes_canonical_artifacts_to_sdd_compiled(
        self, tmp_path: Path
    ) -> None:
        orch = _make_orchestrator(tmp_path)
        orch.build_dir.mkdir(parents=True, exist_ok=True)
        orch.compiled_dir.mkdir(parents=True, exist_ok=True)
        (orch.build_dir / "governance-core.json").write_text(
            '{"fingerprint":"abc","items":[]}', encoding="utf-8"
        )
        (orch.build_dir / "governance-client.json").write_text(
            '{"fingerprint":"def","fingerprint_core_salt":"abc","items":[]}',
            encoding="utf-8",
        )
        (orch.compiled_dir / "governance-core.compiled.msgpack").write_bytes(b"core")
        (orch.compiled_dir / "governance-client-template.compiled.msgpack").write_bytes(
            b"client"
        )
        audit_dir = orch.compiled_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        (audit_dir / "metadata-core.json").write_text("{}", encoding="utf-8")
        (audit_dir / "metadata-client-template.json").write_text("{}", encoding="utf-8")
        (audit_dir / "governance-core.json").write_text(
            '{"fingerprint":"abc","items":[]}', encoding="utf-8"
        )
        (audit_dir / "governance-client.json").write_text(
            '{"fingerprint":"def","items":[]}', encoding="utf-8"
        )

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "core_msgpack_file": str(
                orch.compiled_dir / "governance-core.compiled.msgpack"
            ),
            "client_msgpack_file": str(
                orch.compiled_dir / "governance-client-template.compiled.msgpack"
            ),
            "core_fingerprint_salt": "abc",
            "client_fingerprint": "def",
        }
        mock_compiler.validate_compilation.return_value = True

        with patch(
            "sdd_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()

        assert result["success"] is True
        assert (tmp_path / ".sdd" / "compiled" / "governance-core.json").exists()
        assert (tmp_path / ".sdd" / "compiled" / "governance-client.json").exists()
        assert (tmp_path / ".sdd" / "compiled" / "metadata-core.json").exists()
        assert (
            tmp_path / ".sdd" / "compiled" / "metadata-client-template.json"
        ).exists()


class TestRunFullPipeline:
    def test_returns_false_when_phase2_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        phase1_ok = {
            "success": True,
            "core_item_count": 1,
            "client_item_count": 0,
            "core_fingerprint": "fp1",
            "client_fingerprint": "fp2",
        }
        phase2_fail = {"success": False, "error": "Phase 2 failed"}

        with (
            patch.object(orch, "_run_phase_1", return_value=phase1_ok),
            patch.object(orch, "_run_phase_2", return_value=phase2_fail),
        ):
            result = orch.run_full_pipeline()

        assert result["full_pipeline_success"] is False
        assert result["phase_2"] == phase2_fail
