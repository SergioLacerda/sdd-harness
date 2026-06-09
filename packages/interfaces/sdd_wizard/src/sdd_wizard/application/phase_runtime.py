"""Runtime bridge from the shell boundary to the current interactive engine."""

from __future__ import annotations

import importlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from sdd_wizard.contracts import WizardInvocation
from sdd_wizard.orchestration.wizard.messages import phase2_instructions_message
from sdd_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult,
    InteractivePhase4GenerateResult,
    Phase1GenerateResult,
    Phase2StageResult,
)


class PhaseRuntime:
    """Execute the current interactive wizard through a narrow boundary."""

    def __init__(
        self,
        invocation: WizardInvocation,
        runner: Callable[..., bool] | None = None,
    ) -> None:
        self._invocation = invocation
        self._runner = runner

    def execute(self) -> bool:
        """Run the interactive engine with lazy imports."""
        runner = self._runner or self._load_runner()
        return bool(
            runner(
                self._invocation.project_root,
                output_dir=self._invocation.output_path,
            )
        )

    def _load_runner(self) -> Callable[..., bool]:
        module = importlib.import_module("sdd_wizard.application.interactive_wizard")
        return module.run_interactive_wizard


class PhaseOneContext(Protocol):
    """Narrow contract for delegating Phase 1 orchestration."""

    repo_root: Path
    phase1_choices_dir: Path
    wizard_config_path: Path
    SUPPORTED_PHASE2_PATTERNS: tuple[str, ...]

    def ask_user_preferences(self) -> dict[str, Any]:
        """Return the Phase 1 preference payload."""

    def _load_selector_selection_config(self) -> dict[str, Any]:
        """Load selector selection metadata when present."""

    def _build_selector_discovery_config(
        self, selector_selection: dict[str, Any]
    ) -> dict[str, Any]:
        """Build audit metadata for selector discovery."""

    def _emit_selector_phase1_hint(self, selector_selection: dict[str, Any]) -> None:
        """Emit the optional selector hint to the operator."""

    def _ensure_docs_meta_ready(self) -> tuple[bool, str]:
        """Validate that Phase 1 source inputs are ready."""

    def save_config(self, config: dict[str, Any]) -> Path:
        """Persist wizard config and return its path."""

    def _build_phase1_status(
        self,
        status: str,
        reason: str = "",
        artifacts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build the persisted Phase 1 status block."""

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""


class PhaseOneRuntime:
    """Application boundary for the Phase 1 template-generation flow."""

    def __init__(self, context: PhaseOneContext) -> None:
        self._context = context

    def execute(self) -> Phase1GenerateResult:
        """Run the Phase 1 flow and return the legacy result payload."""
        try:
            generator_type = self._load_generator()
            config = self._context.ask_user_preferences()
            selector_result = self._load_selector_config(config)
            if selector_result is not None:
                return selector_result
            readiness_result = self._ensure_docs_ready(config)
            if readiness_result is not None:
                return readiness_result
            return self._run_generator(generator_type, config)
        except Exception as exc:
            self._context._emit(f"\n❌ Error: {exc}")
            import traceback

            traceback.print_exc()
            return self._build_failure(
                error=str(exc),
                config_path=str(self._context.wizard_config_path),
            )

    def _load_generator(self) -> type[Any]:
        from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator

        return Phase1Generator

    def _load_selector_config(
        self, config: dict[str, Any]
    ) -> Phase1GenerateResult | None:
        from sdd_wizard.orchestration.wizard.selector_bridge import SelectorBridgeError

        try:
            selector_selection = self._context._load_selector_selection_config()
        except SelectorBridgeError as exc:
            config["selector_discovery"] = (
                self._context._build_selector_discovery_config({})
            )
            config["selector_discovery"]["validation_error"] = str(exc)
            reason = f"Invalid selector artifact: {exc}"
            self._context._emit(f"\n❌ {reason}")
            return self._persist_failure(config, reason)
        if selector_selection:
            config["selector_selection"] = selector_selection
        config["selector_discovery"] = self._context._build_selector_discovery_config(
            selector_selection
        )
        self._context._emit_selector_phase1_hint(selector_selection)
        return None

    def _ensure_docs_ready(self, config: dict[str, Any]) -> Phase1GenerateResult | None:
        ready, reason = self._context._ensure_docs_meta_ready()
        if ready:
            return None
        return self._persist_failure(config, reason)

    def _persist_failure(
        self, config: dict[str, Any], reason: str
    ) -> Phase1GenerateResult:
        config["phase1_status"] = self._context._build_phase1_status(
            status="failed", reason=reason
        )
        config_path = self._context.save_config(config)
        self._context._emit(f"\n✅ Configuration saved to: {config_path}")
        return self._build_failure(
            error=reason, config_path=str(config_path), config=config
        )

    def _run_generator(
        self, generator_type: type[Any], config: dict[str, Any]
    ) -> Phase1GenerateResult:
        output_path = self._context.phase1_choices_dir
        generator = generator_type(
            self._context.repo_root / "packages",
            output_path,
            verbose=True,
            config=config,
        )
        result = generator.run()
        if result["success"]:
            generated_files = self._collect_generated_files(output_path)
            config["phase1_status"] = self._context._build_phase1_status(
                status="completed", artifacts=generated_files
            )
            self._context._emit(
                f"""
✅ Phase 1 Complete!

📝 Templates generated: {output_path}
   Language: {config.get("language")}
   Adoption: {config.get("adoption_level")}

Next steps:
1. Review markdown files in phase-1-choices/
2. Edit status fields (required/optional/custom)
3. Run Phase 2 for step-by-step instructions
4. Run Phase 3 to compile
"""
            )
        else:
            config["phase1_status"] = self._context._build_phase1_status(
                status="failed",
                reason=str(result.get("error") or "phase1_generation_failed"),
            )
        config_path = self._context.save_config(config)
        self._context._emit(f"\n✅ Configuration saved to: {config_path}")
        return self._build_result(
            success=bool(result["success"]),
            config_path=str(config_path),
            output_path=str(output_path),
            config=config,
        )

    def _collect_generated_files(self, output_path: Path) -> list[str]:
        return sorted(
            path.name
            for pattern in self._context.SUPPORTED_PHASE2_PATTERNS
            for path in output_path.glob(pattern)
        )

    def _build_failure(
        self,
        *,
        error: str,
        config_path: str,
        config: dict[str, Any] | None = None,
    ) -> Phase1GenerateResult:
        active_config = config or {}
        return {
            "success": False,
            "config_path": config_path,
            "output_path": str(self._context.phase1_choices_dir),
            "language": str(active_config.get("language", "Python")),
            "enforcement_mode": str(active_config.get("enforcement_mode", "warn_mode")),
            "error": error,
        }

    def _build_result(
        self,
        *,
        success: bool,
        config_path: str,
        output_path: str,
        config: dict[str, Any],
    ) -> Phase1GenerateResult:
        return {
            "success": success,
            "config_path": config_path,
            "output_path": output_path,
            "language": str(config.get("language", "Python")),
            "enforcement_mode": str(config.get("enforcement_mode", "warn_mode")),
            "error": "",
        }


class PhaseTwoContext(Protocol):
    """Narrow contract for delegating Phase 2 staging."""

    phase1_choices_dir: Path
    phase2_input_dir: Path
    wizard_config_path: Path
    SUPPORTED_PHASE2_PATTERNS: tuple[str, ...]
    _prompter: Any

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""


class PhaseTwoRuntime:
    """Application boundary for the Phase 2 staging flow."""

    def __init__(self, context: PhaseTwoContext) -> None:
        self._context = context

    def execute(self) -> Phase2StageResult:
        """Stage Phase 1 output into Phase 2 input and guide the operator."""
        phase1_path = self._context.phase1_choices_dir
        output_path = self._context.phase2_input_dir
        failed_status = self._load_failed_phase1_status()
        if failed_status is not None:
            return self._build_failed_status_result(
                phase1_path, output_path, failed_status
            )
        if not phase1_path.exists():
            self._context._emit(f"\n❌ Phase 1 templates not found: {phase1_path}")
            self._context._emit("Run Phase 1 first to generate templates.")
            return self._build_missing_phase1_result(phase1_path, output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        copied_files = self._copy_supported_files(phase1_path, output_path)
        if not copied_files:
            return self._build_no_files_result(phase1_path, output_path)
        self._context._emit(
            phase2_instructions_message(phase1_path, output_path, copied_files)
        )
        self._context._prompter.confirm(
            "Have you completed Phase 2 edits?", default=True
        )
        return self._build_success(phase1_path, output_path, copied_files)

    def _load_failed_phase1_status(self) -> str | None:
        if not self._context.wizard_config_path.exists():
            return None
        try:
            with open(self._context.wizard_config_path, encoding="utf-8") as handle:
                config = json.load(handle)
        except (OSError, ValueError, TypeError) as exc:
            self._context._emit(
                f"⚠️  Unable to read phase1_status from {self._context.wizard_config_path}: {exc}"
            )
            return None
        phase1_status = config.get("phase1_status", {})
        if phase1_status.get("status") != "failed":
            return None
        return str(phase1_status.get("reason") or "unknown reason")

    def _copy_supported_files(self, phase1_path: Path, output_path: Path) -> list[str]:
        files_to_stage: dict[str, Path] = {}
        for pattern in self._context.SUPPORTED_PHASE2_PATTERNS:
            for input_file in sorted(phase1_path.glob(pattern)):
                files_to_stage[input_file.name] = input_file
        copied_files: list[str] = []
        for input_file in files_to_stage.values():
            destination = output_path / input_file.name
            shutil.copy2(input_file, destination)
            copied_files.append(input_file.name)
        return copied_files

    def _build_failed_status_result(
        self, phase1_path: Path, output_path: Path, reason: str
    ) -> Phase2StageResult:
        self._context._emit("\n❌ Phase 1 did not complete successfully.")
        self._context._emit(f"Reason: {reason}")
        self._context._emit(
            "Run Phase 1 again after fixing the issue above before continuing."
        )
        return {
            "success": False,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": [],
            "error": f"Phase 1 status is failed: {reason}",
        }

    def _build_missing_phase1_result(
        self, phase1_path: Path, output_path: Path
    ) -> Phase2StageResult:
        return {
            "success": False,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": [],
            "error": "Phase 1 templates not found.",
        }

    def _build_no_files_result(
        self, phase1_path: Path, output_path: Path
    ) -> Phase2StageResult:
        self._context._emit(f"\n❌ No supported review files found in: {phase1_path}")
        self._context._emit(
            f"Expected one of: {', '.join(self._context.SUPPORTED_PHASE2_PATTERNS)}"
        )
        self._context._emit("Run Phase 1 first to generate templates.")
        return {
            "success": False,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": [],
            "error": "No supported review files found in phase-1-choices.",
        }

    def _build_success(
        self, phase1_path: Path, output_path: Path, copied_files: list[str]
    ) -> Phase2StageResult:
        return {
            "success": True,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": copied_files,
            "error": "",
        }


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
