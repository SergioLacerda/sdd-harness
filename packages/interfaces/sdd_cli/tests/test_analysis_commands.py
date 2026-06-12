"""Tests for sdd analysis commands (M017 — Analysis Plugin Compliance)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sdd_cli.commands.analysis import app as analysis_app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analysis_workspace(tmp_path: Path) -> Path:
    """Create a workspace with .sdd/analysis/ state dirs and sample missions."""
    import yaml  # type: ignore[import-untyped]  # noqa: F401

    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".sdd" / "analysis" / state).mkdir(parents=True)

    (
        tmp_path / ".sdd" / "analysis" / "pending" / "mission-2026-06-01-001.md"
    ).write_text("# Mission", encoding="utf-8")
    (tmp_path / ".sdd" / "plugins" / "registry.yaml").write_text(
        "schema_version: '1.0.0'\nplugins: []\n", encoding="utf-8"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# 6.3 sdd analysis list — empty workspace returns no error
# ---------------------------------------------------------------------------


def test_analysis_list_empty_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sdd analysis list returns empty list with no error when workspace has no missions."""
    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".sdd" / "analysis" / state).mkdir(parents=True)

    from sdd_cli.commands import analysis as analysis_mod

    monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(analysis_app, ["list"])
    assert result.exit_code == 0
    assert "No analysis missions found." in result.output


# ---------------------------------------------------------------------------
# 6.5 sdd-ask delegation triggers on analysis intent keywords
# ---------------------------------------------------------------------------


def test_sdd_ask_delegation_policy_has_triggers() -> None:
    """sdd-ask skill has delegation_policy with analysis mission triggers."""
    from sdd_runtime.skills import _REGISTRY

    skill = _REGISTRY.get("sdd-ask")
    assert skill is not None
    assert skill.delegation_policy is not None
    assert skill.delegation_policy.get("enabled") is True
    triggers = skill.delegation_policy.get("triggers", [])
    assert len(triggers) > 0
    assert any("plan" in t.lower() for t in triggers)


# ---------------------------------------------------------------------------
# 6.6 non-analysis request is not delegated (routing unchanged)
# ---------------------------------------------------------------------------


def test_sdd_ask_delegation_policy_has_delegate_to() -> None:
    """sdd-ask delegation_policy.delegate_to is analysis_orchestrator."""
    from sdd_runtime.skills import _REGISTRY

    skill = _REGISTRY["sdd-ask"]
    assert skill.delegation_policy is not None
    assert skill.delegation_policy.get("delegate_to") == "analysis_orchestrator"
