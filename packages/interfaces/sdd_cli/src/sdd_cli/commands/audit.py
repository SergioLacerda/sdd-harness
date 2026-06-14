"""sdd audit — governance drift and telemetry summary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click
import typer

from sdd_cli.commands._audit_command_support import (
    emit_audit_view,
    emit_bootstrap_check,
    emit_legacy_check,
    resolve_phase_date,
    run_compliance_pack_workflow,
    write_export_manifest,
)
from sdd_cli.services.audit_formatters import (
    _build_export_payload,
    _ctx_json,
    _event_to_row,
    _filter_events,
    _parse_since_date,
    render_audit_text,
    render_view_text,
)
from sdd_cli.services.audit_runner import (
    _compute_base_summary,
    _default_events_path,
    _load_events,
    build_audit_summary_data,
)
from sdd_cli.services.audit_validators import (
    current_policy_date,
    run_bootstrap_check,
    run_legacy_check,
)
from sdd_cli.shared.contracts import build_ok_result
from sdd_cli.utils.output import emit_json
from sdd_cli.utils.sdd_authority import resolve_workspace_root
from sdd_core.utils.process import SafeProcessRunner

app = typer.Typer(
    help="Governance audit and drift analytics", invoke_without_command=True
)


@app.callback()
def audit_run(
    ctx: typer.Context,
    events_file: Path = typer.Option(
        None, "--events-file", help="Path to compliance events JSONL."
    ),
    top: int = typer.Option(10, "--top", min=1, help="Number of drift rows to show."),
    include_non_drift: bool = typer.Option(
        False,
        "--include-non-drift",
        help="Include non-drift events in JSON output diagnostics.",
    ),
) -> None:
    """Summarize governance stats, top drifts, and token input/output comparison."""
    if ctx.invoked_subcommand is not None:
        return
    source = events_file or _default_events_path()
    events = _load_events(source)
    now_utc = datetime.now(timezone.utc)
    data = build_audit_summary_data(events, top, now_utc, include_non_drift)
    data["events_file"] = str(source)

    if _ctx_json():
        emit_json(build_ok_result("audit", data))
        return

    computed = _compute_base_summary(events, top)
    render_audit_text(data, top, computed["rows"], source)


@app.command("view")
def audit_view(
    events_file: Path = typer.Option(
        None, "--events-file", help="Path to compliance events JSONL."
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include events with timestamp >= since (ISO date/datetime).",
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", help="Filter by event name (for example: VIOLATION)."
    ),
) -> None:
    """View compliance events with optional filtering."""
    source = events_file or _default_events_path()
    events = _load_events(source)
    since_dt = _parse_since_date(since)
    filtered = _filter_events(events, since=since_dt, event_type=event_type)
    emit_audit_view(
        source,
        filtered,
        since=since,
        event_type=event_type,
        output_json=_ctx_json(),
        render_view_text=render_view_text,
    )


@app.command("export")
def audit_export(
    events_file: Path = typer.Option(
        None, "--events-file", help="Path to compliance events JSONL."
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include events with timestamp >= since (ISO date/datetime).",
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", help="Filter by event name (for example: VIOLATION)."
    ),
    format: str = typer.Option("csv", "--format", help="Export format."),  # noqa: A002
    manifest_file: Path = typer.Option(
        Path(".sdd/runtime/compliance-export.manifest.json"),
        "--manifest-file",
        help="Where to write export manifest metadata.",
    ),
) -> None:
    """Export compliance events and write evidence manifest."""
    if (fmt := format.strip().lower()) != "csv":
        typer.echo("Only --format=csv is currently supported.")
        raise click.exceptions.Exit(2)
    source = events_file or _default_events_path()
    events = _load_events(source)
    since_dt = _parse_since_date(since)
    filtered = _filter_events(events, since=since_dt, event_type=event_type)
    rows = [_event_to_row(event) for event in filtered]
    csv_blob, manifest = _build_export_payload(
        source=source, since=since, event_type=event_type, rows=rows, fmt=fmt
    )
    # CSV data is emitted to stdout to support shell redirection.
    typer.echo(csv_blob.decode("utf-8"), nl=False)
    write_export_manifest(manifest_file, manifest)


@app.command("legacy-check")
def audit_legacy_check(
    phase_date: str | None = typer.Option(
        None, "--phase-date", help="Override policy date (YYYY-MM-DD) for testing."
    ),
) -> None:
    """Check `/legacy/**` usage against Q3/Q4 2026 enforcement policy."""
    root = resolve_workspace_root()
    emit_legacy_check(
        run_legacy_check(root, resolve_phase_date(phase_date, current_policy_date)),
        output_json=_ctx_json(),
    )


@app.command("bootstrap-check")
def audit_bootstrap_check() -> None:
    """Validate AGENTS/CLAUDE bootstrap contract drift."""
    root = resolve_workspace_root()
    emit_bootstrap_check(run_bootstrap_check(root), output_json=_ctx_json())


@app.command("compliance-pack")
def audit_compliance_pack(
    out_dir: Path = typer.Option(
        Path(".sdd/runtime/compliance-pack"),
        "--out-dir",
        help="Directory for external-review compliance artifacts.",
    ),
    since: str | None = typer.Option(
        None, "--since", help="Filter exported events since ISO date/datetime."
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", help="Filter exported events by event type."
    ),
) -> None:
    """Generate external-review compliance evidence bundle."""
    out_dir.mkdir(parents=True, exist_ok=True)
    from sdd_cli.utils.dev_deps import require_dev_module

    require_dev_module("sdd_cli")
    run_compliance_pack_workflow(
        out_dir,
        since=since,
        event_type=event_type,
        default_events_path=_default_events_path,
        load_events=_load_events,
        parse_since_date=_parse_since_date,
        filter_events=_filter_events,
        event_to_row=_event_to_row,
        build_export_payload=_build_export_payload,
        process_runner_cls=SafeProcessRunner,
        resolve_workspace_root=resolve_workspace_root,
        run_bootstrap_check=run_bootstrap_check,
        run_legacy_check=run_legacy_check,
        current_policy_date=current_policy_date,
    )
    typer.echo(f"Compliance pack written to: {out_dir}")
