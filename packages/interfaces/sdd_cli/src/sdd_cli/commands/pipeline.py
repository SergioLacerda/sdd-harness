"""Strict end-to-end pipeline orchestration for governed correction flow."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import click
import typer
from sdd_runtime import SkillEngine

from sdd_cli.services.ask_payload import build_ask_advisory_block
from sdd_cli.services.ask_snapshot import build_governed_ask_snapshot
from sdd_cli.shared.contracts import (
    build_error_result,
    build_ok_result,
)
from sdd_cli.utils.output import emit_json, is_json_mode

_FREEZE_STATE_PATH = Path(".sdd/runtime/freeze-mode-state.json")
app = typer.Typer(help="Run strict ask->diagnose->correct->converge orchestration.")


def _load_freeze_mode_state(workspace_root: Path, *, task_id: str) -> dict[str, Any]:
    path = workspace_root / _FREEZE_STATE_PATH
    if not path.exists():
        return {"enabled": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False}
    if not isinstance(payload, dict):
        return {"enabled": False}
    loaded_task_id = str(payload.get("task_id", ""))
    if loaded_task_id and loaded_task_id != task_id:
        return {"enabled": False, "task_id": task_id}
    payload.setdefault("task_id", task_id)
    return payload


def _write_freeze_mode_state(
    workspace_root: Path, state: dict[str, Any], *, task_id: str, trace_id: str
) -> None:
    path = workspace_root / _FREEZE_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    payload["task_id"] = task_id
    payload["trace_id"] = trace_id
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    tmp_path.replace(path)


def pipeline_run_cmd(
    *,
    query: str,
    skill: str | None,
    budget: int | None,
    execute: bool,
) -> None:
    """Run ask->diagnose->correct->converge strict orchestration."""
    try:
        ask_snapshot = build_governed_ask_snapshot(
            query=query,
            skill=skill,
            organize_used=False,
            require_handshake=True,
        )
    except PermissionError as exc:
        typer.echo(f"BLOCK [pipeline]: {exc}", err=True)
        raise click.exceptions.Exit(3) from None
    workspace_root = ask_snapshot["workspace_root"]
    learning_recommendation = ask_snapshot["learning_recommendation"]
    learning_context = ask_snapshot["learning_context"]
    if budget is not None:
        if budget <= 0:
            typer.echo("ERROR [pipeline]: --budget must be > 0", err=True)
            raise click.exceptions.Exit(2)
        learning_context["budget_hint"] = budget
    ask_decision_envelope = ask_snapshot["ask_decision_envelope"]
    task_id = str(ask_decision_envelope.get("task_id", ""))
    execution_contract = {
        **ask_decision_envelope,
        "escalation_policy": "human_on_inconclusive_diagnosis",
    }
    freeze_mode_state = _load_freeze_mode_state(workspace_root, task_id=task_id)

    engine = SkillEngine(project_root=workspace_root)
    trace_id = str(uuid4())
    if os.environ.get("SDD_ENFORCE_PIPELINE_CORRECT", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        learning_context["pipeline_enforcement"] = "required"
    diagnose_result = engine.run_skill(
        "sdd-diagnose",
        execute=execute,
        profile="default",
        context={"execution_contract": execution_contract, "trace_id": trace_id},
    )
    diagnosis_report = diagnose_result.artifacts.get("diagnosis_report", {})
    diagnosis_attestation = diagnose_result.artifacts.get("diagnosis_attestation", {})

    correct_result = engine.run_skill(
        "sdd-correct",
        execute=execute,
        profile="default",
        context={
            "execution_contract": execution_contract,
            "diagnosis_report": diagnosis_report,
            "diagnosis_attestation": diagnosis_attestation,
            "freeze_mode_state": freeze_mode_state,
            "trace_id": trace_id,
        },
    )
    gate_decision = correct_result.artifacts.get(
        "gate_decision",
        {
            "decision": "deny",
            "reason_code": "contract.missing_or_invalid",
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
        },
    )

    converge_result = engine.run_skill(
        "sdd-converge",
        execute=False,
        profile="default",
        context={
            "trace_id": trace_id,
            "convergence_delta_report": {
                "alignment_score": 0.95
                if gate_decision.get("decision") == "allow"
                else 0.50,
                "residual_violations": []
                if gate_decision.get("decision") == "allow"
                else [str(gate_decision.get("reason_code", "unknown"))],
                "next_targets": [str(gate_decision.get("next_action", "human-review"))],
            },
        },
    )
    new_freeze_state = converge_result.artifacts.get("freeze_mode_state", {})
    if isinstance(new_freeze_state, dict):
        _write_freeze_mode_state(
            workspace_root, new_freeze_state, task_id=task_id, trace_id=trace_id
        )

    data = {
        "state": "ok" if gate_decision.get("decision") == "allow" else "error",
        "policy_result": "pipeline_completed"
        if gate_decision.get("decision") == "allow"
        else "pipeline_blocked",
        "reason": str(gate_decision.get("reason_code", "unknown")),
        "exit_code": 0 if gate_decision.get("decision") == "allow" else 1,
        "trace_id": trace_id,
        "pipeline": {
            "ask": build_ask_advisory_block(
                ask_decision_envelope=ask_decision_envelope,
                learning_context=learning_context,
                learning_recommendation=learning_recommendation,
                include_empty_recommendations=True,
            ),
            "diagnose": {
                "diagnosis_report": diagnosis_report,
                "diagnosis_attestation": diagnosis_attestation,
            },
            "correct": {
                "gate_decision": gate_decision,
                "command_results": correct_result.command_results,
                "artifacts": correct_result.artifacts,
            },
            "converge": {
                "convergence_delta_report": converge_result.artifacts.get(
                    "convergence_delta_report", {}
                ),
                "freeze_mode_state": converge_result.artifacts.get(
                    "freeze_mode_state", {}
                ),
            },
        },
        "final_gate_decision": gate_decision,
    }
    if data["exit_code"] == 0:
        payload = build_ok_result("pipeline", data)
    else:
        payload = build_error_result(
            "pipeline",
            data,
            code=str(gate_decision.get("reason_code", "unknown")),
            message=str(gate_decision.get("reason_code", "unknown")),
        )

    if is_json_mode(click.get_current_context(silent=True)):
        emit_json(payload, err=data["exit_code"] != 0)
    else:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    if data["exit_code"] != 0:
        raise click.exceptions.Exit(data["exit_code"])


@app.callback(invoke_without_command=True)
def pipeline(
    query: str = typer.Argument(
        ..., help="Governed task query used to build the execution envelope."
    ),
    skill: str | None = typer.Option(
        None, "--skill", help="Optional skill hint for envelope task_type."
    ),
    budget: int | None = typer.Option(
        None, "--budget", help="Reserved budget hint for pipeline orchestration."
    ),
    execute: bool = typer.Option(
        False, "--execute", help="Allow runtime command execution in skill stages."
    ),
) -> None:
    """Run strict end-to-end convergence pipeline."""
    pipeline_run_cmd(query=query, skill=skill, budget=budget, execute=execute)
