"""Governance Seeds."""

import json
import logging
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from ._governance_templates import build_activation_guide, build_verification_script
from .base_generator import BaseSeedlingGenerator

logger = logging.getLogger(__name__)

TOKEN_BUDGET_MEDIUM = "medium"  # nosec B105


class GovernanceSeedsGenerator(BaseSeedlingGenerator):
    """GovernanceSeedsGenerator."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._prompt_commands_mode = "unknown"
        self._prompt_commands_outputs: list[str] = []

    def _resolve_activation_profile(self) -> str:
        enforcement_mode = self.config.get("enforcement_mode", "warn_mode")
        return "critic" if enforcement_mode == "strict_mode" else "executor"

    @property
    def prompt_commands_mode(self) -> str:
        """Prompt Commands Mode."""
        return self._prompt_commands_mode

    def _resolve_skill_set(self) -> list[str]:
        base = [
            "sdd-diagnose",
            "sdd-correct",
            "sdd-converge",
            "sdd-validate-governance",
            "sdd-stabilize",
        ]
        if self.config.get("enforcement_mode", "warn_mode") == "strict_mode":
            base.append("sdd-review-architecture")
        return base

    def _resolve_escalation_mode(self) -> str:
        enforcement_mode = self.config.get("enforcement_mode", "warn_mode")
        return "block" if enforcement_mode == "strict_mode" else "warn"

    def generate_governance_seed(self) -> bool:
        """
        Generate governance.seed.json - GAP v1.0 auto-activation

        This seedling:
        - Auto-activates governance on project load
        - Embeds mandate IDs and fingerprint
        - Includes adoption level and language
        - Triggers SeedlingLoader on "on_project_load"
        """
        try:
            seed_file = self.seedlings_dir / "governance.seed.json"

            seed_data = {
                "schema_version": "1.0.0",
                "auto_activate": self._should_auto_activate(),
                "load_compiled_from": ".sdd/source",
                "on_load": "activate_governance",
                "triggers": ["on_project_load"],
                "description": "Governance Activation Protocol (GAP) v1.0 - Auto-activates on project load",
                "required_context": [
                    ".sdd/source/governance-core.json",
                    ".sdd/seedlings/agent-prep.seed.json",
                ],
                "project_metadata": {
                    "adoption_level": self.config.get("adoption_level", "standard"),
                    "language": self.config.get("language", "python"),
                    "spec_fingerprint": self.spec_fingerprint,
                    "generated_at": self.generated_at,
                    "version": "1.0",
                    "mandates_selected": self.mandate_ids,
                    "guidelines_active": self.active_categories,
                },
                "awakening": {
                    "activation_profile": self._resolve_activation_profile(),
                    "skill_set": self._resolve_skill_set(),
                    "fallback_order": ["skills", "cli"],
                    "response_footer_policy": "always",
                    "budget_policy": {
                        "token_budget": TOKEN_BUDGET_MEDIUM,
                        "max_retries": 1,
                        "timeout_seconds": 120,
                    },
                    "escalation_policy": {
                        "mode": self._resolve_escalation_mode(),
                        "on_repeat_failure": "human_review",
                        "on_critical_violation": "block",
                    },
                    "validation_policy": {
                        "preflight": True,
                        "postcheck": True,
                    },
                    "telemetry_policy": {
                        "emit_runtime_event": True,
                        "emit_audit_event": True,
                        "otel_if_enabled": True,
                    },
                },
                "awakening_flow": [
                    "project_load",
                    "preflight",
                    "context_sync",
                    "skill_profile_resolve",
                    "policy_enforce",
                    "telemetry_emit",
                ],
            }

            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)

            self.log(
                f"✅ Generated governance.seed.json (fingerprint: {self.spec_fingerprint})"
            )
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate governance.seed.json: {e}")
            return False

    def generate_compliance_seed(self) -> bool:
        """
        Generate compliance.seed.json - CI/CD validation hooks

        This seedling:
        - Auto-validates compliance against mandates
        - Triggers pre-commit hooks
        - Sets up GitHub Actions workflows
        - Validates fingerprint hasn't drifted
        """
        try:
            seed_file = self.seedlings_dir / "compliance.seed.json"

            # Get enforcement mode from config (user choice: silent_mode, warn_mode, strict_mode)
            enforcement_mode = self.config.get("enforcement_mode", "warn_mode")

            # Map enforcement modes to actions
            action_map = {
                "silent_mode": "silent",
                "warn_mode": "warn",
                "strict_mode": "block",
            }
            action_on_drift = action_map.get(enforcement_mode, "warn")

            # Map to enforcement level (uppercase for display)
            level_map = {
                "silent_mode": "SILENT",
                "warn_mode": "WARN",
                "strict_mode": "STRICT",
            }
            enforcement_level = level_map.get(enforcement_mode, "WARN")

            seed_data = {
                "auto_activate": True,
                "load_compiled_from": ".sdd/source",
                "on_load": "setup_compliance_hooks",
                "triggers": ["on_git_hook", "on_ci_pipeline"],
                "description": "Compliance Validation - Auto-setup for pre-commit and CI/CD pipelines",
                "required_context": [
                    ".sdd/source/governance-core.json",
                    ".sdd/seedlings/governance.seed.json",
                ],
                "telemetry": {
                    "agent_observability": {
                        "enabled": True,
                        "track_agent_id": True,
                        "log_compliance_rate": True,
                    }
                },
                "compliance_rules": {
                    "signature_validation": {
                        "enabled": True,
                        "signature_mode": "warn",
                        "trusted_keyring": ".sdd/trust/trusted-keys.json",
                        "strict_in_ci": True,
                        "strict_requires_canonical_keyring": True,
                        "unsigned_policy": {
                            "dev": "allowed_warn",
                            "ci_release": "forbidden_block",
                        },
                        "legacy_trust_migration": {
                            "enabled": True,
                            "window_releases": 2,
                            "removal_timeline": "remove legacy keyring fallback after 2 releases",
                        },
                    },
                    "fingerprint_validation": {
                        "enabled": True,
                        "expected_fingerprint": self.spec_fingerprint,
                        "action_on_drift": action_on_drift,
                    },
                    "mandate_enforcement": {
                        "enabled": True,
                        "level": enforcement_level,
                    },
                    "guideline_checks": {
                        "enabled": True,
                        "categories": self.active_categories,
                    },
                },
                "hooks": {
                    "pre_commit": {
                        "enabled": True,
                        "auto_healing": {
                            "enabled": False,  # Feature flag for auto-fixing code via LLM
                            "provider": "gemini-flash",
                            "auto_commit": True,
                        },
                        "checks": [
                            "mandate-compliance",
                            "fingerprint-validation",
                            "guideline-audit",
                        ],
                    },
                    "github_actions": {
                        "enabled": True,
                        "workflow": ".github/workflows/sdd-validation.yml",
                        "triggers": ["push", "pull_request"],
                    },
                },
                "generated_at": self.generated_at,
            }

            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)

            self.log("✅ Generated compliance.seed.json")
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate compliance.seed.json: {e}")
            return False

    def generate_activation_guide(self) -> bool:
        """Generate ACTIVATION_GUIDE.md with step-by-step instructions."""
        try:
            guide_file = self.seedlings_dir / "ACTIVATION_GUIDE.md"

            enforcement_mode = self.config.get("enforcement_mode", "warn_mode")
            enforcement_labels = {
                "silent_mode": "Sem Alertas (Silent)",
                "warn_mode": "Alertas (Warnings only)",
                "strict_mode": "Bloquear (Strict enforcement)",
            }
            enforcement_label = enforcement_labels.get(
                enforcement_mode, "Alertas (Warnings)"
            )
            enforcement_explanations = {
                "silent_mode": "No warnings when violations detected - suitable for learning and experiments",
                "warn_mode": "Show warnings but allow violations to continue - flexible during development",
                "strict_mode": "Block violations in pre-commit hooks - strict enforcement for production",
            }
            enforcement_explanation = enforcement_explanations.get(
                enforcement_mode, "Show warnings only"
            )
            enforcement_behavior = (
                "- **Violations are SILENT**: No warnings or errors, just logging"
                if enforcement_mode == "silent_mode"
                else (
                    "- **Violations show WARNINGS**: Notifications in IDE/logs but no blocking"
                    if enforcement_mode == "warn_mode"
                    else "- **Violations are BLOCKED**: Pre-commit hooks prevent commits with violations"
                )
            )

            content = build_activation_guide(
                fingerprint=self.spec_fingerprint,
                generated_at=self.generated_at,
                enforcement_label=enforcement_label,
                enforcement_explanation=enforcement_explanation,
                enforcement_behavior=enforcement_behavior,
                language=self.config.get("language", "python").upper(),
                mandates_list="\n".join(
                    f"✓ {m['id']}: {m.get('title', 'Unknown')}" for m in self.mandates
                ),
                guidelines_list=(
                    "\n".join(f"✓ {cat.upper()}" for cat in self.active_categories)
                    if self.active_categories
                    else "(None configured)"
                ),
                mandate_ids_joined=", ".join(self.mandate_ids),
            )

            with open(guide_file, "w", encoding="utf-8") as f:
                f.write(content)

            self.log("✅ Generated ACTIVATION_GUIDE.md")
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate activation guide: {e}")
            return False

    def generate_verification_script(self) -> bool:
        """Generate verify.py - verification and health check script."""
        try:
            script_file = self.seedlings_dir / "verify.py"
            content = build_verification_script(
                mandate_ids_str="', '".join(self.mandate_ids)
            )
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(content)
            script_file.chmod(0o755)
            self.log("✅ Generated verify.py")
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate verification script: {e}")
            return False

    def generate_agnostic_agent_instructions(self) -> bool:
        """Generate the centralized, agnostic agent instructions in .sdd/agent-instructions.md"""
        try:
            instructions_dir = self.output_base / ".sdd"
            instructions_dir.mkdir(parents=True, exist_ok=True)

            instructions_file = instructions_dir / "agent-instructions.md"

            # Extract descriptions if available to create a context-rich index
            mandates_lines = []
            for m in self.mandates:
                title = m.get("title", "Unknown")
                desc = m.get("description", m.get("summary", ""))
                if desc:
                    mandates_lines.append(f"- **{m['id']}**: {title} ({desc})")
                else:
                    mandates_lines.append(f"- **{m['id']}**: {title}")

            mandates_list = "\n".join(mandates_lines)

            content = f"""# SDD Agent Instructions — Authority & Bootstrap

