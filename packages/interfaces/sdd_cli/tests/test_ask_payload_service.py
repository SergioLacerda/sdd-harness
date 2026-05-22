from __future__ import annotations

from sdd_cli.services.ask_payload import (
    build_ask_advisory_block,
    build_ask_success_payload,
)


def test_build_ask_advisory_block_omits_recommendations_by_default() -> None:
    payload = build_ask_advisory_block(
        ask_decision_envelope={"task_id": "task-1"},
        learning_context={"window_days": 7},
        learning_recommendation=None,
    )
    assert payload["ask_decision_envelope"]["task_id"] == "task-1"
    assert payload["learning_context"]["window_days"] == 7
    assert "learning_recommendations" not in payload


def test_build_ask_advisory_block_includes_empty_recommendations_when_requested() -> (
    None
):
    payload = build_ask_advisory_block(
        ask_decision_envelope={"task_id": "task-1"},
        learning_context={"window_days": 7},
        learning_recommendation=None,
        include_empty_recommendations=True,
    )
    assert "learning_recommendations" in payload
    assert payload["learning_recommendations"] is None


def test_build_ask_success_payload_sets_reason_code_when_non_actionable() -> None:
    payload = build_ask_success_payload(
        command="ask",
        base_data={"state": "ok"},
        ask_decision_envelope={"task_id": "t1"},
        learning_context={"window_days": 7},
        learning_recommendation={
            "requires_human_review": True,
            "reason_codes": ["governance.block"],
        },
    )
    assert payload["command"] == "ask"
    assert payload["data"]["non_actionable"] is True
    assert payload["data"]["reason_code"] == "governance.block"


def test_build_ask_success_payload_attaches_dossier_lines_when_present() -> None:
    payload = build_ask_success_payload(
        command="ask",
        base_data={"state": "ok"},
        ask_decision_envelope={},
        learning_context={},
        learning_recommendation=None,
        dossier_lines=["line 1", "line 2"],
    )
    assert payload["data"]["dossier"]["lines"] == ["line 1", "line 2"]
