"""Pure helper functions for test and CI-validate commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import typer


def _check_import(module: str) -> bool:
    """Try a real import (not just find_spec) to catch broken packages."""
    try:
        __import__(module)
        return True
    except Exception:
        return False


def _run_script(script_path: str, extra_args: list[str], cwd: str) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    # Match CI behavior on Windows consoles with limited encodings.
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run(
        [sys.executable, script_path] + extra_args,
        cwd=cwd,
        env=env,
    )
    return result.returncode


def _run_cli(args: list[str], cwd: str) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run([sys.executable, "-m", "sdd_cli"] + args, cwd=cwd, env=env)
    return result.returncode


def _run_pytest(args: list[str], cwd: str) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run([sys.executable, "-m", "pytest"] + args, cwd=cwd, env=env)
    return result.returncode


def _resolve_golden_path(root: Path) -> Path:
    return root / ".sdd" / "runtime" / "golden-ast.json"


def _find_artifact(root: Path) -> Path | None:
    """Return the compiled governance-core.json from canonical .sdd location."""
    candidate = root / ".sdd" / "compiled" / "governance-core.json"
    return candidate if candidate.exists() else None


def _save_golden(golden_path: Path, current_ast: Any) -> None:
    """Save the current AST as the golden snapshot."""
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(current_ast.to_json(), encoding="utf-8")
    typer.echo(f"Golden snapshot updated: {golden_path}")
    typer.echo(
        f"  Items: {len(current_ast.items)}, fingerprint: {current_ast.source_fingerprint[:12]}…"
    )


def _print_diff(diff: Any) -> None:
    """Print a formatted diff report of breaking/non-breaking/added changes."""
    if diff.breaking_changes:
        typer.echo(f"\n  BREAKING changes ({len(diff.breaking_changes)}):")
        for entry in diff.breaking_changes:
            typer.echo(
                f"    [{entry.item_id}] {entry.change_type}: {entry.before!r} → {entry.after!r}"
            )

    if diff.non_breaking_changes:
        typer.echo(f"\n  Non-breaking changes ({len(diff.non_breaking_changes)}):")
        for entry in diff.non_breaking_changes:
            field_info = f" ({entry.field})" if entry.field else ""
            typer.echo(
                f"    [{entry.item_id}]{field_info}: {entry.before!r} → {entry.after!r}"
            )

    if diff.added_items:
        typer.echo(f"\n  Added ({len(diff.added_items)}):")
        for entry in diff.added_items:
            typer.echo(f"    + [{entry.item_id}] {entry.after}")