**This workspace is governed by Spec Driven Development (SDD).**

You MUST NOT proceed without reading this file in its entirety.

---

## 1. Authority Hierarchy

**The source of truth for all governance is this directory (`.sdd/`).**

```
.sdd/
├── metadata.json                      ← Workspace version + fingerprints
├── agent-instructions.md              ← THIS FILE (you are reading it)
├── compiled/                          ← Optional binary/runtime artifacts (may be absent in template handoff)
└── source/
    ├── governance-core.json           ← Human-readable mandates snapshot — READ THIS
    ├── mandates/mandates.md           ← Mandate descriptions (enforcement rules)
    └── README.md
```

**Do not trust CLAUDE.md, .vscode/, .cursor/, or any other "convenience" pointers over what is in `.sdd/`.**

---

## 2. Mandatory Bootstrap (3 steps)

Before planning, coding, or deciding:

1. **Read `.sdd/metadata.json`**
   - Check `version` (currently 3.0)
   - Check `mandates_count` (count of active mandates)
   - Verify workspace is not stale
   - Expected fingerprint prefix (first 8 chars): {self.spec_fingerprint}

2. **Read `.sdd/source/governance-core.json`**
   - Extract mandate IDs and titles
   - Example: `"items": [{{"id": "M001", "title": "Clean Architecture"}}, ...]`
   - If `items` is empty or count < 4, governance is broken → escalate to human

