from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from sdd_runtime._skill_executor import CorrectHandler, _evaluate_correction_gate

# ---------------------------------------------------------------------------
# _evaluate_correction_gate unit tests
# ---------------------------------------------------------------------------


def _ctx(
    *,
    evidence: list = (),
    confidence: float = 0.9,
    allowed: list = ("safe/",),
    planned: list = (),
) -> dict:
    task_id = "task-1"
    return {
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": list(evidence),
            "confidence": confidence,
        },
        "execution_contract": {"allowed_paths": list(allowed), "task_id": task_id},
        "diagnosis_attestation": {
            "task_id": task_id,
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": list(evidence),
            "confidence": confidence,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": list(planned),
    }


def test_gate_escalates_when_evidence_missing() -> None:
    result = _evaluate_correction_gate(_ctx(evidence=[]), active_rules=[])
    assert result["decision"] == "escalate"
    assert result["reason_code"] == "evidence.insufficient"


def test_gate_escalates_when_confidence_too_low() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.5), active_rules=[]
    )
    assert result["decision"] == "escalate"
    assert result["reason_code"] == "diagnosis.inconclusive"


def test_gate_denies_when_no_allowed_paths() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9, allowed=[]), active_rules=[]
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "contract.missing_or_invalid"


def test_gate_denies_on_scope_violation() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["unsafe/"]),
        active_rules=[],
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "scope.violation"


def test_gate_denies_when_matching_active_rule() -> None:
    active_rules = [{"pattern": "h|r", "status": "active"}]
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9), active_rules=active_rules
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "rule.blocked"


def test_gate_allows_valid_context() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["safe/"]),
        active_rules=[],
    )
    assert result["decision"] == "allow"
    assert result["reason_code"] == "ok"


def test_gate_escalates_when_attestation_missing() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx.pop("diagnosis_attestation")
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "escalate"
    assert result["reason_code"] == "diagnosis.missing"


def test_gate_denies_when_attestation_stale() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx["diagnosis_attestation"]["expires_at"] = "2000-01-01T00:00:00+00:00"
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "deny"
    assert result["reason_code"] == "diagnosis.stale"


def test_gate_denies_when_contract_stale() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx["execution_contract"]["expires_at"] = "2000-01-01T00:00:00+00:00"
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "deny"
    assert result["reason_code"] == "contract.missing_or_invalid"


def test_gate_denies_when_freeze_mode_active() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx["freeze_mode_state"] = {"enabled": True}
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "deny"
    assert result["reason_code"] == "convergence.freeze_mode_active"


# ---------------------------------------------------------------------------
# CorrectHandler.pre_run
# ---------------------------------------------------------------------------


def _make_learning(active_rules: list | None = None) -> MagicMock:
    m = MagicMock()
    m.list_active_rules.return_value = active_rules or []
    return m


def _make_skill(name: str = "sdd-correct") -> SimpleNamespace:
    return SimpleNamespace(name=name, cli_fallback=["sdd governance validate"])


def test_pre_run_returns_gate_decision_artifact() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["safe/"])
    outcome = handler.pre_run(
        ctx,
        learning=_make_learning(),
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert "gate_decision" in outcome.artifacts
    assert outcome.artifacts["gate_decision"]["decision"] == "allow"
    assert outcome.early_result is None


def test_pre_run_escalates_on_inconclusive_diagnosis() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.2)
    learning = _make_learning()
    outcome = handler.pre_run(
        ctx,
        learning=learning,
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert outcome.early_result is not None
    assert outcome.early_result.policy_result == "escalated"
    learning.append_failure.assert_called_once()


def test_pre_run_denies_scope_violation() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["unsafe/"])
    learning = _make_learning()
    outcome = handler.pre_run(
        ctx,
        learning=learning,
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert outcome.early_result is not None
    assert outcome.early_result.policy_result == "denied"
    learning.append_failure.assert_called_once()


def test_pre_run_uses_footer_fn_for_early_result() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=[], confidence=0.9)
    calls: list[tuple[str, str]] = []

    def footer(drift: str, governance: str) -> str:
        calls.append((drift, governance))
        return "FOOTER"

    outcome = handler.pre_run(
        ctx,
        learning=_make_learning(),
        skill=_make_skill(),
        profile="default",
        footer_fn=footer,
    )
    assert outcome.early_result is not None
    assert outcome.early_result.governance_footer == "FOOTER"
    assert calls == [("fallback_cli", "fail")]


# ---------------------------------------------------------------------------
# CorrectHandler.post_run
# ---------------------------------------------------------------------------


def test_post_run_appends_failure_and_returns_candidates() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9)
    learning = _make_learning()
    candidate = SimpleNamespace(pattern="h|r")
    learning.generate_candidates_from_ledger.return_value = [candidate]

    result = handler.post_run(ctx, learning=learning, exit_code=0, artifacts={})
    learning.append_failure.assert_called_once()
    assert result["rule_candidates"] == [{"pattern": "h|r"}]


def test_post_run_marks_regression_when_exit_code_nonzero() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9)
    learning = _make_learning()
    learning.generate_candidates_from_ledger.return_value = []

    handler.post_run(ctx, learning=learning, exit_code=1, artifacts={})
    call_args = learning.append_failure.call_args[0][0]
    assert call_args.regression is True


def test_post_run_returns_empty_when_diagnosis_report_is_not_dict() -> None:
    handler = CorrectHandler()
    result = handler.post_run(
        {"diagnosis_report": "bad_value"},
        learning=_make_learning(),
        exit_code=0,
        artifacts={},
    )
    assert result == {}
