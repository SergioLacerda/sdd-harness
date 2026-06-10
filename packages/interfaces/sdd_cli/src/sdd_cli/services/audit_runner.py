"""Audit analytics: window classification, correlation, summary aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sdd_cli.services.audit_event_parser import (
    DriftRow,  # noqa: F401 — backward-compat re-export
    _as_score,  # noqa: F401 — backward-compat re-export
    _drift_cause,  # noqa: F401 — backward-compat re-export
    _drift_type,  # noqa: F401 — backward-compat re-export
    _event_ts,  # noqa: F401 — backward-compat re-export
    _has_quality_signals,  # noqa: F401 — backward-compat re-export
    _is_ask_event,
    _is_drift_event,
    _load_events,  # noqa: F401 — backward-compat re-export
    _parse_int,  # noqa: F401 — backward-compat re-export
    _parse_ts,  # noqa: F401 — backward-compat re-export
    _quality_score,
    _token_totals,
    _ts_sort_key,  # noqa: F401 — backward-compat re-export
    _window_events,
)
from sdd_cli.utils.sdd_authority import resolve_workspace_root


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
        from sdd_cli.services.audit_event_parser import _drift_type as _dt

        if _dt(event) != "missing_drift_type":
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


def _compute_base_summary(events: list[dict[str, Any]], top: int) -> dict[str, Any]:
    from sdd_cli.services.audit_event_parser import _drift_cause as _dc
    from sdd_cli.services.audit_event_parser import _drift_type as _dt
    from sdd_cli.services.audit_event_parser import _event_ts as _ets
    from sdd_cli.services.audit_event_parser import _ts_sort_key as _tsk

    drifts = [event for event in events if _is_drift_event(event)]

    events_by_command: dict[str, int] = {}
    drift_by_type: dict[str, int] = {}
    unclassified_drifts = 0
    for event in events:
        command = str(event.get("command", "")).strip() or "unknown"
        events_by_command[command] = events_by_command.get(command, 0) + 1
    for event in drifts:
        dtype = _dt(event)
        drift_by_type[dtype] = drift_by_type.get(dtype, 0) + 1
        if dtype == "missing_drift_type":
            unclassified_drifts += 1

    rows: list[DriftRow] = []
    for event in drifts:
        fingerprint = str(event.get("artifact_fingerprint", "")).strip()
        rows.append(
            DriftRow(
                ts=_ets(event),
                drift_type=_dt(event),
                command=str(event.get("command", "")).strip() or "unknown",
                status=str(event.get("status", "")).strip() or "unknown",
                fingerprint_short=fingerprint[:8] if fingerprint else "",
                cause=_dc(event),
            )
        )
    rows = sorted(rows, key=lambda item: _tsk(item.ts), reverse=True)[:top]
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


def _default_events_path() -> Path:
    try:
        root = resolve_workspace_root()
    except Exception:
        root = Path.cwd()
    return root / ".sdd" / "runtime" / "compliance-events.jsonl"


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def build_audit_summary_data(
    events: list[dict[str, Any]],
    top: int,
    now_utc: datetime,
    include_non_drift: bool,
) -> dict[str, Any]:
    """Build the full audit summary data dict for the main audit command."""
    computed = _compute_base_summary(events, top)
    drifts = computed["drifts"]
    rows: list[DriftRow] = computed["rows"]
    correlation_windows = [
        _window_correlation(events, days=days, now_utc=now_utc) for days in (7, 14, 30)
    ]
    data: dict[str, Any] = {
        "exit_code": 0,
        "total_events": len(events),
        "total_drifts": len(drifts),
        "drift_rate_pct": round((len(drifts) * 100.0 / len(events)), 2)
        if events
        else 0.0,
        "events_by_command": computed["events_by_command"],
        "drift_by_type": computed["drift_by_type"],
        "drift_unclassified_total": computed["unclassified_drifts"],
        "token_comparison": {
            "total_input_tokens": computed["total_in"],
            "total_output_tokens": computed["total_out"],
            "output_input_ratio": round(computed["ratio"], 4),
            "events_with_tokens": computed["with_tokens"],
            "events_missing_tokens": computed["missing_tokens"],
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
    return data