3. **Read `.sdd/source/mandates/mandates.md`**
   - Understand enforcement rules for each active mandate
   - If descriptions are stale or missing, request governance regeneration from the human

---

## 3. Active Mandates (read from `.sdd/source/`)

The authoritative human-readable list is in `.sdd/source/governance-core.json`, not this file.

**Current snapshot** (validate this against `.sdd/source/governance-core.json`):
{mandates_list}

---

## 4. Pre-Task Checklist

Before starting any work:

- [ ] `.sdd/metadata.json` read → version, fingerprint, count verified
- [ ] `.sdd/source/governance-core.json` read → mandates extracted
- [ ] `.sdd/source/mandates/mandates.md` read → enforcement rules understood
- [ ] No contradictions between this file and `.sdd/` (if found → escalate)

**If you cannot complete this checklist, do not proceed — ask the human first.**

---

## 5. Enforcement Scope

Mandates (HARD) are non-negotiable and always take precedence.

Policies, rules, and guidelines (SOFT) must also be applied when they do not conflict with mandates.

Git protocol (M010), testing, architecture, and token budgets must be followed.

### HARD Constraints — Never Violate

These constraints are non-negotiable. Violation requires human escalation, not auto-correction.

- **M010 (Delivery Hygiene)**: NEVER execute git state-modifying commands (add, commit, push, reset, merge, rebase, branch -D, etc.) autonomously via any tool or shell. ONLY suggest git commands in ready-to-run blocks for human execution.
  - Corollary: Task completion does NOT authorize a commit. Only explicit user request does.
  - Read: `.sdd/source/mandates/mandates.md#M010`

