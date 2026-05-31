"""User-facing message templates for InteractiveWizard."""

from pathlib import Path


def phase2_instructions_message(
    phase1_path: Path, output_path: Path, copied_files: list[str]
) -> str:
    """Phase2 Instructions Message."""
    return f"""
═══════════════════════════════════════════════════════════════════
PHASE 2: TWO MANUAL REVIEW STEPS
═══════════════════════════════════════════════════════════════════

📂 LOCATION OF YOUR TEMPLATES:
   {phase1_path}

📌 GOVERNANCE STRUCTURE:
   • Mandates (M001, M002): Immutable core rules → ALWAYS REQUIRED
   • Guidelines (G01-G150): Customizable soft rules → YOU DECIDE

═══════════════════════════════════════════════════════════════════
STEP 1: REVIEW & CLASSIFY EACH CRITERION
═══════════════════════════════════════════════════════════════════

FILE ORGANIZATION (by category):
    ├─ mandates-*.md          (Hard rules - cannot be changed)
    └─ guidelines-*.md        (Soft rules - you decide status)

FOR EACH GUIDELINE, SET ITS STATUS:

    [A] REQUIRED (Default)
            → Mandatory in your project
            → Status: `required: true`
            → Example: Core security checks, mandatory testing

    [B] CUSTOMIZABLE
            → Optional but can be customized to fit your needs
            → Status: `custom: true`
            → Example: Code style preferences, flexibility allowed

    [C] OPTIONAL
            → Skip entirely - not relevant to your project
            → Status: `optional: true`
            → Example: Guidelines for unused frameworks, irrelevant rules

EDITING INSTRUCTIONS:
    1. Open each markdown file
    2. Find the **Status:** field (each rule has one)
    3. Change the value:
         FROM: **Status:** `required: true` (default)
         TO:   **Status:** `custom: true` OR `optional: true`
    4. Save file (no YAML conversion needed)

═══════════════════════════════════════════════════════════════════
STEP 2: STAGE REVIEWED FILES FOR PHASE 3
═══════════════════════════════════════════════════════════════════

ACTION:
    ✅ Markdown files copied automatically from:
        {phase1_path}
    ✅ Into:
        {output_path}

COPIED NOW ({len(copied_files)}):
    {", ".join(copied_files)}

WHEN YOU FINISH EDITING IN PHASE 1:
    Re-run Phase 2 to refresh phase-2-input with your latest edits.

FILES STAGED:
    ✓ *.md (templates + README)
    ✓ *.spec
    ✓ *.dsl

═══════════════════════════════════════════════════════════════════
AFTER PHASE 2: RUN PHASE 3
═══════════════════════════════════════════════════════════════════

Phase 3 will:
    1. Read your reviewed markdown files from: {output_path}
    2. Parse all Status fields (required/custom/optional)
    3. Skip items marked as optional
    4. Compile into final governance JSON

═══════════════════════════════════════════════════════════════════

ℹ️  KEY POINTS FOR AI UNDERSTANDING:
   - Governance has 2 immutable mandates (M001, M002)
   - 150 customizable guidelines (G01-G150) with user-selectable status
   - Status field enables filtering: required/custom/optional
   - Phase 2 auto-stages markdown files to phase-2-input
   - Phase 3 automates compilation of reviewed decisions

"""


def phase3_completed_message() -> str:
    """Phase3 Completed Message."""
    return r"""
✅ COMPLETE WIZARD FLOW FINISHED! 🎉

═══════════════════════════════════════════════════════════════════
YOUR GOVERNANCE PROJECT IS READY
═══════════════════════════════════════════════════════════════════

📂 STEP 1: COPY TO YOUR PROJECT
   Copy the complete .sdd/ directory to your project:

   Linux/macOS:
     cp -r .sdd/ .

   Windows (PowerShell):
     Copy-Item -Path .sdd -Destination . -Recurse

📍 STEP 2: ACTIVATE IN YOUR IDE
   1. Open project in VS Code / Cursor / ChatGPT
   2. Restart IDE
   3. Seedlings auto-activate on project load

🔍 STEP 3: VERIFY
   Run the verification script:

   python .sdd/seedlings/verify.py

📚 STEP 4: REVIEW CONFIGURATION
   Check ACTIVATION_GUIDE.md for your governance setup:

   Linux/macOS: cat .sdd/seedlings/ACTIVATION_GUIDE.md
   Windows: Get-Content .sdd\seedlings\ACTIVATION_GUIDE.md

⚙️ STEP 5: VERIFY SKILLS-FIRST AWARENESS
   sdd runtime status
   sdd governance validate
   sdd skills list
   sdd skills run sdd-validate-governance

🧭 STEP 6: PASTE THIS IN YOUR AGENT PROMPT
   Please evaluate governance from project-root files first, then from `.sdd`.
   Read `AGENTS.md`, `.sdd/agent-instructions.md`, `.sdd/metadata.json`,
   and `.sdd/source/mandates/mandates.md`. Confirm:
   1) active mandates loaded, 2) current fingerprint, 3) any drift/blockers,
   4) next governed action using `sdd-*` commands only.
"""


def phase4_success_message(
    mandates: int, guidelines: int, categories: list[str], final_template_dir: Path
) -> str:
    """Phase4 Success Message."""
    return f"""
✅ Phase 4-6 Complete!

📊 Output Summary:
   Mandates: {mandates}
   Guidelines: {guidelines}
   Categories: {", ".join(categories)}

📂 Consolidated Final Template: {final_template_dir}

🎯 Next Steps:
    1. Copy all content from final-template to your destination project
    2. Review .sdd/compiled/ for runtime governance artifacts
    3. Review .sdd/source/ and .sdd/runtime/README.md for governance onboarding
    4. Commit to version control
"""


def phase4_consolidation_failed_message(source_dir: Path, target_dir: Path) -> str:
    """Phase4 Consolidation Failed Message."""
    return (
        "\n❌ Failed to consolidate final template bundle!\n"
        f"   Source: {source_dir}\n"
        f"   Target: {target_dir}"
    )


def phase6_seedlings_success_message(output_base: Path) -> str:
    """Phase6 Seedlings Success Message."""
    return f"""
✅ Generated intelligent seedlings:
   ✓ governance.seed.json (GAP v1.0)
   ✓ agent-prep.seed.json (IDE hooks)
   ✓ compliance.seed.json (CI/CD validation)
   ✓ ACTIVATION_GUIDE.md (Instructions)
   ✓ verify.py (Verification script)
   Location: {output_base}/.sdd/seedlings/
"""
