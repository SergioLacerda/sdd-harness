"""Supervised-learning commands for the skill layer (`sdd skills learning-*`)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import click
import typer
from sdd_runtime import SupervisedLearningStore

from sdd_cli.services.skills_output import emit_skills_json as _emit_skills_json
from sdd_cli.utils.output import is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(help="Supervised learning rule commands")


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


@app.command("learning-candidates")
def learning_candidates() -> None:
    """Learning Candidates."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    created = [item.__dict__ for item in store.generate_candidates_from_ledger()]
    candidates_path = ws_root / ".sdd" / "runtime" / "rule-candidates.json"
    existing: list[dict[str, Any]] = []
    if candidates_path.exists():
        payload = json.loads(candidates_path.read_text(encoding="utf-8"))
        existing = payload.get("candidates", [])
    if _ctx_json():
        _emit_skills_json(
            command="skills learning-candidates",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "learning_candidates_listed",
                "reason": "rule candidates loaded",
                "exit_code": 0,
                "created_count": len(created),
                "candidates": existing,
            },
            ok=True,
        )
        return
    typer.echo(f"rule candidates: {len(existing)} (newly created: {len(created)})")
    for candidate in existing:
        typer.echo(
            f"- {candidate.get('candidate_id')} pattern={candidate.get('pattern')}"
        )


@app.command("learning-approve")
def learning_approve(
    candidate_id: str,
    reviewer: str = typer.Option("human", "--reviewer"),
    rationale: str = typer.Option(..., "--rationale"),
    ttl_days: int = typer.Option(30, "--ttl-days"),
) -> None:
    """Approve a learning rule candidate with human rationale."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    decision = store.decide_rule(
        candidate_id=candidate_id,
        approved=True,
        reviewer=reviewer,
        rationale=rationale,
        ttl_days=ttl_days,
    )
    if _ctx_json():
        ok = decision.get("status") == "ok"
        _emit_skills_json(
            command="skills learning-approve",
            data={
                "state": "ok" if ok else "error",
                "profile": "default",
                "skill": None,
                "policy_result": "rule_approved" if ok else "missing_candidate",
                "reason": "rule decision recorded",
                "exit_code": 0 if ok else 1,
                "decision": decision,
            },
            ok=ok,
            error_code="missing_candidate" if not ok else None,
            error_message="candidate not found" if not ok else None,
            err=not ok,
        )
    else:
        typer.echo(json.dumps(decision, indent=2, ensure_ascii=False))
    if decision.get("status") != "ok":
        raise typer.Exit(1)


@app.command("learning-reject")
def learning_reject(
    candidate_id: str,
    reviewer: str = typer.Option("human", "--reviewer"),
    rationale: str = typer.Option(..., "--rationale"),
) -> None:
    """Reject a learning rule candidate with human rationale."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    decision = store.decide_rule(
        candidate_id=candidate_id,
        approved=False,
        reviewer=reviewer,
        rationale=rationale,
        ttl_days=30,
    )
    if _ctx_json():
        ok = decision.get("status") == "ok"
        _emit_skills_json(
            command="skills learning-reject",
            data={
                "state": "ok" if ok else "error",
                "profile": "default",
                "skill": None,
                "policy_result": "rule_rejected" if ok else "missing_candidate",
                "reason": "rule decision recorded",
                "exit_code": 0 if ok else 1,
                "decision": decision,
            },
            ok=ok,
            error_code="missing_candidate" if not ok else None,
            error_message="candidate not found" if not ok else None,
            err=not ok,
        )
    else:
        typer.echo(json.dumps(decision, indent=2, ensure_ascii=False))
    if decision.get("status") != "ok":
        raise typer.Exit(1)