---

## 6. Fallback & Escalation

**If `.sdd/` is incomplete or inconsistent:**
- Do not guess or interpolate
- Escalate to human: "`.sdd/` is broken: [specific problem]"
- Example: "`.sdd/source/governance-core.json` has only 1 mandate but `.sdd/metadata.json` claims 4"

**This is not a blocker — it's a signal that the human should regenerate the workspace.**

---

## 7. Fingerprint Integrity Check

**Fingerprint this version:** `{self.spec_fingerprint}`
**Generated at:** {self.generated_at}

Before starting any task, verify bootstrap integrity:

1. Read the fingerprint in your bootstrap file header (e.g. `# Governance fingerprint:` in CLAUDE.md)
2. Compare with `.sdd/metadata.json` → field `governance_fingerprint`
3. If they differ, governance was updated after bootstrap. Run `sdd governance generate` to sync.

If `sdd governance generate` does not update `.sdd/agent-instructions.md`, ask the human to run `sdd wizard` again.

**Golden rule:** Fingerprint in bootstrap file = fingerprint in metadata.json. Divergence = drift.
"""
            with open(instructions_file, "w", encoding="utf-8") as f:
                f.write(content)

            self.log("✅ Generated agnostic .sdd/agent-instructions.md")
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate agnostic agent instructions: {e}")
            return False

    def generate_prompt_commands(self) -> bool:
        """Generate CLI prompt/command files for all supported AI tools.

        Delegates to generate_agent_prompt_commands() from agent_seeds module.
        """
        try:
            module = import_module("sdd_cli.generators.agent_seeds")
            module_any = cast(Any, module)
            generator = cast(
                Callable[[Path, dict[str, Any]], dict[str, Path]],
                module_any.generate_agent_prompt_commands,
            )

            results = generator(self.output_base, self.config)
            if isinstance(results, dict):
                output_paths = list(results.values())
            elif isinstance(results, list):
                output_paths = list(results)
            else:
                output_paths = []

            if not output_paths:
                self.log(
                    "⚠️  Prompt command generator returned no outputs, using fallback"
                )
                return self._generate_minimal_prompt_commands()

            count = len(output_paths)
            self._prompt_commands_mode = "full"
            self._prompt_commands_outputs = sorted(
                str(Path(path).relative_to(self.output_base)) for path in output_paths
            )
            self.log(f"✅ Generated {count} prompt command files")
            return True
        except ImportError:
            # sdd_cli not available in this context — generate minimal fallback
            self.log("⚠️  sdd_cli not available, generating minimal prompt commands")
            return self._generate_minimal_prompt_commands()
        except Exception as e:
            self.log(
                f"⚠️  Failed to generate prompt commands via sdd_cli ({e}), using fallback"
            )
            return self._generate_minimal_prompt_commands()

    def _generate_minimal_prompt_commands(self) -> bool:
        """Fallback: generate minimal prompt command files without sdd_cli dependency.

        NOTE: CLAUDE.md is now generated exclusively by ai_seeds.py:generate_claude_seed()
        to ensure single point of truth and idempotent generation (no append duplication).
        """
        try:
            _commands_table = (
                "| Task | Command |\n"
                "|------|---------|\n"
                "| Run tests | `sdd test run` |\n"
                "| Lint | `sdd lint run` |\n"
                "| Validate governance | `sdd governance validate` |\n"
                "| Compile governance | `sdd governance compile` |\n"
                "| Runtime status | `sdd runtime status` |\n"
                '| Query context | `sdd ask-full "<question>"` |\n'
                "| Diagnostics | `sdd doctor run --mode real` |\n"
                "| Generate seeds | `sdd governance generate` |\n"
            )

            # NOTE: CLAUDE.md is now generated exclusively by ai_seeds.py:generate_claude_seed()
            # Generating it here caused append duplication. Removed.

            # .cursor/rules/sdd-commands.mdc
            cursor_dir = self.output_base / ".cursor" / "rules"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            (cursor_dir / "sdd-commands.mdc").write_text(
                "---\ndescription: SDD CLI commands\nglobs: ['**/*']\nalwaysApply: false\n---\n\n"
                "# SDD CLI Commands\n\n" + _commands_table,
                encoding="utf-8",
            )

            # .gemini/commands.md
            gemini_dir = self.output_base / ".gemini"
            gemini_dir.mkdir(parents=True, exist_ok=True)
            (gemini_dir / "commands.md").write_text(
                "# SDD CLI Commands for Gemini\n\n" + _commands_table,
                encoding="utf-8",
            )

            self._prompt_commands_mode = "fallback"
            self._prompt_commands_outputs = [
                ".cursor/rules/sdd-commands.mdc",
                ".gemini/commands.md",
            ]

            return True
        except Exception as e:
            self._prompt_commands_mode = "error"
            self._emit(f"  ❌ Failed to generate minimal prompt commands: {e}")
            return False

    def generate_ai_instructions(self) -> bool:
        """Deprecated hook retained for API stability; no legacy bootstrap artifacts are generated."""
        self.log("ℹ️ Skipping deprecated legacy bootstrap instructions generation.")
        return True

    def generate_openai_instructions(self) -> bool:
        """Deprecated hook retained for API stability; no legacy bootstrap artifacts are generated."""
        self.log("ℹ️ Skipping deprecated legacy OpenAI instructions generation.")
        return True

    def generate_agents_md(self) -> bool:
        """Generate root AGENTS.md with agent-specific bootstrap paths."""
        try:
            agents_file = self.output_base / "AGENTS.md"
            ids_preview = ", ".join(self.mandate_ids[:5])
            if len(self.mandate_ids) > 5:
                ids_preview += ", ..."
            content = f"""# Agent Bootstrap Paths
