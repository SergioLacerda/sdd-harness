"""Shared utilities for agent seed and instruction document generation."""

from typing import Any


def _fingerprint_prefix(config: dict[str, Any], key: str, size: int = 32) -> str:
    """Return safe fingerprint prefix for template rendering."""
    value = config.get(key)
    if not value and key in {"core_fingerprint", "client_fingerprint"}:
        value = config.get("fingerprint")
    if not value:
        return "N/A"
    return str(value)[:size]


def _item_description(item: dict[str, Any]) -> str:
    """Return non-empty item description for instruction rendering."""
    desc = (
        str(item.get("description") or "").strip()
        or str(item.get("content") or "").strip()
        or str((item.get("metadata") or {}).get("description") or "").strip()
        or str(item.get("summary_minimal") or "").strip()
        or str(item.get("summary_runtime") or "").strip()
    )
    return desc or "(description unavailable)"


def _item_name(item: dict[str, Any]) -> str:
    """Return non-empty item display name, falling back to ID."""
    item_id = str(item.get("id", "")).strip()
    for key in ("name", "title"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return item_id


def _format_rules(rules: list[dict[str, Any]]) -> str:
    """Format rules as markdown list."""
    if not rules:
        return "No mandatory rules defined."

    formatted = []
    for i, rule in enumerate(rules, 1):
        name = rule.get("name", f"Rule {i}")
        description = rule.get("description", "No description")
        formatted.append(f"{i}. **{name}**: {description}")

    return "\n".join(formatted)


def _collect_instruction_sections(
    config: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Group governance items by semantic role for instruction rendering."""
    items: list[dict[str, Any]] = config.get("items", [])

    mandates: list[dict[str, Any]] = []
    guidelines: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for item in items:
        item_type = str(item.get("type", "")).upper()
        metadata_type = str(item.get("metadata", {}).get("type", "")).upper()
        criticality = str(item.get("metadata", {}).get("criticality", "")).upper()

        if item_type == "MANDATE" or metadata_type == "MANDATE":
            mandates.append(item)
        elif item_type in ("GUIDELINE", "RULE") or metadata_type in (
            "GUIDELINE",
            "RULE",
        ):
            guidelines.append(item)
        elif item_type == "DECISION" or metadata_type == "DECISION":
            decisions.append(item)
        elif criticality in ("MANDATORY", "HARD", "CRITICAL"):
            mandates.append(item)
        elif criticality in ("RECOMMENDED", "SOFT", "GUIDELINE"):
            guidelines.append(item)
        else:
            guidelines.append(item)

    return {
        "items": items,
        "mandates": mandates,
        "guidelines": guidelines,
        "decisions": decisions,
    }


def _render_claude_bootstrap_sections() -> list[str]:
    """Return Claude-specific bootstrap, quiz, and navigation sections."""
    return [
        "## Agent Entrypoint (Bootstrap)",
        "",
        "Every Claude session MUST follow this sequence:",
        "",
        "1. DISCOVERY     → Check `.sdd/profile` (governance exists?)",
        "2. HANDSHAKE     → Load indices, activate governance",
        "3. LOAD CORE     → mandates/index, policies/index, rules/index",
        "4. VERIFICATION  → Context Verification quiz (2 questions)",
        "5. TASK CLASS    → Classify work (PATH A/B/C/D)",
        "6. CONTEXT LOAD  → Load minimal context (strategy + budget)",
        "7. DECISION      → CONTEXT_SELECTION + EXECUTION_DECISION",
        "8. ANTI-PATTERN  → Validate no violations",
        "9. EXECUTE       → Mandates > Policies > Rules",
        "10. VALIDATE     → Compliance check",
        "11. OUTPUT       → [SDD STATUS] Governance: ACTIVE",
        "",
        "**Reference:** `.sdd/source/README.md`",
        "",
        "## Pre-Execution: The Two-Question Quiz",
        "",
        "BEFORE any research or action, ask:",
        "",
        "1. Do Governance Rules (`.sdd/source/`) already solve this?",
        "   - If YES → Apply and return. Don't proceed.",
        "   - If NO → Next question.",
        "",
        "2. Does the Local Cache (`.sdd/runtime/.sdd-cache.md`) already solve this?",
        "   - If YES → Use cached info and return.",
        "   - If NO → Only then expand context or research.",
        "",
        "**Reference:** `.sdd/source/README.md`",
        "",
        "## Optimized Context Loading from .sdd/",
        "",
        "Load context in this order (minimal to complete):",
        "",
        "**Level 1 (MUST HAVE):**",
        "- `.sdd/metadata.json` — Version, fingerprints, item counts",
        "- `.sdd/compiled/audit/metadata-core.json` — Core governance state",
        "- `CLAUDE.md` — This file (bootstrap sequence)",
        "",
        "**Level 2 (AS NEEDED):**",
        "- `.sdd/source/mandates/mandates.md` — Full mandate descriptions",
        "- `.sdd/source/README.md` — Pre-cache strategy",
        "",
        "**Level 3 (IF SPECIFIC):**",
        "- `.sdd/source/guidelines/guidelines.md`",
        "- `.sdd/source/mandates/mandates.md`",
        "- `.sdd/compiled/audit/metadata-client-template.json`",
        "",
        "**Agent Memory:** Store loaded context in `.claude/projects/*/memory/`",
        "- Avoids re-reading same artifacts",
        "- Helps subagents bootstrap faster",
        "",
        "## Git & Commit Protocol (P003 Enforcement)",
        "",
        'Golden Rule: "Agents propose, Humans dispose"',
        "",
        "1. Agent SUGGESTS complete command (code block)",
        "2. Agent NEVER executes git operations autonomously",
        "3. Human reviews diff + commit message",
        "4. Human executes or explicitly approves",
        "",
        "**Reference:** `.sdd/source/mandates/mandates.md`",
        "",
    ]


def render_agent_redirector(
    tool_name: str,
    header_lines: list[str],
    fingerprint: str,
    mandate_ids: list[str],
) -> str:
    """Render a lightweight governance redirector for an AI agent instruction file.

    Mirror of sdd_wizard._renderer.render_agent_redirector — keep output format in sync.
    Used by generate_agent_instruction_files() for all agents except Copilot.
    """
    ids_preview = ", ".join(mandate_ids[:5])
    if len(mandate_ids) > 5:
        ids_preview += ", ..."

    fp_lines = [
        f"# Governance fingerprint: {fingerprint[:16]}",
        f"# Active mandates: {len(mandate_ids)}"
        + (f" ({ids_preview})" if ids_preview else ""),
        "# Drift check: fingerprint must match .sdd/metadata.json → governance_fingerprint",
    ]

    lines: list[str] = list(header_lines) + fp_lines
    lines += [
        "",
        "## Agent Entrypoint",
        "",
        "Bootstrap sequence for this agent starts with `.sdd/agent-instructions.md`.",
        "",
        "## Entrypoint Contract",
        "",
        "1. You are under governance. Always resolve instructions from `.sdd`.",
        "   Initial reference: `.sdd/agent-instructions.md`",
        "",
        "## Commands And Skills (Source Of Truth)",
        "",
        "1. Commands source of truth: `.sdd/commands`.",
        "2. Skills source of truth: `.sdd/skills`.",
        "3. On startup, load:",
        "   - `.sdd/commands/registry.json`",
        "   - `.sdd/skills/registry.json`",
        "4. For each active command/skill in registries, read canonical files:",
        "   - Commands: `.sdd/commands/<command-id>/command.yaml`",
        "   - Skills: `.sdd/skills/<skill-name>/skill.yaml`",
        "5. Precedence rule:",
        "   - Local path is for context and ergonomics.",
        "   - `.sdd` is authoritative for routing/policy and wins conflicts.",
        "",
        "## One Rule",
        "",
        "**Before planning, coding, or deciding:** read `.sdd/agent-instructions.md`.",
        "",
        "## Quick Reference",
        "",
        "| File | Purpose |",
        "|------|---------|",
        "| `.sdd/agent-instructions.md` | **START HERE** — Complete agent bootstrap |",
        "| `.sdd/metadata.json` | Workspace version, fingerprints, item counts |",
        "| `.sdd/source/governance-core.json` | Human-readable mandates snapshot |",
        "| `.sdd/source/mandates/mandates.md` | Full mandate descriptions |",
        "",
        "## Validation",
        "",
        "Before finalizing changes, run:",
        "",
        "```bash",
        "sdd governance validate",
        "sdd runtime status",
        "```",
        "",
        "## Safe Fallback",
        "",
        "If registries or canonical files are missing/inconsistent, register bootstrap drift",
        "and continue in safe fallback mode without inventing missing rules.",
        "",
    ]
    return "\n".join(lines)


def _render_instruction_document(
    tool_name: str, header_lines: list[str], config: dict[str, Any]
) -> str:
    """Render a governance instruction document from compiled items.

    For Claude, adds bootstrap sequence, two-question quiz, context navigation,
    and git protocol sections derived from compiled governance artifacts.
    """
    sections = _collect_instruction_sections(config)
    mandates = sections["mandates"]
    guidelines = sections["guidelines"]
    decisions = sections["decisions"]

    lines: list[str] = list(header_lines)
    lines += [
        "",
        "## Workspace Governance",
        "",
        f"This {tool_name} workspace is governed by SDD compiled artifacts.",
        f"Core fingerprint: {_fingerprint_prefix(config, 'core_fingerprint', 16)}",
        f"Client fingerprint: {_fingerprint_prefix(config, 'client_fingerprint', 16)}",
        f"Items loaded: {len(sections['items'])}",
        "",
    ]

    if mandates:
        lines += [
            "## Mandatory Rules (MANDATES)",
            "",
            "These rules are immutable and must be enforced in every implementation:",
            "",
        ]
        for mandate in mandates:
            mid = mandate.get("id", "")
            name = _item_name(mandate) or mid
            desc = _item_description(mandate)
            lines.append(f"- **[{mid}] {name}**: {desc}")
        lines.append("")

    if guidelines:
        lines += ["## Guidelines (SOFT)", ""]
        for guideline in guidelines:
            gid = guideline.get("id", "")
            name = _item_name(guideline) or gid
            desc = _item_description(guideline)
            lines.append(f"- **[{gid}] {name}**: {desc}")
        lines.append("")

    if decisions:
        lines += ["## Architectural Decisions", ""]
        for decision in decisions:
            did = decision.get("id", "")
            name = _item_name(decision) or did
            status = decision.get("status", "")
            desc = _item_description(decision)
            status_tag = f" `{status}`" if status else ""
            lines.append(f"- **[{did}]{status_tag} {name}**: {desc}")
        lines.append("")

    if not (mandates or guidelines or decisions):
        lines += [
            "## Governance Context",
            "",
            "This workspace is governed by SDD (Spec Driven Development).",
            "Run `sdd governance compile` to build governance artifacts.",
            "",
        ]

    if tool_name == "Claude":
        lines += _render_claude_bootstrap_sections()

    lines += [
        "## Validation",
        "",
        "Run `sdd governance validate` before commits.",
        "Run `sdd runtime status` to check workspace health.",
        "",
    ]
    return "\n".join(lines)
