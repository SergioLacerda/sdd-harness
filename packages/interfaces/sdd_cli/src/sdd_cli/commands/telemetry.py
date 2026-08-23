"""sdd telemetry — inspect and manage local compliance-events telemetry."""

from __future__ import annotations

from pathlib import Path

import click
import typer

from sdd_cli.commands._telemetry_command_support import (
    abort_invalid_format,
    abort_workspace_resolution,
    emit_dump,
    emit_status,
)
from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.services.telemetry_handler import (
    _event_ts,  # noqa: F401  backward-compat re-export for unit tests
    _parse_ts,  # noqa: F401  backward-compat re-export for unit tests
    _read_events,
    build_status_data,
    filter_events,
)
from sdd_cli.utils.output import is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root
from sdd_core.governance.compliance_constants import resolve_compliance_log_override

__all__ = ["_event_ts", "_parse_ts"]

app = typer.Typer(
    help="Inspect and manage local telemetry events",
    invoke_without_command=True,
)


def _default_events_path() -> Path:
    override = resolve_compliance_log_override()
    if override.path is not None:
        return override.path
    try:
        root = resolve_workspace_root()
    except Exception as exc:
        raise RuntimeError("failed to resolve workspace root for telemetry") from exc
    return root / ".sdd" / "runtime" / "compliance-events.jsonl"


def _warn_if_telemetry_paths_diverge() -> None:
    """Soft-warn (stderr only) when the compliance-events path env vars diverge.

    ``SDD_COMPLIANCE_LOG``, ``SDD_COMPLIANCE_EVENTS_PATH`` (read by ``sdd ask``
    telemetry, see ``utils/telemetry_paths.resolve_compliance_events_path``),
    and ``SDD_TELEMETRY_PATH`` (read by this module's ``_default_events_path``)
    all resolve the same compliance-events JSONL path independently. If an
    operator sets only one, or sets more than one to the same value, there is
    nothing to compare. Only warn when at least two are explicitly set and
    resolve to different paths — never raise or change exit codes.
    """
    override = resolve_compliance_log_override()
    if not override.diverged_vars:
        return
    conflicts = ", ".join(
        f"{name} ({path})" for name, path in override.diverged_vars.items()
    )
    typer.echo(
        "WARN: telemetry event log paths diverge — "
        f"using {override.winner_var} ({override.path}), ignoring: {conflicts}; "
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


# Imported for its @app.command() registration side effect — query/summary/
# init live in telemetry_query.py (T13 split) but must be imported here so
# lazy command loading (which only imports `sdd_cli.commands.telemetry`)
# still registers them on `app`. Mirrors the existing `_ask_backend/__init__.py`
# pattern for `_ask_cmd_impl`.
from sdd_cli.commands import telemetry_query  # noqa: E402,F401
