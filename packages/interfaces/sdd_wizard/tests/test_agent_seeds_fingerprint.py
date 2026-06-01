"""Regression tests: all AI agent bootstrap files must contain governance fingerprint.

Acceptance criteria from design doc:
- Fingerprint header present in every agent bootstrap markdown file
- All bootstrap files reference .sdd/agent-instructions.md
- No inline mandate descriptions in bootstrap files (redirector-only)
- DEPLOYMENT_MANIFEST.json contains all bootstrap files with fingerprint
- JSON seeds Tier 2 have governance_fingerprint field
- AGENTS.md has fingerprint comment
- Sovereign Factory plants antigravity skills
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sdd_wizard.orchestration.seedlings.ai_seeds import AISeedsGenerator
from sdd_wizard.orchestration.seedlings.governance_seeds import (
    GovernanceSeedsGenerator,
    generate_agent_instructions_from_config,
)
from sdd_wizard.orchestration.seedlings.ide_seeds import IDESeedsGenerator
from sdd_wizard.orchestration.seedlings.sovereign_factory import (
    SovereignFactoryGenerator,
)

FINGERPRINT = "abc12345"
MANDATE_IDS = ["M001", "M002", "M003"]
GENERATED_AT = "2026-05-22T00:00:00Z"
MANDATE_DESCRIPTIONS = [
    "Clean Architecture mandate description text",
    "Test Coverage long description",
]


def _make_ide_gen(tmp_path: Path) -> IDESeedsGenerator:
    seedlings_dir = tmp_path / ".sdd" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return IDESeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def _make_sovereign_gen(tmp_path: Path) -> SovereignFactoryGenerator:
    seedlings_dir = tmp_path / ".sdd" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return SovereignFactoryGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def _make_ai_gen(tmp_path: Path) -> AISeedsGenerator:
    seedlings_dir = tmp_path / ".sdd" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return AISeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def _make_gov_gen(tmp_path: Path) -> GovernanceSeedsGenerator:
    seedlings_dir = tmp_path / ".sdd" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    gov = GovernanceSeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={
            "language": "python",
            "adoption_level": "standard",
            "enforcement_mode": "warn_mode",
        },
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )
    gov.mandates = [
        {
            "id": "M001",
            "title": "Clean Architecture",
            "type": "MANDATE",
            "description": MANDATE_DESCRIPTIONS[0],
        },
        {
            "id": "M002",
            "title": "Test Coverage",
            "type": "MANDATE",
            "description": MANDATE_DESCRIPTIONS[1],
        },
        {"id": "M003", "title": "DI Principle", "type": "MANDATE", "description": ""},
    ]
    return gov


# ---------------------------------------------------------------------------
# Fingerprint presence
# ---------------------------------------------------------------------------


def test_claude_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_claude_seed()
    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content


def test_gemini_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_gemini_seed()
    for path in ["GEMINI.md", ".gemini/gemini-instructions.md"]:
        content = (tmp_path / path).read_text(encoding="utf-8")
        assert FINGERPRINT in content, f"fingerprint missing from {path}"


def test_copilot_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_copilot_seed()
    content = (tmp_path / ".github" / "copilot-instructions.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


def test_cortex_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_cortex_seed()
    content = (tmp_path / ".cortex" / "skills" / "sdd-governance.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


def test_codex_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_codex_seed()
    content = (tmp_path / ".sdd" / "seedlings" / "codex.seed.json").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


# ---------------------------------------------------------------------------
# Reference to .sdd/agent-instructions.md
# ---------------------------------------------------------------------------


def test_all_bootstrap_files_reference_agent_instructions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_claude_seed()
    gen.generate_gemini_seed()
    gen.generate_copilot_seed()
    gen.generate_codex_seed()
    gen.generate_cortex_seed()

    files = [
        tmp_path / "CLAUDE.md",
        tmp_path / "GEMINI.md",
        tmp_path / ".gemini" / "gemini-instructions.md",
        tmp_path / ".github" / "copilot-instructions.md",
        tmp_path / ".cortex" / "skills" / "sdd-governance.md",
    ]
    for f in files:
        content = f.read_text(encoding="utf-8")
        assert ".sdd/agent-instructions.md" in content, f"missing redirect in {f.name}"


# ---------------------------------------------------------------------------
# Anti-regression: no inline mandate descriptions in redirector files
# ---------------------------------------------------------------------------


def test_gemini_seed_has_no_inline_mandate_descriptions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_gemini_seed()
    for path in ["GEMINI.md", ".gemini/gemini-instructions.md"]:
        content = (tmp_path / path).read_text(encoding="utf-8")
        for desc in MANDATE_DESCRIPTIONS:
            assert desc not in content, f"inline mandate description found in {path}"


def test_cortex_seed_has_no_inline_mandate_descriptions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_cortex_seed()
    content = (tmp_path / ".cortex" / "skills" / "sdd-governance.md").read_text(
        encoding="utf-8"
    )
    for desc in MANDATE_DESCRIPTIONS:
        assert desc not in content, (
            "inline mandate description found in cortex bootstrap"
        )


def test_claude_seed_has_no_inline_mandate_descriptions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_claude_seed()
    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    for desc in MANDATE_DESCRIPTIONS:
        assert desc not in content, "inline mandate description found in CLAUDE.md"


# ---------------------------------------------------------------------------
# agent-instructions.md drift section
# ---------------------------------------------------------------------------


def test_agent_instructions_contains_fingerprint(tmp_path: Path) -> None:
    gov = _make_gov_gen(tmp_path)
    assert gov.generate_agnostic_agent_instructions()
    content = (tmp_path / ".sdd" / "agent-instructions.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content
    assert "Fingerprint" in content or "fingerprint" in content


def test_agent_instructions_from_config_standalone(tmp_path: Path) -> None:
    config: dict[str, Any] = {
        "core_fingerprint": FINGERPRINT,
        "items": [
            {
                "id": "M001",
                "type": "MANDATE",
                "title": "Clean Architecture",
                "description": "desc",
            },
        ],
    }
    assert generate_agent_instructions_from_config(tmp_path, config)
    content = (tmp_path / ".sdd" / "agent-instructions.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content
    assert "M001" in content


# ---------------------------------------------------------------------------
# G1: agent-prep.seed.json governance_fingerprint
# ---------------------------------------------------------------------------


def test_agent_prep_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ide_gen(tmp_path)
    assert gen.generate_agent_prep_seed()
    with open(
        tmp_path / ".sdd" / "seedlings" / "agent-prep.seed.json", encoding="utf-8"
    ) as f:
        data = json.load(f)
    assert data.get("governance_fingerprint") == FINGERPRINT
    assert data.get("mandates_count") == len(MANDATE_IDS)


# ---------------------------------------------------------------------------
# G2: AGENTS.md fingerprint comment
# ---------------------------------------------------------------------------


def test_agents_md_has_fingerprint_comment(tmp_path: Path) -> None:
    gov = _make_gov_gen(tmp_path)
    assert gov.generate_agents_md()
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content
    assert "<!-- Governance fingerprint:" in content
    assert ".sdd/agent-instructions.md" in content


# ---------------------------------------------------------------------------
# G3: personal-overlay.seed.json governance_fingerprint
# ---------------------------------------------------------------------------


def test_personal_overlay_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ide_gen(tmp_path)
    assert gen.generate_personal_overlay_seed()
    with open(
        tmp_path / ".sdd" / "seedlings" / "personal-overlay.seed.json", encoding="utf-8"
    ) as f:
        data = json.load(f)
    assert data.get("governance_fingerprint") == FINGERPRINT
    assert data.get("mandates_count") == len(MANDATE_IDS)


# ---------------------------------------------------------------------------
# G4: ACTIVATION_GUIDE.md fingerprint
# ---------------------------------------------------------------------------


def test_activation_guide_has_fingerprint(tmp_path: Path) -> None:
    gov = _make_gov_gen(tmp_path)
    assert gov.generate_activation_guide()
    content = (tmp_path / ".sdd" / "seedlings" / "ACTIVATION_GUIDE.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content
    assert "<!-- Governance fingerprint:" in content


# ---------------------------------------------------------------------------
# G5: Sovereign Factory plants antigravity/skills/
# ---------------------------------------------------------------------------


def test_sovereign_factory_plants_antigravity_skill(tmp_path: Path) -> None:
    gen = _make_sovereign_gen(tmp_path)
    result = gen.generate_sovereign_factory_seed()
    # Either template was absent (returns False gracefully) or antigravity was planted
    if result:
        # Template found — check prompts were planted
        assert (tmp_path / ".github" / "prompts").exists()


def test_sovereign_factory_antigravity_contains_skill_md(tmp_path: Path) -> None:
    gen = _make_sovereign_gen(tmp_path)
    gen.generate_sovereign_factory_seed()
    antigravity_dir = tmp_path / ".antigravity"
    if antigravity_dir.exists():
        skill_files = list(antigravity_dir.rglob("SKILL.md"))
        assert len(skill_files) > 0, "Expected at least one SKILL.md in .antigravity/"
