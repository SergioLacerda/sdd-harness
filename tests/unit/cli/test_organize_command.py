from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from sdd_cli.commands._ask_backend import _should_use_organize, run_sdd_organize
from sdd_cli.main import app


@dataclass
class _FakeProfileContext:
    def as_dict(self) -> dict[str, object]:
        return {"profile": "client", "is_master": False, "is_client": True}


def _patch_profile_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_core.utils.environment.resolve_profile",
        lambda override=None: _FakeProfileContext(),
    )
    monkeypatch.setattr("sdd_cli.utils.profile.governance_gate", lambda _ctx: None)


def test_should_use_organize_heavy_by_line_count() -> None:
    payload = "\n".join(f"line {i} error test_case" for i in range(150))
    heavy, reason = _should_use_organize(payload)
    assert heavy is True
    assert reason


def test_should_use_organize_light_for_small_input() -> None:
    heavy, reason = _should_use_organize("small input")
    assert heavy is False
    assert reason == "light_input"


def test_run_sdd_organize_writes_multi_index_artifact(tmp_path: Path) -> None:
    text = "\n".join(
        [
            "test_auth_flow failed",
            "Traceback (most recent call last):",
            "File app/service.py, line 10",
            "ValueError: broken",
        ]
    )
    artifact, path = run_sdd_organize(
        workspace_root=tmp_path,
        query="diagnose auth failures",
        source_text=text,
        route_reason="line_count>=120",
    )
    assert path.exists()
    assert artifact["intake_index_mode"] == "multi"
    assert artifact["retrieval_policy"] == "indexed_only"
    assert "index_by_error_signature" in artifact["indexes"]
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["chunks"]


def test_organize_command_exposed_and_emits_json(monkeypatch, tmp_path: Path) -> None:
    _patch_profile_gate(monkeypatch)
    monkeypatch.setattr(
        "sdd_cli.commands.organize._resolve_workspace_root", lambda: tmp_path
    )
    result = CliRunner().invoke(app, ["organize", "sample error"])
    assert result.exit_code == 0, result.output
    assert "sdd-organize completed" in result.output
    artifact_line = next(
        line for line in result.output.splitlines() if line.startswith("artifact_path")
    )
    artifact_path = artifact_line.split(":", 1)[1].strip()
    assert Path(artifact_path).exists()
