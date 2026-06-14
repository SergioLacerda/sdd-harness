"""Template for ACTIVATION_GUIDE.md."""

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
    """Render ACTIVATION_GUIDE.md content."""
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
   - `sdd ask --full "<question>"`
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
