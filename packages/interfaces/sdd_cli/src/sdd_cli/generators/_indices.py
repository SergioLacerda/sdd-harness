"""Index generators — externalizes searchable indices to .sdd/indices/ directory."""

import json
from pathlib import Path
from typing import Any, cast


def generate_skill_index(output_dir: str, config: dict[str, Any]) -> dict[str, Any]:
    """Generate skill discovery index.

    Writes:
    - .sdd/indices/skills.index.json — searchable skill metadata

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict

    Returns:
        Dict with keys:
            - index_path: Path to generated skills.index.json
            - skill_count: Number of skills indexed
            - indexed_skills: List of indexed skill names
    """
    try:
        from sdd_runtime.skills import SkillEngine

        engine = SkillEngine()
        skills = engine.list_skills()

        output_path = Path(output_dir)
        indices_dir = output_path / ".sdd" / "indices"
        indices_dir.mkdir(parents=True, exist_ok=True)

        # Build skill index
        skills_index = {
            "schema_version": "1.0.0",
            "index_type": "skills",
            "generated_at": _timestamp_iso8601(),
            "skills": [
                {
                    "name": skill.name,
                    "category": skill.category,
                    "description": skill.description,
                    "version": skill.version,
                    "status": skill.status,
                    "risk_score": skill.risk_score,
                    "executable_via_cli": bool(skill.cli_fallback),
                    "required_permissions": skill.required_permissions or [],
                    "budget_policy": skill.budget_policy or {},
                    "yaml_path": f".sdd/skills/{skill.name}/skill.yaml",
                }
                for skill in sorted(skills, key=lambda s: s.name)
            ],
        }

        index_path = indices_dir / "skills.index.json"
        index_path.write_text(
            json.dumps(skills_index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        indexed_skills: list[str] = [
            cast(dict[str, Any], skill)["name"]
            for skill in cast(list[Any], skills_index["skills"])
        ]

        return {
            "index_path": str(index_path),
            "skill_count": len(indexed_skills),
            "indexed_skills": indexed_skills,
        }

    except ImportError:
        return {
            "index_path": None,
            "skill_count": 0,
            "indexed_skills": [],
            "error": "SkillEngine not available",
        }


def generate_cli_commands_index(
    output_dir: str, config: dict[str, Any]
) -> dict[str, Any]:
    """Generate CLI commands discovery index.

    Writes:
    - .sdd/indices/cli.commands.json — searchable command metadata

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict

    Returns:
        Dict with keys:
            - index_path: Path to generated cli.commands.json
            - command_count: Number of commands indexed
    """
    try:
        output_path = Path(output_dir)
        indices_dir = output_path / ".sdd" / "indices"
        indices_dir.mkdir(parents=True, exist_ok=True)

        # Define canonical SDD CLI commands
        commands = [
            {
                "name": "sdd ask",
                "group": "governance",
                "purpose": "Query governance context",
                "flags": ["--dossier", "--skill", "--budget"],
                "governed_by": ["M010", "G003"],
                "requires_handshake": True,
            },
            {
                "name": "sdd ask-full",
                "group": "governance",
                "purpose": "Query governance with full context and compression",
                "flags": [],
                "governed_by": ["M010", "G003"],
                "requires_handshake": True,
            },
            {
                "name": "sdd governance compile",
                "group": "governance",
                "purpose": "Compile governance sources to msgpack",
                "flags": [],
                "governed_by": ["M005", "M008"],
                "requires_handshake": False,
            },
            {
                "name": "sdd governance generate",
                "group": "governance",
                "purpose": "Generate agent seeds and skills registry",
                "flags": ["--output-dir", "--path"],
                "governed_by": ["M005"],
                "requires_handshake": False,
            },
            {
                "name": "sdd governance validate",
                "group": "governance",
                "purpose": "Validate governance integrity",
                "flags": [],
                "governed_by": ["M005"],
                "requires_handshake": False,
            },
            {
                "name": "sdd skill",
                "group": "skills",
                "purpose": "Execute or inspect a skill",
                "flags": ["--execute", "--list"],
                "governed_by": ["M020"],
                "requires_handshake": True,
            },
            {
                "name": "sdd metrics show",
                "group": "metrics",
                "purpose": "Display token economy metrics",
                "flags": ["--format"],
                "governed_by": ["M005"],
                "requires_handshake": False,
            },
            {
                "name": "sdd runtime status",
                "group": "runtime",
                "purpose": "Check runtime health and configuration",
                "flags": [],
                "governed_by": [],
                "requires_handshake": False,
            },
        ]

        commands_index = {
            "schema_version": "1.0.0",
            "index_type": "cli_commands",
            "generated_at": _timestamp_iso8601(),
            "total_commands": len(commands),
            "commands": sorted(
                commands,
                key=lambda c: cast(str, c["name"]),
            ),
        }

        index_path = indices_dir / "cli.commands.json"
        index_path.write_text(
            json.dumps(commands_index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return {
            "index_path": str(index_path),
            "command_count": len(commands),
            "commands": [cmd["name"] for cmd in commands],
        }

    except Exception as e:
        return {
            "index_path": None,
            "command_count": 0,
            "commands": [],
            "error": str(e),
        }


def _timestamp_iso8601() -> str:
    """Generate ISO 8601 timestamp for index generation."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
