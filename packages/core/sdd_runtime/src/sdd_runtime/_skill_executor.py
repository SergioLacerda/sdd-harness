"""Skill executor — execution engine, handlers, and context builders."""

from __future__ import annotations

import json
import logging
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from sdd_skills import SkillRunResult, format_governance_footer

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

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
    compose_config: dict[str, Any] | None = None


class Handler:
    """Base skill handler lifecycle hooks.

    Example:
        Subclasses override `pre_run`, `post_run`, `can_retry`, `retry_hook`,
        or `timeout_hook` to extend governed execution without changing the
        executor template.
    """

    def can_retry(
        self,
        context: dict[str, Any],
        *,
        exit_code: int,
        error: str,
        attempt_count: int,
    ) -> bool:
        del context, exit_code, error, attempt_count
        return False

    def retry_hook(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: SkillDefinition,
        command: str,
        exit_code: int,
        error: str,
        attempt_count: int,
    ) -> dict[str, Any]:
        del context
        if learning is not None and hasattr(learning, "append_failure"):
            learning.append_failure(
                FailureLedgerEntry(
                    symptom="retry",
                    root_cause=f"{skill.name}:{command}",
                    fix="automatic_retry",
                    validation=f"attempt_{attempt_count}",
                    regression=exit_code != 0,
                    tags=["retry", skill.name],
                    evidence_refs=[error] if error else [],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        return {
            "retry_event": {
                "skill": skill.name,
                "command": command,
                "exit_code": exit_code,
                "error": error,
                "attempt_count": attempt_count,
            }
        }

    def timeout_hook(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: SkillDefinition,
        elapsed_seconds: int,
    ) -> dict[str, Any]:
        if learning is not None and hasattr(learning, "append_failure"):
            learning.append_failure(
                FailureLedgerEntry(
                    symptom="timeout",
                    root_cause=f"skill {skill.name} exceeded {elapsed_seconds}s",
                    fix="retry_with_lower_budget",
                    validation="timeout_hook",
                    regression=True,
                    tags=["timeout", skill.name],
                    evidence_refs=[],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        return {
            "timeout_event": {
                "skill": skill.name,
                "elapsed_seconds": elapsed_seconds,
                "action": "retry_with_lower_budget",
            }
        }


class ContextCarrier:
    def __init__(self, initial_context: dict[str, Any] | None = None) -> None:
        self._layers: list[dict[str, Any]] = []
        self._layer_metadata: list[dict[str, str]] = []
        if initial_context:
            self.push_layer(initial_context, source="initial", skill_name="initial")

    def push_layer(
        self,
        layer: dict[str, Any],
        *,
        source: str,
        skill_name: str,
    ) -> None:
        self._layers.append(dict(layer))
        self._layer_metadata.append({"source": source, "skill": skill_name})
        logger.debug(
            "[ContextCarrier] push_layer source=%s skill=%s keys=%s total_layers=%s",
            source,
            skill_name,
            sorted(layer.keys()),
            len(self._layers),
        )

    def get(self, key: str, default: Any = None) -> Any:
        for layer in reversed(self._layers):
            if key in layer:
                return layer[key]
        return default

    def get_with_source(self, key: str) -> tuple[Any, str | None]:
        for index in range(len(self._layers) - 1, -1, -1):
            layer = self._layers[index]
            if key in layer:
                metadata = self._layer_metadata[index]
                return layer[key], metadata.get("skill")
        return None, None

    def snapshot(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for layer in self._layers:
            merged.update(layer)
        return merged

    def audit_trail(self, key: str) -> list[tuple[Any, str | None]]:
        trail: list[tuple[Any, str | None]] = []
        for index in range(len(self._layers)):
            layer = self._layers[index]
            if key in layer:
                metadata = self._layer_metadata[index]
                trail.append((layer[key], metadata.get("skill")))
        return trail


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


def _summarize_context_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) <= 120:
            return value
        return {
            "type": "string",
            "length": len(value),
            "preview": value[:120],
        }
    if isinstance(value, list):
        sample = value[:3]
        return {
            "type": "list",
            "count": len(value),
            "sample": sample,
        }
    if isinstance(value, dict):
        keys = sorted(str(key) for key in value)
        return {
            "type": "dict",
            "count": len(value),
            "keys": keys[:10],
        }
    return value


def _resolve_project_root_from_context(context: dict[str, Any]) -> Path:
    project_root_raw = context.get("_project_root", Path.cwd())
    return Path(project_root_raw)


def _safe_slug(value: str) -> str:
    normalized = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value
    )
    return normalized.strip("-") or "item"


def _estimate_payload_size(payload: Any) -> int:
    try:
        return len(json.dumps(payload, sort_keys=True, ensure_ascii=True))
    except TypeError:
        return len(str(payload))


def _compress_context(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    critical_keys = {
        "governance_fingerprint",
        "active_mandates",
        "execution_contract",
        "diagnosis_report",
        "diagnosis_attestation",
        "gate_decision",
        "freeze_mode_state",
        "pipeline_state",
        "pipeline_gate_decision",
        "pipeline_escalation",
    }
    compressed: dict[str, Any] = {}
    summarized_keys: list[str] = []
    archival_candidates: list[str] = []

    for key, value in context.items():
        if key in critical_keys:
            compressed[key] = value
            continue
        summarized = _summarize_context_value(value)
        compressed[key] = summarized
        summarized_keys.append(key)
        if (
            isinstance(value, str)
            and len(value) > 120
            or isinstance(value, list | dict)
            and len(value) > 3
        ):
            archival_candidates.append(key)

    original_size = _estimate_payload_size(context)
    compressed_size = _estimate_payload_size(compressed)
    report: dict[str, Any] = {
        "original_key_count": len(context),
        "compressed_key_count": len(compressed),
        "original_estimated_bytes": original_size,
        "compressed_estimated_bytes": compressed_size,
        "preserved_keys": sorted(key for key in context if key in critical_keys),
        "summarized_keys": sorted(summarized_keys),
        "archival_candidates": sorted(archival_candidates),
        "compression_ratio": (
            float(compressed_size) / float(original_size) if original_size > 0 else 1.0
        ),
    }
    return compressed, report


def _archive_context_candidates(
    *,
    project_root: Path,
    context: dict[str, Any],
    archival_candidates: list[str],
) -> dict[str, Any]:
    archive_root = project_root / ".analysis" / "archive"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_dir = archive_root / timestamp
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_items: list[dict[str, Any]] = []
    for key in archival_candidates:
        if key not in context:
            continue
        file_name = f"{_safe_slug(key)}.json"
        target = archive_dir / file_name
        payload = {"key": key, "value": context[key]}
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        archived_items.append(
            {"key": key, "path": str(target.relative_to(project_root))}
        )

    ledger_summary = {
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "count": len(archived_items),
        "items": archived_items,
    }
    summary_path = archive_dir / "compression-summary.json"
    summary_path.write_text(
        json.dumps(ledger_summary, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return {
        "archive_dir": str(archive_dir.relative_to(project_root)),
        "summary_path": str(summary_path.relative_to(project_root)),
        "archived_items": archived_items,
    }


def _build_architecture_review(context: dict[str, Any]) -> dict[str, Any]:
    current_score = context.get("governance_score", 0)
    baseline_score = context.get("baseline_governance_score", current_score)
    if not isinstance(current_score, int | float):
        current_score = 0
    if not isinstance(baseline_score, int | float):
        baseline_score = current_score

    current_violations = context.get("architecture_violations", [])
    baseline_violations = context.get("baseline_architecture_violations", [])
    if not isinstance(current_violations, list):
        current_violations = []
    if not isinstance(baseline_violations, list):
        baseline_violations = []

    added = [item for item in current_violations if item not in baseline_violations]
    resolved = [item for item in baseline_violations if item not in current_violations]

    remediation_proposals: list[str] = []
    if added:
        remediation_proposals.append(
            "review added architectural violations against active mandates"
        )
    if float(current_score) < float(baseline_score):
        remediation_proposals.append(
            "run sdd governance score --verbose and investigate score regression"
        )
    if not remediation_proposals:
        remediation_proposals.append(
            "architecture review is stable; keep current mandate alignment"
        )

    return {
        "governance_score": current_score,
        "baseline_governance_score": baseline_score,
        "architecture_deltas": {
            "score_delta": float(current_score) - float(baseline_score),
            "added_violations": added,
            "resolved_violations": resolved,
        },
        "remediation_proposals": remediation_proposals,
    }


def _load_architecture_baseline(project_root: Path) -> dict[str, Any]:
    baseline_path = (
        project_root / ".analysis" / "archive" / "architecture-baseline.json"
    )
    if not baseline_path.exists():
        return {}
    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_architecture_baseline(project_root: Path, payload: dict[str, Any]) -> Path:
    baseline_path = (
        project_root / ".analysis" / "archive" / "architecture-baseline.json"
    )
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return baseline_path


def _parse_failure_lines(payload: Any, *, mode: str) -> list[str]:
    if not isinstance(payload, str):
        return []
    failures: list[str] = []
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if mode == "lint":
            if "error" in lower or "warning" in lower or "failed" in lower:
                failures.append(line)
        elif mode == "test" and (
            lower.startswith("failed") or " failed" in lower or "error" in lower
        ):
            failures.append(line)
    return failures


def _build_stabilization_report(
    context: dict[str, Any], *, command_results: list[dict[str, Any]]
) -> dict[str, Any]:
    lint_summary = context.get("lint_summary", {})
    test_summary = context.get("test_summary", {})
    if not isinstance(lint_summary, dict):
        lint_summary = {}
    if not isinstance(test_summary, dict):
        test_summary = {}

    lint_failures: list[str] = []
    test_failures: list[str] = []
    critical_issues: list[str] = []

    for item in command_results:
        command = str(item.get("command", ""))
        status = str(item.get("status", "ok"))
        if status == "ok":
            continue
        if "lint" in command:
            lint_failures.append(command)
        elif "test" in command:
            test_failures.append(command)
        else:
            critical_issues.append(command)

    lint_failures.extend(
        [issue for issue in lint_summary.get("failures", []) if isinstance(issue, str)]
    )
    test_failures.extend(
        [issue for issue in test_summary.get("failures", []) if isinstance(issue, str)]
    )
    lint_failures.extend(_parse_failure_lines(context.get("lint_output"), mode="lint"))
    test_failures.extend(_parse_failure_lines(context.get("test_output"), mode="test"))
    critical_issues.extend(
        [
            issue
            for issue in context.get("critical_issues", [])
            if isinstance(issue, str)
        ]
        if isinstance(context.get("critical_issues", []), list)
        else []
    )

    if critical_issues or test_failures:
        decision = "block"
    elif lint_failures:
        decision = "warn"
    else:
        decision = "ready_to_ship"

    return {
        "decision": decision,
        "lint_failures": sorted(dict.fromkeys(lint_failures)),
        "test_failures": sorted(dict.fromkeys(test_failures)),
        "critical_issues": sorted(dict.fromkeys(critical_issues)),
        "escalation_needed": bool(critical_issues),
    }


def _is_retryable_error(*, exit_code: int, error: str) -> bool:
    if exit_code == 124:
        return True
    error_lower = error.lower()
    return any(
        marker in error_lower
        for marker in (
            "temporary",
            "temporarily",
            "timeout",
            "timed out",
            "rate limit",
            "try again",
        )
    )


def _prepare_pipeline_stages(
    carrier: ContextCarrier, compose_config: dict[str, Any]
) -> tuple[list[str], list[str], dict[str, Any]]:
    """Resolve the stage list and any in-progress pipeline state for composition."""
    stages_raw = compose_config.get("stages", [])
    stages = [
        PipelineHandler._normalize_stage_name(stage)
        for stage in stages_raw
        if str(stage).strip()
    ]
    if not stages:
        stages = list(PipelineHandler._DEFAULT_STAGES)

    pipeline_state = carrier.get("pipeline_state", {})
    if not isinstance(pipeline_state, dict):
        pipeline_state = {}
    completed_stages: list[str] = list(pipeline_state.get("completed_stages", []))
    stage_results: dict[str, Any] = dict(pipeline_state.get("stage_results", {}))
    return stages, completed_stages, stage_results


def _classify_execution_outcome(
    *, execute: bool, exit_code: int, execution_errors: list[str]
) -> tuple[str, str, str]:
    """Derive (policy_result, reason, drift) for a completed skill run."""
    if not execute:
        return "planned", "dry-run policy planning", "none"
    policy_result = "timeout" if exit_code == 124 else "executed"
    reason = (
        "runtime execution completed"
        if exit_code == 0
        else f"execution failed: {'; '.join(execution_errors)}"
    )
    return policy_result, reason, "fallback_cli"


def _default_correction_gate_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": "freeze_mode_active",
            "priority": 10,
            "condition": "freeze_mode_enabled",
            "decision": "deny",
            "reason_code": REASON_CODE_CONVERGENCE_FREEZE,
            "next_action": "run-converge-and-human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_missing",
            "priority": 20,
            "condition": "attestation_missing",
            "decision": "escalate",
            "reason_code": REASON_CODE_DIAGNOSIS_MISSING,
            "next_action": "sdd skills run sdd-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_task_mismatch",
            "priority": 30,
            "condition": "attestation_task_mismatch",
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "contract_invalid",
            "priority": 40,
            "condition": "contract_invalid",
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "contract_expired",
            "priority": 50,
            "condition": "contract_expired",
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_invalid",
            "priority": 60,
            "condition": "attestation_invalid",
            "decision": "deny",
            "reason_code": REASON_CODE_DIAGNOSIS_STALE,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_expired",
            "priority": 70,
            "condition": "attestation_expired",
            "decision": "deny",
            "reason_code": REASON_CODE_DIAGNOSIS_STALE,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "evidence_missing",
            "priority": 80,
            "condition": "evidence_missing",
            "decision": "escalate",
            "reason_code": REASON_CODE_EVIDENCE_INSUFFICIENT,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "confidence_too_low",
            "priority": 90,
            "condition": "confidence_too_low",
            "decision": "escalate",
            "reason_code": REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
            "next_action": "human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "allowed_paths_missing",
            "priority": 100,
            "condition": "allowed_paths_missing",
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "narrow-scope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "scope_violation",
            "priority": 110,
            "condition": "scope_violation",
            "decision": "deny",
            "reason_code": REASON_CODE_SCOPE_VIOLATION,
            "next_action": "narrow-scope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "matching_active_rule",
            "priority": 120,
            "condition": "matching_active_rule",
            "decision": "deny",
            "reason_code": REASON_CODE_RULE_BLOCKED,
            "next_action": "human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "default_allow",
            "priority": 1000,
            "condition": "always",
            "decision": "allow",
            "reason_code": "ok",
            "next_action": "apply-correction",
            "requires_human_review": False,
            "escalate_to_human": False,
        },
    ]


def _load_gate_rules(
    *,
    project_root: Path,
    skill: SkillDefinition,
) -> list[dict[str, Any]]:
    gate_rules_file = str(skill.config.get("gate_rules_file", "")).strip()
    if not gate_rules_file or yaml is None:
        return _default_correction_gate_rules()
    rules_path = project_root / gate_rules_file
    if not rules_path.exists():
        return _default_correction_gate_rules()
    payload = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    rules = payload.get("rules", [])
    if not isinstance(rules, list) or not rules:
        return _default_correction_gate_rules()
    normalized = [rule for rule in rules if isinstance(rule, dict)]
    if not normalized:
        return _default_correction_gate_rules()
    return sorted(normalized, key=lambda rule: int(rule.get("priority", 9999)))


def _build_correction_gate_facts(
    context: dict[str, Any],
    *,
    active_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = _build_execution_contract(context)
    freeze_mode_state = context.get("freeze_mode_state", {})
    attestation = context.get("diagnosis_attestation", {})
    if not isinstance(attestation, dict):
        attestation = {}
    contract_expires_at = str(contract.get("expires_at", ""))
    contract_invalid = False
    contract_expired = False
    if contract_expires_at:
        try:
            contract_expires_dt = datetime.fromisoformat(
                contract_expires_at.replace("Z", "+00:00")
            )
            contract_expired = contract_expires_dt <= datetime.now(timezone.utc)
        except ValueError:
            contract_invalid = True

    attestation_invalid = False
    attestation_expired = False
    expires_at = str(attestation.get("expires_at", ""))
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            attestation_expired = expires_dt <= datetime.now(timezone.utc)
        except ValueError:
            attestation_invalid = True

    evidence = attestation.get("evidence_refs", [])
    confidence = attestation.get("confidence", 0.0)
    allowed_paths = contract.get("allowed_paths", [])
    planned_paths = context.get("planned_paths", [])
    min_conf = float(
        contract.get("min_diagnosis_confidence", MIN_DIAGNOSIS_CONFIDENCE_DEFAULT)
    )
    pattern = (
        f"{attestation.get('hypothesis', 'unknown')}|"
        f"{attestation.get('root_cause', 'unknown')}"
    )
    return {
        "freeze_mode_enabled": isinstance(freeze_mode_state, dict)
        and bool(freeze_mode_state.get("enabled")),
        "attestation_missing": not bool(attestation),
        "attestation_task_mismatch": bool(attestation)
        and str(attestation.get("task_id", "")) != str(contract.get("task_id", "")),
        "contract_invalid": contract_invalid,
        "contract_expired": contract_expired,
        "attestation_invalid": attestation_invalid,
        "attestation_expired": attestation_expired,
        "evidence_missing": not isinstance(evidence, list) or not evidence,
        "confidence_too_low": not isinstance(confidence, int | float)
        or float(confidence) < min_conf,
        "allowed_paths_missing": not isinstance(allowed_paths, list)
        or not allowed_paths,
        "scope_violation": isinstance(planned_paths, list)
        and bool(planned_paths)
        and any(path not in allowed_paths for path in planned_paths),
        "matching_active_rule": any(
            rule.get("pattern") == pattern for rule in active_rules
        ),
        "always": True,
    }


def _evaluate_correction_gate(  # noqa: C901
    context: dict[str, Any],
    *,
    active_rules: list[dict[str, Any]],
    gate_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rules = gate_rules or _default_correction_gate_rules()
    facts = _build_correction_gate_facts(context, active_rules=active_rules)
    for rule in sorted(rules, key=lambda item: int(item.get("priority", 9999))):
        condition = str(rule.get("condition", "")).strip()
        if not condition or not bool(facts.get(condition, False)):
            continue
        return {
            "decision": str(rule.get("decision", "deny")),
            "reason_code": str(rule.get("reason_code", "contract.missing_or_invalid")),
            "next_action": str(rule.get("next_action", "human-review")),
            "requires_human_review": bool(rule.get("requires_human_review", True)),
            "escalate_to_human": bool(rule.get("escalate_to_human", True)),
        }
    return _default_correction_gate_rules()[-1].copy()


# ---------------------------------------------------------------------------
# Skill handlers
# ---------------------------------------------------------------------------

_FooterFn = Callable[[str, str], str]


class AskHandler(Handler):
    """Prepare governed ask execution contracts and ledger entries.

    Example:
        Inject recent failures into `historical_context` before running the
        fallback commands, then record the ask outcome in the learning ledger.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        execution_contract = _build_execution_contract(context)
        recent_failures = (
            learning.list_failures(limit=3)
            if learning is not None and hasattr(learning, "list_failures")
            else []
        )
        active_rules = (
            learning.list_active_rules()
            if learning is not None and hasattr(learning, "list_active_rules")
            else []
        )
        if recent_failures or active_rules:
            execution_contract["historical_context"] = {
                "recent_failures": recent_failures,
                "active_rules": active_rules,
            }
        return PreRunOutcome(artifacts={"execution_contract": execution_contract})

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        contract = artifacts.get(
            "execution_contract", context.get("execution_contract", {})
        )
        if not isinstance(contract, dict):
            contract = {}
        if learning is None or not hasattr(learning, "append_failure"):
            return {}
        learning.append_failure(
            FailureLedgerEntry(
                symptom=str(contract.get("task_type", "unspecified")),
                root_cause=str(contract.get("goal", "unspecified")),
                fix="sdd-ask",
                validation="postcheck",
                regression=exit_code != 0,
                tags=["ask", "executed" if exit_code == 0 else "failed"],
                evidence_refs=[],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return {}


class DiagnoseHandler(Handler):
    """Prepare diagnosis artifacts and calibrate confidence from history.

    Example:
        Recurrent failures with the same symptom can increase diagnosis
        confidence before the diagnose fallback commands run.
    """

    def can_retry(
        self,
        context: dict[str, Any],
        *,
        exit_code: int,
        error: str,
        attempt_count: int,
    ) -> bool:
        del context, attempt_count
        return _is_retryable_error(exit_code=exit_code, error=error)

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
        similar_failures = []
        if (
            report.get("hypothesis") != "unknown"
            and learning is not None
            and hasattr(learning, "find_similar_failures")
        ):
            similar_failures = learning.find_similar_failures(
                symptom=str(report.get("hypothesis", "unknown")),
                root_cause=str(report.get("root_cause", "inconclusive")),
                limit=5,
            )
            confidence = report.get("confidence", 0.0)
            if isinstance(confidence, int | float) and similar_failures:
                recurrence_factor = min(len(similar_failures), 5) * 0.2
                report["confidence"] = min(
                    1.0, float(confidence) * (1.0 + recurrence_factor)
                )
                report["historical_matches"] = len(similar_failures)
        attestation = _build_diagnosis_attestation(
            {**context, "diagnosis_report": report}
        )
        return PreRunOutcome(
            artifacts={
                "diagnosis_report": report,
                "diagnosis_attestation": attestation,
            }
        )

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        report = artifacts.get("diagnosis_report", context.get("diagnosis_report", {}))
        if not isinstance(report, dict):
            return {}
        if learning is None or not hasattr(learning, "append_failure"):
            return {}
        learning.append_failure(
            FailureLedgerEntry(
                symptom=str(report.get("hypothesis", "unknown")),
                root_cause=str(report.get("root_cause", "inconclusive")),
                fix="sdd-diagnose",
                validation="postcheck",
                regression=exit_code != 0,
                tags=["diagnose", "executed" if exit_code == 0 else "failed"],
                evidence_refs=[
                    ref
                    for ref in report.get("evidence_refs", [])
                    if isinstance(ref, str)
                ],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return {}


class CorrectHandler(Handler):
    """Evaluate correction gates before any governed fix is attempted.

    Example:
        Deny a correction when `planned_paths` escape `allowed_paths`, or allow
        the correction and record downstream rule-candidate evidence.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        project_root_raw = context.get("_project_root", Path.cwd())
        project_root = Path(project_root_raw)
        gate_rules = _load_gate_rules(project_root=project_root, skill=skill)
        gate = _evaluate_correction_gate(
            context,
            active_rules=learning.list_active_rules(),
            gate_rules=gate_rules,
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


class ConvergeHandler(Handler):
    """Finalize corrective work and compute convergence/freeze artifacts.

    Example:
        Low alignment or too many residual violations enables
        `freeze_mode_state` and forces upstream pipeline escalation.
    """

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


class CompressContextHandler(Handler):
    """Summarize non-critical context and archive large candidates.

    Example:
        Long chat logs or large collections are summarized in memory and
        archived under `.analysis/archive/<timestamp>/`.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        del learning, skill, profile, footer_fn
        project_root = _resolve_project_root_from_context(context)
        compressed_context, compression_report = _compress_context(context)
        archive_report = _archive_context_candidates(
            project_root=project_root,
            context=context,
            archival_candidates=list(compression_report.get("archival_candidates", [])),
        )
        compression_report.update(archive_report)
        return PreRunOutcome(
            artifacts={
                "compressed_context": compressed_context,
                "compression_report": compression_report,
            }
        )


class ReviewArchitectureHandler(Handler):
    """Compare current architecture signals against the persisted baseline.

    Example:
        A lower governance score or new violations produces remediation
        proposals and updates `.analysis/archive/architecture-baseline.json`.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        del learning, skill, profile, footer_fn
        project_root = _resolve_project_root_from_context(context)
        baseline = _load_architecture_baseline(project_root)
        merged_context = dict(context)
        if "baseline_governance_score" not in merged_context:
            merged_context["baseline_governance_score"] = baseline.get(
                "governance_score", merged_context.get("governance_score", 0)
            )
        if "baseline_architecture_violations" not in merged_context:
            merged_context["baseline_architecture_violations"] = baseline.get(
                "architecture_violations", []
            )
        review = _build_architecture_review(merged_context)
        current_baseline = {
            "governance_score": review["governance_score"],
            "architecture_violations": list(
                merged_context.get("architecture_violations", [])
                if isinstance(merged_context.get("architecture_violations", []), list)
                else []
            ),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        baseline_path = _write_architecture_baseline(project_root, current_baseline)
        review["baseline_path"] = str(baseline_path.relative_to(project_root))
        review["baseline_updated"] = True
        return PreRunOutcome(artifacts=review)


class StabilizeHandler(Handler):
    """Aggregate lint/test failures into a handoff decision report.

    Example:
        Failing test commands yield `decision="block"` while lint-only issues
        yield `decision="warn"`.
    """

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        del learning, exit_code
        command_results = artifacts.get("command_results", [])
        if not isinstance(command_results, list):
            command_results = []
        return {
            "stabilization_report": _build_stabilization_report(
                context, command_results=command_results
            )
        }


class PipelineHandler(Handler):
    """Validate and compose the governed ask→diagnose→correct→converge flow.

    Example:
        The handler requests composition when `sdd-pipeline` is invoked and the
        executor runs the configured stages with shared `ContextCarrier` state.
    """

    _DEFAULT_STAGES = [
        "sdd-ask",
        "sdd-diagnose",
        "sdd-correct",
        "sdd-converge",
    ]

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        del learning, profile, footer_fn
        skill_config = getattr(skill, "config", {})
        pipeline_config = (
            skill_config.get("pipeline", {}) if isinstance(skill_config, dict) else {}
        )
        stages = context.get(
            "pipeline_stages",
            pipeline_config.get("stages", self._DEFAULT_STAGES),
        )
        if not isinstance(stages, list) or not stages:
            stages = list(self._DEFAULT_STAGES)
        normalized = [self._normalize_stage_name(stage) for stage in stages]
        invalid = [stage for stage in normalized if stage not in self._DEFAULT_STAGES]
        if invalid:
            early = SkillRunResult(
                state="error",
                profile="default",
                skill=skill.name,
                policy_result="invalid_pipeline",
                reason=f"invalid_pipeline_stages:{','.join(invalid)}",
                exit_code=1,
                governance_footer="",
                artifacts={},
            )
            return PreRunOutcome(early_result=early)
        pipeline_state = {
            "stages": normalized,
            "completed_stages": [],
            "stage_results": {},
            "escalation_triggered": False,
            "escalation_reason": "",
        }
        decision_gates = {
            "diagnose_to_correct_min_confidence": float(
                context.get(
                    "pipeline_min_diagnosis_confidence",
                    pipeline_config.get("decision_gates", {}).get(
                        "diagnose_to_correct_min_confidence", 0.70
                    ),
                )
            )
        }
        return PreRunOutcome(
            artifacts={"pipeline_state": pipeline_state},
            compose_config={"stages": normalized, "decision_gates": decision_gates},
        )

    @classmethod
    def _normalize_stage_name(cls, value: Any) -> str:
        stage = str(value)
        return stage if stage.startswith("sdd-") else f"sdd-{stage}"


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

    def _policy_blocked_result(
        self,
        *,
        name: str,
        profile: str,
        skill: SkillDefinition,
        policy_check: Any,
        footer_fn: _FooterFn,
    ) -> SkillRunResult:
        drift = (
            "handshake_unauthorized"
            if "handshake" in policy_check.reason.lower()
            else "fallback_cli"
        )
        policy_result = (
            "unauthorized" if drift == "handshake_unauthorized" else "blocked"
        )
        return SkillRunResult(
            state="error",
            profile=profile,
            skill=name,
            policy_result=policy_result,
            reason=policy_check.reason,
            exit_code=1,
            governance_footer=footer_fn(drift, "blocked"),
            fallback=list(skill.cli_fallback) if drift == "fallback_cli" else [],
            artifacts={},
        )

    def _try_pre_run(
        self,
        *,
        handler: Any,
        handler_context: dict[str, Any],
        learning: Any,
        skill: SkillDefinition,
        profile: str,
        enforcement_mode: str,
        execute: bool,
        root: Path,
        artifacts: dict[str, Any],
        footer_fn: _FooterFn,
    ) -> SkillRunResult | None:
        """Run the handler's pre_run hook, if any, and resolve any early result."""
        if handler is None or not hasattr(handler, "pre_run"):
            return None
        outcome = handler.pre_run(
            handler_context,
            learning=learning,
            skill=skill,
            profile=profile,
            footer_fn=footer_fn,
        )
        artifacts.update(outcome.artifacts)
        if outcome.early_result is not None:
            return cast(SkillRunResult, outcome.early_result)
        if outcome.compose_config is not None:
            return self._compose_skill(
                parent_skill=skill,
                context=handler_context,
                seed_artifacts=artifacts,
                compose_config=outcome.compose_config,
                execute=execute,
                profile=profile,
                enforcement_mode=enforcement_mode,
                project_root=root,
            )
        return None

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
            result = self._policy_blocked_result(
                name=name,
                profile=profile,
                skill=skill,
                policy_check=policy_check,
                footer_fn=_maybe_footer,
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
        handler_context = dict(context)
        handler_context.setdefault("_project_root", str(root))

        pre_run_result = self._try_pre_run(
            handler=handler,
            handler_context=handler_context,
            learning=learning,
            skill=skill,
            profile=profile,
            enforcement_mode=enforcement_mode,
            execute=execute,
            root=root,
            artifacts=artifacts,
            footer_fn=_maybe_footer,
        )
        if pre_run_result is not None:
            self._emit_skill_telemetry(pre_run_result)
            return pre_run_result

        exit_code, execution_errors, command_results = (
            self._execute_commands(
                skill, root, handler=handler, learning=learning, context=handler_context
            )
            if execute
            else (0, [], [])
        )
        policy_result, reason, drift = _classify_execution_outcome(
            execute=execute, exit_code=exit_code, execution_errors=execution_errors
        )
        artifacts["command_results"] = command_results
        if (
            exit_code == 124
            and handler is not None
            and hasattr(handler, "timeout_hook")
        ):
            artifacts.update(
                handler.timeout_hook(
                    handler_context,
                    learning=learning,
                    skill=skill,
                    elapsed_seconds=int(
                        skill.budget_policy.get("timeout_seconds", 120)
                    ),
                )
            )

        if handler is not None and hasattr(handler, "post_run"):
            artifacts.update(
                handler.post_run(
                    handler_context,
                    learning=learning,
                    exit_code=exit_code,
                    artifacts=artifacts,
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

    def _compose_skill(
        self,
        *,
        parent_skill: SkillDefinition,
        context: dict[str, Any],
        seed_artifacts: dict[str, Any],
        compose_config: dict[str, Any],
        execute: bool,
        profile: str,
        enforcement_mode: str,
        project_root: Path,
    ) -> SkillRunResult:
        carrier = ContextCarrier(context)
        if seed_artifacts:
            carrier.push_layer(
                seed_artifacts, source="handler", skill_name=parent_skill.name
            )
        decision_gates = compose_config.get("decision_gates", {})
        stages, completed_stages, stage_results = _prepare_pipeline_stages(
            carrier, compose_config
        )
        aggregated_command_results: list[dict[str, Any]] = []

        for stage_name in stages:
            stage_result = self.run_skill(
                stage_name,
                execute=execute,
                profile=profile,
                enforcement_mode=enforcement_mode,
                project_root=project_root,
                context=carrier.snapshot(),
            )
            aggregated_command_results.extend(stage_result.command_results)
            stage_results[stage_name] = {
                "state": stage_result.state,
                "policy_result": stage_result.policy_result,
                "reason": stage_result.reason,
                "exit_code": stage_result.exit_code,
            }
            completed_stages.append(stage_name)
            carrier.push_layer(
                {
                    "pipeline_state": {
                        "stages": stages,
                        "completed_stages": completed_stages,
                        "stage_results": stage_results,
                        "escalation_triggered": False,
                        "escalation_reason": "",
                    }
                },
                source="pipeline",
                skill_name=parent_skill.name,
            )
            if stage_result.artifacts:
                carrier.push_layer(
                    stage_result.artifacts, source="skill", skill_name=stage_name
                )
            if stage_name == "sdd-diagnose":
                gate_result = self._check_diagnose_gate(
                    carrier=carrier,
                    decision_gates=decision_gates,
                    stages=stages,
                    completed_stages=completed_stages,
                    stage_results=stage_results,
                    parent_skill=parent_skill,
                    profile=profile,
                    aggregated_command_results=aggregated_command_results,
                )
                if gate_result is not None:
                    return gate_result
            freeze_result = self._check_freeze_gate(
                carrier=carrier,
                stage_name=stage_name,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                aggregated_command_results=aggregated_command_results,
            )
            if freeze_result is not None:
                return freeze_result
            timeout_result = self._check_timeout_gate(
                carrier=carrier,
                stage_result=stage_result,
                stage_name=stage_name,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                aggregated_command_results=aggregated_command_results,
            )
            if timeout_result is not None:
                return timeout_result
            failure_result = self._check_stage_failure(
                carrier=carrier,
                stage_result=stage_result,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                aggregated_command_results=aggregated_command_results,
            )
            if failure_result is not None:
                return failure_result

        return SkillRunResult(
            state="ok",
            profile=profile,
            skill=parent_skill.name,
            policy_result="executed" if execute else "planned",
            reason="pipeline execution completed"
            if execute
            else "pipeline dry-run planning completed",
            exit_code=0,
            governance_footer=format_governance_footer(
                drift="fallback_cli" if execute else "none",
                governance="ok",
                profile=profile,
            ),
            fallback=[],
            command_results=aggregated_command_results,
            artifacts=carrier.snapshot(),
        )

    def _check_diagnose_gate(
        self,
        *,
        carrier: ContextCarrier,
        decision_gates: dict[str, Any],
        stages: list[str],
        completed_stages: list[str],
        stage_results: dict[str, Any],
        parent_skill: SkillDefinition,
        profile: str,
        aggregated_command_results: list[dict[str, Any]],
    ) -> SkillRunResult | None:
        diagnosis_report = carrier.get("diagnosis_report", {})
        if not isinstance(diagnosis_report, dict):
            return None
        confidence = diagnosis_report.get("confidence", 0.0)
        min_confidence = float(
            decision_gates.get("diagnose_to_correct_min_confidence", 0.70)
        )
        if not (
            isinstance(confidence, int | float) and float(confidence) < min_confidence
        ):
            return None
        gate_reason = REASON_CODE_DIAGNOSIS_INCONCLUSIVE
        logger.warning(
            "Pipeline gate escalation after %s: confidence %.2f < %.2f",
            "sdd-diagnose",
            float(confidence),
            min_confidence,
        )
        carrier.push_layer(
            {
                "pipeline_gate_decision": {
                    "from_stage": "sdd-diagnose",
                    "to_stage": "sdd-correct",
                    "decision": "skip_and_escalate",
                    "reason_code": gate_reason,
                    "confidence": float(confidence),
                    "min_confidence": min_confidence,
                },
                "pipeline_state": {
                    "stages": stages,
                    "completed_stages": completed_stages,
                    "stage_results": stage_results,
                    "escalation_triggered": True,
                    "escalation_reason": gate_reason,
                },
            },
            source="pipeline",
            skill_name=parent_skill.name,
        )
        return SkillRunResult(
            state="error",
            profile=profile,
            skill=parent_skill.name,
            policy_result="escalated",
            reason=gate_reason,
            exit_code=1,
            governance_footer=format_governance_footer(
                drift="fallback_cli",
                governance="fail",
                profile=profile,
            ),
            fallback=[],
            command_results=aggregated_command_results,
            artifacts=carrier.snapshot(),
        )

    def _check_freeze_gate(
        self,
        *,
        carrier: ContextCarrier,
        stage_name: str,
        stages: list[str],
        completed_stages: list[str],
        stage_results: dict[str, Any],
        parent_skill: SkillDefinition,
        profile: str,
        aggregated_command_results: list[dict[str, Any]],
    ) -> SkillRunResult | None:
        freeze_mode_state = carrier.get("freeze_mode_state", {})
        if not (
            isinstance(freeze_mode_state, dict)
            and bool(freeze_mode_state.get("enabled"))
            and stage_name == "sdd-converge"
        ):
            return None
        escalation_reason = str(
            freeze_mode_state.get("trigger_reason", REASON_CODE_CONVERGENCE_FREEZE)
        )
        logger.critical(
            "Pipeline freeze escalation triggered by %s: %s",
            stage_name,
            escalation_reason,
        )
        carrier.push_layer(
            {
                "pipeline_state": {
                    "stages": stages,
                    "completed_stages": completed_stages,
                    "stage_results": stage_results,
                    "escalation_triggered": True,
                    "escalation_reason": escalation_reason,
                },
                "pipeline_escalation": {
                    "reason": escalation_reason,
                    "trigger_stage": stage_name,
                },
            },
            source="pipeline",
            skill_name=parent_skill.name,
        )
        return SkillRunResult(
            state="error",
            profile=profile,
            skill=parent_skill.name,
            policy_result="escalated",
            reason=escalation_reason,
            exit_code=2,
            governance_footer=format_governance_footer(
                drift="fallback_cli", governance="fail", profile=profile
            ),
            fallback=[],
            command_results=aggregated_command_results,
            artifacts=carrier.snapshot(),
        )

    def _check_timeout_gate(
        self,
        *,
        carrier: ContextCarrier,
        stage_result: SkillRunResult,
        stage_name: str,
        stages: list[str],
        completed_stages: list[str],
        stage_results: dict[str, Any],
        parent_skill: SkillDefinition,
        profile: str,
        aggregated_command_results: list[dict[str, Any]],
    ) -> SkillRunResult | None:
        if stage_result.exit_code != 124:
            return None
        timeout_reason = f"stage_timeout:{stage_name}"
        logger.warning(
            "Pipeline stage timeout at %s; escalating with reason=%s",
            stage_name,
            timeout_reason,
        )
        carrier.push_layer(
            {
                "pipeline_timeout": {
                    "reason": timeout_reason,
                    "trigger_stage": stage_name,
                },
                "pipeline_state": {
                    "stages": stages,
                    "completed_stages": completed_stages,
                    "stage_results": stage_results,
                    "escalation_triggered": True,
                    "escalation_reason": timeout_reason,
                },
            },
            source="pipeline",
            skill_name=parent_skill.name,
        )
        return SkillRunResult(
            state="error",
            profile=profile,
            skill=parent_skill.name,
            policy_result="escalated",
            reason=timeout_reason,
            exit_code=124,
            governance_footer=format_governance_footer(
                drift="fallback_cli", governance="fail", profile=profile
            ),
            fallback=[],
            command_results=aggregated_command_results,
            artifacts=carrier.snapshot(),
        )

    def _check_stage_failure(
        self,
        *,
        carrier: ContextCarrier,
        stage_result: SkillRunResult,
        stages: list[str],
        completed_stages: list[str],
        stage_results: dict[str, Any],
        parent_skill: SkillDefinition,
        profile: str,
        aggregated_command_results: list[dict[str, Any]],
    ) -> SkillRunResult | None:
        if stage_result.exit_code == 0:
            return None
        carrier.push_layer(
            {
                "pipeline_state": {
                    "stages": stages,
                    "completed_stages": completed_stages,
                    "stage_results": stage_results,
                    "escalation_triggered": stage_result.policy_result
                    in {"escalated", "denied", "blocked"},
                    "escalation_reason": stage_result.reason,
                }
            },
            source="pipeline",
            skill_name=parent_skill.name,
        )
        return SkillRunResult(
            state="error",
            profile=profile,
            skill=parent_skill.name,
            policy_result=stage_result.policy_result,
            reason=stage_result.reason,
            exit_code=stage_result.exit_code,
            governance_footer=format_governance_footer(
                drift="fallback_cli", governance="fail", profile=profile
            ),
            fallback=[],
            command_results=aggregated_command_results,
            artifacts=carrier.snapshot(),
        )

    def _execute_commands(
        self,
        skill: SkillDefinition,
        root: Path,
        *,
        handler: Any = None,
        learning: Any = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[int, list[str], list[dict[str, Any]]]:
        if not skill.cli_fallback:
            return 0, [], []

        from sdd_core.utils.process import SafeProcessRunner

        timeout_seconds = int(skill.budget_policy.get("timeout_seconds", 120))
        max_retries = int(skill.budget_policy.get("max_retries", 0))
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
            attempt = 0
            while True:
                cmd_result = self._run_command_attempt(
                    safe_runner, cmd, root, timeout_seconds, attempt
                )
                command_results.append(cmd_result)
                if cmd_result["status"] == "ok":
                    break

                if self._handle_command_retry(
                    handler=handler,
                    context=context,
                    learning=learning,
                    skill=skill,
                    cmd=cmd,
                    cmd_result=cmd_result,
                    attempt=attempt,
                    max_retries=max_retries,
                ):
                    attempt += 1
                    continue

                exit_code = int(cmd_result["exit_code"])
                if exit_code == 124:
                    execution_errors.append(f"Command '{cmd}' timed out")
                else:
                    execution_errors.append(
                        f"Command '{cmd}' failed: {cmd_result['error']}"
                    )
                break
            if exit_code != 0:
                break

        return exit_code, execution_errors, command_results

    def _run_command_attempt(
        self,
        safe_runner: Any,
        cmd: str,
        root: Path,
        timeout_seconds: int,
        attempt: int,
    ) -> dict[str, Any]:
        import shlex

        from sdd_core.utils.process import ProcessTimeoutError

        cmd_result: dict[str, Any] = {
            "command": cmd,
            "status": "ok",
            "exit_code": 0,
            "error": "",
            "attempt": attempt,
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
                cmd_result["exit_code"] = safe_proc.returncode or 1
                cmd_result["error"] = (
                    safe_proc.stderr or f"command returned {safe_proc.returncode}"
                )
        except ProcessTimeoutError:
            cmd_result["status"] = "error"
            cmd_result["exit_code"] = 124
            cmd_result["error"] = "timeout"
        except Exception as e:
            cmd_result["status"] = "error"
            cmd_result["exit_code"] = 1
            cmd_result["error"] = str(e)
        return cmd_result

    def _handle_command_retry(
        self,
        *,
        handler: Any,
        context: dict[str, Any] | None,
        learning: Any,
        skill: SkillDefinition,
        cmd: str,
        cmd_result: dict[str, Any],
        attempt: int,
        max_retries: int,
    ) -> bool:
        """Apply retry hooks and return True if the command should be retried."""
        can_retry = (
            handler.can_retry(
                context or {},
                exit_code=int(cmd_result["exit_code"]),
                error=str(cmd_result["error"]),
                attempt_count=attempt,
            )
            if handler is not None and hasattr(handler, "can_retry")
            else _is_retryable_error(
                exit_code=int(cmd_result["exit_code"]),
                error=str(cmd_result["error"]),
            )
        )
        if not (attempt < max_retries and can_retry):
            return False

        wait_seconds = min(0.01 * (2**attempt), 0.05)
        if handler is not None and hasattr(handler, "retry_hook"):
            retry_artifact = handler.retry_hook(
                context or {},
                learning=learning,
                skill=skill,
                command=cmd,
                exit_code=int(cmd_result["exit_code"]),
                error=str(cmd_result["error"]),
                attempt_count=attempt + 1,
            )
            if isinstance(retry_artifact, dict) and retry_artifact:
                cmd_result["retry_event"] = retry_artifact.get(
                    "retry_event", retry_artifact
                )
        logger.info(
            "Retrying skill command '%s' in %.2fs (attempt %s/%s)",
            cmd,
            wait_seconds,
            attempt + 1,
            max_retries,
        )
        time.sleep(wait_seconds)
        return True

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
