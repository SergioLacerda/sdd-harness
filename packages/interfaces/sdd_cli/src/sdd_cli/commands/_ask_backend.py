"""sdd ask — governed context query command.

Security:
  - Query text is NEVER logged; only sha256[:8] hash is recorded.
  - trace_id is uuid4 local-only; no external correlation.
  - Compliance JSONL is append-only at .sdd/runtime/compliance-events.jsonl.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import typer
from sdd_runtime import OtelBridge, TelemetrySink
from sdd_runtime.otel import OtlpHttpExporter
from typer.models import OptionInfo

from sdd_cli.services.ask_context import (
    check_fingerprint_drift as _check_fingerprint_drift_impl,
)
from sdd_cli.services.ask_context import (
    get_profile_state as _get_profile_state_impl,
)
from sdd_cli.services.ask_context import (
    load_compiled_governance as _load_compiled_governance_from_ctx,
)
from sdd_cli.services.ask_context import (
    write_runtime_cache as _write_runtime_cache_impl,
)
from sdd_cli.services.ask_dossier import (
    build_and_output_dossier as _build_and_output_dossier_impl,
)
from sdd_cli.services.ask_dossier import (
    build_dossier_lines as _build_dossier_lines_impl,
)
from sdd_cli.services.ask_dossier import (
    handle_dossier_error as _handle_dossier_error_impl,
)
from sdd_cli.services.ask_dossier import (
    load_dossier_artifact as _load_dossier_artifact_impl,
)
from sdd_cli.services.ask_dossier import (
    resolve_dossier_budget as _resolve_dossier_budget_impl,
)
from sdd_cli.services.ask_filter import (
    collect_learning_signals as _collect_learning_signals_impl,
)
from sdd_cli.services.ask_filter import (
    count_signals_from_tail as _count_signals_from_tail_impl,
)
from sdd_cli.services.ask_governance import (
    GovResult as _GovResult,
)
from sdd_cli.services.ask_governance import (
    fingerprint_file as _fingerprint_file_impl,
)
from sdd_cli.services.ask_governance import (
    signature_mode as _signature_mode_impl,
)
from sdd_cli.services.ask_governance import (
    try_sdd_compiled_dir as _try_sdd_compiled_dir_impl,
)
from sdd_cli.services.ask_governance import (
    validate_signature_for_artifact as _validate_signature_for_artifact_impl,
)
from sdd_cli.services.ask_organize import (
    run_sdd_organize,
)
from sdd_cli.services.ask_organize import (
    should_use_organize as _should_use_organize,
)
from sdd_cli.services.ask_payload import (
    build_ask_json_data,
)
from sdd_cli.services.ask_renderer import (
    render_context_header as _render_context_header,
)
from sdd_cli.services.ask_renderer import (
    render_governance_footer as _render_governance_footer_impl,
)
from sdd_cli.services.ask_telemetry import (
    emit_ask_telemetry as _emit_ask_telemetry_impl,
)
from sdd_cli.services.ask_telemetry import (
    resolve_tokens as _resolve_tokens_impl,
)
from sdd_cli.services.ask_telemetry import (
    upsert_ask_session as _upsert_ask_session_impl,
)
from sdd_cli.utils.output import emit_json, is_json_mode
from sdd_cli.utils.sdd_authority import (
    compiled_active_dir,
    enforce_path_policy,
)
from sdd_cli.utils.sdd_authority import (
    resolve_workspace_root as resolve_authority_workspace_root,
)

__all__ = [
    "app",
    "ask_cmd",
    "build_governed_ask_snapshot",
    "run_sdd_organize",
    "_should_use_organize",
    "_resolve_tokens",
    "_capture_effective_tokens",
    "_emit_ask_telemetry",
    "_resolve_workspace_root",
    "_get_profile_state",
    "_run_organize_intake",
    "_render_context_output",
    "_try_sdd_compiled_dir",
    "_hash_query",
    "_load_compiled_governance",
    "_check_fingerprint_drift",
    "_check_budget_zone_and_compress",
    "_write_runtime_cache",
    "_upsert_ask_session",
    "_emit_state_warnings",
    "_governance_footer_for_state",
    "_guard_budget_breach",
    "_guard_handshake",
    "TelemetrySink",
    "OtelBridge",
    "OtlpHttpExporter",
]

app = typer.Typer(help="Query SDD governance context.")
logger = logging.getLogger(__name__)
_LEARNING_WINDOW_DAYS = 7


@dataclass(frozen=True)
class _AskInputs:
    query: str
    dossier: bool
    skill: str | None
    budget: int | None
    full: bool
    log_path: str | None
    log_format: str
    tokens_input: int | None
    tokens_output: int | None


@dataclass(frozen=True)
class _AskSessionContext:
    workspace_root: Path
    organize_used: bool
    organize_reason: str
    organize_artifact_path: str
    organize_chunks: int
    organize_retrieval: str
    profile: str
    state: str
    agent_id: str
    trace_id: str
    start_mono: float
    start_ts: str


_TRUE_VALUES = {"1", "true", "yes", "on"}
_JSON_MODE_OVERRIDE: ContextVar[bool | None] = ContextVar(
    "ask_json_mode_override", default=None
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:8]


def _normalize_typer_value(value: Any, default: Any) -> Any:
    """Normalize Typer OptionInfo leakage when command functions are called directly."""
    return default if isinstance(value, OptionInfo) else value


def _prefer_full_summary() -> bool:
    """Return whether ask context rendering should prefer summary_full."""
    raw = os.environ.get("SDD_ASK_PREFER_FULL_SUMMARY", "")
    return raw.strip().lower() in _TRUE_VALUES


def _try_sdd_compiled_dir(sdd_compiled: Path) -> tuple[str, str, int] | None:
    return _try_sdd_compiled_dir_impl(sdd_compiled, logger=logger)


def _signature_mode() -> str:
    return _signature_mode_impl()


def _validate_signature_for_artifact(
    artifact_path: Path, *, signature_mode: str
) -> tuple[bool, bool, str, str]:
    return _validate_signature_for_artifact_impl(
        artifact_path, signature_mode_value=signature_mode
    )


def _load_compiled_governance(workspace_root: Path) -> _GovResult:
    return _load_compiled_governance_from_ctx(workspace_root)


def _fingerprint_file(path: Path) -> str:
    return _fingerprint_file_impl(path)


def _resolve_workspace_root() -> Path:
    root = resolve_authority_workspace_root()
    return enforce_path_policy(root, workspace_root=root, mode="normal")


def _get_cached_ahp() -> dict[str, Any] | None:
    ctx = click.get_current_context(silent=True)
    if ctx is not None and isinstance(ctx.obj, dict):
        cached = ctx.obj.get("_ahp")
        if isinstance(cached, dict):
            return cached
    return None


def _get_profile_state() -> tuple[str, str]:
    """Return (profile, state) best-effort; never raises."""
    return _get_profile_state_impl(_resolve_workspace_root())


def _write_runtime_cache(workspace_root: Path, last_ask: dict[str, Any]) -> None:
    _write_runtime_cache_impl(workspace_root, last_ask)


def _runtime_drift_check(workspace_root: Path, loaded_fingerprint: str) -> bool:
    """Return True if the loaded fingerprint differs from the cached governance state.

    Compares ``loaded_fingerprint`` (current artifact) against the fingerprint
    stored in governance-state.json from the previous run, so that a recompile
    is detected on the next invocation.
    """
    return _check_fingerprint_drift(workspace_root, loaded_fingerprint)


def _resolve_ask_drift_type(*, drift_detected: bool, authenticated: bool) -> str:
    """Classify ask drift for telemetry consumers."""
    if not drift_detected:
        return "none"
    if not authenticated:
        return "auth_drift"
    return "fingerprint_drift"


def _resolve_ask_degraded_reason(
    *, degraded: bool, degrade_reason: str, authenticated: bool
) -> str:
    """Provide stable degraded reason when none is explicitly available."""
    if degrade_reason.strip():
        return degrade_reason.strip()
    if degraded and not authenticated:
        return "artifact_unverified"
    if degraded:
        return "degraded_unspecified"
    return ""


def _check_fingerprint_drift(workspace_root: Path, loaded_fingerprint: str) -> bool:
    return _check_fingerprint_drift_impl(workspace_root, loaded_fingerprint)


def _render_context_output(
    fingerprint: str,
    mandates_count: int,
    *,
    degraded: bool,
    degrade_reason: str,
) -> str:
    return _render_context_header(
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )


def _governance_footer_for_state(
    *,
    state: str,
    profile: str,
    drift_detected: bool,
) -> str:
    return _render_governance_footer_impl(
        state=state, profile=profile, drift_detected=drift_detected
    )


def _json_mode() -> bool:
    override = _JSON_MODE_OVERRIDE.get()
    if override is not None:
        return override
    ctx = click.get_current_context(silent=True)
    while ctx is not None:
        if is_json_mode(ctx):
            return True
        ctx = ctx.parent
    return False


def _count_signals_from_tail(
    path: Path, signals: dict[str, int], cutoff_ts: float, *, from_failures: bool
) -> None:
    _count_signals_from_tail_impl(path, signals, cutoff_ts, from_failures=from_failures)


def _collect_learning_signals(
    workspace_root: Path, *, window_days: int = _LEARNING_WINDOW_DAYS
) -> dict[str, int]:
    return _collect_learning_signals_impl(workspace_root, window_days=window_days)


# ---------------------------------------------------------------------------
# Budget circuit breaker
# ---------------------------------------------------------------------------


_BREACH_EXIT_CODE = 3


def _guard_budget_breach() -> None:
    """Block context loading if the session budget is in BREACH state.

    Reads ``SDD_BUDGET_UTILIZATION_PCT`` from the environment (set by the
    agent after each context load).  When utilization is ≥ 100 the command
    is aborted with exit code 3 and a human checkpoint message is displayed.

    This enforces §economy/execution-budget.md Circuit Breaker Rule 3:
    "Agent MUST NOT load additional context once BREACH is reached."
    """
    pct_str = os.environ.get("SDD_BUDGET_UTILIZATION_PCT", "").strip()
    if not pct_str:
        return
    try:
        pct = float(pct_str)
    except ValueError:
        return
    if pct < 100.0:
        return

    typer.echo(
        f"\n[SDD] BUDGET BREACH: context utilization at {pct:.1f}% (>= 100%).\n"
        "Further context loading is blocked (§economy/execution-budget.md).\n"
        "Human checkpoint required. Options:\n"
        "  1. Decompose the task into smaller PATH A/B units\n"
        "  2. Clear session context and restart\n"
        "  3. Run: sdd runtime status  (inspect workspace state)\n",
        err=True,
    )
    raise typer.Exit(_BREACH_EXIT_CODE)


def _guard_handshake(workspace_root: Path) -> None:
    """Enforce handshake requirement (M015) based on signature mode."""
    try:
        sig_mode = _signature_mode()
        cached_ahp = _get_cached_ahp()
        is_valid = (
            bool(cached_ahp.get("valid")) if isinstance(cached_ahp, dict) else None
        )
        if is_valid is None:
            from sdd_core.governance.handshake import AgentHandshakeProtocol

            ahp = AgentHandshakeProtocol(project_root=workspace_root)
            is_valid = ahp.is_handshake_valid(strict=sig_mode == "strict")
        if not is_valid:
            if sig_mode == "strict":
                typer.echo(
                    "BLOCK [ask]: Missing or incomplete handshake. "
                    "Run 'sdd governance validate' to establish a session contract first.",
                    err=True,
                )
                raise typer.Exit(3)
            else:
                if not _json_mode():
                    typer.echo(
                        "SOFT [ask]: No active handshake. "
                        "Run 'sdd governance handshake --init' to formalize your session.",
                        err=True,
                    )
    except Exception as exc:
        logger.debug("Handshake guard skipped: %s", exc)


# ---------------------------------------------------------------------------
# sdd_runtime telemetry integration
# ---------------------------------------------------------------------------


def _resolve_tokens(query: str, output_text: str) -> tuple[int | None, int | None, str]:
    return _resolve_tokens_impl(query, output_text)


def _emit_ask_telemetry(
    event_name: str,
    *,
    command: str,
    workspace_root: Path,
    trace_id: str,
    agent_id: str,
    fingerprint: str,
    context_source: str,
    mandates_count: int,
    profile: str,
    state: str,
    drift_detected: bool,
    query_hash: str = "",
    path_id: str = "",
    start_ts: str = "",
    end_ts: str = "",
    duration_ms: int | None = None,
    context_bytes_loaded: int | None = None,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    retry_count: int | None = None,
    compression_ratio: float | None = None,
    extra_details: dict[str, Any] | None = None,
) -> None:
    _emit_ask_telemetry_impl(
        event_name,
        command=command,
        workspace_root=workspace_root,
        trace_id=trace_id,
        agent_id=agent_id,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        profile=profile,
        state=state,
        drift_detected=drift_detected,
        query_hash=query_hash,
        path_id=path_id,
        start_ts=start_ts,
        end_ts=end_ts,
        duration_ms=duration_ms,
        context_bytes_loaded=context_bytes_loaded,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        retry_count=retry_count,
        compression_ratio=compression_ratio,
        extra_details=extra_details,
        logger=logger,
        telemetry_sink_cls=TelemetrySink,
        otel_bridge_cls=OtelBridge,
        otlp_exporter_cls=OtlpHttpExporter,
    )


# ---------------------------------------------------------------------------
# sdd_runtime session integration
# ---------------------------------------------------------------------------


def _upsert_ask_session(
    workspace_root: Path,
    agent_id: str,
    work_item_id: str,
    artifact_fingerprint: str,
) -> None:
    _upsert_ask_session_impl(
        workspace_root=workspace_root,
        agent_id=agent_id,
        work_item_id=work_item_id,
        artifact_fingerprint=artifact_fingerprint,
        logger=logger,
    )


# ---------------------------------------------------------------------------
# Dossier builder (C1)
# ---------------------------------------------------------------------------


def _handle_dossier_error(exc: Exception) -> None:
    _handle_dossier_error_impl(
        exc,
        logger=logger,
        typer_module=typer,
    )


def _build_and_output_dossier(
    query: str,
    skill: str | None,
    budget: int | None,
    mandates_count: int,
    workspace_root: Path | None = None,
) -> None:
    _build_and_output_dossier_impl(
        query=query,
        skill=skill,
        budget=budget,
        mandates_count=mandates_count,
        workspace_root=workspace_root,
        resolve_workspace_root_fn=_resolve_workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
        logger=logger,
        typer_module=typer,
    )


def _resolve_dossier_budget(budget: int | None) -> int:
    return _resolve_dossier_budget_impl(budget)


def _load_dossier_artifact(workspace_root: Path) -> Any | None:
    artifact = _load_dossier_artifact_impl(
        workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
    )
    if artifact is None:
        compiled_path = compiled_active_dir(workspace_root) / "governance-core.json"
        logger.debug("Could not load artifact from %s", compiled_path)
    return artifact


def _build_dossier_lines(
    query: str,
    skill: str | None,
    budget: int,
    mandates_count: int,
    budget_utilization_pct: float,
    context_result: Any,
) -> list[str]:
    return _build_dossier_lines_impl(
        query=query,
        skill=skill,
        budget=budget,
        mandates_count=mandates_count,
        budget_utilization_pct=budget_utilization_pct,
        context_result=context_result,
    )


# ---------------------------------------------------------------------------
# sdd ask — helpers
# ---------------------------------------------------------------------------


def _run_organize_intake(
    workspace_root: Path, query: str
) -> tuple[bool, str, str, int, str]:
    """Run sdd-organize intake and return (used, reason, artifact_path, chunks, retrieval)."""
    organize_used, organize_reason = _should_use_organize(query)
    organize_artifact_path = ""
    organize_chunks = 0
    organize_retrieval = "indexed_only"
    if organize_used:
        try:
            organize_artifact, organize_path = run_sdd_organize(
                workspace_root=workspace_root,
                query=query,
                source_text=query,
                route_reason=organize_reason,
            )
            organize_artifact_path = str(organize_path)
            organize_chunks = len(organize_artifact.get("chunks", []))
            organize_retrieval = str(
                organize_artifact.get("retrieval_policy", "indexed_only")
            )
        except Exception as exc:
            logger.debug("sdd-organize failed in ask: %s", exc)
            organize_retrieval = "degraded"
    return (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
    )


def _emit_state_warnings(state: str) -> None:
    if _json_mode():
        return
    if state in ("NOT_INITIALIZED", "MISCONFIGURED"):
        typer.echo(
            f"SOFT [ask]: workspace {state}. Run 'sdd governance compile' before using ask.",
            err=True,
        )
    elif state == "PARTIAL":
        typer.echo(
            "SOFT [ask]: workspace PARTIAL — compiled governance may be stale. "
            "Next: 'sdd governance compile'",
            err=True,
        )


def build_governed_ask_snapshot(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
    workspace_root: Path | None = None,
    require_handshake: bool = True,
) -> dict[str, Any]:
    """Build a governed ask snapshot with envelope + learning context."""
    root = workspace_root or _resolve_workspace_root()
    if require_handshake:
        _guard_handshake(root)
    (
        context_source,
        fingerprint,
        mandates_count,
        authenticated,
        degraded,
        degrade_reason,
        trust_source,
    ) = _load_compiled_governance(root)
    if _signature_mode() == "strict" and not authenticated:
        raise PermissionError(degrade_reason)
    drift_detected = _runtime_drift_check(root, fingerprint)
    learning_signals = _collect_learning_signals(workspace_root=root)
    return {
        "workspace_root": root,
        "context_source": context_source,
        "fingerprint": fingerprint,
        "mandates_count": mandates_count,
        "authenticated": authenticated,
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "trust_source": trust_source,
        "drift_detected": drift_detected,
        "learning_signals": learning_signals,
    }


# ---------------------------------------------------------------------------
# sdd ask
# ---------------------------------------------------------------------------


@app.command("ask")
def _ask_cli_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    dossier: bool = typer.Option(
        False, "--dossier", help="Build comprehensive task dossier with analysis."
    ),
    skill: str | None = typer.Option(  # noqa: UP045
        None, "--skill", help="Skill context (e.g., 'diagnose', 'optimize')."
    ),
    budget: int | None = typer.Option(  # noqa: UP045
        None, "--budget", help="Token budget ceiling for this query."
    ),
    full: bool = typer.Option(
        False, "--full", help="Emit detailed steps and full telemetry payload."
    ),
    log_path: str | None = typer.Option(  # noqa: UP045
        None, "--log-path", help="Custom compliance log path."
    ),
    log_format: str = typer.Option(
        "jsonl", "--log-format", help="Log format: jsonl or compact."
    ),
    tokens_input: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-input",
        help="LLM API input tokens (overrides SDD_TOKENS_INPUT).",
    ),
    tokens_output: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-output",
        help="LLM API output tokens (overrides SDD_TOKENS_OUTPUT).",
    ),
) -> None:
    """Query SDD governance context — minimal governed output."""
    token = _JSON_MODE_OVERRIDE.set(is_json_mode(ctx))
    try:
        ask_cmd(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )
    finally:
        _JSON_MODE_OVERRIDE.reset(token)


def ask_cmd(
    query: str,
    dossier: bool = False,
    skill: str | None = None,
    budget: int | None = None,
    full: bool = False,
    log_path: str | None = None,
    log_format: str = "jsonl",
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    *,
    output_json: bool | None = None,
) -> None:
    """Query SDD governance context — minimal governed output."""
    token = _JSON_MODE_OVERRIDE.set(output_json) if output_json is not None else None
    try:
        _ask_cmd_impl(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )
    finally:
        if token is not None:
            _JSON_MODE_OVERRIDE.reset(token)


def _normalize_ask_inputs(
    *,
    query: str,
    dossier: bool,
    skill: str | None,
    budget: int | None,
    full: bool,
    log_path: str | None,
    log_format: str,
    tokens_input: int | None,
    tokens_output: int | None,
) -> _AskInputs:
    skill_value = _normalize_typer_value(skill, None)
    budget_value = _normalize_typer_value(budget, None)
    log_path_value = _normalize_typer_value(log_path, None)
    log_format_value = _normalize_typer_value(log_format, "jsonl")
    tokens_input_value = _normalize_typer_value(tokens_input, None)
    tokens_output_value = _normalize_typer_value(tokens_output, None)
    return _AskInputs(
        query=query,
        dossier=bool(_normalize_typer_value(dossier, False)),
        skill=skill_value if isinstance(skill_value, str) else None,
        budget=budget_value if isinstance(budget_value, int) else None,
        full=bool(_normalize_typer_value(full, False)),
        log_path=log_path_value if isinstance(log_path_value, str) else None,
        log_format=log_format_value if isinstance(log_format_value, str) else "jsonl",
        tokens_input=(
            tokens_input_value if isinstance(tokens_input_value, int) else None
        ),
        tokens_output=(
            tokens_output_value if isinstance(tokens_output_value, int) else None
        ),
    )


def _start_ask_session(query: str) -> _AskSessionContext:
    start_mono = time.monotonic()
    start_ts = _now()
    _guard_budget_breach()
    workspace_root = _resolve_workspace_root()
    (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
    ) = _run_organize_intake(workspace_root, query)
    _guard_handshake(workspace_root)
    profile, state = _get_profile_state()
    _emit_state_warnings(state)
    return _AskSessionContext(
        workspace_root=workspace_root,
        organize_used=organize_used,
        organize_reason=organize_reason,
        organize_artifact_path=organize_artifact_path,
        organize_chunks=organize_chunks,
        organize_retrieval=organize_retrieval,
        profile=profile,
        state=state,
        agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
        trace_id=str(uuid.uuid4()),
        start_mono=start_mono,
        start_ts=start_ts,
    )


def _load_ask_snapshot(
    inputs: _AskInputs, session: _AskSessionContext
) -> dict[str, Any]:
    try:
        return build_governed_ask_snapshot(
            query=inputs.query,
            skill=inputs.skill,
            organize_used=session.organize_used,
            workspace_root=session.workspace_root,
            require_handshake=True,
        )
    except PermissionError as exc:
        typer.echo(f"BLOCK [ask]: {exc}", err=True)
        raise typer.Exit(3) from None


def _resolve_runtime_token_metrics(
    inputs: _AskInputs, output_text: str
) -> tuple[int | None, int | None, str]:
    tokens_in, tokens_out, token_source = _capture_effective_tokens_with_source(
        inputs.tokens_input, inputs.tokens_output
    )
    if tokens_in is None or tokens_out is None:
        est_in, est_out, est_source = _resolve_tokens(inputs.query, output_text)
        if tokens_in is None:
            tokens_in = est_in
        if tokens_out is None:
            tokens_out = est_out
        if token_source in {"", "unknown"}:
            token_source = est_source
    return tokens_in, tokens_out, token_source


def _sync_ask_runtime(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
) -> tuple[str, str]:
    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    authenticated = ask_snapshot["authenticated"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    learning_signals = ask_snapshot["learning_signals"]
    end_ts = _now()
    duration_ms = int((time.monotonic() - session.start_mono) * 1000)
    output_text = _render_context_output(
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )
    tokens_in, tokens_out, token_source = _resolve_runtime_token_metrics(
        inputs, output_text
    )
    path_id = os.environ.get("SDD_PATH_ID") or (
        "PATH_B" if session.organize_used else "PATH_A"
    )
    drift_type = _resolve_ask_drift_type(
        drift_detected=drift_detected, authenticated=authenticated
    )
    effective_degraded_reason = _resolve_ask_degraded_reason(
        degraded=degraded, degrade_reason=degrade_reason, authenticated=authenticated
    )
    _emit_ask_telemetry(
        "governance.ask",
        command="ask",
        workspace_root=session.workspace_root,
        trace_id=session.trace_id,
        agent_id=session.agent_id,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        profile=session.profile,
        state=session.state,
        drift_detected=drift_detected,
        query_hash=_hash_query(inputs.query),
        path_id=path_id,
        start_ts=session.start_ts,
        end_ts=end_ts,
        duration_ms=duration_ms,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        extra_details={
            "compiled_fingerprint_used": fingerprint,
            "degraded": degraded,
            "degraded_reason": effective_degraded_reason,
            "drift_type": drift_type,
            "trust_source": trust_source,
            "authenticated": authenticated,
            "intake_route": "heavy" if session.organize_used else "light",
            "intake_route_reason": session.organize_reason,
            "intake_artifact": session.organize_artifact_path,
            "intake_chunks": session.organize_chunks,
            "intake_retrieval": session.organize_retrieval,
            "token_source": token_source,
            "learning_signal_count": sum(
                value
                for key, value in learning_signals.items()
                if key not in {"observed_events", "window_days"}
            ),
            "full_mode": inputs.full,
            "log_format": inputs.log_format,
            "log_path": inputs.log_path or "default",
        },
    )
    _write_runtime_cache(
        session.workspace_root,
        {
            "ts": _now(),
            "trace_id": session.trace_id,
            "context_source": context_source,
            "compiled_fingerprint_used": fingerprint,
            "mandates_loaded": mandates_count,
            "agent_id": session.agent_id,
            "degraded": degraded,
            "degraded_reason": effective_degraded_reason,
            "trust_source": trust_source,
        },
    )
    _upsert_ask_session(session.workspace_root, session.agent_id, "ask", fingerprint)
    return output_text, _governance_footer_for_state(
        state=session.state,
        profile=session.profile,
        drift_detected=drift_detected,
    )


def _build_json_dossier_lines(
    inputs: _AskInputs, session: _AskSessionContext, mandates_count: int
) -> list[str]:
    if not inputs.dossier:
        return []
    try:
        from sdd_runtime.context import ContextLoader, ContextRequest

        dossier_budget = _resolve_dossier_budget(inputs.budget)
        budget_utilization_pct = 50.0
        artifact = _load_dossier_artifact(session.workspace_root)
        context_result = ContextLoader().load_result(
            ContextRequest(
                query=inputs.query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=budget_utilization_pct,
                prefer_full_summary=_prefer_full_summary(),
            )
        )
        return _build_dossier_lines(
            query=inputs.query,
            skill=inputs.skill,
            budget=dossier_budget,
            mandates_count=mandates_count,
            budget_utilization_pct=budget_utilization_pct,
            context_result=context_result,
        )
    except Exception as exc:
        _handle_dossier_error(exc)
        return []


def _emit_ask_json_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    governance_footer: str,
) -> None:
    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    learning_signals = ask_snapshot["learning_signals"]
    dossier_lines = _build_json_dossier_lines(inputs, session, mandates_count)
    # light_input means the query is too small to need indexing — allow it through.
    # Block only when organize was expected but did not run (non-light reason).
    _gate_blocked = (
        not session.organize_used and session.organize_reason != "light_input"
    )
    execution_gate = "blocked" if _gate_blocked else "allowed"
    gate_reason = (
        None
        if execution_gate == "allowed"
        else "intake_index_mode=none: governance context not indexed; agent must not proceed"
    )
    data = build_ask_json_data(
        profile=session.profile,
        query_hash=_hash_query(inputs.query),
        context_source=context_source,
        fingerprint=fingerprint,
        mandates_loaded=mandates_count,
        trust_source=trust_source,
        degraded=degraded,
        degraded_reason=degrade_reason,
        drift_detected=drift_detected,
        governance_footer=governance_footer,
        intake_index_mode="multi" if session.organize_used else "none",
        intake_chunks=session.organize_chunks,
        intake_retrieval=session.organize_retrieval,
        intake_artifact=session.organize_artifact_path or "n/a",
        governance_mode="hard",
        execution_gate=execution_gate,
        gate_reason=gate_reason,
        ahp_state=session.state,
        learning_signals=learning_signals,
        full=inputs.full,
        steps=[
            {
                "step_id": "PARSE",
                "ok": True,
                "ts_start": session.start_ts,
                "ts_end": _now(),
            },
            {
                "step_id": "CONTEXT_LOAD",
                "ok": True,
                "context_source": context_source,
                "fingerprint": fingerprint,
            },
        ]
        if inputs.full
        else None,
        extra={"log_format": inputs.log_format} if inputs.full else None,
    )
    if dossier_lines:
        data["dossier"] = {"lines": dossier_lines}
    emit_json(
        {
            "status": "ok",
            "command": "ask",
            "ok": True,
            "error": None,
            "data": data,
        }
    )


def _emit_ask_text_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    output_text: str,
    governance_footer: str,
) -> None:
    mandates_count = ask_snapshot["mandates_count"]
    typer.echo(output_text)
    pt_intake_mode = "multi" if session.organize_used else "none"
    _gate_blocked = (
        not session.organize_used and session.organize_reason != "light_input"
    )
    pt_gate = "blocked" if _gate_blocked else "allowed"
    pt_gate_suffix = (
        ""
        if pt_gate == "allowed"
        else "\ngate_reason       : intake_index_mode=none"
        f"\nintake_skipped    : {session.organize_reason} (query {len(inputs.query)} chars"
        " < 6000; pass ≥6000 chars or use: sdd-organize --input-file <path> <query>)"
    )
    typer.echo(
        f"intake_index_mode : {pt_intake_mode}\n"
        f"intake_chunks     : {session.organize_chunks}\n"
        f"intake_retrieval  : {session.organize_retrieval}\n"
        f"intake_artifact   : {session.organize_artifact_path or 'n/a'}\n"
        f"governance_mode   : hard\n"
        f"execution_gate    : {pt_gate}"
        f"{pt_gate_suffix}"
    )
    if inputs.dossier:
        _build_and_output_dossier(
            query=inputs.query,
            skill=inputs.skill,
            budget=inputs.budget,
            mandates_count=mandates_count,
            workspace_root=session.workspace_root,
        )
    typer.echo(governance_footer)


def _ask_cmd_impl(
    *,
    query: str,
    dossier: bool,
    skill: str | None,
    budget: int | None,
    full: bool,
    log_path: str | None,
    log_format: str,
    tokens_input: int | None,
    tokens_output: int | None,
) -> None:
    inputs = _normalize_ask_inputs(
        query=query,
        dossier=dossier,
        skill=skill,
        budget=budget,
        full=full,
        log_path=log_path,
        log_format=log_format,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
    )
    session = _start_ask_session(inputs.query)
    ask_snapshot = _load_ask_snapshot(inputs, session)
    output_text, governance_footer = _sync_ask_runtime(inputs, session, ask_snapshot)
    if _json_mode():
        _emit_ask_json_response(inputs, session, ask_snapshot, governance_footer)
        return
    _emit_ask_text_response(
        inputs, session, ask_snapshot, output_text, governance_footer
    )


def _capture_effective_tokens(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None]:
    """Capture token counts from CLI flags or environment variables.

    Backward-compatible public helper that returns only token counts.
    """
    effective_tokens_input, effective_tokens_output, _ = (
        _capture_effective_tokens_with_source(tokens_input, tokens_output)
    )
    return effective_tokens_input, effective_tokens_output


def _capture_effective_tokens_with_source(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None, str]:
    """Capture token counts and source from CLI flags or environment variables."""
    from sdd_runtime.llm import SimulatedTokenCapture

    effective_tokens_input = tokens_input
    effective_tokens_output = tokens_output
    token_source = (
        "cli" if tokens_input is not None or tokens_output is not None else ""
    )
    if effective_tokens_input is None or effective_tokens_output is None:
        captured = SimulatedTokenCapture().capture_from_env()
        if captured:
            if effective_tokens_input is None:
                effective_tokens_input = captured.tokens_input
            if effective_tokens_output is None:
                effective_tokens_output = captured.tokens_output
            token_source = token_source or "env"
    return effective_tokens_input, effective_tokens_output, token_source or "unknown"


def _check_budget_zone_and_compress(
    query: str, estimated_context_bytes: int, mandates_count: int
) -> tuple[int, float | None]:
    """Check budget zone and attempt compression if in YELLOW zone."""
    compression_ratio: float | None = None
    path_id = os.environ.get("SDD_PATH_ID", "")
    result_bytes = estimated_context_bytes

    try:
        from sdd_runtime.telemetry import _PATH_BUDGET_BYTES

        if path_id in _PATH_BUDGET_BYTES:
            budget_bytes = _PATH_BUDGET_BYTES[path_id]
            utilization_pct = (estimated_context_bytes / budget_bytes) * 100
            if 70.0 <= utilization_pct < 100.0:
                try:
                    from sdd_runtime.context import ContextLoader, ContextRequest

                    loader = ContextLoader()
                    cr = ContextRequest(
                        query=query,
                        max_items=mandates_count,
                        budget_utilization_pct=utilization_pct,
                        prefer_full_summary=_prefer_full_summary(),
                    )
                    result = loader.load_result(cr)
                    if result.compression_ratio is not None:
                        compression_ratio = result.compression_ratio
                        result_bytes = result.bytes_loaded
                except Exception as exc:
                    logger.debug("Compression attempt at YELLOW zone failed: %s", exc)
    except Exception as exc:
        logger.debug("Budget zone check failed: %s", exc)

    return result_bytes, compression_ratio
