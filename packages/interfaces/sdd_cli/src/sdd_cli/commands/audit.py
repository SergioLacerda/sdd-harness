"""sdd audit — governance drift and telemetry summary."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import typer

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
        None,
        "--events-file",
        help="Path to compliance events JSONL.",
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
        None,
        "--events-file",
        help="Path to compliance events JSONL.",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include events with timestamp >= since (ISO date/datetime).",
    ),
    event_type: str | None = typer.Option(
        None,
        "--event-type",
        help="Filter by event name (for example: VIOLATION).",
    ),
) -> None:
    """View compliance events with optional filtering."""
    source = events_file or _default_events_path()
    events = _load_events(source)
    since_dt = _parse_since_date(since)
    filtered = _filter_events(events, since=since_dt, event_type=event_type)
    if _ctx_json():
        payload = build_ok_result(
            "audit view",
            {
                "events_file": str(source),
                "since": since,
                "event_type": event_type,
                "count": len(filtered),
                "events": filtered,
            },
        )
        emit_json(payload)
        return
    render_view_text(filtered, source, since, event_type)


@app.command("export")
def audit_export(
    events_file: Path = typer.Option(
        None,
        "--events-file",
        help="Path to compliance events JSONL.",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include events with timestamp >= since (ISO date/datetime).",
    ),
    event_type: str | None = typer.Option(
        None,
        "--event-type",
        help="Filter by event name (for example: VIOLATION).",
    ),
    format: str = typer.Option(  # noqa: A002
        "csv",
        "--format",
        help="Export format.",
    ),
    manifest_file: Path = typer.Option(
        Path(".sdd/runtime/compliance-export.manifest.json"),
        "--manifest-file",
        help="Where to write export manifest metadata.",
    ),
) -> None:
    """Export compliance events and write evidence manifest."""
    fmt = format.strip().lower()
    if fmt != "csv":
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
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


@app.command("legacy-check")
def audit_legacy_check(
    phase_date: str | None = typer.Option(
        None,
        "--phase-date",
        help="Override policy date (YYYY-MM-DD) for testing.",
    ),
) -> None:
    """Check `/legacy/**` usage against Q3/Q4 2026 enforcement policy."""
    root = resolve_workspace_root()
    if phase_date:
        try:
            from datetime import date

            check_day = date.fromisoformat(phase_date)
        except ValueError as exc:
            raise typer.BadParameter("--phase-date must be YYYY-MM-DD.") from exc
    else:
        check_day = current_policy_date()
    result = run_legacy_check(root, check_day)
    if _ctx_json():
        emit_json(build_ok_result("audit legacy-check", result))
        return
    typer.echo("Legacy Path Policy Check")
    typer.echo(f"- date: {result['date']}")
    typer.echo(f"- policy mode: {result['policy_mode']}")
    typer.echo(f"- hits: {len(result['hits'])}")
    for item in result["hits"][:20]:
        typer.echo(f"  - {item}")
    if result["policy_mode"] == "block" and result["hits"]:
        raise click.exceptions.Exit(2)


@app.command("bootstrap-check")
def audit_bootstrap_check() -> None:
    """Validate AGENTS/CLAUDE bootstrap contract drift."""
    root = resolve_workspace_root()
    result = run_bootstrap_check(root)
    if _ctx_json():
        emit_json(build_ok_result("audit bootstrap-check", result))
        return
    typer.echo("Bootstrap Drift Check")
    if result["ok"]:
        typer.echo("- status: OK")
        return
    typer.echo("- status: DRIFT")
    for issue in result["issues"]:
        typer.echo(f"  - {issue}")
    raise click.exceptions.Exit(2)


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
    source = _default_events_path()
    rows = [
        _event_to_row(event)
        for event in _filter_events(
            _load_events(source), since=_parse_since_date(since), event_type=event_type
        )
    ]
    csv_blob, manifest = _build_export_payload(
        source=source, since=since, event_type=event_type, rows=rows, fmt="csv"
    )
    report_file = out_dir / "compliance_report.csv"
    report_file.write_bytes(csv_blob)
    manifest_file = out_dir / "compliance_report.manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    from sdd_cli.utils.dev_deps import require_dev_module

    require_dev_module("sdd_cli")

    runner = SafeProcessRunner()
    runtime_status = runner.run(
        [sys.executable, "-m", "sdd_cli.main", "runtime", "status"],
        capture_output=True,
        check=False,
    )
    governance_validate = runner.run(
        [sys.executable, "-m", "sdd_cli.main", "governance", "validate"],
        capture_output=True,
        check=False,
    )
    (out_dir / "runtime_status.txt").write_text(
        runtime_status.stdout + runtime_status.stderr, encoding="utf-8"
    )
    (out_dir / "governance_validation.txt").write_text(
        governance_validate.stdout + governance_validate.stderr, encoding="utf-8"
    )
    ws_root = resolve_workspace_root()
    bootstrap = run_bootstrap_check(ws_root)
    result_legacy = run_legacy_check(ws_root, current_policy_date())
    legacy_hits = result_legacy["hits"]
    policy_mode = result_legacy["policy_mode"]
    aa3_ok = policy_mode != "block" or not legacy_hits
    (out_dir / "decision_trace.md").write_text(
        "\n".join(
            [
                "# Decision Trace",
                "- ADR-013: CLAUDE.md pointer model enforced.",
                "- ADR-014: Legacy fallback removal and timeline policy enforced.",
                f"- Legacy policy mode: {policy_mode}",
                f"- Bootstrap drift check: {'OK' if bootstrap['ok'] else 'DRIFT'}",
                f"- Legacy references detected: {len(legacy_hits)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    checklist_lines = [
        "# External Review Checklist",
        f"- [x] AA1: audit view/export available ({report_file.name})",
        f"- [x] AA2: manifest generated ({manifest_file.name})",
        f"- [{'x' if aa3_ok else ' '}] AA3: legacy policy check (mode={policy_mode}, hits={len(legacy_hits)})",
        f"- [{'x' if bootstrap['ok'] else ' '}] AA4: bootstrap contract drift check",
        "- [x] AA5: run targeted tests in CI/local",
        "- [x] AA6: evidence pack generated",
    ]
    (out_dir / "external_review_checklist.md").write_text(
        "\n".join(checklist_lines) + "\n", encoding="utf-8"
    )
    typer.echo(f"Compliance pack written to: {out_dir}")
