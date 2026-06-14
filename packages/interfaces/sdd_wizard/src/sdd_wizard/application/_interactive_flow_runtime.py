"""Application boundary for top-level phase dispatch."""

from __future__ import annotations

from typing import Protocol

from sdd_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult,
    InteractivePhase4GenerateResult,
    Phase1GenerateResult,
    Phase2StageResult,
)


class InteractiveFlowContext(Protocol):
    """Narrow contract for menu dispatch of the interactive wizard."""

    def show_phase_menu(self) -> str:
        """Return the selected phase key."""

    def phase_1_generate_templates(self) -> Phase1GenerateResult:
        """Run Phase 1."""

    def phase_2_show_instructions(self) -> Phase2StageResult:
        """Run Phase 2."""

    def phase_3_compile_templates(self) -> InteractivePhase3CompileResult:
        """Run Phase 3."""

    def phase_4_generate_project(self) -> InteractivePhase4GenerateResult:
        """Run Phase 4."""

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""


class InteractiveFlowRuntime:
    """Application boundary for top-level phase dispatch."""

    def __init__(self, context: InteractiveFlowContext) -> None:
        self._context = context

    def execute(self) -> bool:
        """Route the chosen phase and translate wizard exceptions."""
        try:
            return self._dispatch(self._context.show_phase_menu())
        except KeyboardInterrupt:
            self._context._emit("\n\n❌ Wizard cancelled by user")
            return False
        except Exception as exc:
            self._context._emit(f"\n❌ Error: {exc}")
            import traceback

            traceback.print_exc()
            return False

    def _dispatch(self, choice: str) -> bool:
        if choice == "1":
            return bool(self._context.phase_1_generate_templates()["success"])
        if choice == "2":
            return bool(self._context.phase_2_show_instructions()["success"])
        if choice == "3":
            return bool(self._context.phase_3_compile_templates()["success"])
        if choice == "4":
            return bool(self._context.phase_4_generate_project()["success"])
        self._context._emit("\n❌ Invalid choice. Please select 1, 2, 3, or 4.")
        return False
