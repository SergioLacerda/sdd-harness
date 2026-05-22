"""Governance Seeds."""

import json
import logging
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any, cast

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
        """
        Generate ACTIVATION_GUIDE.md with step-by-step instructions

        This guide:
        - Explains what the seedlings do
        - Provides verification checklist
        - Lists activation steps
        - Includes troubleshooting and enforcement explanation
        """
        try:
            guide_file = self.seedlings_dir / "ACTIVATION_GUIDE.md"

            # Get enforcement configuration
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

            language = self.config.get("language", "python").upper()

            mandates_list = "\n".join(
                f"✓ {m['id']}: {m.get('title', 'Unknown')}" for m in self.mandates
            )
            guidelines_list = (
                "\n".join(f"✓ {cat.upper()}" for cat in self.active_categories)
                if self.active_categories
                else "(None configured)"
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

            content = f"""# Governance Activation Guide
<!-- Governance fingerprint: {self.spec_fingerprint} -->
<!-- Generated: {self.generated_at} -->
<!-- Drift check: if fingerprint differs from .sdd/metadata.json, run sdd governance generate -->

## What This Is

This `.sdd/seedlings/` directory contains **auto-activation files** for the Governance Activation Protocol (GAP v1.0).

**Generated for:**
- 🔐 Enforcement Mode: **{enforcement_label}**
  - {enforcement_explanation}
- 🔤 Language: **{language}**
- 📅 Generated: {self.generated_at}

---

## ✅ Quick Start (3 Steps)

### Step 1: Copy Governance Files

**Linux/macOS:**
```bash
cp -r .sdd/ .
cp -r .sdd/seedlings/ .
ls -la .sdd/source/mandates/
ls -la .sdd/seedlings/
```

**Windows (PowerShell):**
```powershell
Copy-Item -Path .sdd -Destination . -Recurse
Copy-Item -Path .sdd\\seedlings -Destination . -Recurse
dir .sdd\\source\\mandates
dir .sdd\\seedlings
```

### Step 2: Restart IDE

**VS Code:**
```bash
code .
```

**Cursor:**
```bash
cursor .
```

**Windsurf:**
```bash
windsurf .
```

### Step 3: Verify Activation
```bash
# Run verification script
python3 .sdd/seedlings/verify.py

# Expected output:
# ✅ .sdd/source/mandates/ exists
# ✅ .sdd/seedlings/ exists
# ✅ governance.seed.json valid
# ✅ SeedlingLoader works
# ✅ GAP is ACTIVE
```

---

## 📋 Activation Checklist

### Before Activation
- [ ] `.sdd/source/mandates/mandates.md` exists
- [ ] `.sdd/source/guidelines/` exists
- [ ] `.sdd/metadata.json` exists
- [ ] `.sdd/seedlings/` has 5 files (3 seeds + guide + verify)

### During Activation
- [ ] Close all IDE windows
- [ ] Reopen project in IDE
- [ ] Wait 5 seconds for seedlings to load

### After Activation
- [ ] Run `python3 .sdd/seedlings/verify.py`
- [ ] Check SeedlingLoader output
- [ ] Test agent knowledge of mandates
- [ ] Confirm every governed response ends with:
  `SDD GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>`

---

## 🔑 Your Governance Configuration

### Mandates
Your project enforces these mandatory principles:
```
{mandates_list}
```

### Guidelines
Your project follows guidelines in these categories:
```
{guidelines_list}
```

### Fingerprint
Governance fingerprint for validation:
```
{self.spec_fingerprint}
```

This fingerprint will be used to detect if governance rules have changed.

---

## � Enforcement Mode

### Your Configuration: **{enforcement_label}**

{enforcement_explanation}

**How violations are handled:**

{enforcement_behavior}

**What this affects:**
- SeedlingLoader activation behavior
- Pre-commit hook response to violations
- CI/CD pipeline behavior on non-compliance

**To change this after setup:**
1. Edit `.sdd/seedlings/compliance.seed.json`
2. Change `action_on_drift` value
3. Restart IDE

---

## 📁 What Each Seedling Does

### 1. governance.seed.json (GAP v1.0)
**Purpose:** Auto-activates governance on project load
- Loads mandates into memory
- Sets up agent context
- Enables fingerprint validation
- Auto-triggers on `on_project_load`

**You'll know it works when:** Agent chat knows your mandates

### 2. agent-prep.seed.json (IDE Integration)
**Purpose:** Configures AI agents in your IDE
- Supports: Copilot, Claude, Gemini, Local LLM
- Auto-injects `.sdd/source/` context
- Configures IDE hooks (VS Code, Cursor, Windsurf)
- Triggers on project load and editor focus

**You'll know it works when:** Agent gives governance-aware suggestions

### 3. compliance.seed.json (CI/CD Validation)
**Purpose:** Sets up compliance checking
- Validates fingerprint hasn't drifted
- Enforces mandates in CI/CD
- Configures pre-commit hooks
- Triggers on git operations

**You'll know it works when:** Pre-commit blocks non-compliant changes

### 4. ACTIVATION_GUIDE.md (This File)
**Purpose:** Instructions for using seedlings

### 5. verify.py (Verification Script)
**Purpose:** Checks if activation succeeded

---

## Invocation Playbook (Skills + CLI)

Use this routing model when handling user requests:

0. Always run preflight first:
   - `sdd runtime status`
   - `sdd governance validate`
1. Prefer **skills** for capability/intention tasks:
   - `sdd skills list`
   - `sdd skills describe sdd-validate-governance`
   - `sdd skills run sdd-validate-governance`
   - `sdd skills run sdd-diagnose`
2. Use **CLI primitives** for explicit low-level operations:
   - `sdd governance validate`
   - `sdd governance compile`
   - `sdd runtime status`
   - `sdd ask-full "<question>"`
3. Fallback order (default): `skills -> cli`

### Canonical prompts

- Skill-based prompt:
  - `Run the skill \"sdd-validate-governance\" and return policy_result in JSON.`
- CLI-based prompt:
  - `Run sdd governance validate and summarize violations with next steps.`

### Escalation by enforcement mode

- `silent_mode`: log-only, no blocking.
- `warn_mode`: warn and continue.
- `strict_mode`: block on critical violations and request human review.

---

## 🧪 Verification

### Automatic Check
```bash
python3 .sdd/seedlings/verify.py
```

This will verify:
- All required directories exist
- All required files are valid JSON
- SeedlingLoader can discover seeds
- GAP can initialize
- Mandates are loaded

### Manual Checks

**Check 1: Directory Structure**
```bash
find . -name ".sdd" -o -name ".sdd/seedlings"
# Should show both directories
```

**Check 2: Seed Files Valid**
```bash
python3 -m json.tool .sdd/seedlings/governance.seed.json
# Should print formatted JSON
```

**Check 3: SeedlingLoader Works**
```python
from tools.governance.seedling_loader import SeedlingLoader
loader = SeedlingLoader(".")
loaded = loader.load_all()
logger.info(f"Loaded {{len(loaded)}} seedlings")  # Should print: 3
```

**Check 4: Agent Knows Mandates**
In VS Code/Cursor chat, ask:
```
"What are my project mandates?"
```
Agent should cite: {", ".join(self.mandate_ids)}

---

## 🔧 Troubleshooting

### Problem: Seedlings not loading
**Check:**
1. Does `.sdd/seedlings/` directory exist?
2. Are all 5 files present and not corrupted?
3. Run: `python3 .sdd/seedlings/verify.py`

**Fix:**
- Regenerate seedlings from wizard
- Or copy from backup

### Problem: Agent doesn't know mandates
**Check:**
1. Does `.sdd/source/mandates/mandates.md` exist?
2. Is it readable and has content?
3. Restart IDE and try again

**Fix:**
- Verify `.sdd/` was copied completely
- Restart IDE
- Reload agent context

### Problem: Fingerprint validation failing
**Check:**
1. Was `.sdd/metadata.json` copied correctly?
2. Run: `sdd doctor` (if installed)

**Expected value:** {self.spec_fingerprint}

**Fix:**
- Regenerate seedlings if governance changed
- Update expected fingerprint in compliance.seed.json

### Problem: Pre-commit hooks not working
**Check:**
1. Are git hooks installed?
2. Does compliance.seed.json have correct trigger?

**Fix:**
```bash
# Install/reinstall git hooks
python3 scripts/git_hooks.py install
```

---

## 📚 More Information

- [Intelligent Seedlings Guide](../../../../docs/guides/intelligent-seedlings-guide.md)
- [GAP v1.0 Specification](../../../../docs/guides/governance-activation.md)
- [SeedlingLoader Reference](../../../../tools/governance/seedling_loader.py)
- [Agent Integration](../../../../docs/guides/ai-integration.md)

---

## ✨ After Activation

Once activated, your project will:

✅ **Auto-load governance** on project open
✅ **Give agents access** to mandates and guidelines
✅ **Validate compliance** in pre-commit hooks
✅ **Enforce rules** in CI/CD pipelines
✅ **Track fingerprint** to detect drift

---

**Last updated:** {self.generated_at}
**Version:** 1.0
**Status:** Ready for activation
    """

            with open(guide_file, "w", encoding="utf-8") as f:
                f.write(content)

            self.log("✅ Generated ACTIVATION_GUIDE.md")
            return True
        except Exception as e:
            self._emit(f"  ❌ Failed to generate activation guide: {e}")
            return False

    def generate_verification_script(self) -> bool:
        """
        Generate verify.py - Verification and health check script

        This script:
        - Checks directory structure
        - Validates JSON files
        - Tests SeedlingLoader
        - Verifies GAP activation
        - Suggests fixes for common issues
        """
        try:
            script_file = self.seedlings_dir / "verify.py"
            mandate_ids_str = "', '".join(self.mandate_ids)

            content = f'''#!/usr/bin/env python3
"""Governance Activation Verification Script

This script verifies that governance seedlings are properly activated.

Usage:
    python3 verify.py
    python3 verify.py --verbose
"""

import json
import sys
from pathlib import Path


class GovernanceVerifier:
    """Verify governance activation status"""

    def __init__(self, project_root: Path = None, verbose: bool = False):
        self.project_root = project_root or Path.cwd()
        self.verbose = verbose
        self.checks = {{}}
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, message: str):
        if self.verbose:
            logger.info(f"  {{message}}")

    def check_directory(self, path: str, description: str) -> bool:
        full_path = self.project_root / path
        passed = full_path.exists() and full_path.is_dir()
        status = "✅" if passed else "❌"
        logger.info(f"  {{status}} {{description}}: {{path}}")
        self.checks[description] = "pass" if passed else "fail"
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        return passed

    def check_file(self, path: str, description: str, must_be_json: bool = False) -> bool:
        full_path = self.project_root / path
        exists = full_path.exists() and full_path.is_file()

        if not exists:
            logger.warning(f"  ❌ {{description}}: {{path}}")
            self.checks[description] = "fail"
            self.failed += 1
            return False

        if must_be_json:
            try:
                with open(full_path, "r") as f:
                    json.load(f)
                status = "✅"
                result = True
            except json.JSONDecodeError as e:
                status = "❌"
                result = False
                logger.info(f"  {{status}} {{description}} (Invalid JSON): {{path}}")
                self.failed += 1
                return False
        else:
            status = "✅"
            result = True

        logger.info(f"  {{status}} {{description}}: {{path}}")
        self.checks[description] = "pass"
        if result:
            self.passed += 1
        return result

    def check_seedling_loader(self) -> bool:
        """Test SeedlingLoader discovery"""
        try:
            # Robust path discovery: search for tools directory up to 4 levels deep
            root = self.project_root
            found_root = False
            for _ in range(5):
                if (root / "tools" / "governance").exists():
                    sys.path.insert(0, str(root))
                    found_root = True
                    break
                if root == root.parent:
                    break
                root = root.parent

            if not found_root:
                # Fallback: try to find repository root by looking for 'packages' or '.git'
                current_path = Path(__file__).resolve().parent
                repo_root = None
                for _ in range(10): # Limit depth to prevent infinite loop
                    if (current_path / "packages").is_dir() or (current_path / ".git").is_dir():
                        repo_root = current_path
                        break
                    if current_path == current_path.parent: # Reached filesystem root
                        break
                    current_path = current_path.parent

                if repo_root:
                    sys.path.insert(0, str(repo_root))
                else:
                    # Last resort, might not be correct for all setups
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

            from tools.governance.seedling_loader import SeedlingLoader

            loader = SeedlingLoader(self.project_root)
            loaded = loader.load_all()

            if len(loaded) >= 3:
                logger.info(f"  ✅ SeedlingLoader: Discovered {{len(loaded)}} seedlings")
                self.checks["SeedlingLoader"] = "pass"
                self.passed += 1
                return True
            else:
                logger.warning(f"  ⚠️  SeedlingLoader: Found only {{len(loaded)}} seedlings (expected 3+)")
                self.checks["SeedlingLoader"] = "warn"
                self.warnings += 1
                return False
        except Exception as e:
            logger.warning(f"  ⚠️  SeedlingLoader: Could not test")
            self.checks["SeedlingLoader"] = "warn"
            self.warnings += 1
            return False

    def verify_mandates(self) -> bool:
        """Verify mandates are configured"""
        expected = {{'{mandate_ids_str}'}}
        gov_seed_path = self.project_root / ".sdd/seedlings/governance.seed.json"

        try:
            with open(gov_seed_path, "r") as f:
                data = json.load(f)
                configured = set(data.get("project_metadata", {{}}).get("mandates_selected", []))

            if configured == expected:
                logger.info(f"  ✅ Mandates: {{', '.join(expected)}}")
                self.checks["Mandates"] = "pass"
                self.passed += 1
                return True
            else:
                logger.warning(f"  ❌ Mandates mismatch: Expected {{expected}}, got {{configured}}")
                self.checks["Mandates"] = "fail"
                self.failed += 1
                return False
        except Exception as e:
            logger.warning(f"  ❌ Mandates: Could not verify")
            self.checks["Mandates"] = "fail"
            self.failed += 1
            return False

    def run(self) -> bool:
        """Run all verification checks"""
        logger.debug("=" * 70)
        logger.info("🔍 Governance Activation Verification")
        logger.debug("=" * 70)

        logger.info("\\n📂 Directory Structure:")
        self.check_directory(".sdd/source/mandates", ".sdd/source/mandates")
        self.check_directory(".sdd/source/guidelines", ".sdd/source/guidelines")
        self.check_directory(".sdd/runtime", ".sdd/runtime")
        self.check_directory(".sdd/seedlings", ".sdd/seedlings")

        logger.info("\\n📄 Required Files:")
        self.check_file(".sdd/metadata.json", ".sdd/metadata.json", must_be_json=True)
        self.check_file(".sdd/runtime/mandate.bin", "mandate.bin")
        self.check_file(".sdd/source/mandates/mandates.md", "mandates.md")
        self.check_file(".sdd/seedlings/governance.seed.json", "governance.seed.json", must_be_json=True)
        self.check_file(".sdd/seedlings/agent-prep.seed.json", "agent-prep.seed.json", must_be_json=True)
        self.check_file(".sdd/seedlings/compliance.seed.json", "compliance.seed.json", must_be_json=True)

        logger.info("\\n🔑 Governance Configuration:")
        self.verify_mandates()

        logger.info("\\n🧩 Integration Tests:")
        self.check_seedling_loader()

        logger.debug("=" * 70)
        logger.info("📊 Summary")
        logger.debug("=" * 70)
        logger.info(f"✅ Passed: {{self.passed}}")
        if self.warnings:
            logger.info(f"⚠️  Warnings: {{self.warnings}}")
        if self.failed:
            logger.info(f"❌ Failed: {{self.failed}}")

        if self.failed == 0 and self.warnings == 0:
            logger.info("\\n🎉 Governance is fully activated!")
            return True
        elif self.failed == 0:
            logger.info(f"\\n⚠️  Governance is mostly activated ({{self.warnings}} warnings)")
            return True
        else:
            logger.info(f"\\n❌ Governance activation failed ({{self.failed}} critical issues)")
            logger.info("\\n💡 Next Steps:")
            logger.info("   1. Review ACTIVATION_GUIDE.md for troubleshooting")
            logger.info("   2. Verify all files copied from wizard output")
            logger.info("   3. Restart IDE and try again")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify governance activation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--project",
        "-p",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )

    args = parser.parse_args()

    verifier = GovernanceVerifier(project_root=args.project, verbose=args.verbose)
    success = verifier.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
    '''

            with open(script_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Make script executable
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
        import logging

        logging.getLogger(__name__).warning(
            f"Failed to regenerate agent-instructions.md: {e}"
        )
        return False
