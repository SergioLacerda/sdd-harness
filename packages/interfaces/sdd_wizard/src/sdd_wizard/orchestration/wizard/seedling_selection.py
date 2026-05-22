"""Seedling selection prompt helpers for interactive wizard."""

from collections.abc import Callable

SEEDLINGS: list[tuple[str, str, str]] = [
    ("governance", "CORE", "GAP v1.0 auto-activation"),
    ("agent-prep", "CORE", "IDE integration hooks"),
    ("compliance", "CORE", "CI/CD + pre-commit"),
    ("claude", "AGENT/IDE", "Claude / Claude Code"),
    ("copilot", "AGENT/IDE", "GitHub Copilot"),
    ("cursor", "AGENT/IDE", "Cursor IDE"),
    ("vscode", "AGENT/IDE", "VS Code"),
    ("gemini", "AGENT/IDE", "Gemini"),
    ("cortex", "AGENT/IDE", "Snowflake Cortex Code"),
    ("activation-guide", "UTIL", "ACTIVATION_GUIDE.md"),
    ("verify", "UTIL", "verify.py"),
    ("prompt-commands", "UTIL", "prompt templates"),
]


def ask_seedling_selection(
    emitter: Callable[[str], None],
    prompter: Callable[[str], str] | None = None,
) -> set[str] | None:
    """Ask the user which seedlings to include. Returns None for all.

    Args:
        emitter: Output callback for display messages.
        prompter: Input callback for reading user input. Defaults to built-in
            ``input`` when None. Pass a custom callable in tests to avoid
            requiring a real TTY.
    """
    emitter("\n📦 Seedlings Selection")
    emitter("-" * 50)
    last_group = None
    for i, (key, group, desc) in enumerate(SEEDLINGS, start=1):
        if group != last_group:
            emitter(f"\n  {group}")
            last_group = group
        emitter(f"  [{i:2}] {key:<18} — {desc}")

    emitter("\n  Enter numbers separated by commas (e.g. 1,2,3,4)")
    emitter("  'all' or blank → generate all seedlings")
    _prompt = prompter if prompter is not None else input
    raw = _prompt("\n  Selection: ").strip()

    if not raw or raw.lower() == "all":
        emitter("  → Generating all seedlings")
        return None

    selected: set[str] = set()
    known = {seed[0] for seed in SEEDLINGS}
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(SEEDLINGS):
                selected.add(SEEDLINGS[idx][0])
            else:
                emitter(f"  ⚠️  Ignoring invalid index: {token}")
            continue
        if token in known:
            selected.add(token)
        else:
            emitter(f"  ⚠️  Unknown seedling key: {token}")

    if not selected:
        emitter("  ⚠️  No valid selection — generating all seedlings")
        return None

    emitter(f"  → Generating: {', '.join(sorted(selected))}")
    return selected
