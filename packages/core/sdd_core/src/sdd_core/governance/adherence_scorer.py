"""Governance adherence scoring engine.

Computes a composite 0-100 score across three weighted dimensions:
- Behavioral (50 pts): allow / (allow + warn + block) from compliance events
- Structural (30 pts): fingerprint match between state and artifacts
- Freshness (20 pts): linear decay from last_check vs TTL
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GovernanceAdherenceScorer:
    """Computes governance adherence score from compliance events and state."""

    @staticmethod
    def compute(
        *,
        workspace_root: Path | None = None,
        log_path: Path | None = None,
        state_path: Path | None = None,
        window_hours: int = 24,
    ) -> dict[str, Any]:
        """Compute governance adherence score (0-100).

        Dimensions:
            Behavioral (50): allow / (allow + warn + block) from compliance events
                             in the last ``window_hours`` hours.
                             No events → ratio = 1.0 (assume perfect).
            Structural (30): fingerprint match between governance-state.json
                             and the current compiled artifact.
            Freshness  (20): linear decay from last_check vs TTL.
                             TTL = 1800 s (client) or 28800 s (master / default).

        Returns:
            score       (int):   combined 0-100 score
            behavioral  (float): ratio 0.0-1.0
            structural  (bool):  fingerprint matches
            freshness   (float): ratio 0.0-1.0
            details     (dict):  diagnostic breakdown
        """
        now = datetime.now()
        cutoff = now - timedelta(hours=window_hours)

        # ---- Resolve state file ----
        resolved_state: Path | None = state_path
        if resolved_state is None:
            root = workspace_root
            if root is None:
                try:
                    from sdd_core.utils.environment import find_workspace_root

                    root = find_workspace_root()
                except Exception as exc:
                    logger.debug(
                        "Could not resolve workspace root for governance adherence state file: %s",
                        exc,
                    )
            if root is not None:
                resolved_state = root / ".sdd" / "runtime" / "governance-state.json"

        # ---- Compute each dimension ----
        all_events = GovernanceAdherenceScorer._read_all_events(
            workspace_root=workspace_root, log_path=log_path
        )
        beh = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)
        struct = GovernanceAdherenceScorer._compute_structural(
            resolved_state, workspace_root
        )
        fresh = GovernanceAdherenceScorer._compute_freshness(struct["state_data"], now)

        total_score = beh["score"] + struct["score"] + fresh["score"]

        return {
            "score": total_score,
            "behavioral": beh["ratio"],
            "structural": struct["match"],
            "freshness": fresh["ratio"],
            "details": {
                "allows": beh["allows"],
                "warns": beh["warns"],
                "blocks": beh["blocks"],
                "window_events": beh["window_events"],
                "window_hours": window_hours,
                "structural_status": struct["detail"],
                "freshness_status": fresh["detail"],
                "behavioral_score": beh["score"],
                "structural_score": struct["score"],
                "freshness_score": fresh["score"],
            },
        }

    @staticmethod
    def _read_all_events(
        *,
        workspace_root: Path | None = None,
        log_path: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Read ALL compliance events from the JSONL log (no N cap)."""
        from sdd_core.governance.compliance_constants import default_log_path

        target = log_path or default_log_path(workspace_root)
        if target is None or not target.exists():
            return []
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            parsed = []
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        parsed.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return parsed
        except Exception as exc:
            logger.warning("Failed to read all compliance events: %s", exc)
            return []

    @staticmethod
    def _get_compiled_fingerprint(workspace_root: Path | None = None) -> str:
        """Return the fingerprint from the first available compiled governance artifact."""
        root = workspace_root
        if root is None:
            try:
                from sdd_core.utils.environment import find_workspace_root

                root = find_workspace_root()
            except Exception as exc:
                logger.debug(
                    "Could not resolve workspace root for compiled fingerprint lookup: %s",
                    exc,
                )
        if root is None:
            return ""
        candidates = [
            root / ".sdd" / "compiled" / "governance-core.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    data = json.loads(path.read_bytes())
                    fp = str(data.get("fingerprint", "")).strip()
                    if fp:
                        return fp
                    # Fallback: compute from content (legacy artifacts without embedded fingerprint)
                    clean = {
                        k: v
                        for k, v in data.items()
                        if k not in {"_signature", "fingerprint"}
                    }
                    return hashlib.sha256(
                        json.dumps(clean, sort_keys=True).encode()
                    ).hexdigest()
                except Exception:  # nosec B112 — intentional: invalid artifacts are skipped
                    continue
        return ""

    @staticmethod
    def _compute_behavioral(
        all_events: list[dict[str, Any]],
        cutoff: datetime,
    ) -> dict[str, Any]:
        """Compute behavioral dimension (50 pts) from compliance events within the time window."""
        from sdd_core.governance.compliance_constants import (
            GOVERNANCE_CHECKED,
            VIOLATION,
        )

        window_events = []
        for ev in all_events:
            try:
                ts_str = ev.get("timestamp", ev.get("ts", ""))
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is not None:
                    ts = ts.astimezone().replace(tzinfo=None)
                if ts >= cutoff:
                    window_events.append(ev)
            except (ValueError, TypeError):
                continue

        allows = sum(1 for e in window_events if e.get("event") == GOVERNANCE_CHECKED)
        warns = sum(
            1
            for e in window_events
            if e.get("event") == VIOLATION
            and (e.get("details") or {}).get("action") == "warn"
        )
        blocks = sum(
            1
            for e in window_events
            if e.get("event") == VIOLATION
            and (e.get("details") or {}).get("action") == "block"
        )
        total = allows + warns + blocks
        ratio = allows / total if total > 0 else 1.0
        return {
            "ratio": ratio,
            "score": round(ratio * 50),
            "allows": allows,
            "warns": warns,
            "blocks": blocks,
            "window_events": len(window_events),
        }

    @staticmethod
    def _compute_structural(
        resolved_state: Path | None,
        workspace_root: Path | None,
    ) -> dict[str, Any]:
        """Compute structural dimension (30 pts) via fingerprint comparison."""
        match = False
        detail = "no_state_file"
        state_data: dict[str, Any] = {}

        if resolved_state is not None and resolved_state.exists():
            try:
                state_data = json.loads(resolved_state.read_text(encoding="utf-8"))
                cached_fp = str(state_data.get("spec_fingerprint", "")).strip()
                if cached_fp:
                    artifact_fp = GovernanceAdherenceScorer._get_compiled_fingerprint(
                        workspace_root
                    )
                    if artifact_fp:
                        match = cached_fp[:16] == artifact_fp[:16]
                        detail = "match" if match else "drift_detected"
                    else:
                        detail = "no_artifact"
                else:
                    detail = "no_fingerprint_in_state"
            except Exception as exc:
                detail = f"error: {exc}"

        return {
            "match": match,
            "score": 30 if match else 0,
            "detail": detail,
            "state_data": state_data,
        }

    @staticmethod
    def _compute_freshness(
        state_data: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        """Compute freshness dimension (20 pts) via linear TTL decay."""
        ratio = 0.0
        detail = "no_state_file"

        if state_data:
            try:
                last_check_str = state_data.get("last_check", "")
                if last_check_str:
                    last_check = datetime.fromisoformat(last_check_str)
                    elapsed = (now - last_check).total_seconds()
                    profile_from_state = str(state_data.get("profile", "master"))
                    ttl = 1800.0 if profile_from_state == "client" else 28800.0
                    ratio = max(0.0, 1.0 - elapsed / ttl)
                    detail = f"elapsed={int(elapsed)}s ttl={int(ttl)}s"
                else:
                    detail = "no_last_check"
            except Exception as exc:
                detail = f"error: {exc}"

        return {"ratio": ratio, "score": round(ratio * 20), "detail": detail}
