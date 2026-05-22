"""
Phase 4-6 Generator for SDD Wizard v3

Phase 4: Load governance JSON + apply templates
Phase 5: Generate directory structure + organize by category + copy files
Phase 6: Validate output + create manifest

Output Structure (AI Agent Optimized):
.sdd/
├── source/                    (Unique source of truth for agent queries)
│   ├── mandates/
│   │   └── mandates.md       (Compiled, IA-FIRST optimized)
│   ├── guidelines/
│   │   ├── git.md
│   │   ├── testing.md
│   │   ├── naming.md
│   │   ├── docs.md
│   │   ├── style.md
│   │   └── performance.md
│   └── README.md             (Agent instructions)
├── runtime/
│   └── README.md             (Pre-cache instructions for agents)
└── metadata.json

.github/workflows/
└── sdd-validation.yml

.vscode/, .cursor/ (seedlings with references to .sdd/source)
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sdd_adapters import AdapterGenerator
from sdd_core.utils.environment import get_sdd_paths

from .phase4_governance_loader import GovernanceLoader
from .phase5_artifact_compiler import ArtifactCompiler
from .phase5_source_writer import SddSourceWriter
from .phase6_ide_deployer import IdeTemplateDeployer
from .phase6_output_validator import OutputValidator
from .phase6_seedlings_orchestrator import SeedlingsOrchestrator
from .wizard.models import Phase456RunResult


class Phase456Generator:
    """Orchestrate Phase 4-6: load governance → write source → compile → deploy → validate."""

    def __init__(
        self,
        repo_root: Path,
        output_base: Path,
        config: dict[str, Any],
        verbose: bool = False,
        selected_seedlings: set[str] | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths
        self.output_base = output_base
        self.config = config
        self.verbose = verbose
        self.selected_seedlings = selected_seedlings
        self._emit = emitter or print

        # Key paths
        self.dir = output_base / ".sdd"
        self.source_dir = self.dir / "source"
        self.runtime_dir = self.dir / "runtime"
        self.mandates_dir = self.source_dir / "mandates"
        self.guidelines_dir = self.source_dir / "guidelines"

        # Governance input paths
        self.governance_core_path = (
            paths["client_compiled"] / "source" / "governance-core.json"
        )
        if not self.governance_core_path.exists():
            self.governance_core_path = (
                output_base / ".sdd" / "source" / "governance-core.json"
            )

        self.governance_client = (
            paths["client_compiled"] / "source" / "governance-client.json"
        )
        if not self.governance_client.exists():
            self.governance_client = (
                output_base / ".sdd" / "source" / "governance-client.json"
            )

    def log(self, message: str) -> None:
        """Log."""
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def _load_governance(
        self,
    ) -> tuple[
        list[dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, list[dict[str, Any]]],
        Phase456RunResult,
    ]:
        """Load governance (Phase 4)."""
        loader = GovernanceLoader(
            governance_core_path=self.governance_core_path,
            governance_client_path=self.governance_client,
            verbose=self.verbose,
        )
        result: Phase456RunResult = {
            "success": False,
            "phase": "Phase 4-6",
            "output_path": str(self.dir),
            "mandates": 0,
            "guidelines": 0,
            "categories": [],
            "errors": [],
        }
        if not loader.load():
            result["errors"].append("Failed to load governance")
            return [], {}, {}, result
        return loader.mandates, loader.guidelines, loader.guidelines_by_category, result

    def _write_sources(
        self,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        """Write source files (Phase 5)."""
        writer = SddSourceWriter(
            output_base=self.output_base,
            source_dir=self.source_dir,
            runtime_dir=self.runtime_dir,
            mandates_dir=self.mandates_dir,
            guidelines_dir=self.guidelines_dir,
            mandates=mandates,
            guidelines=guidelines,
            guidelines_by_category=guidelines_by_category,
            config=self.config,
            verbose=self.verbose,
        )
        for step, label in [
            (writer.create_directories, "Failed to create directories"),
            (writer.generate_mandates_file, "Failed to generate mandates"),
            (writer.generate_guidelines_files, "Failed to generate guidelines"),
            (writer.generate_source_readme, "Failed to generate source README"),
            (writer.generate_runtime_readme, "Failed to generate runtime README"),
        ]:
            if not step():
                result["errors"].append(label)
                return False
        return True

    def _compile_artifacts(
        self,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
    ) -> tuple[bool, Any]:
        """Compile artifacts."""
        compiler = ArtifactCompiler(
            repo_root=self.repo_root,
            sdd_dir=self.dir,
            runtime_dir=self.runtime_dir,
            mandates=mandates,
            guidelines=guidelines,
            guidelines_by_category=guidelines_by_category,
            config=self.config,
            verbose=self.verbose,
            emitter=self._emit,
        )
        if not compiler.compile_artifacts():
            self.log("⚠️  Artifact compilation skipped or failed (non-critical)")
        if not compiler.generate_metadata():
            return False, compiler
        return True, compiler

    def _deploy_ide_templates(self, compiler: Any, result: Phase456RunResult) -> bool:
        """Deploy IDE templates (Phase 6)."""
        deployer = IdeTemplateDeployer(
            repo_root=self.repo_root,
            output_base=self.output_base,
            verbose=self.verbose,
        )
        if not deployer.copy_templates():
            result["errors"].append("Failed to copy templates")
            return False
        if not deployer.create_ide_templates():
            result["errors"].append("Failed to copy configuration templates")
            return False
        deployer.inject_bootstrap_metadata(
            fingerprint=compiler.governance_fingerprint,
            generated_at=compiler.generated_at,
            mandates_count=len(compiler.mandates),
        )
        deployer.populate_ide_rules(
            mandates=compiler.mandates,
            fingerprint=compiler.governance_fingerprint,
        )
        return True

    def _generate_seedlings(
        self,
        mandates: list[dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        """Generate intelligent seedlings."""
        seedlings = SeedlingsOrchestrator(
            output_base=self.output_base,
            mandates=mandates,
            guidelines_by_category=guidelines_by_category,
            config=self.config,
            governance_core_path=self.governance_core_path,
            paths=self.paths,
            verbose=self.verbose,
            emitter=self._emit,
        )
        if not seedlings.generate(selected=self.selected_seedlings):
            result["errors"].append("Failed to generate intelligent seedlings")
            return False
        return True

    def _generate_adapters(self) -> None:
        """Generate Level 2 adapters (skills/commands per agent)."""
        try:
            adapter_gen = AdapterGenerator()
            adapter_results = adapter_gen.generate(output_dir=self.output_base)
            for target, adapter_result in adapter_results.items():
                if adapter_result.success:
                    self._emit(
                        f"✅ Generated {len(adapter_result.files_written)} adapter files for {target}"
                    )
                else:
                    self._emit(
                        f"⚠️  Adapter generation for {target} had errors: {adapter_result.errors}"
                    )
        except Exception as e:
            self._emit(f"⚠️  Adapter generation failed (non-critical): {e}")

    def _validate_output(
        self,
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        """Validate output (Phase 6)."""
        validator = OutputValidator(
            output_base=self.output_base,
            sdd_dir=self.dir,
            source_dir=self.source_dir,
            runtime_dir=self.runtime_dir,
            mandates_dir=self.mandates_dir,
            guidelines_dir=self.guidelines_dir,
            guidelines_by_category=guidelines_by_category,
            verbose=self.verbose,
            emitter=self._emit,
        )
        valid, validation_result = validator.validate()
        if not valid:
            result["errors"].extend(validation_result["errors"])
            return False
        result["validation"] = validation_result["checks"]
        return True

    def run(self) -> Phase456RunResult:
        """Execute Phase 4-6 generation."""
        self._emit("\n🏗️  PHASE 4-6: Generate Project Structure")
        self._emit("=" * 70)

        # --- Phase 4: Load governance ---
        mandates, guidelines, guidelines_by_category, result = self._load_governance()
        if result["errors"]:
            return result

        result["mandates"] = len(mandates)
        result["guidelines"] = len(guidelines)
        result["categories"] = list(guidelines_by_category.keys())

        # --- Phase 5: Write source files ---
        if not self._write_sources(
            mandates, guidelines, guidelines_by_category, result
        ):
            return result

        # --- Compile artifacts ---
        success, compiler = self._compile_artifacts(
            mandates, guidelines, guidelines_by_category
        )
        if not success:
            result["errors"].append("Failed to generate metadata")
            return result

        # --- Phase 6: Deploy IDE templates ---
        if not self._deploy_ide_templates(compiler, result):
            return result

        # --- Generate intelligent seedlings ---
        if not self._generate_seedlings(mandates, guidelines_by_category, result):
            return result

        # --- Generate Level 2 Adapters ---
        self._generate_adapters()

        # --- Phase 6: Validate ---
        if not self._validate_output(guidelines_by_category, result):
            return result

        result["success"] = True

        self._emit("\n✅ Phase 4-6 Complete!")
        self._emit("\n📊 Structure Generated:")
        self._emit(f"   Mandates: {result['mandates']}")
        self._emit(f"   Guidelines: {result['guidelines']}")
        self._emit(f"   Categories: {', '.join(result['categories'])}")
        self._emit(f"\n📂 Location: {result['output_path']}")
        self._emit("\n🎯 Next Steps:")
        self._emit("   1. Review .sdd/source/ for governance organization")
        self._emit(
            "   2. Review .sdd/runtime/README.md for agent pre-cache instructions"
        )
        self._emit(
            "   3. Copy IDE templates from packages/features/sdd_integration/src/sdd_integration/templates/"
        )
        self._emit("   4. Commit to version control")

        return result


def run_phase_4_5_6_generator(
    repo_root: Path,
    output_base: Path,
    config: dict[str, Any],
    selected_seedlings: set[str] | None = None,
) -> Phase456RunResult:
    """Entry point for Phase 4-6 generator."""
    generator = Phase456Generator(
        repo_root,
        output_base,
        config,
        verbose=True,
        selected_seedlings=selected_seedlings,
    )
    return generator.run()
