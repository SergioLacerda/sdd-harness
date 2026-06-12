"""Constants, registry loaders, and pure string builders for prompt command generation."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

_COMMANDS_TABLE = (
    "| Task | Command |\n"
    "|------|---------|\n"
    "| Run tests | `sdd test run` |\n"
    "| Lint | `sdd lint run` |\n"
    "| Validate governance | `sdd governance validate` |\n"
    "| Compile governance | `sdd governance compile` |\n"
    "| Runtime status | `sdd runtime status` |\n"
    '| Query context | `sdd ask --full "<question>"` |\n'
    '| Organize large context | `sdd organize "<context>"` |\n'
    "| Diagnostics | `sdd doctor run --mode real` |\n"
    "| Generate agent seeds | `sdd governance generate` |\n"
)

_RUNTIME_STATUS_NOTE = (
    "Exit codes for `sdd runtime status`: "
    "0=HEALTHY, 1=NOT_INITIALIZED, 2=MISCONFIGURED, 3=NOT_CONNECTED.\n"
)

_SOFT_GOVERNANCE_CHECK = (
    "\nSDD GOVERNANCE CHECK\n"
    "- Always end responses with this compact footer:\n"
    "  `SDD GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`\n"
)

_AUDIT_JSON_NOTE = (
    "\nAudit JSON policy:\n"
    "- `.sdd/compiled/audit/*.json` is human/audit oriented.\n"
    "- Agents should prefer `.sdd/source/*` for human-readable governance context and\n"
    "  runtime checks (`sdd runtime status`, `sdd ask --full`) for operational state.\n"
)

__all__ = [
    "_AUDIT_JSON_NOTE",
    "_COMMANDS_TABLE",
    "_RUNTIME_STATUS_NOTE",
    "_SOFT_GOVERNANCE_CHECK",
]

_ASK_500_FALLBACK_NOTE = (
    "\nOperational fallback (IDE/API failures):\n"
    "- If the IDE/provider returns `API Error: 5xx`, stop IDE retry loops for this turn.\n"
    "- Run local fallback immediately in terminal:\n"
    '  `sdd ask --full "$QUERY"`\n'
    "- Capture and report the provider `request_id` for incident triage.\n"
)


def _load_slash_aliases(output_dir: Path) -> list[tuple[str, str]]:
    """Load slash aliases from canonical command registry with safe fallback."""
    registry_path = output_dir / ".sdd" / "commands" / "registry.json"
    aliases: list[tuple[str, str]] = []
    try:
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        commands = data.get("commands", [])
        if isinstance(commands, list):
            for cmd in commands:
                if not isinstance(cmd, dict):
                    continue
                slash = str(cmd.get("slash", "")).strip()
                cmd_id = str(cmd.get("id", "")).strip()
                if slash and cmd_id:
                    aliases.append((slash, cmd_id))
    except Exception:
        aliases = []

    if not aliases:
        aliases = [
            ("/sdd-diagnose", "sdd-diagnose"),
            ("/sdd-validate-governance", "sdd-validate-governance"),
            ("/sdd-stabilize", "sdd-stabilize"),
            ("/sdd-compress-context", "sdd-compress-context"),
            ("/sdd-review-architecture", "sdd-review-architecture"),
            ("/sdd-correct", "sdd-correct"),
            ("/sdd-converge", "sdd-converge"),
            ("/sdd-ask", "sdd-ask"),
            ("/sdd-organize", "sdd-organize"),
        ]

    alias_map = {slash: cmd_id for slash, cmd_id in aliases}
    return [(slash, cmd_id) for slash, cmd_id in alias_map.items()]


def _load_command_entries(output_dir: Path) -> list[dict[str, Any]]:
    """Load full command entries from canonical registry with safe fallback."""
    registry_path = output_dir / ".sdd" / "commands" / "registry.json"
    try:
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        commands = data.get("commands", [])
        if isinstance(commands, list):
            out: list[dict[str, Any]] = []
            for cmd in commands:
                if not isinstance(cmd, dict):
                    continue
                slash = str(cmd.get("slash", "")).strip()
                cmd_id = str(cmd.get("id", "")).strip()
                routes = cmd.get("routes_to", {})
                if slash and cmd_id and isinstance(routes, dict):
                    out.append(cmd)
            if out:
                return out
    except (OSError, ValueError):
        return _default_command_entries()

    # Fallback for early bootstrap without registry available.
    return _default_command_entries()


def _default_command_entries() -> list[dict[str, Any]]:
    """Return minimal command set used before registry generation."""
    return [
        {
            "id": "sdd-ask",
            "slash": "/sdd-ask",
            "routes_to": {"type": "cli", "command": "sdd ask"},
        },
        {
            "id": "sdd-organize",
            "slash": "/sdd-organize",
            "routes_to": {"type": "cli", "command": "sdd organize"},
        },
    ]


def _slash_aliases_markdown(aliases: list[tuple[str, str]]) -> str:
    """Return markdown table of slash aliases."""
    lines = [
        "## Slash aliases (`/sdd-*`)",
        "",
        "| Alias | Adapter target |",
        "|------|----------------|",
    ]
    for slash, cmd_id in aliases:
        lines.append(f"| `{slash}` | `.codex/skills/{cmd_id}.prompt.md` |")
    lines.append("")
    return "\n".join(lines)


def _prompt_spec_for_command(command: dict[str, Any]) -> tuple[str, str, str, str]:
    """Build prompt metadata/body from a canonical command entry."""
    slug = str(command.get("id", "")).strip()
    route = command.get("routes_to", {})
    route_type = str(route.get("type", "")).strip() if isinstance(route, dict) else ""

    if slug == "sdd-ask":
        return (
            slug,
            "Query SDD governance context",
            "agent",
            "Query the SDD governance context with the user's question.\n\n"
            'Execute in the terminal:\n```bash\nsdd runtime status\nsdd governance validate\nsdd ask --full "$QUERY"\n```\n\n'
            "Replace `$QUERY` with the user's question.\n\n"
            "HARD contract for this command:\n"
            "- Run preflight in order (`sdd runtime status` then `sdd governance validate`).\n"
            "- If preflight fails, do not continue; return governance-blocked status.\n"
            "- Only continue to `sdd ask --full` when preflight is healthy.\n"
            '- For large/noisy input, run `sdd organize "$QUERY"` first and consume indexed chunks only.\n\n'
            "Response contract:\n"
            "- Show `fingerprint`, `context_source`, and `mandates_loaded` from runtime output.\n"
            "- Treat `.sdd` runtime artifacts as source of truth for these fields.\n"
            + _ASK_500_FALLBACK_NOTE,
        )

    if slug == "sdd-organize":
        return (
            slug,
            "Prepare indexed context for large inputs",
            "agent",
            "Prepare large/noisy input before diagnosis or ask.\n\n"
            'Execute in the terminal:\n```bash\nsdd organize "$QUERY"\n```\n\n'
            "Use `.sdd/runtime/ask-intake/` artifacts for selective retrieval.",
        )

    if route_type == "cli" and isinstance(route, dict):
        cli_command = str(route.get("command", "")).strip()
        return (
            slug,
            f"Run {cli_command}",
            "agent",
            "Run the mapped SDD CLI command.\n\n"
            f"Execute in the terminal:\n```bash\n{cli_command}\n```\n",
        )

    if route_type == "skill" and isinstance(route, dict):
        skill_id = str(route.get("id", "")).strip()
        return (
            slug,
            f"Run governed skill {skill_id}",
            "agent",
            "Run the mapped governed skill through the runtime engine.\n\n"
            f"Execute in the terminal:\n```bash\nsdd skills run {skill_id}\n```\n",
        )

    return (
        slug,
        f"Run {slug}",
        "agent",
        "Run the mapped governed operation for this command as defined in `.sdd/commands/registry.json`.",
    )