<!-- Governance fingerprint: {self.spec_fingerprint} -->
<!-- Active mandates: {len(self.mandate_ids)}{" (" + ids_preview + ")" if ids_preview else ""} -->
<!-- Generated: {self.generated_at} -->
<!-- Drift check: fingerprint must match .sdd/metadata.json → governance_fingerprint -->

Objective: standardize where each agent must load local instructions, commands, and skills in this project.

## Mandatory Rules

1. Always prioritize local project files/folders before global sources.
2. On startup, each agent must read its dedicated path(s) listed below.
3. If `SKILL.md`, `*.md`, `commands/`, `prompts/`, or equivalent files exist, load them as operational context.
4. You are under governance: always resolve authoritative rules from `.sdd`.
   Initial reference: `.sdd/agent-instructions.md`.

## Governance Authority (`.sdd`)

1. Governance is mandatory and authoritative from `.sdd`.
2. Initial reference: `.sdd/agent-instructions.md`.
3. If any local/global convenience file conflicts with `.sdd`, follow `.sdd`.

## Commands And Skills (Source Of Truth)

1. Commands source of truth: `.sdd/commands`.
2. Skills source of truth: `.sdd/skills`.
3. On startup, agents must load:
   - `.sdd/commands/registry.json`
   - `.sdd/skills/registry.json`
