from __future__ import annotations

from sdd_cli.shared.contracts import build_error_result, build_ok_result


def test_build_ok_result_uses_canonical_envelope() -> None:
    payload = build_ok_result("runtime status", {"state": "HEALTHY"})
    assert payload["status"] == "ok"
    assert payload["command"] == "runtime status"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["data"]["state"] == "HEALTHY"


def test_build_error_result_uses_canonical_envelope() -> None:
    payload = build_error_result(
        "runtime status",
        {"state": "NOT_CONNECTED"},
        code="runtime_state_not_healthy",
        message="runtime unavailable",
    )
    assert payload["status"] == "error"
    assert payload["command"] == "runtime status"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "runtime_state_not_healthy"
    assert payload["error"]["message"] == "runtime unavailable"
    assert payload["data"]["state"] == "NOT_CONNECTED"
