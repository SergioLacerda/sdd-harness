"""CLI prompt/command file generators for all supported AI tools."""

import contextlib
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
            ("/sdd-ask-full", "sdd-ask-full"),
            ("/sdd-organize", "sdd-organize"),
        ]

    alias_map = {slash: cmd_id for slash, cmd_id in aliases}
    alias_map.setdefault("/sdd-ask-full", "sdd-ask-full")
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
                return _ensure_compat_command_entries(out)
    except (OSError, ValueError):
        return _ensure_compat_command_entries(_default_command_entries())

    # Fallback for early bootstrap without registry available.
    return _ensure_compat_command_entries(_default_command_entries())


def _ensure_compat_command_entries(
    commands: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ensure compatibility aliases remain available in generated prompts."""
    by_id = {
        str(command.get("id", "")).strip(): command
        for command in commands
        if isinstance(command, dict)
    }
    by_id.setdefault(
        "sdd-ask-full",
        {
            "id": "sdd-ask-full",
            "slash": "/sdd-ask-full",
            "routes_to": {"type": "cli", "command": 'sdd ask --full "$QUERY"'},
        },
    )
    return list(by_id.values())


def _default_command_entries() -> list[dict[str, Any]]:
    """Return minimal command set used before registry generation."""
    return [
        {
            "id": "sdd-ask",
            "slash": "/sdd-ask",
            "routes_to": {"type": "cli", "command": "sdd ask"},
        },
        {
            "id": "sdd-ask-full",
            "slash": "/sdd-ask-full",
            "routes_to": {"type": "cli", "command": 'sdd ask --full "$QUERY"'},
        },
        {
            "id": "sdd-organize",
            "slash": "/sdd-organize",
            "routes_to": {"type": "cli", "command": "sdd organize"},
        },
    ]


def _slash_aliases_markdown(aliases: list[tuple[str, str]]) -> str:
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

    if slug == "sdd-ask-full":
        return (
            slug,
            "Query SDD governance context (full output)",
            "agent",
            "Query the SDD governance context with the user's question.\n\n"
            'Execute in the terminal:\n```bash\nsdd runtime status\nsdd governance validate\nsdd ask --full "$QUERY"\n```\n\n'
            "Replace `$QUERY` with the user's question.\n\n"
            "Response contract:\n"
            "- Use the canonical full-output path via `sdd ask --full`.\n"
            "- Do not emit duplicated `ask-full` invocations.\n"
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


def _write_copilot_prompts(
    prompts_dir: Path, command_entries: list[dict[str, Any]]
) -> list[tuple[str, Path]]:
    """Write VS Code Copilot slash-command prompt files."""
    prompts_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, Path]] = []
    for command in command_entries:
        slug, description, mode, body = _prompt_spec_for_command(command)
        target = prompts_dir / f"{slug}.prompt.md"
        content = (
            f"---\ndescription: {description}\nmode: {mode}\n---\n\n"
            f"{body}\n{_SOFT_GOVERNANCE_CHECK}{_AUDIT_JSON_NOTE}\n"
        )
        target.write_text(content, encoding="utf-8")
        written.append((f"Copilot/{slug}", target))
    return written


def _write_cursor_commands(cursor_rules_dir: Path) -> tuple[str, Path]:
    """Write Cursor commands rule file."""
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_commands = cursor_rules_dir / "sdd-commands.mdc"
    cursor_commands.write_text(
        "---\n"
        "description: SDD CLI commands — invoked when user asks to run tests, lint, governance, etc.\n"
        "globs: ['**/*']\n"
        "alwaysApply: false\n"
        "---\n\n"
        "# SDD CLI Commands\n\n"
        "When the user asks to run tests, lint, check governance, or diagnose the workspace, "
        "use the following SDD CLI commands in the terminal:\n\n"
        + _COMMANDS_TABLE
        + "\n"
        + _RUNTIME_STATUS_NOTE,
        encoding="utf-8",
    )
    cursor_commands.write_text(
        cursor_commands.read_text(encoding="utf-8")
        + _SOFT_GOVERNANCE_CHECK
        + _AUDIT_JSON_NOTE,
        encoding="utf-8",
    )
    return ("Cursor/sdd-commands", cursor_commands)


def _write_gemini_files(gemini_dir: Path) -> list[tuple[str, Path]]:
    """Write Gemini CLI commands and settings files."""
    gemini_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, Path]] = []

    gemini_commands = gemini_dir / "commands.md"
    gemini_commands.write_text(
        "# SDD CLI Commands for Gemini\n\n"
        "Use these commands when asked to run tests, lint, or manage governance:\n\n"
        + _COMMANDS_TABLE
        + "\n"
        + _RUNTIME_STATUS_NOTE,
        encoding="utf-8",
    )
    gemini_commands.write_text(
        gemini_commands.read_text(encoding="utf-8")
        + _SOFT_GOVERNANCE_CHECK
        + _AUDIT_JSON_NOTE,
        encoding="utf-8",
    )
    written.append(("Gemini/commands.md", gemini_commands))

    gemini_settings = gemini_dir / "settings.json"
    _existing: dict[str, Any] = {}
    if gemini_settings.exists():
        with contextlib.suppress(Exception):
            _existing = _json.loads(gemini_settings.read_text(encoding="utf-8"))
    _existing["promptFiles"] = [".gemini/commands.md"]
    gemini_settings.write_text(_json.dumps(_existing, indent=2), encoding="utf-8")
    written.append(("Gemini/settings.json", gemini_settings))

    return written


def _write_codex_commands(
    codex_dir: Path, aliases: list[tuple[str, str]]
) -> tuple[str, Path]:
    """Write Codex slash aliases manifest."""
    codex_dir.mkdir(parents=True, exist_ok=True)
    codex_commands = codex_dir / "commands.md"
    codex_commands.write_text(
        "# SDD Commands for Codex\n\n"
        "Entrypoint contract:\n"
        "1. You must learn commands and skills from your custom folder path:\n"
        "   - `.codex/commands.md`\n"
        "   - `.codex/skills/`\n"
        "2. You are under governance. Always resolve instructions from `.sdd`.\n"
        "   Initial reference: `.sdd/agent-instructions.md`\n\n"
        "Use the aliases below as slash commands and route each one to its generated adapter.\n\n"
        + _slash_aliases_markdown(aliases)
        + "\n"
        + "Notes:\n"
        + "- Canonical commands registry: `.sdd/commands/registry.json`\n"
        + "- Canonical skills registry: `.sdd/skills/registry.json`\n",
        encoding="utf-8",
    )
    codex_commands.write_text(
        codex_commands.read_text(encoding="utf-8")
        + _SOFT_GOVERNANCE_CHECK
        + _AUDIT_JSON_NOTE,
        encoding="utf-8",
    )
    return ("Codex/commands.md", codex_commands)


def generate_agent_prompt_commands(
    output_dir: Path,
    config: dict[str, Any] | None = None,
) -> list[tuple[str, Path]]:
    """Generate CLI prompt/command files for all supported AI tools.

    These files let users invoke SDD CLI commands natively from each tool:
    - VS Code Copilot: .github/prompts/*.prompt.md  (slash commands /sdd-*)
    - Cursor:          .cursor/rules/sdd-commands.mdc
    - Gemini CLI:      .gemini/commands.md + .gemini/settings.json

    NOTE: CLAUDE.md is generated exclusively by ai_seeds.py:generate_claude_seed()
    to ensure single source of truth.

    Args:
        output_dir: Workspace root directory.
        config: Unused (kept for API compatibility).

    Returns:
        List of (label, path) for each written file.
    """
    written: list[tuple[str, Path]] = []

    command_entries = _load_command_entries(output_dir)
    aliases = _load_slash_aliases(output_dir)
    written += _write_copilot_prompts(
        output_dir / ".github" / "prompts", command_entries
    )
    written.append(_write_cursor_commands(output_dir / ".cursor" / "rules"))
    written.append(_write_codex_commands(output_dir / ".codex", aliases))
    # NOTE: CLAUDE.md is now generated exclusively by ai_seeds.py:generate_claude_seed()
    # to ensure single source of truth and prevent duplication.
    written += _write_gemini_files(output_dir / ".gemini")
    return written
