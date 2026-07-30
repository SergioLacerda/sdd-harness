"""ask_response_json — JSON response and dossier line construction for `sdd ask`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sdd_cli.services.ask_dossier import estimate_budget_utilization_pct
from sdd_cli.services.ask_payload import build_ask_json_data
from sdd_cli.services.ask_response import (
    _hash_query,
    _looks_like_implementation_intent,
    _now,
    build_intake_contract_fields,
    resolve_execution_gate,
)
from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext
from sdd_cli.utils.output import emit_json


def build_json_dossier_lines(
    inputs: _AskInputs,
    session: _AskSessionContext,
    mandates_count: int,
    *,
    resolve_dossier_budget_fn: Callable[[int | None], int],
    load_dossier_artifact_fn: Callable[[Path], Any | None],
    build_dossier_lines_fn: Callable[..., list[str]],
    handle_dossier_error_fn: Callable[[Exception], None],
    prefer_full_summary_fn: Callable[[], bool],
) -> list[str]:
    """Build dossier lines for the JSON response, or [] if not requested."""
    if not inputs.dossier:
        return []
    try:
        from sdd_runtime.context import ContextLoader, ContextRequest

        dossier_budget = resolve_dossier_budget_fn(inputs.budget)
        artifact = load_dossier_artifact_fn(session.workspace_root)
        prefer_full_summary = prefer_full_summary_fn()
        loader = ContextLoader()
        # Probe pass at 0% utilization: measures real bytes_loaded without
        # triggering compression or breach (see ask_dossier.build_and_output_dossier
        # for the text-mode twin of this logic).
        probe_result = loader.load_result(
            ContextRequest(
                query=inputs.query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=0.0,
                prefer_full_summary=prefer_full_summary,
            )
        )
        budget_utilization_pct = estimate_budget_utilization_pct(
            probe_result.bytes_loaded, dossier_budget
        )
        context_result = loader.load_result(
            ContextRequest(
                query=inputs.query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=budget_utilization_pct,
                prefer_full_summary=prefer_full_summary,
            )
        )
        return build_dossier_lines_fn(
            query=inputs.query,
            skill=inputs.skill,
            budget=dossier_budget,
            mandates_count=mandates_count,
            budget_utilization_pct=budget_utilization_pct,
            context_result=context_result,
        )
    except Exception as exc:
        handle_dossier_error_fn(exc)
        return []


def emit_ask_json_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    governance_footer: str,
    *,
    duration_ms: int = 0,
    resolve_dossier_budget_fn: Callable[[int | None], int],
    load_dossier_artifact_fn: Callable[[Path], Any | None],
    build_dossier_lines_fn: Callable[..., list[str]],
    handle_dossier_error_fn: Callable[[Exception], None],
    prefer_full_summary_fn: Callable[[], bool],
) -> None:
    """Emit the full JSON response for `sdd ask` to stdout."""
    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    root_seed_drift_detected = ask_snapshot["root_seed_drift_detected"]
    learning_signals = ask_snapshot["learning_signals"]
    handbook_lookup = ask_snapshot.get("handbook_lookup")
    dossier_lines = build_json_dossier_lines(
        inputs,
        session,
        mandates_count,
        resolve_dossier_budget_fn=resolve_dossier_budget_fn,
        load_dossier_artifact_fn=load_dossier_artifact_fn,
        build_dossier_lines_fn=build_dossier_lines_fn,
        handle_dossier_error_fn=handle_dossier_error_fn,
        prefer_full_summary_fn=prefer_full_summary_fn,
    )
    execution_gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    gate_reason = (
        None
        if execution_gate == "allowed"
        else "intake_index_mode=none: governance context not indexed; agent must not proceed"
    )
    phase_records = session.phase_timer.records()
    timing: dict[str, Any] | None = None
    if inputs.full and phase_records:
        timing = {
            "total_ms": duration_ms,
            "phase_total_ms": session.phase_timer.phase_total_ms(),
            "unattributed_ms": session.phase_timer.unattributed_ms(
                session_duration_ms=duration_ms
            ),
            "phases": [
                {
                    "phase_id": record.phase_id,
                    "duration_ms": record.duration_ms,
                    "latency_domain": record.latency_domain,
                    "measurement_quality": record.measurement_quality,
                    "phase_slow": record.phase_slow,
                }
                for record in phase_records
            ],
        }
    implementation_intent = _looks_like_implementation_intent(inputs.query)
    intake_contract = build_intake_contract_fields(
        execution_gate=execution_gate, query=inputs.query, skill=inputs.skill
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
        root_seed_drift_detected=root_seed_drift_detected,
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
        extra={
            **intake_contract,
            **({"log_format": inputs.log_format} if inputs.full else {}),
            **({"timing": timing} if timing is not None else {}),
            **(
                {
                    "implementation_intent": {
                        "sdd_ask_contract": "governance-context query only",
                        "delegation_status": "not_executed",
                        "next_valid_path": "implementation_handoff",
                    }
                }
                if implementation_intent
                else {}
            ),
            **(
                {"runtime_handbook": handbook_lookup}
                if isinstance(handbook_lookup, dict)
                else {}
            ),
        },
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


def emit_ask_intake_only_json_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    *,
    runtime_handbook_hint: dict[str, Any] | None = None,
) -> None:
    """Cheap hook-mode JSON response: gate + structured intent only.

    Deliberately omits fingerprint, mandates_loaded, degraded/drift status,
    trust_source, and full runtime_handbook payloads — those require the full
    governance snapshot this profile exists to avoid loading (spike:
    20260714-sdd-ask-single-entrypoint-spike, A-005/I-005). A compact
    runtime_handbook_hint may be present when a runtime-only lookup finds an
    opportunistic runbook signal.
    """
    execution_gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    intake_contract = build_intake_contract_fields(
        execution_gate=execution_gate, query=inputs.query, skill=inputs.skill
    )
    data: dict[str, Any] = {
        "profile": session.profile,
        "query_hash": _hash_query(inputs.query),
        "intake_index_mode": "multi" if session.organize_used else "none",
        "intake_chunks": session.organize_chunks,
        "intake_retrieval": session.organize_retrieval,
        "intake_artifact": session.organize_artifact_path or "n/a",
        "governance_mode": "hard",
        "execution_gate": execution_gate,
        "intake_profile": "cheap",
        **intake_contract,
    }
    if runtime_handbook_hint:
        data["runtime_handbook_hint"] = runtime_handbook_hint
    emit_json(
        {
            "status": "ok",
            "command": "ask",
            "ok": True,
            "error": None,
            "data": data,
        }
    )
