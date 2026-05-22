"""Helpers for organize-intake heuristics and artifact generation."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:8]


def _estimate_input_complexity(text: str) -> dict[str, int]:
    lines = text.splitlines()
    line_count = max(1, len(lines))
    char_count = len(text)
    traceback_count = len(re.findall(r"\btraceback\b", text, flags=re.IGNORECASE))
    test_marker_count = len(re.findall(r"\btest[_\w]*\b", text, flags=re.IGNORECASE))
    error_marker_count = len(
        re.findall(r"\b(error|exception|failed|failure)\b", text, flags=re.IGNORECASE)
    )
    return {
        "line_count": line_count,
        "char_count": char_count,
        "traceback_count": traceback_count,
        "test_marker_count": test_marker_count,
        "error_marker_count": error_marker_count,
    }


def should_use_organize(text: str) -> tuple[bool, str]:
    """Return whether organize intake should be used and the trigger reason."""
    metrics = _estimate_input_complexity(text)
    if metrics["char_count"] >= 6000:
        return True, "char_count>=6000"
    if metrics["line_count"] >= 120:
        return True, "line_count>=120"
    if metrics["traceback_count"] >= 2:
        return True, "traceback_count>=2"
    if metrics["error_marker_count"] >= 8 and metrics["test_marker_count"] >= 4:
        return True, "dense_error_test_markers"
    return False, "light_input"


def _split_into_chunks(text: str, *, max_lines: int = 40) -> list[dict[str, Any]]:
    lines = text.splitlines()
    if not lines:
        lines = [text]
    chunks: list[dict[str, Any]] = []
    cursor = 0
    chunk_id = 0
    while cursor < len(lines):
        window = lines[cursor : cursor + max_lines]
        chunk_text = "\n".join(window)
        offset_start = len("\n".join(lines[:cursor])) + (1 if cursor > 0 else 0)
        offset_end = offset_start + len(chunk_text)
        chunks.append(
            {
                "chunk_id": f"c{chunk_id:04d}",
                "line_start": cursor + 1,
                "line_end": cursor + len(window),
                "offset_start": offset_start,
                "offset_end": offset_end,
                "text_hash": hashlib.sha256(chunk_text.encode()).hexdigest()[:12],
                "preview": chunk_text[:220],
            }
        )
        cursor += max_lines
        chunk_id += 1
    return chunks


def _extract_error_signature(block: str) -> str:
    match = re.search(
        r"([A-Za-z_][A-Za-z0-9_]*(Error|Exception))", block, flags=re.IGNORECASE
    )
    if match:
        return match.group(1)
    if "failed" in block.lower():
        return "AssertionFailed"
    return "UnknownError"


def _extract_test_case(block: str) -> str:
    match = re.search(r"\b(test[_A-Za-z0-9]+)\b", block)
    return match.group(1) if match else "unknown_test"


def _extract_file_path(block: str) -> str:
    match = re.search(r"([A-Za-z0-9_\-./]+\.py)", block)
    return match.group(1) if match else "unknown_file"


def _extract_time_key(block: str) -> str:
    match = re.search(r"(\d{2}:\d{2}:\d{2})", block)
    return match.group(1) if match else "unknown_time"


def _new_index_entry(
    *, chunk_id: str, severity: str, confidence: float
) -> dict[str, Any]:
    return {
        "chunks": [chunk_id],
        "severity": severity,
        "first_seen": _now(),
        "repeat_count": 1,
        "confidence": confidence,
        "noise_score": 0.0,
    }


def _append_or_merge_index(
    index: dict[str, dict[str, Any]],
    key: str,
    chunk_id: str,
    *,
    severity: str = "medium",
    confidence: float = 0.7,
) -> None:
    if key not in index:
        index[key] = _new_index_entry(
            chunk_id=chunk_id, severity=severity, confidence=confidence
        )
        return
    existing = index[key]
    if chunk_id not in existing["chunks"]:
        existing["chunks"].append(chunk_id)
    existing["repeat_count"] = int(existing.get("repeat_count", 1)) + 1


def _build_multi_index(
    source_text: str, chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    lines = source_text.splitlines()
    by_error: dict[str, dict[str, Any]] = {}
    by_root_cause: dict[str, dict[str, Any]] = {}
    by_test_case: dict[str, dict[str, Any]] = {}
    by_file_path: dict[str, dict[str, Any]] = {}
    by_time_window: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        start = int(chunk["line_start"]) - 1
        end = int(chunk["line_end"])
        block = "\n".join(lines[start:end]).strip()
        chunk_id = str(chunk["chunk_id"])
        signature = _extract_error_signature(block)
        root_cause = signature
        test_case = _extract_test_case(block)
        file_path = _extract_file_path(block)
        time_key = _extract_time_key(block)
        _append_or_merge_index(
            by_error,
            signature,
            chunk_id,
            severity="high"
            if "Error" in signature or "Exception" in signature
            else "medium",
            confidence=0.85,
        )
        _append_or_merge_index(by_root_cause, root_cause, chunk_id, confidence=0.75)
        _append_or_merge_index(by_test_case, test_case, chunk_id, confidence=0.65)
        _append_or_merge_index(by_file_path, file_path, chunk_id, confidence=0.6)
        _append_or_merge_index(by_time_window, time_key, chunk_id, confidence=0.5)
    return {
        "index_by_error_signature": by_error,
        "index_by_root_cause": by_root_cause,
        "index_by_test_case": by_test_case,
        "index_by_file_path": by_file_path,
        "index_by_time_window": by_time_window,
    }


def _build_organize_artifact(
    *,
    query: str,
    source_text: str,
    route_reason: str,
    degraded: bool = False,
) -> dict[str, Any]:
    chunks = _split_into_chunks(source_text)
    indexes = _build_multi_index(source_text, chunks)
    indexed_lines = sum(
        max(0, int(chunk["line_end"]) - int(chunk["line_start"]) + 1)
        for chunk in chunks
    )
    total_lines = max(1, len(source_text.splitlines()))
    discarded_pct = max(0.0, 100.0 - ((indexed_lines / total_lines) * 100.0))
    return {
        "schema_version": "1.0.0",
        "query_hash": _hash_query(query),
        "query_original": query,
        "intake_index_mode": "multi",
        "route": "heavy",
        "route_reason": route_reason,
        "retrieval_policy": "degraded" if degraded else "indexed_only",
        "index_degraded": degraded,
        "chunks": chunks,
        "indexes": indexes,
        "coverage_stats": {
            "total_lines": total_lines,
            "indexed_lines": indexed_lines,
            "indexed_pct": round((indexed_lines / total_lines) * 100.0, 2),
            "discarded_noise_pct": round(discarded_pct, 2),
        },
    }


def _write_organize_artifact(workspace_root: Path, artifact: dict[str, Any]) -> Path:
    out_dir = workspace_root / ".sdd" / "runtime" / "ask-intake"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = artifact.get("query_hash", "unknown")
    out_path = out_dir / f"{ts}-{suffix}.json"
    out_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out_path


def run_sdd_organize(
    *,
    workspace_root: Path,
    query: str,
    source_text: str,
    route_reason: str,
) -> tuple[dict[str, Any], Path]:
    """Run sdd-organize intake and persist artifact."""
    artifact = _build_organize_artifact(
        query=query,
        source_text=source_text,
        route_reason=route_reason,
    )
    path = _write_organize_artifact(workspace_root, artifact)
    return artifact, path
