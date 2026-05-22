"""
Incremental Compilation State Manager

Tracks source file hashes and compilation state to enable incremental compilation.
Allows skipping Phase 1 (parsing) and Phase 2 (msgpack encoding) when sources
are unchanged.

State file: .sdd/runtime/.compile-state.json

Structure:
{
  "version": "1.0",
  "timestamp": "2026-05-11T10:30:00Z",
  "sources": {
    "mandate": {"hash": "abc123", "size": 12345},
    "guidelines": {"hash": "def456", "size": 67890}
  },
  "artifacts": {
    "mandate_bin": {"size": 1024, "path": "governance-core.compiled.msgpack"},
    "guidelines_bin": {"size": 2048, "path": "governance-client-template.compiled.msgpack"}
  }
}
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CompileState:
    """Manages incremental compilation state"""

    def __init__(self, state_file: Path):
        """Initialize compile state manager

        Args:
            state_file: Path to .sdd/runtime/.compile-state.json
        """
        self.state_file = state_file
        self.state: dict[str, Any] = {
            "version": "1.0",
            "timestamp": None,
            "sources": {},
            "artifacts": {},
        }
        self._load()

    def _load(self) -> None:
        """Load state from file if it exists"""
        if self.state_file.exists():
            try:
                content = self.state_file.read_text(encoding="utf-8")
                self.state = json.loads(content)
            except (OSError, json.JSONDecodeError):
                # If file is corrupted, start fresh
                self.state = {
                    "version": "1.0",
                    "timestamp": None,
                    "sources": {},
                    "artifacts": {},
                }

    def save(self) -> None:
        """Save state to file"""
        self.state["timestamp"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    @staticmethod
    def _file_hash(path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def update_source(self, name: str, path: Path) -> None:
        """Update source file hash and size

        Args:
            name: Source name (e.g., 'mandate', 'guidelines')
            path: Path to source file
        """
        if not path.exists():
            return

        file_hash = self._file_hash(path)
        file_size = path.stat().st_size

        self.state["sources"][name] = {
            "hash": file_hash,
            "size": file_size,
        }

    def get_source_hash(self, name: str) -> str | None:
        """Get stored hash for a source file

        Args:
            name: Source name (e.g., 'mandate', 'guidelines')

        Returns:
            Hash string or None if not stored
        """
        val = self.state.get("sources", {}).get(name, {}).get("hash")
        return str(val) if val is not None else None

    def source_changed(self, name: str, path: Path) -> bool:
        """Check if source file has changed since last compilation

        Args:
            name: Source name
            path: Path to source file

        Returns:
            True if file has changed, False if unchanged
        """
        if not path.exists():
            return True

        current_hash = self._file_hash(path)
        stored_hash = self.get_source_hash(name)

        if stored_hash is None:
            return True

        return current_hash != stored_hash

    def any_source_changed(self, sources: dict[str, Path]) -> bool:
        """Check if any source files have changed

        Args:
            sources: Dict mapping source names to paths

        Returns:
            True if any source has changed
        """
        return any(self.source_changed(name, path) for name, path in sources.items())

    def update_artifact(self, name: str, path: Path) -> None:
        """Update artifact metadata after successful compilation

        Args:
            name: Artifact name (e.g., 'mandate_bin', 'guidelines_bin')
            path: Path to compiled artifact
        """
        if not path.exists():
            return

        file_size = path.stat().st_size

        self.state["artifacts"][name] = {
            "size": file_size,
            # Persist path using POSIX separators for cross-platform stability.
            "path": path.relative_to(path.parent.parent.parent).as_posix(),
        }

    def get_artifact_path(self, name: str) -> str | None:
        """Get stored path for an artifact

        Args:
            name: Artifact name

        Returns:
            Relative path string or None
        """
        val = self.state.get("artifacts", {}).get(name, {}).get("path")
        return str(val) if val is not None else None

    def get_last_compiled_time(self) -> str | None:
        """Get timestamp of last compilation

        Returns:
            ISO timestamp string or None
        """
        return self.state.get("timestamp")

    def to_dict(self) -> dict[str, Any]:
        """Get state as dictionary

        Returns:
            State dictionary
        """
        return self.state.copy()
