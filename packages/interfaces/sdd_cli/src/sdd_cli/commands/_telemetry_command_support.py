"""Rendering helpers for telemetry command output."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

import typer

from sdd_cli.shared.contracts import build_error_result, build_ok_result
from sdd_cli.utils.output import emit_json


def abort_invalid_time_filter(field: str, value: str, *, output_json: bool) -> None:
    message = f"Invalid --{field} value: {value!r}"
    if output_json:
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


def abort_invalid_format(fmt: str, *, output_json: bool) -> None:
    message = f"Invalid --format value: {fmt!r}"
    if output_json:
        emit_json(
            build_error_result(
                "telemetry dump",
                code="invalid_format",
                message=message,
                data={"format": fmt, "exit_code": 1},
            ),
            err=True,
        )
    else:
        typer.echo(message, err=True)
    raise typer.Exit(1)


def abort_workspace_resolution(
    command: str, exc: RuntimeError, *, output_json: bool
) -> NoReturn:
    if output_json:
        emit_json(
            build_error_result(
                command,
                code="workspace_resolution_failed",
                message=str(exc),
                data={"exit_code": 1},
            ),
            err=True,
        )
    else:
        typer.echo(f"ERROR: {exc}", err=True)
        typer.echo(
            "Hint: set SDD_TELEMETRY_PATH to an explicit events file path.",
            err=True,
        )
    raise typer.Exit(1) from exc


def emit_status(path: Path, data: dict[str, Any], *, output_json: bool) -> None:
    if data["total_events"] == 0:
        if output_json:
            emit_json(build_ok_result("telemetry status", {**data, "exit_code": 0}))
            return
        typer.echo(f"No events found at {path}")
        hint = data.get("hint")
        if hint:
            typer.echo(f"Hint: {hint}")
        return

    if output_json:
        emit_json(build_ok_result("telemetry status", {**data, "exit_code": 0}))
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


def emit_dump(
    path: Path,
    selected: list[dict[str, Any]],
    *,
    event_type: str | None,
    trace_id: str | None,
    limit: int,
    fmt: str,
    output_json: bool,
) -> None:
    if output_json:
        emit_json(
            build_ok_result(
                "telemetry dump",
                {
                    "events_file": str(path),
                    "event_type": event_type,
                    "trace_id": trace_id,
                    "limit": limit,
                    "returned": len(selected),
                    "events": selected,
                    "exit_code": 0,
                },
            )
        )
        return
    if fmt == "json":
        typer.echo(json.dumps(selected, ensure_ascii=False))
        return
    for event in selected:
        typer.echo(json.dumps(event, ensure_ascii=False))


def emit_query(
    path: Path,
    selected: list[dict[str, Any]],
    matched: int,
    *,
    event_type: str | None,
    status_filter: str | None,
    level: str | None,
    trace_id: str | None,
    since: str | None,
    until: str | None,
    work_item: str | None,
    limit: int,
    output_json: bool,
) -> None:
    if output_json:
        emit_json(
            build_ok_result(
                "telemetry query",
                {
                    "events_file": str(path),
                    "event_type": event_type,
                    "status_filter": status_filter,
                    "level": level,
                    "trace_id": trace_id,
                    "since": since,
                    "until": until,
                    "work_item": work_item,
                    "limit": limit,
                    "matched": matched,
                    "returned": len(selected),
                    "events": selected,
                    "exit_code": 0,
                },
            )
        )
        return
    for event in selected:
        typer.echo(json.dumps(event, ensure_ascii=False))
    typer.echo(f"\n({matched} events matched)", err=True)


def emit_init(path: Path, result: dict[str, Any], *, output_json: bool) -> None:
    invalid_line = result["invalid_line"]
    if result["created"]:
        if output_json:
            emit_json(
                build_ok_result(
                    "telemetry init",
                    {"events_file": str(path), **result, "exit_code": 0},
                )
            )
            return
        typer.echo(f"Created {path}")
        return

    if invalid_line is not None:
        if output_json:
            emit_json(
                build_error_result(
                    "telemetry init",
                    code="invalid_jsonl",
                    message=f"Invalid JSON at line {invalid_line} in {path}",
                    data={"events_file": str(path), **result, "exit_code": 1},
                ),
                err=True,
            )
            raise typer.Exit(1)
        typer.echo(f"Invalid JSON at line {invalid_line}: {path}", err=True)
        raise typer.Exit(1)

    if output_json:
        emit_json(
            build_ok_result(
                "telemetry init", {"events_file": str(path), **result, "exit_code": 0}
            )
        )
        return
    typer.echo(f"Already exists (valid): {path}")
