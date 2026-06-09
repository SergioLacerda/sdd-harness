"""Artifact-oriented governance handlers (compile/generate/consistency)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sdd_cli.services.governance_payloads import (
    build_governance_compile_data,
    build_governance_generate_data,
    governance_error,
    governance_ok,
)
from sdd_cli.utils.loader import resolve_governance_compiled_dir
from sdd_cli.utils.output import emit_json


def run_governance_compile_json(
    *,
    phase_1: dict[str, Any],
    phase_2: dict[str, Any],
    core_fingerprint: str,
    consistency_ok: bool,
    consistency_reason: str,
) -> tuple[dict[str, Any], bool]:
    """Build canonical JSON payload for compile command.

    Returns `(payload, is_error)`.
    """
    if not consistency_ok:
        data = build_governance_compile_data(
            core_items=int(phase_1.get("core_item_count", 0)),
            client_items=int(phase_1.get("client_item_count", 0)),
            core_msgpack=str(phase_2.get("core_msgpack_file", "N/A")),
            client_msgpack=str(phase_2.get("client_msgpack_file", "N/A")),
            core_fingerprint=core_fingerprint,
            consistency_reason=consistency_reason,
            exit_code=1,
        )
        return (
            governance_error(
                "governance compile",
                data,
                code="artifact_consistency_failed",
                message=f"Artifact consistency failed: {consistency_reason}",
            ),
            True,
        )

    data = build_governance_compile_data(
        core_items=int(phase_1.get("core_item_count", 0)),
        client_items=int(phase_1.get("client_item_count", 0)),
        core_msgpack=str(phase_2.get("core_msgpack_file", "N/A")),
        client_msgpack=str(phase_2.get("client_msgpack_file", "N/A")),
        core_fingerprint=core_fingerprint,
        exit_code=0,
    )
    return governance_ok("governance compile", data), False


def render_governance_compile_table(
    *,
    console: Console,
    phase_1: dict[str, Any],
    phase_2: dict[str, Any],
    core_fingerprint: str,
) -> None:
    """Render human-readable compile summary."""
    table = Table(title="Compilation Summary", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Core items", str(int(phase_1.get("core_item_count", 0))))
    table.add_row("Client items", str(int(phase_1.get("client_item_count", 0))))
    table.add_row("Core msgpack", str(phase_2.get("core_msgpack_file", "N/A")))
    table.add_row("Client msgpack", str(phase_2.get("client_msgpack_file", "N/A")))
    console.print(table)


def run_governance_generate_json(
    *,
    resolved_path: str,
    output_base: Path,
    seeds_dir: Path,
    rows: list[dict[str, Any]],
    skills_generated: bool,
    skill_index_generated: bool,
    cli_index_generated: bool,
) -> dict[str, Any]:
    """Build canonical JSON payload for generate command."""
    data = build_governance_generate_data(
        path=resolved_path,
        output_base=str(output_base),
        seeds_dir=str(seeds_dir),
        generated_files=rows,
        skills_generated=skills_generated,
        skill_index_generated=skill_index_generated,
        cli_index_generated=cli_index_generated,
        exit_code=0,
    )
    return governance_ok("governance generate", data)


def emit_generate_invalid_path_error(*, resolved_path: str, output_dir: str) -> None:
    """Emit canonical invalid-path error for governance generate."""
    data = {"path": resolved_path, "output_base": output_dir, "exit_code": 1}
    payload = governance_error(
        "governance generate",
        data,
        code="invalid_governance_path",
        message=f"Invalid governance path: {resolved_path}",
    )
    emit_json(payload, err=True)
    raise typer.Exit(1)


def emit_generate_missing_items_error(*, resolved_path: str, output_dir: str) -> None:
    """Emit canonical missing-items error for governance generate."""
    data = {"path": resolved_path, "output_base": output_dir, "exit_code": 1}
    payload = governance_error(
        "governance generate",
        data,
        code="missing_governance_items",
        message=(
            "No governance items loaded. Run 'sdd governance compile' "
            "before 'sdd governance generate'."
        ),
    )
    emit_json(payload, err=True)
    raise typer.Exit(1)


def render_generate_table(
    *, console: Console, rows: list[dict[str, Any]], seeds_dir: Path
) -> None:
    """Render human-readable generated files table."""
    table = Table(title="Generated Files", show_header=True, header_style="bold")
    table.add_column("Agent Template", style="cyan")
    table.add_column("Location", style="green")
    table.add_column("Status", style="green")
    for row in rows:
        table.add_row(row["agent_template"], row["location"], row["status"])
    console.print(table)
    console.print(
        Panel(
            f"[green]Agent seeds generated to {seeds_dir}[/green]",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# Artifact consistency checks (extracted from commands/governance.py)
# ---------------------------------------------------------------------------


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_consistency_artifacts(
    compiled_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    audit_dir = compiled_dir / "audit"
    core_json = _safe_json(compiled_dir / "governance-core.json") or _safe_json(
        audit_dir / "governance-core.json"
    )
    client_json = _safe_json(compiled_dir / "governance-client.json") or _safe_json(
        audit_dir / "governance-client.json"
    )
    core_meta = _safe_json(audit_dir / "metadata-core.json") or _safe_json(
        compiled_dir / "metadata-core.json"
    )
    client_meta = _safe_json(audit_dir / "metadata-client-template.json") or _safe_json(
        compiled_dir / "metadata-client-template.json"
    )
    if any(x is None for x in (core_json, client_json, core_meta, client_meta)):
        return None
    assert core_json is not None
    assert client_json is not None
    assert core_meta is not None
    assert client_meta is not None
    return core_json, client_json, core_meta, client_meta


def _count_items_by_type(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        item_type = str(item.get("type", "UNKNOWN")).upper()
        counts[item_type] = counts.get(item_type, 0) + 1
    return counts


def _has_malformed_titles(items: list[dict[str, Any]]) -> bool:
    for item in items:
        title = str(item.get("title") or "").strip().lower()
        if title.startswith("- status:"):
            return True
    return False


def _validate_payload_vs_metadata(
    payload: dict[str, Any], metadata: dict[str, Any], label: str
) -> str | None:
    items = payload.get("items", [])
    if not isinstance(items, list):
        return "invalid payload schema: items must be a list"
    if payload.get("fingerprint") != metadata.get("fingerprint"):
        return f"{label} fingerprint mismatch between payload and metadata"
    if int(metadata.get("item_count", -1)) != len(items):
        return f"{label} item_count mismatch"
    if _count_items_by_type(items) != dict(metadata.get("items_by_type", {})):
        return f"{label} items_by_type mismatch"
    if label == "core" and _has_malformed_titles(items):
        return "malformed mandate title detected"
    return None


def check_artifact_consistency(path: str) -> tuple[bool, str]:
    """Cross-check compiled governance JSON and metadata consistency."""
    compiled_dir = resolve_governance_compiled_dir(path)
    if compiled_dir is None:
        return (
            False,
            f"could not resolve compiled governance directory at {path} (check path policy or missing artifacts)",
        )
    loaded = _load_consistency_artifacts(compiled_dir)
    if loaded is None:
        return False, "missing governance JSON or metadata artifacts"
    core_json, client_json, core_meta, client_meta = loaded

    core_issue = _validate_payload_vs_metadata(core_json, core_meta, "core")
    if core_issue:
        return False, core_issue
    client_issue = _validate_payload_vs_metadata(client_json, client_meta, "client")
    if client_issue:
        return False, client_issue
    if client_json.get("fingerprint_core_salt") != client_meta.get(
        "fingerprint_core_salt"
    ):
        return False, "client fingerprint_core_salt mismatch"

    return True, "ok"
