"""Contract tests for hard-mode governance propagation to agent-instructions.md and skill registry."""

from __future__ import annotations

from pathlib import Path

import pytest
from sdd_runtime.skills import _REGISTRY

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).parent.parent.parent
_CONTROLLED_SKILLS = ["sdd-ask", "sdd-converge", "sdd-correct", "sdd-stabilize"]

_GOVERNANCE_SEEDS = (
    _REPO_ROOT
    / "packages"
    / "interfaces"
    / "sdd_wizard"
    / "src"
    / "sdd_wizard"
    / "orchestration"
    / "seedlings"
    / "_agent_instructions_content.py"
)


class TestAgentInstructionsTemplate:
    def test_governance_mode_section_present_in_template(self):
        """governance_seeds.py template contains ## Governance Mode section."""
        source = _GOVERNANCE_SEEDS.read_text(encoding="utf-8")
        assert "## Governance Mode" in source

    def test_hard_mode_rule1_gate_present(self):
        """Rule 1 (execution_gate=blocked → STOP) is in the template."""
        source = _GOVERNANCE_SEEDS.read_text(encoding="utf-8")
        assert "execution_gate" in source
        assert "blocked" in source

    def test_hard_mode_rule2_git_authorization_present(self):
        """Rule 2 (git commands blocked without authorization) is in the template."""
        source = _GOVERNANCE_SEEDS.read_text(encoding="utf-8")
        assert "Task completion is NOT authorization" in source

    def test_hard_mode_rule3_intake_none_not_permission(self):
        """Rule 3 (intake_index_mode=none is not permission) is in the template."""
        source = _GOVERNANCE_SEEDS.read_text(encoding="utf-8")
        assert "intake_index_mode" in source
        assert "not permission" in source.lower() or "surface" in source.lower()


class TestSkillRegistryInvariants:
    def test_sdd_ask_has_hard_mode_protocol(self):
        """sdd-ask registry entry has hard_mode_protocol defined."""
        assert _REGISTRY["sdd-ask"].hard_mode_protocol is not None

    @pytest.mark.parametrize("skill_name", _CONTROLLED_SKILLS)
    def test_controlled_skill_has_hard_mode_invariants(self, skill_name: str):
        """All four controlled skills have hard_mode_invariants defined."""
        assert _REGISTRY[skill_name].hard_mode_invariants is not None, (
            f"{skill_name} missing hard_mode_invariants in _REGISTRY"
        )

    @pytest.mark.parametrize("skill_name", _CONTROLLED_SKILLS)
    def test_hard_mode_invariants_post_conditions_reference_m010(self, skill_name: str):
        """hard_mode_invariants post_conditions reference M010."""
        invariants = _REGISTRY[skill_name].hard_mode_invariants
        post = invariants.get("post_conditions", [])
        assert "M010" in str(post), (
            f"{skill_name}: M010 not referenced in post_conditions"
        )

    @pytest.mark.parametrize("skill_name", _CONTROLLED_SKILLS)
    def test_hard_mode_invariants_post_conditions_reference_m015(self, skill_name: str):
        """hard_mode_invariants post_conditions reference M015."""
        invariants = _REGISTRY[skill_name].hard_mode_invariants
        post = invariants.get("post_conditions", [])
        assert "M015" in str(post), (
            f"{skill_name}: M015 not referenced in post_conditions"
        )
