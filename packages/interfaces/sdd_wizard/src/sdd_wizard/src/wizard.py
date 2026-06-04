#!/usr/bin/env python
"""
SDD v3.0 Wizard - Interactive CLI for project generation

Transforms architect specs (core/) into client-ready projects
via 7-phase orchestration pipeline.

Usage:
  Interactive mode:
    python wizard.py

  Non-interactive mode:
    python wizard.py --language java --output ~/my-project/

  Dry-run (preview without creating files):
    python wizard.py --language python --dry-run --verbose
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import typer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import phase implementations
# Import interactive mode
from sdd_core.utils.environment import get_sdd_paths
from sdd_wizard.orchestration.phase_1_validate import phase_1_validate_source
from sdd_wizard.orchestration.phase_2_load_compiled_v3 import (
    phase_2_load_compiled_v3 as phase_2_load_compiled,
)
from sdd_wizard.orchestration.phase_3_filter_mandates import phase_3_filter_mandates
from sdd_wizard.orchestration.phase_4_filter_guidelines import phase_4_filter_guidelines
from sdd_wizard.orchestration.phase_5_apply_template import phase_5_apply_template
from sdd_wizard.orchestration.phase_6_generate_project import phase_6_generate_project
from sdd_wizard.orchestration.phase_7_validate_output import phase_7_validate_output
from sdd_wizard.orchestration.wizard.final_template_bundle import ensure_context_cache


class WizardOrchestrator:
    """Main orchestrator for 7-phase wizard pipeline"""

    def __init__(self, repo_root: Path | None = None, verbose: bool = False):
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths
        self.verbose = verbose
        self.phases_results: dict[str, dict[str, Any]] = {}
        self.artifacts: dict[str, Any] = {}

    def log(self, level: str, message: str) -> None:
        """Print log message with level indicator"""
        if level == "INFO" or self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level:8s} {message}")  # noqa: T201

    def print_phase_header(self, phase_num: int, phase_name: str) -> None:
        """Print phase execution header"""
        print()  # noqa: T201
        print("=" * 60)  # noqa: T201
        print(f"Phase {phase_num}: {phase_name}")  # noqa: T201
        print("=" * 60)  # noqa: T201

    def print_phase_result(self, success: bool, report: dict[str, Any]) -> None:
        """Print phase result summary"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"\n{status} - {report.get('phase', 'UNKNOWN')}")  # noqa: T201

        if report.get("data"):
            print(f"  Data: {report['data']}")  # noqa: T201

        if report.get("warnings"):
            for warning in report["warnings"]:
                print(f"  ⚠️  Warning: {warning}")  # noqa: T201

        if report.get("errors") and self.verbose:
            for error in report["errors"]:
                print(f"  ❌ Error: {error}")  # noqa: T201

    def run_phase_1(self) -> bool:
        """Execute Phase 1: Validate SOURCE"""
        self.print_phase_header(1, "Validate SOURCE (core/)")
        self.log("INFO", "Checking mandate.spec and guidelines.dsl...")

        success_raw, report = phase_1_validate_source(self.repo_root)
        success = bool(success_raw)
        self.phases_results["phase_1"] = report
        self.print_phase_result(success, report)

        return success

    def run_phase_2(self) -> bool:
        """Execute Phase 2: Load COMPILED"""
        self.print_phase_header(2, "Load COMPILED (runtime/)")
        self.log("INFO", "Deserializing compiled artifacts...")

        success_raw, report = phase_2_load_compiled(self.repo_root)
        success = bool(success_raw)
        self.phases_results["phase_2"] = report

        # Store artifacts for next phases
        if "_artifacts" in report:
            self.artifacts = report["_artifacts"]

        self.print_phase_result(success, report)
        return success

    def run_phase_3(self, mandates: list[str] | None = None) -> bool:
        """Execute Phase 3: Filter mandates"""
        self.print_phase_header(3, "Filter Mandates")
        self.log("INFO", "Filtering mandates by user selection...")

        # Get mandates from Phase 2
        phase_2_report = self.phases_results.get("phase_2", {})
        compiled_mandates = phase_2_report.get("data", {}).get("mandate", {})

        if not compiled_mandates:
            self.log("ERROR", "No mandates from Phase 2")
            return False

        success_raw, report = phase_3_filter_mandates(
            compiled_mandates, selected_mandate_ids=mandates, repo_root=self.repo_root
        )
        success = bool(success_raw)
        self.phases_results["phase_3"] = report
        self.print_phase_result(success, report)
        return success

    def run_phase_4(self, language: str = "python") -> bool:
        """Execute Phase 4: Filter guidelines"""
        self.print_phase_header(4, "Filter Guidelines")
        self.log("INFO", f"Filtering guidelines by language={language}...")

        # Get guidelines from Phase 2
        phase_2_report = self.phases_results.get("phase_2", {})
        compiled_guidelines = phase_2_report.get("data", {}).get("guidelines", {})

        if not compiled_guidelines:
            self.log("ERROR", "No guidelines from Phase 2")
            return False

        success_raw, report = phase_4_filter_guidelines(
            compiled_guidelines, language=language, repo_root=self.repo_root
        )
        success = bool(success_raw)
        self.phases_results["phase_4"] = report
        self.print_phase_result(success, report)
        return success

    def run_phase_5(
        self, language: str = "python", output_dir: Path | None = None
    ) -> bool:
        """Execute Phase 5: Apply template"""
        self.print_phase_header(5, "Apply Template Scaffold")
        self.log("INFO", "Copying and customizing template files...")

        if output_dir is None:
            output_dir = self.paths["client_build"] / "scaffold"

        success_raw, report = phase_5_apply_template(
            scaffolding_dir=output_dir, language=language, repo_root=self.repo_root
        )
        success = bool(success_raw)
        self.phases_results["phase_5"] = report
        self.print_phase_result(success, report)
        return success

    def run_phase_6(
        self, output_dir: Path | None = None, language: str = "python"
    ) -> bool:
        """Execute Phase 6: Generate project"""
        self.print_phase_header(6, "Generate Project Structure")
        self.log("INFO", "Generating complete project structure...")

        # Get data from previous phases
        phase_1_report = self.phases_results.get("phase_1", {})
        phase_2_report = self.phases_results.get("phase_2", {})
        phase_3_report = self.phases_results.get("phase_3", {})
        phase_4_report = self.phases_results.get("phase_4", {})

        # Extract mandate and guideline text from Phase 1
        mandate_text = phase_1_report.get("data", {}).get("mandate_text", "")
        guidelines_text = phase_1_report.get("data", {}).get("guidelines_text", "")

        # Extract metadata from Phase 2
        metadata = phase_2_report.get("data", {}).get("metadata", {})

        # Extract filtered mandates and guidelines from Phases 3-4
        filtered_mandates = phase_3_report.get("data", {}).get("filtered_mandates", {})
        filtered_guidelines = phase_4_report.get("data", {}).get(
            "filtered_guidelines", {}
        )

        if output_dir is None:
            output_dir = self.paths["client_build"] / "project"

        success_raw, report = phase_6_generate_project(
            filtered_mandates=filtered_mandates,
            filtered_guidelines=filtered_guidelines,
            mandate_text=mandate_text,
            guidelines_text=guidelines_text,
            metadata=metadata,
            output_dir=output_dir,
            language=language,
            repo_root=self.repo_root,
        )
        success = bool(success_raw)
        self.phases_results["phase_6"] = report
        self.print_phase_result(success, report)
        return success

    def run_phase_7(self, project_dir: Path | None = None) -> bool:
        """Execute Phase 7: Validate output"""
        self.print_phase_header(7, "Validate Output")
        self.log("INFO", "Validating generated project...")

        if project_dir is None:
            project_dir = self.paths["client_build"] / "project"

        success_raw, report = phase_7_validate_output(
            project_dir=project_dir, repo_root=self.repo_root
        )
        success = bool(success_raw)

        # M003 requirement: non-interactive flow must also ensure context cache.
        ensure_context_cache(project_dir, ".sdd/runtime/.sdd-cache.md")

        self.phases_results["phase_7"] = report
        self.print_phase_result(success, report)
        return success

    def run_full_pipeline(
        self,
        language: str = "python",
        mandates: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> bool:
        """Execute complete pipeline (phases 1-7)"""
        print()  # noqa: T201
        print("🔮 SDD v3.0 Wizard - Project Generator")  # noqa: T201
        print("=" * 60)  # noqa: T201
        print(f"Started: {datetime.now().isoformat()}")  # noqa: T201
        print(f"Language: {language}")  # noqa: T201
        print()  # noqa: T201

        # Phase 1: Validate SOURCE
        if not self.run_phase_1():
            print("\n❌ Pipeline stopped at Phase 1 (Validation failed)")  # noqa: T201
            return False

        # Phase 2: Load COMPILED
        if not self.run_phase_2():
            print(  # noqa: T201
                "\n❌ Pipeline stopped at Phase 2 (Failed to load compiled artifacts)"
            )
            return False

        # Phase 3: Filter Mandates
        if not self.run_phase_3(mandates):
            print("\n❌ Pipeline stopped at Phase 3 (Mandate filtering failed)")  # noqa: T201
            return False

        # Phase 4: Filter Guidelines
        if not self.run_phase_4(language):
            print("\n❌ Pipeline stopped at Phase 4 (Guideline filtering failed)")  # noqa: T201
            return False

        # Phase 5: Apply Template
        scaffold_dir = (output_dir or (self.paths["client_build"])) / "scaffold"
        if not self.run_phase_5(language, scaffold_dir):
            print("\n⚠️  Phase 5 warning (template not critical)")  # noqa: T201

        # Phase 6: Generate Project
        project_dir = (output_dir or (self.paths["client_build"])) / "project"
        if not self.run_phase_6(project_dir, language):
            print("\n❌ Pipeline stopped at Phase 6 (Project generation failed)")  # noqa: T201
            return False

        # Phase 7: Validate Output
        if not self.run_phase_7(project_dir):
            print("\n⚠️  Phase 7 warning (validation issues)")  # noqa: T201

        print()  # noqa: T201
        print("=" * 60)  # noqa: T201
        print("✅ Phases 1-7 Complete!")  # noqa: T201
        print("=" * 60)  # noqa: T201
        print()  # noqa: T201
        print("📋 Pipeline Status:")  # noqa: T201
        for _phase_name, report in self.phases_results.items():
            status = "✅" if report["status"] == "SUCCESS" else "❌"
            print(f"  {status} {report['phase']}")  # noqa: T201

        print()  # noqa: T201
        print()  # noqa: T201
        print(f"📁 Generated project: {project_dir}")  # noqa: T201
        print()  # noqa: T201

        return True


app = typer.Typer(
    help="SDD v3.0 Wizard - Generate project from compiled specifications"
)

LanguageChoice = Literal["java", "python", "js"]

_LANGUAGE_OPTION = typer.Option(
    None,
    help="Target programming language (interactive if not specified)",
    case_sensitive=False,
)
_MANDATES_OPTION = typer.Option(
    None,
    help="Comma-separated mandate IDs (e.g., M001,M002)",
)
_OUTPUT_OPTION = typer.Option(
    None,
    help="Output directory for generated project",
)
_DRY_RUN_OPTION = typer.Option(
    False, "--dry-run", help="Preview without creating files"
)
_VERBOSE_OPTION = typer.Option(False, help="Show detailed output")
_INTERACTIVE_OPTION = typer.Option(False, help="Run in interactive guided mode")


@app.command()
def main(
    language: LanguageChoice | None = _LANGUAGE_OPTION,
    mandates: str | None = _MANDATES_OPTION,
    output: Path | None = _OUTPUT_OPTION,
    dry_run: bool = _DRY_RUN_OPTION,
    verbose: bool = _VERBOSE_OPTION,
    interactive: bool = _INTERACTIVE_OPTION,
) -> None:
    """Generate a project from compiled SDD specifications."""
    orchestrator = WizardOrchestrator(verbose=verbose)

    should_run_interactive = interactive or (
        not language and not mandates and not output
    )

    if should_run_interactive:
        try:
            from sdd_wizard.src.interactive_mode import run_interactive_wizard

            success = run_interactive_wizard(orchestrator.repo_root)
        except ImportError:
            success = orchestrator.run_full_pipeline()
        raise typer.Exit(0 if success else 1)

    mandate_ids = mandates.split(",") if mandates else None
    success = orchestrator.run_full_pipeline(
        language=language or "python",
        mandates=mandate_ids,
        output_dir=output,
    )
    raise typer.Exit(0 if success else 1)


if __name__ == "__main__":
    app()
