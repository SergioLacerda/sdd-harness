"""
Unit tests for the extracted Phase 4-6 classes and seedling selection feature.

Coverage:
- GovernanceLoader: load, type inference, deduplication
- SddSourceWriter: directories, mandates, guidelines, READMEs
- ArtifactCompiler: metadata fingerprint, skips missing spec
- IdeTemplateDeployer: copy_templates, create_ide_templates, inject_bootstrap_metadata
- OutputValidator: pass / fail scenarios
- SeedlingsOrchestrator: delegates to IntelligentSeedlingsGenerator with selected
- IntelligentSeedlingsGenerator.generate_all: selected filtering
- interactive_mode._ask_seedling_selection: parse indices, names, 'all', empty
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from sdd_wizard.orchestration.intelligent_seedlings_generator import (
    IntelligentSeedlingsGenerator,
)
from sdd_wizard.orchestration.phase4_governance_loader import GovernanceLoader
from sdd_wizard.orchestration.phase5_artifact_compiler import ArtifactCompiler
from sdd_wizard.orchestration.phase5_source_writer import SddSourceWriter
from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer
from sdd_wizard.orchestration.phase6_output_validator import OutputValidator
from sdd_wizard.orchestration.phase6_seedlings_orchestrator import SeedlingsOrchestrator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patched_input(prompt: str) -> str:
    return input(prompt)


def _make_sdd_paths(tmp_path: Path) -> dict[str, Any]:
    client_compiled = tmp_path / "generated" / "client" / "compiled"
    return {
        "root": tmp_path,
        "client_compiled": client_compiled,
        "master_compiled": tmp_path / "generated" / "master" / "compiled",
    }


def _write_governance(
    tmp_path: Path,
    core_items: list[dict[str, Any]] | None = None,
    client_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paths = _make_sdd_paths(tmp_path)
    source = paths["client_compiled"] / "source"
    source.mkdir(parents=True, exist_ok=True)
    core = {"category": "CORE", "version": "3.0", "items": core_items or []}
    client = {"category": "CLIENT", "version": "3.0", "items": client_items or []}
    (source / "governance-core.json").write_text(json.dumps(core), encoding="utf-8")
    (source / "governance-client.json").write_text(json.dumps(client), encoding="utf-8")
    return paths


# ---------------------------------------------------------------------------
# GovernanceLoader
# ---------------------------------------------------------------------------


class TestGovernanceLoader:
    def test_load_returns_true_and_populates(self, tmp_path: Path) -> None:
        paths = _write_governance(
            tmp_path,
            core_items=[{"id": "M001", "title": "Clean Arch", "content": "x"}],
            client_items=[{"id": "G001", "category": "testing", "content": "y"}],
        )
        loader = GovernanceLoader(
            paths["client_compiled"] / "source" / "governance-core.json",
            paths["client_compiled"] / "source" / "governance-client.json",
        )
        assert loader.load() is True
        assert len(loader.mandates) == 1
        assert loader.mandates[0]["id"] == "M001"
        assert "G001" in loader.guidelines
        assert "testing" in loader.guidelines_by_category

    def test_load_returns_false_when_core_missing(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(
            tmp_path / "missing.json",
            tmp_path / "also-missing.json",
        )
        assert loader.load() is False

    def test_deduplicates_mandates(self, tmp_path: Path) -> None:
        duplicate = {"id": "M001", "type": "MANDATE", "title": "Dup", "content": "x"}
        paths = _write_governance(tmp_path, core_items=[duplicate, duplicate])
        loader = GovernanceLoader(
            paths["client_compiled"] / "source" / "governance-core.json",
            paths["client_compiled"] / "source" / "governance-client.json",
        )
        loader.load()
        assert len(loader.mandates) == 1

    def test_infers_type_from_id_prefix(self, tmp_path: Path) -> None:
        paths = _write_governance(
            tmp_path,
            core_items=[{"id": "M002", "content": "no type field"}],
            client_items=[
                {"id": "G002", "category": "git", "content": "no type field"}
            ],
        )
        loader = GovernanceLoader(
            paths["client_compiled"] / "source" / "governance-core.json",
            paths["client_compiled"] / "source" / "governance-client.json",
        )
        loader.load()
        assert any(m["id"] == "M002" for m in loader.mandates)
        assert "G002" in loader.guidelines

    def test_client_file_optional(self, tmp_path: Path) -> None:
        paths = _write_governance(
            tmp_path,
            core_items=[{"id": "M001", "type": "MANDATE", "content": "x"}],
        )
        loader = GovernanceLoader(
            paths["client_compiled"] / "source" / "governance-core.json",
            tmp_path / "nonexistent-client.json",
        )
        assert loader.load() is True
        assert len(loader.mandates) == 1


# ---------------------------------------------------------------------------
# SddSourceWriter
# ---------------------------------------------------------------------------


class TestSddSourceWriter:
    def _make_writer(
        self,
        tmp_path: Path,
        mandates: list[dict[str, Any]] | None = None,
        guidelines_by_category: dict[str, Any] | None = None,
    ) -> SddSourceWriter:
        sdd = tmp_path / ".sdd"
        source = sdd / "source"
        return SddSourceWriter(
            output_base=tmp_path,
            source_dir=source,
            runtime_dir=sdd / "runtime",
            mandates_dir=source / "mandates",
            guidelines_dir=source / "guidelines",
            mandates=mandates or [],
            guidelines={},
            guidelines_by_category=guidelines_by_category or {},
            config={"language": "Python", "adoption_level": "FULL"},
        )

    def test_create_directories(self, tmp_path: Path) -> None:
        writer = self._make_writer(tmp_path)
        assert writer.create_directories() is True
        assert (tmp_path / ".sdd" / "source" / "mandates").exists()
        assert (tmp_path / ".sdd" / "runtime").exists()
        assert (tmp_path / ".github" / "workflows").exists()

    def test_generate_mandates_file(self, tmp_path: Path) -> None:
        writer = self._make_writer(
            tmp_path,
            mandates=[{"id": "M001", "title": "Clean Arch", "content": "Do X"}],
        )
        writer.create_directories()
        assert writer.generate_mandates_file() is True
        content = (tmp_path / ".sdd" / "source" / "mandates" / "mandates.md").read_text(
            encoding="utf-8"
        )
        assert "M001" in content
        assert "Clean Arch" in content

    def test_generate_mandates_fallback_title(self, tmp_path: Path) -> None:
        writer = self._make_writer(
            tmp_path,
            mandates=[{"id": "M003"}],
        )
        writer.create_directories()
        writer.generate_mandates_file()
        content = (tmp_path / ".sdd" / "source" / "mandates" / "mandates.md").read_text(
            encoding="utf-8"
        )
        assert "Mandate M003" in content

    def test_generate_guidelines_files(self, tmp_path: Path) -> None:
        writer = self._make_writer(
            tmp_path,
            guidelines_by_category={
                "testing": [
                    {"id": "G001", "title": "Test All", "content": "Write tests"}
                ]
            },
        )
        writer.create_directories()
        assert writer.generate_guidelines_files() is True
        assert (tmp_path / ".sdd" / "source" / "guidelines" / "testing.md").exists()

    def test_generate_guidelines_fallback_title(self, tmp_path: Path) -> None:
        writer = self._make_writer(
            tmp_path,
            guidelines_by_category={"git": [{"id": "G010"}]},
        )
        writer.create_directories()
        writer.generate_guidelines_files()
        content = (tmp_path / ".sdd" / "source" / "guidelines" / "git.md").read_text(
            encoding="utf-8"
        )
        assert "Guideline G010" in content

    def test_generate_source_readme(self, tmp_path: Path) -> None:
        writer = self._make_writer(tmp_path)
        writer.create_directories()
        assert writer.generate_source_readme() is True
        assert (tmp_path / ".sdd" / "source" / "README.md").exists()

    def test_generate_runtime_readme(self, tmp_path: Path) -> None:
        writer = self._make_writer(tmp_path)
        writer.create_directories()
        assert writer.generate_runtime_readme() is True
        assert (tmp_path / ".sdd" / "runtime" / "README.md").exists()


# ---------------------------------------------------------------------------
# ArtifactCompiler
# ---------------------------------------------------------------------------


class TestArtifactCompiler:
    def _make_compiler(
        self,
        tmp_path: Path,
        mandates: list[dict[str, Any]] | None = None,
    ) -> ArtifactCompiler:
        sdd = tmp_path / ".sdd"
        sdd.mkdir(parents=True, exist_ok=True)
        runtime = sdd / "runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        return ArtifactCompiler(
            repo_root=tmp_path,
            sdd_dir=sdd,
            runtime_dir=runtime,
            mandates=mandates or [{"id": "M001", "title": "T", "content": "x"}],
            guidelines={},
            guidelines_by_category={},
            config={"language": "Python", "adoption_level": "FULL"},
        )

    def test_generate_metadata_creates_file(self, tmp_path: Path) -> None:
        compiler = self._make_compiler(tmp_path)
        assert compiler.generate_metadata() is True
        meta = json.loads(
            (tmp_path / ".sdd" / "metadata.json").read_text(encoding="utf-8")
        )
        assert meta["version"] == "3.0"
        assert "combined" in meta["fingerprints"]

    def test_generate_metadata_sets_fingerprint_attr(self, tmp_path: Path) -> None:
        compiler = self._make_compiler(tmp_path)
        compiler.generate_metadata()
        assert compiler.governance_fingerprint != "unknown"
        assert compiler.generated_at != "unknown"

    def test_compile_artifacts_skips_when_no_spec_dir(self, tmp_path: Path) -> None:
        compiler = self._make_compiler(tmp_path)
        # No spec/ or docs/spec/ exists — should return True (non-critical)
        assert compiler.compile_artifacts() is True

    def test_metadata_fingerprint_changes_with_different_mandates(
        self, tmp_path: Path
    ) -> None:
        sdd = tmp_path / ".sdd"
        sdd.mkdir()
        runtime = sdd / "runtime"
        runtime.mkdir()

        def make(mandates: list[dict[str, Any]]) -> str:
            c = ArtifactCompiler(tmp_path, sdd, runtime, mandates, {}, {}, {})
            c.generate_metadata()
            return c.governance_fingerprint

        fp1 = make([{"id": "M001", "title": "A", "content": "x"}])
        fp2 = make([{"id": "M001", "title": "B", "content": "y"}])
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# IdeTemplateDeployer
# ---------------------------------------------------------------------------


class TestIdeTemplateDeployer:
    def _make_template_tree(self, tmp_path: Path) -> Path:
        """Create a minimal sdd_integration template tree."""
        tpl = (
            tmp_path
            / "packages"
            / "features"
            / "sdd_integration"
            / "src"
            / "sdd_integration"
            / "templates"
        )
        for d in [
            ".github",
            ".vscode",
            ".claude",
            ".gemini",
            ".cursor/rules",
        ]:
            (tpl / d).mkdir(parents=True, exist_ok=True)
        (tpl / ".github" / "setup-precommit-hook.sh").write_text(
            "#!/bin/sh\n", encoding="utf-8"
        )
        (tpl / ".github" / "copilot-instructions.md").write_text(
            "copilot\n", encoding="utf-8"
        )
        (tpl / ".vscode" / "ai-rules.md").write_text("vscode\n", encoding="utf-8")
        (tpl / ".cursor" / "rules" / "spec.mdc").write_text(
            "cursor\n", encoding="utf-8"
        )
        (tpl / ".claude" / "claude-instructions.md").write_text(
            "claude\n", encoding="utf-8"
        )
        (tpl / ".gemini" / "gemini-instructions.md").write_text(
            "gemini\n", encoding="utf-8"
        )
        return tpl

    def test_create_ide_templates_copies_all_dirs(self, tmp_path: Path) -> None:
        self._make_template_tree(tmp_path)
        out = tmp_path / "project"
        deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=out)
        assert deployer.create_ide_templates() is True
        assert (out / ".github" / "copilot-instructions.md").exists()
        assert (out / ".vscode" / "ai-rules.md").exists()
        assert (out / ".cursor" / "rules" / "spec.mdc").exists()
        assert (out / ".claude" / "claude-instructions.md").exists()
        assert (out / ".gemini" / "gemini-instructions.md").exists()

    def test_create_ide_templates_fails_when_base_missing(self, tmp_path: Path) -> None:
        deployer = IdeTemplateDeployer(
            repo_root=tmp_path / "nonexistent", output_base=tmp_path / "out"
        )
        assert deployer.create_ide_templates() is False

    def test_inject_bootstrap_metadata_appends_footer(self, tmp_path: Path) -> None:
        out = tmp_path / "project"
        claude_dir = out / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "claude-instructions.md").write_text(
            "# Claude\n", encoding="utf-8"
        )

        deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=out)
        deployer.inject_bootstrap_metadata("abc123", "2026-01-01T00:00:00", 3)

        content = (claude_dir / "claude-instructions.md").read_text(encoding="utf-8")
        assert "sdd:bootstrap-metadata" in content
        assert "abc123" in content

    def test_inject_bootstrap_metadata_idempotent(self, tmp_path: Path) -> None:
        out = tmp_path / "project"
        (out / ".claude").mkdir(parents=True)
        f = out / ".claude" / "claude-instructions.md"
        f.write_text("# Claude\n", encoding="utf-8")

        deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=out)
        deployer.inject_bootstrap_metadata("fp1", "2026-01-01", 1)
        deployer.inject_bootstrap_metadata("fp1", "2026-01-01", 1)

        assert f.read_text(encoding="utf-8").count("sdd:bootstrap-metadata") == 1


# ---------------------------------------------------------------------------
# OutputValidator
# ---------------------------------------------------------------------------


class TestOutputValidator:
    def _make_validator(
        self,
        tmp_path: Path,
        guidelines_by_category: dict[str, Any] | None = None,
    ) -> OutputValidator:
        sdd = tmp_path / ".sdd"
        source = sdd / "source"
        return OutputValidator(
            output_base=tmp_path,
            sdd_dir=sdd,
            source_dir=source,
            runtime_dir=sdd / "runtime",
            mandates_dir=source / "mandates",
            guidelines_dir=source / "guidelines",
            guidelines_by_category=guidelines_by_category or {},
        )

    def test_validate_fails_when_dirs_missing(self, tmp_path: Path) -> None:
        validator = self._make_validator(tmp_path)
        valid, result = validator.validate()
        assert valid is False
        assert result["errors"]

    def test_validate_passes_when_all_required_present(self, tmp_path: Path) -> None:
        out = tmp_path / "project"
        sdd = out / ".sdd"
        source = sdd / "source"
        mandates_dir = source / "mandates"
        guidelines_dir = source / "guidelines"
        runtime_dir = sdd / "runtime"

        for d in [
            mandates_dir,
            guidelines_dir,
            runtime_dir,
            out / ".github" / "workflows",
        ]:
            d.mkdir(parents=True, exist_ok=True)

        (mandates_dir / "mandates.md").write_text("", encoding="utf-8")
        (runtime_dir / "README.md").write_text("", encoding="utf-8")
        (source / "README.md").write_text("", encoding="utf-8")
        (sdd / "metadata.json").write_text("{}", encoding="utf-8")
        (out / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")
        (out / ".vscode").mkdir()
        (out / ".vscode" / "ai-rules.md").write_text("", encoding="utf-8")
        (out / ".cursor" / "rules").mkdir(parents=True)
        (out / ".cursor" / "rules" / "spec.mdc").write_text("", encoding="utf-8")
        (out / ".claude").mkdir()
        (out / ".claude" / "claude-instructions.md").write_text("", encoding="utf-8")
        (out / ".gemini").mkdir()
        (out / ".gemini" / "gemini-instructions.md").write_text("", encoding="utf-8")

        validator = OutputValidator(
            out, sdd, source, runtime_dir, mandates_dir, guidelines_dir, {}
        )
        valid, result = validator.validate()
        assert valid is True
        assert not result["errors"]

    def test_validate_checks_guideline_files(self, tmp_path: Path) -> None:
        validator = self._make_validator(
            tmp_path, guidelines_by_category={"testing": []}
        )
        valid, result = validator.validate()
        assert valid is False
        assert any("testing" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# SeedlingsOrchestrator — selective generation
# ---------------------------------------------------------------------------


class TestSeedlingsOrchestrator:
    def test_generate_calls_generate_all_with_selected(self, tmp_path: Path) -> None:
        paths = _write_governance(tmp_path)
        orchestrator = SeedlingsOrchestrator(
            output_base=tmp_path / "out",
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=paths["client_compiled"]
            / "source"
            / "governance-core.json",
            paths=paths,
        )

        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            instance = MagicMock()
            instance.generate_all.return_value = True
            instance.get_summary.return_value = {
                "count": 1,
                "fingerprint": "fp",
                "mandates": [],
                "guidelines": [],
            }
            MockGen.return_value = instance

            result = orchestrator.generate(selected={"claude", "governance"})

        assert result is True
        instance.generate_all.assert_called_once_with(selected={"claude", "governance"})

    def test_generate_passes_none_when_no_selection(self, tmp_path: Path) -> None:
        paths = _write_governance(tmp_path)
        orchestrator = SeedlingsOrchestrator(
            output_base=tmp_path / "out",
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=paths["client_compiled"]
            / "source"
            / "governance-core.json",
            paths=paths,
        )

        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            instance = MagicMock()
            instance.generate_all.return_value = True
            instance.get_summary.return_value = {
                "count": 12,
                "fingerprint": "fp",
                "mandates": [],
                "guidelines": [],
            }
            MockGen.return_value = instance

            orchestrator.generate(selected=None)

        instance.generate_all.assert_called_once_with(selected=None)


# ---------------------------------------------------------------------------
# IntelligentSeedlingsGenerator.generate_all — selected filtering
# ---------------------------------------------------------------------------


class TestGenerateAllFiltering:
    def _make_generator(self, tmp_path: Path) -> IntelligentSeedlingsGenerator:
        paths = _write_governance(tmp_path)
        gov_path = paths["client_compiled"] / "source" / "governance-core.json"
        return IntelligentSeedlingsGenerator(
            output_base=tmp_path / "out",
            mandates=[{"id": "M001", "title": "T", "content": "x"}],
            guidelines_by_category={},
            config={
                "language": "Python",
                "adoption_level": "FULL",
                "enforcement_mode": "warn_mode",
            },
            governance_core_path=gov_path,
            verbose=False,
        )

    def test_generate_all_none_runs_all_generators(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)
        result = gen.generate_all(selected=None)
        assert result is True
        assert (tmp_path / "out" / ".sdd" / "seedlings").exists()

    def test_generate_all_selected_subset_creates_only_those(
        self, tmp_path: Path
    ) -> None:
        gen = self._make_generator(tmp_path)
        result = gen.generate_all(selected={"governance", "claude"})
        assert result is True
        seedlings_dir = tmp_path / "out" / ".sdd" / "seedlings"
        files = {f.name for f in seedlings_dir.iterdir()}
        assert "governance.seed.json" in files
        # claude now generates CLAUDE.md at the project root, not a seed JSON
        assert (tmp_path / "out" / "CLAUDE.md").exists()
        # Others should NOT be present
        assert "copilot.seed.json" not in files
        assert "gemini.seed.json" not in files
        assert "compliance.seed.json" not in files

    def test_generate_all_empty_set_generates_nothing(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)
        result = gen.generate_all(selected=set())
        assert result is True
        seedlings_dir = tmp_path / "out" / ".sdd" / "seedlings"
        files = list(seedlings_dir.iterdir())
        assert files == []


# ---------------------------------------------------------------------------
# _ask_seedling_selection (interactive_mode)
# ---------------------------------------------------------------------------


class TestAskSeedlingSelection:
    def _make_wizard(self, tmp_path: Path) -> Any:
        from unittest.mock import patch as _patch

        with _patch(
            "sdd_wizard.src.interactive_mode.get_sdd_paths",
            return_value={
                "root": tmp_path,
                "client_compiled": tmp_path / "gen" / "compiled",
                "client_build": tmp_path / "gen" / "build",
                "master_compiled": tmp_path / "gen" / "master",
            },
        ):
            from sdd_wizard.src.interactive_mode import InteractiveWizard

            return InteractiveWizard(repo_root=tmp_path, prompter=_patched_input)

    def test_returns_none_for_all(self, tmp_path: Path) -> None:
        wizard = self._make_wizard(tmp_path)
        with patch("builtins.input", return_value="all"):
            result = wizard._ask_seedling_selection()
        assert result is None

    def test_returns_none_for_blank(self, tmp_path: Path) -> None:
        wizard = self._make_wizard(tmp_path)
        with patch("builtins.input", return_value=""):
            result = wizard._ask_seedling_selection()
        assert result is None

    def test_parses_indices(self, tmp_path: Path) -> None:
        wizard = self._make_wizard(tmp_path)
        # indices 1=governance, 2=agent-prep, 4=claude
        with patch("builtins.input", return_value="1,2,4"):
            result = wizard._ask_seedling_selection()
        assert result == {"governance", "agent-prep", "claude"}

    def test_parses_key_names_directly(self, tmp_path: Path) -> None:
        wizard = self._make_wizard(tmp_path)
        with patch("builtins.input", return_value="claude,copilot"):
            result = wizard._ask_seedling_selection()
        assert result == {"claude", "copilot"}

    def test_returns_none_when_all_tokens_invalid(self, tmp_path: Path) -> None:
        wizard = self._make_wizard(tmp_path)
        with patch("builtins.input", return_value="99,999"):
            result = wizard._ask_seedling_selection()
        assert result is None

    def test_ignores_unknown_key_names(self, tmp_path: Path) -> None:
        wizard = self._make_wizard(tmp_path)
        with patch("builtins.input", return_value="claude,unknown-key"):
            result = wizard._ask_seedling_selection()
        assert result == {"claude"}


# ---------------------------------------------------------------------------
# Phase456Generator + run_phase_4_5_6_generator
# ---------------------------------------------------------------------------


class TestPhase456Generator:
    def _make_generator(
        self, tmp_path: Path, sdd_paths: dict[str, Any] | None = None
    ) -> Any:
        from sdd_wizard.orchestration.phase_4_5_6_generator import Phase456Generator

        paths = sdd_paths or _make_sdd_paths(tmp_path)
        with patch(
            "sdd_wizard.orchestration.phase_4_5_6_generator.get_sdd_paths",
            return_value=paths,
        ):
            return Phase456Generator(
                repo_root=tmp_path,
                output_base=tmp_path / "out",
                config={"language": "Python"},
                verbose=False,
            )

    def test_init_sets_paths(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)
        assert gen.output_base == tmp_path / "out"
        assert gen.dir == tmp_path / "out" / ".sdd"

    def test_run_returns_false_when_loader_fails(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)
        mock_loader = MagicMock()
        mock_loader.load.return_value = False
        with patch(
            "sdd_wizard.orchestration.phase_4_5_6_generator.GovernanceLoader",
            return_value=mock_loader,
        ):
            result = gen.run()
        assert result["success"] is False
        assert result["errors"]

    def test_run_returns_true_on_full_success(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)

        mock_loader = MagicMock()
        mock_loader.load.return_value = True
        mock_loader.mandates = [{"id": "M001"}]
        mock_loader.guidelines = []
        mock_loader.guidelines_by_category = {}

        mock_writer = MagicMock()
        mock_writer.create_directories.return_value = True
        mock_writer.generate_mandates_file.return_value = True
        mock_writer.generate_guidelines_files.return_value = True
        mock_writer.generate_source_readme.return_value = True
        mock_writer.generate_runtime_readme.return_value = True

        mock_compiler = MagicMock()
        mock_compiler.compile_artifacts.return_value = True
        mock_compiler.generate_metadata.return_value = True
        mock_compiler.governance_fingerprint = "abc"
        mock_compiler.generated_at = "2026-01-01T00:00:00"

        mock_deployer = MagicMock()
        mock_deployer.copy_templates.return_value = True
        mock_deployer.create_ide_templates.return_value = True

        mock_seedlings = MagicMock()
        mock_seedlings.generate.return_value = True

        mock_validator = MagicMock()
        mock_validator.validate.return_value = (True, {"checks": [], "errors": []})

        with (
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.GovernanceLoader",
                return_value=mock_loader,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.SddSourceWriter",
                return_value=mock_writer,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.ArtifactCompiler",
                return_value=mock_compiler,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.IdeTemplateDeployer",
                return_value=mock_deployer,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.SeedlingsOrchestrator",
                return_value=mock_seedlings,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.OutputValidator",
                return_value=mock_validator,
            ),
        ):
            result = gen.run()

        assert result["success"] is True
        assert result["mandates"] == 1

    def test_run_returns_false_when_writer_step_fails(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)

        mock_loader = MagicMock()
        mock_loader.load.return_value = True
        mock_loader.mandates = []
        mock_loader.guidelines = []
        mock_loader.guidelines_by_category = {}

        mock_writer = MagicMock()
        mock_writer.create_directories.return_value = False  # fail on first step

        with (
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.GovernanceLoader",
                return_value=mock_loader,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.SddSourceWriter",
                return_value=mock_writer,
            ),
        ):
            result = gen.run()

        assert result["success"] is False
        assert any("directories" in e.lower() for e in result["errors"])

    def test_run_returns_false_when_validator_fails(self, tmp_path: Path) -> None:
        gen = self._make_generator(tmp_path)

        mock_loader = MagicMock()
        mock_loader.load.return_value = True
        mock_loader.mandates = []
        mock_loader.guidelines = []
        mock_loader.guidelines_by_category = {}

        mock_writer = MagicMock()
        for attr in [
            "create_directories",
            "generate_mandates_file",
            "generate_guidelines_files",
            "generate_source_readme",
            "generate_runtime_readme",
        ]:
            getattr(mock_writer, attr).return_value = True

        mock_compiler = MagicMock()
        mock_compiler.compile_artifacts.return_value = True
        mock_compiler.generate_metadata.return_value = True
        mock_compiler.governance_fingerprint = "fp"
        mock_compiler.generated_at = "now"

        mock_deployer = MagicMock()
        mock_deployer.copy_templates.return_value = True
        mock_deployer.create_ide_templates.return_value = True

        mock_seedlings = MagicMock()
        mock_seedlings.generate.return_value = True

        mock_validator = MagicMock()
        mock_validator.validate.return_value = (
            False,
            {"checks": [], "errors": ["bad output"]},
        )

        with (
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.GovernanceLoader",
                return_value=mock_loader,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.SddSourceWriter",
                return_value=mock_writer,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.ArtifactCompiler",
                return_value=mock_compiler,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.IdeTemplateDeployer",
                return_value=mock_deployer,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.SeedlingsOrchestrator",
                return_value=mock_seedlings,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.OutputValidator",
                return_value=mock_validator,
            ),
        ):
            result = gen.run()

        assert result["success"] is False
        assert "bad output" in result["errors"]


class TestRunPhase456Generator:
    def test_delegates_to_phase456_generator(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_4_5_6_generator import (
            run_phase_4_5_6_generator,
        )

        paths = _make_sdd_paths(tmp_path)
        mock_instance = MagicMock()
        mock_instance.run.return_value = {"success": True, "mandates": 2, "errors": []}

        with (
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.get_sdd_paths",
                return_value=paths,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.Phase456Generator",
                return_value=mock_instance,
            ),
        ):
            result = run_phase_4_5_6_generator(
                tmp_path, tmp_path / "out", {"language": "Python"}
            )

        assert result["success"] is True
        mock_instance.run.assert_called_once()
