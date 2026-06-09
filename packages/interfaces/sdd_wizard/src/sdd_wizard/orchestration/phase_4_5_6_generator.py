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


def _resolve_governance_inputs(
    repo_root: Path, paths: dict[str, Any], output_base: Path
) -> tuple[Path, Path]:
    """Resolve governance input files with .sdd-first precedence."""
    core_candidates = [
        repo_root / ".sdd" / "compiled" / "governance-core.json",
        repo_root / ".sdd" / "source" / "governance-core.json",
        paths["client_compiled"] / "source" / "governance-core.json",
        output_base / ".sdd" / "source" / "governance-core.json",
    ]
    client_candidates = [
        repo_root / ".sdd" / "compiled" / "governance-client.json",
        repo_root / ".sdd" / "source" / "governance-client.json",
        paths["client_compiled"] / "source" / "governance-client.json",
        output_base / ".sdd" / "source" / "governance-client.json",
    ]
    core_path = next((p for p in core_candidates if p.exists()), core_candidates[0])
    client_path = next(
        (p for p in client_candidates if p.exists()), client_candidates[0]
    )
    return core_path, client_path


def _load_governance(
    core_path: Path,
    client_path: Path,
    verbose: bool,
    sdd_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    Phase456RunResult,
]:
    """Load governance data (Phase 4)."""
    loader = GovernanceLoader(
        governance_core_path=core_path,
        governance_client_path=client_path,
        verbose=verbose,
    )
    result: Phase456RunResult = {
        "success": False,
        "phase": "Phase 4-6",
        "output_path": str(sdd_dir),
        "mandates": 0,
        "guidelines": 0,
        "categories": [],
        "errors": [],
    }
    if not loader.load():
        result["errors"].append("Failed to load governance")
        return [], {}, {}, result
    return loader.mandates, loader.guidelines, loader.guidelines_by_category, result


def _compile_artifacts(
    repo_root: Path,
    sdd_dir: Path,
    runtime_dir: Path,
    mandates: list[dict[str, Any]],
    guidelines: dict[str, dict[str, Any]],
    guidelines_by_category: dict[str, list[dict[str, Any]]],
    config: dict[str, Any],
    verbose: bool,
    emit: Callable[[str], None],
) -> tuple[bool, Any]:
    """Compile governance artifacts and generate metadata."""
    compiler = ArtifactCompiler(
        repo_root=repo_root,
        sdd_dir=sdd_dir,
        runtime_dir=runtime_dir,
        mandates=mandates,
        guidelines=guidelines,
        guidelines_by_category=guidelines_by_category,
        config=config,
        verbose=verbose,
        emitter=emit,
    )
    if not compiler.compile_artifacts() and verbose:
        emit("  ℹ️  ⚠️  Artifact compilation skipped or failed (non-critical)")
    if not compiler.generate_metadata():
        return False, compiler
    return True, compiler


def _deploy_ide_templates(
    repo_root: Path,
    output_base: Path,
    config: dict[str, Any],
    verbose: bool,
    compiler: Any,
    result: Phase456RunResult,
) -> bool:
    """Deploy IDE templates and inject bootstrap metadata (Phase 6)."""
    deployer = IdeTemplateDeployer(
        repo_root=repo_root,
        output_base=output_base,
        config=config,
        verbose=verbose,
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


def _validate_output(
    output_base: Path,
    guidelines_by_category: dict[str, list[dict[str, Any]]],
    config: dict[str, Any],
    verbose: bool,
    emit: Callable[[str], None],
    result: Phase456RunResult,
) -> bool:
    """Validate generated output structure (Phase 6)."""
    sdd_dir = output_base / ".sdd"
    source_dir = sdd_dir / "source"
    validator = OutputValidator(
        output_base=output_base,
        sdd_dir=sdd_dir,
        source_dir=source_dir,
        runtime_dir=sdd_dir / "runtime",
        mandates_dir=source_dir / "mandates",
        guidelines_dir=source_dir / "guidelines",
        guidelines_by_category=guidelines_by_category,
        config=config,
        verbose=verbose,
        emitter=emit,
    )
    valid, validation_result = validator.validate()
    if not valid:
        result["errors"].extend(validation_result["errors"])
        return False
    result["validation"] = validation_result["checks"]
    return True


def _generate_adapters(output_base: Path, emit: Callable[[str], None]) -> None:
    """Generate Level 2 adapters (skills/commands per agent)."""
    try:
        adapter_gen = AdapterGenerator()
        adapter_results = adapter_gen.generate(output_dir=output_base)
        for target, adapter_result in adapter_results.items():
            if adapter_result.success:
                emit(
                    f"✅ Generated {len(adapter_result.files_written)} adapter files for {target}"
                )
            else:
                emit(
                    f"⚠️  Adapter generation for {target} had errors: {adapter_result.errors}"
                )
    except Exception as e:
        emit(f"⚠️  Adapter generation failed (non-critical): {e}")


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

        self.dir = output_base / ".sdd"
        self.source_dir = self.dir / "source"
        self.runtime_dir = self.dir / "runtime"
        self.mandates_dir = self.source_dir / "mandates"
        self.guidelines_dir = self.source_dir / "guidelines"
        self.governance_core_path, self.governance_client = _resolve_governance_inputs(
            self.repo_root, self.paths, output_base
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
        return _load_governance(
            self.governance_core_path, self.governance_client, self.verbose, self.dir
        )

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
            (writer.generate_plugin_workspace, "Failed to generate plugin workspace"),
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
        return _compile_artifacts(
            self.repo_root,
            self.dir,
            self.runtime_dir,
            mandates,
            guidelines,
            guidelines_by_category,
            self.config,
            self.verbose,
            self._emit,
        )

    def _deploy_ide_templates(self, compiler: Any, result: Phase456RunResult) -> bool:
        """Deploy IDE templates (Phase 6)."""
        return _deploy_ide_templates(
            self.repo_root,
            self.output_base,
            self.config,
            self.verbose,
            compiler,
            result,
        )

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
        _generate_adapters(self.output_base, self._emit)

    def _validate_output(
        self,
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        """Validate output (Phase 6)."""
        return _validate_output(
            self.output_base,
            guidelines_by_category,
            self.config,
            self.verbose,
            self._emit,
            result,
        )

    def run(self) -> Phase456RunResult:
        """Execute Phase 4-6 generation."""
        self._emit("\n🏗️  PHASE 4-6: Generate Project Structure")
        self._emit("=" * 70)

        mandates, guidelines, guidelines_by_category, result = self._load_governance()
        if result["errors"]:
            return result

        result["mandates"] = len(mandates)
        result["guidelines"] = len(guidelines)
        result["categories"] = list(guidelines_by_category.keys())

        if not self._write_sources(
            mandates, guidelines, guidelines_by_category, result
        ):
            return result

        success, compiler = self._compile_artifacts(
            mandates, guidelines, guidelines_by_category
        )
        if not success:
            result["errors"].append("Failed to generate metadata")
            return result

        if not self._deploy_ide_templates(compiler, result):
            return result

        if not self._generate_seedlings(mandates, guidelines_by_category, result):
            return result

        self._generate_adapters()

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
