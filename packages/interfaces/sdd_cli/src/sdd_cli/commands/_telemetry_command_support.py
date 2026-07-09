"""Rendering helpers for telemetry command output."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import typer
from sdd_runtime.metrics import AskLatencyCollector

from sdd_cli.commands._telemetry_command_validation import (
    abort_invalid_format,
    abort_invalid_time_filter,
    abort_workspace_resolution,
)
from sdd_cli.shared.contracts import build_error_result, build_ok_result
from sdd_cli.utils.output import emit_json

__all__ = [
    "abort_invalid_format",
    "abort_invalid_time_filter",
    "abort_workspace_resolution",
    "emit_dump",
    "emit_init",
    "emit_query",
    "emit_status",
    "emit_summary",
]


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


def emit_summary(
    path: Path,
    events: list[dict[str, Any]],
    *,
    phase_id: str | None,
    latency_domain: str | None,
    path_id: str | None,
    output_json: bool,
) -> None:
    collector = AskLatencyCollector()
    for event in events:
        collector.ingest(event)
    snapshot = collector.snapshot()

    groups = [
        {
            "phase_id": key[0],
            "latency_domain": key[1],
            "path_id": key[2],
            "count": group.count,
            "min_ms": group.min_ms,
            "max_ms": group.max_ms,
            "avg_ms": group.avg_ms,
            "p50_ms": group.p50_ms,
            "p95_ms": group.p95_ms,
        }
        for key, group in snapshot.groups.items()
    ]

    if output_json:
        emit_json(
            build_ok_result(
                "telemetry summary",
                {
                    "events_file": str(path),
                    "phase_id": phase_id,
                    "latency_domain": latency_domain,
                    "path_id": path_id,
                    "groups": groups,
                    "exit_code": 0,
                },
            )
        )
        return

    if not groups:
        typer.echo(f"No governance.ask.phase events found at {path}")
        return

    typer.echo(
        f"{'phase_id':<28} {'latency_domain':<16} {'path_id':<10} "
        f"{'count':>6} {'min_ms':>8} {'avg_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'max_ms':>8}"
    )
    for row in groups:
        typer.echo(
            f"{row['phase_id']:<28} {row['latency_domain']:<16} {row['path_id']:<10} "
            f"{row['count']:>6} {row['min_ms']:>8} {row['avg_ms']:>8.1f} "
            f"{row['p50_ms']:>8} {row['p95_ms']:>8} {row['max_ms']:>8}"
        )


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
