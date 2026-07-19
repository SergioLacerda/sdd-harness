"""sdd ask — runtime telemetry sync and command implementation."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from sdd_cli.commands._ask_backend._pipeline_runtime_support import (
    build_runtime_details,
    emit_ask_response,
    normalize_ask_inputs,
)
from sdd_cli.services.ask_response import (
    emit_ask_intake_only_text_response as _emit_ask_intake_only_text_response,
)
from sdd_cli.services.ask_response import (
    emit_ask_text_response as _emit_ask_text_response,
)
from sdd_cli.services.ask_response_json import (
    emit_ask_intake_only_json_response as _emit_ask_intake_only_json_response,
)
from sdd_cli.services.ask_response_json import (
    emit_ask_json_response as _emit_ask_json_response,
)
from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext

from ._helpers import (
    _hash_query,
    _json_mode,
    _normalize_typer_value,
    _now,
    _prefer_full_summary,
    _render_context_output,
    _resolve_ask_degraded_reason,
    _resolve_ask_drift_type,
)
from ._phase_timer import PhaseTimer
from ._pipeline_metrics import _resolve_runtime_token_metrics
from ._pipeline_session import _load_ask_snapshot, _start_ask_session
from ._telemetry import (
    _build_and_output_dossier,
    _handle_dossier_error,
    _resolve_dossier_budget,
)

logger = logging.getLogger(__name__)


def _maybe_record_llm_exchange_phase(timer: PhaseTimer) -> None:
    """Record `ask.external.llm_exchange` only when adapter-reported.

    Reads the optional `SDD_ADAPTER_LLM_EXCHANGE_MS` env var, the minimal
    viable channel for an IDE/adapter to report externally-observed LLM
    exchange latency that `sdd_cli` cannot measure locally. If unset or not
    a valid non-negative integer, no phase is recorded — never fabricate a
    `0ms` measurement.
    """
    raw = os.environ.get("SDD_ADAPTER_LLM_EXCHANGE_MS", "").strip()
    if not raw:
        return
    try:
        duration_ms = int(raw)
    except ValueError:
        return
    if duration_ms < 0:
        return
    timer.record_external(
        "ask.external.llm_exchange",
        latency_domain="external_llm",
        duration_ms=duration_ms,
        measurement_quality="adapter_reported",
        observed_by="adapter",
    )


def _sync_ask_runtime(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
) -> tuple[str, str, int]:
    from sdd_cli.commands import _ask_backend as _backend

    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    authenticated = ask_snapshot["authenticated"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    root_seed_drift_detected = ask_snapshot["root_seed_drift_detected"]
    learning_signals = ask_snapshot["learning_signals"]
    handbook_lookup = ask_snapshot.get("handbook_lookup")
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
    parent_event = _backend._emit_ask_telemetry(
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
        extra_details=build_runtime_details(
            fingerprint=fingerprint,
            degraded=degraded,
            degraded_reason=effective_degraded_reason,
            drift_type=drift_type,
            trust_source=trust_source,
            authenticated=authenticated,
            session=session,
            token_source=token_source,
            learning_signals=learning_signals,
            inputs=inputs,
            handbook_lookup=handbook_lookup
            if isinstance(handbook_lookup, dict)
            else None,
        ),
    )
    parent_span_id = getattr(parent_event, "span_id", "") or ""
    _maybe_record_llm_exchange_phase(session.phase_timer)
    for record in session.phase_timer.records():
        _backend._emit_ask_telemetry(
            "governance.ask.phase",
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
            path_id=path_id,
            start_ts=record.start_ts,
            end_ts=record.end_ts,
            duration_ms=record.duration_ms,
            parent_event_id=parent_span_id,
            extra_details={
                "phase_id": record.phase_id,
                "latency_domain": record.latency_domain,
                "measurement_quality": record.measurement_quality,
                "observed_by": record.observed_by,
                "failed": record.failed,
                # Phase events inherit drift_detected from the parent
                # invocation; without the classification they surface as
                # missing_drift_type rows in audit drift tables.
                "drift_type": drift_type,
            },
        )
    _backend._write_runtime_cache(
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
    _backend._upsert_ask_session(
        session.workspace_root, session.agent_id, "ask", fingerprint
    )
    return (
        output_text,
        _backend._governance_footer_for_state(
            state=session.state,
            profile=session.profile,
            drift_detected=drift_detected,
            root_seed_drift_detected=root_seed_drift_detected,
        ),
        duration_ms,
    )


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
    intake_only: bool = False,
) -> None:
    inputs = normalize_ask_inputs(
        query=query,
        dossier=dossier,
        skill=skill,
        budget=budget,
        full=full,
        log_path=log_path,
        log_format=log_format,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        normalize_value_fn=_normalize_typer_value,
    )
    from sdd_cli.commands import _ask_backend as _backend

    session = _start_ask_session(inputs.query)
    if intake_only:
        # Cheap hook-mode profile (spike: 20260714-sdd-ask-single-entrypoint-
        # spike, I-005). Deliberately skips build_governed_ask_snapshot
        # (compiled-governance load, signature verification, drift checks,
        # handbook lookup) and telemetry/runtime-cache writes — those are the
        # stages the spike identified as unnecessary for every hook-fired
        # prompt. Full `sdd ask` behavior (no --intake-only) is unchanged.
        if _json_mode():
            _emit_ask_intake_only_json_response(inputs, session)
        else:
            _emit_ask_intake_only_text_response(inputs, session)
        return
    ask_snapshot = _load_ask_snapshot(inputs, session)
    output_text, governance_footer, duration_ms = _sync_ask_runtime(
        inputs, session, ask_snapshot
    )
    emit_ask_response(
        inputs=inputs,
        session=session,
        ask_snapshot=ask_snapshot,
        output_text=output_text,
        governance_footer=governance_footer,
        duration_ms=duration_ms,
        json_mode_fn=_json_mode,
        emit_json_response_fn=_emit_ask_json_response,
        emit_text_response_fn=_emit_ask_text_response,
        resolve_dossier_budget_fn=_resolve_dossier_budget,
        load_dossier_artifact_fn=_backend._load_dossier_artifact,
        build_dossier_lines_fn=_backend._build_dossier_lines,
        handle_dossier_error_fn=_handle_dossier_error,
        prefer_full_summary_fn=_prefer_full_summary,
        build_and_output_dossier_fn=_build_and_output_dossier,
    )
