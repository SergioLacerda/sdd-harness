"""Tests for DevinPluginGenerator (Soft/Standalone Devin plugin bundle)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sdd_adapters.devin.plugin_generator import DevinPluginGenerator, _policy_digest
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
