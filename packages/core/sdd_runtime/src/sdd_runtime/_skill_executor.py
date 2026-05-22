"""Skill executor — execution engine, handlers, and context builders."""

from __future__ import annotations

import json
import logging
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sdd_skills import SkillRunResult, format_governance_footer

from ._skill_contracts import SkillDefinition, _is_deprecation_due
from ._skill_registry import SkillRegistry
from .learning import FailureLedgerEntry, SupervisedLearningStore
from .telemetry import RuntimeEvent, TelemetrySink

logger = logging.getLogger(__name__)
MIN_DIAGNOSIS_CONFIDENCE_DEFAULT = 0.80
ATTESTATION_TTL_MINUTES_DEFAULT = 30
CONVERGENCE_FREEZE_ALIGNMENT_THRESHOLD = 0.60
REASON_CODE_CONTRACT_MISSING_OR_INVALID = "contract.missing_or_invalid"
REASON_CODE_DIAGNOSIS_MISSING = "diagnosis.missing"
REASON_CODE_DIAGNOSIS_INCONCLUSIVE = "diagnosis.inconclusive"
REASON_CODE_DIAGNOSIS_STALE = "diagnosis.stale"
REASON_CODE_SCOPE_VIOLATION = "scope.violation"
REASON_CODE_EVIDENCE_INSUFFICIENT = "evidence.insufficient"
REASON_CODE_RULE_BLOCKED = "rule.blocked"
REASON_CODE_CONVERGENCE_FREEZE = "convergence.freeze_mode_active"

# ---------------------------------------------------------------------------
# Pre-run outcome
# ---------------------------------------------------------------------------


@dataclass
class PreRunOutcome:
    artifacts: dict[str, Any] = field(default_factory=dict)
    early_result: SkillRunResult | None = None


# ---------------------------------------------------------------------------
# Context builders (shared across handlers)
# ---------------------------------------------------------------------------


def _build_execution_contract(context: dict[str, Any]) -> dict[str, Any]:
    contract = context.get("execution_contract", {})
    if not isinstance(contract, dict):
        contract = {}
    defaults: dict[str, Any] = {
        "task_id": f"task-{uuid4().hex[:12]}",
        "task_type": "unspecified",
        "goal": "unspecified",
        "allowed_paths": [],
        "forbidden_paths": [],
        "allowed_tools": [],
        "validation_set": [],
        "rollback_hint": "manual_rollback",
        "escalation_policy": "human_on_inconclusive_diagnosis",
        "requires_diagnosis": True,
        "min_diagnosis_confidence": MIN_DIAGNOSIS_CONFIDENCE_DEFAULT,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc)
            + timedelta(minutes=ATTESTATION_TTL_MINUTES_DEFAULT)
        ).isoformat(),
    }
    return {**defaults, **contract}


def _build_diagnosis_report(context: dict[str, Any]) -> dict[str, Any]:
    report = context.get("diagnosis_report", {})
    if not isinstance(report, dict):
        report = {}
    defaults: dict[str, Any] = {
        "hypothesis": "unknown",
        "root_cause": "inconclusive",
        "evidence_refs": [],
        "confidence": 0.0,
        "affected_invariants": [],
    }
    return {**defaults, **report}


def _build_diagnosis_attestation(context: dict[str, Any]) -> dict[str, Any]:
    contract = _build_execution_contract(context)
    report = _build_diagnosis_report(context)
    issued_at = datetime.now(timezone.utc)
    defaults = {
        "task_id": contract.get("task_id", ""),
        "hypothesis": report.get("hypothesis", "unknown"),
        "root_cause": report.get("root_cause", "inconclusive"),
        "evidence_refs": report.get("evidence_refs", []),
        "confidence": report.get("confidence", 0.0),
        "affected_invariants": report.get("affected_invariants", []),
        "issued_at": issued_at.isoformat(),
        "expires_at": (
            issued_at + timedelta(minutes=ATTESTATION_TTL_MINUTES_DEFAULT)
        ).isoformat(),
    }
    override = context.get("diagnosis_attestation", {})
    if isinstance(override, dict):
        return {**defaults, **override}
    return defaults


