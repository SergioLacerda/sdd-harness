"""sdd ask / sdd ask-full — governed context query commands.

``sdd ask``       — minimal, governed query against compiled SDD context.
``sdd ask-full``  — full microtransaction telemetry variant with per-step tracing.

Security:
  - Query text is NEVER logged; only sha256[:8] hash is recorded.
  - trace_id is uuid4 local-only; no external correlation.
  - Compliance JSONL is append-only at .sdd/runtime/compliance-events.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click
import typer
from sdd_runtime import OtelBridge, TelemetrySink
from sdd_runtime.otel import OtlpHttpExporter
from typer.models import OptionInfo

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
from sdd_cli.services.ask_governance import (
    GovResult as _GovResult,
)
from sdd_cli.services.ask_governance import (
    fingerprint_file as _fingerprint_file_impl,
)
from sdd_cli.services.ask_governance import (
    load_compiled_governance as _load_compiled_governance_impl,
)
from sdd_cli.services.ask_governance import (
    load_governance_via_runtime as _load_governance_via_runtime,
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
    build_ask_success_payload,
    derive_non_actionable_reason,
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
    profile_active_path,
)
from sdd_cli.utils.sdd_authority import (
    resolve_workspace_root as resolve_authority_workspace_root,
)

__all__ = [
    "app",
    "ask_cmd",
    "ask_full_cmd",
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
_LEARNING_POLICY_VERSION = "ask-learning-v1"
_LEARNING_WINDOW_DAYS = 7
_ASK_MIN_DIAGNOSIS_CONFIDENCE = 0.80
_ASK_ENVELOPE_TTL_MINUTES = 30
_ASK_SCOPE_MODE_DEFAULT = "inferred"
_TRUE_VALUES = {"1", "true", "yes", "on"}


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


def _load_compiled_governance(
    workspace_root: Path,
) -> _GovResult:
    return _load_compiled_governance_impl(
        workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
        logger=logger,
        load_via_runtime_fn=_load_governance_via_runtime,
    )


def _fingerprint_file(path: Path) -> str:
    return _fingerprint_file_impl(path)


def _resolve_workspace_root() -> Path:
    root = resolve_authority_workspace_root()
    return enforce_path_policy(root, workspace_root=root, mode="normal")


def _get_profile_state() -> tuple[str, str]:
    """Return (profile, state) best-effort; never raises."""
    workspace_root = _resolve_workspace_root()
    profile = ""
    profile_path = profile_active_path(workspace_root)
    if profile_path.exists():
        try:
            import configparser

            parser = configparser.ConfigParser()
            parser.read(profile_path)
            profile = parser.get("sdd", "type", fallback="").strip()
        except Exception:
            profile = ""
    try:
        from sdd_core.governance.handshake import AgentHandshakeProtocol

        ahp = AgentHandshakeProtocol(project_root=workspace_root)
        state, _ = ahp.validate(output_mode="silent")
        return profile or "default", state
    except Exception:
        return profile or "default", "UNKNOWN"


def _write_runtime_cache(workspace_root: Path, last_ask: dict[str, Any]) -> None:
    """Update last_ask block in governance-state.json."""
    try:
        state_path = workspace_root / ".sdd" / "runtime" / "governance-state.json"
        data: dict[str, Any] = {}
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["last_ask"] = last_ask
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        logger.debug("Failed to update runtime cache: %s", exc)


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
    """Return True if the loaded governance fingerprint differs from the cached state.

    Compares the first 8 chars of the fingerprint used to load governance
    against the first 8 chars of ``spec_fingerprint`` in governance-state.json.
    Returns False (no drift) when the state file is absent or has no fingerprint.
    """
    if not loaded_fingerprint:
        return False
    try:
        state_path = workspace_root / ".sdd" / "runtime" / "governance-state.json"
        if not state_path.exists():
            return False
        data = json.loads(state_path.read_text(encoding="utf-8"))
        cached_fp = str(data.get("spec_fingerprint", "")).strip()
        if not cached_fp:
            return False
        return loaded_fingerprint[:8] != cached_fp[:8]
    except Exception:
        return False


def _render_context_output(
    query: str,
    context_source: str,
    fingerprint: str,
    mandates_count: int,
    *,
    degraded: bool,
    degrade_reason: str,
    trust_source: str,
) -> str:
    """Build plain-text governed context block for the query."""
    if degraded:
        status_line = (
            "\u26a0 Governance loaded in DEGRADED mode (untrusted context). "
            "Run `sdd governance validate` to investigate."
        )
    else:
        status_line = (
            "Governance is active. Respond in compliance with loaded mandates."
        )
    lines = [
        "=== SDD Governance Context ===",
        f"query_hash      : {_hash_query(query)}",
        f"context_source  : {context_source}",
        f"fingerprint     : {fingerprint or 'n/a'}",
        f"mandates_loaded : {mandates_count}",
        f"trust_source    : {trust_source}",
        f"degraded        : {'yes' if degraded else 'no'}",
        "",
        status_line,
        "Run `sdd governance validate` to confirm workspace state.",
    ]
    if degrade_reason:
        lines.append(f"degraded_reason : {degrade_reason}")
    return "\n".join(lines)


def _governance_footer_for_state(
    *,
    state: str,
    profile: str,
    drift_detected: bool,
) -> str:
    from sdd_runtime import format_governance_footer

    governance = "ok" if state in {"HEALTHY", "PARTIAL"} else "warn"
    drift = "detected" if drift_detected else "none"
    return format_governance_footer(
        drift=drift,
        governance=governance,
        profile=profile or "default",
    )


def _json_mode() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _safe_parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except Exception:  # nosec B112
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _load_recent_jsonl_rows(path: Path, *, cutoff_ts: float) -> list[dict[str, Any]]:
    """Load JSONL rows newest-first until cutoff_ts, avoiding full-file scans."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for raw in reversed(lines):
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except Exception:  # nosec B112
            continue
        if not isinstance(parsed, dict):
            continue
        ts = _safe_parse_iso(str(parsed.get("timestamp", "")))
        if ts is None:
            continue
        if ts.timestamp() < cutoff_ts:
            break
        rows.append(parsed)
    rows.reverse()
    return rows


