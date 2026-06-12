"""Application boundaries for Phase 3 and Phase 4 interactive flows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from sdd_wizard.orchestration.wizard.messages import (
    phase3_completed_message,
    phase4_consolidation_failed_message,
    phase4_success_message,
)
from sdd_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult as Phase3CompileResult,
)
from sdd_wizard.orchestration.wizard.models import (
    InteractivePhase4GenerateResult as Phase4GenerateResult,
)
from sdd_wizard.orchestration.wizard.models import (
    build_interactive_phase3_result,
    build_interactive_phase4_result,
)

if TYPE_CHECKING:
    from sdd_wizard.orchestration.wizard.models import (
        FinalTemplateConsolidationResult,
        Phase456RunResult,
    )


class PhaseThreeContext(Protocol):
    """Narrow contract for Phase 3 compilation."""

    phase2_input_dir: Path
    client_compiled_dir: Path
    paths: dict[str, Any]

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""

    def print_header(self, title: str, icon: str = "🧙") -> None:
        """Print a formatted wizard header."""

    def phase_6_generate_seedlings(self, output_base: Path) -> bool:
        """Run Phase 6 seedling generation."""

    def _get_enforcement_label(self) -> str:
        """Return the enforcement label for operator messages."""


class PhaseThreeRuntime:
    """Boundary for staged template compilation and seedling follow-up."""

    def __init__(self, context: PhaseThreeContext) -> None:
        self._context = context

    def execute(self) -> Phase3CompileResult:
        """Compile staged templates and trigger seedling generation."""
        markdown_path = self._context.phase2_input_dir
        output_path = self._context.client_compiled_dir
        self._emit_paths(markdown_path, output_path)
        if not markdown_path.exists():
            return self._build_missing_templates(markdown_path, output_path)
        try:
            compiler = self._build_compiler(markdown_path, output_path)
            result = compiler.run()
            return self._handle_compiler_result(result, output_path)
        except Exception as exc:
            self._context._emit(f"\n❌ Error: {exc}")
            import traceback

            traceback.print_exc()
            return build_interactive_phase3_result(
                success=False,
                output_path=output_path,
                error=str(exc),
            )

    def _emit_paths(self, markdown_path: Path, output_path: Path) -> None:
        self._context._emit(f"  📂 Input (phase-2-input): {markdown_path}")
        self._context._emit(f"  📂 Output (client-compiled): {output_path}")

    def _build_missing_templates(
        self, markdown_path: Path, output_path: Path
    ) -> Phase3CompileResult:
        self._context._emit(f"\n❌ Templates not found: {markdown_path}")
        self._context._emit("\nYou need to:")
        self._context._emit("1. Run Phase 1 to generate templates")
        self._context._emit("2. Run Phase 2 to stage edited files into phase-2-input")
        self._context._emit("3. Run Phase 3 to compile")
        return build_interactive_phase3_result(
            success=False,
            output_path=output_path,
            error=f"Templates not found: {markdown_path}",
        )

    def _build_compiler(self, markdown_path: Path, output_path: Path) -> Any:
        from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler

        return Phase3Compiler(
            markdown_path, output_path, self._context.paths["root"], verbose=True
        )

    def _handle_compiler_result(
        self, result: dict[str, Any], output_path: Path
    ) -> Phase3CompileResult:
        if not result["success"]:
            self._context._emit(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
            return build_interactive_phase3_result(
                success=False,
                output_path=Path(str(result.get("output_path", str(output_path)))),
                mandates=int(result.get("mandates", 0)),
                guidelines=int(result.get("guidelines", 0)),
                files=list(result.get("files", [])),
                seedlings_success=False,
                error=str(result.get("error", "Unknown error")),
            )
        self._emit_compile_success(result)
        self._emit_seedling_header()
        seedlings_success = self._context.phase_6_generate_seedlings(output_path)
        if seedlings_success:
            self._emit_seedling_success()
        else:
            self._emit_seedling_warning(output_path)
        return build_interactive_phase3_result(
            success=True,
            output_path=Path(str(result.get("output_path", str(output_path)))),
            mandates=int(result.get("mandates", 0)),
            guidelines=int(result.get("guidelines", 0)),
            files=list(result.get("files", [])),
            seedlings_success=seedlings_success,
        )

    def _emit_compile_success(self, result: dict[str, Any]) -> None:
        self._context._emit(
            f"""
✅ PHASE 3 COMPLETE!

📊 COMPILATION RESULTS:
   ✓ Mandates: {result.get("mandates", 0)}
   ✓ Guidelines: {result.get("guidelines", 0)}
   ✓ Output Files: {", ".join(result.get("files", []))}
   ✓ Location: {result.get("output_path")}