def _build_convergence_delta_report(context: dict[str, Any]) -> dict[str, Any]:
    report = context.get("convergence_delta_report", {})
    if not isinstance(report, dict):
        report = {}
    defaults: dict[str, Any] = {
        "alignment_score": 0.0,
        "residual_violations": [],
        "next_targets": [],
    }
    return {**defaults, **report}


def _evaluate_correction_gate(  # noqa: C901
    context: dict[str, Any],
    *,
    active_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = _build_execution_contract(context)
    freeze_mode_state = context.get("freeze_mode_state", {})
    if isinstance(freeze_mode_state, dict) and bool(freeze_mode_state.get("enabled")):
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_CONVERGENCE_FREEZE,
            "next_action": "run-converge-and-human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    attestation = context.get("diagnosis_attestation", {})
    if not isinstance(attestation, dict):
        attestation = {}
    if not attestation:
        return {
            "decision": "escalate",
            "reason_code": REASON_CODE_DIAGNOSIS_MISSING,
            "next_action": "sdd skills run sdd-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    if str(attestation.get("task_id", "")) != str(contract.get("task_id", "")):
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    contract_expires_at = str(contract.get("expires_at", ""))
    try:
        contract_expires_dt = datetime.fromisoformat(
            contract_expires_at.replace("Z", "+00:00")
        )
    except ValueError:
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    if contract_expires_dt <= datetime.now(timezone.utc):
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    expires_at = str(attestation.get("expires_at", ""))
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_DIAGNOSIS_STALE,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    if expires_dt <= datetime.now(timezone.utc):
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_DIAGNOSIS_STALE,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        }

    evidence = attestation.get("evidence_refs", [])
    confidence = attestation.get("confidence", 0.0)
    allowed_paths = contract.get("allowed_paths", [])
    if not isinstance(evidence, list) or not evidence:
        return {
            "decision": "escalate",
            "reason_code": REASON_CODE_EVIDENCE_INSUFFICIENT,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    min_conf = float(
        contract.get("min_diagnosis_confidence", MIN_DIAGNOSIS_CONFIDENCE_DEFAULT)
    )
    if not isinstance(confidence, int | float) or float(confidence) < min_conf:
        return {
            "decision": "escalate",
            "reason_code": REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
            "next_action": "human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    if not isinstance(allowed_paths, list) or not allowed_paths:
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "narrow-scope",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    planned_paths = context.get("planned_paths", [])
    if (
        isinstance(planned_paths, list)
        and planned_paths
        and any(path not in allowed_paths for path in planned_paths)
    ):
        return {
            "decision": "deny",
            "reason_code": REASON_CODE_SCOPE_VIOLATION,
            "next_action": "narrow-scope",
            "requires_human_review": True,
            "escalate_to_human": True,
        }
    pattern = f"{attestation.get('hypothesis', 'unknown')}|{attestation.get('root_cause', 'unknown')}"
    for rule in active_rules:
        if rule.get("pattern") == pattern:
            return {
                "decision": "deny",
                "reason_code": REASON_CODE_RULE_BLOCKED,
                "next_action": "human-review",
                "requires_human_review": True,
                "escalate_to_human": True,
            }
    return {
        "decision": "allow",
        "reason_code": "ok",
        "next_action": "apply-correction",
        "requires_human_review": False,
        "escalate_to_human": False,
    }


# ---------------------------------------------------------------------------
# Skill handlers
# ---------------------------------------------------------------------------

_FooterFn = Callable[[str, str], str]


class AskHandler:
    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        return PreRunOutcome(
            artifacts={"execution_contract": _build_execution_contract(context)}
        )


class DiagnoseHandler:
    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        report = _build_diagnosis_report(context)
        attestation = _build_diagnosis_attestation(
            {**context, "diagnosis_report": report}
        )
        return PreRunOutcome(
            artifacts={
                "diagnosis_report": report,
                "diagnosis_attestation": attestation,
            }
        )


class CorrectHandler:
    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        gate = _evaluate_correction_gate(
            context, active_rules=learning.list_active_rules()
        )
        artifacts: dict[str, Any] = {"gate_decision": gate}
        if gate["decision"] != "allow":
            diag_report = context.get("diagnosis_report", {})
            entry = FailureLedgerEntry(
                symptom="correction_blocked",
                root_cause=gate["reason_code"],
                fix="escalate_or_re_diagnose",
                validation=gate["next_action"],
                regression=False,
                tags=["gate", "correct"],
                evidence_refs=list(diag_report.get("evidence_refs", []))
                if isinstance(diag_report, dict)
                else [],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            learning.append_failure(entry)
            early = SkillRunResult(
                state="error",
                profile=profile,
                skill=skill.name,
                policy_result="escalated"
                if gate["decision"] == "escalate"
                else "denied",
                reason=gate["reason_code"],
                exit_code=1,
                governance_footer=footer_fn("fallback_cli", "fail"),
                fallback=list(skill.cli_fallback),
                command_results=[],
                artifacts=artifacts,
            )
            return PreRunOutcome(artifacts=artifacts, early_result=early)
        return PreRunOutcome(artifacts=artifacts)

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        diag = context.get("diagnosis_report", {})
        if not isinstance(diag, dict):
            return {}
        learning.append_failure(
            FailureLedgerEntry(
                symptom=str(diag.get("hypothesis", "unknown")),
                root_cause=str(diag.get("root_cause", "unknown")),
                fix="sdd-correct",
                validation="postcheck",
                regression=exit_code != 0,
                tags=["correct", "executed" if exit_code == 0 else "failed"],
                evidence_refs=[
                    ref for ref in diag.get("evidence_refs", []) if isinstance(ref, str)
                ],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return {
            "rule_candidates": [
                candidate.__dict__
                for candidate in learning.generate_candidates_from_ledger()
            ]
        }


class ConvergeHandler:
    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        delta_report = _build_convergence_delta_report(context)
        freeze_mode = {
            "enabled": False,
            "trigger_reason": "",
            "since": "",
            "exit_criteria": "alignment_score>=0.80 and residual_violations<3",
        }
        alignment_score = float(delta_report.get("alignment_score", 0.0))
        residual = delta_report.get("residual_violations", [])
        if alignment_score < CONVERGENCE_FREEZE_ALIGNMENT_THRESHOLD or (
            isinstance(residual, list) and len(residual) >= 3
        ):
            freeze_mode = {
                "enabled": True,
                "trigger_reason": REASON_CODE_CONVERGENCE_FREEZE,
                "since": datetime.now(timezone.utc).isoformat(),
                "exit_criteria": "alignment_score>=0.80 and residual_violations<3",
            }
        new_artifacts: dict[str, Any] = {
            "convergence_delta_report": delta_report,
            "freeze_mode_state": freeze_mode,
        }
        decision = context.get("rule_decision")
        if isinstance(decision, dict):
            new_artifacts["rule_decision"] = learning.decide_rule(
                candidate_id=str(decision.get("candidate_id", "")),
                approved=bool(decision.get("approved", False)),
                reviewer=str(decision.get("reviewer", "human")),
                rationale=str(decision.get("rationale", "")),
                ttl_days=int(decision.get("ttl_days", 30)),
            )
        impact = context.get("rule_impact")
        if isinstance(impact, dict):
            learning.record_rule_impact(
                rule_id=str(impact.get("rule_id", "")),
                rework_delta=float(impact.get("rework_delta", 0.0)),
                false_block_rate=float(impact.get("false_block_rate", 0.0)),
                escalation_delta=float(impact.get("escalation_delta", 0.0)),
                rollback_flag=bool(impact.get("rollback_flag", False)),
            )
            new_artifacts["rule_impact"] = impact
        return new_artifacts


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------


def _get_skill_handler(name: str) -> Any:
    if not name.startswith("sdd-"):
        return None
    suffix = name[4:]
    class_name = suffix.replace("-", " ").title().replace(" ", "") + "Handler"
    cls = globals().get(class_name)
    if cls is None:
        return None
    return cls()


# ---------------------------------------------------------------------------
# SkillExecutor
# ---------------------------------------------------------------------------


class SkillExecutor:
    """Execution engine for skills. Delegates registry lookups to SkillRegistry."""

    def __init__(
        self,
        registry: SkillRegistry,
        sink: TelemetrySink | None = None,
    ) -> None:
        self._registry = registry
        self._sink = sink

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
        context = context or {}
        footer_policy = self._resolve_footer_policy(project_root)
        root = project_root or Path.cwd()
        learning = SupervisedLearningStore(root)

        def _maybe_footer(drift: str, governance: str) -> str:
            if footer_policy != "always":
                return ""
            return format_governance_footer(
                drift=drift, governance=governance, profile=profile
            )

        skill = self._registry.get_skill(name)
        if skill is None:
            result = SkillRunResult(
                state="error",
                profile=profile,
                skill=name,
                policy_result="missing_skill",
                reason="skill not found",
                exit_code=1,
                governance_footer=_maybe_footer("missing_skill", "error"),
                artifacts={},
            )
            self._emit_skill_telemetry(result)
            return result

        from .policy import PolicyEngine

        policy_check = PolicyEngine().evaluate_skill_policy(
            skill_name=name,
            skill=skill,
            enforcement_mode=enforcement_mode,
            project_root=project_root,
        )
        if not policy_check.allowed:
            drift = (
                "handshake_unauthorized"
                if "handshake" in policy_check.reason.lower()
                else "fallback_cli"
            )
            result = SkillRunResult(
                state="error",
                profile=profile,
                skill=name,
                policy_result="unauthorized"
                if drift == "handshake_unauthorized"
                else "blocked",
                reason=policy_check.reason,
                exit_code=1,
                governance_footer=_maybe_footer(drift, "blocked"),
                fallback=list(skill.cli_fallback) if drift == "fallback_cli" else [],
                artifacts={},
            )
            self._emit_skill_telemetry(result)
            return result

        if _is_deprecation_due(skill.deprecated_after):
            warnings.warn(
                f"Skill '{skill.name}' is deprecated (deprecated_after={skill.deprecated_after}).",
                DeprecationWarning,
                stacklevel=2,
            )

        artifacts: dict[str, Any] = {}
        handler = _get_skill_handler(name)

        if handler is not None and hasattr(handler, "pre_run"):
            outcome = handler.pre_run(
                context,
                learning=learning,
                skill=skill,
                profile=profile,
                footer_fn=_maybe_footer,
            )
            artifacts.update(outcome.artifacts)
            if outcome.early_result is not None:
                early: SkillRunResult = outcome.early_result
                self._emit_skill_telemetry(early)
                return early

        exit_code, execution_errors, command_results = (
            self._execute_commands(skill, root) if execute else (0, [], [])
        )
        policy_result = "executed" if execute else "planned"
        reason = (
            "runtime execution completed"
            if execute and exit_code == 0
            else f"execution failed: {'; '.join(execution_errors)}"
            if execute
            else "dry-run policy planning"
        )
        drift = "fallback_cli" if execute else "none"

        if handler is not None and hasattr(handler, "post_run"):
            artifacts.update(
                handler.post_run(
                    context, learning=learning, exit_code=exit_code, artifacts=artifacts
                )
            )

        governance = "ok" if exit_code == 0 else "fail"
        result = SkillRunResult(
            state="ok" if exit_code == 0 else "error",
            profile=profile,
            skill=name,
            policy_result=policy_result,
            reason=reason,
            exit_code=exit_code,
            governance_footer=_maybe_footer(drift, governance),
            fallback=list(skill.cli_fallback),
            command_results=command_results,
            artifacts=artifacts,
        )
        self._emit_skill_telemetry(result)
        return result

    def _execute_commands(
        self, skill: SkillDefinition, root: Path
    ) -> tuple[int, list[str], list[dict[str, Any]]]:
        if not skill.cli_fallback:
            return 0, [], []

        import shlex

        from sdd_core.utils.process import ProcessTimeoutError, SafeProcessRunner

        timeout_seconds = int(skill.budget_policy.get("timeout_seconds", 120))
        exit_code = 0
        execution_errors: list[str] = []
        command_results: list[dict[str, Any]] = []

        try:
            safe_runner: SafeProcessRunner = SafeProcessRunner()
        except Exception as e:
            for cmd in skill.cli_fallback:
                command_results.append(
                    {
                        "command": cmd,
                        "status": "error",
                        "exit_code": 1,
                        "error": f"runner_init_failed: {e}",
                    }
                )
            execution_errors.append(f"SafeProcessRunner init failed: {e}")
            return 1, execution_errors, command_results

        for cmd in skill.cli_fallback:
            cmd_result: dict[str, Any] = {
                "command": cmd,
                "status": "ok",
                "exit_code": 0,
                "error": "",
            }
            try:
                safe_proc = safe_runner.run(
                    shlex.split(cmd),
                    cwd=root,
                    capture_output=False,
                    timeout=timeout_seconds,
                )
                if not safe_proc.success:
                    cmd_result["status"] = "error"
                    cmd_result["exit_code"] = safe_proc.returncode
                    cmd_result["error"] = (
                        safe_proc.stderr or f"command returned {safe_proc.returncode}"
                    )
                    exit_code = safe_proc.returncode or 1
                    execution_errors.append(
                        f"Command '{cmd}' returned {safe_proc.returncode}"
                    )
            except ProcessTimeoutError:
                cmd_result["status"] = "error"
                cmd_result["exit_code"] = 124
                cmd_result["error"] = "timeout"
                exit_code = 124
                execution_errors.append(f"Command '{cmd}' timed out")
            except Exception as e:
                cmd_result["status"] = "error"
                cmd_result["exit_code"] = 1
                cmd_result["error"] = str(e)
                exit_code = 1
                execution_errors.append(f"Command '{cmd}' failed: {e}")
            finally:
                command_results.append(cmd_result)

        return exit_code, execution_errors, command_results

    def _emit_skill_telemetry(self, result: SkillRunResult) -> None:
        if self._sink is None:
            return
        self._sink.emit(
            RuntimeEvent(
                event="runtime.skill.run",
                command=f"skills run {result.skill}",
                status="ok" if result.exit_code == 0 else "fail",
                trace_id=result.trace_id or "",
                details={
                    "profile": result.profile,
                    "policy_result": result.policy_result,
                    "reason": result.reason,
                    "fallback": result.fallback,
                },
            )
        )

    @staticmethod
    def _resolve_footer_policy(project_root: Path | None) -> str:
        root = project_root or Path.cwd()
        state_path = root / ".sdd" / "runtime" / "governance-state.json"
        try:
            if state_path.exists():
                payload = json.loads(state_path.read_text(encoding="utf-8"))
                policy = payload.get("response_footer_policy")
                if isinstance(policy, str) and policy.strip():
                    return policy.strip().lower()
        except (json.JSONDecodeError, KeyError, AttributeError, OSError) as exc:
            logger.debug("Could not read footer policy from %s: %s", state_path, exc)
        return "always"
