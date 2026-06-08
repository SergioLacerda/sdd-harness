"""Skill runtime contracts and execution engine.

This module is the canonical authority for capability-oriented execution:
CLI adapters should delegate here and avoid embedding domain execution logic.

Public contracts (SkillRunResult, AwakeningProfile, errors, validate_*) are
re-exported from sdd_skills for consumers that do not need the full engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .telemetry import TelemetrySink

from sdd_skills import (
    AwakeningProfile,
    SkillContractError,
    SkillRunResult,
    UnauthorizedSkillError,
    format_governance_footer,
    validate_awakening_profile,
    validate_skill_definition,
)

from ._skill_contracts import (
    TOKEN_BUDGET_LOW,
    TOKEN_BUDGET_MEDIUM,
    RiskScore,
    SkillDefinition,
    SkillStatus,
)
from ._skill_executor import (
    AskHandler,
    ConvergeHandler,
    CorrectHandler,
    DiagnoseHandler,
    PreRunOutcome,
    SkillExecutor,
    _build_convergence_delta_report,
    _build_diagnosis_attestation,
    _build_diagnosis_report,
    _build_execution_contract,
    _evaluate_correction_gate,
    _get_skill_handler,
)
from ._skill_registry import SkillRegistry

# ---------------------------------------------------------------------------
# Hardcoded fallback registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, SkillDefinition] = {
    "sdd-ask": SkillDefinition(
        name="sdd-ask",
        version="1.0.0",
        category="orchestrator",
        description="Classify user intent and route to the correct governed skill pipeline. Single entrypoint for all user requests.",
        when_to_use=[
            "any user request requiring skill routing",
            "before any other skill",
            "operational fix",
            "diagnostic",
            "analysis",
        ],
        outcomes=[
            "execution_contract",
            "selected_route",
            "confidence_scores",
            "skill_pipeline_result",
        ],
        allowed_tools=[
            "sdd ask",
            "sdd governance validate",
            "sdd runtime status --force",
        ],
        cli_fallback=["sdd runtime status --force", "sdd governance validate"],
        required_permissions=["workspace-read"],
        risk_score="controlled",
        tags=["orchestrator", "routing", "entrypoint"],
        budget_policy={
            "token_budget": TOKEN_BUDGET_MEDIUM,
            "timeout_seconds": 180,
            "max_retries": 1,
        },
        escalation_policy={
            "mode": "warn",
            "require_human_on": [
                "drift.critical",
                "governance.violation",
                "contract.invalid",
            ],
        },
        triggers=[
            "any request",
            "route",
            "classify",
            "help",
            "fix",
            "diagnose",
            "analyze",
        ],
        forbidden=[
            "execute skills without execution_contract",
            "skip confidence gate",
            "skip drift check",
            "route to skill with circuit_open",
        ],
        fallback_to=None,
        idempotent=False,
        context_policy={"max_context_tokens": 1200, "default_detail": "minimal"},
        delegation_policy={
            "enabled": True,
            "triggers": [
                "analyze and plan",
                "create implementation plan",
                "implementation plan",
                "analysis mission",
                "orchestrate",
                "multi-phase analysis",
            ],
            "delegate_to": "analysis_orchestrator",
            "plugin_registry": ".sdd/plugins/registry.yaml",
            "input_transform": {
                "user_prompt": "mission_contract",
                "reviewed_task": "direct_execution",
            },
            "result_handling": {
                "validate_against": ".sdd/contracts/mission-result.schema.yaml",
                "on_invalid": "emit_governance_violation",
                "on_no_provider": "error_no_analysis_provider_registered",
            },
        },
        hard_mode_protocol={
            "read_field": "execution_gate",
            "on_blocked": [
                {"emit": "GovernanceEvent"},
                {"action": "report_to_user"},
                {"action": "stop"},
            ],
            "on_allowed": "continue",
        },
        hard_mode_invariants={
            "pre_conditions": [
                {"gate_check": "execution_gate must be allowed before proceeding"},
                {
                    "git_authorization": "git state-modifying commands require explicit user authorization in current message"
                },
            ],
            "post_conditions": [
                {"no_unauthorized_git": "M010"},
                {"gate_respected": "M015"},
            ],
            "stop_conditions": [
                "execution_gate=blocked",
                "governance_mode=hard and intake_index_mode=none",
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "treat_intake_index_mode_none_as_permission",
            ],
        },
    ),
    "sdd-diagnose": SkillDefinition(
        name="sdd-diagnose",
        version="1.0.0",
        category="analysis",
        description="Diagnose runtime/workspace problems with governed checks.",
        when_to_use=["failing checks", "unknown workspace failures"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["sdd doctor run", "sdd runtime status --force"],
        cli_fallback=["sdd doctor run", "sdd runtime status --force"],
        required_permissions=["workspace-read"],
        risk_score="low",
        tags=["analysis", "runtime", "soft-governance"],
        triggers=[
            "failing",
            "error",
            "traceback",
            "root cause",
            "why",
            "what is wrong",
            "unknown failure",
            "diagnose",
            "analyze",
            "investigate",
        ],
        forbidden=[
            "modify files",
            "apply fixes",
            "run destructive commands",
            "write output",
        ],
        fallback_to=None,
        idempotent=True,
    ),
    "sdd-validate-governance": SkillDefinition(
        name="sdd-validate-governance",
        version="1.1.0",
        category="governance",
        description="Validate governance integrity and runtime preflight.",
        when_to_use=["pre-delivery gate", "compliance checks"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["sdd governance validate", "sdd runtime status"],
        cli_fallback=["sdd governance validate", "sdd runtime status"],
        required_permissions=["workspace-read"],
        risk_score="medium",
        tags=["governance", "validation"],
        triggers=[
            "validate governance",
            "compliance check",
            "pre-delivery",
            "governance check",
            "runtime preflight",
            "fingerprint",
            "integrity check",
        ],
        forbidden=[
            "modify governance files",
            "auto-repair governance",
            "skip validation steps",
            "report ok when checks fail",
        ],
        fallback_to=None,
        idempotent=True,
        context_policy={"max_context_tokens": 1200, "default_detail": "minimal"},
    ),
    "sdd-stabilize": SkillDefinition(
        name="sdd-stabilize",
        version="1.0.0",
        category="operations",
        description="Run stabilization checks before handoff.",
        when_to_use=["before release", "before merge"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["sdd lint run", "sdd test ci-validate"],
        cli_fallback=["sdd lint run", "sdd test ci-validate"],
        required_permissions=["workspace-read"],
        risk_score="medium",
        tags=["stability", "quality-gate"],
        triggers=[
            "before release",
            "before merge",
            "quality gate",
            "stabilize",
            "pre-handoff",
            "ci validation",
            "lint",
            "ready to ship",
        ],
        forbidden=[
            "modify files",
            "auto-fix lint errors",
            "skip failing checks",
            "mark as stable when checks fail",
        ],
        fallback_to="sdd-diagnose",
        idempotent=True,
        context_policy={"max_context_tokens": 1200, "default_detail": "minimal"},
        hard_mode_invariants={
            "pre_conditions": [
                {"gate_check": "execution_gate must be allowed before proceeding"},
                {
                    "git_authorization": "git state-modifying commands require explicit user authorization in current message"
                },
            ],
            "post_conditions": [
                {"no_unauthorized_git": "M010"},
                {"gate_respected": "M015"},
            ],
            "stop_conditions": [
                "execution_gate=blocked",
                "governance_mode=hard and intake_index_mode=none",
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "treat_intake_index_mode_none_as_permission",
            ],
        },
    ),
    "sdd-compress-context": SkillDefinition(
        name="sdd-compress-context",
        version="1.0.0",
        category="economy",
        description="Reduce context footprint while preserving governance context.",
        when_to_use=["high token usage", "long sessions"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["sdd runtime status"],
        cli_fallback=["sdd runtime status"],
        required_permissions=["workspace-read"],
        risk_score="low",
        tags=["token-economy", "context"],
        budget_policy={
            "token_budget": TOKEN_BUDGET_LOW,
            "timeout_seconds": 60,
            "max_retries": 1,
        },
        triggers=[
            "high token usage",
            "context limit",
            "compress",
            "token budget exhausted",
            "long session",
            "context full",
        ],
        forbidden=[
            "modify files",
            "apply fixes",
            "run tests",
            "write output outside context summary",
        ],
        fallback_to=None,
        idempotent=True,
        context_policy={"max_context_tokens": 600, "default_detail": "minimal"},
    ),
    "sdd-review-architecture": SkillDefinition(
        name="sdd-review-architecture",
        version="1.0.0",
        category="architecture",
        description="Review architecture adherence against SDD mandates.",
        when_to_use=["major refactor", "architecture review"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["sdd governance score --verbose"],
        cli_fallback=["sdd governance score --verbose"],
        required_permissions=["workspace-read"],
        risk_score="high",
        tags=["architecture", "review"],
        escalation_policy={
            "mode": "warn",
            "require_human_on": ["critical_violation", "high_risk_change"],
        },
        triggers=[
            "architecture review",
            "refactor",
            "major change",
            "design review",
            "architecture adherence",
            "mandate compliance",
            "structural assessment",
        ],
        forbidden=[
            "modify files",
            "apply fixes",
            "suggest implementation details outside declared scope",
        ],
        fallback_to="sdd-diagnose",
        idempotent=True,
    ),
    "sdd-correct": SkillDefinition(
        name="sdd-correct",
        version="1.0.0",
        category="correction",
        description="Apply minimal targeted correction to a specific governance violation.",
        when_to_use=[
            "specific violation identified by sdd-diagnose",
            "governance drift on a single item",
        ],
        outcomes=["correction_applied", "violation_resolved", "residual_violations"],
        allowed_tools=[
            "sdd governance validate",
            "sdd runtime status --force",
            "sdd doctor run",
        ],
        cli_fallback=["sdd governance validate", "sdd doctor run"],
        required_permissions=["workspace-read", "workspace-write-controlled"],
        risk_score="medium",
        tags=["correction", "governance", "surgical"],
        triggers=[
            "governance violation",
            "fix violation",
            "correct drift",
            "specific violation",
            "targeted fix",
            "correction",
        ],
        forbidden=[
            "modify files outside declared scope",
            "apply multiple corrections in one pass",
            "skip postcheck",
        ],
        fallback_to="sdd-diagnose",
        idempotent=False,
        hard_mode_invariants={
            "pre_conditions": [
                {"gate_check": "execution_gate must be allowed before proceeding"},
                {
                    "git_authorization": "git state-modifying commands require explicit user authorization in current message"
                },
            ],
            "post_conditions": [
                {"no_unauthorized_git": "M010"},
                {"gate_respected": "M015"},
            ],
            "stop_conditions": [
                "execution_gate=blocked",
                "governance_mode=hard and intake_index_mode=none",
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "treat_intake_index_mode_none_as_permission",
            ],
        },
    ),
    "sdd-converge": SkillDefinition(
        name="sdd-converge",
        version="1.0.0",
        category="convergence",
        description="Drive systemic alignment toward spec target after targeted corrections.",
        when_to_use=[
            "residual delta after sdd-correct passes",
            "pattern of drift detected",
        ],
        outcomes=[
            "alignment_score",
            "convergence_plan",
            "delta_report",
            "next_correct_targets",
        ],
        allowed_tools=[
            "sdd ask",
            "sdd governance validate",
            "sdd runtime status --force",
            "sdd doctor run",
        ],
        cli_fallback=["sdd governance validate", "sdd doctor run"],
        required_permissions=["workspace-read", "workspace-write-controlled"],
        risk_score="high",
        tags=["convergence", "governance", "strategic", "alignment"],
        escalation_policy={
            "mode": "block",
            "require_human_on": ["critical_violation", "alignment_score_below_minimum"],
        },
        triggers=[
            "residual drift",
            "pattern of violations",
            "systemic alignment",
            "converge",
            "after correction",
            "alignment score",
            "recurring violations",
        ],
        forbidden=[
            "modify files without prior sdd-correct pass",
            "skip preflight",
            "ignore scope boundaries",
            "execute without execution_contract",
        ],
        fallback_to="sdd-correct",
        idempotent=False,
        hard_mode_invariants={
            "pre_conditions": [
                {"gate_check": "execution_gate must be allowed before proceeding"},
                {
                    "git_authorization": "git state-modifying commands require explicit user authorization in current message"
                },
            ],
            "post_conditions": [
                {"no_unauthorized_git": "M010"},
                {"gate_respected": "M015"},
            ],
            "stop_conditions": [
                "execution_gate=blocked",
                "governance_mode=hard and intake_index_mode=none",
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "treat_intake_index_mode_none_as_permission",
            ],
        },
    ),
    "sdd-pipeline": SkillDefinition(
        name="sdd-pipeline",
        version="1.0.0",
        category="orchestrator",
        description="Orchestrate ask -> diagnose -> correct -> converge as a governed skill pipeline.",
        when_to_use=[
            "strict end-to-end correction flow",
            "pipeline orchestration",
            "multi-stage governed remediation",
        ],
        outcomes=["ask_result", "diagnosis_report", "gate_decision", "delta_report"],
        allowed_tools=[
            "sdd ask",
            "sdd skills run sdd-diagnose",
            "sdd skills run sdd-correct",
            "sdd skills run sdd-converge",
        ],
        cli_fallback=[
            "sdd ask --full",
            "sdd skills run sdd-diagnose",
            "sdd skills run sdd-correct",
            "sdd skills run sdd-converge",
        ],
        required_permissions=["workspace-read", "workspace-write-controlled"],
        risk_score="controlled",
        tags=["pipeline", "orchestration", "governance"],
        triggers=["pipeline", "orchestrate", "ask diagnose correct converge"],
        forbidden=[
            "skip ask stage",
            "skip diagnosis attestation",
            "bypass governance gates",
        ],
        fallback_to="sdd-ask",
        idempotent=False,
    ),
}


# ---------------------------------------------------------------------------
# SkillEngine — thin facade over SkillRegistry + SkillExecutor
# ---------------------------------------------------------------------------


class SkillEngine:
    """Canonical runtime executor for capability-oriented operations."""

    def __init__(
        self,
        sink: TelemetrySink | None = None,
        project_root: Path | str | None = None,
    ) -> None:
        if project_root is None:
            root = Path.cwd()
        elif isinstance(project_root, str):
            root = Path(project_root)
        else:
            root = project_root
        self._registry = SkillRegistry(_REGISTRY, root)
        self._executor = SkillExecutor(self._registry, sink)

    def list_skills(self) -> list[SkillDefinition]:
        """List Skills."""
        return self._registry.list_skills()

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Get Skill."""
        return self._registry.get_skill(name)

    def export_skills_payload(self, fmt: str) -> dict[str, Any]:
        """Export Skills Payload."""
        return self._registry.export_skills_payload(fmt)

    def run_skill(
        self,
        name: str,
        *,
        execute: bool = False,
        profile: str = "default",
        enforcement_mode: str = "warn",
        project_root: Path | None = None,
        context: dict[str, Any] | None = None,
    ) -> SkillRunResult:
        """Run a registered skill through the runtime executor."""
        return self._executor.run_skill(
            name,
            execute=execute,
            profile=profile,
            enforcement_mode=enforcement_mode,
            project_root=project_root,
            context=context,
        )


__all__ = [
    "_REGISTRY",
    "AskHandler",
    "AwakeningProfile",
    "ConvergeHandler",
    "CorrectHandler",
    "DiagnoseHandler",
    "PreRunOutcome",
    "RiskScore",
    "SkillContractError",
    "SkillDefinition",
    "SkillEngine",
    "SkillExecutor",
    "SkillRegistry",
    "SkillRunResult",
    "SkillStatus",
    "TOKEN_BUDGET_LOW",
    "TOKEN_BUDGET_MEDIUM",
    "UnauthorizedSkillError",
    "_build_convergence_delta_report",
    "_build_diagnosis_attestation",
    "_build_diagnosis_report",
    "_build_execution_contract",
    "_evaluate_correction_gate",
    "_get_skill_handler",
    "format_governance_footer",
    "validate_awakening_profile",
    "validate_skill_definition",
]
