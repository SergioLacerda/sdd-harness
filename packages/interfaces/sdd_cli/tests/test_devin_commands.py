"""Tests for sdd devin commands (Soft/Standalone governance plugin build)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import sdd_cli.commands.devin as devin_mod

runner = CliRunner()
devin_app = devin_mod.app


def _write_minimal_registry(ws_root: Path) -> None:
    skills_dir = ws_root / ".sdd" / "skills" / "alpha"
    skills_dir.mkdir(parents=True)
    (ws_root / ".sdd" / "skills" / "registry.json").write_text(
        json.dumps({"skills": [{"name": "alpha"}]}), encoding="utf-8"
    )
    (skills_dir / "skill.yaml").write_text(
        "name: alpha\ndescription: test skill\n", encoding="utf-8"
    )


def test_devin_build_writes_plugin_bundle(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_registry(tmp_path)
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "dist" / "devin-plugin" / "AGENTS.md").exists()


def test_devin_build_reports_failure_when_no_skills(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build"])

    assert result.exit_code == 1
    assert "failed" in result.output.lower()


def test_devin_build_accepts_custom_dest(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_registry(tmp_path)
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)
    custom_dest = tmp_path / "custom-out"

    result = runner.invoke(devin_app, ["build", "--dest", str(custom_dest)])

    assert result.exit_code == 0, result.output
    assert (custom_dest / "AGENTS.md").exists()


def test_devin_build_standalone_writes_zero_sdd_config(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build", "--standalone"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".devin" / "config.json").exists()
    # Standalone mode does not require a .sdd/skills/ registry at all.
    assert not (tmp_path / "dist").exists()


def test_devin_build_standalone_refuses_on_existing_agents_md(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)
    (tmp_path / "AGENTS.md").write_text("existing", encoding="utf-8")

    result = runner.invoke(devin_app, ["build", "--standalone"])

    assert result.exit_code == 1
    assert "failed" in result.output.lower()


def test_devin_build_standalone_and_skills_are_mutually_exclusive(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build", "--standalone", "--skills"])

    assert result.exit_code == 1
    assert not (tmp_path / "AGENTS.md").exists()


def test_devin_build_standalone_and_dest_are_rejected_together(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(
        devin_app, ["build", "--standalone", "--dest", str(tmp_path / "out")]
    )

    assert result.exit_code == 1
    assert not (tmp_path / "AGENTS.md").exists()
