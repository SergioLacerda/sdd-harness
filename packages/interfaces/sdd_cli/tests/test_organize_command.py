from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


def test_organize_output_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / ".sdd" / "runtime" / "organized.json"
    monkeypatch.setattr(
        "sdd_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [{"id": 1}, {"id": 2}], "retrieval_policy": "indexed_only"},
            artifact_path,
        ),
    )
    result = runner.invoke(app, ["organize", "--output-json", "hello world"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "organize"
    assert payload["ok"] is True
    assert payload["data"]["intake_chunks"] == 2
    assert payload["data"]["artifact_path"] == str(artifact_path)


def test_organize_global_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / ".sdd" / "runtime" / "organized.json"
    monkeypatch.setattr(
        "sdd_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [{"id": 1}], "retrieval_policy": "indexed_only"},
            artifact_path,
        ),
    )
    result = runner.invoke(app, ["--json", "organize", "hello world"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "organize"
    assert payload["data"]["intake_chunks"] == 1


def test_organize_json_uses_canonical_data_payload(monkeypatch, tmp_path: Path) -> None:
    artifact_path = tmp_path / ".sdd" / "runtime" / "organized.json"
    monkeypatch.setattr(
        "sdd_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [{"id": 1}, {"id": 2}, {"id": 3}]},
            artifact_path,
        ),
    )
    result = runner.invoke(app, ["--json", "organize", "hello world"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "organize"
    assert payload["data"]["intake_chunks"] == 3
    assert "intake_chunks" not in payload