def _build_learning_recommendation(
    *,
    workspace_root: Path,
    drift_detected: bool,
    window_days: int = _LEARNING_WINDOW_DAYS,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    runtime_dir = workspace_root / ".sdd" / "runtime"
    cutoff = datetime.now(timezone.utc).timestamp() - (window_days * 24 * 3600)
    recent_failures = _load_recent_jsonl_rows(
        runtime_dir / "failure-ledger.jsonl", cutoff_ts=cutoff
    )
    recent_event_rows = _load_recent_jsonl_rows(
        runtime_dir / "compliance-events.jsonl", cutoff_ts=cutoff
    )

    diagnosis_inconclusive = sum(
        1
        for row in recent_failures
        if str(row.get("root_cause", "")) == "diagnosis.inconclusive"
    )
    evidence_insufficient = sum(
        1
        for row in recent_failures
        if str(row.get("root_cause", "")) == "evidence.insufficient"
    )
    scope_violation = sum(
        1
        for row in recent_failures
        if str(row.get("root_cause", "")) == "scope.violation"
    )

    recent_fail_or_warn_events = sum(
        1
        for row in recent_event_rows
        if str(row.get("status", "")).lower() in {"warn", "fail", "error"}
    )

    signals: list[str] = []
    reason_codes: list[str] = []
    if diagnosis_inconclusive >= 2:
        signals.append("diagnosis_inconclusive_recurrent")
        reason_codes.append("diagnosis.inconclusive.recurrent")
    if evidence_insufficient >= 2:
        signals.append("evidence_insufficient_recurrent")
        reason_codes.append("evidence.insufficient.recurrent")
    if scope_violation >= 2:
        signals.append("scope_violation_recurrent")
        reason_codes.append("scope.violation.recurrent")
    if drift_detected and recent_fail_or_warn_events >= 1:
        signals.append("drift_recurrent")
        reason_codes.append("drift.recurrent.failure_recent")

    context = {
        "window_days": window_days,
        "observed_events": len(recent_failures) + len(recent_event_rows),
        "recommendation_policy_version": _LEARNING_POLICY_VERSION,
    }
    if not signals:
        return None, context

    confidence = min(1.0, len(signals) / 3.0)
    recommendation = {
        "enabled": True,
        "confidence": round(confidence, 4),
        "signals": signals,
        "reason_codes": reason_codes,
        "next_actions": [
            "sdd skills learning-candidates",
            f"sdd skills learning-status --window-days {window_days}",
            'sdd skills learning-approve <candidate-id> --rationale "..."',
            'sdd skills learning-reject <candidate-id> --rationale "..."',
        ],
        "requires_human_review": True,
    }
    return recommendation, context


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
        from sdd_core.governance.handshake import AgentHandshakeProtocol

        ahp = AgentHandshakeProtocol(project_root=workspace_root)
        sig_mode = _signature_mode()
        if not ahp.is_handshake_valid(strict=sig_mode == "strict"):
            if sig_mode == "strict":
                typer.echo(
                    "BLOCK [ask]: Missing or incomplete handshake. "
                    "Run 'sdd governance validate' to establish a session contract first.",
                    err=True,
                )
                raise typer.Exit(3)
            else:
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


def _infer_allowed_paths_from_query(query: str) -> list[str]:
    explicit_matches = re.findall(
        r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", query.strip()
    )
    normalized: list[str] = []
    for match in explicit_matches:
        candidate = match.strip().strip("`\"'")
        if not candidate:
            continue
        if "." in Path(candidate).name:
            candidate = str(Path(candidate).parent)
        if candidate and not candidate.endswith("/"):
            candidate = f"{candidate}/"
        if candidate and candidate not in normalized and candidate != "./":
            normalized.append(candidate)
    if normalized:
        return normalized

    q = query.lower()
    inferred: list[str] = []
    keyword_map = [
        ("runtime", "packages/core/sdd_runtime/src/"),
        ("cli", "packages/interfaces/sdd_cli/src/"),
        ("compiler", "packages/core/sdd_compiler/src/"),
        ("wizard", "packages/interfaces/sdd_wizard/src/"),
        ("docs", "docs/"),
        ("test", "tests/"),
        ("governance", ".sdd/"),
    ]
    for key, path in keyword_map:
        if key in q and path not in inferred:
            inferred.append(path)
    return inferred


def _extract_explicit_allowed_paths(query: str) -> list[str]:
    explicit_matches = re.findall(
        r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", query.strip()
    )
    normalized: list[str] = []
    for match in explicit_matches:
        candidate = match.strip().strip("`\"'")
        if not candidate:
            continue
        if "." in Path(candidate).name:
            candidate = str(Path(candidate).parent)
        if candidate and not candidate.endswith("/"):
            candidate = f"{candidate}/"
        if candidate and candidate not in normalized and candidate != "./":
            normalized.append(candidate)
    return normalized


def _resolve_envelope_scope_mode() -> str:
    mode = (
        os.environ.get("SDD_ENVELOPE_SCOPE_MODE", _ASK_SCOPE_MODE_DEFAULT)
        .strip()
        .lower()
    )
    if mode not in {"inferred", "explicit_only"}:
        return _ASK_SCOPE_MODE_DEFAULT
    return mode


def _build_ask_decision_envelope(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
) -> dict[str, Any]:
    issued_at = datetime.now(timezone.utc)
    task_type = "diagnostic" if organize_used else "analysis"
    if skill:
        task_type = skill
    scope_mode = _resolve_envelope_scope_mode()
    allowed_paths = _infer_allowed_paths_from_query(query)
    if scope_mode == "explicit_only":
        allowed_paths = _extract_explicit_allowed_paths(query)
    return {
        "task_id": f"task-{uuid.uuid4().hex[:12]}",
        "task_type": task_type,
        "goal": query.strip() or "unspecified",
        "allowed_paths": allowed_paths,
        "forbidden_paths": [],
        "allowed_tools": [
            "sdd ask",
            "sdd skills run sdd-diagnose",
            "sdd skills run sdd-correct",
        ],
        "validation_set": ["sdd governance validate", "sdd runtime status --force"],
        "rollback_hint": "manual_rollback",
        "requires_diagnosis": True,
        "envelope_scope_mode": scope_mode,
        "min_diagnosis_confidence": _ASK_MIN_DIAGNOSIS_CONFIDENCE,
        "issued_at": issued_at.isoformat(),
        "expires_at": (
            issued_at + timedelta(minutes=_ASK_ENVELOPE_TTL_MINUTES)
        ).isoformat(),
    }


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
    learning_recommendation, learning_context = _build_learning_recommendation(
        workspace_root=root,
        drift_detected=drift_detected,
    )
    ask_decision_envelope = _build_ask_decision_envelope(
        query=query,
        skill=skill,
        organize_used=organize_used,
    )
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
        "learning_recommendation": learning_recommendation,
        "learning_context": learning_context,
        "ask_decision_envelope": ask_decision_envelope,
    }


