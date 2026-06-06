"""Analysis workspace commands — list, status, and clean analysis missions."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click
import typer

from sdd_cli.utils.output import emit_json, is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


app = typer.Typer(help="Analysis workspace management")


@app.callback(invoke_without_command=True)
def analysis_default(ctx: typer.Context) -> None:
    """List missions when called without a subcommand."""
    if ctx.invoked_subcommand is None:
        list_missions()


_STATES = ("todo", "pending", "refined", "done")
_DURATION_RE = re.compile(r"^(\d+)(d|h|m)$")


def _analysis_root(ws_root: Path) -> Path:
    return ws_root / ".sdd" / "analysis"


def _parse_duration(value: str) -> timedelta | None:
    m = _DURATION_RE.match(value.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "d":
        return timedelta(days=n)
    if unit == "h":
        return timedelta(hours=n)
    return timedelta(minutes=n)


def _collect_missions(analysis_root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {s: [] for s in _STATES}
    for state in _STATES:
        state_dir = analysis_root / state
        if not state_dir.exists():
            continue
        for p in sorted(state_dir.iterdir()):
            if p.is_file() and p.suffix == ".md":
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                result[state].append(
                    {
                        "mission_id": p.stem,
                        "file": str(p),
                        "date": mtime.date().isoformat(),
                        "state": state,
                    }
                )
    return result


@app.command("list")
def list_missions(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """List analysis missions grouped by state."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    missions = _collect_missions(_analysis_root(ws_root))

    if _ctx_json() or json_output:
        emit_json({"command": "analysis list", "ok": True, "data": missions})
        return

    any_mission = any(missions[s] for s in _STATES)
    if not any_mission:
        typer.echo("No analysis missions found.")
        return

    for state in _STATES:
        items = missions[state]
        typer.echo(f"\n[{state.upper()}]")
        if not items:
            typer.echo("  (empty)")
            continue
        for item in items:
            typer.echo(f"  {item['mission_id']}  {item['date']}")


@app.command("status")
def mission_status(
    mission_id: str = typer.Argument(..., help="Mission id to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Show phase, artifacts, and blockers for a mission."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    root = _analysis_root(ws_root)
    found: dict[str, Any] | None = None

    for state in _STATES:
        candidate = root / state / f"{mission_id}.md"
        if candidate.exists():
            found = {
                "mission_id": mission_id,
                "state": state,
                "artifact": str(candidate),
                "next_action": _next_action(state),
            }
            break

    if found is None:
        msg = f"Mission '{mission_id}' not found. Run `sdd analysis list` to see available missions."
        if _ctx_json() or json_output:
            emit_json(
                {
                    "command": "analysis status",
                    "ok": False,
                    "data": {},
                    "error": {"code": "mission_not_found", "message": msg},
                }
            )
        else:
            typer.echo(f"Error: {msg}", err=True)
        raise typer.Exit(1)

    if _ctx_json() or json_output:
        emit_json({"command": "analysis status", "ok": True, "data": found})
        return

    typer.echo(f"mission_id : {found['mission_id']}")
    typer.echo(f"state      : {found['state']}")
    typer.echo(f"artifact   : {found['artifact']}")
    typer.echo(f"next_action: {found['next_action']}")


def _collect_expired(done_dir: Path, cutoff: datetime, dry_run: bool) -> list[str]:
    removed: list[str] = []
    if not done_dir.exists():
        return removed
    for p in sorted(done_dir.iterdir()):
        if not p.is_file():
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            removed.append(str(p))
            if not dry_run:
                p.unlink()
    return removed


def _next_action(state: str) -> str:
    actions = {
        "todo": "move to pending when analysis begins",
        "pending": "discovery in progress — awaiting Ranger artifact",
        "refined": "plan ready — awaiting approval gate",
        "done": "mission complete",
    }
    return actions.get(state, "unknown")


@app.command("clean")
def clean_missions(
    older_than: str = typer.Option(
        "30d",
        "--older-than",
        help="Remove missions older than this duration (e.g. 30d, 7d, 12h)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without deleting"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Remove completed missions from done/ older than the given duration."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    delta = _parse_duration(older_than)
    if delta is None:
        typer.echo(
            f"Error: invalid duration '{older_than}'. Use format: 30d, 12h, 60m",
            err=True,
        )
        raise typer.Exit(1)

    done_dir = _analysis_root(ws_root) / "done"
    cutoff = datetime.now(tz=timezone.utc) - delta
    removed = _collect_expired(done_dir, cutoff, dry_run)

    count = len(removed)
    suffix = " (dry-run)" if dry_run else ""

    if _ctx_json() or json_output:
        emit_json(
            {
                "command": "analysis clean",
                "ok": True,
                "data": {
                    "removed": count,
                    "dry_run": dry_run,
                    "files": removed,
                },
            }
        )
        return

    typer.echo(f"{count} mission(s) removed{suffix}.")
    if dry_run and removed:
        for f in removed:
            typer.echo(f"  would remove: {f}")
