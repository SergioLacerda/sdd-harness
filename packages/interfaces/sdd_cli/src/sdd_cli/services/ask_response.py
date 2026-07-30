"""ask_response — final text response emission for `sdd ask`.

Dossier helpers are injected as callables since they are thin wrappers
owned by `commands/_ask_backend.py`.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import typer

from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext

# Env var set by the prompt-submit hook when it invokes `sdd ask` on the
# agent's behalf. Any other invocation path (direct CLI use, or the slash
# command adapter's own `sdd ask` call) is a deliberate/explicit invocation.
ASK_ENTRYPOINT_ENV = "SDD_ASK_ENTRYPOINT"


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:8]


def _looks_like_implementation_intent(query: str) -> bool:
    normalized = query.casefold()
    intent_markers = (
        "implement",
        "implementation",
        "implementar",
        "implementacao",
        "implementação",
        "apply change",
        "make the change",
        "fix this",
        "corrigir",
        "aplicar",
    )
    return any(marker in normalized for marker in intent_markers)


def classify_ask_intent(query: str, skill: str | None = None) -> str:
    """Classify the governed intake intent using the existing local heuristics.

    Mirrors the keyword categories already used for implementation-intent
    detection and handbook task-type inference, mapped onto the structured
    `intent` values shared by adapters (hook, slash command). No provider
    lookup or LLM-based classification is performed.
    """
    if _looks_like_implementation_intent(query):
        return "implementation_request"
    skill_value = (skill or "").strip().casefold()
    if skill_value == "planning":
        return "planning_request"
    if skill_value in {"diagnosis", "diagnose", "debug", "stabilize"}:
        return "analysis_request"
    query_value = query.casefold()
    if any(token in query_value for token in ("diagnos", "erro", "error", "fail")):
        return "analysis_request"
    if any(token in query_value for token in ("plan", "design", "proposal")):
        return "planning_request"
    return "governance_query"


def resolve_ask_entrypoint() -> tuple[str, str | None]:
    """Resolve (entrypoint, explicit_command) from how `sdd ask` was invoked.

    Returns ``("hook", None)`` only when the prompt-submit hook set
    ``SDD_ASK_ENTRYPOINT=hook`` before calling `sdd ask`. Every other call —
    a human typing `sdd ask` directly, or the slash-command adapter running
    its own explicit invocation — is treated as ``("explicit_command",
    "sdd-ask")``.
    """
    if os.environ.get(ASK_ENTRYPOINT_ENV, "").strip().casefold() == "hook":
        return "hook", None
    return "explicit_command", "sdd-ask"


def resolve_ask_next_action(execution_gate: str, intent: str) -> str:
    """Resolve the single next action a calling agent should take."""
    if execution_gate == "blocked":
        return "acknowledge_context"
    if intent == "implementation_request":
        return "create_execution_contract"
    return "answer_from_governance"


def resolve_execution_gate(*, organize_used: bool, organize_reason: str) -> str:
    """Resolve `execution_gate` from the organize-intake classification.

    Shared by the full and cheap (`--intake-only`) response paths so the gate
    formula lives in exactly one place.
    """
    gate_blocked = not organize_used and organize_reason != "light_input"
    return "blocked" if gate_blocked else "allowed"


def build_intake_contract_fields(
    *, execution_gate: str, query: str, skill: str | None
) -> dict[str, Any]:
    """Build the additive structured-intake fields shared by text/JSON output.

    These fields are additive to the existing `execution_gate`,
    `intake_index_mode`, and `next_valid_path` signals — they do not replace
    or rename them. `delegation_executed` and `provider_bound` are always
    `false`: no provider invocation path exists yet in `sdd ask` (see spike
    analysis A-001 Q4).
    """
    intent = classify_ask_intent(query, skill)
    entrypoint, explicit_command = resolve_ask_entrypoint()
    return {
        "intent": intent,
        "entrypoint": entrypoint,
        "explicit_command": explicit_command,
        "next_action": resolve_ask_next_action(execution_gate, intent),
        "delegation_executed": False,
        "provider_bound": False,
        "handoff_owner": "calling_agent",
        "requires_user_approval": intent == "implementation_request",
    }


def emit_ask_text_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    output_text: str,
    governance_footer: str,
    *,
    duration_ms: int = 0,
    build_and_output_dossier_fn: Callable[..., None],
) -> None:
    """Echo the plain-text response and footer for `sdd ask` to stdout."""
    mandates_count = ask_snapshot["mandates_count"]
    typer.echo(output_text)
    intake_mode = "multi" if session.organize_used else "none"
    gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    gate_suffix = (
        ""
        if gate == "allowed"
        else "\ngate_reason       : intake_index_mode=none"
        f"\nintake_skipped    : {session.organize_reason} (query {len(inputs.query)} chars"
        " < 6000; pass ≥6000 chars or use: sdd-organize --input-file <path> <query>)"
    )
    typer.echo(
        f"intake_index_mode : {intake_mode}\n"
        f"intake_chunks     : {session.organize_chunks}\n"
        f"intake_retrieval  : {session.organize_retrieval}\n"
        f"intake_artifact   : {session.organize_artifact_path or 'n/a'}\n"
        f"governance_mode   : hard\n"
        f"execution_gate    : {gate}"
        f"{gate_suffix}"
    )
    intake_contract = build_intake_contract_fields(
        execution_gate=gate, query=inputs.query, skill=inputs.skill
    )
    typer.echo(
        f"intent            : {intake_contract['intent']}\n"
        f"entrypoint        : {intake_contract['entrypoint']}\n"
        f"next_action       : {intake_contract['next_action']}"
    )
    if _looks_like_implementation_intent(inputs.query):
        typer.echo(
            "sdd ask contract  : governance-context query only\n"
            "delegation_status : not_executed\n"
            "next_valid_path   : implementation_handoff\n"
            "delegation_executed : false\n"
            "provider_bound    : false"
        )
    if inputs.dossier:
        build_and_output_dossier_fn(
            query=inputs.query,
            skill=inputs.skill,
            budget=inputs.budget,
            mandates_count=mandates_count,
            workspace_root=session.workspace_root,
        )
    typer.echo(governance_footer)
    phase_records = session.phase_timer.records()
    if inputs.full and phase_records:
        phase_timer = session.phase_timer
        typer.echo("timing:")
        typer.echo(
            f"  total_ms={duration_ms} "
            f"phase_total_ms={phase_timer.phase_total_ms()} "
            f"unattributed_ms="
            f"{phase_timer.unattributed_ms(session_duration_ms=duration_ms)}"
        )
        for record in phase_records:
            slow_marker = " SLOW" if record.phase_slow else ""
            typer.echo(
                f"  {record.phase_id}={record.duration_ms}ms "
                f"{record.latency_domain} {record.measurement_quality}{slow_marker}"
            )


def emit_ask_intake_only_text_response(
    inputs: _AskInputs, session: _AskSessionContext
) -> None:
    """Cheap hook-mode text response: gate + structured intent only.

    Deliberately omits fingerprint, mandates count, degraded/drift status,
    handbook lookup, and dossier/timing output — those require the full
    governance snapshot this profile exists to avoid loading (spike:
    20260714-sdd-ask-single-entrypoint-spike, A-005/I-005).
    """
    gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    intake_contract = build_intake_contract_fields(
        execution_gate=gate, query=inputs.query, skill=inputs.skill
    )
    typer.echo(
        f"intake_index_mode : {'multi' if session.organize_used else 'none'}\n"
        f"intake_chunks     : {session.organize_chunks}\n"
        f"intake_retrieval  : {session.organize_retrieval}\n"
        f"intake_artifact   : {session.organize_artifact_path or 'n/a'}\n"
        f"governance_mode   : hard\n"
        f"execution_gate    : {gate}\n"
        f"intake_profile    : cheap\n"
        f"intent            : {intake_contract['intent']}\n"
        f"entrypoint        : {intake_contract['entrypoint']}\n"
        f"next_action       : {intake_contract['next_action']}\n"
        f"delegation_executed : false\n"
        f"provider_bound    : false"
    )
