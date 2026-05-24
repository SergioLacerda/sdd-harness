import builtins
import contextlib
import hashlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.helpers.text_io import read_text_utf8, write_text_utf8

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPO_SDD_ROOT = (_REPO_ROOT / ".sdd").resolve()
_SDD_SNAPSHOT_START: dict[str, str] = {}

tomllib: ModuleType | None
try:
    import tomllib as _tomllib  # type: ignore[import-not-found]  # stdlib on 3.11+

    tomllib = _tomllib
except ImportError:
    try:
        import tomli as _tomllib  # backport for 3.10

        tomllib = _tomllib
    except ImportError:
        tomllib = None


def get_governance_config() -> dict[str, str]:
    """Lê as configurações de governança do pyproject.toml como fonte única de verdade."""
    # tests/conftest.py -> raiz do repositório é o diretório pai de tests/
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"

    if not pyproject.exists() or tomllib is None:
        return {
            "source_root": "docs/spec/canonical/core/policies",
            "compiled_output": "packages/core/sdd_compiler/src/sdd_compiler/compiled",
        }

    with open(pyproject, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    tool_cfg = data.get("tool")
    if not isinstance(tool_cfg, dict):
        return {}

    sdd_cfg = tool_cfg.get("sdd")
    if not isinstance(sdd_cfg, dict):
        return {}

    gov_cfg = sdd_cfg.get("governance")
    if not isinstance(gov_cfg, dict):
        return {}

    return {str(k): str(v) for k, v in gov_cfg.items()}


def _configure_console_encoding() -> None:
    """Reconfigure stdout/stderr for Windows CI UTF-8 safety."""
    with contextlib.suppress(Exception):
        stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
        if callable(stdout_reconfigure):
            stdout_reconfigure(errors="replace")
        stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
        if callable(stderr_reconfigure):
            stderr_reconfigure(errors="replace")


def _governance_artifacts_valid(paths: dict[str, Path]) -> bool:
    """Return True if all required artifacts exist and the core JSON is parseable."""
    import json as _json

    required = [
        paths["master_compiled"] / "governance-core.json",
        paths["master_compiled"] / "governance-core.compiled.msgpack",
        paths["master_compiled"] / "governance-client-template.compiled.msgpack",
        paths["master_compiled"] / "metadata-core.json",
        paths["master_compiled"] / "metadata-client-template.json",
        paths["client_compiled"] / "governance-core.compiled.msgpack",
    ]
    if not all(p.exists() for p in required):
        return False
    # Prefer client compiled for item count validation (client has full item set in
    # single-profile environments where master compiled may have a subset).
    for candidate in (
        paths["client_compiled"] / "governance-core.json",
        paths["master_compiled"] / "governance-core.json",
    ):
        if not candidate.exists():
            continue
        try:
            _data = _json.loads(read_text_utf8(candidate))
            _items = _data.get("items", [])
            # Require a minimum viable mandate set; single-item artifacts are stale.
            if len(_items) >= 4 and all("id" in _item for _item in _items):
                return True
        except Exception:
            continue
    return False


def _try_docs_update() -> None:
    try:
        import importlib

        docs_module = importlib.import_module("sdd_cli.commands.docs")
        docs_update = getattr(docs_module, "update", None)
        if callable(docs_update):
            docs_update(dry_run=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[conftest] docs update skipped: {exc}")


def _count_governance_items(compiled_dir: Path) -> int:
    """Return number of items in the compiled governance-core.json, or 0 on any error."""
    import json as _json

    core_json = compiled_dir / "governance-core.json"
    if not core_json.exists():
        return 0
    try:
        data = _json.loads(read_text_utf8(core_json))
        return len(data.get("items", []))
    except Exception:
        return 0


def _sync_compiled_dirs(master_compiled: Path, client_compiled: Path) -> None:
    """Mirror artifacts between master_compiled and client_compiled as needed."""
    if master_compiled == client_compiled:
        return

    master_count = _count_governance_items(master_compiled)
    client_count = _count_governance_items(client_compiled)

    if client_count > master_count:
        # Client has richer artifacts — copy to master so tests that check
        # master_compiled find a full item set.
        master_compiled.mkdir(parents=True, exist_ok=True)
        for artifact in client_compiled.glob("*.msgpack"):
            shutil.copy2(artifact, master_compiled / artifact.name)
        for artifact in client_compiled.glob("*.json"):
            shutil.copy2(artifact, master_compiled / artifact.name)
        print(
            f"[conftest] Synced client_compiled → master_compiled "
            f"({client_count} > {master_count} items)"
        )
    elif master_count > client_count:
        client_compiled.mkdir(parents=True, exist_ok=True)
        for artifact in master_compiled.glob("*.msgpack"):
            shutil.copy2(artifact, client_compiled / artifact.name)
        for artifact in master_compiled.glob("*.json"):
            shutil.copy2(artifact, client_compiled / artifact.name)
        print(
            "[conftest] Synced master_compiled → client_compiled for CI/CD compatibility"
        )


def _bootstrap_governance(root: Path, paths: dict[str, Path]) -> None:
    from sdd_core.deployment_manager import DeploymentManager
    from sdd_core.governance_orchestrator import GovernanceOrchestrator

    _try_docs_update()

    orchestrator = GovernanceOrchestrator(repo_root=str(root))
    result = orchestrator.run_full_pipeline()
    if not result.get("full_pipeline_success"):
        raise RuntimeError(f"governance bootstrap failed: {result}")

    deploy_result = DeploymentManager(repo_root=str(root)).deploy()
    if not deploy_result.get("success"):
        raise RuntimeError(f"deployment bootstrap failed: {deploy_result}")

    _sync_compiled_dirs(paths["master_compiled"], paths["client_compiled"])


def pytest_sessionstart(session: object) -> None:  # noqa: ARG001
    """Build governance compiled artifacts if they are missing."""
    root = Path(__file__).resolve().parent.parent

    _configure_console_encoding()

    test_output = Path(tempfile.gettempdir()) / f"sdd-test-output-{os.getpid()}"
    test_output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SDD_TEST_OUTPUT_DIR", str(test_output))
    # In shadow-repo container checks we intentionally allow local workspace
    # telemetry paths (tmp_path/.sdd/runtime/...) to preserve test semantics.
    if os.environ.get("SDD_ALLOW_REPO_SDD_MUTATION", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        os.environ.setdefault(
            "SDD_COMPLIANCE_EVENTS_PATH",
            str((test_output / "compliance-events.jsonl").resolve()),
        )

    from sdd_core.utils.environment import get_sdd_paths

    paths = get_sdd_paths()
    required = [
        paths["master_compiled"] / "governance-core.json",
        paths["master_compiled"] / "governance-core.compiled.msgpack",
        paths["master_compiled"] / "governance-client-template.compiled.msgpack",
        paths["master_compiled"] / "metadata-core.json",
        paths["master_compiled"] / "metadata-client-template.json",
        paths["client_compiled"] / "governance-core.compiled.msgpack",
    ]
    global _SDD_SNAPSHOT_START

    if _governance_artifacts_valid(paths):
        # Artifacts already valid — take baseline snapshot and exit without rebuilding.
        _SDD_SNAPSHOT_START = _snapshot_repo_sdd_tree()
        return

    print("\n[conftest] Governance artifacts missing — rebuilding...")
    _bootstrap_governance(root, paths)

    missing_after = [str(p) for p in required if not p.exists()]
    if missing_after:
        raise RuntimeError(
            "bootstrap completed but required artifacts are still missing: "
            + ", ".join(missing_after)
        )

    _SDD_SNAPSHOT_START = _snapshot_repo_sdd_tree()


def pytest_sessionfinish(session: object, exitstatus: int) -> None:  # noqa: ARG001
    """Fail session when repository .sdd tree changed during tests."""
    del exitstatus
    if os.environ.get("SDD_ALLOW_REPO_SDD_MUTATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    after = _snapshot_repo_sdd_tree()
    if after != _SDD_SNAPSHOT_START:
        before_keys = set(_SDD_SNAPSHOT_START.keys())
        after_keys = set(after.keys())
        added = sorted(after_keys - before_keys)
        removed = sorted(before_keys - after_keys)
        changed = sorted(
            key
            for key in (before_keys & after_keys)
            if _SDD_SNAPSHOT_START[key] != after[key]
        )
        diff_preview = f"added={added[:5]} removed={removed[:5]} changed={changed[:5]}"
        raise RuntimeError(
            "TEST POLICY: repository .sdd mutated during test session. " + diff_preview
        )


def _snapshot_repo_sdd_tree() -> dict[str, str]:
    """Return deterministic snapshot of repository .sdd content."""
    if not _REPO_SDD_ROOT.exists():
        return {}
    snapshot: dict[str, str] = {}
    for path in sorted(_REPO_SDD_ROOT.rglob("*")):
        rel = str(path.relative_to(_REPO_ROOT))
        if path.is_dir():
            snapshot[rel + "/"] = "dir"
            continue
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot[rel] = digest
    return snapshot


def _resolve_candidate_path(target: Any) -> Path | None:
    """Best-effort conversion of path-like target to absolute Path."""
    try:
        candidate = Path(target)
    except Exception:
        return None
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _is_repo_sdd_path(target: Any) -> bool:
    candidate = _resolve_candidate_path(target)
    if candidate is None:
        return False
    try:
        return candidate.is_relative_to(_REPO_SDD_ROOT)
    except Exception:
        return False


def _guard_repo_sdd_write(target: Any, op: str) -> None:
    if _is_repo_sdd_path(target):
        raise RuntimeError(
            f"TEST POLICY: write to repository .sdd is forbidden "
            f"(op={op}, path={target})"
        )


@pytest.fixture(autouse=True)
def _forbid_repo_sdd_writes(monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: C901
    """Hard-fail any test-time write mutation under repository .sdd."""
    original_open = builtins.open

    def guarded_builtin_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_repo_sdd_write(file, "open")
        return original_open(file, mode, *args, **kwargs)

    original_io_open = io.open

    def guarded_io_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_repo_sdd_write(file, "io.open")
        return original_io_open(file, mode, *args, **kwargs)

    original_path_open = Path.open

    def guarded_path_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any):  # noqa: ANN001
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_repo_sdd_write(self, "Path.open")
        return original_path_open(self, mode, *args, **kwargs)

    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes
    original_touch = Path.touch
    original_mkdir = Path.mkdir
    original_unlink = Path.unlink
    original_rename = Path.rename
    original_replace = Path.replace

    def guarded_write_text(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.write_text")
        return original_write_text(self, *args, **kwargs)

    def guarded_write_bytes(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.write_bytes")
        return original_write_bytes(self, *args, **kwargs)

    def guarded_touch(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.touch")
        return original_touch(self, *args, **kwargs)

    def guarded_mkdir(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.mkdir")
        return original_mkdir(self, *args, **kwargs)

    def guarded_unlink(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.unlink")
        return original_unlink(self, *args, **kwargs)

    def guarded_rename(self: Path, target: Any, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.rename-src")
        _guard_repo_sdd_write(target, "Path.rename-dst")
        return original_rename(self, target, *args, **kwargs)

    def guarded_replace(self: Path, target: Any, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.replace-src")
        _guard_repo_sdd_write(target, "Path.replace-dst")
        return original_replace(self, target, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
    monkeypatch.setattr(io, "open", guarded_io_open)
    monkeypatch.setattr(Path, "open", guarded_path_open)
    monkeypatch.setattr(Path, "write_text", guarded_write_text)
    monkeypatch.setattr(Path, "write_bytes", guarded_write_bytes)
    monkeypatch.setattr(Path, "touch", guarded_touch)
    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)
    monkeypatch.setattr(Path, "unlink", guarded_unlink)
    monkeypatch.setattr(Path, "rename", guarded_rename)
    monkeypatch.setattr(Path, "replace", guarded_replace)

    return


@pytest.fixture(autouse=True)
def _reap_subprocesses() -> Any:
    """Kill any child processes spawned during a test that outlive it.

    Prevents zombie / orphan subprocesses from blocking the session.
    """
    import os

    yield  # ← test runs here

    # After the test, check for leftover child processes.
    # waitpid/WNOHANG is POSIX-only; on Windows this cleanup is not available.
    if not hasattr(os, "waitpid") or not hasattr(os, "WNOHANG"):
        return
    try:
        while True:
            child_pid, _ = os.waitpid(-1, os.WNOHANG)
            if child_pid == 0:
                break
    except ChildProcessError:
        pass  # no children — normal case


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    """Cria uma estrutura de repositório fake para testes isolados."""
    config = get_governance_config()

    # Estrutura de Source (Fase 1)
    source_dir = tmp_path / config.get(
        "source_root", "docs/spec/canonical/core/policies"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    write_text_utf8(
        source_dir / "mandate.md",
        "# M001: Clean Architecture\n\n**Category**: Architecture\n**Owner**: Platform Team\n\nThis is a mandate.",
    )
    write_text_utf8(
        source_dir / "guidelines.md", "# G01: Test Guideline\n\nThis is a guideline."
    )

    # Estrutura de Artefatos Compilados (Fase 2 v3)
    compiled_dir = tmp_path / "compiler" / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)

    # Mock JSONs with fingerprints consistent with loader validation logic.
    core_items = [
        {
            "id": "M001",
            "type": "MANDATE",
            "title": "Clean Architecture",
            "criticality": "OBRIGATÓRIO",
            "category": "architecture",
            "customizable": False,
        }
    ]
    core_payload = {"items": core_items}

    import hashlib
    import json

    core_fingerprint = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    core_json = json.dumps({**core_payload, "fingerprint": core_fingerprint})

    client_items = [
        {
            "id": "G001",
            "type": "GUIDELINE",
            "title": "Test Guideline",
            "criticality": "OPCIONAL",
            "category": "quality",
            "customizable": True,
        }
    ]
    client_payload = {
        "items": client_items,
        "fingerprintpackages_salt": core_fingerprint,
    }
    client_fingerprint = hashlib.sha256(
        json.dumps(client_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    client_json = json.dumps({**client_payload, "fingerprint": client_fingerprint})

    write_text_utf8(compiled_dir / "governance-core.json", core_json)
    write_text_utf8(compiled_dir / "governance-client.json", client_json)
    write_text_utf8(compiled_dir / "governance-core.compiled.msgpack", "fake_msgpack")
    write_text_utf8(
        compiled_dir / "governance-client-template.compiled.msgpack", "fake_msgpack"
    )
    write_text_utf8(compiled_dir / "metadata-core.json", '{"version": "1.0.0"}')
    write_text_utf8(compiled_dir / "metadata-client.json", '{"version": "1.0.0"}')

    # Bootstrap defaults for Phase 1 existence check (governance_fetcher bootstrap)
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    write_text_utf8(sdd_dir / "governance-core.json", core_json)
    write_text_utf8(sdd_dir / "governance-client.json", client_json)

    return tmp_path
