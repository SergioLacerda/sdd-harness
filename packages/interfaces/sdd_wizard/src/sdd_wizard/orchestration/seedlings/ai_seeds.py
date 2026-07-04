"""Ai Seeds."""

import json
import logging

from sdd_core.utils.text_io import write_text_utf8

from ._ai_seed_templates import (
    CLAUDE_BOOTSTRAP_SCRIPT,
    CLAUDE_SETTINGS,
    CLAUDE_SETTINGS_HOOK_MODE,
    CODEX_CONFIG_TOML_HOOK_MODE,
    GEMINI_SETTINGS_HOOK_MODE_EXTRA,
    GOVERNANCE_INJECT_SCRIPT,
    build_claude_md,
    build_copilot_instructions,
)
from ._renderer import build_fingerprint_header, render_agent_redirector
from .base_generator import BaseSeedlingGenerator

logger = logging.getLogger(__name__)


class AISeedsGenerator(BaseSeedlingGenerator):
    """AISeedsGenerator."""

    def generate_gemini_seed(self) -> bool:
        """Generate Gemini CLI governance bootstrap: GEMINI.md, settings.json, seed.json."""
        try:
            gemini_dir = self.output_base / ".gemini"
            gemini_dir.mkdir(parents=True, exist_ok=True)
            redirector_content = render_agent_redirector(
                tool_name="Gemini",
                config_paths=[
                    ".gemini/commands.md",
                    ".gemini/antigravity/skills/",
                    "GEMINI.md",
                ],
                fingerprint=self.spec_fingerprint,
                mandate_ids=self.mandate_ids,
                generated_at=self.generated_at,
            )
            write_text_utf8(gemini_dir / "gemini-instructions.md", redirector_content)
            write_text_utf8(self.output_base / "GEMINI.md", redirector_content)
            settings = {"contextFileName": "GEMINI.md"}
            if self.config.get("handshake_mode") == "hook":
                write_text_utf8(
                    gemini_dir / "sdd-governance-inject.py", GOVERNANCE_INJECT_SCRIPT
                )
                (gemini_dir / "sdd-governance-inject.py").chmod(0o755)
                settings["hooks"] = GEMINI_SETTINGS_HOOK_MODE_EXTRA
            write_text_utf8(
                gemini_dir / "settings.json", json.dumps(settings, indent=2) + "\n"
            )
            seed_data = {
                "auto_activate": True,
                "agent": "gemini",
                "description": "Gemini CLI governance bootstrap — redirects to compiled SDD source",
                "load_compiled_from": ".sdd",
                "instructions_ref": "GEMINI.md",
                "commands_ref": ".gemini/commands.md",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [".sdd/metadata.json", "GEMINI.md"],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "gemini.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )
            self.log(
                "✅ Generated Gemini seed (GEMINI.md, settings.json, gemini.seed.json)"
            )
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate Gemini seed: {e}")
            return False

    def generate_copilot_seed(self) -> bool:
        """Generate GitHub Copilot bootstrap instructions."""
        try:
            copilot_dir = self.output_base / ".github"
            copilot_dir.mkdir(parents=True, exist_ok=True)
            fp_header = "\n".join(
                build_fingerprint_header(
                    self.spec_fingerprint, self.mandate_ids, self.generated_at
                )
            )
            content = build_copilot_instructions(fp_header)
            write_text_utf8(copilot_dir / "copilot-instructions.md", content)
            self.log(
                "✅ Generated GitHub Copilot instructions (.github/copilot-instructions.md)"
            )
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate Copilot instructions: {e}")
            return False

    def generate_claude_seed(self) -> bool:
        """Generate CLAUDE.md pointer with governance metadata."""
        try:
            skill_file = self.output_base / "CLAUDE.md"
            claude_dir = self.output_base / ".claude"
            hook_file = claude_dir / "sdd-bootstrap.sh"
            settings_file = claude_dir / "settings.json"
            fp_header = "\n".join(
                build_fingerprint_header(
                    self.spec_fingerprint, self.mandate_ids, self.generated_at
                )
            )
            content = build_claude_md(fp_header)
            write_text_utf8(skill_file, content)
            claude_dir.mkdir(parents=True, exist_ok=True)
            if self.config.get("handshake_mode") == "hook":
                inject_file = claude_dir / "sdd-governance-inject.py"
                write_text_utf8(inject_file, GOVERNANCE_INJECT_SCRIPT)
                inject_file.chmod(0o755)
                write_text_utf8(settings_file, CLAUDE_SETTINGS_HOOK_MODE)
                self.log("✅ Generated CLAUDE.md pointer and Claude prompt-submit hook")
            else:
                write_text_utf8(hook_file, CLAUDE_BOOTSTRAP_SCRIPT)
                hook_file.chmod(0o755)
                write_text_utf8(settings_file, CLAUDE_SETTINGS)
                self.log("✅ Generated CLAUDE.md pointer and Claude bootstrap hook")
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate CLAUDE.md: {e}")
            return False

    def generate_codex_seed(self) -> bool:
        """Generate Codex governance bootstrap seed."""
        try:
            codex_dir = self.output_base / ".codex"
            codex_dir.mkdir(parents=True, exist_ok=True)
            seed_data = {
                "auto_activate": True,
                "agent": "codex",
                "description": "Codex governance bootstrap — routes command aliases through .codex/commands.md",
                "load_compiled_from": ".sdd",
                "commands_ref": ".codex/commands.md",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [".sdd/metadata.json", ".codex/commands.md"],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "codex.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )
            if self.config.get("handshake_mode") == "hook":
                inject_file = codex_dir / "sdd-governance-inject.py"
                write_text_utf8(inject_file, GOVERNANCE_INJECT_SCRIPT)
                inject_file.chmod(0o755)
                write_text_utf8(codex_dir / "config.toml", CODEX_CONFIG_TOML_HOOK_MODE)
                self.log(
                    "✅ Generated Codex seed and prompt-submit hook (.codex/config.toml)"
                )
            else:
                self.log("✅ Generated Codex seed (.sdd/seedlings/codex.seed.json)")
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate Codex seed: {e}")
            return False