@app.command("learning-impact")
def learning_impact(
    rule_id: str,
    rework_delta: float = typer.Option(..., "--rework-delta"),
    false_block_rate: float = typer.Option(..., "--false-block-rate"),
    escalation_delta: float = typer.Option(..., "--escalation-delta"),
    rollback_flag: bool = typer.Option(False, "--rollback-flag"),
) -> None:
    """Record impact telemetry for an active learning rule."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    store.record_rule_impact(
        rule_id=rule_id,
        rework_delta=rework_delta,
        false_block_rate=false_block_rate,
        escalation_delta=escalation_delta,
        rollback_flag=rollback_flag,
    )
    payload = {
        "rule_id": rule_id,
        "rework_delta": rework_delta,
        "false_block_rate": false_block_rate,
        "escalation_delta": escalation_delta,
        "rollback_flag": rollback_flag,
    }
    if _ctx_json():
        _emit_skills_json(
            command="skills learning-impact",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "rule_impact_recorded",
                "reason": "rule impact recorded",
                "exit_code": 0,
                "impact": payload,
            },
            ok=True,
        )
        return
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command("learning-rules")
def learning_rules() -> None:
    """Learning Rules."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    rules = store.list_active_rules()
    if _ctx_json():
        _emit_skills_json(
            command="skills learning-rules",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "active_rules_listed",
                "reason": "active supervised rules loaded",
                "exit_code": 0,
                "rules": rules,
            },
            ok=True,
        )
        return
    typer.echo(f"active rules: {len(rules)}")
    for rule in rules:
        typer.echo(f"- {rule.get('rule_id')} pattern={rule.get('pattern')}")


@app.command("learning-status")
def learning_status(
    window_days: int = typer.Option(7, "--window-days", min=1),
) -> None:
    """Show supervised learning status and recent impact metrics."""
    ws_root = resolve_workspace_root()
    runtime_dir = ws_root / ".sdd" / "runtime"
    candidates_path = runtime_dir / "rule-candidates.json"
    registry_path = runtime_dir / "rule-registry.json"
    impact_path = runtime_dir / "rule-impact.jsonl"

    candidates = 0
    if candidates_path.exists():
        payload = json.loads(candidates_path.read_text(encoding="utf-8"))
        candidates = len(payload.get("candidates", []))

    rules_payload: dict[str, Any] = {"rules": []}
    if registry_path.exists():
        rules_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    rules = rules_payload.get("rules", [])
    active_rules = sum(1 for r in rules if r.get("status") == "active")
    rolled_back_rules = sum(1 for r in rules if r.get("status") == "rolled_back")
    expired_rules = sum(1 for r in rules if r.get("status") == "expired")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    recent_impacts: list[dict[str, Any]] = []
    if impact_path.exists():
        for line in impact_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            ts = row.get("timestamp")
            try:
                dt = datetime.fromisoformat(str(ts))
            except ValueError:
                continue
            if dt >= cutoff:
                recent_impacts.append(row)
    impact_count = len(recent_impacts)
    avg_false_block_rate = (
        sum(float(i.get("false_block_rate", 0.0)) for i in recent_impacts)
        / impact_count
        if impact_count
        else 0.0
    )
    avg_rework_delta = (
        sum(float(i.get("rework_delta", 0.0)) for i in recent_impacts) / impact_count
        if impact_count
        else 0.0
    )
    recent_rollbacks = sum(1 for i in recent_impacts if i.get("rollback_flag") is True)

    status = {
        "window_days": window_days,
        "candidates_total": candidates,
        "rules_total": len(rules),
        "rules_active": active_rules,
        "rules_rolled_back": rolled_back_rules,
        "rules_expired": expired_rules,
        "impacts_recent": impact_count,
        "avg_false_block_rate_recent": round(avg_false_block_rate, 6),
        "avg_rework_delta_recent": round(avg_rework_delta, 6),
        "kpi_rework_reduction_pct_recent": round(
            max(0.0, -avg_rework_delta * 100.0), 4
        ),
        "rollbacks_recent": recent_rollbacks,
    }
    if _ctx_json():
        _emit_skills_json(
            command="skills learning-status",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "learning_status_loaded",
                "reason": "supervised learning status summary",
                "exit_code": 0,
                "status": status,
            },
            ok=True,
        )
        return
    typer.echo(json.dumps(status, indent=2, ensure_ascii=False))
