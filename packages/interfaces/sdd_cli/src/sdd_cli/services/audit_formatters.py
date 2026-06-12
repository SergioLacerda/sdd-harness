"""Audit output rendering, event filtering, and CSV export."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import typer

from sdd_cli.utils.output import is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _resolve_governance_fingerprint() -> str:
    try:
        root = resolve_workspace_root()
    except Exception:
        root = Path.cwd()
    agent_instructions = root / ".sdd" / "agent-instructions.md"
    if agent_instructions.exists():
        with contextlib.suppress(OSError):
            for line in agent_instructions.read_text(encoding="utf-8").splitlines():
                if "Fingerprint this version:" in line:
                    return line.split(":", 1)[1].strip().strip("`")
    metadata = root / ".sdd" / "metadata.json"
    if metadata.exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            raw = json.loads(metadata.read_text(encoding="utf-8"))
            fp = raw.get("fingerprints", {}).get("combined", "")
            if isinstance(fp, str) and fp.strip():
                return fp.strip()
    return ""


def _parse_since_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise typer.BadParameter(
            "--since must be ISO date (YYYY-MM-DD) or datetime."
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _filter_events(
    events: list[dict[str, Any]],
    *,
    since: datetime | None,
    event_type: str | None,
) -> list[dict[str, Any]]:
    from sdd_cli.services.audit_runner import _event_ts, _parse_ts, _ts_sort_key

    wanted_event = (event_type or "").strip().upper()
    out: list[dict[str, Any]] = []
    for event in events:
        if wanted_event:
            ev_name = str(event.get("event", "")).strip().upper()
            if ev_name != wanted_event:
                continue
        if since is not None:
            dt = _parse_ts(_event_ts(event))
            if dt is None or dt < since:
                continue
        out.append(event)
    return sorted(
        out,
        key=lambda item: (
            _ts_sort_key(_event_ts(item)),
            str(item.get("event", "")),
            str(item.get("command", "")),
        ),
    )


def _event_to_row(event: dict[str, Any]) -> dict[str, str]:
    from sdd_cli.services.audit_runner import _drift_cause, _event_ts, _parse_int

    details = event.get("details", {})
    if not isinstance(details, dict):
        details = {}
    return {
        "timestamp": _event_ts(event),
        "event": str(event.get("event", "")).strip(),
        "command": str(event.get("command", "")).strip(),
        "status": str(event.get("status", "")).strip(),
        "drift_type": str(details.get("drift_type", "")).strip(),
        "cause": _drift_cause(event),
        "artifact_fingerprint": str(event.get("artifact_fingerprint", "")).strip(),
        "tokens_input": str(_parse_int(event.get("tokens_input")) or ""),
        "tokens_output": str(_parse_int(event.get("tokens_output")) or ""),
    }


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    fieldnames = [
        "timestamp",
        "event",
        "command",
        "status",
        "drift_type",
        "cause",
        "artifact_fingerprint",
        "tokens_input",
        "tokens_output",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _build_export_payload(
    *,
    source: Path,
    since: str | None,
    event_type: str | None,
    rows: list[dict[str, str]],
    fmt: str,
) -> tuple[bytes, dict[str, Any]]:
    csv_blob = _csv_bytes(rows)
    sha256 = hashlib.sha256(csv_blob).hexdigest()
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "events_file": str(source),
        "format": fmt,
        "filters": {"since": since, "event_type": event_type},
        "count": len(rows),
        "governance_fingerprint": _resolve_governance_fingerprint(),
        "sha256": sha256,
    }
    return csv_blob, manifest


# ---------------------------------------------------------------------------
# Public rendering helpers
# ---------------------------------------------------------------------------


def render_audit_text(
    summary: dict[str, Any],
    top: int,
    rows: list[Any],
    source: Path,
) -> None:
    """Emit human-readable audit summary via typer.echo."""
    typer.echo("SDD Audit Summary")
    typer.echo(f"- events file: {source}")
    typer.echo(f"- total events: {summary['total_events']}")
    typer.echo(f"- total drifts: {summary['total_drifts']}")
    typer.echo(f"- drift rate: {summary['drift_rate_pct']}%")
    typer.echo("")
    typer.echo("Token Comparison")
    tc = summary["token_comparison"]
    typer.echo(f"- input tokens: {tc['total_input_tokens']}")
    typer.echo(f"- output tokens: {tc['total_output_tokens']}")
    typer.echo(f"- output/input ratio: {tc['output_input_ratio']}")
    typer.echo(f"- events without tokens: {tc['events_missing_tokens']}")
    typer.echo("")
    typer.echo("Correlation Windows (7/14/30)")
    for row in summary["correlation_windows"]:
        typer.echo(
            f"- {row['window_days']}d: class={row['classification']} "
            f"conf={row['confidence']} ask={row['ask_events']} "
            f"drift={row['drift_rate_pct']}% "
            f"ratio={row['tokens']['output_input_ratio']}"
        )
    typer.echo("")
    typer.echo(f"Top {top} Drift Events")
    if not rows:
        typer.echo("- no drift events found")
        return
    for idx, row in enumerate(rows, start=1):
        cause = f" | cause={row.cause}" if row.cause else ""
        typer.echo(
            f"{idx:02d}. ts={row.ts or '-'} | type={row.drift_type} | "
            f"cmd={row.command} | status={row.status} | "
            f"fp={row.fingerprint_short or '-'}{cause}"
        )


def render_view_text(
    filtered: list[dict[str, Any]],
    source: Path,
    since: str | None,
    event_type: str | None,
) -> None:
    """Emit human-readable view output via typer.echo."""
    typer.echo("SDD Compliance Event Viewer")
    typer.echo(f"- events file: {source}")
    typer.echo(f"- matched events: {len(filtered)}")
    if since:
        typer.echo(f"- since: {since}")
    if event_type:
        typer.echo(f"- event type: {event_type}")
    typer.echo("")
    if not filtered:
        typer.echo("- no events matched")
        return
    for idx, event in enumerate(filtered, start=1):
        row = _event_to_row(event)
        typer.echo(
            f"{idx:03d}. ts={row['timestamp'] or '-'} | event={row['event'] or '-'} | "
            f"cmd={row['command'] or '-'} | status={row['status'] or '-'}"
        )
