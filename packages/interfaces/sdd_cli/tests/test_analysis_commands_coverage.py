"""Coverage tests for analysis command branches."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sdd_cli.commands import analysis as analysis_mod
from sdd_cli.commands.analysis import app as analysis_app

runner = CliRunner()


def _write_mission(path: Path, days_ago: int = 0) -> None:
    path.write_text("# mission\n", encoding="utf-8")
    timestamp = (datetime.now(tz=timezone.utc) - timedelta(days=days_ago)).timestamp()
    os.utime(path, (timestamp, timestamp))


def _make_analysis_workspace(tmp_path: Path) -> Path:
    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".sdd" / "analysis" / state).mkdir(parents=True, exist_ok=True)
    return tmp_path


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
