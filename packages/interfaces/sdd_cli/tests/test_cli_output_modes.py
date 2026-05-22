from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sdd_cli.main import app
from sdd_cli.services.runtime_preflight import PreflightResult

runner = CliRunner()


class _FakeReport:
    confidence = 87.5
    status = "ok"


class _FakeAHP:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root
        self.skill_profile = "default"

    def validate(
        self, output_mode: str, force_recheck: bool = False
    ) -> tuple[str, _FakeReport]:
        return "HEALTHY", _FakeReport()

    def format_combined_output(self, state: str, report: _FakeReport, mode: str) -> str:
        return f"{state}:{mode}:{report.confidence}"

    def is_handshake_valid(self) -> bool:
        return True


def _parse_result_json(output: str) -> dict:
    """Parse JSON output allowing CI preamble/noise before canonical envelope."""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def _parse_json_output(result) -> dict:
    """Parse structured CLI output robustly when non-JSON lines are present.

    CI can occasionally include advisory lines before the JSON envelope.
    We parse the last non-empty line as JSON when direct parse fails.
    """
    raw = result.output or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        lines = [line for line in raw.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def test_root_json_flag_sets_structured_runtime_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_core.utils.environment.find_workspace_root", lambda: Path(".")
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.runtime._emit_runtime_status",
        lambda **_: {"detected": False, "type": "none", "reason": ""},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.runtime._show_ask_confidence",
        lambda workspace_root, emit=True: {"last_ask_ts": "now"},
    )

    result = runner.invoke(app, ["--json", "runtime", "status"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["state"] == "HEALTHY"
    assert payload["data"]["exit_code"] == 0
    assert payload["data"]["drift"]["detected"] is False
    assert payload["data"]["governance_footer"].startswith("SDD GOVERNANCE:")


def test_governance_validate_json_bypasses_rich_tables(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands.governance.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.load_governance_config",
        lambda _: {"core_fingerprint": "a", "client_fingerprint": "b"},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_files_accessible", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_fingerprints_valid", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_no_conflicts", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.run_runtime_preflight",
        lambda _: PreflightResult(passed=True, reason="", details={"skipped": False}),
    )
    with patch("sdd_cli.commands.governance.Table") as mocked_table:
        result = runner.invoke(app, ["--json", "governance", "validate"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["preflight"]["passed"] is True
    mocked_table.assert_not_called()


def test_global_verbose_is_accepted_on_runtime_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_core.utils.environment.find_workspace_root", lambda: Path(".")
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.runtime._emit_runtime_status",
        lambda **_: {"detected": False, "type": "none", "reason": ""},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.runtime._show_ask_confidence",
        lambda workspace_root, emit=True: None,
    )

    result = runner.invoke(app, ["--verbose", "runtime", "status"])

    assert result.exit_code == 0, result.output
    assert "HEALTHY:verbose" in result.output
    assert "SDD GOVERNANCE: drift=none" in result.output


def test_governance_load_json_uses_canonical_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands.governance.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.load_governance_config",
        lambda _: {"core_fingerprint": "a"},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.get_governance_summary",
        lambda _path, config=None: {"items": 1},
    )
    result = runner.invoke(app, ["--json", "governance", "load"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["summary"]["items"] == 1


def test_governance_load_json_error_uses_canonical_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands.governance.validate_governance_path", lambda _: False
    )
    result = runner.invoke(app, ["--json", "governance", "load"])

    assert result.exit_code == 1, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_governance_path"
    assert isinstance(payload["data"], dict)


def test_governance_generate_json_uses_canonical_envelope(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands.governance.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.load_governance_config",
        lambda _: {"items": [{"id": "M001"}]},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._resolve_output_base",
        lambda _output_dir: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._generate_seeds",
        lambda output_dir, config: ([("copilot", tmp_path / "a.md", "ok")], tmp_path),
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._run_generate_phases",
        lambda output_base, config: (True, True, True),
    )
    result = runner.invoke(app, ["--json", "governance", "generate"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["command"] == "governance generate"


def test_governance_generate_json_error_uses_canonical_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands.governance.validate_governance_path", lambda _: False
    )
    result = runner.invoke(app, ["--json", "governance", "generate"])

    assert result.exit_code == 1, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_governance_path"
    assert isinstance(payload["data"], dict)


def test_governance_compile_json_uses_canonical_envelope(monkeypatch) -> None:
    mock_result = {
        "full_pipeline_success": True,
        "phase_1": {
            "core_fingerprint": "a" * 64,
            "core_item_count": 2,
            "client_item_count": 1,
        },
        "phase_2": {
            "core_msgpack_file": "/out/core.msgpack",
            "client_msgpack_file": "/out/client.msgpack",
        },
    }
    monkeypatch.setattr(
        "sdd_cli.commands.governance._run_compilation",
        lambda profile=None: mock_result,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._update_profile_hash",
        lambda core_fingerprint: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._resolve_generate_path",
        lambda path: "runtime/compiled",
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_artifact_consistency",
        lambda path: (True, "ok"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._regenerate_seeds",
        lambda: None,
    )
    result = runner.invoke(app, ["--json", "governance", "compile"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["summary"]["core_items"] == 2


def test_governance_compile_json_error_uses_canonical_envelope(monkeypatch) -> None:
    mock_result = {
        "full_pipeline_success": True,
        "phase_1": {"core_fingerprint": "a" * 64},
        "phase_2": {},
    }
    monkeypatch.setattr(
        "sdd_cli.commands.governance._run_compilation",
        lambda profile=None: mock_result,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._update_profile_hash",
        lambda core_fingerprint: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._resolve_generate_path",
        lambda path: "runtime/compiled",
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_artifact_consistency",
        lambda path: (False, "bad metadata"),
    )
    result = runner.invoke(app, ["--json", "governance", "compile"])

    assert result.exit_code == 1, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "artifact_consistency_failed"
    assert isinstance(payload["data"], dict)


def test_ask_full_json_output_uses_canonical_envelope(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._should_use_organize",
        lambda query: (False, "light"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._guard_handshake",
        lambda workspace_root: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._load_compiled_governance",
        lambda workspace_root: ("compiled", "fp-1", 1, True, False, "", "verified"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._signature_mode",
        lambda: "warn",
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._runtime_drift_check",
        lambda workspace_root, fingerprint: False,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._build_learning_recommendation",
        lambda workspace_root, drift_detected: (
            {
                "requires_human_review": True,
                "reason_codes": ["diagnosis.inconclusive.recurrent"],
            },
            {},
        ),
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["ask-full", "--json-output", "status?"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["command"] == "ask-full"
    assert payload["data"]["non_actionable"] is True
    assert payload["data"]["reason_code"] == "diagnosis.inconclusive.recurrent"


def test_ask_full_global_json_flag_uses_canonical_envelope(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._should_use_organize",
        lambda query: (False, "light"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._guard_handshake",
        lambda workspace_root: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._load_compiled_governance",
        lambda workspace_root: ("compiled", "fp-1", 1, True, False, "", "verified"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._signature_mode",
        lambda: "warn",
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._runtime_drift_check",
        lambda workspace_root, fingerprint: False,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._build_learning_recommendation",
        lambda workspace_root, drift_detected: (None, {}),
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask-full", "status?"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["command"] == "ask-full"
    assert payload["data"]["non_actionable"] is False


def test_runtime_status_json_uses_canonical_data_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "sdd_core.utils.environment.find_workspace_root", lambda: Path(".")
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.runtime._emit_runtime_status",
        lambda **_: {"detected": False, "type": "none", "reason": ""},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.runtime._show_ask_confidence",
        lambda workspace_root, emit=True: {"last_ask_ts": "now"},
    )

    result = runner.invoke(app, ["--json", "runtime", "status"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["data"]["state"] == "HEALTHY"
    assert "state" not in payload


def test_governance_validate_json_uses_canonical_data_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands.governance.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.load_governance_config",
        lambda _: {"core_fingerprint": "a", "client_fingerprint": "b"},
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_files_accessible", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_fingerprints_valid", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_no_conflicts", lambda _: True
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance._check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.governance.run_runtime_preflight",
        lambda _: PreflightResult(passed=True, reason="", details={"skipped": False}),
    )
    result = runner.invoke(app, ["--json", "governance", "validate"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["data"]["exit_code"] == 0
    assert "exit_code" not in payload


def test_ask_full_json_uses_canonical_data_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._should_use_organize",
        lambda query: (False, "light"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._guard_handshake",
        lambda workspace_root: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._load_compiled_governance",
        lambda workspace_root: ("compiled", "fp-1", 1, True, False, "", "verified"),
    )
    monkeypatch.setattr("sdd_cli.commands._ask_backend._signature_mode", lambda: "warn")
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._runtime_drift_check",
        lambda workspace_root, fingerprint: False,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "sdd_cli.commands._ask_backend._build_learning_recommendation",
        lambda workspace_root, drift_detected: (None, {}),
    )
    monkeypatch.setattr(
        "sdd_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask-full", "status?"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["data"]["policy_result"] == "governance_context_loaded"
    assert "policy_result" not in payload


def test_governance_audit_json_uses_canonical_envelope(monkeypatch) -> None:
    class _Issue:
        severity = "LOW"
        category = "config"
        message = "ok"
        remediation = "none"

    class _Report:
        ok = True
        score = 95
        issues = [_Issue()]
        metadata = {"runtime": "ok"}

    class _Auditor:
        def perform_audit(self):
            return _Report()

    monkeypatch.setattr("sdd_core.governance.audit.GovernanceAuditor", _Auditor)
    result = runner.invoke(app, ["--json", "governance", "audit"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance audit"
    assert payload["ok"] is True
    assert payload["data"]["score"] == 95


def test_governance_handshake_init_json_uses_canonical_envelope(monkeypatch) -> None:
    class _Challenge:
        def to_dict(self):
            return {"session_id": "sess-1", "signature_status": "verified"}

    class _AHP:
        def generate_challenge(self, task_description: str):
            return _Challenge()

    monkeypatch.setattr("sdd_core.governance.handshake.AgentHandshakeProtocol", _AHP)
    result = runner.invoke(app, ["--json", "governance", "handshake", "--init"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance handshake"
    assert payload["ok"] is True
    assert payload["data"]["session_id"] == "sess-1"


def test_governance_handshake_response_json_uses_canonical_envelope(
    monkeypatch,
) -> None:
    class _Result:
        agent_id = "agent-1"
        timestamp = "2026-05-21T10:00:00Z"
        skills_to_use = ["sdd-ask"]

    class _AHP:
        def validate(self, output_mode: str = "silent"):
            return ("HEALTHY", None)

        def complete_handshake(self, response_data):
            return _Result()

    monkeypatch.setattr("sdd_core.governance.handshake.AgentHandshakeProtocol", _AHP)
    result = runner.invoke(
        app,
        [
            "--json",
            "governance",
            "handshake",
            "--response",
            '{"ack":true}',
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance handshake"
    assert payload["ok"] is True
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["agent_id"] == "agent-1"


def test_governance_handshake_response_json_uses_canonical_data_payload(
    monkeypatch,
) -> None:
    class _Result:
        agent_id = "agent-1"
        timestamp = "2026-05-21T10:00:00Z"
        skills_to_use = ["sdd-ask"]

    class _AHP:
        def validate(self, output_mode: str = "silent"):
            return ("HEALTHY", None)

        def complete_handshake(self, response_data):
            return _Result()

    monkeypatch.setattr("sdd_core.governance.handshake.AgentHandshakeProtocol", _AHP)
    result = runner.invoke(
        app,
        [
            "--json",
            "governance",
            "handshake",
            "--response",
            '{"ack":true}',
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance handshake"
    assert payload["ok"] is True
    assert payload["data"]["agent_id"] == "agent-1"
    assert "agent_id" not in payload
