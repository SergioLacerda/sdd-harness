"""Support helpers for audit analytics aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sdd_cli.services.audit_event_parser import (
    DriftRow,
    _is_ask_event,
    _is_drift_event,
    _quality_score,
    _token_totals,
    _window_events,
)


def window_confidence(token_coverage: float, drift_classified_coverage: float) -> str:
    if token_coverage >= 0.7 and drift_classified_coverage >= 0.8:
        return "HIGH"
    if token_coverage >= 0.7 or drift_classified_coverage >= 0.8:
        return "MEDIUM"
    return "LOW"


def window_classification(
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


def window_correlation(
    *,
    events: list[dict[str, Any]],
    days: int,
    now_utc: datetime,
    drift_type_fn: Any,
    window_confidence_fn: Any,
    window_classification_fn: Any,
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
    prev_token_coverage = (prev_with_tokens / len(prev_asks)) if prev_asks else 0.0
    ratio = (total_out / total_in) if total_in > 0 else 0.0
    prev_ratio = (prev_out / prev_in) if prev_in > 0 else 0.0
    classified = sum(
        1 for event in drifts if drift_type_fn(event) != "missing_drift_type"
    )
    drift_classified_coverage = (classified / len(drifts)) if drifts else 1.0
    current_drift_rate = (len(drifts) * 100.0 / len(asks)) if asks else 0.0
    prev_drift_rate = (len(prev_drifts) * 100.0 / len(prev_asks)) if prev_asks else 0.0
    quality_score = _quality_score(asks)
    prev_quality_score = _quality_score(prev_asks)
    quality_signal_available = (
        quality_score is not None and prev_quality_score is not None
    )
    quality_delta = (
        quality_score - prev_quality_score
        if quality_score is not None and prev_quality_score is not None
        else None
    )
    classification, recommended_action = window_classification_fn(
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
        "confidence": window_confidence_fn(token_coverage, drift_classified_coverage),
        "recommended_action": recommended_action,
    }


def compute_base_summary(
    *,
    events: list[dict[str, Any]],
    top: int,
    drift_cause_fn: Any,
    drift_type_fn: Any,
    event_ts_fn: Any,
    ts_sort_key_fn: Any,
) -> dict[str, Any]:
    drifts = [event for event in events if _is_drift_event(event)]
    events_by_command: dict[str, int] = {}
    drift_by_type: dict[str, int] = {}
    unclassified_drifts = 0
    for event in events:
        command = str(event.get("command", "")).strip() or "unknown"
        events_by_command[command] = events_by_command.get(command, 0) + 1
    for event in drifts:
        dtype = drift_type_fn(event)
        drift_by_type[dtype] = drift_by_type.get(dtype, 0) + 1
        if dtype == "missing_drift_type":
            unclassified_drifts += 1
    rows = sorted(
        [
            DriftRow(
                ts=event_ts_fn(event),
                drift_type=drift_type_fn(event),
                command=str(event.get("command", "")).strip() or "unknown",
                status=str(event.get("status", "")).strip() or "unknown",
                fingerprint_short=(
                    str(event.get("artifact_fingerprint", "")).strip()[:8]
                ),
                cause=drift_cause_fn(event),
            )
            for event in drifts
        ],
        key=lambda item: ts_sort_key_fn(item.ts),
        reverse=True,
    )[:top]
    total_in, total_out, with_tokens = _token_totals(events)
    ratio = (total_out / total_in) if total_in > 0 else 0.0
    return {
        "drifts": drifts,
        "events_by_command": events_by_command,
        "drift_by_type": drift_by_type,
        "unclassified_drifts": unclassified_drifts,
        "rows": rows,
        "total_in": total_in,
        "total_out": total_out,
        "ratio": ratio,
        "missing_tokens": len(events) - with_tokens,
        "with_tokens": with_tokens,
    }


def default_events_path(*, resolve_workspace_root_fn: Any) -> Path:
    try:
        root = resolve_workspace_root_fn()
    except Exception:
        root = Path.cwd()
    return Path(root) / ".sdd" / "runtime" / "compliance-events.jsonl"
