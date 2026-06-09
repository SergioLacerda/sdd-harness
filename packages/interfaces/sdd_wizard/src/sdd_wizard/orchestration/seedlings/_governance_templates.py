"""Large inline templates extracted from GovernanceSeedsGenerator.

Each function returns a rendered string given the dynamic values that were
previously interpolated inside the generator methods.
"""

from __future__ import annotations


def build_activation_guide(
    fingerprint: str,
    generated_at: str,
    enforcement_label: str,
    enforcement_explanation: str,
    enforcement_behavior: str,
    language: str,
    mandates_list: str,
    guidelines_list: str,
    mandate_ids_joined: str,
) -> str:
    return f"""# Governance Activation Guide
<!-- Governance fingerprint: {fingerprint} -->
<!-- Generated: {generated_at} -->
<!-- Drift check: if fingerprint differs from .sdd/metadata.json, run sdd governance generate -->

## What This Is

This `.sdd/seedlings/` directory contains **auto-activation files** for the Governance Activation Protocol (GAP v1.0).

**Generated for:**
- 🔐 Enforcement Mode: **{enforcement_label}**
  - {enforcement_explanation}
- 🔤 Language: **{language}**
- 📅 Generated: {generated_at}

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
{fingerprint}
```

This fingerprint will be used to detect if governance rules have changed.

---

## 🔒 Enforcement Mode

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
Agent should cite: {mandate_ids_joined}

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

**Expected value:** {fingerprint}

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

**Last updated:** {generated_at}
**Version:** 1.0
**Status:** Ready for activation
    """


def build_verification_script(mandate_ids_str: str) -> str:
    return f'''#!/usr/bin/env python3
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


def build_agent_instructions(
    spec_fingerprint: str,
    generated_at: str,
    mandates_list: str,
) -> str:
    return f"""# SDD Agent Instructions — Authority & Bootstrap

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
   - Expected fingerprint prefix (first 8 chars): {spec_fingerprint}

2. **Read `.sdd/metadata.json`**
   - Extract mandate IDs and titles
   - Example: `"items": [{{"id": "M001", "title": "Clean Architecture"}}, ...]`
   - If `items` is empty or count < 4, governance is broken → escalate to human

3. **Read `.sdd/source/mandates/mandates.md`**
   - Understand enforcement rules for each active mandate
   - If descriptions are stale or missing, request governance regeneration from the human

---

## 3. Active Mandates (read from `.sdd/source/`)

The authoritative human-readable list is in `.sdd/metadata.json`, not this file.

**Current snapshot** (validate this against `.sdd/metadata.json`):
{mandates_list}

---

## 4. Pre-Task Checklist

Before starting any work:

- [ ] `.sdd/metadata.json` read → version, fingerprint, count verified
- [ ] `.sdd/metadata.json` read → mandates extracted
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

## Governance Mode

When operating under SDD via a skill or CLI entry point (`sdd ask`, `sdd-ask`, `sdd-converge`, etc.),
the execution context is **HARD governance mode**.

| Entry point | Mode |
|-------------|------|
| `sdd ask` / `sdd-ask` skill | HARD |
| `sdd-converge`, `sdd-correct`, `sdd-stabilize` | HARD |
| Direct API / notebook / ad-hoc | SOFT |

### HARD Mode Rules

**Rule 1 — Execution gate:**
If `sdd ask` output contains `execution_gate: blocked`, **STOP immediately**.
Report the `gate_reason` to the user. Do not proceed with any action until the user re-authorizes.

**Rule 2 — Git authorization:**
Git state-modifying commands (`add`, `commit`, `push`, `reset`, `merge`, `rebase`, etc.)
are **blocked** unless the current user message contains explicit authorization.
Task completion is NOT authorization. "Fix the tests" is NOT authorization. Only explicit phrases
like "commit this", "push to remote", "run git add and commit" constitute authorization.

**Rule 3 — `intake_index_mode: none` is not permission to act:**
`intake_index_mode: none` means no governance context was indexed.
This is a **signal to surface to the user and stop** — not a green light to proceed.
The agent must report the condition and wait for the user to decide how to continue.

---

## 6. Fallback & Escalation

**If `.sdd/` is incomplete or inconsistent:**
- **STOP EXECUTION IMMEDIATELY. Do not guess or interpolate.**
- Escalate to human: "`.sdd/` is broken: [specific problem]"
- Example: "`.sdd/metadata.json` has only 1 mandate but `.sdd/metadata.json` claims 4"
- You must refuse to bypass the governance gate.

**This is not a blocker — it's a signal that the human should regenerate the workspace.**

---

## 7. Fingerprint Integrity Check

**Fingerprint this version:** `{spec_fingerprint}`
**Generated at:** {generated_at}

Before starting any task, verify bootstrap integrity:

1. Read the fingerprint in your bootstrap file header (e.g. `# Governance fingerprint:` in CLAUDE.md)
2. Compare with `.sdd/metadata.json` → field `governance_fingerprint`
3. If they differ, governance was updated after bootstrap. Run `sdd governance generate` to sync.

If `sdd governance generate` does not update `.sdd/agent-instructions.md`, ask the human to run `sdd wizard` again.

**Golden rule:** Fingerprint in bootstrap file = fingerprint in metadata.json. Divergence = drift.
"""


def build_agents_md(
    spec_fingerprint: str,
    generated_at: str,
    mandate_count: int,
    ids_preview: str,
) -> str:
    preview_str = f" ({ids_preview})" if ids_preview else ""
    return f"""# Agent Bootstrap Paths
<!-- Governance fingerprint: {spec_fingerprint} -->
<!-- Active mandates: {mandate_count}{preview_str} -->
<!-- Generated: {generated_at} -->
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
