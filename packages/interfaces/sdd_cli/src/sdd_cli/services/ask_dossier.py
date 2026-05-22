"""Dossier helpers extracted from ask backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def handle_dossier_error(exc: Exception, *, logger: Any, typer_module: Any) -> None:
    """Handle errors during dossier generation."""
    from sdd_runtime.context import BudgetBreachError

    if isinstance(exc, BudgetBreachError):
        typer_module.echo(
            f"[red]❌ Budget breach: {exc}[/red]",
            err=True,
        )
        raise SystemExit(1) from exc
    logger.debug("Dossier builder failed: %s", exc)
    typer_module.echo(
        "[yellow]⚠ Dossier generation failed (continuing with minimal output)[/yellow]",
        err=True,
    )


def resolve_dossier_budget(budget: int | None) -> int:
    """Resolve dossier budget from input or runtime config."""
    if budget is not None:
        return budget
    from sdd_runtime.metrics import _load_token_budget_config

    config = _load_token_budget_config()
    return int(config.get("token_budget_ceiling", 100000))


def load_dossier_artifact(
    workspace_root: Path, *, compiled_active_dir_fn: Any
) -> Any | None:
    """Load compiled governance artifact for dossier context."""
    from sdd_runtime.artifacts import CompiledArtifact

    compiled_path = compiled_active_dir_fn(workspace_root) / "governance-core.json"
    if not compiled_path.exists():
        return None
    try:
        return CompiledArtifact.from_governance_json(compiled_path)
    except Exception:
        return None


def build_dossier_lines(
    query: str,
    skill: str | None,
    budget: int,
    mandates_count: int,
    budget_utilization_pct: float,
    context_result: Any,
) -> list[str]:
    """Build human-readable dossier output lines."""
    lines = [
        "",
        "## DOSSIER: Task Context Analysis",
        f"**Task Query:** {query}",
        "",
    ]
    if skill:
        lines.extend([f"**Skill:** `{skill}` (governance-required)", ""])
    lines.extend(
        [
            f"**Budget:** {budget} tokens (current utilization: {budget_utilization_pct:.1f}%)",
            f"**Mandates Active:** {mandates_count}",
            f"**Context Items Loaded:** {context_result.matched}",
            "",
        ]
    )
    if context_result.compression_ratio is not None:
        lines.extend(
            [
                f"**Compression Applied:** {context_result.compression_ratio:.2f}x (YELLOW zone)",
                "",
            ]
        )
    lines.extend(
        [
            "### Applicable Governance",
            *context_result.items,
            "",
            "### Recommended Approach",
        ]
    )
    if context_result.items:
        lines.append("- Respect the mandates and guidelines above")
    lines.extend(
        [
            "- Declare intent before tool invocation",
            "- Emit telemetry on all transitions",
            "",
        ]
    )
    return lines


def build_and_output_dossier(
    query: str,
    skill: str | None,
    budget: int | None,
    mandates_count: int,
    *,
    workspace_root: Path | None,
    resolve_workspace_root_fn: Any,
    compiled_active_dir_fn: Any,
    logger: Any,
    typer_module: Any,
) -> None:
    """Build and output comprehensive task dossier."""
    try:
        from sdd_runtime.context import ContextLoader, ContextRequest

        resolved_budget = resolve_dossier_budget(budget)
        budget_utilization_pct = 50.0
        workspace = workspace_root or resolve_workspace_root_fn()
        artifact = load_dossier_artifact(
            workspace,
            compiled_active_dir_fn=compiled_active_dir_fn,
        )
        context_result = ContextLoader().load_result(
            ContextRequest(
                query=query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=budget_utilization_pct,
                prefer_full_summary=(
                    str(os.environ.get("SDD_ASK_PREFER_FULL_SUMMARY", ""))
                    .strip()
                    .lower()
                    in {"1", "true", "yes", "on"}
                ),
            )
        )
        typer_module.echo(
            "\n".join(
                build_dossier_lines(
                    query=query,
                    skill=skill,
                    budget=resolved_budget,
                    mandates_count=mandates_count,
                    budget_utilization_pct=budget_utilization_pct,
                    context_result=context_result,
                )
            )
        )
    except Exception as exc:
        handle_dossier_error(exc, logger=logger, typer_module=typer_module)
