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
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from sdd_core.utils.environment import get_sdd_paths
from sdd_wizard.orchestration.wizard.final_template_bundle import (
    consolidate_final_template,
)
from sdd_wizard.orchestration.wizard.messages import (
    phase2_instructions_message,
    phase3_completed_message,
    phase4_consolidation_failed_message,
    phase4_success_message,
)
from sdd_wizard.orchestration.wizard.models import (
    FinalTemplateConsolidationResult,
    Phase1GenerateResult,
    Phase2StageResult,
    build_interactive_phase3_result,
    build_interactive_phase4_result,
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
from sdd_wizard.src.prompter import Prompter, _wrap_prompter


class InteractiveWizard:
    """Interactive guide for SDD Wizard v3"""

    PHASE1_CHOICES_DIRNAME = "phase-1-choices"
    PHASE2_INPUT_DIRNAME = "phase-2-input"
    PHASE3_OUTPUT_DIRNAME = "compiled"
    FINAL_TEMPLATE_DIRNAME = "final-template"
    SUPPORTED_PHASE2_PATTERNS = ("*.md", "*.spec", "*.dsl")
    FINAL_TEMPLATE_COMPILED_FILES = (
        "governance-core.compiled.msgpack",
        "governance-client-template.compiled.msgpack",
    )
    FINAL_TEMPLATE_AUDIT_FILES = (
        "metadata-core.json",
        "metadata-client-template.json",
    )
    FINAL_TEMPLATE_MANIFEST_FILE = "DEPLOYMENT_MANIFEST.json"
    FINAL_TEMPLATE_CONTEXT_CACHE_FILE = ".sdd/runtime/.sdd-cache.md"

    def __init__(
        self,
        repo_root: Path,
        emitter: Callable[[str], None] | None = None,
        prompter: Prompter | Callable[[str], str] | None = None,
        output_dir: Path | None = None,
    ):
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths
        self._emit = emitter or print
        self._prompter = _wrap_prompter(prompter)
        self.config: dict[str, Any] = {}
        self.client_build_dir = self.paths["client_build"]
        self.client_compiled_dir = self.paths["client_compiled"]
        self.phase1_choices_dir = self.client_build_dir / self.PHASE1_CHOICES_DIRNAME
        self.phase2_input_dir = self.client_build_dir / self.PHASE2_INPUT_DIRNAME
        self.final_template_dir = (
            output_dir
            if output_dir is not None
            else self.client_build_dir / self.FINAL_TEMPLATE_DIRNAME
        )
        self.wizard_config_path = self.client_build_dir / "wizard-config.json"

    def _consolidate_final_template(self) -> FinalTemplateConsolidationResult:
        """Move all compiled artifacts into build/final-template for user handoff."""
        result = consolidate_final_template(
            source_dir=self.client_compiled_dir,
            target_dir=self.final_template_dir,
            compiled_files=self.FINAL_TEMPLATE_COMPILED_FILES,
            audit_files=self.FINAL_TEMPLATE_AUDIT_FILES,
            manifest_file=self.FINAL_TEMPLATE_MANIFEST_FILE,
            context_cache_relative_file=self.FINAL_TEMPLATE_CONTEXT_CACHE_FILE,
        )
        if result["success"]:
            self._emit(
                f"  ✅ Consolidated {result['moved_items']} artifact(s) into {self.final_template_dir}"
            )
        return result

    def print_header(self, title: str, icon: str = "🧙") -> None:
        """Print formatted header"""
        self._emit(f"\n{icon} {title}")
        self._emit("=" * 70)

    _PHASE_CHOICES: dict[str, str] = {
        "1": "Phase 1: Generate governance templates (start here or reset)",
        "2": "Phase 2: How to customize templates (guidance on editing)",
        "3": "Phase 3: Compile governance (after editing Phase 1 output)",
        "4": "Phase 4-6: Generate Project Structure (after Phase 3)",
    }

    def show_phase_menu(self) -> str:
        """Show menu to choose which phase to start at."""
        self.print_header("SDD Wizard v3 - Choose Starting Phase", "🧙")
        self._emit(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        labels = list(self._PHASE_CHOICES.values())
        selected = self._prompter.select("Which phase would you like to run?", labels)
        for key, val in self._PHASE_CHOICES.items():
            if val == selected:
                return key
        return "1"

    _ENFORCEMENT_CHOICES = ["Sem Alertas", "Alertas", "Bloquear"]
    _ENFORCEMENT_MAP = {
        "Sem Alertas": "silent_mode",
        "Alertas": "warn_mode",
        "Bloquear": "strict_mode",
    }
    _LANGUAGE_CHOICES = ["Python", "Java", "TypeScript"]

    def ask_user_preferences(self) -> dict[str, Any]:
        """Ask user for preferences: enforcement mode and programming language."""
        self.print_header("User Preferences Setup", "⚙️")

        self._emit("\n1️⃣  How should governance violations be handled?")
        enforcement_label = self._prompter.select(
            "Select enforcement:", self._ENFORCEMENT_CHOICES
        )
        enforcement_mode = self._ENFORCEMENT_MAP.get(enforcement_label, "warn_mode")
        self._emit(f"   ✅ Selected: {enforcement_label}")

        self._emit(
            "\n2️⃣  Which language would you like examples in?"
            "\n(This is for code examples only - governance applies to all languages)"
        )
        language = self._prompter.select("Select language:", self._LANGUAGE_CHOICES)
        self._emit(f"   ✅ Selected: {language}")

        config = {
            "language": language,
            "enforcement_mode": enforcement_mode,
            "generated_at": datetime.now().isoformat(),
        }

        return config

    def save_config(self, config: dict[str, Any]) -> Path:
        """Save configuration to wizard-config.json"""
        config_dir = self.client_build_dir
        config_dir.mkdir(parents=True, exist_ok=True)

        config_path = self.wizard_config_path

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        return config_path

    def _docs_meta_ready(self) -> bool:
        docs_meta = self.client_build_dir / "docs-meta"
        has_mandate = any(
            (docs_meta / name).exists() for name in ("mandate.spec", "mandate.md")
        )
        has_guidelines = any(
            (docs_meta / name).exists() for name in ("guidelines.dsl", "guidelines.md")
        )
        return has_mandate and has_guidelines

    def _ensure_docs_meta_ready(self) -> tuple[bool, str]:
        """Ensure docs-meta inputs exist for Phase 1 in clean environments."""
        if self._docs_meta_ready():
            return True, ""
        docs_meta = self.client_build_dir / "docs-meta"
        return (
            False,
            f"docs-meta artifacts are missing at {docs_meta}. "
            "Run 'sdd governance compile' to regenerate governance artifacts.",
        )

    def phase_1_generate_templates(self) -> Phase1GenerateResult:
        """Execute Phase 1: Generate templates with user preferences"""
        self.print_header("PHASE 1: Generate Governance Templates", "📝")

        try:
            from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator

            # Collect user preferences
            config = self.ask_user_preferences()
            self.config = config

            # Save config
            config_path = self.save_config(config)
            self._emit(f"\n✅ Configuration saved to: {config_path}")

            ready, reason = self._ensure_docs_meta_ready()
            if not ready:
                return {
                    "success": False,
                    "config_path": str(config_path),
                    "output_path": str(self.phase1_choices_dir),
                    "language": str(config.get("language", "Python")),
                    "enforcement_mode": str(
                        config.get("enforcement_mode", "warn_mode")
                    ),
                    "error": reason,
                }

            core_path = self.paths["root"] / "packages"
            output_path = self.phase1_choices_dir

            generator = Phase1Generator(
                core_path, output_path, verbose=True, config=config
            )
            result = generator.run()

            if result["success"]:
                self._emit(f"""
✅ Phase 1 Complete!

📝 Templates generated: {output_path}
   Language: {config.get("language")}
   Adoption: {config.get("adoption_level")}

Next steps:
1. Review markdown files in phase-1-choices/
2. Edit status fields (required/optional/custom)
3. Run Phase 2 for step-by-step instructions
4. Run Phase 3 to compile
""")

            return {
                "success": bool(result["success"]),
                "config_path": str(config_path),
                "output_path": str(output_path),
                "language": str(config.get("language", "Python")),
                "enforcement_mode": str(config.get("enforcement_mode", "warn_mode")),
                "error": "",
            }
        except Exception as e:
            self._emit(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "config_path": str(self.wizard_config_path),
                "output_path": str(self.phase1_choices_dir),
                "language": "Python",
                "enforcement_mode": "warn_mode",
                "error": str(e),
            }

    def phase_2_show_instructions(self) -> Phase2StageResult:
        """Show Phase 2 instructions and stage markdown files into phase-2-input."""
        self.print_header("PHASE 2: Review & Customize Governance", "📋")

        phase1_path = self.phase1_choices_dir
        output_path = self.phase2_input_dir

        if not phase1_path.exists():
            self._emit(f"\n❌ Phase 1 templates not found: {phase1_path}")
            self._emit("Run Phase 1 first to generate templates.")
            return {
                "success": False,
                "phase1_path": str(phase1_path),
                "output_path": str(output_path),
                "copied_files": [],
                "error": "Phase 1 templates not found.",
            }

        output_path.mkdir(parents=True, exist_ok=True)

        files_to_stage: dict[str, Path] = {}
        for pattern in self.SUPPORTED_PHASE2_PATTERNS:
            for input_file in sorted(phase1_path.glob(pattern)):
                files_to_stage[input_file.name] = input_file

        copied_files: list[str] = []
        for input_file in files_to_stage.values():
            destination = output_path / input_file.name
            shutil.copy2(input_file, destination)
            copied_files.append(input_file.name)

        if not copied_files:
            self._emit(f"\n❌ No supported review files found in: {phase1_path}")
            self._emit(f"Expected one of: {', '.join(self.SUPPORTED_PHASE2_PATTERNS)}")
            self._emit("Run Phase 1 first to generate templates.")
            return {
                "success": False,
                "phase1_path": str(phase1_path),
                "output_path": str(output_path),
                "copied_files": [],
                "error": "No supported review files found in phase-1-choices.",
            }

        self._emit(phase2_instructions_message(phase1_path, output_path, copied_files))

        self._prompter.confirm("Have you completed Phase 2 edits?", default=True)
        return {
            "success": True,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": copied_files,
            "error": "",
        }

    def _ask_seedling_selection(self) -> set[str] | None:
        """Ask the user which seedlings to include. Returns None for all."""
        return ask_seedling_selection(self._emit, prompter=self._prompter)

    def phase_4_generate_project(self) -> Phase4GenerateResult:
        """Execute Phase 4-6: Generate project structure from compiled governance"""
        self.print_header("PHASE 4-6: Generate Project Structure", "🏗️")

        try:
            from sdd_wizard.orchestration.phase_4_5_6_generator import (
                run_phase_4_5_6_generator,
            )

            # Load config from wizard-config.json
            config_path = self.wizard_config_path

            if not config_path.exists():
                self._emit("\n❌ Configuration not found!")
                self._emit("You must run Phase 1 first to set preferences.")
                return build_interactive_phase4_result(
                    success=False,
                    error="Configuration not found; run Phase 1 first.",
                )

            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

            # Check if Phase 3 completed
            phase3_output = self.client_compiled_dir
            if not phase3_output.exists():
                self._emit("\n❌ Phase 3 output not found!")
                self._emit("You must run Phase 3 first to compile governance.")
                return build_interactive_phase4_result(
                    success=False,
                    error="Phase 3 output not found; run Phase 3 first.",
                )

            # Ask which seedlings to include
            selected_seedlings = self._ask_seedling_selection()

            # Output base is where .sdd/ will be created
            output_base = self.client_compiled_dir

            # Run Phase 4-6 generator
            result = run_phase_4_5_6_generator(
                self.paths["root"], output_base, config, selected_seedlings
            )

            if result["success"]:
                consolidation = self._consolidate_final_template()
                if not consolidation["success"]:
                    self._emit(
                        phase4_consolidation_failed_message(
                            self.client_compiled_dir, self.final_template_dir
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

                self._emit(
                    phase4_success_message(
                        int(result["mandates"]),
                        int(result["guidelines"]),
                        list(result["categories"]),
                        self.final_template_dir,
                    )
                )
                return build_interactive_phase4_result(
                    success=True,
                    mandates=int(result.get("mandates", 0)),
                    guidelines=int(result.get("guidelines", 0)),
                    categories=list(result.get("categories", [])),
                    consolidated=True,
                )
            else:
                self._emit("\n❌ Phase 4-6 generation failed!")
                for error in result.get("errors", []):
                    self._emit(f"   • {error}")
                error_messages = result.get("errors", [])
                return build_interactive_phase4_result(
                    success=False,
                    error="; ".join(error_messages)
                    if error_messages
                    else "Phase 4-6 generation failed.",
                )
        except Exception as e:
            self._emit(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return build_interactive_phase4_result(success=False, error=str(e))

    def phase_3_compile_templates(self) -> Phase3CompileResult:
        """Execute Phase 3: Compile edited templates to governance JSON"""
        self.print_header("PHASE 3: Compile Governance from Staged Templates", "⚙️")

        # Phase 3 reads edited markdown from phase-2-input
        markdown_path = self.phase2_input_dir
        output_path = self.client_compiled_dir

        self._emit(f"  📂 Input (phase-2-input): {markdown_path}")
        self._emit(f"  📂 Output (client-compiled): {output_path}")

        if not markdown_path.exists():
            self._emit(f"\n❌ Templates not found: {markdown_path}")
            self._emit("\nYou need to:")
            self._emit("1. Run Phase 1 to generate templates")
            self._emit("2. Run Phase 2 to stage edited files into phase-2-input")
            self._emit("3. Run Phase 3 to compile")
            return build_interactive_phase3_result(
                success=False,
                output_path=output_path,
                error=f"Templates not found: {markdown_path}",
            )

        try:
            from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler

            compiler = Phase3Compiler(
                markdown_path, output_path, self.paths["root"], verbose=True
            )
            result = compiler.run()

            if result["success"]:
                self._emit(f"""
✅ PHASE 3 COMPLETE!

📊 COMPILATION RESULTS:
   ✓ Mandates: {result.get("mandates", 0)}
   ✓ Guidelines: {result.get("guidelines", 0)}
   ✓ Output Files: {", ".join(result.get("files", []))}
   ✓ Location: {result.get("output_path")}

""")
                # Automatically run Phase 6: Generate intelligent seedlings
                self._emit("\n" + "=" * 70)
                self.print_header("PHASE 6: Generate Intelligent Seedlings", "🌱")
                self._emit("=" * 70)

                if self.phase_6_generate_seedlings(output_path):
                    self._emit(phase3_completed_message())
                    self._emit(
                        f"""
✓ Governance mandates are ready for agents
✓ Enforcement mode: {self._get_enforcement_label()}
✓ IDE integration configured
✓ CI/CD compliance hooks ready

ℹ️  For more details, see README.md in your project root.
"""
                    )
                    return build_interactive_phase3_result(
                        success=True,
                        output_path=Path(
                            str(result.get("output_path", str(output_path)))
                        ),
                        mandates=int(result.get("mandates", 0)),
                        guidelines=int(result.get("guidelines", 0)),
                        files=list(result.get("files", [])),
                        seedlings_success=True,
                    )
                else:
                    self._emit(
                        "\n⚠️  Phase 6 (Seedlings) had issues, but Phase 3 succeeded"
                    )
                    self._emit(
                        f"   You can manually run Phase 6 or copy files from {output_path}"
                    )
                    return build_interactive_phase3_result(
                        success=True,
                        output_path=Path(
                            str(result.get("output_path", str(output_path)))
                        ),
                        mandates=int(result.get("mandates", 0)),
                        guidelines=int(result.get("guidelines", 0)),
                        files=list(result.get("files", [])),
                        seedlings_success=False,
                    )
            else:
                self._emit(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
                return build_interactive_phase3_result(
                    success=False,
                    output_path=Path(str(result.get("output_path", str(output_path)))),
                    mandates=int(result.get("mandates", 0)),
                    guidelines=int(result.get("guidelines", 0)),
                    files=list(result.get("files", [])),
                    seedlings_success=False,
                    error=str(result.get("error", "Unknown error")),
                )
        except Exception as e:
            self._emit(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return build_interactive_phase3_result(
                success=False,
                output_path=output_path,
                error=str(e),
            )

    def phase_6_generate_seedlings(self, output_base: Path) -> bool:
        """Execute Phase 6: Generate intelligent seedlings"""
        try:
            return run_phase6_seedlings_generation(
                wizard_config_path=self.wizard_config_path,
                output_base=output_base,
                emitter=self._emit,
            )
        except Exception as e:
            self._emit(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _get_enforcement_label(self) -> str:
        """Get enforcement mode label from config"""
        try:
            config_path = self.wizard_config_path
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                    enforcement_mode = config.get("enforcement_mode", "warn_mode")
                    labels = {
                        "silent_mode": "Sem Alertas",
                        "warn_mode": "Alertas",
                        "strict_mode": "Bloquear",
                    }
                    return labels.get(enforcement_mode, "Alertas")
        except Exception:  # nosec B110 noqa: BLE001
            pass
        return "Alertas"

    def run(self) -> bool:
        """Main interactive flow"""
        try:
            choice = self.show_phase_menu()

            if choice == "1":
                return self.phase_1_generate_templates()["success"]
            elif choice == "2":
                return self.phase_2_show_instructions()["success"]
            elif choice == "3":
                return self.phase_3_compile_templates()["success"]
            elif choice == "4":
                return self.phase_4_generate_project()["success"]
            else:
                self._emit("\n❌ Invalid choice. Please select 1, 2, 3, or 4.")
                return False

        except KeyboardInterrupt:
            self._emit("\n\n❌ Wizard cancelled by user")
            return False
        except Exception as e:
            self._emit(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return False


def run_interactive_wizard(repo_root: Path, output_dir: Path | None = None) -> bool:
    """Entry point for interactive wizard"""
    wizard = InteractiveWizard(repo_root, output_dir=output_dir)
    return wizard.run()
