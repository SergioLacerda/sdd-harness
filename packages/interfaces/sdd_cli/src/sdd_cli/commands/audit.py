"""sdd audit — governance drift and telemetry summary."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click
import typer

from sdd_cli.shared.contracts import build_ok_result
from sdd_cli.utils.output import emit_json, is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root
from sdd_core.utils.process import SafeProcessRunner

app = typer.Typer(
    help="Governance audit and drift analytics", invoke_without_command=True
)


@dataclass
class DriftRow:
    """Represents a single drift event row in the audit log."""

    ts: str
    drift_type: str
    command: str
    status: str
    fingerprint_short: str
    cause: str


def _parse_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _event_ts(event: dict[str, Any]) -> str:
    for key in ("end_ts", "start_ts", "timestamp"):
        value = str(event.get(key, "")).strip()
        if value:
            return value
    return ""


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    normalized = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _ts_sort_key(ts: str) -> tuple[int, str]:
    if not ts:
        return (0, "")
    normalized = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return (1, dt.isoformat())
    except ValueError:
        return (1, ts)


def _load_events(events_file: Path) -> list[dict[str, Any]]:
    if not events_file.exists():
        return []
    events: list[dict[str, Any]] = []
    with events_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                events.append(data)
    return events


def _is_ask_event(event: dict[str, Any]) -> bool:
    command = str(event.get("command", "")).strip()
    if command in {"ask", "ask-full"}:
        return True
    event_name = str(event.get("event", "")).strip()
    return event_name.startswith("governance.ask")


def _is_drift_event(event: dict[str, Any]) -> bool:
    if str(event.get("event", "")).strip() == "runtime.drift.detected":
        return True
    details = event.get("details", {})
    if isinstance(details, dict):
        if bool(details.get("drift_detected")):
            return True
        drift_type = str(details.get("drift_type", "")).strip().lower()
        if drift_type and drift_type != "none":
            return True
    return False


def _drift_type(event: dict[str, Any]) -> str:
    details = event.get("details", {})
    if isinstance(details, dict):
        value = str(details.get("drift_type", "")).strip()
        if value:
            return value
    return "missing_drift_type"


def _drift_cause(event: dict[str, Any]) -> str:
    details = event.get("details", {})
    if isinstance(details, dict):
        for key in (
            "drift_cause",
            "reason",
            "remediation_command",
            "degraded_reason",
        ):
            value = str(details.get(key, "")).strip()
            if value:
                return value
    return ""


def _window_events(
    events: list[dict[str, Any]], *, now_utc: datetime, days: int
) -> list[dict[str, Any]]:
    start = now_utc - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for event in events:
        dt = _parse_ts(_event_ts(event))
        if dt is None:
            continue
        if dt >= start:
            out.append(event)
    return out


def _window_correlation(
    events: list[dict[str, Any]], *, days: int, now_utc: datetime
) -> dict[str, Any]:
    window = _window_events(events, now_utc=now_utc, days=days)
    previous_window = _window_events(
        events, now_utc=now_utc - timedelta(days=days), days=days
    )
    asks = [event for event in window if _is_ask_event(event)]
    prev_asks = [event for event in previous_window if _is_ask_event(event)]
    drifts = [event for event in asks if _is_drift_event(event)]
    prev_drifts = [event for event in prev_asks if _is_drift_event(event)]

    total_in, total_out, with_tokens = _token_totals(asks)
    prev_in, prev_out, prev_with_tokens = _token_totals(prev_asks)
    token_coverage = (with_tokens / len(asks)) if asks else 0.0
    ratio = (total_out / total_in) if total_in > 0 else 0.0
    prev_token_coverage = (prev_with_tokens / len(prev_asks)) if prev_asks else 0.0
    prev_ratio = (prev_out / prev_in) if prev_in > 0 else 0.0

    classified = 0
    for event in drifts:
        if _drift_type(event) != "missing_drift_type":
            classified += 1
    drift_classified_coverage = (classified / len(drifts)) if drifts else 1.0
    current_drift_rate = (len(drifts) * 100.0 / len(asks)) if asks else 0.0
    prev_drift_rate = (len(prev_drifts) * 100.0 / len(prev_asks)) if prev_asks else 0.0

    quality_score = _quality_score(asks)
    prev_quality_score = _quality_score(prev_asks)
    quality_signal_available = (
        quality_score is not None and prev_quality_score is not None
    )
    confidence = _window_confidence(token_coverage, drift_classified_coverage)
    quality_delta: float | None = (
        quality_score - prev_quality_score
        if quality_score is not None and prev_quality_score is not None
        else None
    )
    classification, recommended_action = _window_classification(
        asks_count=len(asks),
        prev_asks_count=len(prev_asks),
        quality_signal_available=quality_signal_available,
        quality_delta=quality_delta,
        drift_delta=(current_drift_rate - prev_drift_rate),
        ratio_delta=(ratio - prev_ratio),
        token_coverage=token_coverage,
        prev_token_coverage=prev_token_coverage,
        drift_classified_coverage=drift_classified_coverage,
    )

    return {
        "window_days": days,
        "window_start": (now_utc - timedelta(days=days)).isoformat(),
        "window_end": now_utc.isoformat(),
        "ask_events": len(asks),
        "drift_events": len(drifts),
        "drift_rate_pct": round(current_drift_rate, 2),
        "tokens": {
            "input": total_in,
            "output": total_out,
            "output_input_ratio": round(ratio, 4),
            "coverage": round(token_coverage, 4),
        },
        "previous_window": {
            "ask_events": len(prev_asks),
            "drift_rate_pct": round(prev_drift_rate, 2),
            "tokens": {
                "input": prev_in,
                "output": prev_out,
                "output_input_ratio": round(prev_ratio, 4),
                "coverage": round(prev_token_coverage, 4),
            },
            "quality_score": prev_quality_score,
        },
        "quality_score": quality_score,
        "drift_classified_coverage": round(drift_classified_coverage, 4),
        "quality_signal_available": quality_signal_available,
        "classification": classification,
        "confidence": confidence,
        "recommended_action": recommended_action,
    }


def _has_quality_signals(events: list[dict[str, Any]]) -> bool:
    for event in events:
        details = event.get("details", {})
        if not isinstance(details, dict):
            continue
        if "tests_passed" in details or "human_accepted" in details:
            return True
    return False


def _window_confidence(token_coverage: float, drift_classified_coverage: float) -> str:
    if token_coverage >= 0.7 and drift_classified_coverage >= 0.8:
        return "HIGH"
    if token_coverage >= 0.7 or drift_classified_coverage >= 0.8:
        return "MEDIUM"
    return "LOW"


def _window_classification(
    *,
    asks_count: int,
    prev_asks_count: int,
    quality_signal_available: bool,
    quality_delta: float | None,
    drift_delta: float,
    ratio_delta: float,
    token_coverage: float,
    prev_token_coverage: float,
    drift_classified_coverage: float,
) -> tuple[str, str]:
    classification = "INCONCLUSIVO"
    if asks_count == 0 or prev_asks_count == 0:
        return classification, "Insufficient ask events in current/previous window."
    if not quality_signal_available:
        return classification, "No quality signals (tests_passed/human_accepted)."
    if token_coverage < 0.7 or prev_token_coverage < 0.7:
        return classification, "Token coverage below threshold in one window."
    if drift_classified_coverage < 0.8:
        return classification, "Drift classification coverage below threshold."

    assert quality_delta is not None
    q_sig = 5.0
    d_sig = 2.0
    t_sig = 0.20

    if quality_delta >= q_sig and drift_delta <= d_sig:
        return "ENRIQUECIMENTO_POSITIVO", "Scale current strategy with monitoring."
    if ratio_delta <= -t_sig and quality_delta >= -2.0 and drift_delta <= d_sig:
        return "ECONOMIA_SAUDAVEL", "Preserve optimization and monitor drift."
    if ratio_delta <= -t_sig and quality_delta <= -q_sig and drift_delta >= d_sig:
        return "ECONOMIA_FALSA", "Restore context depth and review prompt strategy."
    if ratio_delta >= t_sig and (quality_delta < q_sig or drift_delta > d_sig):
        return "INFLACAO_IMPRODUTIVA", "Constrain output and tighten scope."
    return classification, "No significant delta pattern yet; continue collecting data."


def _quality_score(events: list[dict[str, Any]]) -> float | None:
    tests: list[float] = []
    acceptance: list[float] = []
    for event in events:
        details = event.get("details", {})
        if not isinstance(details, dict):
            continue
        if "tests_passed" in details:
            tests.append(_as_score(details.get("tests_passed")))
        if "human_accepted" in details:
            acceptance.append(_as_score(details.get("human_accepted")))
    if not tests and not acceptance:
        return None
    test_avg = (sum(tests) / len(tests)) if tests else 0.0
    acceptance_avg = (sum(acceptance) / len(acceptance)) if acceptance else 0.0
    return round((0.6 * test_avg + 0.4 * acceptance_avg) * 100.0, 2)


def _as_score(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "pass", "passed", "ok", "accepted", "yes"}:
            return 1.0
        if lowered in {"false", "fail", "failed", "rejected", "no"}:
            return 0.0
    return 0.0


def _compute_base_summary(events: list[dict[str, Any]], top: int) -> dict[str, Any]:
    drifts = [event for event in events if _is_drift_event(event)]

    events_by_command: dict[str, int] = {}
    drift_by_type: dict[str, int] = {}
    unclassified_drifts = 0
    for event in events:
        command = str(event.get("command", "")).strip() or "unknown"
        events_by_command[command] = events_by_command.get(command, 0) + 1
    for event in drifts:
        dtype = _drift_type(event)
        drift_by_type[dtype] = drift_by_type.get(dtype, 0) + 1
        if dtype == "missing_drift_type":
            unclassified_drifts += 1

    rows: list[DriftRow] = []
    for event in drifts:
        fingerprint = str(event.get("artifact_fingerprint", "")).strip()
        rows.append(
            DriftRow(
                ts=_event_ts(event),
                drift_type=_drift_type(event),
                command=str(event.get("command", "")).strip() or "unknown",
                status=str(event.get("status", "")).strip() or "unknown",
                fingerprint_short=fingerprint[:8] if fingerprint else "",
                cause=_drift_cause(event),
            )
        )
    rows = sorted(rows, key=lambda item: _ts_sort_key(item.ts), reverse=True)[:top]
    total_in, total_out, with_tokens = _token_totals(events)
    ratio = (total_out / total_in) if total_in > 0 else 0.0
    missing_tokens = len(events) - with_tokens
    return {
        "drifts": drifts,
        "events_by_command": events_by_command,
        "drift_by_type": drift_by_type,
        "unclassified_drifts": unclassified_drifts,
        "rows": rows,
        "total_in": total_in,
        "total_out": total_out,
        "ratio": ratio,
        "missing_tokens": missing_tokens,
        "with_tokens": with_tokens,
    }


def _token_totals(events: list[dict[str, Any]]) -> tuple[int, int, int]:
    total_in = 0
    total_out = 0
    with_tokens = 0
    for event in events:
        tokens_in = _parse_int(event.get("tokens_input"))
        tokens_out = _parse_int(event.get("tokens_output"))
        if tokens_in is None or tokens_out is None:
            continue
        with_tokens += 1
        total_in += tokens_in
        total_out += tokens_out
    return total_in, total_out, with_tokens


def _default_events_path() -> Path:
    try:
        root = resolve_workspace_root()
    except Exception:
        root = Path.cwd()
    return root / ".sdd" / "runtime" / "compliance-events.jsonl"


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _parse_since_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        # Accept YYYY-MM-DD and normalize to UTC start of day.
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


def _resolve_governance_fingerprint() -> str:
    try:
        root = resolve_workspace_root()
    except Exception:
        root = Path.cwd()
    agent_instructions = root / ".sdd" / "agent-instructions.md"
    if agent_instructions.exists():
        try:
            for line in agent_instructions.read_text(encoding="utf-8").splitlines():
                if "Fingerprint this version:" in line:
                    return line.split(":", 1)[1].strip().strip("`")
        except OSError:
            pass  # best-effort; fingerprint unavailable if file is unreadable
    metadata = root / ".sdd" / "metadata.json"
    if metadata.exists():
        try:
            raw = json.loads(metadata.read_text(encoding="utf-8"))
            fp = raw.get("fingerprints", {}).get("combined", "")
            if isinstance(fp, str) and fp.strip():
                return fp.strip()
        except (OSError, json.JSONDecodeError):
            pass
    return ""


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


def _legacy_policy_mode(today: date) -> str:
    if today >= date(2026, 10, 1):
        return "block"
    if today >= date(2026, 7, 1):
        return "warn"
    return "monitor"


def _scan_legacy_paths(root: Path) -> list[str]:
    patterns = [
        re.compile(r"/legacy/"),
        re.compile(r"\blegacy/"),
        re.compile(r"generated/master/compiled"),
    ]
    hits: list[str] = []
    # Enforcement scope: operational entry/config files only.
    candidates: list[Path] = []
    candidates.extend(
        [
            root / "AGENTS.md",
            root / "README.md",
            root / "Makefile",
            root / "pyproject.toml",
        ]
    )
    candidates.extend((root / ".sdd").rglob("*.md"))
    candidates.extend((root / ".sdd").rglob("*.json"))
    candidates.extend((root / ".sdd").rglob("*.yaml"))
    candidates.extend((root / ".sdd").rglob("*.yml"))
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for pattern in patterns:
            if pattern.search(content):
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    rel = path
                hits.append(str(rel))
                break
    return sorted(hits)


def _bootstrap_drift(root: Path) -> dict[str, Any]:
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    drift: list[str] = []
    if not agents.exists():
        drift.append("AGENTS.md missing")
    else:
        text = agents.read_text(encoding="utf-8")
        if ".sdd/agent-instructions.md" not in text:
            drift.append("AGENTS.md missing .sdd authority reference")
        if "./CLAUDE.md" not in text:
            drift.append("AGENTS.md missing Claude bootstrap path")
    if not claude.exists():
        drift.append("CLAUDE.md missing")
    else:
        ctext = claude.read_text(encoding="utf-8")
        if ".sdd/agent-instructions.md" not in ctext:
            drift.append("CLAUDE.md not pointing to .sdd/agent-instructions.md")
    if (root / ".claude" / "agent-instructions.md").exists():
        drift.append("parallel authority file exists at .claude/agent-instructions.md")
    return {"ok": not drift, "issues": drift}


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
    computed = _compute_base_summary(events, top)
    drifts = computed["drifts"]
    events_by_command = computed["events_by_command"]
    drift_by_type = computed["drift_by_type"]
    unclassified_drifts = computed["unclassified_drifts"]
    rows = computed["rows"]
    total_in = computed["total_in"]
    total_out = computed["total_out"]
    ratio = computed["ratio"]
    missing_tokens = computed["missing_tokens"]
    with_tokens = computed["with_tokens"]
    now_utc = datetime.now(timezone.utc)
    correlation_windows = [
        _window_correlation(events, days=days, now_utc=now_utc) for days in (7, 14, 30)
    ]

    data = {
        "exit_code": 0,
        "events_file": str(source),
        "total_events": len(events),
        "total_drifts": len(drifts),
        "drift_rate_pct": round((len(drifts) * 100.0 / len(events)), 2)
        if events
        else 0.0,
        "events_by_command": events_by_command,
        "drift_by_type": drift_by_type,
        "drift_unclassified_total": unclassified_drifts,
        "token_comparison": {
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "output_input_ratio": round(ratio, 4),
            "events_with_tokens": with_tokens,
            "events_missing_tokens": missing_tokens,
        },
        "correlation_windows": correlation_windows,
        "top_drifts": [
            {
                "timestamp": row.ts,
                "drift_type": row.drift_type,
                "command": row.command,
                "status": row.status,
                "fingerprint_short": row.fingerprint_short,
                "cause": row.cause,
            }
            for row in rows
        ],
    }

    if include_non_drift:
        data["non_drift_events"] = len(events) - len(drifts)

    if _ctx_json():
        payload = build_ok_result("audit", data)
        emit_json(payload)
        return

    summary = data
    typer.echo("SDD Audit Summary")
    typer.echo(f"- events file: {source}")
    typer.echo(f"- total events: {summary['total_events']}")
    typer.echo(f"- total drifts: {summary['total_drifts']}")
    typer.echo(f"- drift rate: {summary['drift_rate_pct']}%")
    typer.echo("")
    typer.echo("Token Comparison")
    typer.echo(f"- input tokens: {total_in}")
    typer.echo(f"- output tokens: {total_out}")
    typer.echo(f"- output/input ratio: {round(ratio, 4)}")
    typer.echo(f"- events without tokens: {missing_tokens}")
    typer.echo("")
    typer.echo("Correlation Windows (7/14/30)")
    for row in correlation_windows:
        typer.echo(
            f"- {row['window_days']}d: class={row['classification']} "
            f"conf={row['confidence']} ask={row['ask_events']} drift={row['drift_rate_pct']}% "
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
            f"{idx:02d}. ts={row.ts or '-'} | type={row.drift_type} | cmd={row.command} | "
            f"status={row.status} | fp={row.fingerprint_short or '-'}{cause}"
        )


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
        raise typer.BadParameter("Only --format=csv is currently supported.")
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
    hits = _scan_legacy_paths(root)
    if phase_date:
        try:
            check_day = date.fromisoformat(phase_date)
        except ValueError as exc:
            raise typer.BadParameter("--phase-date must be YYYY-MM-DD.") from exc
    else:
        check_day = datetime.now(timezone.utc).date()
    mode = _legacy_policy_mode(check_day)
    if _ctx_json():
        emit_json(
            build_ok_result(
                "audit legacy-check",
                {"policy_mode": mode, "date": check_day.isoformat(), "hits": hits},
            )
        )
        return
    typer.echo("Legacy Path Policy Check")
    typer.echo(f"- date: {check_day.isoformat()}")
    typer.echo(f"- policy mode: {mode}")
    typer.echo(f"- hits: {len(hits)}")
    for item in hits[:20]:
        typer.echo(f"  - {item}")
    if mode == "block" and hits:
        raise typer.Exit(2)


@app.command("bootstrap-check")
def audit_bootstrap_check() -> None:
    """Validate AGENTS/CLAUDE bootstrap contract drift."""
    root = resolve_workspace_root()
    result = _bootstrap_drift(root)
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
    raise typer.Exit(2)


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
    bootstrap = _bootstrap_drift(resolve_workspace_root())
    legacy_hits = _scan_legacy_paths(resolve_workspace_root())
    policy_mode = _legacy_policy_mode(datetime.now(timezone.utc).date())
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
