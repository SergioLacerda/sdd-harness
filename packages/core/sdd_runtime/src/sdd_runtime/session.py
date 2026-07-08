"""Session lifecycle — state isolation per (workspace_id, agent_id, work_item_id)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


@dataclass
class SessionState:
    """Runtime session record.  Mandatory fields per §12.3 of the plan."""

    workspace_id: str
    agent_id: str
    work_item_id: str
    artifact_fingerprint: str
    schema_version: str
    policy_set_version: str
    parent_session_id: str | None = None
    decomposition_level: int = 0
    session_type: str = "long"  # "short" | "long"
    last_validation_ts: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, object]:
        """To Dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SessionState:
        """From Dict."""
        parent_id = data.get("parent_session_id")
        parent_session_id = str(parent_id) if isinstance(parent_id, str) else None

        raw_level = data.get("decomposition_level", 0)
        decomposition_level = int(raw_level) if isinstance(raw_level, int | str) else 0

        return cls(
            workspace_id=str(data.get("workspace_id", "")),
            agent_id=str(data.get("agent_id", "")),
            work_item_id=str(data.get("work_item_id", "")),
            artifact_fingerprint=str(data.get("artifact_fingerprint", "")),
            schema_version=str(data.get("schema_version", "")),
            policy_set_version=str(data.get("policy_set_version", "")),
            parent_session_id=parent_session_id,
            decomposition_level=decomposition_level,
            session_type=str(data.get("session_type", "long")),
            last_validation_ts=str(data.get("last_validation_ts", _utc_now())),
        )


class SessionManager:
    """In-memory session registry with optional file-based persistence.

    Parameters
    ----------
    state_dir:
        If provided, sessions are persisted as JSON under this directory.
        Allows warm-starts across process restarts within a work item.
    """

    _STATE_FILENAME = "sdd-runtime-sessions.json"

    def __init__(self, state_dir: Path | None = None) -> None:
        self._sessions: dict[tuple[str, str, str], SessionState] = {}
        self._state_dir = state_dir
        if state_dir is not None:
            self._load_from_disk()

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def upsert(self, state: SessionState) -> SessionState:
        """Insert or replace a session.  Persists to disk if *state_dir* set."""
        self._sessions[self._key(state)] = state
        if self._state_dir is not None:
            self._save_to_disk()
        return state

    def get(
        self, workspace_id: str, agent_id: str, work_item_id: str
    ) -> SessionState | None:
        """Return the session for the given workspace/agent/work item key."""
        return self._sessions.get((workspace_id, agent_id, work_item_id))

    def is_bound_to_fingerprint(
        self,
        workspace_id: str,
        agent_id: str,
        work_item_id: str,
        artifact_fingerprint: str,
    ) -> bool:
        """Return True iff the session exists and is bound to *artifact_fingerprint*."""
        state = self.get(workspace_id, agent_id, work_item_id)
        if state is None:
            return False
        return state.artifact_fingerprint == artifact_fingerprint

    def delete(self, workspace_id: str, agent_id: str, work_item_id: str) -> bool:
        """Remove a session.  Returns True if it existed."""
        key = (workspace_id, agent_id, work_item_id)
        existed = key in self._sessions
        if existed:
            del self._sessions[key]
            if self._state_dir is not None:
                self._save_to_disk()
        return existed

    def all_sessions(self) -> list[SessionState]:
        """All Sessions."""
        return list(self._sessions.values())

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Explicitly persist in-memory state to disk.

        No-op when *state_dir* was not provided.
        """
        if self._state_dir is not None:
            self._save_to_disk()

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _key(state: SessionState) -> tuple[str, str, str]:
        return (state.workspace_id, state.agent_id, state.work_item_id)

    def _state_file(self) -> Path:
        if self._state_dir is None:
            raise RuntimeError("SessionManager state_dir is required for persistence")
        return self._state_dir / self._STATE_FILENAME

    def _save_to_disk(self) -> None:
        if self._state_dir is None:
            raise RuntimeError("SessionManager state_dir is required for persistence")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        data = [s.to_dict() for s in self._sessions.values()]
        self._state_file().write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _load_from_disk(self) -> None:
        path = self._state_file()
        if not path.exists():
            return
        try:
            raw: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
            for entry in raw:
                state = SessionState.from_dict(entry)
                self._sessions[self._key(state)] = state
        except (json.JSONDecodeError, KeyError):
            # Corrupt state file — start clean; do not crash.
            self._sessions = {}
