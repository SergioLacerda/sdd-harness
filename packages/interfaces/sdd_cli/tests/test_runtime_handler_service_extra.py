from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from sdd_cli.services import runtime_handler as runtime_mod
from sdd_cli.services import runtime_handler_status as runtime_status_mod


def test_read_workspace_id_and_profile_from_ini(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / ".sdd" / "profile"
    profile.parent.mkdir(parents=True)
    profile.write_text("[sdd]\nworkspace_id = ws-1\ntype = client\n", encoding="utf-8")
    monkeypatch.setattr(runtime_mod, "profile_active_path", lambda root: profile)
    assert runtime_mod._read_workspace_id(tmp_path) == "ws-1"
    assert runtime_mod._read_profile(tmp_path) == "client"


def test_check_cache_staleness_and_footer_status(tmp_path: Path) -> None:
    assert runtime_status_mod._check_cache_staleness(tmp_path)["missing"] is True
    cache = tmp_path / ".sdd" / "runtime" / ".sdd-cache.md"
    cache.parent.mkdir(parents=True)
    cache.write_text("x", encoding="utf-8")
    info = runtime_status_mod._check_cache_staleness(tmp_path)
    assert info["missing"] is False
    assert (
        runtime_status_mod._footer_drift_status(
            {"detected": True, "type": "spec_drift"}
        )
        == "spec_drift"
    )
    assert (
        runtime_status_mod._footer_drift_status(
            {"detected": False, "type": "spec_drift"}
        )
        == "none"
    )


def test_normalize_report_and_show_ask_confidence(tmp_path: Path, capsys) -> None:
    report = SimpleNamespace(ok=True, other=Path("/tmp/x"))
    normalized = runtime_mod._normalize_report(report)
    assert normalized["ok"] is True
    assert normalized["other"] == "/tmp/x"

    state = tmp_path / ".sdd" / "runtime" / "governance-state.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps(
            {
                "last_ask": {
                    "ts": "now",
                    "context_source": "compiled",
                    "compiled_fingerprint_used": "fp",
                    "trace_id": "1234567890",
                }
            }
        ),
        encoding="utf-8",
    )
    payload = runtime_mod._show_ask_confidence(tmp_path)
    captured = capsys.readouterr()
    assert payload is not None
    assert payload["trace_id"] == "12345678"
    assert "ask_confidence" in captured.out


def test_emit_runtime_status_handles_missing_compiled_dir(
    monkeypatch, tmp_path: Path
) -> None:
    fake = ModuleType("sdd_runtime")
    fake.CompiledArtifact = SimpleNamespace(
        from_sdd_compiled_dir=lambda compiled_dir, profile: None
    )
    fake.DriftDetector = lambda: SimpleNamespace(classify=lambda **kwargs: None)
    fake.GovernanceInjector = lambda: SimpleNamespace(
        inject_from_path=lambda path: SimpleNamespace(
            loaded=False,
            artifact_fingerprint="fp",
            schema_version="1",
            mandates_loaded=0,
        )
    )
    fake.RuntimeEvent = lambda **kwargs: kwargs
    fake.SessionManager = lambda state_dir: SimpleNamespace(upsert=lambda session: None)
    fake.SessionState = lambda **kwargs: kwargs
    fake.TelemetrySink = lambda jsonl_path, logging_mode: SimpleNamespace(
        emit=lambda event: None
    )
    monkeypatch.setitem(sys.modules, "sdd_runtime", fake)
    monkeypatch.setattr(
        runtime_mod, "compiled_active_dir", lambda root: tmp_path / "missing"
    )
    assert (
        runtime_mod._emit_runtime_status(
            root=tmp_path,
            ahp_state="HEALTHY",
            workspace_profile="client",
            current_profile="client",
        )["type"]
        == "none"
    )


def test_emit_runtime_status_emits_drift(monkeypatch, tmp_path: Path) -> None:
    compiled = tmp_path / ".sdd" / "compiled"
    compiled.mkdir(parents=True)
    events: list[dict] = []
    emitted: list[str] = []

    class _FakeDriftReport:
        drift_detected = True
        drift_type = "spec_drift"
        remediation_command = "sdd governance compile"

    fake = ModuleType("sdd_runtime")
    fake.CompiledArtifact = SimpleNamespace(
        from_sdd_compiled_dir=lambda compiled_dir, profile: object()
    )
    fake.DriftDetector = lambda: SimpleNamespace(
        classify=lambda **kwargs: _FakeDriftReport()
    )
    fake.GovernanceInjector = lambda: SimpleNamespace(
        inject_from_path=lambda path: SimpleNamespace(
            loaded=True,
            artifact_fingerprint="fp",
            schema_version="1",
            mandates_loaded=16,
        )
    )
    fake.RuntimeEvent = lambda **kwargs: kwargs
    fake.SessionManager = lambda state_dir: SimpleNamespace(upsert=lambda session: None)
    fake.SessionState = lambda **kwargs: kwargs
    fake.TelemetrySink = lambda jsonl_path, logging_mode: SimpleNamespace(
        emit=lambda event: events.append(event)
    )
    monkeypatch.setitem(sys.modules, "sdd_runtime", fake)
    monkeypatch.setattr(runtime_mod, "compiled_active_dir", lambda root: compiled)
    monkeypatch.setattr(
        runtime_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: workspace_root / "events.jsonl",
    )
    info = runtime_mod._emit_runtime_status(
        root=tmp_path,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
        emit_fn=lambda msg: emitted.append(msg),
    )
    assert info["detected"] is True
    assert events[0]["event"] == "runtime.session.start"
    assert events[1]["event"] == "runtime.drift.detected"
    assert "spec_drift" in emitted[0]
