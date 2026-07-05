"""ask_response_json — JSON response and dossier line construction for `sdd ask`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sdd_cli.services.ask_payload import build_ask_json_data
from sdd_cli.services.ask_response import _hash_query, _now
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
        budget_utilization_pct = 50.0
        artifact = load_dossier_artifact_fn(session.workspace_root)
        context_result = ContextLoader().load_result(
            ContextRequest(
                query=inputs.query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=budget_utilization_pct,
                prefer_full_summary=prefer_full_summary_fn(),
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
    # light_input means the query is too small to need indexing — allow it through.
    # Block only when organize was expected but did not run (non-light reason).
    gate_blocked = (
        not session.organize_used and session.organize_reason != "light_input"
    )
    execution_gate = "blocked" if gate_blocked else "allowed"
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
