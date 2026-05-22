"""Tests for AdapterGenerator — integration tests using tmp_path."""

import json
from pathlib import Path

import yaml

from sdd_adapters import AdapterGenerator
from sdd_core.utils.text_io import read_text_utf8, write_text_utf8


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project with .sdd/skills/ and .sdd/commands/."""
    sdd = tmp_path / ".sdd"
    skills_dir = sdd / "skills"
    skills_dir.mkdir(parents=True)
    commands_dir = sdd / "commands"
    commands_dir.mkdir(parents=True)

    skills = [
        {
            "name": "diagnose",
            "category": "analysis",
            "description": "Diagnose runtime problems.",
            "risk_score": "low",
            "when_to_use": ["failing checks"],
            "allowed_tools": ["sdd doctor run"],
            "cli_fallback": ["sdd doctor run"],
        },
        {
            "name": "stabilize",
            "category": "operations",
            "description": "Run stabilization checks.",
            "risk_score": "medium",
            "when_to_use": ["pre-delivery"],
            "allowed_tools": ["sdd lint run"],
            "cli_fallback": ["sdd lint run"],
        },
    ]

    registry = {
        "schema_version": "1.0.0",
        "skills": [
            {"name": s["name"], "description": s["description"]} for s in skills
        ],
    }
    (skills_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

    for skill in skills:
        skill_dir = skills_dir / skill["name"]
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(yaml.dump(skill), encoding="utf-8")

    commands = [
        {
            "id": "sdd-diagnose",
            "slash": "/sdd-diagnose",
            "routes_to": {"type": "skill", "id": "diagnose"},
            "targets": ["claude", "codex", "copilot", "antigravity"],
        },
        {
            "id": "sdd-ask",
            "slash": "/sdd-ask",
            "routes_to": {"type": "cli", "command": "sdd ask"},
            "targets": ["claude", "codex", "copilot", "antigravity"],
        },
    ]
    (commands_dir / "registry.json").write_text(
        json.dumps({"schema_version": "1.0.0", "commands": commands}),
        encoding="utf-8",
    )
    for command in commands:
        cmd_dir = commands_dir / command["id"]
        cmd_dir.mkdir()
        (cmd_dir / "command.yaml").write_text(yaml.dump(command), encoding="utf-8")

    return tmp_path


class TestAdapterGenerator:
    def test_generate_creates_files_for_all_targets(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()
        results = gen.generate(output_dir=project)

        assert set(results.keys()) == {"claude", "codex", "copilot", "antigravity"}
        for target, result in results.items():
            assert result.success, f"{target} failed: {result.errors}"
            assert len(result.files_written) == 4  # skills + commands

    def test_claude_commands_written(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()
        gen.generate(output_dir=project)

        claude_dir = project / ".claude" / "commands"
        assert (claude_dir / "diagnose.md").exists()
        assert (claude_dir / "stabilize.md").exists()

        content = read_text_utf8(claude_dir / "diagnose.md")
        assert "sdd doctor run" in content
        assert ".sdd/skills/registry.json" in content

    def test_codex_skills_written(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()
        gen.generate(output_dir=project)

        codex_dir = project / ".codex" / "skills"
        assert (codex_dir / "diagnose.prompt.md").exists()
        assert (codex_dir / "stabilize.prompt.md").exists()

        content = read_text_utf8(codex_dir / "diagnose.prompt.md")
        assert "SDD GOVERNANCE" in content
        assert "sdd organize" in content  # analysis category
        command_skill = read_text_utf8(codex_dir / "sdd-diagnose.prompt.md")
        command_cli = read_text_utf8(codex_dir / "sdd-ask.prompt.md")
        assert "sdd skills run diagnose" in command_skill
        assert "`sdd ask`" in command_cli

    def test_antigravity_uses_subdirectory_per_skill(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()
        gen.generate(output_dir=project)

        ag_base = project / ".gemini" / "antigravity" / "skills"
        assert (ag_base / "diagnose" / "SKILL.md").exists()
        assert (ag_base / "stabilize" / "SKILL.md").exists()

    def test_empty_skills_registry_generates_no_files(self, tmp_path: Path) -> None:
        sdd = tmp_path / ".sdd" / "skills"
        sdd.mkdir(parents=True)
        write_text_utf8(
            sdd / "registry.json", json.dumps({"schema_version": "1.0.0", "skills": []})
        )

        gen = AdapterGenerator()
        results = gen.generate(output_dir=tmp_path)

        for _target, result in results.items():
            assert result.success
            assert result.files_written == []

    def test_generate_captures_target_level_exception(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()

        original = gen._generate_for_target

        def _boom(target: str, output_dir: Path):  # type: ignore[no-untyped-def]
            if target == "codex":
                raise RuntimeError("broken target")
            return original(target, output_dir)

        gen._generate_for_target = _boom  # type: ignore[method-assign]
        results = gen.generate(output_dir=project)

        assert results["codex"].success is False
        assert "broken target" in results["codex"].errors[0]

    def test_generate_skips_command_without_target(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        command_yaml = project / ".sdd" / "commands" / "sdd-diagnose" / "command.yaml"
        data = yaml.safe_load(read_text_utf8(command_yaml))
        data["adapter_targets"] = ["claude"]
        command_yaml.write_text(yaml.safe_dump(data), encoding="utf-8")

        gen = AdapterGenerator()
        result = gen._generate_for_target("codex", project)

        assert all(
            "sdd-diagnose.prompt.md" not in path for path in result.files_written
        )
        assert any("sdd-ask.prompt.md" in path for path in result.files_written)

    def test_generate_collects_skill_render_error(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()

        original = gen._render_skill_adapter

        def _maybe_fail(target: str, skill: dict[str, str], output_dir: Path) -> Path:
            if skill.get("name") == "diagnose":
                raise RuntimeError("skill render failed")
            return original(target, skill, output_dir)

        gen._render_skill_adapter = _maybe_fail  # type: ignore[method-assign]
        result = gen._generate_for_target("codex", project)

        assert result.success is False
        assert any("skill render failed" in err for err in result.errors)

    def test_generate_collects_command_render_error(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        gen = AdapterGenerator()

        original = gen._render_command_adapter

        def _maybe_fail(target: str, command: dict[str, str], output_dir: Path) -> Path:
            if command.get("id") == "sdd-ask":
                raise RuntimeError("command render failed")
            return original(target, command, output_dir)

        gen._render_command_adapter = _maybe_fail  # type: ignore[method-assign]
        result = gen._generate_for_target("codex", project)

        assert result.success is False
        assert any("command render failed" in err for err in result.errors)
