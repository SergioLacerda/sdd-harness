"""Supervised learning primitives for skill pipeline convergence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class FailureLedgerEntry:
    """FailureLedgerEntry."""

    symptom: str
    root_cause: str
    fix: str
    validation: str
    regression: bool
    tags: list[str]
    evidence_refs: list[str]
    timestamp: str


@dataclass(frozen=True)
class RuleCandidate:
    """RuleCandidate."""

    candidate_id: str
    pattern: str
    proposed_guardrail: str
    risk_level: str
    expected_impact: str
    evidence_refs: list[str]
    source_count: int
    created_at: str


class SupervisedLearningStore:
    """File-backed learning registry with human approval gate."""

    def __init__(self, project_root: Path) -> None:
        self._runtime_dir = project_root / ".sdd" / "runtime"
        self._runtime_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._runtime_dir / "failure-ledger.jsonl"
        self._candidates_path = self._runtime_dir / "rule-candidates.json"
        self._registry_path = self._runtime_dir / "rule-registry.json"
        self._impact_path = self._runtime_dir / "rule-impact.jsonl"

    def append_failure(self, entry: FailureLedgerEntry) -> None:
        """Append Failure."""
        with self._ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=True) + "\n")

    def list_failures(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        """Return most recent failure rows, newest first."""
        rows = list(reversed(self._read_jsonl(self._ledger_path)))
        if limit is None or limit <= 0:
            return rows
        return rows[:limit]

    def find_similar_failures(
        self,
        *,
        symptom: str,
        root_cause: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return ledger entries matching symptom and optionally root_cause."""
        matches = [
            row
            for row in self.list_failures()
            if str(row.get("symptom", "")) == symptom
            and (
                root_cause is None or str(row.get("root_cause", "")) == str(root_cause)
            )
        ]
        if limit is None or limit <= 0:
            return matches
        return matches[:limit]

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            rows.append(json.loads(raw))
        return rows

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )

    def generate_candidates_from_ledger(
        self, *, min_occurrences: int = 2
    ) -> list[RuleCandidate]:
        """Generate candidates from recurring failure ledger patterns."""
        ledger = self._read_jsonl(self._ledger_path)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in ledger:
            key = f"{row.get('symptom', '')}|{row.get('root_cause', '')}"
            grouped.setdefault(key, []).append(row)

        existing = self._read_json(self._candidates_path, {"candidates": []})
        existing_patterns = {
            str(item.get("pattern", "")) for item in existing.get("candidates", [])
        }
        created: list[RuleCandidate] = []
        for key, rows in grouped.items():
            if len(rows) < min_occurrences:
                continue
            symptom, root_cause = key.split("|", 1)
            evidence_refs = sorted(
                {
                    ref
                    for row in rows
                    for ref in row.get("evidence_refs", [])
                    if isinstance(ref, str) and ref.strip()
                }
            )
            if not evidence_refs or key in existing_patterns:
                continue
            created.append(
                RuleCandidate(
                    candidate_id=f"rc-{uuid4().hex[:12]}",
                    pattern=key,
                    proposed_guardrail=(
                        f"Block speculative correction when pattern '{symptom}' "
                        f"with root cause '{root_cause}' appears without evidence."
                    ),
                    risk_level="medium",
                    expected_impact="reduce_rework",
                    evidence_refs=evidence_refs,
                    source_count=len(rows),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        if created:
            payload = existing
            payload.setdefault("candidates", [])
            payload["candidates"].extend(asdict(item) for item in created)
            self._write_json(self._candidates_path, payload)
        return created

    def decide_rule(
        self,
        *,
        candidate_id: str,
        approved: bool,
        reviewer: str,
        rationale: str,
        ttl_days: int = 30,
    ) -> dict[str, Any]:
        """Record an approval/rejection decision for a rule candidate."""
        candidates_payload = self._read_json(self._candidates_path, {"candidates": []})
        candidate = next(
            (
                c
                for c in candidates_payload.get("candidates", [])
                if c.get("candidate_id") == candidate_id
            ),
            None,
        )
        if candidate is None:
            return {"status": "missing_candidate", "candidate_id": candidate_id}

        registry = self._read_json(self._registry_path, {"rules": []})
        decision = {
            "candidate_id": candidate_id,
            "approved": approved,
            "reviewer": reviewer,
            "rationale": rationale,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "ttl_days": ttl_days,
        }
        if approved:
            registry["rules"].append(
                {
                    "rule_id": f"rr-{uuid4().hex[:12]}",
                    "candidate_id": candidate_id,
                    "pattern": candidate["pattern"],
                    "proposed_guardrail": candidate["proposed_guardrail"],
                    "active_from": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (
                        datetime.now(timezone.utc) + timedelta(days=ttl_days)
                    ).isoformat(),
                    "status": "active",
                    "decision": decision,
                }
            )
            self._write_json(self._registry_path, registry)
        return {"status": "ok", "decision": decision}

    def list_active_rules(self) -> list[dict[str, Any]]:
        """List Active Rules."""
        now = datetime.now(timezone.utc)
        registry = self._read_json(self._registry_path, {"rules": []})
        active: list[dict[str, Any]] = []
        changed = False
        for rule in registry.get("rules", []):
            expires_at = datetime.fromisoformat(str(rule.get("expires_at")))
            if expires_at <= now and rule.get("status") == "active":
                rule["status"] = "expired"
                changed = True
            if rule.get("status") == "active":
                active.append(rule)
        if changed:
            self._write_json(self._registry_path, registry)
        return active

    def record_rule_impact(
        self,
        *,
        rule_id: str,
        rework_delta: float,
        false_block_rate: float,
        escalation_delta: float,
        rollback_flag: bool,
    ) -> None:
        """Record rule impact metrics and optionally rollback active rules."""
        payload = {
            "rule_id": rule_id,
            "rework_delta": rework_delta,
            "false_block_rate": false_block_rate,
            "escalation_delta": escalation_delta,
            "rollback_flag": rollback_flag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._impact_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        if rollback_flag:
            self._rollback_rule(rule_id)

    def _rollback_rule(self, rule_id: str) -> None:
        registry = self._read_json(self._registry_path, {"rules": []})
        changed = False
        for rule in registry.get("rules", []):
            if rule.get("rule_id") == rule_id and rule.get("status") == "active":
                rule["status"] = "rolled_back"
                rule["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
        if changed:
            self._write_json(self._registry_path, registry)