4. For each active command/skill in the registries, agents must read canonical files before use:
   - Commands: `.sdd/commands/<command-id>/command.yaml`
   - Skills: `.sdd/skills/<skill-name>/skill.yaml`
5. If registry or canonical file is missing/inconsistent, register bootstrap drift and continue in safe fallback mode without inventing missing rules.

## Agent-Specific Paths

- Codex: `./.codex/`
- Claude: `./CLAUDE.md`, `./.claude/commands/`
- Gemini: `./.gemini/`
- GitHub Copilot: `./.github/copilot-instructions.md`, `./.github/prompts/`
- Cursor: `./.cursor/rules/`
- VS Code Prompts: `./.github/prompts/`
## Minimal Fallback

If a dedicated path does not exist:

1. Register that local bootstrap is missing.
2. Continue with default agent behavior, without inventing local context.
"""
            agents_file.write_text(content, encoding="utf-8")
            self.log("✅ Generated AGENTS.md bootstrap contract")
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate AGENTS.md: {e}")
            return False

    def _should_auto_activate(self) -> bool:
        """
        Determine if governance should auto-activate based on adoption level

        Returns:
            True for enterprise/standard, False for lite
        """
        adoption_level = str(self.config.get("adoption_level", "standard")).lower()
        return adoption_level != "lite"

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of generated seedlings

        Returns:
            Dict with generation summary
        """
        seedling_files = [
            ("governance.seed.json", "GAP v1.0"),
            ("agent-prep.seed.json", "IDE hooks — all agents"),
            ("compliance.seed.json", "CI/CD"),
            ("copilot.seed.json", "GitHub Copilot redirector"),
            ("gemini.seed.json", "Gemini redirector"),
            ("vscode.seed.json", "VS Code redirector"),
            ("cursor.seed.json", "Cursor IDE redirector"),
            ("claude.seed.json", "Claude Code redirector"),
            ("ACTIVATION_GUIDE.md", "Instructions"),
            ("verify.py", "Verification script"),
        ]
        files = [
            f"{name} ({description})"
            for name, description in seedling_files
            if (self.seedlings_dir / name).exists()
        ]
        if (self.output_base / "AGENTS.md").exists():
            files.append("AGENTS.md (Agent bootstrap contract)")
        if self._prompt_commands_outputs:
            files.append("prompt commands: " + ", ".join(self._prompt_commands_outputs))

        return {
            "seedlings_dir": str(self.seedlings_dir),
            "count": len(files),
            "files": files,
            "fingerprint": self.spec_fingerprint,
            "mandates": self.mandate_ids,
            "guidelines": self.active_categories,
            "adoption_level": self.config.get("adoption_level", "standard"),
            "language": self.config.get("language", "python"),
            "generated_at": self.generated_at,
            "awareness_pack": {
                "prompt_commands_mode": self._prompt_commands_mode,
                "prompt_commands_outputs": self._prompt_commands_outputs,
            },
        }


