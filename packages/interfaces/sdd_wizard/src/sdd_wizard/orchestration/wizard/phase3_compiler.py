"""Phase 3 Compiler — orchestrates template compilation pipeline."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from sdd_core.utils.environment import get_sdd_paths

from .guidelines_compiler import GuidelinesCompiler
from .mandates_compiler import MandatesCompiler
from .markdown_parser import MarkdownParser
from .models import ParsedItems, Phase3RunResult
from .source_readme_compiler import SourceReadmeCompiler
from .template_locator import TemplateLocator


def _copy_seedlings(
    repo_root: Path,
    output_path: Path,
    emitter: Callable[[str], None],
) -> bool:
    """Copy seedling templates from sdd_integration into output_path."""
    try:
        source_seedling_dir = (
            repo_root
            / "packages"
            / "features"
            / "sdd_integration"
            / "src"
            / "sdd_integration"
            / "templates"
        )
        if not source_seedling_dir.exists():
            return True
        output_path.mkdir(parents=True, exist_ok=True)
        for seedling_type in (".github", ".vscode", ".cursor"):
            source_path = source_seedling_dir / seedling_type
            if source_path.exists():
                target_path = output_path / seedling_type
                target_path.mkdir(parents=True, exist_ok=True)
                for item in source_path.rglob("*"):
                    if item.is_file():
                        dest = target_path / item.relative_to(source_path)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
        return True
    except Exception as exc:
        emitter(f"  ❌ Error copying seedlings: {exc}")
        import traceback

        traceback.print_exc()
        return False


def _generate_spec_file(
    repo_root: Path, output_path: Path, emitter: Callable[[str], None]
) -> None:
    """Generate mandates.json spec file from canonical mandate markdown files."""
    try:
        from sdd_integration.builders.governance.pipeline_builder import PipelineBuilder

        canonical_dir = repo_root / "docs" / "spec" / "canonical" / "core" / "mandates"
        if not canonical_dir.is_dir() or not list(canonical_dir.glob("M*.md")):
            return
        spec_output = output_path / "spec" / "mandates.json"
        result = PipelineBuilder.generate_spec_file(
            canonical_mandates_dir=canonical_dir,
            output_path=spec_output,
            generated_by="sdd-wizard",
        )
        emitter(
            f"  ✅ Spec file: {result['mandates_written']} mandates → {spec_output}"
        )
    except Exception as exc:
        emitter(f"  ⚠️  Spec file generation skipped: {exc}")


def _generate_source_files(
    output_path: Path,
    language: str,
    emitter: Callable[[str], None],
    mandates: list[dict[str, Any]],
    guidelines: list[dict[str, Any]],
) -> str | None:
    """Write mandates.md, guidelines files, and source README. Returns error msg or None."""
    if not MandatesCompiler(output_path, language, emitter).write(mandates):
        return "Failed to generate mandates.md"
    if not GuidelinesCompiler(output_path, emitter).write(guidelines):
        return "Failed to generate guidelines files"
    if not SourceReadmeCompiler(output_path, language, emitter).write(
        mandates, guidelines
    ):
        return "Failed to generate source README"
    return None


def _load_compiled_governance(
    output_path: Path,
    emitter: Callable[[str], None],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load mandates and guidelines from compiled governance JSON files."""
    try:
        source_dir = output_path / "source"
        mandates: list[dict[str, Any]] = []
        guidelines: list[dict[str, Any]] = []
        core_file = source_dir / "governance-core.json"
        client_file = source_dir / "governance-client.json"
        if core_file.exists():
            with open(core_file, encoding="utf-8") as f:
                for item in json.load(f).get("items", []):
                    if item["type"] == "MANDATE":
                        mandates.append(item)
        if client_file.exists():
            with open(client_file, encoding="utf-8") as f:
                for item in json.load(f).get("items", []):
                    if item["type"] == "GUIDELINE":
                        guidelines.append(item)
        return mandates, guidelines
    except Exception as exc:
        emitter(f"  ❌ Error loading compiled governance: {exc}")
        import traceback

        traceback.print_exc()
        return [], []


