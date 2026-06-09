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


def test_organize_accepts_input_file_after_query_argument(
    monkeypatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / ".sdd" / "runtime" / "organized.json"
    input_file = tmp_path / "context.txt"
    input_text = "traceback\nerror\nfull file content"
    input_file.write_text(input_text, encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    def _capture_run(**kwargs: object) -> tuple[dict[str, object], Path]:
        captured_kwargs.update(kwargs)
        return (
            {"chunks": [{"id": 1}], "retrieval_policy": "indexed_only"},
            artifact_path,
        )

    monkeypatch.setattr(
        "sdd_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "sdd_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr("sdd_cli.commands.organize.run_sdd_organize", _capture_run)

    result = runner.invoke(
        app,
        ["organize", "short query", "--input-file", str(input_file)],
    )

    assert result.exit_code == 0, result.output
    assert captured_kwargs["query"] == "short query"
    assert captured_kwargs["source_text"] == input_text
    assert "artifact_path" in result.output
