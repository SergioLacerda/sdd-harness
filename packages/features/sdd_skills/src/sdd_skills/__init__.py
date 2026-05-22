"""sdd_skills — public contracts for SDD skill execution.

Provides lightweight types and validation that can be imported without
pulling in the full sdd_runtime engine.
"""

from .contracts import (
    AwakeningProfile,
    SkillContractError,
    SkillRunResult,
    UnauthorizedSkillError,
)
from .formatter import format_governance_footer
from .validation import validate_awakening_profile, validate_skill_definition

__all__ = [
    "AwakeningProfile",
    "SkillContractError",
    "SkillRunResult",
    "UnauthorizedSkillError",
    "format_governance_footer",
    "validate_awakening_profile",
    "validate_skill_definition",
]
