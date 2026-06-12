"""sdd telemetry — inspect and manage local compliance-events telemetry."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import click
import typer

from sdd_cli.services.telemetry_handler import (
    _event_ts,  # noqa: F401  backward-compat re-export for unit tests
    _parse_ts,  # noqa: F401  backward-compat re-export for unit tests
    _read_events,
    apply_time_filter,
    build_init_result,
    build_status_data,
    filter_events,
)
from sdd_cli.shared.contracts import (
    build_error_result,
    build_ok_result,
)
from sdd_cli.utils.output import emit_json, is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root

__all__ = ["_event_ts", "_parse_ts"]

app = typer.Typer(
    help="Inspect and manage local telemetry events",
    invoke_without_command=True,
)


def _default_events_path() -> Path:
    env_path = os.environ.get("SDD_TELEMETRY_PATH", "").strip()
    if env_path:
        return Path(env_path)
    try:
        root = resolve_workspace_root()
    except Exception as exc:
        raise RuntimeError("failed to resolve workspace root for telemetry") from exc
    return root / ".sdd" / "runtime" / "compliance-events.jsonl"


def _resolve_events_path(command: str) -> Path:
    try:
        return _default_events_path()
    except RuntimeError as exc:
        if _ctx_json():
            payload = build_error_result(
                command,
                code="workspace_resolution_failed",
                message=str(exc),
                data={"exit_code": 1},
            )
            emit_json(payload, err=True)
        else:
            typer.echo(f"ERROR: {exc}", err=True)
            typer.echo(
                "Hint: set SDD_TELEMETRY_PATH to an explicit events file path.",
                err=True,
            )
        raise typer.Exit(1) from exc


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _abort_invalid_time_filter(field: str, value: str) -> None:
    """Report an invalid --since/--until value and raise typer.Exit(1)."""
    message = f"Invalid --{field} value: {value!r}"
    if _ctx_json():
        emit_json(
            build_error_result(
                "telemetry query",
                code=f"invalid_{field}",
                message=message,
                data={field: value, "exit_code": 1},
            ),
            err=True,
        )
        raise typer.Exit(1)
    typer.echo(message, err=True)
    raise typer.Exit(1)


@app.callback()
def telemetry_default(ctx: typer.Context) -> None:
    """Show telemetry status summary (default when no subcommand given)."""
    if ctx.invoked_subcommand is not None:
        return
    _print_status()


def _print_status() -> None:
    path = _resolve_events_path("telemetry status")
    data = build_status_data(path)

    if data["total_events"] == 0:
        if _ctx_json():
            payload = build_ok_result("telemetry status", {**data, "exit_code": 0})
            emit_json(payload)
            return
        typer.echo(f"No events found at {path}")
        hint = data.get("hint")
        if hint:
            typer.echo(f"Hint: {hint}")
        return

    if _ctx_json():
        payload = build_ok_result("telemetry status", {**data, "exit_code": 0})
        emit_json(payload)
        return

    typer.echo(f"File:         {data['events_file']}")
    typer.echo(f"Total events: {data['total_events']}")
    typer.echo(f"Errors:       {data['errors']}")
    typer.echo(f"First event:  {data['first_event']}")
    typer.echo(f"Last event:   {data['last_event']}")
    typer.echo("")
    typer.echo("Events by type:")
    for event_type, count in Counter(data["events_by_type"]).most_common():
        typer.echo(f"  {event_type:<35} {count}")


@app.command()
def status() -> None:
    """Show telemetry file status and event-type breakdown."""
    _print_status()


@app.command()
def dump(
    limit: int = typer.Option(
        50, "--limit", "-n", help="Max events to print (newest first)."
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", "-t", help="Filter by event_type (case-insensitive)."
    ),
    trace_id: str | None = typer.Option(None, "--trace-id", help="Filter by trace_id."),
    fmt: str = typer.Option(
        "jsonl", "--format", "-f", help="Output format: jsonl (default) or json array."
    ),
) -> None:
    """Dump raw telemetry events as JSON lines."""
    path = _resolve_events_path("telemetry dump")
    if fmt not in {"json", "jsonl"}:
        if _ctx_json():
            payload = build_error_result(
                "telemetry dump",
                code="invalid_format",
                message=f"Invalid --format value: {fmt!r}",
                data={"format": fmt, "exit_code": 1},
            )
            emit_json(payload, err=True)
        else:
            typer.echo(f"Invalid --format value: {fmt!r}", err=True)
        raise typer.Exit(1)
    events = _read_events(path)
    events = filter_events(events, event_type=event_type, trace_id=trace_id)

    selected = events[-limit:]
    if _ctx_json():
        data = {
            "events_file": str(path),
            "event_type": event_type,
            "trace_id": trace_id,
            "limit": limit,
            "returned": len(selected),
            "events": selected,
            "exit_code": 0,
        }
        payload = build_ok_result("telemetry dump", data)
        emit_json(payload)
        return

    if fmt == "json":
        typer.echo(json.dumps(selected, ensure_ascii=False))
    else:
        for event in selected:
            typer.echo(json.dumps(event, ensure_ascii=False))


@app.command()
def query(
    event_type: str | None = typer.Option(
        None, "--event-type", "-t", help="Filter by event_type (case-insensitive)."
    ),
    status_filter: str | None = typer.Option(
        None, "--status", "-s", help="Filter by status field (e.g. ok, warn, fail)."
    ),
    level: str | None = typer.Option(
        None, "--level", "-l", help="Filter by level field (e.g. INFO, ERROR)."
    ),
    trace_id: str | None = typer.Option(None, "--trace-id", help="Filter by trace_id."),
    since: str | None = typer.Option(
        None,
        "--since",
        "--from",
        help="ISO datetime lower bound, e.g. 2026-05-01 or 2026-05-01T00:00:00Z.",
    ),
    until: str | None = typer.Option(
        None,
        "--until",
        "--to",
        help="ISO datetime upper bound.",
    ),
    work_item: str | None = typer.Option(
        None, "--work-item", "-w", help="Filter by work_item_id."
    ),
    limit: int = typer.Option(100, "--limit", "-n", help="Max events to return."),
) -> None:
    """Query telemetry events with optional filters (all filters are AND)."""
    path = _resolve_events_path("telemetry query")
    events = _read_events(path)
    events = filter_events(
        events,
        event_type=event_type,
        status_filter=status_filter,
        level=level,
        trace_id=trace_id,
        work_item=work_item,
    )

    events, since_error, until_error = apply_time_filter(events, since, until)

    if since_error is not None:
        _abort_invalid_time_filter("since", since_error)
    if until_error is not None:
        _abort_invalid_time_filter("until", until_error)

    selected = events[-limit:]
    if _ctx_json():
        data = {
            "events_file": str(path),
            "event_type": event_type,
            "status_filter": status_filter,
            "level": level,
            "trace_id": trace_id,
            "since": since,
            "until": until,
            "work_item": work_item,
            "limit": limit,
            "matched": len(events),
            "returned": len(selected),
            "events": selected,
            "exit_code": 0,
        }
        payload = build_ok_result("telemetry query", data)
        emit_json(payload)
        return

    for event in selected:
        typer.echo(json.dumps(event, ensure_ascii=False))

    typer.echo(f"\n({len(events)} events matched)", err=True)


@app.command()
def init() -> None:
    """Initialize telemetry storage (.sdd/runtime/ dir + empty JSONL file)."""
    path = _resolve_events_path("telemetry init")
    result = build_init_result(path)
    invalid_line = result["invalid_line"]

    if result["created"]:
        if _ctx_json():
            data = {"events_file": str(path), **result, "exit_code": 0}
            emit_json(build_ok_result("telemetry init", data))
            return
        typer.echo(f"Created {path}")
        return

    if invalid_line is not None:
        if _ctx_json():
            data = {"events_file": str(path), **result, "exit_code": 1}
            emit_json(
                build_error_result(
                    "telemetry init",
                    code="invalid_jsonl",
                    message=f"Invalid JSON at line {invalid_line} in {path}",
                    data=data,
                ),
                err=True,
            )
            raise typer.Exit(1)
        typer.echo(f"Invalid JSON at line {invalid_line}: {path}", err=True)
        raise typer.Exit(1)

    if _ctx_json():
        data = {"events_file": str(path), **result, "exit_code": 0}
        emit_json(build_ok_result("telemetry init", data))
        return
    typer.echo(f"Already exists (valid): {path}")
