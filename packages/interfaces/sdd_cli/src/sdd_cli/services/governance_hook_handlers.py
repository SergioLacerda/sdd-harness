"""Handlers for `sdd governance hook status|disable|enable`.

Deliberately dependency-light: only stdlib + `sdd_core.utils.environment`.
This command must keep working to disable the prompt-submit governance hook
even when the rest of the `sdd` CLI (governance loading, msgpack compilation)
is what's broken — that's the exact scenario it exists to rescue.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

HOOK_SENTINEL_RELATIVE = Path(".sdd") / "runtime" / "hook-disabled"

_PLATFORM_HOOK_FILES = {
    "claude": Path(".claude") / "sdd-governance-inject.py",
    "codex": Path(".codex") / "sdd-governance-inject.py",
    "gemini": Path(".gemini") / "sdd-governance-inject.py",
}


def _resolve_root() -> Path:
    from sdd_core.utils.environment import find_workspace_root

    return find_workspace_root() or Path.cwd()


def run_governance_hook_disable(*, console: Console) -> None:
    """Create the hook-disabled sentinel, stopping the prompt-submit hook."""
    sentinel = _resolve_root() / HOOK_SENTINEL_RELATIVE
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("", encoding="utf-8")
    console.print("[yellow]Governance prompt-submit hook disabled.[/yellow]")
    console.print(f"  sentinel: {sentinel}")
    console.print("  run 'sdd governance hook enable' to restore it")


def run_governance_hook_enable(*, console: Console) -> None:
    """Remove the hook-disabled sentinel, restoring the prompt-submit hook."""
    sentinel = _resolve_root() / HOOK_SENTINEL_RELATIVE
    sentinel.unlink(missing_ok=True)
    console.print("[green]Governance prompt-submit hook enabled.[/green]")


def run_governance_hook_status(*, console: Console) -> None:
    """Report sentinel state and, best-effort, per-platform hook file presence."""
    root = _resolve_root()
    sentinel = root / HOOK_SENTINEL_RELATIVE
    if sentinel.exists():
        console.print("[yellow]Governance prompt-submit hook: disabled[/yellow]")
    else:
        console.print("[green]Governance prompt-submit hook: enabled[/green]")

    for platform, relative_path in _PLATFORM_HOOK_FILES.items():
        try:
            present = (root / relative_path).exists()
        except OSError:
            present = None
        state = "configured" if present else "not configured"
        if present is None:
            state = "unknown"
        console.print(f"  {platform}: {state}")
