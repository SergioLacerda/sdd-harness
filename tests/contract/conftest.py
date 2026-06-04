"""Contract test session setup.

Recompiles governance artifacts before the contract test suite runs.
This prevents stale-artifact failures when tests are invoked via
'sdd test run', 'make check', or 'pytest tests/contract/' directly.

In CI, the bootstrap action already compiles and validates artifacts
(sdd governance compile + sync). The fixture skips recompilation when
valid artifacts are already present to avoid a redundant pipeline run
that could fail due to env differences (e.g. missing .sdd/source/).
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path

import pytest

from sdd_cli.utils.sdd_authority import compiled_active_dir, resolve_workspace_root


def _artifacts_valid(repo_root: Path) -> bool:
    """Return True if compiled artifacts exist and contain a viable mandate set."""
    import json as _json

    del repo_root
    canonical = compiled_active_dir() / "governance-core.json"
    if not canonical.exists():
        return False
    with contextlib.suppress(Exception):
        data = _json.loads(canonical.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if len(items) >= 4 and all("id" in item for item in items):
            return True
    return False


@pytest.fixture(scope="session", autouse=True)
def fresh_governance_artifact() -> None:
    """Ensure governance-core.json is up to date before contract tests run.

    Skips recompilation when valid artifacts already exist (CI bootstrap path).
    Forces recompilation when run directly or artifacts are missing/stale.
    """
    repo_root = Path(__file__).parent.parent.parent

    if _artifacts_valid(repo_root):
        return

    # xdist workers can enter this fixture concurrently and race while
    # writing/reading governance artifacts. Serialize compilation with a lock.
    workspace_root = resolve_workspace_root()
    lock_file = workspace_root / ".sdd" / "runtime" / "contract-compile.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd: int | None = None
    deadline = time.time() + 60.0
    while lock_fd is None:
        try:
            lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        except FileExistsError:
            # Another worker is compiling. Wait for it and re-check validity.
            if _artifacts_valid(repo_root):
                return
            if time.time() >= deadline:
                pytest.fail(f"Timeout waiting for governance compile lock: {lock_file}")
            time.sleep(0.2)

    from sdd_core.governance_orchestrator import GovernanceOrchestrator

    try:
        # Another worker may have completed while we were waiting to acquire lock.
        if _artifacts_valid(repo_root):
            return
        result = GovernanceOrchestrator(
            repo_root=str(repo_root),
            workspace_root=str(workspace_root),
        ).run_full_pipeline()
        if not result.get("full_pipeline_success"):
            pytest.fail(
                f"Governance compilation failed before contract tests: {result}"
            )
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        with contextlib.suppress(Exception):
            lock_file.unlink(missing_ok=True)
