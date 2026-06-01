"""Ai Seeds."""

import json
import logging

from sdd_core.utils.text_io import write_text_utf8

from ._renderer import build_fingerprint_header, render_agent_redirector
from .base_generator import BaseSeedlingGenerator

logger = logging.getLogger(__name__)


class AISeedsGenerator(BaseSeedlingGenerator):
    """AISeedsGenerator."""

    _CLAUDE_BOOTSTRAP_SCRIPT = """#!/usr/bin/env sh
set -eu

if [ ! -f ".sdd/metadata.json" ]; then
  echo "[sdd-bootstrap] missing .sdd/metadata.json"
  exit 0
fi

if command -v sdd >/dev/null 2>&1; then
  sdd bootstrap run --session-guard-hours 4 >/dev/null 2>&1 || true
fi
"""

    _CLAUDE_SETTINGS = """{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/sdd-bootstrap.sh"
          }
        ]
      }
    ]
  }
}
"""

    def generate_gemini_seed(self) -> bool:
        """Generate Gemini CLI governance bootstrap: GEMINI.md, settings.json, seed.json."""
        try:
            gemini_dir = self.output_base / ".gemini"
            gemini_dir.mkdir(parents=True, exist_ok=True)

            # 1. .gemini/gemini-instructions.md + GEMINI.md — redirectors with fingerprint
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

            # 3. .gemini/settings.json — Gemini CLI config
            settings = {"contextFileName": "GEMINI.md"}
            write_text_utf8(
                gemini_dir / "settings.json",
                json.dumps(settings, indent=2) + "\n",
            )

            # 4. .sdd/seedlings/gemini.seed.json — activation seed
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
                "required_context": [
                    ".sdd/metadata.json",
                    "GEMINI.md",
                ],
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

            copilot_file = copilot_dir / "copilot-instructions.md"
            fp_header = "\n".join(
                build_fingerprint_header(
                    self.spec_fingerprint, self.mandate_ids, self.generated_at
                )
            )
            content = f"""# GitHub Copilot Governance Bootstrap
{fp_header}

You are operating in a workspace governed by **Spec Driven Development (SDD)**.

## Entrypoint Contract

1. You must learn commands and skills from your custom folder path:
   - `.github/prompts/`
2. You are under governance. Always resolve instructions from `.sdd`.
   Initial reference:
   - `.sdd/agent-instructions.md`

## Commands And Skills (Source Of Truth)

1. Commands source of truth: `.sdd/commands`.
2. Skills source of truth: `.sdd/skills`.
3. On startup, load:
   - `.sdd/commands/registry.json`
   - `.sdd/skills/registry.json`
4. For each active command/skill in registries, read canonical files:
   - Commands: `.sdd/commands/<command-id>/command.yaml`
   - Skills: `.sdd/skills/<skill-name>/skill.yaml`
5. Precedence rule:
   - Local path (`.github/prompts/*`) is for context and ergonomics.
   - `.sdd` is authoritative for routing/policy and wins conflicts.

## Critical Instruction

Read and adhere to the canonical governance rules in:
```
.sdd/agent-instructions.md
```

This file is the **single source of truth** for all governance policies in this workspace.

## Quick Reference

- **Mandate enforcement**: Non-negotiable rules (M001-M010, M015)
- **Governance status**: Run `sdd runtime status` to check workspace health
- **Validation**: Run `sdd governance validate` before finalizing changes
- **Activation**: Governance activates automatically on project load via `.sdd/seedlings/`

## Governance Documentation

All governance documentation lives in `.sdd/source/`:
- `mandates/mandates.md` — Mandate descriptions and enforcement rules
- `guidelines/` — Customizable guidelines by category (if any)
- `README.md` — Onboarding guide for agents

## Operating Rules

- Do not bypass mandatory mandates.
- Prefer generated templates and `.sdd/*` canonical governance over improvised structure.
- When the workspace state is unclear, run `sdd runtime status` first.

## Expected Validation Commands

```bash
sdd governance validate
sdd runtime status
```

## Notes

This bootstrap is intentionally a redirector. Do not rely on framework-external paths.

## Safe Fallback

If registries or canonical files are missing/inconsistent, register bootstrap drift and continue in safe fallback mode without inventing missing rules.
"""
            write_text_utf8(copilot_file, content)
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
            content = f"""# CLAUDE.md
# Generated by: sdd governance generate
# Version: 3.0
{fp_header}

## ⚠️ CRITICAL: Governance Source of Truth

**This Claude workspace is governed by `.sdd/` (Spec Driven Development artifacts).**

## Entrypoint Contract

1. You must learn commands and skills from your custom folder path:
   - `.claude/commands/`
   - `CLAUDE.md`
2. You are under governance. Always resolve instructions from `.sdd`.
   Initial reference:
   - `.sdd/agent-instructions.md`

## Commands And Skills (Source Of Truth)

1. Commands source of truth: `.sdd/commands`.
2. Skills source of truth: `.sdd/skills`.
3. On startup, load:
   - `.sdd/commands/registry.json`
   - `.sdd/skills/registry.json`
4. For each active command/skill in registries, read canonical files:
   - Commands: `.sdd/commands/<command-id>/command.yaml`
   - Skills: `.sdd/skills/<skill-name>/skill.yaml`
5. Precedence rule:
   - Local path (`.claude/*`, `CLAUDE.md`) is for context and ergonomics.
   - `.sdd` is authoritative for routing/policy and wins conflicts.

**You MUST read `.sdd/agent-instructions.md` BEFORE any other action.**

No other file overrides or extends the governance in `.sdd/`. Everything you need is there.

---

## Quick Reference

| File | Purpose |
|------|---------|
| `.sdd/agent-instructions.md` | **START HERE** — Complete agent bootstrap instructions |
| `.sdd/metadata.json` | Workspace version, fingerprints, item counts |
| `.sdd/metadata.json` | Human-readable mandates snapshot |
| `.sdd/source/mandates/mandates.md` | Full mandate descriptions with enforcement rules |

---

## One Rule

**Before planning, coding, or deciding:** read `.sdd/agent-instructions.md`.

If that file says something different from what you remember seeing in CLAUDE.md, **trust `.sdd/agent-instructions.md` — it is authoritative.**

---

## Safe Fallback

If registries or canonical files are missing/inconsistent, register bootstrap drift and continue in safe fallback mode without inventing missing rules.
"""
            # Always write (replace), never append — ensures idempotence
            write_text_utf8(skill_file, content)
            claude_dir.mkdir(parents=True, exist_ok=True)
            write_text_utf8(hook_file, self._CLAUDE_BOOTSTRAP_SCRIPT)
            hook_file.chmod(0o755)
            write_text_utf8(settings_file, self._CLAUDE_SETTINGS)

            self.log("✅ Generated CLAUDE.md pointer and Claude bootstrap hook")
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate CLAUDE.md: {e}")
            return False

    def generate_cortex_seed(self) -> bool:
        """Generate Snowflake Cortex Code governance bootstrap."""
        try:
            cortex_skills_dir = self.output_base / ".cortex" / "skills"
            cortex_skills_dir.mkdir(parents=True, exist_ok=True)

            claude_skills_dir = self.output_base / ".claude" / "skills"
            claude_skills_dir.mkdir(parents=True, exist_ok=True)

            skill_content = render_agent_redirector(
                tool_name="Cortex Code",
                config_paths=[".cortex/skills/", ".claude/skills/"],
                fingerprint=self.spec_fingerprint,
                mandate_ids=self.mandate_ids,
                generated_at=self.generated_at,
            )
            # Primary path: .cortex/skills/
            write_text_utf8(cortex_skills_dir / "sdd-governance.md", skill_content)
            # Compat path: .claude/skills/
            write_text_utf8(claude_skills_dir / "sdd-governance.md", skill_content)

            # .sdd/seedlings/cortex.seed.json
            seed_data = {
                "auto_activate": True,
                "agent": "cortex",
                "description": "Snowflake Cortex Code governance bootstrap — redirects to compiled SDD source",
                "load_compiled_from": ".sdd",
                "instructions_ref": ".cortex/skills/sdd-governance.md",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load"],
                "required_context": [
                    ".sdd/metadata.json",
                    ".cortex/skills/sdd-governance.md",
                ],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "cortex.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )

            self.log(
                "✅ Generated Cortex seed (.cortex/skills/, .claude/skills/, cortex.seed.json)"
            )
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate Cortex seed: {e}")
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
                "required_context": [
                    ".sdd/metadata.json",
                    ".codex/commands.md",
                ],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "codex.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )

            self.log("✅ Generated Codex seed (.sdd/seedlings/codex.seed.json)")
            return True
        except Exception as e:
            logger.warning(f"  ❌ Failed to generate Codex seed: {e}")
            return False
