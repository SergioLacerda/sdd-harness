"""Skill layer commands for capability-oriented operations."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import typer
from sdd_runtime import SkillEngine, SupervisedLearningStore

from sdd_cli.generators._commands import generate_commands_registry
from sdd_cli.generators._indices import (
    generate_cli_commands_index,
    generate_skill_index,
)
from sdd_cli.generators._skills import generate_skills_registry
from sdd_cli.generators.agent_seeds import (
    generate_agent_instruction_files,
    generate_agent_prompt_commands,
    generate_agent_seeds,
)
from sdd_cli.services.registry_reconciliation import reconcile_registries
from sdd_cli.services.skills_registry import (
    export_skills_payload,
    get_skill,
    list_skills,
)
from sdd_cli.shared.contracts import (
    build_error_result,
    build_ok_result,
)
from sdd_cli.utils.loader import load_governance_config, validate_governance_path
from sdd_cli.utils.output import emit_json, is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(help="Capability-oriented skill commands")


def _emit_skills_json(
    *,
    command: str,
    data: dict[str, Any],
    ok: bool,
    error_code: str | None = None,
    error_message: str | None = None,
    err: bool = False,
) -> None:
    """Emit canonical JSON envelope for skills commands."""
    if ok:
        payload = build_ok_result(command, data)
    else:
        payload = build_error_result(
            command,
            data,
            code=error_code or "skills_error",
            message=error_message or "skills command failed",
        )
    emit_json(payload, err=err)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    full_bootstrap: bool = typer.Option(
        False,
        "--full-bootstrap",
        help=(
            "Generate all available skills/commands/seeds artifacts from canonical "
            ".sdd governance data."
        ),
    ),
    regenerate_seeds: bool = typer.Option(
        False,
        "--regenerate-seeds",
        help=(
            "Regenerate and reconcile root seed artifacts from canonical "
            ".sdd command/skill registries (deletes stale managed seed files)."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview seed reconciliation changes without deleting managed artifacts.",
    ),
) -> None:
    """Skill operations."""
    if dry_run and not regenerate_seeds:
        typer.echo("ERROR: --dry-run requires --regenerate-seeds", err=True)
        raise typer.Exit(2)

    if not full_bootstrap and not regenerate_seeds:
        return
    if ctx.invoked_subcommand is not None:
        return
    _run_full_bootstrap(regenerate_seeds=regenerate_seeds, dry_run=dry_run)


def _ctx_json() -> bool:
    import click

    return is_json_mode(click.get_current_context(silent=True))


def _read_registry_ids(registry_path: Path, key: str, id_key: str) -> list[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = data.get(key, [])
    if not isinstance(rows, list):
        raise ValueError(f"invalid registry format for {registry_path}")
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(id_key, "")).strip()
        if value:
            ids.append(value)
    return ids


def _prune_managed_files(
    dir_path: Path,
    expected_names: set[str],
    pattern: str,
    stats: dict[str, int],
    *,
    dry_run: bool,
) -> None:
    if not dir_path.exists():
        return
    for path in dir_path.glob(pattern):
        if path.name not in expected_names:
            stats["would_delete"] += 1
            if not dry_run:
                path.unlink(missing_ok=True)
                stats["deleted"] += 1


def _prune_antigravity_skills(
    root: Path, skill_names: set[str], stats: dict[str, int], *, dry_run: bool
) -> None:
    antigravity_skills_dir = root / ".gemini" / "antigravity" / "skills"
    if not antigravity_skills_dir.exists():
        return
    protected = {"sdd-governance", "sdd-harness"}
    for path in antigravity_skills_dir.iterdir():
        if not path.is_dir():
            continue
        if path.name in skill_names or path.name in protected:
            continue
        stats["would_delete"] += 1
        if not dry_run:
            shutil.rmtree(path)
            stats["deleted"] += 1


def _reconcile_root_seed_artifacts(
    root: Path, *, dry_run: bool = False
) -> dict[str, int]:
    commands_registry = root / ".sdd" / "commands" / "registry.json"
    skills_registry = root / ".sdd" / "skills" / "registry.json"
    missing = [str(p) for p in (commands_registry, skills_registry) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "missing canonical registry file(s): " + ", ".join(missing)
        )

    command_ids = set(
        _read_registry_ids(commands_registry, key="commands", id_key="id")
    )
    skill_names = set(_read_registry_ids(skills_registry, key="skills", id_key="name"))

    expected_prompt_files = {f"{cmd_id}.prompt.md" for cmd_id in command_ids}
    expected_claude_command_files = {f"{cmd_id}.md" for cmd_id in command_ids}
    stats: dict[str, int] = {"deleted": 0, "would_delete": 0}

    _prune_managed_files(
        root / ".github" / "prompts",
        expected_prompt_files,
        "*.prompt.md",
        stats,
        dry_run=dry_run,
    )
    _prune_managed_files(
        root / ".codex" / "skills",
        expected_prompt_files,
        "*.prompt.md",
        stats,
        dry_run=dry_run,
    )
    _prune_managed_files(
        root / ".claude" / "commands",
        expected_claude_command_files,
        "sdd-*.md",
        stats,
        dry_run=dry_run,
    )
    _prune_antigravity_skills(root, skill_names, stats, dry_run=dry_run)
    return stats


def _validate_and_load_governance(compiled_path: Path) -> dict[str, Any]:
    if not validate_governance_path(str(compiled_path)):
        message = (
            "Missing/invalid governance artifacts at .sdd/compiled. "
            "Run step 2 first: sdd governance generate --full-bootstrap"
        )
        if _ctx_json():
            _emit_skills_json(
                command="skills full-bootstrap",
                data={
                    "state": "error",
                    "policy_result": "missing_governance_artifacts",
                    "reason": message,
                    "error": {"type": "ValueError", "message": message},
                    "exit_code": 1,
                },
                ok=False,
                error_code="missing_governance_artifacts",
                error_message=message,
                err=True,
            )
        else:
            typer.echo(f"ERROR: {message}", err=True)
        raise typer.Exit(1)
    config = load_governance_config(str(compiled_path))
    items = config.get("items", []) if isinstance(config, dict) else []
    if not isinstance(items, list) or len(items) == 0:
        message = (
            "No governance items found in .sdd/compiled. "
            "Run step 2 first: sdd governance generate --full-bootstrap"
        )
        if _ctx_json():
            _emit_skills_json(
                command="skills full-bootstrap",
                data={
                    "state": "error",
                    "policy_result": "missing_governance_items",
                    "reason": message,
                    "error": {"type": "ValueError", "message": message},
                    "exit_code": 1,
                },
                ok=False,
                error_code="missing_governance_items",
                error_message=message,
                err=True,
            )
        else:
            typer.echo(f"ERROR: {message}", err=True)
        raise typer.Exit(1)
    return config


def _generate_adapters(output_base: Path) -> tuple[int, str | None]:
    try:
        from sdd_adapters.adapter_generator import AdapterGenerator

        adapter_results = AdapterGenerator().generate(output_dir=output_base)
        return len(adapter_results), None
    except Exception as exc:
        return 0, str(exc)


def _handle_adapter_error(adapter_error: str) -> None:
    message = (
        "adapter generation failed during skills full bootstrap. "
        "Fix adapters/templates and retry."
    )
    if _ctx_json():
        _emit_skills_json(
            command="skills full-bootstrap",
            data={
                "state": "error",
                "policy_result": "adapter_generation_failed",
                "reason": message,
                "error": {"type": "RuntimeError", "message": adapter_error},
                "exit_code": 1,
                "details": {"error": adapter_error},
            },
            ok=False,
            error_code="adapter_generation_failed",
            error_message=adapter_error,
            err=True,
        )
    else:
        typer.echo(f"ERROR: {message}", err=True)
        typer.echo(f"- adapter error: {adapter_error}", err=True)
    raise typer.Exit(1)


def _run_reconcile(output_base: Path, *, dry_run: bool) -> tuple[int, int]:
    try:
        reconcile_stats = _reconcile_root_seed_artifacts(output_base, dry_run=dry_run)
        return int(reconcile_stats.get("deleted", 0)), int(
            reconcile_stats.get("would_delete", 0)
        )
    except Exception as exc:
        message = "seed reconciliation failed. Ensure canonical registries are valid and retry."
        if _ctx_json():
            _emit_skills_json(
                command="skills full-bootstrap",
                data={
                    "state": "error",
                    "policy_result": "seed_reconciliation_failed",
                    "reason": message,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                    "exit_code": 1,
                    "details": {"error": str(exc)},
                },
                ok=False,
                error_code="seed_reconciliation_failed",
                error_message=str(exc),
                err=True,
            )
        else:
            typer.echo(f"ERROR: {message}", err=True)
            typer.echo(f"- reconcile error: {exc}", err=True)
        raise typer.Exit(1) from exc


def _run_full_bootstrap(
    *, regenerate_seeds: bool = False, dry_run: bool = False
) -> None:
    ws_root = resolve_workspace_root()
    compiled_path = ws_root / ".sdd" / "compiled"
    config = _validate_and_load_governance(compiled_path)

    output_base = Path(ws_root)
    seeds_dir = output_base / ".vscode" / "agents"
    try:
        seeds_info = generate_agent_seeds(seeds_dir, config)
    except OSError:
        seeds_dir = output_base / ".sdd" / "agents"
        seeds_info = generate_agent_seeds(seeds_dir, config)

    generate_agent_instruction_files(output_base, config)
    generate_agent_prompt_commands(output_base, config)
    skills_result = generate_skills_registry(str(output_base), config)
    commands_result = generate_commands_registry(str(output_base), config)
    reconciliation_summary = reconcile_registries(output_base)
    skill_index_result = generate_skill_index(str(output_base), config)
    cli_index_result = generate_cli_commands_index(str(output_base), config)

    adapter_targets, adapter_error = _generate_adapters(output_base)
    if adapter_error is not None:
        _handle_adapter_error(adapter_error)

    deleted_count = 0
    would_delete_count = 0
    if regenerate_seeds:
        deleted_count, would_delete_count = _run_reconcile(output_base, dry_run=dry_run)

    if _ctx_json():
        _emit_skills_json(
            command="skills full-bootstrap",
            data={
                "state": "ok",
                "policy_result": "skills_full_bootstrap_completed",
                "reason": "generated all available skills/commands/seeds artifacts",
                "exit_code": 0,
                "summary": {
                    "workspace": str(output_base),
                    "compiled_path": str(compiled_path),
                    "seeds_dir": str(seeds_dir),
                    "seed_files": len(seeds_info),
                    "skills_count": int(skills_result.get("skill_count", 0)),
                    "commands_count": int(commands_result.get("command_count", 0)),
                    "skill_index_count": int(skill_index_result.get("skill_count", 0)),
                    "cli_index_count": int(cli_index_result.get("command_count", 0)),
                    "adapter_targets": adapter_targets,
                    "registry_reconciliation": reconciliation_summary.as_json(),
                    "seeds_deleted": deleted_count,
                    "seeds_would_delete": would_delete_count,
                    "dry_run": dry_run,
                },
            },
            ok=True,
        )
        return

    typer.echo("skills full bootstrap completed")
    typer.echo(f"- workspace: {output_base}")
    typer.echo(f"- compiled: {compiled_path}")
    typer.echo(f"- seeds dir: {seeds_dir}")
    typer.echo(f"- seed files: {len(seeds_info)}")
    typer.echo(f"- skills: {int(skills_result.get('skill_count', 0))}")
    typer.echo(f"- commands: {int(commands_result.get('command_count', 0))}")
    typer.echo(
        "- registries reconciled: "
        f"commands(+{reconciliation_summary.commands['added']}/-{reconciliation_summary.commands['removed']}), "
        f"skills(+{reconciliation_summary.skills['added']}/-{reconciliation_summary.skills['removed']})"
    )
    if regenerate_seeds:
        if dry_run:
            typer.echo(f"- stale seeds to delete (dry-run): {would_delete_count}")
        else:
            typer.echo(f"- stale seeds deleted: {deleted_count}")


@app.command("list")
def list_cmd() -> None:
    """List Cmd."""
    skills = list_skills()
    if _ctx_json():
        _emit_skills_json(
            command="skills list",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "listed",
                "reason": "skills loaded",
                "exit_code": 0,
                "skills": [
                    {
                        "name": s.name,
                        "version": s.version,
                        "category": s.category,
                        "status": s.status,
                        "risk_score": s.risk_score,
                    }
                    for s in skills
                ],
            },
            ok=True,
        )
        return

    typer.echo("Available skills:")
    for s in skills:
        typer.echo(
            f"- {s.name} ({s.version}) [{s.category}] risk={s.risk_score} status={s.status}"
        )


@app.command("describe")
def describe(name: str) -> None:
    """Describe."""
    skill = get_skill(name)
    if skill is None:
        if _ctx_json():
            _emit_skills_json(
                command="skills describe",
                data={
                    "state": "error",
                    "profile": "default",
                    "skill": name,
                    "policy_result": "missing_skill",
                    "reason": "skill not found",
                    "error": {"type": "LookupError", "message": "skill not found"},
                    "exit_code": 1,
                },
                ok=False,
                error_code="missing_skill",
                error_message="skill not found",
                err=True,
            )
        else:
            typer.echo(f"ERROR: Skill not found: {name}", err=True)
        raise typer.Exit(1)

    payload = skill.to_dict()
    if _ctx_json():
        _emit_skills_json(
            command="skills describe",
            data={
                "state": "ok",
                "profile": "default",
                "skill": name,
                "policy_result": "described",
                "reason": "skill metadata loaded",
                "exit_code": 0,
                "definition": payload,
            },
            ok=True,
        )
        return

    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command("run")
def run(
    name: str,
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Execute fallback CLI commands. Default is dry-run policy planning.",
    ),
) -> None:
    """Run a skill in dry-run or execute mode."""
    enforce_pipeline = os.environ.get(
        "SDD_ENFORCE_PIPELINE_CORRECT", "0"
    ).strip().lower() in {"1", "true", "yes", "on"}
    if enforce_pipeline and name == "sdd-correct":
        message = "pipeline_required_for_sdd_correct"
        if _ctx_json():
            _emit_skills_json(
                command="skills run",
                data={
                    "state": "error",
                    "profile": "default",
                    "skill": name,
                    "policy_result": "denied",
                    "reason": message,
                    "error": {"type": "PermissionError", "message": message},
                    "exit_code": 1,
                    "next_action": "sdd pipeline <query>",
                },
                ok=False,
                error_code="pipeline_required_for_sdd_correct",
                error_message=message,
                err=True,
            )
        else:
            typer.echo(
                "ERROR: sdd-correct direto bloqueado por política. Use: sdd pipeline <query>",
                err=True,
            )
        raise typer.Exit(1)
    engine = SkillEngine()
    result = engine.run_skill(name, execute=execute, profile="default")
    fallback = result.fallback

    if _ctx_json():
        _emit_skills_json(
            command="skills run",
            data={
                "state": result.state,
                "profile": result.profile,
                "skill": result.skill,
                "policy_result": result.policy_result,
                "reason": result.reason,
                "exit_code": result.exit_code,
                "governance_footer": result.governance_footer,
                "fallback": fallback,
                "command_results": result.command_results,
                "artifacts": result.artifacts,
            },
            ok=result.exit_code == 0,
            error_code=result.policy_result if result.exit_code != 0 else None,
            error_message=result.reason if result.exit_code != 0 else None,
        )
    else:
        typer.echo(f"skill={result.skill}")
        typer.echo(f"policy_result={result.policy_result}")
        typer.echo(f"reason={result.reason}")
        typer.echo("fallback commands:")
        for cmd in fallback:
            typer.echo(f"  - {cmd}")
        typer.echo(result.governance_footer)

    if result.exit_code != 0:
        raise typer.Exit(result.exit_code)


@app.command("export")
def export(
    format: Literal["json", "openai", "langchain", "crewai", "autogen"] = typer.Option(
        "json", "--format", "-f", help="Export format"
    ),
) -> None:
    """Export skill definitions in a machine-consumable format."""
    payload = export_skills_payload(format)
    if _ctx_json() or format == "json":
        _emit_skills_json(
            command="skills export",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "exported",
                "reason": f"exported as {format}",
                "exit_code": 0,
                "payload": payload,
            },
            ok=True,
        )
        return

    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


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
