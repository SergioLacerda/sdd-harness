"""SkillExecutor — execution engine for governed skill runs."""

from __future__ import annotations

import json
import logging
import time
import warnings
from pathlib import Path
from typing import Any, cast

from sdd_skills import SkillRunResult, format_governance_footer

from .._skill_contracts import SkillDefinition, _is_deprecation_due
from .._skill_registry import SkillRegistry
from ..learning import SupervisedLearningStore
from ..telemetry import RuntimeEvent, TelemetrySink
from ._base import ContextCarrier
from ._constants import (
    REASON_CODE_CONVERGENCE_FREEZE,
    REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
    _FooterFn,
)
from ._handlers import (
    _classify_execution_outcome,
    _get_skill_handler,
    _prepare_pipeline_stages,
)
from ._stabilization import _is_retryable_error

logger = logging.getLogger(__name__)


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

        from ..policy import PolicyEngine

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
