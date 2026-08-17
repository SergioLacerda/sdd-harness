"""Tests for DevinPluginGenerator (Soft/Standalone Devin plugin bundle)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sdd_adapters.devin.plugin_generator import (
    DevinPluginGenerator,
    _governance_summary_digest,
    _load_governance_summary,
    _parse_governance_sections,
    _policy_digest,
)
from sdd_core.utils.text_io import read_json_utf8


def test_policy_digest_is_deterministic_for_same_input() -> None:
    skills = [{"name": "a", "risk_score": "high"}, {"name": "b", "risk_score": "low"}]

    assert _policy_digest(skills) == _policy_digest(skills)
    assert len(_policy_digest(skills)) == 64


def test_policy_digest_changes_with_content() -> None:
    skills_a = [{"name": "a", "risk_score": "low"}]
    skills_b = [{"name": "a", "risk_score": "high"}]

    assert _policy_digest(skills_a) != _policy_digest(skills_b)


def _write_skill(sdd_dir: Path, name: str, **overrides: object) -> None:
    skills_dir = sdd_dir / "skills" / name
    skills_dir.mkdir(parents=True)
    base = {
        "name": name,
        "description": f"{name} description.",
        "when_to_use": ["testing"],
        "allowed_tools": [f"sdd {name}"],
        "triggers": [name],
        "risk_score": "low",
    }
    base.update(overrides)
    (skills_dir / "skill.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
    registry_path = sdd_dir / "skills" / "registry.json"
    registry = {"skills": []}
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["skills"].append({"name": name})
    registry_path.write_text(json.dumps(registry), encoding="utf-8")


def test_generate_writes_full_plugin_bundle(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")
    _write_skill(sdd_dir, "beta")

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path,
        source_revision="deadbeef",
        built_at="2026-08-17T00:00:00+00:00",
    )

    assert result.success is True
    bundle = tmp_path / "dist" / "devin-plugin"
    assert (bundle / ".devin-plugin" / "plugin.json").exists()
    assert (bundle / "AGENTS.md").exists()
    assert (bundle / "hooks.json").exists()
    assert (bundle / "metadata" / "provenance.json").exists()
    assert (bundle / "hooks" / "session-start-assurance.sh").exists()
    assert (bundle / "skills" / "alpha" / "SKILL.md").exists()
    assert (bundle / "skills" / "beta" / "SKILL.md").exists()

    plugin_json = read_json_utf8(bundle / ".devin-plugin" / "plugin.json")
    assert plugin_json["name"] == "sdd-governance-devin"

    provenance = read_json_utf8(bundle / "metadata" / "provenance.json")
    assert provenance["source_revision"] == "deadbeef"
    assert provenance["profile"] == "soft"
    assert provenance["embedded_policy_digest"] == f"sha256:{result.policy_digest}"

    hook_script = bundle / "hooks" / "session-start-assurance.sh"
    assert hook_script.stat().st_mode & 0o111  # executable bits set


def test_generate_is_deterministic_for_same_input(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")

    r1 = DevinPluginGenerator().generate(
        output_dir=tmp_path, source_revision="x", built_at="2026-08-17T00:00:00+00:00"
    )
    r2 = DevinPluginGenerator().generate(
        output_dir=tmp_path, source_revision="x", built_at="2026-08-17T00:00:00+00:00"
    )

    assert r1.policy_digest == r2.policy_digest


def test_generate_reports_error_when_no_skills(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate(output_dir=tmp_path)

    assert result.success is False
    assert result.errors


def test_generate_never_touches_the_network(tmp_path: Path, monkeypatch) -> None:
    import socket

    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "network access attempted during Soft/Standalone generation"
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert result.success is True


def test_generate_against_real_repo_registry(tmp_path: Path) -> None:
    repo_root = None
    for parent in Path(__file__).resolve().parents:
        if (parent / ".sdd" / "skills" / "registry.json").exists():
            repo_root = parent
            break
    if repo_root is None:
        pytest.skip(
            "no .sdd/skills/registry.json found above this test file — this "
            "environment does not include the full SDD Harness source tree "
            "(e.g. a packaging/shadow-repo check); skipping the real-registry "
            "integration test."
        )

    result = DevinPluginGenerator().generate(
        output_dir=repo_root,
        dest=tmp_path / "devin-plugin",
        built_at="2026-08-17T00:00:00+00:00",
    )

    assert result.success is True, result.errors
    # Skill inventory is environment-dependent (the shadow/container repo may
    # rebuild .sdd/skills/ with a different set than a full host checkout), so
    # this only proves the real registry drives the generator end-to-end —
    # it does not pin an exact skill count or name.
    skill_dirs = sorted(
        p.name for p in (tmp_path / "devin-plugin" / "skills").iterdir()
    )
    assert len(skill_dirs) >= 1
    assert len(result.policy_digest) == 64


def test_parse_governance_sections_extracts_id_title_and_description() -> None:
    text = (
        "## M001: Clean Architecture\n"
        "\n"
        "**Criticality**: high\n"
        "**Customizable**: No\n"
        "\n"
        "Layers must not depend on outer layers.\n"
    )

    sections = _parse_governance_sections(text)

    assert sections == [
        {
            "id": "M001",
            "title": "Clean Architecture",
            "description": "Layers must not depend on outer layers.",
            "has_description": True,
        }
    ]


def test_parse_governance_sections_flags_placeholder_as_no_description() -> None:
    text = (
        "## M002: Test-Driven Development (TDD)\n"
        "\n"
        "**Criticality**: high\n"
        "\n"
        "No description available\n"
    )

    sections = _parse_governance_sections(text)

    assert sections[0]["has_description"] is False
    assert sections[0]["description"] == ""


def test_parse_governance_sections_ignores_non_id_headings() -> None:
    text = "## Overview\n\nSome prose.\n\n## M001: Clean Architecture\n\nReal text.\n"

    sections = _parse_governance_sections(text)

    assert len(sections) == 1
    assert sections[0]["id"] == "M001"


def _write_governance_source(sdd_dir: Path) -> None:
    sdd_dir.mkdir(parents=True, exist_ok=True)
    (sdd_dir / "metadata.json").write_text(
        json.dumps({"governance_fingerprint": "abc123", "version": "3.0"}),
        encoding="utf-8",
    )
    mandates_dir = sdd_dir / "source" / "mandates"
    mandates_dir.mkdir(parents=True)
    (mandates_dir / "mandates.md").write_text(
        "## M001: Clean Architecture\n\n**Criticality**: high\n\nReal description.\n\n"
        "## M002: TDD\n\n**Criticality**: high\n\nNo description available\n",
        encoding="utf-8",
    )
    guidelines_dir = sdd_dir / "source" / "guidelines"
    guidelines_dir.mkdir(parents=True)
    (guidelines_dir / "general.md").write_text(
        "## G01: Dependency Direction\n\n**Type**: GUIDELINE\n\nInner layers first.\n",
        encoding="utf-8",
    )
    (guidelines_dir / "other.md").write_text(
        "## G02: Something\n\n**Type**: GUIDELINE\n\nNo description available\n",
        encoding="utf-8",
    )


def test_load_governance_summary_reads_metadata_mandates_and_guidelines(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)

    summary = _load_governance_summary(tmp_path)

    assert summary["governance_fingerprint"] == "abc123"
    assert summary["workspace_version"] == "3.0"
    assert summary["mandate_count"] == 2
    assert summary["guideline_categories"] == ["general", "other"]
    general = next(g for g in summary["guidelines"] if g["category"] == "general")
    other = next(g for g in summary["guidelines"] if g["category"] == "other")
    assert general["has_highlight"] is True
    assert other["has_highlight"] is False


def test_load_governance_summary_degrades_gracefully_when_source_absent(
    tmp_path: Path,
) -> None:
    summary = _load_governance_summary(tmp_path)

    assert summary["governance_fingerprint"] == "unknown"
    assert summary["mandate_count"] == 0
    assert summary["mandates"] == []
    assert summary["guideline_categories"] == []


def test_governance_summary_digest_is_independent_of_policy_digest(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)
    _write_skill(sdd_dir, "alpha")

    r1 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    # Changing only skill content must not change governance_summary_digest.
    _write_skill(sdd_dir, "beta")
    r2 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert r1.governance_summary_digest == r2.governance_summary_digest
    assert r1.policy_digest != r2.policy_digest

    # Changing only mandate content must not change policy_digest.
    (sdd_dir / "source" / "mandates" / "mandates.md").write_text(
        "## M001: Clean Architecture\n\n**Criticality**: high\n\nChanged text.\n",
        encoding="utf-8",
    )
    r3 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert r3.governance_summary_digest != r2.governance_summary_digest
    assert r3.policy_digest == r2.policy_digest


def test_generate_writes_governance_summary_bundle_content(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)
    _write_skill(sdd_dir, "alpha")

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert result.success is True
    bundle = tmp_path / "dist" / "devin-plugin"
    summary_path = bundle / "rules" / "sdd-harness-summary.md"
    assert summary_path.exists()

    agents_md = (bundle / "AGENTS.md").read_text(encoding="utf-8")
    assert "SDD Harness Summary" in agents_md
    assert "M001" in agents_md

    summary_content = summary_path.read_text(encoding="utf-8")
    assert f"sha256:{result.governance_summary_digest}" in summary_content
    assert "Real description." in summary_content
    assert "(no summary available in source)" in summary_content
    assert "No description available" not in summary_content

    provenance = read_json_utf8(bundle / "metadata" / "provenance.json")
    assert (
        provenance["embedded_governance_summary_digest"]
        == f"sha256:{result.governance_summary_digest}"
    )
