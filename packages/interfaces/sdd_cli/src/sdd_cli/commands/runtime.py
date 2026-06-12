"""sdd runtime — workspace runtime state commands."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any, Literal

import typer

from sdd_cli.services.runtime_handler import (
    _check_cache_staleness,
    _emit_runtime_status,  # noqa: F401  patchable by tests
    _footer_drift_status,
    _normalize_report,
    _read_profile,
    _show_ask_confidence,  # noqa: F401  patchable by tests
)
from sdd_cli.utils.output import emit_json, is_json_mode, is_verbose_mode
from sdd_cli.utils.sdd_authority import (
    PathPolicyViolation,
    enforce_path_policy,
    profile_active_path,
    resolve_workspace_root,
)

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.callback()
def _() -> None:
    """Workspace runtime operations."""


@app.command()
def status(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full layer-by-layer breakdown."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip cache and run fresh validation."
    ),
    update_cache: bool = typer.Option(
        False,
        "--update-cache",
        help="Print M003 compliance quiz and refresh .sdd-cache.md.",
    ),
) -> None:
    """Show current workspace governance state (AHP + GAP + runtime drift)."""

    root = resolve_workspace_root()
    try:
        root = enforce_path_policy(root, workspace_root=root, mode="normal")
    except PathPolicyViolation as exc:
        typer.echo(
            f"[SDD] ERROR: workspace path rejected — {exc.reason}\n  Hint: {exc.hint}",
            err=True,
        )
        raise typer.Exit(2) from exc

    if update_cache:
        _do_update_cache(root)
        raise typer.Exit(0)

    try:
        from sdd_runtime import format_governance_footer

        from sdd_core.governance.handshake import AgentHandshakeProtocol
    except ImportError as exc:
        typer.echo(f"ERROR: sdd_core not installed — {exc}", err=True)
        raise typer.Exit(2) from exc

    effective_verbose = bool(verbose or is_verbose_mode(ctx))
    output_json = is_json_mode(ctx)

    output_mode: Literal["silent", "compact", "verbose"] = (
        "verbose" if effective_verbose else "compact"
    )

    if effective_verbose and not output_json:
        cache_file = root / ".sdd" / "runtime" / "governance-state.json"
        typer.echo(_format_diagnostic_block(root, cache_file=cache_file))
        typer.echo("")

    ahp = AgentHandshakeProtocol(project_root=root)
    state, report = ahp.validate(output_mode=output_mode, force_recheck=force)

    _EXIT_CODES = {
        "HEALTHY": 0,
        "PARTIAL": 0,
        "NOT_INITIALIZED": 1,
        "MISCONFIGURED": 2,
        "NOT_CONNECTED": 3,
    }
    code = _EXIT_CODES.get(state, 1)

    workspace_profile = _read_profile(root)
    current_profile = workspace_profile
    if isinstance(ctx.obj, dict):
        current_profile = str(
            ctx.obj.get("profile", workspace_profile) or workspace_profile
        )

    try:
        drift_info = _emit_runtime_status(
            root=root,
            ahp_state=state,
            workspace_profile=workspace_profile,
            current_profile=current_profile,
        )
    except ImportError as exc:
        typer.echo(f"ERROR: sdd_runtime not installed — {exc}", err=True)
        raise typer.Exit(2) from exc

    governance_footer = format_governance_footer(
        drift=_footer_drift_status(drift_info),
        governance=state.lower(),
        profile=ahp.skill_profile,
    )

    _render_status_output(
        ahp=ahp,
        state=state,
        report=report,
        code=code,
        drift_info=drift_info,
        governance_footer=governance_footer,
        cache_staleness=_check_cache_staleness(root),
        ask_confidence=_show_ask_confidence(root, emit=not output_json),
        output_json=output_json,
        output_mode=output_mode,
    )

    if code != 0:
        raise typer.Exit(code)


def _do_update_cache(root: Path) -> None:
    """Print M003 compliance quiz from compiled governance and refresh .sdd-cache.md."""
    import os as _os
    import time as _time

    gov_path = root / ".sdd" / "compiled" / "governance-core.json"
    if not gov_path.exists():
        typer.echo(
            "ERROR: governance-core.json not found. Run: sdd governance compile",
            err=True,
        )
        raise typer.Exit(1)

    try:
        from sdd_compiler.ast import GovernanceAST
    except ImportError as exc:
        typer.echo(f"ERROR: sdd_compiler not installed — {exc}", err=True)
        raise typer.Exit(2) from exc

    ast = GovernanceAST.from_compiled_json(gov_path)
    m003 = ast.item_by_id("M003")

    if m003 is None or not m003.enforcement_steps:
        typer.echo(
            "ERROR: M003 enforcement_steps not compiled.\n"
            "Run: sdd governance compile  (requires mandate-pipeline-enrichment)",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo("# M003 — Context Awareness & Task Caching\n")
    typer.echo("Confirm the following before the cache is refreshed:\n")
    for i, step in enumerate(m003.enforcement_steps, 1):
        typer.echo(f"{i}. {step}")
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


def _format_diagnostic_block(root: Path, *, cache_file: Path) -> str:
    """Return the verbose diagnostic header block for --verbose output."""
    import importlib.metadata
    import time as _time

    lines = ["═══ SDD Runtime Diagnostics ═══"]
    lines.append(f"workspace root : {root}")

    profile_path = profile_active_path(root)
    profile_type = _read_profile(root) or "unknown"
    try:
        rel = profile_path.relative_to(root)
    except ValueError:
        rel = profile_path
    lines.append(f"profile file   : {rel} [type={profile_type}]")

    if cache_file.exists():
        try:
            import json as _json

            mtime = cache_file.stat().st_mtime
            age_sec = int(_time.time() - mtime)
            raw = _json.loads(cache_file.read_text(encoding="utf-8"))
            cached_state = raw.get("state", "?")
            try:
                rel_cache = cache_file.relative_to(root)
            except ValueError:
                rel_cache = cache_file
            lines.append(
                f"cache file     : {rel_cache} [age={age_sec}s, state={cached_state}]"
            )
        except Exception:
            lines.append(
                "cache file     : .sdd/runtime/governance-state.json [unreadable]"
            )
    else:
        lines.append(
            "cache file     : .sdd/runtime/governance-state.json [NONE, revalidating]"
        )

    for pkg in ("sdd-core", "sdd-cli"):
        with contextlib.suppress(Exception):
            ver = importlib.metadata.version(pkg)
            lines.append(f"{pkg:<14} : {ver}")

    return "\n".join(lines)


def _render_status_output(
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
            "report": _normalize_report(report),
            "drift": drift_info,
            "ask_confidence": ask_confidence,
            "governance_footer": governance_footer,
            "cache_staleness": cache_staleness,
        }
        if code == 0:
            payload = build_ok_result("runtime status", data)
        else:
            payload = build_error_result(
                "runtime status",
                data,
                code="runtime_state_not_healthy",
                message=f"runtime status returned non-success state '{state}'",
            )
        emit_json(payload, err=code != 0)
    else:
        typer.echo(governance_footer)
