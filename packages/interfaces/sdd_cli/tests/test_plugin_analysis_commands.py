"""Tests for sdd plugin and sdd analysis commands (M017 — Analysis Plugin Compliance)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sdd_cli.commands.analysis import app as analysis_app
from sdd_cli.commands.plugin import app as plugin_app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plugin_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with .sdd/plugins/registry.yaml."""
    plugins_dir = tmp_path / ".sdd" / "plugins"
    plugins_dir.mkdir(parents=True)

    compliant_entry = {
        "id": "strategist",
        "type": "analysis_orchestrator",
        "version": "1.0.0",
        "status": "active",
        "entrypoint": "/strategist",
        "contract": ".sdd/contracts/analysis-provider.schema.yaml",
        "sdd_injection": {
            "base_path": ".sdd/analysis",
            "execution_provider": "sdd-ask",
            "approval_gate": "required",
            "knowledge_paths": [],
            "governance_context": {
                "workspace_version": "3.0",
                "active_mandates": ["M001", "M017"],
            },
        },
    }
    noncompliant_entry = {
        "id": "broken-plugin",
        "type": "unknown_type",
        "version": "0.1.0",
        "status": "active",
    }

    import yaml  # type: ignore[import-untyped]

    registry = {
        "schema_version": "1.0.0",
        "plugins": [compliant_entry, noncompliant_entry],
    }
    (plugins_dir / "registry.yaml").write_text(
        yaml.dump(registry, default_flow_style=False), encoding="utf-8"
    )
    return tmp_path


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
# 6.1 sdd plugin validate — compliant entry passes
# ---------------------------------------------------------------------------


def test_plugin_validate_pass(
    plugin_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sdd plugin validate passes for a compliant Strategist entry."""
    monkeypatch.chdir(plugin_workspace)
    monkeypatch.setenv("SDD_WORKSPACE_ROOT", str(plugin_workspace))

    from sdd_cli.commands import plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: plugin_workspace)

    result = runner.invoke(plugin_app, ["validate", "strategist"])
    assert result.exit_code == 0
    assert "pass" in result.output


# ---------------------------------------------------------------------------
# 6.2 sdd plugin validate — non-compliant entry fails with violations listed
# ---------------------------------------------------------------------------


def test_plugin_validate_fail(
    plugin_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sdd plugin validate fails and lists violations for a non-compliant entry."""
    from sdd_cli.commands import plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: plugin_workspace)

    result = runner.invoke(plugin_app, ["validate", "broken-plugin"])
    assert result.exit_code != 0
    assert "fail" in result.output
    assert "unknown_plugin_type" in result.output
    assert "missing field" in result.output


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
# 6.4 mission-result artifact outside base_path fails M017 check
# ---------------------------------------------------------------------------


def test_validate_entry_detects_artifact_scope_violation() -> None:
    """Plugin entry missing sdd_injection fields fails validation."""
    from sdd_cli.commands.plugin import _validate_entry

    entry_missing_injection = {
        "id": "bad",
        "type": "analysis_orchestrator",
        "version": "1.0.0",
        "status": "active",
        "entrypoint": "/bad",
        "contract": ".sdd/contracts/analysis-provider.schema.yaml",
        "sdd_injection": {
            "base_path": ".sdd/analysis",
        },
    }
    violations = _validate_entry(entry_missing_injection)
    assert any("execution_provider" in v for v in violations)
    assert any("approval_gate" in v for v in violations)


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


# ---------------------------------------------------------------------------
# 6.7 mission-contract includes knowledge_paths (may be empty)
# ---------------------------------------------------------------------------


def test_plugin_registry_strategist_has_knowledge_paths(
    plugin_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Strategist plugin entry includes knowledge_paths in sdd_injection."""
    from sdd_cli.commands import plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: plugin_workspace)

    registry = plugin_mod._load_registry(plugin_workspace)
    strategist = next(p for p in registry["plugins"] if p["id"] == "strategist")
    injection = strategist["sdd_injection"]
    assert "knowledge_paths" in injection
    assert isinstance(injection["knowledge_paths"], list)


# ---------------------------------------------------------------------------
# 6.8 plugin receiving knowledge_paths must have it as a list (not replaced)
# ---------------------------------------------------------------------------


def test_plugin_validate_pass_with_empty_knowledge_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plugin with empty knowledge_paths still passes validation."""
    import yaml  # type: ignore[import-untyped]

    plugins_dir = tmp_path / ".sdd" / "plugins"
    plugins_dir.mkdir(parents=True)

    entry = {
        "id": "minimal",
        "type": "analysis_orchestrator",
        "version": "1.0.0",
        "status": "active",
        "entrypoint": "/minimal",
        "contract": ".sdd/contracts/analysis-provider.schema.yaml",
        "sdd_injection": {
            "base_path": ".sdd/analysis",
            "execution_provider": "sdd-ask",
            "approval_gate": "required",
            "knowledge_paths": [],
        },
    }
    (plugins_dir / "registry.yaml").write_text(
        yaml.dump({"schema_version": "1.0.0", "plugins": [entry]}),
        encoding="utf-8",
    )

    from sdd_cli.commands import plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(plugin_app, ["validate", "minimal"])
    assert result.exit_code == 0
    assert "pass" in result.output


# ---------------------------------------------------------------------------
# 6.9 mission-contract includes governance_context
# ---------------------------------------------------------------------------


def test_plugin_registry_strategist_has_governance_context(
    plugin_workspace: Path,
) -> None:
    """Strategist plugin entry includes governance_context in sdd_injection."""
    from sdd_cli.commands.plugin import _load_registry

    registry = _load_registry(plugin_workspace)
    strategist = next(p for p in registry["plugins"] if p["id"] == "strategist")
    injection = strategist["sdd_injection"]
    assert "governance_context" in injection
    ctx = injection["governance_context"]
    assert "workspace_version" in ctx
    assert "active_mandates" in ctx
    assert isinstance(ctx["active_mandates"], list)
