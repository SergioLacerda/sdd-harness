"""sdd telemetry — inspect and manage local compliance-events telemetry."""

from __future__ import annotations

import os
from pathlib import Path

import click
import typer

from sdd_cli.commands._telemetry_command_support import (
    abort_invalid_format,
    abort_invalid_time_filter,
    abort_workspace_resolution,
    emit_dump,
    emit_init,
    emit_query,
    emit_status,
    emit_summary,
)
from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.services.telemetry_handler import (
    _event_ts,  # noqa: F401  backward-compat re-export for unit tests
    _parse_ts,  # noqa: F401  backward-compat re-export for unit tests
    _read_events,
    apply_time_filter,
    build_init_result,
    build_status_data,
    filter_events,
)
from sdd_cli.utils.output import is_json_mode
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


def _warn_if_telemetry_paths_diverge() -> None:
    """Soft-warn (stderr only) when the two telemetry path env overrides diverge.

    ``SDD_COMPLIANCE_EVENTS_PATH`` (read by ``sdd ask`` telemetry, see
    ``utils/telemetry_paths.resolve_compliance_events_path``) and
    ``SDD_TELEMETRY_PATH`` (read by this module's ``_default_events_path``)
    resolve the compliance-events JSONL path independently. If an operator
    sets only one, or sets both to the same value, there is nothing to
    compare. Only warn when both are explicitly set and resolve to
    different absolute paths — never raise or change exit codes.
    """
    compliance_raw = os.environ.get("SDD_COMPLIANCE_EVENTS_PATH", "").strip()
    telemetry_raw = os.environ.get("SDD_TELEMETRY_PATH", "").strip()
    if not compliance_raw or not telemetry_raw:
        return
    compliance_path = Path(compliance_raw).expanduser().resolve()
    telemetry_path = Path(telemetry_raw).expanduser().resolve()
    if compliance_path != telemetry_path:
        typer.echo(
            "WARN: telemetry event log paths diverge — "
            f"SDD_COMPLIANCE_EVENTS_PATH ({compliance_path}) != "
            f"SDD_TELEMETRY_PATH ({telemetry_path}); "
            "sdd ask and sdd telemetry may read/write different event logs.",
            err=True,
        )


def _resolve_events_path(command: str) -> Path:
    _warn_if_telemetry_paths_diverge()
    try:
        return _default_events_path()
    except RuntimeError as exc:
        abort_workspace_resolution(command, exc, output_json=_ctx_json())


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


@app.callback()
def telemetry_default(
    ctx: typer.Context,
    list_commands: bool = typer.Option(
        False, "--list", help="List telemetry commands."
    ),
) -> None:
    """Show telemetry status summary (default when no subcommand given)."""
    if ctx.invoked_subcommand is not None:
        return
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Telemetry", ["status", "dump", "query", "summary", "init"])
        raise typer.Exit(0)


def _print_status() -> None:
    path = _resolve_events_path("telemetry status")
    emit_status(path, build_status_data(path), output_json=_ctx_json())


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
        abort_invalid_format(fmt, output_json=_ctx_json())
    events = _read_events(path)
    events = filter_events(events, event_type=event_type, trace_id=trace_id)
    emit_dump(
        path,
        events[-limit:],
        event_type=event_type,
        trace_id=trace_id,
        limit=limit,
        fmt=fmt,
        output_json=_ctx_json(),
    )


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
        abort_invalid_time_filter("since", since_error, output_json=_ctx_json())
    if until_error is not None:
        abort_invalid_time_filter("until", until_error, output_json=_ctx_json())
    emit_query(
        path,
        events[-limit:],
        len(events),
        event_type=event_type,
        status_filter=status_filter,
        level=level,
        trace_id=trace_id,
        since=since,
        until=until,
        work_item=work_item,
        limit=limit,
        output_json=_ctx_json(),
    )


@app.command()
def summary(
    phase_id: str | None = typer.Option(
        None, "--phase-id", help="Filter by details.phase_id."
    ),
    latency_domain: str | None = typer.Option(
        None, "--latency-domain", help="Filter by details.latency_domain."
    ),
    path_id: str | None = typer.Option(None, "--path-id", help="Filter by path_id."),
) -> None:
    """Aggregate governance.ask.phase events into per-phase latency statistics."""
    path = _resolve_events_path("telemetry summary")
    events = _read_events(path)
    events = filter_events(
        events,
        event_type="governance.ask.phase",
        phase_id=phase_id,
        latency_domain=latency_domain,
        path_id=path_id,
    )
    emit_summary(
        path,
        events,
        phase_id=phase_id,
        latency_domain=latency_domain,
        path_id=path_id,
        output_json=_ctx_json(),
    )


@app.command()
def init() -> None:
    """Initialize telemetry storage (.sdd/runtime/ dir + empty JSONL file)."""
    path = _resolve_events_path("telemetry init")
    emit_init(path, build_init_result(path), output_json=_ctx_json())