# ---------------------------------------------------------------------------
# sdd ask
# ---------------------------------------------------------------------------


@app.command("ask")
def ask_cmd(
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    dossier: bool = typer.Option(
        False, "--dossier", help="Build comprehensive task dossier with analysis."
    ),
    skill: str | None = typer.Option(
        None, "--skill", help="Skill context (e.g., 'diagnose', 'optimize')."
    ),
    budget: int | None = typer.Option(
        None, "--budget", help="Token budget ceiling for this query."
    ),
) -> None:
    """Query SDD governance context — minimal governed output."""
    dossier = bool(_normalize_typer_value(dossier, False))
    skill = _normalize_typer_value(skill, None)
    if not isinstance(skill, str):
        skill = None
    budget = _normalize_typer_value(budget, None)
    if not isinstance(budget, int):
        budget = None

    _start_mono = time.monotonic()
    _start_ts = _now()
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
    agent_id = os.environ.get("SDD_AGENT_ID", "unknown")
    trace_id = str(uuid.uuid4())
    _emit_state_warnings(state)

    try:
        ask_snapshot = build_governed_ask_snapshot(
            query=query,
            skill=skill,
            organize_used=organize_used,
            workspace_root=workspace_root,
            require_handshake=True,
        )
    except PermissionError as exc:
        typer.echo(f"BLOCK [ask]: {exc}", err=True)
        raise typer.Exit(3) from None
    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    authenticated = ask_snapshot["authenticated"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    learning_recommendation = ask_snapshot["learning_recommendation"]
    learning_context = ask_snapshot["learning_context"]
    ask_decision_envelope = ask_snapshot["ask_decision_envelope"]

    # ── sdd_runtime: emit typed RuntimeEvent to canonical JSONL sink ──────
    _end_ts = _now()
    _duration_ms = int((time.monotonic() - _start_mono) * 1000)
    _output_text = _render_context_output(
        query,
        context_source,
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
        trust_source=trust_source,
    )
    _tokens_in, _tokens_out, _token_source = _resolve_tokens(query, _output_text)
    _path_id = os.environ.get("SDD_PATH_ID") or (
        "PATH_B" if organize_used else "PATH_A"
    )
    _drift_type = _resolve_ask_drift_type(
        drift_detected=drift_detected, authenticated=authenticated
    )
    _effective_degraded_reason = _resolve_ask_degraded_reason(
        degraded=degraded, degrade_reason=degrade_reason, authenticated=authenticated
    )
    _emit_ask_telemetry(
        "governance.ask",
        command="ask",
        workspace_root=workspace_root,
        trace_id=trace_id,
        agent_id=agent_id,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        profile=profile,
        state=state,
        drift_detected=drift_detected,
        query_hash=_hash_query(query),
        path_id=_path_id,
        start_ts=_start_ts,
        end_ts=_end_ts,
        duration_ms=_duration_ms,
        tokens_input=_tokens_in,
        tokens_output=_tokens_out,
        extra_details={
            "compiled_fingerprint_used": fingerprint,
            "degraded": degraded,
            "degraded_reason": _effective_degraded_reason,
            "drift_type": _drift_type,
            "trust_source": trust_source,
            "authenticated": authenticated,
            "intake_route": "heavy" if organize_used else "light",
            "intake_route_reason": organize_reason,
            "intake_artifact": organize_artifact_path,
            "intake_chunks": organize_chunks,
            "intake_retrieval": organize_retrieval,
            "token_source": _token_source,
            "learning_recommendation_emitted": learning_recommendation is not None,
            "learning_signal_count": len(learning_recommendation["signals"])
            if learning_recommendation
            else 0,
        },
    )

    # Update last_ask in runtime cache
    _write_runtime_cache(
        workspace_root,
        {
            "ts": _now(),
            "trace_id": trace_id,
            "context_source": context_source,
            "compiled_fingerprint_used": fingerprint,
            "mandates_loaded": mandates_count,
            "agent_id": agent_id,
            "degraded": degraded,
            "degraded_reason": _effective_degraded_reason,
            "trust_source": trust_source,
        },
    )

    # ── sdd_runtime: upsert canonical session state ───────────────────────
    _upsert_ask_session(workspace_root, agent_id, "ask", fingerprint)

    governance_footer = _governance_footer_for_state(
        state=state,
        profile=profile,
        drift_detected=drift_detected,
    )
    if _json_mode():
        dossier_lines: list[str] = []
        if dossier:
            try:
                from sdd_runtime.context import ContextLoader, ContextRequest

                dossier_budget = _resolve_dossier_budget(budget)
                budget_utilization_pct = 50.0
                artifact = _load_dossier_artifact(workspace_root)
                context_result = ContextLoader().load_result(
                    ContextRequest(
                        query=query,
                        artifact=artifact,
                        max_items=mandates_count,
                        budget_utilization_pct=budget_utilization_pct,
                        prefer_full_summary=_prefer_full_summary(),
                    )
                )
                dossier_lines = _build_dossier_lines(
                    query=query,
                    skill=skill,
                    budget=dossier_budget,
                    mandates_count=mandates_count,
                    budget_utilization_pct=budget_utilization_pct,
                    context_result=context_result,
                )
            except Exception as exc:
                _handle_dossier_error(exc)
        data: dict[str, Any] = build_ask_json_data(
            profile=profile,
            query_hash=_hash_query(query),
            context_source=context_source,
            fingerprint=fingerprint,
            mandates_loaded=mandates_count,
            trust_source=trust_source,
            degraded=degraded,
            degraded_reason=degrade_reason,
            drift_detected=drift_detected,
            governance_footer=governance_footer,
            intake_index_mode="multi" if organize_used else "none",
            intake_chunks=organize_chunks,
            intake_retrieval=organize_retrieval,
            intake_artifact=organize_artifact_path or "n/a",
        )
        payload = build_ask_success_payload(
            command="ask",
            base_data=data,
            ask_decision_envelope=ask_decision_envelope,
            learning_context=learning_context,
            learning_recommendation=learning_recommendation,
            include_empty_recommendations=False,
            dossier_lines=dossier_lines,
        )
        emit_json(payload)
        return

    typer.echo(
        _render_context_output(
            query,
            context_source,
            fingerprint,
            mandates_count,
            degraded=degraded,
            degrade_reason=degrade_reason,
            trust_source=trust_source,
        )
    )
    typer.echo(
        f"intake_index_mode : {'multi' if organize_used else 'none'}\n"
        f"intake_chunks     : {organize_chunks}\n"
        f"intake_retrieval  : {organize_retrieval}\n"
        f"intake_artifact   : {organize_artifact_path or 'n/a'}"
    )

    # Build dossier if requested (C1: Dossier builder)
    if dossier:
        _build_and_output_dossier(
            query=query,
            skill=skill,
            budget=budget,
            mandates_count=mandates_count,
            workspace_root=workspace_root,
        )

    typer.echo(governance_footer)


# ---------------------------------------------------------------------------
# sdd ask-full
# ---------------------------------------------------------------------------


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


@app.command("ask-full")
def ask_full_cmd(  # noqa: C901
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    log_path: str | None = typer.Option(
        None, "--log-path", help="Custom compliance log path."
    ),
    log_format: str = typer.Option(
        "jsonl", "--log-format", help="Log format: jsonl or compact."
    ),
    tokens_input: int | None = typer.Option(
        None,
        "--tokens-input",
        help="LLM API input tokens (overrides SDD_TOKENS_INPUT).",
    ),
    tokens_output: int | None = typer.Option(
        None,
        "--tokens-output",
        help="LLM API output tokens (overrides SDD_TOKENS_OUTPUT).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        help="Emit canonical JSON envelope instead of plain-text output.",
    ),
) -> None:
    """Query SDD governance context with full microtransaction telemetry."""
    log_path = _normalize_typer_value(log_path, None)
    if not isinstance(log_path, str):
        log_path = None
    log_format = _normalize_typer_value(log_format, "jsonl")
    if not isinstance(log_format, str):
        log_format = "jsonl"
    tokens_input = _normalize_typer_value(tokens_input, None)
    if not isinstance(tokens_input, int):
        tokens_input = None
    tokens_output = _normalize_typer_value(tokens_output, None)
    if not isinstance(tokens_output, int):
        tokens_output = None
    json_output = bool(_normalize_typer_value(json_output, False))

    _guard_budget_breach()
    workspace_root = _resolve_workspace_root()
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
            logger.debug("sdd-organize failed in ask-full: %s", exc)
            organize_retrieval = "degraded"
    _guard_handshake(workspace_root)
    trace_id = str(uuid.uuid4())
    agent_id = os.environ.get("SDD_AGENT_ID", "unknown")
    steps: list[dict[str, Any]] = []

    # Capture effective tokens from CLI or env
    effective_tokens_input, effective_tokens_output, token_source = (
        _capture_effective_tokens_with_source(tokens_input, tokens_output)
    )

    def _step(step_id: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        rec: dict[str, Any] = {"step_id": step_id, "ts_start": _now()}
        if extra:
            rec.update(extra)
        return rec

    def _close(rec: dict[str, Any], ok: bool = True, **kw: Any) -> dict[str, Any]:
        rec["ts_end"] = _now()
        rec["ok"] = ok
        rec.update(kw)
        return rec

    # STEP: PARSE
    s = _step("PARSE")
    query_hash = _hash_query(query)
    steps.append(_close(s))

    # STEP: CONTEXT_LOAD
    s = _step("CONTEXT_LOAD")
    (
        context_source,
        fingerprint,
        mandates_count,
        authenticated,
        degraded,
        degrade_reason,
        trust_source,
    ) = _load_compiled_governance(workspace_root)
    if _signature_mode() == "strict" and not authenticated:
        typer.echo(f"BLOCK [ask-full]: {degrade_reason}", err=True)
        raise typer.Exit(3)
    steps.append(_close(s, context_source=context_source, fingerprint=fingerprint))

    # STEP: GOV_CHECK
    s = _step("GOV_CHECK")
    profile, state = _get_profile_state()
    gate_result = (
        "PASS" if state == "HEALTHY" else ("SOFT" if state == "PARTIAL" else "BLOCK")
    )
    steps.append(_close(s, gate_result=gate_result))

    if gate_result == "BLOCK":
        typer.echo(
            f"SOFT [ask-full]: workspace {state} — cannot load governance. "
            "Run 'sdd init' then 'sdd governance compile'.",
            err=True,
        )

    # STEP: ANSWER_RENDER
    s = _step("ANSWER_RENDER")
    output_text = _render_context_output(
        query,
        context_source,
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
        trust_source=trust_source,
    )
    if effective_tokens_input is None or effective_tokens_output is None:
        est_in, est_out, est_source = _resolve_tokens(query, output_text)
        if effective_tokens_input is None:
            effective_tokens_input = est_in
        if effective_tokens_output is None:
            effective_tokens_output = est_out
        if token_source in {"", "unknown"}:
            token_source = est_source
    steps.append(_close(s, model_confidence=None))

    # STEP: OUTPUT_WRITE
    s = _step("OUTPUT_WRITE")
    drift_detected = _runtime_drift_check(workspace_root, fingerprint)
    governance_footer = _governance_footer_for_state(
        state=state,
        profile=profile,
        drift_detected=drift_detected,
    )
    if not (json_output or _json_mode()):
        typer.echo(output_text)
        typer.echo(
            f"intake_index_mode : {'multi' if organize_used else 'none'}\n"
            f"intake_chunks     : {organize_chunks}\n"
            f"intake_retrieval  : {organize_retrieval}\n"
            f"intake_artifact   : {organize_artifact_path or 'n/a'}"
        )
        typer.echo(governance_footer)
    steps.append(_close(s))

    # Determine effective log path
    effective_log: Path | None = Path(log_path) if log_path else None

    # ── Token Economy: Estimate context bytes and check budget utilization ──
    estimated_context_bytes = max(100, mandates_count * 500)
    estimated_context_bytes, compression_ratio = _check_budget_zone_and_compress(
        query, estimated_context_bytes, mandates_count
    )

    path_id = os.environ.get("SDD_PATH_ID", "")

    # ── sdd_runtime: emit typed RuntimeEvent to canonical JSONL sink ──────
    _emit_ask_telemetry(
        "governance.ask.full",
        command="ask-full",
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
        context_bytes_loaded=estimated_context_bytes,
        tokens_input=effective_tokens_input,
        tokens_output=effective_tokens_output,
        retry_count=0,  # ask-full is initial request, no retries
        compression_ratio=compression_ratio,
        extra_details={
            "compiled_fingerprint_used": fingerprint,
            "steps": steps,
            "log_path": str(effective_log) if effective_log else "default",
            "log_format": log_format,
            "gate_result": gate_result,
            "degraded": degraded,
            "degraded_reason": _resolve_ask_degraded_reason(
                degraded=degraded,
                degrade_reason=degrade_reason,
                authenticated=authenticated,
            ),
            "drift_type": _resolve_ask_drift_type(
                drift_detected=drift_detected,
                authenticated=authenticated,
            ),
            "trust_source": trust_source,
            "authenticated": authenticated,
            "token_source": token_source,
            "intake_route": "heavy" if organize_used else "light",
            "intake_route_reason": organize_reason,
            "intake_artifact": organize_artifact_path,
            "intake_chunks": organize_chunks,
            "intake_retrieval": organize_retrieval,
        },
    )

    # Update last_ask in runtime cache
    _write_runtime_cache(
        workspace_root,
        {
            "ts": _now(),
            "trace_id": trace_id,
            "context_source": context_source,
            "compiled_fingerprint_used": fingerprint,
            "mandates_loaded": mandates_count,
            "agent_id": agent_id,
            "degraded": degraded,
            "degraded_reason": _resolve_ask_degraded_reason(
                degraded=degraded,
                degrade_reason=degrade_reason,
                authenticated=authenticated,
            ),
            "trust_source": trust_source,
        },
    )

    # ── sdd_runtime: upsert canonical session state ───────────────────────
    _upsert_ask_session(workspace_root, agent_id, "ask-full", fingerprint)

    # Compact summary line if requested
    if log_format == "compact":
        compact = (
            f"ask-full|{trace_id[:8]}|{query_hash}|{context_source}|"
            f"{fingerprint}|{mandates_count}|{gate_result}"
        )
        if not (json_output or _json_mode()):
            typer.echo(compact)

    if json_output or _json_mode():
        learning_recommendation, learning_context = _build_learning_recommendation(
            workspace_root=workspace_root,
            drift_detected=drift_detected,
        )
        non_actionable, _ = derive_non_actionable_reason(learning_recommendation)
        data = build_ask_json_data(
            profile=profile,
            query_hash=query_hash,
            context_source=context_source,
            fingerprint=fingerprint,
            mandates_loaded=mandates_count,
            trust_source=trust_source,
            degraded=degraded,
            degraded_reason=degrade_reason,
            drift_detected=drift_detected,
            governance_footer=governance_footer,
            intake_index_mode="multi" if organize_used else "none",
            intake_chunks=organize_chunks,
            intake_retrieval=organize_retrieval,
            intake_artifact=organize_artifact_path or "n/a",
            extra={
                "steps": steps,
                "log_format": log_format,
                "non_actionable": non_actionable,
            },
        )
        payload = build_ask_success_payload(
            command="ask-full",
            base_data=data,
            ask_decision_envelope={},
            learning_context=learning_context,
            learning_recommendation=learning_recommendation,
            include_empty_recommendations=False,
        )
        emit_json(payload)
        return