class Phase3Compiler:
    """Compile edited markdown templates to governance artifacts."""

    PHASE2_INPUT_DIRNAME = "phase-2-input"
    WIZARD_CONFIG_FILENAME = "wizard-config.json"

    def __init__(
        self,
        markdown_input_path: Path,
        output_path: Path,
        repo_root: Path,
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.markdown_input_path = markdown_input_path
        self.output_path = output_path
        self.repo_root = repo_root
        self.verbose = verbose
        self.language = "Python"
        self.config: dict[str, Any] = {}
        self.selected_guidelines: list[str] = []
        self.client_build_dir = self.markdown_input_path.parent
        self.phase2_input_dir = self.client_build_dir / self.PHASE2_INPUT_DIRNAME
        self.wizard_config_path = self.client_build_dir / self.WIZARD_CONFIG_FILENAME
        self._emit = emitter or print
        self._parser = MarkdownParser()
        self._locator = TemplateLocator(repo_root, self._emit)

    @property
    def last_error(self) -> str | None:
        """Last error message from the template locator."""
        return self._locator.last_error

    @last_error.setter
    def last_error(self, value: str | None) -> None:
        self._locator.last_error = value

    def log(self, message: str) -> None:
        """Emit a verbose-only info message."""
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def validate_template_root(self) -> bool:
        """Return True if the wizard templates directory exists under repo_root."""
        return self._locator.validate_template_root()

    def resolve_language_template_dir(self) -> Path | None:
        """Return the language-specific template directory, or None if missing."""
        return self._locator.resolve_language_dir(self.language)

    def has_staged_input_files(self) -> bool:
        """Return True if any markdown files exist in markdown_input_path."""
        if not self.markdown_input_path.exists():
            return False
        return any(path.is_file() for path in self.markdown_input_path.iterdir())

    def load_wizard_config(self) -> bool:
        """Load wizard.json config from the client build directory."""
        try:
            if self.wizard_config_path.exists():
                with open(self.wizard_config_path, encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.language = self.config.get("language", "Python")
            return True
        except Exception as exc:
            self._emit(f"  ❌ Error loading config: {exc}")
            return False

    def create_structure(self) -> bool:
        """Create .sdd/source/ directory tree."""
        try:
            (self.output_path / "source").mkdir(parents=True, exist_ok=True)
            return True
        except Exception as exc:
            self._emit(f"  ❌ Error creating structure: {exc}")
            return False

    def copy_seedlings(self) -> bool:
        """Copy pre-built seedling JSON files into the output .sdd/seedlings/ directory."""
        return _copy_seedlings(self.repo_root, self.output_path, self._emit)

    def parse_markdown_items(self) -> ParsedItems:
        """Parse staged markdown templates into mandate/guideline dicts."""
        items = self._parser.parse_items(self.markdown_input_path)
        self.selected_guidelines = [g["id"] for g in items["guidelines"]]
        return items

    def compile_with_pipeline_builder(self, items: ParsedItems) -> bool:
        """Run PipelineBuilder on parsed items and save outputs to .sdd/source/."""
        try:
            from sdd_integration.builders.governance.pipeline_builder import (
                PipelineBuilder,
            )

            try:
                paths = get_sdd_paths()
                spec_path = paths.get("docs_meta", paths["client_build"] / "docs-meta")
            except RuntimeError:
                spec_path = (
                    self.repo_root / "generated" / "client" / "build" / "docs-meta"
                )

            builder = PipelineBuilder(
                str(spec_path),
                parsed_items=cast(dict[str, list[dict[str, Any]]], items),
            )
            builder.build()
            source = self.output_path / "source"
            source.mkdir(parents=True, exist_ok=True)
            builder.save_outputs(str(source))
            return True
        except ImportError as exc:
            self._emit(f"❌ PipelineBuilder not available as package: {exc}")
            return False
        except Exception as exc:
            self._emit(f"❌ Pipeline builder error: {exc}")
            import traceback

            traceback.print_exc()
            return False

    def load_compiled_governance(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Load compiled mandates and guidelines from .sdd/source/."""
        return _load_compiled_governance(self.output_path, self._emit)

    def run(self) -> Phase3RunResult:
        """Execute all Phase 3 steps and return a result dict."""
        self._emit("\n⚙️  PHASE 3: Compile Governance from Staged Templates")
        self._emit("=" * 70)
        self._emit(f"  📂 Input (phase-2-input): {self.markdown_input_path}")
        self._emit(f"  📂 Output (client-compiled): {self.output_path}")

        if not self.has_staged_input_files():
            return {
                "success": False,
                "error": (
                    f"No staged files found in {self.markdown_input_path}. "
                    "Run Phase 2 after editing templates to populate phase-2-input."
                ),
            }

        if not self.load_wizard_config():
            return {"success": False, "error": "Failed to load config"}
        if not self.create_structure():
            return {"success": False, "error": "Failed to create .sdd structure"}

        items = self.parse_markdown_items()
        self._emit(
            f"  ✅ Parsed {len(items['mandates'])} mandates, {len(items['guidelines'])} guidelines"
        )

        if not self.compile_with_pipeline_builder(items):
            return {"success": False, "error": "Failed to compile"}

        _generate_spec_file(self.repo_root, self.output_path, self._emit)

        if not self.copy_seedlings():
            return {"success": False, "error": "Failed to copy seedlings"}

        mandates, guidelines = self.load_compiled_governance()
        if mandates or guidelines:
            err = _generate_source_files(
                self.output_path, self.language, self._emit, mandates, guidelines
            )
            if err:
                return {"success": False, "error": err}

        self._emit("  ✅ Compiled governance artifacts")
        self._emit(f"  📂 Output: {self.output_path}")

        return {
            "success": True,
            "output_path": str(self.output_path),
            "language": self.language,
            "files": [
                "governance-core.json",
                "governance-client.json",
                "seedling/",
                "mandates.md",
                "guidelines/",
            ],
            "mandates": len(mandates),
            "guidelines": len(guidelines),
        }
