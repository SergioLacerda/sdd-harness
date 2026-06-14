"""Top-level run() pipeline for Phase456Generator."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from ._phase456_governance_io import _load_governance
from ._phase456_pipeline_steps import (
    _compile_artifacts,
    _deploy_ide_templates,
    _generate_adapters,
    _validate_output,
)
from .wizard.models import Phase456RunResult


class _Phase456GeneratorProtocol(Protocol):
    """Structural type for Phase456Generator, avoiding a circular import with phase_4_5_6_generator."""

    repo_root: Path
    output_base: Path
    config: dict[str, Any]
    verbose: bool
    dir: Path
    runtime_dir: Path
    governance_core_path: Path
    governance_client: Path
    _emit: Callable[[str], None]

    def _write_sources(
        self,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        pass

    def _generate_seedlings(
        self,
        mandates: list[dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        pass


def run_phase456_pipeline(generator: _Phase456GeneratorProtocol) -> Phase456RunResult:
    """Execute Phase 4-6 generation."""
    generator._emit("\n🏗️  PHASE 4-6: Generate Project Structure")
    generator._emit("=" * 70)

    mandates, guidelines, guidelines_by_category, result = _load_governance(
        generator.governance_core_path,
        generator.governance_client,
        generator.verbose,
        generator.dir,
    )
    if result["errors"]:
        return result

    result["mandates"] = len(mandates)
    result["guidelines"] = len(guidelines)
    result["categories"] = list(guidelines_by_category.keys())

    if not generator._write_sources(
        mandates, guidelines, guidelines_by_category, result
    ):
        return result

    success, compiler = _compile_artifacts(
        generator.repo_root,
        generator.dir,
        generator.runtime_dir,
        mandates,
        guidelines,
        guidelines_by_category,
        generator.config,
        generator.verbose,
        generator._emit,
    )
    if not success:
        result["errors"].append("Failed to generate metadata")
        return result

    if not _deploy_ide_templates(
        generator.repo_root,
        generator.output_base,
        generator.config,
        generator.verbose,
        compiler,
        result,
    ):
        return result

    if not generator._generate_seedlings(mandates, guidelines_by_category, result):
        return result

    _generate_adapters(generator.output_base, generator._emit)

    if not _validate_output(
        generator.output_base,
        guidelines_by_category,
        generator.config,
        generator.verbose,
        generator._emit,
        result,
    ):
        return result

    result["success"] = True

    generator._emit("\n✅ Phase 4-6 Complete!")
    generator._emit("\n📊 Structure Generated:")
    generator._emit(f"   Mandates: {result['mandates']}")
    generator._emit(f"   Guidelines: {result['guidelines']}")
    generator._emit(f"   Categories: {', '.join(result['categories'])}")
    generator._emit(f"\n📂 Location: {result['output_path']}")
    generator._emit("\n🎯 Next Steps:")
    generator._emit("   1. Review .sdd/source/ for governance organization")
    generator._emit(
        "   2. Review .sdd/runtime/README.md for agent pre-cache instructions"
    )
    generator._emit(
        "   3. Copy IDE templates from packages/features/sdd_integration/src/sdd_integration/templates/"
    )
    generator._emit("   4. Commit to version control")

    return result
