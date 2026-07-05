"""
OutputValidator — Phase 6 step: verify the generated output structure is complete.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .prompt_submit_hooks import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
    CENTRAL_PROMPT_SUBMIT_HOOK,
    SUPPORTED_PROMPT_HOOK_AGENTS,
)
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
        config: dict[str, Any] | None = None,
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
        self.config = config or {}
        self.verbose = verbose
        self._emit = emitter or print

    def _log(self, message: str) -> None:
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def _path_exists(self, path: Path) -> bool:
        return path.exists()

    def _cursor_rules_exist(self) -> bool:
        cursor_rules_dir = self.output_base / ".cursor" / "rules"
        return any(
            self._path_exists(cursor_rules_dir / filename)
            for filename in ("spec.mdc", "sdd-governance.mdc")
        )

    def _optional_hooks_enabled(self) -> bool:
        """Return whether optional hook artifacts are required."""
        return bool(self.config.get("include_optional_hooks", False))

    def _prompt_submit_hooks_enabled(self) -> bool:
        """Return whether prompt-submit governance hooks are required."""
        return self.config.get("handshake_mode") == "hook"

    def _prompt_submit_hook_agents(self) -> set[str]:
        configured = self.config.get("prompt_submit_hook_agents")
        if isinstance(configured, list):
            return {
                str(agent)
                for agent in configured
                if str(agent) in SUPPORTED_PROMPT_HOOK_AGENTS
            }
        return set(SUPPORTED_PROMPT_HOOK_AGENTS)

    def _validate_optional_hook_files(self, result: ValidationDetail) -> None:
        """Validate optional hook artifacts only when explicitly enabled."""
        if not self._optional_hooks_enabled():
            return
        optional_files = [
            self.output_base / ".pre-commit-config.yaml",
            self.output_base / ".github" / "setup-precommit-hook.sh",
        ]
        for optional_file in optional_files:
            exists = self._path_exists(optional_file)
            result["checks"][f"optional: {optional_file.name}"] = (
                "OK" if exists else "MISSING"
            )
            if not exists:
                result["valid"] = False
                result["errors"].append(
                    f"Missing optional-enabled file: {optional_file}"
                )

    def _validate_prompt_submit_hook_files(self, result: ValidationDetail) -> None:
        """Validate prompt-submit hook artifacts when handshake_mode=hook."""
        if not self._prompt_submit_hooks_enabled():
            return
        hook_files = [(self.output_base / CENTRAL_PROMPT_SUBMIT_HOOK, "central hook")]
        agents = self._prompt_submit_hook_agents()
        if "claude" in agents:
            hook_files.append(
                (self.output_base / ".claude" / "settings.json", "Claude adapter")
            )
        if "codex" in agents:
            hook_files.append(
                (self.output_base / ".codex" / "config.toml", "Codex adapter")
            )
        if "gemini" in agents:
            hook_files.append(
                (self.output_base / ".gemini" / "settings.json", "Gemini adapter")
            )
        for hook_file, desc in hook_files:
            exists = self._path_exists(hook_file)
            result["checks"][f"hook: {desc}"] = "OK" if exists else "MISSING"
            if not exists:
                result["valid"] = False
                result["errors"].append(
                    f"Missing handshake_mode=hook file: {hook_file}"
                )
                continue
            if desc != "central hook" and CENTRAL_PROMPT_SUBMIT_COMMAND not in (
                hook_file.read_text(encoding="utf-8")
            ):
                result["valid"] = False
                result["checks"][f"hook command: {desc}"] = "MISSING"
                result["errors"].append(
                    f"Missing central prompt-submit command in: {hook_file}"
                )

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
                (
                    self.output_base / ".github" / "copilot-instructions.md",
                    "Copilot Instructions",
                ),
                (self.output_base / ".vscode" / "ai-rules.md", "VS Code AI Rules"),
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
                exists = self._path_exists(req_file)
                result["checks"][f"file: {desc}"] = "OK" if exists else "MISSING"
                if not exists:
                    result["valid"] = False
                    result["errors"].append(f"Missing file: {req_file}")

            cursor_rules_ok = self._cursor_rules_exist()
            result["checks"]["file: Cursor Rules"] = (
                "OK" if cursor_rules_ok else "MISSING"
            )
            if not cursor_rules_ok:
                result["valid"] = False
                result["errors"].append(
                    "Missing file: expected one of "
                    f"{self.output_base / '.cursor' / 'rules' / 'spec.mdc'} or "
                    f"{self.output_base / '.cursor' / 'rules' / 'sdd-governance.mdc'}"
                )

            self._validate_optional_hook_files(result)
            self._validate_prompt_submit_hook_files(result)

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
