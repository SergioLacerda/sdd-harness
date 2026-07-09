"""ACTIVATION_GUIDE.md sections: invocation playbook, verification, and
troubleshooting/footer. Split out of _activation_guide_template.py to keep
files under the 200-line convention.
"""

from __future__ import annotations


def _invocation_playbook_section() -> str:
    return """## Invocation Playbook (Skills + CLI)

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
  - `Run the skill "sdd-validate-governance" and return policy_result in JSON.`
- CLI-based prompt:
  - `Run sdd governance validate and summarize violations with next steps.`

### Escalation by enforcement mode

- `silent_mode`: log-only, no blocking.
- `warn_mode`: warn and continue.
- `strict_mode`: block on critical violations and request human review.

---

"""


def _verification_section(mandate_ids_joined: str) -> str:
    return f"""## 🧪 Verification

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

"""


def _troubleshooting_section(fingerprint: str) -> str:
    return f"""## 🔧 Troubleshooting

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

### Problem: prompts hanging or erroring in Claude Code / Codex CLI / Gemini CLI
**Check:**
1. Is `handshake_mode: hook` active (every prompt routes through
   `.sdd/runtime/hooks/prompt-submit.py`)?
2. Is `sdd` itself broken, slow, or misconfigured?

**Fix:**
- Run `sdd governance hook disable` to immediately stop the prompt-submit
  hook from firing (safe: it does not touch `.claude/settings.json`,
  `.codex/config.toml`, or `.gemini/settings.json`)
- Run `sdd governance hook status` to check current state
- Run `sdd governance hook enable` once the underlying issue is fixed

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

"""


def _footer_section(generated_at: str) -> str:
    return f"""## 📚 More Information

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
