"""Coverage tests for analysis and doctor command branches."""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

import sdd_core.governance.compliance as compliance_mod
import sdd_core.governance.handshake as handshake_mod
import sdd_core.governance.scoring as scoring_mod
import sdd_core.utils.environment as env_mod
from sdd_cli.commands import analysis as analysis_mod
from sdd_cli.commands import doctor as doctor_mod
from sdd_cli.commands.analysis import app as analysis_app
from sdd_cli.commands.doctor import app as doctor_app

runner = CliRunner()


def _write_mission(path: Path, days_ago: int = 0) -> None:
    path.write_text("# mission\n", encoding="utf-8")
    timestamp = (datetime.now(tz=timezone.utc) - timedelta(days=days_ago)).timestamp()
    os.utime(path, (timestamp, timestamp))


def _make_analysis_workspace(tmp_path: Path) -> Path:
    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".sdd" / "analysis" / state).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _fake_doctor_integration_engine(report_score: int = 100):
    class _FakeReport:
        def pretty(self) -> str:
            return "pretty-report"

        def score(self) -> int:
            return report_score

    class _FakeEngine:
        def __init__(
            self, spec: str, context_overrides: dict[str, object] | None = None
        ):
            self.spec = spec
            self.context_overrides = context_overrides

        def run(self) -> _FakeReport:
            return _FakeReport()

    return _FakeEngine


def _install_fake_integration_engine(
    monkeypatch: pytest.MonkeyPatch, engine_cls: type[object]
) -> None:
    root_mod = types.ModuleType("sdd_integration")
    engine_pkg = types.ModuleType("sdd_integration.engine")
    engine_mod = types.ModuleType("sdd_integration.engine.integration_engine")
    engine_mod.IntegrationEngine = engine_cls
    root_mod.engine = engine_pkg
    engine_pkg.integration_engine = engine_mod
    monkeypatch.setitem(sys.modules, "sdd_integration", root_mod)
    monkeypatch.setitem(sys.modules, "sdd_integration.engine", engine_pkg)
    monkeypatch.setitem(
        sys.modules, "sdd_integration.engine.integration_engine", engine_mod
    )


class TestAnalysisHelpers:
    def test_parse_duration_variants(self) -> None:
        assert analysis_mod._parse_duration("2d") == timedelta(days=2)
        assert analysis_mod._parse_duration("3h") == timedelta(hours=3)
        assert analysis_mod._parse_duration("4m") == timedelta(minutes=4)
        assert analysis_mod._parse_duration("nope") is None

    def test_analysis_root_builds_expected_path(self, tmp_path: Path) -> None:
        assert analysis_mod._analysis_root(tmp_path) == tmp_path / ".sdd" / "analysis"

    def test_collect_missions_skips_non_markdown_and_missing_dirs(
        self, tmp_path: Path
    ) -> None:
        analysis_root = _make_analysis_workspace(tmp_path) / ".sdd" / "analysis"
        _write_mission(analysis_root / "pending" / "mission-a.md", days_ago=1)
        (analysis_root / "pending" / "ignore.txt").write_text("x", encoding="utf-8")

        missions = analysis_mod._collect_missions(analysis_root)

        assert [item["mission_id"] for item in missions["pending"]] == ["mission-a"]
        assert missions["todo"] == []
        assert missions["refined"] == []

    def test_collect_missions_with_missing_state_dir(self, tmp_path: Path) -> None:
        analysis_root = tmp_path / ".sdd" / "analysis"
        (analysis_root / "todo").mkdir(parents=True, exist_ok=True)
        _write_mission(analysis_root / "todo" / "mission-a.md")

        missions = analysis_mod._collect_missions(analysis_root)

        assert missions["todo"]
        assert missions["pending"] == []
        assert missions["refined"] == []
        assert missions["done"] == []

    def test_collect_expired_handles_missing_dir(self, tmp_path: Path) -> None:
        cutoff = datetime.now(tz=timezone.utc)
        assert (
            analysis_mod._collect_expired(tmp_path / "done", cutoff, dry_run=True) == []
        )

    def test_collect_expired_dry_run_and_delete(self, tmp_path: Path) -> None:
        done_dir = _make_analysis_workspace(tmp_path) / ".sdd" / "analysis" / "done"
        old_file = done_dir / "old.md"
        new_file = done_dir / "new.md"
        (done_dir / "folder").mkdir()
        _write_mission(old_file, days_ago=10)
        _write_mission(new_file, days_ago=0)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=1)

        dry_run = analysis_mod._collect_expired(done_dir, cutoff, dry_run=True)
        assert dry_run == [str(old_file)]
        assert old_file.exists()

        removed = analysis_mod._collect_expired(done_dir, cutoff, dry_run=False)
        assert removed == [str(old_file)]
        assert not old_file.exists()
        assert new_file.exists()

    def test_next_action_map_and_unknown(self) -> None:
        assert analysis_mod._next_action("todo").startswith("move to pending")
        assert analysis_mod._next_action("pending").startswith("discovery in progress")
        assert analysis_mod._next_action("refined").startswith("plan ready")
        assert analysis_mod._next_action("done") == "mission complete"
        assert analysis_mod._next_action("other") == "unknown"


