"""Phase 1 Generator — orchestrates governance template generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdd_core.utils.environment import get_sdd_paths
from sdd_wizard.templates.mandate_templates import phase1_readme

from .guideline_renderer import GuidelineRenderer
from .mandate_renderer import MandateRenderer
from .models import Guideline, Mandate, Phase1RunResult
from .spec_parser import GuidelinesDslParser, MandateSpecParser


def _candidate_names(filename: str) -> list[str]:
    if filename == "mandate.spec":
        return ["mandate.spec", "mandate.md"]
    if filename == "guidelines.dsl":
        return ["guidelines.dsl", "guidelines.md"]
    return [filename]


@dataclass
class Phase1Generator:
    """Generate markdown templates from governance source files."""

    PHASE2_INPUT_DIRNAME = "phase-2-input"

    def __init__(
        self,
        core_path: Path,
        output_path: Path,
        verbose: bool = False,
        config: dict[str, Any] | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.core_path = core_path
        self.output_path = output_path
        self.verbose = verbose
        self.config = config or {}
        self.language = self.config.get("language", "Python")
        self.adoption_level = self.config.get("adoption_level", "FULL")
        self.mandates: list[Mandate] = []
        self.guidelines: list[Guideline] = []
        self.last_error: str | None = None
        self.resolved_source_files: dict[str, Path] = {}
        self.local_source_dir = self.output_path.parent
        self.source_spec_dirs: list[Path] = []
        self._emit = emitter or print
        self._mandate_parser = MandateSpecParser(emitter)
        self._guideline_parser = GuidelinesDslParser(emitter)
        self._init_source_dirs()

    def _init_source_dirs(self) -> None:
        try:
            paths = get_sdd_paths()
            docs_meta_dir = paths.get("docs_meta", self.local_source_dir / "docs-meta")
            source_spec_dir = paths.get("source_spec", docs_meta_dir)
            candidates = [
                self.local_source_dir / "docs-meta",
                docs_meta_dir,
                source_spec_dir,
            ]
        except RuntimeError:
            candidates = [self.local_source_dir / "docs-meta"]
        self.source_spec_dirs = list(dict.fromkeys(candidates))

    def log(self, message: str) -> None:
        """Emit a verbose-only info message."""
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def _resolve_source_file(self, filename: str) -> Path | None:
        candidates = [
            source_dir / name
            for source_dir in self.source_spec_dirs
            for name in _candidate_names(filename)
        ]
        for candidate in candidates:
            if candidate.exists():
                self.resolved_source_files[filename] = candidate
                return candidate
        self.last_error = (
            f"{filename} not found. Searched: {', '.join(str(p) for p in candidates)}. "
            "Run 'sdd governance compile' to regenerate governance artifacts."
        )
        self._emit(f"  ❌ {self.last_error}")
        return None

    def parse_mandate_spec(self) -> bool:
        """Parse mandate.spec (or mandate.md) and populate self.mandates."""
        path = self._resolve_source_file("mandate.spec")
        if path is None:
            return False
        content = path.read_text(encoding="utf-8")
        self.mandates = self._mandate_parser.parse(
            content, is_markdown=path.suffix == ".md"
        )
        return len(self.mandates) > 0

    def parse_guidelines_dsl(self) -> bool:
        """Parse guidelines.dsl (or guidelines.md) and populate self.guidelines."""
        path = self._resolve_source_file("guidelines.dsl")
        if path is None:
            return False
        content = path.read_text(encoding="utf-8")
        self.guidelines = self._guideline_parser.parse(
            content, is_markdown=path.suffix == ".md"
        )
        return True

    def _extract_field(self, content: str, field: str) -> str:
        import re

        match = re.search(rf'{field}:\s*"([^"]*)"', content)
        return match.group(1) if match else ""

    def _selector_selection_ids(self) -> list[str]:
        selection = self.config.get("selector_selection", {})
        if isinstance(selection, dict):
            resolved = selection.get("resolved_ids", selection.get("selected_ids"))
            if isinstance(resolved, list) and all(isinstance(i, str) for i in resolved):
                return list(resolved)
        legacy = self.config.get("selector_selection_ids", [])
        if isinstance(legacy, list) and all(isinstance(i, str) for i in legacy):
            return list(legacy)
        return []

    def _apply_selector_selection(self) -> bool:
        selected_ids = self._selector_selection_ids()
        if not selected_ids:
            return True
        selected = set(selected_ids)
        available = {m.id for m in self.mandates} | {g.id for g in self.guidelines}
        unknown = sorted(selected - available)
        if unknown:
            self.last_error = f"Unknown selected IDs: {', '.join(unknown)}"
            self._emit(f"  ❌ {self.last_error}")
            return False
        self.mandates = [m for m in self.mandates if m.id in selected]
        self.guidelines = [g for g in self.guidelines if g.id in selected]
        return True

    def generate_markdown_templates(self) -> bool:
        """Write per-category mandate and guideline markdown files to output_path."""
        self.output_path.mkdir(parents=True, exist_ok=True)
        for pattern in ("mandates-*.md", "guidelines-*.md", "README.md"):
            for stale in self.output_path.glob(pattern):
                if stale.is_file():
                    stale.unlink()
        MandateRenderer(self.output_path, self._emit).render(self.mandates)
        GuidelineRenderer(self.output_path, self._emit).render(self.guidelines)
        readme_content = phase1_readme(
            self.language, self.adoption_level, len(self.mandates), len(self.guidelines)
        )
        (self.output_path / "README.md").write_text(readme_content, encoding="utf-8")
        return True

    def run(self) -> Phase1RunResult:
        """Execute all Phase 1 steps and return a result dict."""
        self._emit("\n📝 PHASE 1: Generate Governance Templates")
        self._emit("=" * 70)

        mandate_file = self._resolve_source_file("mandate.spec")
        if mandate_file is None:
            return {
                "success": False,
                "error": self.last_error or "Failed to locate mandate.spec",
            }

        guidelines_file = self._resolve_source_file("guidelines.dsl")
        if guidelines_file is None:
            return {
                "success": False,
                "error": self.last_error or "Failed to locate guidelines.dsl",
            }

        if not self.parse_mandate_spec():
            return {
                "success": False,
                "error": self.last_error or "Failed to parse mandate.spec",
            }

        if not self.parse_guidelines_dsl():
            return {
                "success": False,
                "error": self.last_error or "Failed to parse guidelines.dsl",
            }

        if not self._apply_selector_selection():
            return {
                "success": False,
                "error": self.last_error or "Failed to apply selector selection",
            }

        if not self.generate_markdown_templates():
            return {"success": False, "error": "Failed to generate markdown templates"}

        (self.output_path.parent / self.PHASE2_INPUT_DIRNAME).mkdir(
            parents=True, exist_ok=True
        )

        self._emit(f"  ✅ Generated {len(self.mandates)} mandates")
        self._emit(f"  ✅ Generated {len(self.guidelines)} guidelines")
        self._emit(f"  📂 Templates: {self.output_path}")

        return {
            "success": True,
            "mandate_count": len(self.mandates),
            "guideline_count": len(self.guidelines),
            "mandate_spec_output": str(mandate_file),
            "output_path": str(self.output_path),
            "mandates": [m.to_dict() for m in self.mandates],
            "guidelines": [g.to_dict() for g in self.guidelines],
        }
