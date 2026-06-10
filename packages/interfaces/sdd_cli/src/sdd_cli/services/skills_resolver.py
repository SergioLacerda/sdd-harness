"""Skills bootstrap, reconciliation, and validation service functions."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

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
from sdd_cli.services.skills_seed_reconciler import (
    _read_registry_ids as _read_registry_ids,
)
from sdd_cli.services.skills_seed_reconciler import (
    _reconcile_root_seed_artifacts as _reconcile_root_seed_artifacts,
)
from sdd_cli.utils.loader import load_governance_config, validate_governance_path


def _generate_adapters(output_base: Path) -> tuple[int, str | None]:
    try:
        from sdd_adapters.adapter_generator import AdapterGenerator

        adapter_results = AdapterGenerator().generate(output_dir=output_base)
        return len(adapter_results), None
    except Exception as exc:
        return 0, str(exc)


def validate_and_load_governance(
    compiled_path: Path,
    *,
    output_json: bool,
    emit_fn: Callable[..., None],
) -> dict[str, Any]:
    """Validate governance path and load config; raises typer.Exit(1) on failure."""
    if not validate_governance_path(str(compiled_path)):
        message = (
            "Missing/invalid governance artifacts at .sdd/compiled. "
            "Run step 2 first: sdd governance generate --full-bootstrap"
        )
        if output_json:
            emit_fn(
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
        if output_json:
            emit_fn(
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


def handle_adapter_error(
    adapter_error: str,
    *,
    output_json: bool,
    emit_fn: Callable[..., None],
) -> None:
    """Emit adapter error and raise typer.Exit(1)."""
    message = (
        "adapter generation failed during skills full bootstrap. "
        "Fix adapters/templates and retry."
    )
    if output_json:
        emit_fn(
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


def run_reconcile(
    output_base: Path,
    *,
    dry_run: bool,
    output_json: bool,
    emit_fn: Callable[..., None],
) -> tuple[int, int]:
    """Run seed reconciliation; raises typer.Exit(1) on failure."""
    try:
        reconcile_stats = _reconcile_root_seed_artifacts(output_base, dry_run=dry_run)
        return int(reconcile_stats.get("deleted", 0)), int(
            reconcile_stats.get("would_delete", 0)
        )
    except Exception as exc:
        message = "seed reconciliation failed. Ensure canonical registries are valid and retry."
        if output_json:
            emit_fn(
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


def run_full_bootstrap(
    ws_root: Path,
    *,
    regenerate_seeds: bool = False,
    dry_run: bool = False,
    output_json: bool,
    emit_fn: Callable[..., None],
) -> None:
    """Execute full bootstrap pipeline and emit output."""
    compiled_path = ws_root / ".sdd" / "compiled"
    config = validate_and_load_governance(
        compiled_path, output_json=output_json, emit_fn=emit_fn
    )

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
        handle_adapter_error(adapter_error, output_json=output_json, emit_fn=emit_fn)

    deleted_count = 0
    would_delete_count = 0
    if regenerate_seeds:
        deleted_count, would_delete_count = run_reconcile(
            output_base, dry_run=dry_run, output_json=output_json, emit_fn=emit_fn
        )

    if output_json:
        emit_fn(
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