class TestAnalysisCommands:
    def test_list_missions_missing_workspace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: None)
        result = runner.invoke(analysis_app, ["list"])
        assert result.exit_code != 0
        assert "workspace root not found" in result.output

    def test_list_missions_plain_and_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workspace = _make_analysis_workspace(tmp_path)
        _write_mission(workspace / ".sdd" / "analysis" / "todo" / "mission-todo.md")
        _write_mission(
            workspace / ".sdd" / "analysis" / "pending" / "mission-pending.md"
        )

        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: workspace)

        json_payloads: list[dict[str, object]] = []
        monkeypatch.setattr(analysis_mod, "emit_json", json_payloads.append)

        json_result = runner.invoke(analysis_app, ["list", "--json"])
        assert json_result.exit_code == 0
        assert json_payloads[0]["command"] == "analysis list"

        plain_result = runner.invoke(analysis_app, ["list"])
        assert plain_result.exit_code == 0
        assert "[TODO]" in plain_result.output
        assert "mission-todo" in plain_result.output

    def test_list_missions_empty_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workspace = _make_analysis_workspace(tmp_path)
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: workspace)
        result = runner.invoke(analysis_app, ["list"])
        assert result.exit_code == 0
        assert "No analysis missions found." in result.output

    def test_status_found_plain_and_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workspace = _make_analysis_workspace(tmp_path)
        mission = workspace / ".sdd" / "analysis" / "refined" / "mission-x.md"
        _write_mission(mission)
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: workspace)

        json_payloads: list[dict[str, object]] = []
        monkeypatch.setattr(analysis_mod, "emit_json", json_payloads.append)

        json_result = runner.invoke(analysis_app, ["status", "mission-x", "--json"])
        assert json_result.exit_code == 0
        assert json_payloads[0]["data"]["state"] == "refined"

        plain_result = runner.invoke(analysis_app, ["status", "mission-x"])
        assert plain_result.exit_code == 0
        assert "mission_id : mission-x" in plain_result.output
        assert "next_action: plan ready" in plain_result.output

    def test_status_missing_plain_and_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workspace = _make_analysis_workspace(tmp_path)
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: workspace)

        json_payloads: list[dict[str, object]] = []
        monkeypatch.setattr(analysis_mod, "emit_json", json_payloads.append)

        json_result = runner.invoke(analysis_app, ["status", "missing", "--json"])
        assert json_result.exit_code != 0
        assert json_payloads[0]["error"]["code"] == "mission_not_found"

        plain_result = runner.invoke(analysis_app, ["status", "missing"])
        assert plain_result.exit_code != 0
        assert "Mission 'missing' not found" in plain_result.output

    def test_clean_missing_workspace_and_invalid_duration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: None)
        missing_result = runner.invoke(analysis_app, ["clean"])
        assert missing_result.exit_code != 0

        workspace = _make_analysis_workspace(tmp_path)
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: workspace)
        invalid_result = runner.invoke(analysis_app, ["clean", "--older-than", "bad"])
        assert invalid_result.exit_code != 0
        assert "invalid duration" in invalid_result.output

    def test_clean_plain_json_and_delete(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workspace = _make_analysis_workspace(tmp_path)
        done_dir = workspace / ".sdd" / "analysis" / "done"
        old_file = done_dir / "old.md"
        _write_mission(old_file, days_ago=10)
        monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: workspace)

        json_payloads: list[dict[str, object]] = []
        monkeypatch.setattr(analysis_mod, "emit_json", json_payloads.append)

        json_result = runner.invoke(
            analysis_app,
            ["clean", "--older-than", "1d", "--json"],
        )
        assert json_result.exit_code == 0
        assert json_payloads[0]["data"]["removed"] == 1

        _write_mission(old_file, days_ago=10)
        plain_result = runner.invoke(
            analysis_app,
            ["clean", "--older-than", "1d", "--dry-run"],
        )
        assert plain_result.exit_code == 0
        assert "mission(s) removed (dry-run)." in plain_result.output
        assert old_file.exists()

        plain_delete = runner.invoke(
            analysis_app,
            ["clean", "--older-than", "1d"],
        )
        assert plain_delete.exit_code == 0
        assert not old_file.exists()


