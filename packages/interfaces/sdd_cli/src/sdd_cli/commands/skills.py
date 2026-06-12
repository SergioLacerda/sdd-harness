"""Skill layer commands for capability-oriented operations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import click
import typer
from sdd_runtime import SkillEngine

from sdd_cli.commands.skills_learning import app as _learning_app
from sdd_cli.services.skills_output import emit_skills_json as _emit_skills_json
from sdd_cli.services.skills_registry import (
    export_skills_payload,
    get_skill,
    list_skills,
)
from sdd_cli.services.skills_resolver import (
    _generate_adapters,  # noqa: F401  backward-compat re-export for unit tests
    _read_registry_ids,  # noqa: F401  backward-compat re-export for unit tests
    _reconcile_root_seed_artifacts,  # noqa: F401  backward-compat re-export for unit tests
    handle_adapter_error,
    run_reconcile,
    validate_and_load_governance,
)
from sdd_cli.services.skills_resolver import (
    run_full_bootstrap as _run_full_bootstrap_service,
)
from sdd_cli.utils.output import is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(help="Capability-oriented skill commands")
app.registered_commands.extend(_learning_app.registered_commands)


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _validate_and_load_governance(compiled_path: Path) -> dict[str, Any]:
    return validate_and_load_governance(
        compiled_path, output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


def _handle_adapter_error(adapter_error: str) -> None:
    handle_adapter_error(
        adapter_error, output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


def _run_reconcile(output_base: Path, *, dry_run: bool) -> tuple[int, int]:
    return run_reconcile(
        output_base, dry_run=dry_run, output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


def _run_full_bootstrap(
    *, regenerate_seeds: bool = False, dry_run: bool = False
) -> None:
    ws_root = resolve_workspace_root()
    _run_full_bootstrap_service(
        ws_root,
        regenerate_seeds=regenerate_seeds,
        dry_run=dry_run,
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )


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
        raise click.exceptions.Exit(2)

    if not full_bootstrap and not regenerate_seeds:
        return
    if ctx.invoked_subcommand is not None:
        return
    _run_full_bootstrap(regenerate_seeds=regenerate_seeds, dry_run=dry_run)


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
                    "next_action": "sdd skills run sdd-pipeline",
                },
                ok=False,
                error_code="pipeline_required_for_sdd_correct",
                error_message=message,
                err=True,
            )
        else:
            typer.echo(
                "ERROR: sdd-correct direto bloqueado por política. Use: sdd skills run sdd-pipeline",
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
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Export format",
    ),
) -> None:
    """Export skill definitions in a machine-consumable format."""
    format = format.strip().lower()
    if format not in {"json", "openai", "langchain", "crewai", "autogen"}:
        raise typer.BadParameter(
            "format must be one of: json, openai, langchain, crewai, autogen."
        )
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
