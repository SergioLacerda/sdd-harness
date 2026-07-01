"""Support helpers for the runtime command group."""

from __future__ import annotations

import contextlib
import json
import time as _time
from pathlib import Path
from typing import Any

import typer


def do_update_cache(root: Path) -> None:
    """Print M003 compliance quiz from compiled governance and refresh .sdd-cache.md."""
    import os as _os

    gov_path = root / ".sdd" / "compiled" / "governance-core.json"
    if not gov_path.exists():
        typer.echo(
            "ERROR: governance-core.json not found. Run: sdd governance compile",
            err=True,
        )
        raise typer.Exit(1)
    try:
        from sdd_core.governance.ast import GovernanceAST
    except ImportError as exc:
        typer.echo(f"ERROR: sdd_core.governance.ast not importable — {exc}", err=True)
        raise typer.Exit(2) from exc
    ast = GovernanceAST.from_compiled_json(gov_path)
    m003 = ast.item_by_id("M003")
    if m003 is None or not m003.enforcement_steps:
        typer.echo(
            "ERROR: M003 enforcement_steps not compiled.\nRun: sdd governance compile  (requires mandate-pipeline-enrichment)",
            err=True,
        )
        raise typer.Exit(1)
    typer.echo("# M003 — Context Awareness & Task Caching\n")
    typer.echo("Confirm the following before the cache is refreshed:\n")
    for index, step in enumerate(m003.enforcement_steps, 1):
        typer.echo(f"{index}. {step}")
    typer.echo("\n---")
    typer.echo("Refreshing .sdd-cache.md...")
    cache_file = root / ".sdd" / "runtime" / ".sdd-cache.md"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if cache_file.exists():
        now = _time.time()
        _os.utime(cache_file, (now, now))
    else:
        cache_file.write_text(
            "# SDD Cache\n\nInitialized by: sdd runtime status --update-cache\n",
            encoding="utf-8",
        )
    typer.echo("✓ .sdd-cache.md refreshed.")


def format_diagnostic_block(
    root: Path, *, cache_file: Path, profile_active_path: Any, read_profile: Any
) -> str:
    """Return the verbose diagnostic header block for --verbose output."""
    import importlib.metadata

    lines = ["═══ SDD Runtime Diagnostics ═══", f"workspace root : {root}"]
    profile_path = profile_active_path(root)
    profile_type = read_profile(root) or "unknown"
    try:
        rel = profile_path.relative_to(root)
    except ValueError:
        rel = profile_path
    lines.append(f"profile file   : {rel} [type={profile_type}]")
    lines.append(_cache_line(root, cache_file))
    for pkg in ("sdd-core", "sdd-cli"):
        with contextlib.suppress(Exception):
            lines.append(f"{pkg:<14} : {importlib.metadata.version(pkg)}")
    return "\n".join(lines)


def _cache_line(root: Path, cache_file: Path) -> str:
    if cache_file.exists():
        try:
            mtime = cache_file.stat().st_mtime
            age_sec = int(_time.time() - mtime)
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_state = raw.get("state", "?")
            try:
                rel_cache = cache_file.relative_to(root)
            except ValueError:
                rel_cache = cache_file
            return (
                f"cache file     : {rel_cache} [age={age_sec}s, state={cached_state}]"
            )
        except Exception:
            return "cache file     : .sdd/runtime/governance-state.json [unreadable]"
    return "cache file     : .sdd/runtime/governance-state.json [NONE, revalidating]"


def render_status_output(
    *,
    ahp: Any,
    state: str,
    report: Any,
    code: int,
    drift_info: dict[str, Any],
    governance_footer: str,
    cache_staleness: dict[str, Any],
    ask_confidence: dict[str, Any] | None,
    output_json: bool,
    output_mode: str,
    normalize_report: Any,
    emit_json_fn: Any,
) -> None:
    """Emit status output: AHP report, cache staleness warning, JSON or text footer."""
    from sdd_cli.shared.contracts import build_error_result, build_ok_result

    if not output_json:
        typer.echo(ahp.format_combined_output(state, report, mode=output_mode))
    if not output_json and cache_staleness["stale"]:
        typer.echo(
            f"\nWARNING L2: .sdd-cache.md is stale ({cache_staleness['age_min']} min ago)."
            " Update it before committing to a protected branch."
            "\n  → Run: sdd runtime status --update-cache",
            err=False,
        )
    if output_json:
        data = {
            "state": state,
            "exit_code": code,
            "report": normalize_report(report),
            "drift": drift_info,
            "ask_confidence": ask_confidence,
            "governance_footer": governance_footer,
            "cache_staleness": cache_staleness,
        }
        payload = (
            build_ok_result("runtime status", data)
            if code == 0
            else build_error_result(
                "runtime status",
                data,
                code="runtime_state_not_healthy",
                message=f"runtime status returned non-success state '{state}'",
            )
        )
        emit_json_fn(payload, err=code != 0)
        return
    typer.echo(governance_footer)