class TestDoctorHelpers:
    def test_get_default_spec_uses_repo_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor_mod, "detect_repo_root", lambda: tmp_path)
        assert (
            doctor_mod._get_default_spec()
            .as_posix()
            .endswith(
                "packages/features/sdd_integration/src/sdd_integration/protocol/integration_flow.yaml"
            )
        )

    def test_apply_score_gate_disabled_and_policy_short_circuit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doctor_mod._apply_score_gate(0)

        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: None
        )
        doctor_mod._apply_score_gate(10)

    def test_apply_score_gate_profile_not_initialized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)
        (compiled_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": "0123456789abcdef"}),
            encoding="utf-8",
        )

        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: (_ for _ in ()).throw(
                env_mod.WorkspaceNotInitializedError("not ready")
            ),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 100)
        doctor_mod._apply_score_gate(50)

    def test_apply_score_gate_exit_and_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text(
            json.dumps({"fingerprint": "0123456789abcdef"}), encoding="utf-8"
        )

        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: SimpleNamespace(core_hash="0123456789abcdef"),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 10)

        with pytest.raises(typer.Exit):
            doctor_mod._apply_score_gate(50)

        monkeypatch.setattr(
            scoring_mod,
            "compute_governance_score",
            lambda checks: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        doctor_mod._apply_score_gate(50)

    def test_apply_score_gate_fingerprint_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)
        artifact_path = compiled_dir / "governance-core.json"
        payload = {"alpha": 1, "beta": 2}
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        expected_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:16]

        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: SimpleNamespace(core_hash=expected_hash),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 100)
        doctor_mod._apply_score_gate(50)

    def test_apply_score_gate_hash_decode_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)
        (compiled_dir / "governance-core.json").write_bytes(b"not-json")

        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: SimpleNamespace(core_hash="0123456789abcdef"),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 100)
        doctor_mod._apply_score_gate(50)

    def test_apply_adherence_gate_variants(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doctor_mod._apply_adherence_gate(0)

        monkeypatch.setattr(
            compliance_mod,
            "compute_governance_adherence",
            lambda workspace_root: {"score": 10},
        )
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: Path("/tmp"))
        with pytest.raises(typer.Exit):
            doctor_mod._apply_adherence_gate(50)

        monkeypatch.setattr(
            compliance_mod,
            "compute_governance_adherence",
            lambda workspace_root: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        doctor_mod._apply_adherence_gate(50)


class TestDoctorRun:
    def test_callback_invokes_run_without_subcommand(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(doctor_mod, "run", lambda **kwargs: None)
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        result = runner.invoke(doctor_app, [])
        assert result.exit_code == 0

    def test_run_import_error_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        real_import = builtins.__import__

        def _blocked_import(name: str, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("sdd_integration"):
                raise ImportError("blocked for test")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _blocked_import)
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        result = runner.invoke(
            doctor_app, ["run", "--spec", str(tmp_path / "spec.yaml")]
        )
        assert result.exit_code != 0
        assert "unavailable because optional dependency" in result.output

    def test_run_missing_spec_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        spec = tmp_path / "spec.yaml"
        monkeypatch.setattr(doctor_mod, "_get_default_spec", lambda: spec)
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )

        fake_engine = _fake_doctor_integration_engine(report_score=100)
        _install_fake_integration_engine(monkeypatch, fake_engine)
        result = runner.invoke(doctor_app, ["run"])

        assert result.exit_code != 0
        assert "Spec file not found" in result.output

    def test_run_real_mode_and_failure_score(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        spec = tmp_path / "spec.yaml"
        spec.write_text("spec", encoding="utf-8")
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )

        fake_engine = _fake_doctor_integration_engine(report_score=99)
        _install_fake_integration_engine(monkeypatch, fake_engine)
        monkeypatch.setattr(doctor_mod, "detect_repo_root", lambda: tmp_path)
        result = runner.invoke(
            doctor_app, ["run", "--spec", str(spec), "--mode", "real"]
        )

        assert result.exit_code != 0
        assert "Next: review failing checks above" in result.output

    def test_run_success_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        spec = tmp_path / "spec.yaml"
        spec.write_text("spec", encoding="utf-8")
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(doctor_mod, "detect_repo_root", lambda: tmp_path)

        fake_engine = _fake_doctor_integration_engine(report_score=100)
        _install_fake_integration_engine(monkeypatch, fake_engine)
        result = runner.invoke(doctor_app, ["run", "--spec", str(spec)])

        assert result.exit_code == 0
        assert "pretty-report" in result.output
