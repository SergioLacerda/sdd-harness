"""ask_types — shared dataclasses for `sdd ask` request/session state.

Extracted from `commands/_ask_backend.py` so that
`services/ask_response.py` can depend on these types without
creating a module-level cyclic import with `_ask_backend.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class _AskInputs:
    query: str
    dossier: bool
    skill: str | None
    budget: int | None
    full: bool
    log_path: str | None
    log_format: str
    tokens_input: int | None
    tokens_output: int | None


@dataclass(frozen=True)
class _AskSessionContext:
    workspace_root: Path
    organize_used: bool
    organize_reason: str
    organize_artifact_path: str
    organize_chunks: int
    organize_retrieval: str
    profile: str
    state: str
    agent_id: str
    trace_id: str
    start_mono: float
    start_ts: str
