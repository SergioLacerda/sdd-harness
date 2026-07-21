"""Commands registry generator — creates .sdd/commands/ with CLI and skill-routed commands."""

import json
from pathlib import Path
from typing import Any

# Canonical command registry: skill-routed + CLI-routed commands.
# Skill-routed commands are derived from _REGISTRY in sdd_runtime.skills.
# CLI-routed commands wrap sdd CLI primitives as agent slash commands.
_CLI_COMMANDS = [
    {
        "id": "sdd-ask",
        "slash": "/sdd-ask",
        "routes_to": {"type": "cli", "command": "sdd ask"},
        "description": "Query SDD governance context. Minimal governed query against compiled context.",
        "targets": ["claude", "codex", "copilot", "antigravity"],
    },
    {
        "id": "sdd-organize",
        "slash": "/sdd-organize",
        "routes_to": {"type": "cli", "command": "sdd organize"},
        "description": "Index and prepare large context blocks for efficient retrieval before analysis.",
        "targets": ["claude", "codex", "copilot", "antigravity"],
    },
]


def generate_commands_registry(
    output_dir: str, config: dict[str, Any]
) -> dict[str, Any]:
    """Generate commands registry at .sdd/commands/registry.json.

    Writes:
    - .sdd/commands/registry.json — index of skill-routed + CLI-routed commands
    - .sdd/commands/<id>/command.yaml — individual command definitions

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict (unused, kept for API consistency)

    Returns:
        Dict with keys:
            - registry_path: Path to generated registry.json
            - command_count: Number of commands exported
    """
    try:
        from sdd_runtime.skills import _REGISTRY

        output_path = Path(output_dir)
        commands_dir = output_path / ".sdd" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        commands: list[dict[str, Any]] = []

        # CLI-routed commands take precedence; build an exclusion set first.
        cli_ids = {cmd["id"] for cmd in _CLI_COMMANDS}

        # Skill-routed commands: one per registered skill, unless a CLI route already owns the id.
        for skill_name in _REGISTRY:
            if skill_name in cli_ids:
                continue
            commands.append(
                {
                    "id": skill_name,
                    "slash": f"/{skill_name}",
                    "routes_to": {"type": "skill", "id": skill_name},
                    "targets": ["claude", "codex", "copilot", "antigravity"],
                }
            )

        # CLI-routed commands (canonical route for sdd-ask and sdd-organize)
        commands.extend(_CLI_COMMANDS)

        # Write individual command.yaml files
        for cmd in commands:
            cmd_dir = commands_dir / cmd["id"]
            cmd_dir.mkdir(parents=True, exist_ok=True)
            cmd_yaml = cmd_dir / "command.yaml"
            routes = cmd["routes_to"]
            lines = [
                f'id: "{cmd["id"]}"',
                f'slash: "{cmd["slash"]}"',
                "routes_to:",
                f"  type: {routes['type']}",
            ]
            if routes["type"] == "skill":
                lines.append(f"  id: {routes['id']}")
            else:
                lines.append(f'  command: "{routes["command"]}"')
            lines.extend(["args: []", "adapter_targets:"])
            for t in cmd.get("targets", []):
                lines.append(f"  - {t}")
            cmd_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Write registry.json
        registry = {
            "schema_version": "1.0.0",
            "commands": [
                {
                    "id": cmd["id"],
                    "slash": cmd["slash"],
                    "routes_to": cmd["routes_to"],
                    "targets": cmd.get("targets", []),
                }
                for cmd in commands
            ],
        }
        registry_path = commands_dir / "registry.json"
        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return {
            "registry_path": registry_path.as_posix(),
            "command_count": len(commands),
        }

    except ImportError:
        return {
            "registry_path": None,
            "command_count": 0,
            "error": "sdd_runtime not available",
        }