def generate_agent_instructions_from_config(
    output_base: "Path",
    config: "dict[str, Any]",
) -> bool:
    """Regenerate .sdd/agent-instructions.md from a governance config dict.

    Callable by sdd_cli (governance generate) without running the full wizard.
    Config must contain 'items' list with mandate/guideline dicts.
    """
    from datetime import datetime, timezone
    from pathlib import Path

    try:
        items = config.get("items", [])
        mandates = [i for i in items if str(i.get("type", "")).upper() == "MANDATE"]
        fingerprint = str(
            config.get("core_fingerprint") or config.get("fingerprint") or "unknown"
        )[:16]
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        mandate_ids = [m.get("id", "") for m in mandates if m.get("id")]

        mandates_lines = []
        for m in mandates:
            title = m.get("title", m.get("name", "Unknown"))
            desc = m.get("description", m.get("summary", ""))
            if desc:
                mandates_lines.append(f"- **{m.get('id', '?')}**: {title} ({desc})")
            else:
                mandates_lines.append(f"- **{m.get('id', '?')}**: {title}")
        mandates_list = (
            "\n".join(mandates_lines)
            if mandates_lines
            else "(none — run sdd governance compile)"
        )

        ids_preview = ", ".join(mandate_ids[:5])
        if len(mandate_ids) > 5:
            ids_preview += ", ..."

        instructions_dir = Path(output_base) / ".sdd"
        instructions_dir.mkdir(parents=True, exist_ok=True)
        instructions_file = instructions_dir / "agent-instructions.md"

        content = f"""# SDD Agent Instructions — Authority & Bootstrap
# Regenerated by: sdd governance generate
# Governance fingerprint: {fingerprint}
# Active mandates: {len(mandate_ids)}{" (" + ids_preview + ")" if ids_preview else ""}
# Regenerated at: {generated_at}

**This workspace is governed by Spec Driven Development (SDD).**

---

## 1. Authority Hierarchy

**The source of truth for all governance is `.sdd/`.**

```
.sdd/
├── metadata.json              ← Workspace version + fingerprints
├── agent-instructions.md      ← THIS FILE
└── source/
    ├── governance-core.json   ← Human-readable mandates snapshot
    ├── mandates/mandates.md   ← Mandate descriptions
    └── README.md
```

---

## 2. Mandatory Bootstrap

Before planning, coding, or deciding:

1. **Read `.sdd/metadata.json`** — check version, fingerprint, mandate count
2. **Read `.sdd/source/governance-core.json`** — extract mandate IDs and titles
3. **Read `.sdd/source/mandates/mandates.md`** — understand enforcement rules

---

## 3. Active Mandates

{mandates_list}

---

## 4. Pre-Task Checklist

- [ ] `.sdd/metadata.json` read → version, fingerprint, count verified
- [ ] `.sdd/source/governance-core.json` read → mandates extracted
- [ ] `.sdd/source/mandates/mandates.md` read → enforcement rules understood

---

## 5. Fingerprint Integrity Check

**Fingerprint this version:** `{fingerprint}`
**Regenerated at:** {generated_at}

Verify bootstrap integrity:
1. Compare fingerprint in your bootstrap file (CLAUDE.md, GEMINI.md, etc.)
2. Compare with `.sdd/metadata.json` → field `governance_fingerprint`
3. If they differ → run `sdd governance generate` to sync

---

## 6. Fallback & Escalation

If `.sdd/` is incomplete or inconsistent:
- Do not guess or interpolate
- Escalate to human with specific problem description
"""
        with open(instructions_file, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to regenerate agent-instructions.md: {e}"
        )
        return False
