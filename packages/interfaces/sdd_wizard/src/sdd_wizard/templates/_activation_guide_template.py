"""Template for ACTIVATION_GUIDE.md."""

from __future__ import annotations

from ._activation_guide_reference_sections import (
    _footer_section,
    _invocation_playbook_section,
    _troubleshooting_section,
    _verification_section,
)
from ._activation_guide_setup_sections import (
    _checklist_section,
    _enforcement_mode_section,
    _governance_config_section,
    _seedling_descriptions_section,
)


def _intro_and_quickstart_section(
    fingerprint: str,
    generated_at: str,
    enforcement_label: str,
    enforcement_explanation: str,
    language: str,
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

"""


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
    return (
        _intro_and_quickstart_section(
            fingerprint,
            generated_at,
            enforcement_label,
            enforcement_explanation,
            language,
        )
        + _checklist_section()
        + _governance_config_section(mandates_list, guidelines_list, fingerprint)
        + _enforcement_mode_section(
            enforcement_label, enforcement_explanation, enforcement_behavior
        )
        + _seedling_descriptions_section()
        + _invocation_playbook_section()
        + _verification_section(mandate_ids_joined)
        + _troubleshooting_section(fingerprint)
        + _footer_section(generated_at)
    )
