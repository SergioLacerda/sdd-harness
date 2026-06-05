"""Shared payload builders for ask-derived JSON contracts."""

from __future__ import annotations

from typing import Any

from sdd_cli.shared.contracts import build_ok_result


def build_ask_json_data(
    *,
    profile: str,
    query_hash: str,
    context_source: str,
    fingerprint: str | None,
    mandates_loaded: int,
    trust_source: str,
    degraded: bool,
    degraded_reason: str,
    drift_detected: bool,
    governance_footer: str,
    intake_index_mode: str,
    intake_chunks: int,
    intake_retrieval: str,
    intake_artifact: str,
    governance_mode: str = "hard",
    execution_gate: str = "allowed",
    gate_reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build base canonical `data` payload shared by ask and ask-full."""
    payload: dict[str, Any] = {
        "state": "ok",
        "profile": profile,
        "policy_result": "governance_context_loaded",
        "reason": "governance context loaded",
        "exit_code": 0,
        "query_hash": query_hash,
        "context_source": context_source,
        "fingerprint": fingerprint or "n/a",
        "mandates_loaded": mandates_loaded,
        "trust_source": trust_source,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "drift_detected": drift_detected,
        "governance_footer": governance_footer,
        "intake_index_mode": intake_index_mode,
        "intake_chunks": intake_chunks,
        "intake_retrieval": intake_retrieval,
        "intake_artifact": intake_artifact,
        "governance_mode": governance_mode,
        "execution_gate": execution_gate,
    }
    if gate_reason is not None:
        payload["gate_reason"] = gate_reason
    if extra:
        payload.update(extra)
    return payload


def build_ask_advisory_block(
    *,
    ask_decision_envelope: dict[str, Any],
    learning_context: dict[str, Any],
    learning_recommendation: dict[str, Any] | None,
    include_empty_recommendations: bool = False,
) -> dict[str, Any]:
    """Build the canonical ask advisory block used by ask/pipeline JSON outputs."""
    payload: dict[str, Any] = {
        "ask_decision_envelope": ask_decision_envelope,
        "learning_context": learning_context,
    }
    if include_empty_recommendations or learning_recommendation is not None:
        payload["learning_recommendations"] = learning_recommendation
    return payload


def derive_non_actionable_reason(
    learning_recommendation: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    """Return (non_actionable, reason_code) for ask JSON contract."""
    if not isinstance(learning_recommendation, dict):
        return False, None
    if not bool(learning_recommendation.get("requires_human_review")):
        return False, None
    reason_codes = learning_recommendation.get("reason_codes")
    if isinstance(reason_codes, list):
        for value in reason_codes:
            if isinstance(value, str) and value.strip():
                return True, value.strip()
    return True, "unspecified_non_actionable"


def build_ask_success_payload(
    *,
    command: str,
    base_data: dict[str, Any],
    ask_decision_envelope: dict[str, Any],
    learning_context: dict[str, Any],
    learning_recommendation: dict[str, Any] | None,
    include_empty_recommendations: bool = False,
    dossier_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Build canonical success envelope for ask-family commands."""
    data = dict(base_data)
    data.update(
        build_ask_advisory_block(
            ask_decision_envelope=ask_decision_envelope,
            learning_context=learning_context,
            learning_recommendation=learning_recommendation,
            include_empty_recommendations=include_empty_recommendations,
        )
    )
    non_actionable, reason_code = derive_non_actionable_reason(learning_recommendation)
    data["non_actionable"] = non_actionable
    if non_actionable:
        data["reason_code"] = reason_code
    if dossier_lines:
        data["dossier"] = {"lines": dossier_lines}
    return build_ok_result(command, data)
