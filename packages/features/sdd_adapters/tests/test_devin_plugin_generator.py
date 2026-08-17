"""Tests for DevinPluginGenerator (Soft/Standalone Devin plugin bundle)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sdd_adapters.devin.plugin_generator import (
    DevinPluginGenerator,
    _coding_practices_digest,
    _governance_summary_digest,
    _load_coding_practices,
    _load_governance_summary,
    _parse_anti_pattern,
    _parse_governance_sections,
    _policy_digest,
    _standalone_collision_paths,
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


def test_generate_with_include_skills_false_omits_skill_catalog(tmp_path: Path) -> None:
    # No .sdd/skills/registry.json at all — include_skills=False must not require one.
    result = DevinPluginGenerator().generate(
        output_dir=tmp_path,
        built_at="2026-08-17T00:00:00+00:00",
        include_skills=False,
    )

    assert result.success is True, result.errors
    bundle = tmp_path / "dist" / "devin-plugin"
    assert not (bundle / "skills").exists()
    assert (bundle / "AGENTS.md").exists()
    assert (bundle / "rules" / "sdd-harness-summary.md").exists()

    plugin_json = read_json_utf8(bundle / ".devin-plugin" / "plugin.json")
    assert "skills" not in plugin_json

    agents_md = (bundle / "AGENTS.md").read_text(encoding="utf-8")
    assert "does not embed the SDD skill catalog" in agents_md


def test_generate_with_include_skills_true_still_requires_skills(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate(
        output_dir=tmp_path,
        built_at="2026-08-17T00:00:00+00:00",
        include_skills=True,
    )

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


def test_parse_governance_sections_accepts_three_hash_headings() -> None:
    # .sdd/source/guidelines/other.md uses '###' while general.md/mandates.md use
    # '##' — the parser must accept both heading levels (regression for the bug
    # where '###' sections were silently dropped, zero items extracted).
    two_hash = _parse_governance_sections(
        "## G01: Dependency Direction\n\n**Type**: GUIDELINE\n\nInner layers first.\n"
    )
    three_hash = _parse_governance_sections(
        "### G01: Dependency Direction\n\n**Type**: GUIDELINE\n\nInner layers first.\n"
    )

    assert two_hash == three_hash
    assert three_hash[0]["id"] == "G01"
    assert three_hash[0]["has_description"] is True


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
    # Real .sdd/source/guidelines/other.md uses '###' headings, unlike general.md's
    # '##' — keep that mismatch in the fixture so tests exercise the real shape.
    (guidelines_dir / "other.md").write_text(
        "### G02: Something\n\n**Type**: GUIDELINE\n\nOther real description.\n",
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
    # other.md uses '###' headings — this must be picked up too (regression for
    # the heading-level bug), not silently dropped.
    assert other["has_highlight"] is True
    assert other["highlight"] == "Other real description."


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


def test_load_governance_summary_counts_described_mandates(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)

    summary = _load_governance_summary(tmp_path)

    # mandates.md fixture: M001 has a real description, M002 is the placeholder.
    assert summary["mandate_count"] == 2
    assert summary["mandate_described_count"] == 1


def test_generate_writes_mandate_description_coverage_line(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)
    _write_skill(sdd_dir, "alpha")

    DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    agents_md = (
        tmp_path / "dist" / "devin-plugin" / "AGENTS.md"
    ).read_text(encoding="utf-8")

    assert "Mandates with a source description: `1/2`" in agents_md


def test_generate_writes_soft_governance_behavior_file(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)
    _write_skill(sdd_dir, "alpha")

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    behavior_path = (
        tmp_path / "dist" / "devin-plugin" / "rules" / "sdd-soft-governance-behavior.md"
    )
    assert behavior_path.exists()
    content = behavior_path.read_text(encoding="utf-8")

    # Curated CLI-independent content must be present.
    assert "Git safety" in content
    assert "Escalate on incomplete" in content
    assert "Mandates outrank guidelines" in content

    # CLI-coupled Hard/Connected concepts must NOT leak into the actual curated
    # rules — this is the scope boundary from design.md § D-003. The intro
    # disclaimer is allowed to *name* these as excluded topics, so only the rule
    # bodies (from "## Rule 1" onward) are checked here.
    rules_body = content.split("## Rule 1", 1)[1]
    assert "execution_gate" not in rules_body
    assert "intake_index_mode" not in rules_body
    assert "handshake" not in rules_body.lower()

    provenance = read_json_utf8(
        tmp_path / "dist" / "devin-plugin" / "metadata" / "provenance.json"
    )
    assert provenance["soft_governance_ruleset_version"] == "1.0.0"
    assert result.success is True


def test_soft_governance_ruleset_version_is_independent_of_content_digests(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_governance_source(sdd_dir)
    _write_skill(sdd_dir, "alpha")

    r1 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    _write_skill(sdd_dir, "beta")
    (sdd_dir / "source" / "mandates" / "mandates.md").write_text(
        "## M001: Clean Architecture\n\n**Criticality**: high\n\nChanged.\n",
        encoding="utf-8",
    )
    r2 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    provenance = read_json_utf8(
        tmp_path / "dist" / "devin-plugin" / "metadata" / "provenance.json"
    )
    assert r1.policy_digest != r2.policy_digest
    assert r1.governance_summary_digest != r2.governance_summary_digest
    assert provenance["soft_governance_ruleset_version"] == "1.0.0"


# --- Coding practices (Go pilot) -------------------------------------------

_VALID_ANTI_PATTERN_TEXT = (
    "# Anti-Pattern: Example\n"
    "\n"
    "## ❌ The Problem\n"
    "\n"
    "Doing the wrong thing.\n"
    "\n"
    "## ✅ The Cure\n"
    "\n"
    "Do the right thing instead.\n"
    "\n"
    "## \U0001f50d Universal Symptoms\n"
    "\n"
    "You'll notice X.\n"
    "\n"
    "## \U0001f4a3 Why It's Dangerous\n"
    "\n"
    "It causes Y.\n"
    "\n"
    "## \U0001f4cf Benchmark\n"
    "\n"
    "Under 5 minutes.\n"
    "\n"
    "## References\n"
    "\n"
    "- somewhere\n"
)


def test_parse_anti_pattern_extracts_all_sections() -> None:
    result = _parse_anti_pattern(_VALID_ANTI_PATTERN_TEXT, "example.md")

    assert result["title"] == "Anti-Pattern: Example"
    assert result["problem"] == "Doing the wrong thing."
    assert result["cure"] == "Do the right thing instead."
    assert result["benchmark"] == "Under 5 minutes."
    assert result["has_symptoms"] is True
    assert result["symptoms"] == "You'll notice X."
    assert result["has_danger"] is True
    assert result["danger"] == "It causes Y."


def test_parse_anti_pattern_accepts_universal_cure_heading_variant() -> None:
    # docs/cognition/anti-patterns/RESOLUTION_BYPASS.md uses "The Universal
    # Cure" while the other 4 files use "The Cure" — must match both.
    text = _VALID_ANTI_PATTERN_TEXT.replace("The Cure", "The Universal Cure")

    result = _parse_anti_pattern(text, "resolution_bypass.md")

    assert result["cure"] == "Do the right thing instead."


def test_parse_anti_pattern_raises_on_missing_required_section() -> None:
    text = (
        "# Anti-Pattern: Broken\n\n## ❌ The Problem\n\nSomething.\n"
        # No Cure section, no Benchmark section.
    )

    with pytest.raises(ValueError, match="missing required section"):
        _parse_anti_pattern(text, "broken.md")


def test_parse_anti_pattern_raises_on_missing_title() -> None:
    text = "## ❌ The Problem\n\nSomething.\n\n## ✅ The Cure\n\nFix.\n\n## \U0001f4cf Benchmark\n\nFast.\n"

    with pytest.raises(ValueError, match="missing title"):
        _parse_anti_pattern(text, "no_title.md")


def test_parse_anti_pattern_captures_content_glued_to_heading() -> None:
    # docs/cognition/anti-patterns/lang/GO_RESOLUTION_BYPASS.md's real "Rule"
    # section has content on the same line as the heading marker, no line
    # break — the parser must not silently drop it.
    text = (
        "# Anti-Pattern: Glued\n\n"
        "## ❌ The Problem> problem text here\n\n"
        "## ✅ The Cure> cure text here\n\n"
        "## \U0001f4cf Benchmark> benchmark text here\n"
    )

    result = _parse_anti_pattern(text, "glued.md")

    assert result["problem"] == "> problem text here"
    assert result["cure"] == "> cure text here"
    assert result["benchmark"] == "> benchmark text here"


def test_parse_anti_pattern_ignores_heading_like_line_inside_code_fence() -> None:
    # docs/cognition/anti-patterns/SCOPE_CREEP.md's real Cure section contains
    # a fenced example with "## Parking Lot" inside it — that must not be
    # treated as a new section boundary, or the rest of the real Cure content
    # (and Benchmark) would be silently dropped.
    text = (
        "# Anti-Pattern: Fenced\n\n"
        "## ❌ The Problem\n\nProblem text.\n\n"
        "## ✅ The Cure\n\n"
        "Real cure text.\n\n"
        "```markdown\n"
        "## \U0001f17f️ Parking Lot (example only)\n"
        "- not a real section\n"
        "```\n\n"
        "More real cure text after the fence.\n\n"
        "## \U0001f4cf Benchmark\n\nBenchmark text.\n"
    )

    result = _parse_anti_pattern(text, "fenced.md")

    assert "Real cure text." in result["cure"]
    assert "More real cure text after the fence." in result["cure"]
    assert "Parking Lot" in result["cure"]  # fenced example content preserved
    assert result["benchmark"] == "Benchmark text."


def _write_coding_practices_source(repo_dir: Path) -> None:
    anti_patterns_dir = repo_dir / "docs" / "cognition" / "anti-patterns"
    anti_patterns_dir.mkdir(parents=True)
    for name in (
        "COGNITIVE_OVERLOAD",
        "PREMATURE_EXECUTION",
        "RESOLUTION_BYPASS",
        "SCOPE_CREEP",
        "SYMPTOM_FIXING",
    ):
        (anti_patterns_dir / f"{name}.md").write_text(
            _VALID_ANTI_PATTERN_TEXT, encoding="utf-8"
        )
    lang_dir = anti_patterns_dir / "lang"
    lang_dir.mkdir()
    (lang_dir / "GO_RESOLUTION_BYPASS.md").write_text(
        "# Resolution Bypass — Go\n\n"
        "## ❌ Go-Specific Hacks\n\nDon't do this.\n\n"
        "## ✅ Go Cures\n\nDo this instead.\n\n"
        "## \U0001f50d Detection\n\ngrep for it.\n\n"
        "## \U0001f4cf Rule\n\nAlways works after clone.\n",
        encoding="utf-8",
    )


def test_load_coding_practices_returns_none_when_category_absent(
    tmp_path: Path,
) -> None:
    assert _load_coding_practices(tmp_path) is None


def test_load_coding_practices_parses_all_sources_when_present(
    tmp_path: Path,
) -> None:
    _write_coding_practices_source(tmp_path)

    result = _load_coding_practices(tmp_path)

    assert result is not None
    assert len(result["anti_patterns"]) == 5
    assert result["go_resolution_bypass"]["rule"] == "Always works after clone."


def test_load_coding_practices_raises_when_one_file_missing(
    tmp_path: Path,
) -> None:
    _write_coding_practices_source(tmp_path)
    (tmp_path / "docs" / "cognition" / "anti-patterns" / "SCOPE_CREEP.md").unlink()

    with pytest.raises(ValueError, match="missing anti-pattern source"):
        _load_coding_practices(tmp_path)


def test_generate_omits_coding_practices_file_when_category_absent(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")
    # No docs/cognition/anti-patterns/ — must not be a hard failure for a
    # project that isn't the SDD Harness repo itself.

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert result.success is True, result.errors
    assert not (
        tmp_path / "dist" / "devin-plugin" / "rules" / "sdd-coding-practices.md"
    ).exists()
    assert result.coding_practices_digest == ""
    provenance = read_json_utf8(
        tmp_path / "dist" / "devin-plugin" / "metadata" / "provenance.json"
    )
    assert provenance["coding_practices_digest"] is None


def test_generate_writes_coding_practices_when_category_present(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")
    _write_coding_practices_source(tmp_path)

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert result.success is True, result.errors
    practices_path = (
        tmp_path / "dist" / "devin-plugin" / "rules" / "sdd-coding-practices.md"
    )
    assert practices_path.exists()
    content = practices_path.read_text(encoding="utf-8")
    assert "Anti-Pattern: Example" in content
    assert "Go-Specific Guidance" in content
    assert f"sha256:{result.coding_practices_digest}" in content

    agents_md = (tmp_path / "dist" / "devin-plugin" / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "rules/sdd-coding-practices.md" in agents_md

    rule4 = (
        tmp_path
        / "dist"
        / "devin-plugin"
        / "rules"
        / "sdd-soft-governance-behavior.md"
    ).read_text(encoding="utf-8")
    assert "Rule 4" in rule4
    assert "Rule 3" in rule4

    # No CLI-coupled content in the actual rule bodies. The intro disclaimer
    # is allowed to *name* excluded commands (same pattern as the prior
    # mission's "handshake" disclaimer), so only Rule 4's own body — the new
    # content this task adds — is checked here.
    rule4_body = rule4.split("## Rule 4", 1)[1]
    assert "sdd runtime status" not in content
    assert "sdd governance validate" not in content
    assert "sdd test run" not in content
    assert "sdd lint run" not in content
    assert "sdd runtime status" not in rule4_body
    assert "sdd governance validate" not in rule4_body
    assert "sdd test run" not in rule4_body
    assert "sdd lint run" not in rule4_body


def test_coding_practices_digest_is_independent_of_other_digests(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")
    _write_governance_source(sdd_dir)
    _write_coding_practices_source(tmp_path)

    r1 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    # Changing only coding-practices content must not change the other three
    # digest/version fields.
    (
        tmp_path
        / "docs"
        / "cognition"
        / "anti-patterns"
        / "SCOPE_CREEP.md"
    ).write_text(
        _VALID_ANTI_PATTERN_TEXT.replace("Do the right thing", "Do a different thing"),
        encoding="utf-8",
    )
    r2 = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert r1.coding_practices_digest != r2.coding_practices_digest
    assert r1.policy_digest == r2.policy_digest
    assert r1.governance_summary_digest == r2.governance_summary_digest


def test_coding_practices_digest_helper_changes_with_content() -> None:
    base = {
        "anti_patterns": [
            {
                "id": "A",
                "title": "A",
                "problem": "p",
                "cure": "c",
                "benchmark": "b",
            }
        ],
        "go_resolution_bypass": {"hacks": "h", "cures": "c", "detection": "d", "rule": "r"},
    }
    changed = {
        **base,
        "go_resolution_bypass": {**base["go_resolution_bypass"], "rule": "different"},
    }

    assert _coding_practices_digest(base) != _coding_practices_digest(changed)


def test_generate_coding_practices_against_real_repo_sources(tmp_path: Path) -> None:
    repo_root = None
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "cognition" / "anti-patterns").exists():
            repo_root = parent
            break
    if repo_root is None:
        pytest.skip(
            "no docs/cognition/anti-patterns/ found above this test file — this "
            "environment does not include the full SDD Harness source tree "
            "(e.g. a packaging/shadow-repo check); skipping the real-source "
            "regression test."
        )

    result = DevinPluginGenerator().generate(
        output_dir=repo_root,
        dest=tmp_path / "devin-plugin",
        built_at="2026-08-17T00:00:00+00:00",
    )

    assert result.success is True, result.errors
    practices_path = tmp_path / "devin-plugin" / "rules" / "sdd-coding-practices.md"
    assert practices_path.exists()
    content = practices_path.read_text(encoding="utf-8")
    for title_fragment in (
        "Cognitive Overload",
        "Premature Execution",
        "Resolution Bypass",
        "Scope Creep",
        "Symptom Fixing",
    ):
        assert title_fragment in content
    assert "Go-Specific Guidance" in content


# --- Standalone (zero-SDD-mention) mode -------------------------------------

_STANDALONE_EXPECTED_FILES = (
    "AGENTS.md",
    ".devin/config.json",
    ".devin/hooks.v1.json",
    ".devin/rules/architecture.md",
    ".devin/rules/git-safety.md",
    ".devin/rules/testing.md",
    ".devin/rules/generated-artifacts.md",
    ".devin/rules/python.md",
    ".devin/rules/go.md",
    ".devin/rules/documentation.md",
)


def test_standalone_collision_paths_empty_when_clean(tmp_path: Path) -> None:
    assert _standalone_collision_paths(tmp_path) == []


def test_standalone_collision_paths_detects_existing_agents_md(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("existing", encoding="utf-8")

    conflicts = _standalone_collision_paths(tmp_path)

    assert conflicts == [tmp_path / "AGENTS.md"]


def test_standalone_collision_paths_detects_existing_devin_dir(tmp_path: Path) -> None:
    (tmp_path / ".devin").mkdir()

    conflicts = _standalone_collision_paths(tmp_path)

    assert conflicts == [tmp_path / ".devin"]


def test_generate_standalone_refuses_when_agents_md_exists(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("existing", encoding="utf-8")

    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is False
    assert "AGENTS.md" in result.errors[0]
    assert result.files_written == []
    # Refusal must not touch anything else either.
    assert not (tmp_path / ".devin").exists()


def test_generate_standalone_refuses_when_devin_dir_exists(tmp_path: Path) -> None:
    (tmp_path / ".devin").mkdir()

    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is False
    assert ".devin" in result.errors[0]


def test_generate_standalone_writes_exactly_the_expected_files(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True, result.errors
    for rel_path in _STANDALONE_EXPECTED_FILES:
        assert (tmp_path / rel_path).exists(), f"missing {rel_path}"
        assert (tmp_path / rel_path).stat().st_size > 0

    written = {Path(p).relative_to(tmp_path) for p in result.files_written}
    expected = {Path(p) for p in _STANDALONE_EXPECTED_FILES}
    assert written == expected


def test_generate_standalone_config_json_is_valid_and_denies_git_mutation(
    tmp_path: Path,
) -> None:
    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    config = json.loads((tmp_path / ".devin" / "config.json").read_text(encoding="utf-8"))

    assert "Exec(git push)" in config["permissions"]["deny"]
    assert "Exec(git commit)" in config["permissions"]["deny"]
    assert "Exec(git add)" in config["permissions"]["deny"]
    assert "Read(**)" in config["permissions"]["allow"]


def test_generate_standalone_hooks_v1_json_is_valid_schema(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    hooks = json.loads(
        (tmp_path / ".devin" / "hooks.v1.json").read_text(encoding="utf-8")
    )

    # Top-level keys are event names directly — no wrapper key (confirmed real
    # schema, docs/spec/guides/devin-plugin-provider-surface-evidence.md).
    assert "SessionStart" in hooks
    assert hooks["SessionStart"][0]["hooks"][0]["type"] == "command"


def test_generate_standalone_rule_content_matches_expected_topics(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    rules_dir = tmp_path / ".devin" / "rules"
    assert "Red-Green-Refactor" in (rules_dir / "testing.md").read_text(encoding="utf-8")
    assert "golangci-lint" in (rules_dir / "go.md").read_text(encoding="utf-8")
    assert "ruff" in (rules_dir / "python.md").read_text(encoding="utf-8")
    assert "hand-edit" in (rules_dir / "generated-artifacts.md").read_text(encoding="utf-8")
    assert "git" in (rules_dir / "git-safety.md").read_text(encoding="utf-8").lower()
    assert "Naming" in (rules_dir / "architecture.md").read_text(encoding="utf-8")
    assert "WHY" in (rules_dir / "documentation.md").read_text(encoding="utf-8")


def test_generate_standalone_output_never_mentions_sdd(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    for rel_path in _STANDALONE_EXPECTED_FILES:
        content = (tmp_path / rel_path).read_text(encoding="utf-8")
        assert "sdd" not in content.lower(), f"{rel_path} mentions sdd"


def test_generate_standalone_real_sources_exist() -> None:
    # Standalone content is curated (D-001), not parsed — this is the closest
    # available regression signal that the sources it was drawn from haven't
    # moved or been deleted (same lesson as the coding-practices mission's
    # real-file test, adapted for static content with no parser to re-run).
    repo_root = None
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "guidelines" / "core-engineering-principles.md").exists():
            repo_root = parent
            break
    if repo_root is None:
        pytest.skip(
            "no docs/guidelines/core-engineering-principles.md found above this "
            "test file — this environment does not include the full SDD Harness "
            "source tree; skipping the real-source existence check."
        )

    for rel_path in (
        "docs/guidelines/core-engineering-principles.md",
        "docs/guidelines/languages/go.md",
        "docs/guidelines/languages/python.md",
        "docs/spec/canonical/features/TDD.md",
    ):
        path = repo_root / rel_path
        assert path.exists(), f"standalone-mode source missing: {rel_path}"
        assert path.stat().st_size > 0, f"standalone-mode source empty: {rel_path}"


def test_generate_standalone_never_touches_the_network(
    tmp_path: Path, monkeypatch
) -> None:
    import socket

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "network access attempted during standalone generation"
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = DevinPluginGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True, result.errors
