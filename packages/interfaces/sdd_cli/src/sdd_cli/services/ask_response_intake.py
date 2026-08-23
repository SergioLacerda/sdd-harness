"""ask_response_intake — structured intake/intent classification for `sdd ask`.

Split out of `ask_response.py`/`ask_response_json.py` (T4,
`.analysis/pending/2026-06-15-sdd-cli-refactoring-pending-followup.md`): these
are the intake-classification helpers shared by both the text and JSON
response paths, plus the JSON-path intake-only responder that depends on them.
"""

from __future__ import annotations

import os
from typing import Any

from sdd_cli.services.ask_hash import _hash_query
from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext
from sdd_cli.utils.output import emit_json

# Env var set by the prompt-submit hook when it invokes `sdd ask` on the
# agent's behalf. Any other invocation path (direct CLI use, or the slash
# command adapter's own `sdd ask` call) is a deliberate/explicit invocation.
ASK_ENTRYPOINT_ENV = "SDD_ASK_ENTRYPOINT"


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