"""
        )

    def _emit_seedling_header(self) -> None:
        self._context._emit("\n" + "=" * 70)
        self._context.print_header("PHASE 6: Generate Intelligent Seedlings", "🌱")
        self._context._emit("=" * 70)

    def _emit_seedling_success(self) -> None:
        self._context._emit(phase3_completed_message())
        self._context._emit(
            f"""
✓ Governance mandates are ready for agents
✓ Enforcement mode: {self._context._get_enforcement_label()}
✓ IDE integration configured
✓ CI/CD compliance hooks ready

ℹ️  For more details, see README.md in your project root.
"""
        )

    def _emit_seedling_warning(self, output_path: Path) -> None:
        self._context._emit(
            "\n⚠️  Phase 6 (Seedlings) had issues, but Phase 3 succeeded"
        )
        self._context._emit(
            f"   You can manually run Phase 6 or copy files from {output_path}"
        )


class PhaseFourContext(Protocol):
    """Narrow contract for Phase 4-6 project generation."""

    wizard_config_path: Path
    client_compiled_dir: Path
    final_template_dir: Path
    paths: dict[str, Any]

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""

    def _ask_seedling_selection(self) -> set[str] | None:
        """Return selected seedlings or None for all."""

    def _consolidate_final_template(self) -> FinalTemplateConsolidationResult:
        """Consolidate compiled artifacts into final-template."""

    def _cleanup_post_generation_artifacts(self) -> list[str]:
        """Cleanup temporary onboarding artifacts."""


class PhaseFourRuntime:
    """Boundary for final project generation and consolidation."""

    def __init__(self, context: PhaseFourContext) -> None:
        self._context = context

    def execute(self) -> Phase4GenerateResult:
        """Generate project structure from compiled governance."""
        try:
            config = self._load_config()
            if config is None:
                return build_interactive_phase4_result(
                    success=False,
                    error="Configuration not found; run Phase 1 first.",
                )
            if not self._context.client_compiled_dir.exists():
                self._context._emit("\n❌ Phase 3 output not found!")
                self._context._emit("You must run Phase 3 first to compile governance.")
                return build_interactive_phase4_result(
                    success=False,
                    error="Phase 3 output not found; run Phase 3 first.",
                )
            return self._run_generator(config)
        except Exception as exc:
            self._context._emit(f"\n❌ Error: {exc}")
            import traceback

            traceback.print_exc()
            return build_interactive_phase4_result(success=False, error=str(exc))

    def _load_config(self) -> dict[str, Any] | None:
        if not self._context.wizard_config_path.exists():
            self._context._emit("\n❌ Configuration not found!")
            self._context._emit("You must run Phase 1 first to set preferences.")
            return None
        with open(self._context.wizard_config_path, encoding="utf-8") as handle:
            config: dict[str, Any] = json.load(handle)
            return config

    def _run_generator(self, config: dict[str, Any]) -> Phase4GenerateResult:
        from sdd_wizard.orchestration.phase_4_5_6_generator import (
            run_phase_4_5_6_generator,
        )

        result = run_phase_4_5_6_generator(
            self._context.paths["root"],
            self._context.client_compiled_dir,
            config,
            self._context._ask_seedling_selection(),
        )
        if not result["success"]:
            return self._build_failure(result)
        return self._build_success(result)

    def _build_failure(self, result: Phase456RunResult) -> Phase4GenerateResult:
        self._context._emit("\n❌ Phase 4-6 generation failed!")
        for error in result.get("errors", []):
            self._context._emit(f"   • {error}")
        error_messages = result.get("errors", [])
        return build_interactive_phase4_result(
            success=False,
            error="; ".join(error_messages)
            if error_messages
            else "Phase 4-6 generation failed.",
        )

    def _build_success(self, result: Phase456RunResult) -> Phase4GenerateResult:
        consolidation = self._context._consolidate_final_template()
        if not consolidation["success"]:
            self._context._emit(
                phase4_consolidation_failed_message(
                    self._context.client_compiled_dir, self._context.final_template_dir
                )
            )
            return build_interactive_phase4_result(
                success=False,
                mandates=int(result.get("mandates", 0)),
                guidelines=int(result.get("guidelines", 0)),
                categories=list(result.get("categories", [])),
                consolidated=False,
                error="Failed to consolidate final template bundle.",
            )
        self._context._emit(
            phase4_success_message(
                int(result["mandates"]),
                int(result["guidelines"]),
                list(result["categories"]),
                self._context.final_template_dir,
            )
        )
        self._emit_cleanup()
        return build_interactive_phase4_result(
            success=True,
            mandates=int(result.get("mandates", 0)),
            guidelines=int(result.get("guidelines", 0)),
            categories=list(result.get("categories", [])),
            consolidated=True,
        )

    def _emit_cleanup(self) -> None:
        cleaned = self._context._cleanup_post_generation_artifacts()
        if not cleaned:
            return
        self._context._emit("  🧹 Cleaned temporary onboarding artifacts:")
        for relative_path in cleaned:
            self._context._emit(f"     - {relative_path}")
