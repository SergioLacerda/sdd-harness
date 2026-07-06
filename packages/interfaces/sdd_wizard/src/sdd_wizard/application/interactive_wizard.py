#!/usr/bin/env python3
"""
Interactive mode for SDD Wizard v3 - Phase-based template generation

4-phase flow:
1. Phase 1: Generate markdown templates (asks: language, adoption_level)
2. Phase 2: Review + stage files into phase-2-input
3. Phase 3: Compile staged templates
4. Phase 4: Generate project structure
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sdd_core.utils.environment import get_sdd_paths
from sdd_wizard.application.generation_runtime import (
    PhaseFourRuntime,
    PhaseThreeRuntime,
)
from sdd_wizard.application.operator_state import read_enforcement_label
from sdd_wizard.application.phase_runtime import (
    InteractiveFlowRuntime,
    PhaseOneRuntime,
    PhaseTwoRuntime,
)
from sdd_wizard.application.preferences_flow import PreferencesFlow
from sdd_wizard.application.prompter import Prompter, _wrap_prompter
from sdd_wizard.application.seedling_bridge import SeedlingBridge
from sdd_wizard.application.workspace_runtime import (
    build_selector_discovery_config,
    build_selector_selection_config,
    cleanup_post_generation_artifacts,
    docs_meta_ready,
    emit_selector_phase1_hint,
    ensure_onboarding_scaffold,
    load_selector_selection_ids,
    source_spec_ready,
)
from sdd_wizard.orchestration.wizard.final_template_bundle import (
    consolidate_final_template,
)
from sdd_wizard.orchestration.wizard.models import (
    FinalTemplateConsolidationResult,
    Phase1GenerateResult,
    Phase2StageResult,
)
from sdd_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult as Phase3CompileResult,
)
from sdd_wizard.orchestration.wizard.models import (
    InteractivePhase4GenerateResult as Phase4GenerateResult,
)
from sdd_wizard.orchestration.wizard.seedling_selection import ask_seedling_selection
from sdd_wizard.orchestration.wizard.seedlings_runtime import (
    run_phase6_seedlings_generation,
)

from ._interactive_wizard_constants import (
    _ENFORCEMENT_CHOICES,
    _ENFORCEMENT_MAP,
    _FINAL_TEMPLATE_DIRNAME,
    _HANDSHAKE_CHOICES,
    _HANDSHAKE_MAP,
    _INTERACTION_LANGUAGE_CHOICES,
    _LOCAL_DOCS_LANGUAGE_CHOICES,
    _LOCALE_BY_LANGUAGE,
    _ONBOARDING_BASELINE_GUIDELINES,
    _ONBOARDING_BASELINE_MANDATE,
    _PHASE1_CHOICES_DIRNAME,
    _PHASE2_INPUT_DIRNAME,
    _TEMP_BUILD_DIRS,
    _TEMP_COMPILED_DIRS,
)
from ._interactive_wizard_helpers import (
    _build_phase1_status,
    _do_consolidate_final_template,
    _ensure_docs_meta_ready,
    _save_config,
)


class InteractiveWizard:
    """Interactive guide for SDD Wizard v3"""

    SUPPORTED_PHASE2_PATTERNS: tuple[str, ...] = ("*.md", "*.spec", "*.dsl")

    def __init__(
        self,
        repo_root: Path,
        emitter: Callable[[str], None] | None = None,
        prompter: Prompter | Callable[[str], str] | None = None,
        output_dir: Path | None = None,
        non_interactive: bool = False,
        custom_governance_path: Path | None = None,
    ):
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths
        self._emit = emitter or print
        self._prompter = _wrap_prompter(prompter)
        self._preferences_flow = PreferencesFlow(self._prompter, self._emit)
        self.non_interactive = non_interactive
        self.custom_governance_path = custom_governance_path
        self._resolved_preferences: dict[str, Any] | None = None
        self._resolved_agent_selection: set[str] | None = None
        self._agent_selection_resolved = False
        self.config: dict[str, Any] = {}
        self.client_build_dir = self.paths["client_build"]
        self.client_compiled_dir = self.paths["client_compiled"]
        self.phase1_choices_dir = self.client_build_dir / _PHASE1_CHOICES_DIRNAME
        self.phase2_input_dir = self.client_build_dir / _PHASE2_INPUT_DIRNAME
        self.final_template_dir = (
            output_dir
            if output_dir is not None
            else self.client_build_dir / _FINAL_TEMPLATE_DIRNAME
        )
        self.wizard_config_path = self.client_build_dir / "wizard-config.json"
        self.selector_output_path = self.client_build_dir / "selector-selection.json"
        self.selector_site_path = (
            self.repo_root / "build" / "site" / "selector" / "index.html"
        )

    def load_selector_selection_ids(
        self,
        selection_path: Path | None = None,
        *,
        available_ids: set[str] | None = None,
    ) -> list[str]:
        """Load selector IDs when a selection artifact is present."""
        return load_selector_selection_ids(
            selection_path or self.selector_output_path,
            available_ids=available_ids,
        )

    def _load_selector_selection_config(self) -> dict[str, Any]:
        """Return selector selection metadata when an export artifact exists."""
        return build_selector_selection_config(self.selector_output_path)

    def _emit_selector_phase1_hint(self, selector_selection: dict[str, Any]) -> None:
        """Emit an optional selector hint without changing phase semantics."""
        emit_selector_phase1_hint(
            self._emit,
            selector_output_path=self.selector_output_path,
            selector_site_path=self.selector_site_path,
            selector_selection=selector_selection,
        )

    def _build_selector_discovery_config(
        self, selector_selection: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist selector discovery context for auditability."""
        return build_selector_discovery_config(
            selector_output_path=self.selector_output_path,
            selector_site_path=self.selector_site_path,
            selector_selection=selector_selection,
        )

    def _consolidate_final_template(self) -> FinalTemplateConsolidationResult:
        """Move all compiled artifacts into build/final-template for user handoff."""
        return _do_consolidate_final_template(
            self.client_compiled_dir,
            self.final_template_dir,
            self._emit,
            consolidate_final_template,
        )

    def print_header(self, title: str, icon: str = "🧙") -> None:
        """Print formatted header"""
        self._emit(f"\n{icon} {title}")
        self._emit("=" * 70)

    def ask_user_preferences(self) -> dict[str, Any]:
        """Resolve user preferences: enforcement mode, language, and handshake mode.

        Resolved once and cached — safe to call multiple times (e.g. hoisted
        at the top of the flow, then again internally by PhaseOneRuntime)
        without prompting twice. When `non_interactive` is set, resolves
        without prompting at all (see `PreferencesFlow.resolve_non_interactive_preferences`).
        """
        if self._resolved_preferences is not None:
            return self._resolved_preferences

        if self.non_interactive:
            self._resolved_preferences = (
                self._preferences_flow.resolve_non_interactive_preferences(
                    self.client_build_dir
                )
            )
            return self._resolved_preferences

        self.print_header("User Preferences Setup", "⚙️")
        self._resolved_preferences = self._preferences_flow.collect_preferences(
            enforcement_choices=_ENFORCEMENT_CHOICES,
            enforcement_map=_ENFORCEMENT_MAP,
            interaction_language_choices=_INTERACTION_LANGUAGE_CHOICES,
            local_docs_language_choices=_LOCAL_DOCS_LANGUAGE_CHOICES,
            locale_by_language=_LOCALE_BY_LANGUAGE,
            handshake_choices=_HANDSHAKE_CHOICES,
            handshake_map=_HANDSHAKE_MAP,
        )
        return self._resolved_preferences

    def save_config(self, config: dict[str, Any]) -> Path:
        """Save configuration to wizard-config.json"""
        return _save_config(self.client_build_dir, self.wizard_config_path, config)

    def _build_phase1_status(
        self, status: str, reason: str = "", artifacts: list[str] | None = None
    ) -> dict[str, Any]:
        """Build phase-1 status block persisted to wizard-config.json."""
        return _build_phase1_status(status, reason, artifacts)

    def _ensure_onboarding_scaffold(self) -> tuple[bool, str]:
        """Create minimal wizard scaffold for first-run onboarding."""
        return ensure_onboarding_scaffold(
            client_build_dir=self.client_build_dir,
            phase1_choices_dir=self.phase1_choices_dir,
            phase2_input_dir=self.phase2_input_dir,
            baseline_mandate=_ONBOARDING_BASELINE_MANDATE,
            baseline_guidelines=_ONBOARDING_BASELINE_GUIDELINES,
        )

    def _ensure_docs_meta_ready(self) -> tuple[bool, str]:
        """Ensure Phase 1 inputs exist (legacy docs-meta or unified source_spec)."""
        scaffold_ok, scaffold_reason = self._ensure_onboarding_scaffold()
        return _ensure_docs_meta_ready(
            scaffold_ok,
            scaffold_reason,
            docs_meta_ready(self.client_build_dir),
            source_spec_ready(self.paths, self.client_build_dir),
            self.client_build_dir,
            self.paths,
        )

    def phase_1_generate_templates(self) -> Phase1GenerateResult:
        """Execute Phase 1: Generate templates with user preferences"""
        self.print_header("PHASE 1: Generate Governance Templates", "📝")
        result = PhaseOneRuntime(self).execute()
        if result["success"]:
            self.config = json.loads(
                self.wizard_config_path.read_text(encoding="utf-8")
            )
        return result

    def phase_2_show_instructions(self) -> Phase2StageResult:
        """Show Phase 2 instructions and stage markdown files into phase-2-input."""
        self.print_header("PHASE 2: Review & Customize Governance", "📋")
        return PhaseTwoRuntime(self).execute()

    def _ask_seedling_selection(self) -> set[str] | None:
        """Resolve which seedlings to include. Returns None for all.

        Resolved once and cached — safe to call multiple times without
        prompting twice. When `non_interactive` is set, resolves to `None`
        (all seedlings) without prompting.
        """
        if self._agent_selection_resolved:
            return self._resolved_agent_selection

        if self.non_interactive:
            self._resolved_agent_selection = None
        else:
            self._resolved_agent_selection = ask_seedling_selection(
                self._emit, prompter=self._prompter
            )
        self._agent_selection_resolved = True
        return self._resolved_agent_selection

    def phase_4_generate_project(self) -> Phase4GenerateResult:
        """Execute Phase 4-6: Generate project structure from compiled governance"""
        self.print_header("PHASE 4-6: Generate Project Structure", "🏗️")
        return PhaseFourRuntime(self).execute()

    def _cleanup_post_generation_artifacts(self) -> list[str]:
        """Remove wizard temporary artifacts while preserving final-template."""
        return cleanup_post_generation_artifacts(
            repo_root=self.repo_root,
            client_build_dir=self.client_build_dir,
            client_compiled_dir=self.client_compiled_dir,
            final_template_dir=self.final_template_dir,
            wizard_config_path=self.wizard_config_path,
            temp_build_dirs=_TEMP_BUILD_DIRS,
            temp_compiled_dirs=_TEMP_COMPILED_DIRS,
        )

    def phase_3_compile_templates(self) -> Phase3CompileResult:
        """Execute Phase 3: Compile edited templates to governance JSON"""
        self.print_header("PHASE 3: Compile Governance from Staged Templates", "⚙️")
        return PhaseThreeRuntime(self).execute()

    def phase_6_generate_seedlings(self, output_base: Path) -> bool:
        """Execute Phase 6: Generate intelligent seedlings"""
        return SeedlingBridge().generate(
            wizard_config_path=self.wizard_config_path,
            output_base=output_base,
            emitter=self._emit,
            runner=run_phase6_seedlings_generation,
        )

    def _get_enforcement_label(self) -> str:
        """Get enforcement mode label from config"""
        return read_enforcement_label(self.wizard_config_path)

    def run(self) -> bool:
        """Main interactive flow"""
        return InteractiveFlowRuntime(self).execute()


def run_interactive_wizard(
    repo_root: Path,
    output_dir: Path | None = None,
    non_interactive: bool = False,
    custom_governance_path: Path | None = None,
) -> bool:
    """Create an InteractiveWizard and run the main interactive flow."""
    return InteractiveWizard(
        repo_root=repo_root,
        output_dir=output_dir,
        non_interactive=non_interactive,
        custom_governance_path=custom_governance_path,
    ).run()
