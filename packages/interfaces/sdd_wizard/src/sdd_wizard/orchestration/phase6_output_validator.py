"""
OutputValidator — Phase 6 step: verify the generated output structure is complete.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .wizard.models import ValidationDetail


class OutputValidator:
    """Validate that all expected files and directories were produced."""

    def __init__(
        self,
        output_base: Path,
        sdd_dir: Path,
        source_dir: Path,
        runtime_dir: Path,
        mandates_dir: Path,
        guidelines_dir: Path,
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.output_base = output_base
        self.sdd_dir = sdd_dir
        self.source_dir = source_dir
        self.runtime_dir = runtime_dir
        self.mandates_dir = mandates_dir
        self.guidelines_dir = guidelines_dir
        self.guidelines_by_category = guidelines_by_category
        self.verbose = verbose
        self._emit = emitter or print

    def _log(self, message: str) -> None:
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def validate(self) -> tuple[bool, ValidationDetail]:
        """Return (is_valid, detail_dict) after checking all required paths."""
        self._log("Validating output structure")
        result: ValidationDetail = {"valid": True, "checks": {}, "errors": []}

        try:
            required_dirs = [
                self.mandates_dir,
                self.guidelines_dir,
                self.runtime_dir,
                self.output_base / ".github" / "workflows",
            ]
            for req_dir in required_dirs:
                exists = req_dir.exists()
                result["checks"][str(req_dir.relative_to(self.output_base))] = (
                    "OK" if exists else "MISSING"
                )
                if not exists:
                    result["valid"] = False
                    result["errors"].append(f"Missing directory: {req_dir}")

            required_files = [
                (self.mandates_dir / "mandates.md", "Mandates"),
                (self.runtime_dir / "README.md", "Runtime README"),
                (self.source_dir / "README.md", "Source README"),
                (self.sdd_dir / "metadata.json", "Metadata"),
                (self.output_base / ".pre-commit-config.yaml", "Pre-commit Config"),
                (
                    self.output_base / ".github" / "setup-precommit-hook.sh",
                    "Pre-commit Hook Setup",
                ),
                (
                    self.output_base / ".github" / "copilot-instructions.md",
                    "Copilot Instructions",
                ),
                (self.output_base / ".vscode" / "ai-rules.md", "VS Code AI Rules"),
                (self.output_base / ".cursor" / "rules" / "spec.mdc", "Cursor Rules"),
                (
                    self.output_base / ".claude" / "claude-instructions.md",
                    "Claude Instructions",
                ),
                (
                    self.output_base / ".gemini" / "gemini-instructions.md",
                    "Gemini Instructions",
                ),
            ]
            for req_file, desc in required_files:
                exists = req_file.exists()
                result["checks"][f"file: {desc}"] = "OK" if exists else "MISSING"
                if not exists:
                    result["valid"] = False
                    result["errors"].append(f"Missing file: {req_file}")

            for category in self.guidelines_by_category:
                guideline_file = self.guidelines_dir / f"{category}.md"
                exists = guideline_file.exists()
                result["checks"][f"guideline: {category}"] = (
                    "OK" if exists else "MISSING"
                )
                if not exists:
                    result["valid"] = False
                    result["errors"].append(f"Missing guideline: {guideline_file}")

            return result["valid"], result
        except Exception as e:
            self._emit(f"  ❌ Validation failed: {e}")
            result["valid"] = False
            result["errors"].append(str(e))
            return False, result
