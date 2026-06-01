# Client Onboarding & Runtime Observability — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two client-facing bugs (traceback on exit, stale NOT_CONNECTED cache) and unify onboarding so `sdd init --type client` completes setup in one command.

**Architecture:** Three independent layers: (1) quick fixes in `main.py` and `handshake_cache.py` that require no new files, (2) a new `OnboardingOrchestrator` service that `init.py` delegates to, (3) an expanded verbose diagnostic block in `runtime.py`. Each layer can be committed independently.

**Tech Stack:** Python 3.10+, typer, click, pytest, typer.testing.CliRunner, unittest.mock

---

## Task 1: Fix typer.Exit traceback in main.py

**Files:**

- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/main.py:267`
- Test: `tests/unit/cli/test_runtime_command.py`

**Step 1: Write the failing test**

Add to `tests/unit/cli/test_runtime_command.py`:

```python
class TestMainExitHandling:
    """typer.Exit must not leak as a raw traceback regardless of typer version."""

    def test_typer_exit_is_caught_by_main(self) -> None:
        """Simulate old-typer scenario where typer.Exit != click.exceptions.Exit."""
        import click.exceptions
        import typer

        # Verify the fix: main() must handle typer.Exit even if it is not
        # a subclass of click.exceptions.Exit (old typer versions).
        from sdd_cli.main import main

        with patch("sdd_cli.main.app") as mock_app:
            mock_app.side_effect = typer.Exit(3)
            result = main()
        assert result == 3
```

**Step 2: Run to confirm it fails**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestMainExitHandling -v
```

Expected: FAIL — `typer.Exit` propagates uncaught when it differs from `click.exceptions.Exit`.

**Step 3: Apply fix**

In `packages/interfaces/sdd_cli/src/sdd_cli/main.py`, line 267:

```python
# Before:
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)

# After:
    except (click.exceptions.Exit, typer.Exit) as exc:
        return int(exc.exit_code)
```

**Step 4: Run test**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestMainExitHandling -v
```

Expected: PASS

**Step 5: Commit**

```
git add packages/interfaces/sdd_cli/src/sdd_cli/main.py \
        tests/unit/cli/test_runtime_command.py
git commit -m "fix: catch typer.Exit in main() to prevent traceback on non-zero exit"
```

---

## Task 2: Never cache NOT_CONNECTED state

**Files:**

- Modify: `packages/core/sdd_core/src/sdd_core/governance/handshake_cache.py:41-56` (load_cache)
- Modify: `packages/core/sdd_core/src/sdd_core/governance/handshake_cache.py:116-163` (save_cache)
- Test: `tests/unit/cli/test_runtime_command.py`

**Background:** `load_cache` serves any cached state within TTL. `save_cache` writes every state including `NOT_CONNECTED`. A client who runs `sdd runtime status` mid-onboarding gets a `NOT_CONNECTED` entry that blocks subsequent runs for 30 minutes.

**Step 1: Write failing tests**

Add to `tests/unit/cli/test_runtime_command.py`:

```python
class TestHandshakeCacheNotConnected:
    """NOT_CONNECTED must never be read from or written to cache."""

    def test_load_cache_rejects_not_connected(self, tmp_path: Path) -> None:
        import json
        from datetime import datetime, timedelta

        from sdd_core.governance.handshake_cache import HandshakeCache

        cache_dir = tmp_path / ".sdd" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"
        cache_file.write_text(
            json.dumps({
                "state": "NOT_CONNECTED",
                "last_check": datetime.now().isoformat(),
                "confidence": 0.0,
                "gap_version": "1.0",
                "status": "NOT_ACTIVE",
                "checks": [],
                "mandates_loaded": [],
                "skill_profile": "default",
                "spec_fingerprint": "",
                "agent_id": "test",
            }),
            encoding="utf-8",
        )
        cache = HandshakeCache(
            cache_file, cache_dir, timedelta(minutes=30), tmp_path, "test-agent"
        )
        assert cache.load_cache() is None

    def test_save_cache_skips_not_connected(self, tmp_path: Path) -> None:
        from datetime import timedelta

        from sdd_core.governance.handshake_cache import HandshakeCache

        cache_dir = tmp_path / ".sdd" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"
        cache = HandshakeCache(
            cache_file, cache_dir, timedelta(minutes=30), tmp_path, "test-agent"
        )
        cache.save_cache("NOT_CONNECTED", [], 0.0, "default")
        assert not cache_file.exists()
```

**Step 2: Run to confirm they fail**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestHandshakeCacheNotConnected -v
```

Expected: FAIL — cache currently reads and writes NOT_CONNECTED.

**Step 3: Apply fix to load_cache**

In `packages/core/sdd_core/src/sdd_core/governance/handshake_cache.py`, method `load_cache` (line ~41):

```python
def load_cache(self) -> dict[str, Any] | None:
    """Load cached state if still valid."""
    if not self.cache_file.exists():
        return None

    try:
        with open(self.cache_file, encoding="utf-8") as f:
            cache = cast(dict[str, Any], json.load(f))

        if cache.get("state") == "NOT_CONNECTED":
            return None  # never serve transient setup state from cache

        last_check = datetime.fromisoformat(cache.get("last_check", ""))
        if (datetime.now() - last_check) < self.cache_ttl:
            return cache
    except Exception as exc:
        logger.warning("Failed to load AHP cache: %s", exc)

    return None
```

**Step 4: Apply fix to save_cache**

At the top of the `save_cache` method body (line ~124), add an early return:

```python
def save_cache(
    self,
    state: str,
    checks: list[dict[str, Any]],
    confidence: float,
    skill_profile: str,
) -> None:
    """Save state to persistent cache with GAP fields."""
    if state == "NOT_CONNECTED":
        return  # transient setup state; never persist
    try:
        # ... rest of existing implementation unchanged
```

**Step 5: Run tests**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestHandshakeCacheNotConnected -v
```

Expected: PASS

**Step 6: Run full unit suite to check no regressions**

```bash
pytest tests/unit/ -x -q
```

Expected: all pass

**Step 7: Commit**

```
git add packages/core/sdd_core/src/sdd_core/governance/handshake_cache.py \
        tests/unit/cli/test_runtime_command.py
git commit -m "fix: never cache NOT_CONNECTED handshake state to prevent stale onboarding blocks"
```

---

## Task 3: Auto-heal stale NOT_CONNECTED in handshake.validate()

**Files:**

- Modify: `packages/core/sdd_core/src/sdd_core/governance/handshake.py:286-316` (validate method, cache-hit branch)
- Test: `tests/unit/cli/test_runtime_command.py`

**Background:** Even after Task 2, old cache files created before the fix may still exist with `NOT_CONNECTED`. The auto-heal ensures a full revalidation whenever cached state is `NOT_CONNECTED` and `.sdd/` exists.

**Step 1: Write failing test**

```python
class TestHandshakeAutoHeal:
    """If cache says NOT_CONNECTED but .sdd/ now exists, revalidate."""

    def test_auto_heal_discards_not_connected_cache_when_sdd_exists(
        self, tmp_path: Path
    ) -> None:
        import json
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock, patch

        from sdd_core.governance.handshake import AgentHandshakeProtocol

        (tmp_path / ".sdd").mkdir()

        # Write a stale NOT_CONNECTED cache (pre-fix format)
        cache_dir = tmp_path / ".sdd" / "runtime"
        cache_dir.mkdir()
        cache_file = cache_dir / "governance-state.json"
        cache_file.write_text(
            json.dumps({
                "state": "NOT_CONNECTED",
                "last_check": datetime.now().isoformat(),
                "confidence": 0.0,
                "gap_version": "1.0",
                "status": "NOT_ACTIVE",
                "checks": [],
                "mandates_loaded": [],
                "skill_profile": "default",
                "spec_fingerprint": "",
                "agent_id": "test",
            }),
            encoding="utf-8",
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        # Patch the validator to return PARTIAL (not NOT_CONNECTED)
        with patch.object(ahp._validator, "layer_1_discovery", return_value=("CONNECTED", [])), \
             patch.object(ahp._validator, "layer_2_link_validation", return_value=("CONNECTED", [])), \
             patch.object(ahp._validator, "layer_3_runtime_validation", return_value=("INITIALIZED", [])), \
             patch.object(ahp._validator, "layer_4_governance_health", return_value=("UNKNOWN", [])):
            state, _ = ahp.validate()

        assert state != "NOT_CONNECTED"
```

**Step 2: Run to confirm it fails**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestHandshakeAutoHeal -v
```

Expected: FAIL — validate() currently returns cached NOT_CONNECTED.

**Step 3: Apply fix in validate()**

In `packages/core/sdd_core/src/sdd_core/governance/handshake.py`, in the `validate` method, after the cache is loaded (line ~288), add the auto-heal check before returning:

```python
if not force_recheck:
    cache = self._load_cache()
    if cache:
        cached_state = cache.get("state", "")
        # Auto-heal: stale NOT_CONNECTED cache when .sdd/ now exists
        if cached_state == "NOT_CONNECTED" and (self.project_root / ".sdd").is_dir():
            cache = None  # discard; fall through to full revalidation

    if cache:
        # ... existing cache-hit branch unchanged
```

**Step 4: Run test**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestHandshakeAutoHeal -v
```

Expected: PASS

**Step 5: Commit**

```
git add packages/core/sdd_core/src/sdd_core/governance/handshake.py \
        tests/unit/cli/test_runtime_command.py
git commit -m "fix: auto-heal stale NOT_CONNECTED cache when .sdd/ directory exists"
```

---

## Task 4: Wrap PathPolicyViolation in runtime status

**Files:**

- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/runtime.py:37-51`
- Test: `tests/unit/cli/test_runtime_command.py`

**Background:** `enforce_path_policy` raises `PathPolicyViolation` (a `ValueError` subclass) when the workspace path is outside permitted locations. Today this propagates as a raw traceback.

**Step 1: Write failing test**

```python
class TestRuntimeStatusPathPolicy:
    """PathPolicyViolation must surface as a clean error message, not a traceback."""

    def test_path_policy_violation_exits_2(self, tmp_path: Path) -> None:
        from sdd_cli.utils.sdd_authority import PathPolicyViolation

        with (
            patch(
                "sdd_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.commands.runtime.enforce_path_policy",
                side_effect=PathPolicyViolation(
                    requested_path=tmp_path,
                    reason="outside permitted paths",
                    hint="use SDD_WORKSPACE_ROOT",
                ),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)
        assert exc_info.value.exit_code == 2
```

**Step 2: Run to confirm it fails**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestRuntimeStatusPathPolicy -v
```

Expected: FAIL — PathPolicyViolation propagates uncaught.

**Step 3: Apply fix in runtime.py**

In `packages/interfaces/sdd_cli/src/sdd_cli/commands/runtime.py`, wrap the `enforce_path_policy` call (around line 37):

```python
from sdd_cli.utils.sdd_authority import (
    PathPolicyViolation,   # add this to existing import
    compiled_active_dir,
    enforce_path_policy,
    profile_active_path,
    resolve_workspace_root,
)

# In status():
    root = resolve_workspace_root()
    try:
        root = enforce_path_policy(root, workspace_root=root, mode="normal")
    except PathPolicyViolation as exc:
        typer.echo(
            f"[SDD] ERROR: workspace path rejected — {exc.reason}\n  Hint: {exc.hint}",
            err=True,
        )
        raise typer.Exit(2) from exc
```

**Step 4: Run test**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestRuntimeStatusPathPolicy -v
```

Expected: PASS

**Step 5: Commit**

```
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/runtime.py \
        tests/unit/cli/test_runtime_command.py
git commit -m "fix: convert PathPolicyViolation to clean error message in runtime status"
```

---

## Task 5: Add verbose diagnostic block to runtime status

**Files:**

- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/runtime.py`
- Test: `tests/unit/cli/test_runtime_command.py`

**Step 1: Write failing test**

```python
class TestRuntimeStatusVerboseDiagnostics:
    """--verbose must print workspace root and per-layer diagnostic block."""

    def test_verbose_prints_workspace_root(self, tmp_path: Path, capsys) -> None:
        ahp_instance = _make_ahp_patch("HEALTHY")
        ahp_instance.format_combined_output.return_value = "[state=HEALTHY]"

        with (
            patch("sdd_core.utils.environment.find_workspace_root", return_value=tmp_path),
            patch("sdd_cli.commands.runtime.enforce_path_policy", return_value=tmp_path),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", return_value=ahp_instance),
            patch("sdd_cli.commands.runtime._emit_runtime_status", return_value={}),
            patch("sdd_cli.commands.runtime._show_ask_confidence", return_value=""),
            patch("sdd_runtime.format_governance_footer", return_value=""),
        ):
            ctx = MagicMock()
            ctx.obj = {}
            status(ctx=ctx, verbose=True, force=False, update_cache=False)

        captured = capsys.readouterr()
        assert "workspace root" in captured.out
        assert str(tmp_path) in captured.out
```

**Step 2: Run to confirm it fails**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestRuntimeStatusVerboseDiagnostics -v
```

Expected: FAIL — verbose output does not include "workspace root".

**Step 3: Implement `_format_diagnostic_block` helper in runtime.py**

Add this function near the other display helpers (~line 402):

```python
def _format_diagnostic_block(
    root: Path,
    cache_file: Path,
    report: Any,
) -> str:
    """Return the verbose diagnostic header block."""
    import importlib.metadata

    lines = ["═══ SDD Runtime Diagnostics ═══"]

    lines.append(f"workspace root : {root}")

    profile_path = profile_active_path(root)
    profile_type = _read_profile(root) or "unknown"
    lines.append(
        f"profile file   : {profile_path.relative_to(root) if profile_path.exists() else 'NOT FOUND'}"
        f" [type={profile_type}]"
    )

    if cache_file.exists():
        import json as _json
        import time

        try:
            mtime = cache_file.stat().st_mtime
            age_sec = int(time.time() - mtime)
            raw = _json.loads(cache_file.read_text(encoding="utf-8"))
            cached_state = raw.get("state", "?")
            lines.append(
                f"cache file     : {cache_file.relative_to(root)}"
                f" [age={age_sec}s, state={cached_state}]"
            )
        except Exception:
            lines.append(f"cache file     : {cache_file.relative_to(root)} [unreadable]")
    else:
        lines.append("cache file     : .sdd/runtime/governance-state.json [NONE, revalidating]")

    for pkg in ("sdd-core", "sdd-cli"):
        try:
            ver = importlib.metadata.version(pkg)
            lines.append(f"{pkg:<14} : {ver}")
        except importlib.metadata.PackageNotFoundError:
            pass

    return "\n".join(lines)
```

**Step 4: Call it in `status()` when verbose**

In `status()`, after `output_mode` is set and before `ahp.validate()`, add:

```python
    if effective_verbose and not output_json:
        cache_file = root / ".sdd" / "runtime" / "governance-state.json"
        diag = _format_diagnostic_block(root, cache_file, None)
        typer.echo(diag)
        typer.echo("")
```

**Step 5: Run test**

```bash
pytest tests/unit/cli/test_runtime_command.py::TestRuntimeStatusVerboseDiagnostics -v
```

Expected: PASS

**Step 6: Manual smoke test**

```bash
sdd runtime status --verbose
```

Expected: diagnostic header with `workspace root`, `profile file`, `cache file` printed before the layer report.

**Step 7: Commit**

```
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/runtime.py \
        tests/unit/cli/test_runtime_command.py
git commit -m "feat: add workspace root and cache diagnostics to runtime status --verbose"
```

---

## Task 6: Create OnboardingOrchestrator service

**Files:**

- Create: `packages/interfaces/sdd_cli/src/sdd_cli/services/onboarding.py`
- Test: `packages/interfaces/sdd_cli/tests/test_onboarding_service.py` (new)

**Step 1: Write failing tests**

Create `packages/interfaces/sdd_cli/tests/test_onboarding_service.py`:

```python
"""Tests for OnboardingOrchestrator service."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from sdd_cli.services.onboarding import OnboardingOrchestrator, OnboardingResult

pytestmark = pytest.mark.unit


class TestOnboardingOrchestrator:
    def test_step_governance_skipped_when_artifacts_exist(self, tmp_path: Path) -> None:
        """governance generate is skipped if governance-core.json already exists."""
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            orc.step_governance(force=False)
        mock_run.assert_not_called()

    def test_step_governance_runs_when_force(self, tmp_path: Path) -> None:
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            orc.step_governance(force=True)
        mock_run.assert_called_once()

    def test_run_stops_on_first_failure(self, tmp_path: Path) -> None:
        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "step_governance", return_value=False):
            result = orc.run(force=False)
        assert result.success is False
        assert result.failed_step == "governance"

    def test_run_returns_success_when_all_pass(self, tmp_path: Path) -> None:
        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
        ):
            result = orc.run(force=False)
        assert result.success is True
        assert result.failed_step is None
```

**Step 2: Run to confirm they fail**

```bash
pytest packages/interfaces/sdd_cli/tests/test_onboarding_service.py -v
```

Expected: FAIL — module does not exist.

**Step 3: Implement OnboardingOrchestrator**

Create `packages/interfaces/sdd_cli/src/sdd_cli/services/onboarding.py`:

```python
"""OnboardingOrchestrator — orchestrates client workspace bootstrap."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import typer

from sdd_core.utils.process import SafeProcessRunner


@dataclass
class OnboardingResult:
    success: bool
    failed_step: str | None = None
    messages: list[str] = field(default_factory=list)


class OnboardingOrchestrator:
    """Orchestrates the 3-step client workspace bootstrap sequence."""

    TOTAL_STEPS = 3

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    def _run_step(self, label: str, args: list[str]) -> bool:
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        runner = SafeProcessRunner()
        result = runner.run(
            ["sdd"] + args,
            cwd=self.cwd,
            env=env,
            capture_output=False,
        )
        return result.success

    def step_governance(self, *, force: bool) -> bool:
        """[2/3] Generate governance artifacts."""
        compiled = self.cwd / ".sdd" / "compiled" / "governance-core.json"
        if not force and compiled.exists():
            typer.echo("[2/3] Generating governance artifacts... (skipped — already compiled)")
            return True
        typer.echo("[2/3] Generating governance artifacts...")
        ok = self._run_step(
            "governance generate",
            ["governance", "generate", "--full-bootstrap"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} governance generate")
        return ok

    def step_skills(self, *, force: bool) -> bool:
        """[3/3] Initialize skills."""
        seeds_dir = self.cwd / ".sdd" / "skills"
        if not force and seeds_dir.exists() and any(seeds_dir.iterdir()):
            typer.echo("[3/3] Initializing skills... (skipped — already seeded)")
            return True
        typer.echo("[3/3] Initializing skills...")
        ok = self._run_step(
            "skills bootstrap",
            ["skills", "--full-bootstrap", "--regenerate-seeds"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} skills bootstrap")
        return ok

    def step_validate(self) -> bool:
        """[4/4] Validate runtime state."""
        typer.echo("[4/4] Validating runtime state...")
        ok = self._run_step(
            "runtime status",
            ["runtime", "status", "--force"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} runtime status")
        return ok

    def run(self, *, force: bool) -> OnboardingResult:
        """Run full bootstrap sequence. Stops on first failure."""
        if not self.step_governance(force=force):
            return OnboardingResult(
                success=False,
                failed_step="governance",
                messages=["governance generate failed — re-run with --verbose for detail"],
            )
        if not self.step_skills(force=force):
            return OnboardingResult(
                success=False,
                failed_step="skills",
                messages=["skills bootstrap failed — check permissions and seed files"],
            )
        if not self.step_validate():
            return OnboardingResult(
                success=False,
                failed_step="validate",
                messages=[
                    "workspace initialized but governance not active",
                    "run: sdd runtime status --verbose",
                ],
            )
        return OnboardingResult(success=True)
```

**Step 4: Run tests**

```bash
pytest packages/interfaces/sdd_cli/tests/test_onboarding_service.py -v
```

Expected: PASS

**Step 5: Commit**

```
git add packages/interfaces/sdd_cli/src/sdd_cli/services/onboarding.py \
        packages/interfaces/sdd_cli/tests/test_onboarding_service.py
git commit -m "feat: add OnboardingOrchestrator service for client workspace bootstrap"
```

---

## Task 7: Refactor init.py — bootstrap default for --type client

**Files:**

- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/init.py`
- Test: `packages/interfaces/sdd_cli/tests/test_init.py`

**Background:** Currently `--full-bootstrap` is opt-in (default False) for all types, and it uses `_run_cli_step` inline. The new design makes bootstrap the default when `--type client`, with `--no-bootstrap` to opt out. The `OnboardingOrchestrator` handles steps 2-4; `init.py` keeps only step 1 (profile creation).

**Step 1: Write failing tests**

Add to `packages/interfaces/sdd_cli/tests/test_init.py`:

```python
class TestBootstrapDefault:
    """--type client runs bootstrap by default; --no-bootstrap skips it."""

    def test_client_type_runs_orchestrator_by_default(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from sdd_cli.commands.init import app

        runner = CliRunner()
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
            patch("sdd_core.utils.environment.write_profile") as mock_profile,
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_profile.return_value = MagicMock(type="client", name="test", workspace_id="abc")
            MockOrch.return_value.run.return_value = MagicMock(
                success=True, failed_step=None, messages=[]
            )
            result = runner.invoke(app, ["--type", "client", "--name", "test", "--force"])
        MockOrch.return_value.run.assert_called_once_with(force=True)
        assert result.exit_code == 0

    def test_no_bootstrap_skips_orchestrator(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from sdd_cli.commands.init import app

        runner = CliRunner()
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
            patch("sdd_core.utils.environment.write_profile") as mock_profile,
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_profile.return_value = MagicMock(type="client", name="test", workspace_id="abc")
            result = runner.invoke(
                app, ["--type", "client", "--name", "test", "--no-bootstrap", "--force"]
            )
        MockOrch.assert_not_called()
        assert result.exit_code == 0

    def test_master_type_does_not_bootstrap_by_default(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from sdd_cli.commands.init import app

        runner = CliRunner()
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
            patch("sdd_core.utils.environment.write_profile") as mock_profile,
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_profile.return_value = MagicMock(type="master", name="test", workspace_id="abc")
            result = runner.invoke(app, ["--type", "master", "--force"])
        MockOrch.assert_not_called()
        assert result.exit_code == 0

    def test_orchestrator_failure_exits_nonzero(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from sdd_cli.commands.init import app
        from sdd_cli.services.onboarding import OnboardingResult

        runner = CliRunner()
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
            patch("sdd_core.utils.environment.write_profile") as mock_profile,
            patch("sdd_cli.commands.init.OnboardingOrchestrator") as MockOrch,
        ):
            mock_profile.return_value = MagicMock(type="client", name="test", workspace_id="abc")
            MockOrch.return_value.run.return_value = OnboardingResult(
                success=False,
                failed_step="governance",
                messages=["governance generate failed"],
            )
            result = runner.invoke(app, ["--type", "client", "--force"])
        assert result.exit_code != 0
```

**Step 2: Run to confirm they fail**

```bash
pytest packages/interfaces/sdd_cli/tests/test_init.py::TestBootstrapDefault -v
```

Expected: FAIL — `OnboardingOrchestrator` not imported, `--no-bootstrap` flag doesn't exist.

**Step 3: Refactor init.py**

Replace the `full_bootstrap` option and its handling with:

```python
# In imports, add:
from sdd_cli.services.onboarding import OnboardingOrchestrator

# Replace the full_bootstrap option with:
    no_bootstrap: bool = typer.Option(
        False,
        "--no-bootstrap",
        help="Skip governance and skills bootstrap (profile only). Default for --type master.",
    ),

# Replace the full_bootstrap block (lines 144-169) with:
    run_bootstrap = (profile_type == "client") and not no_bootstrap
    if run_bootstrap:
        typer.echo("")
        typer.echo("[1/4] Workspace profile created ✓")
        orc = OnboardingOrchestrator(cwd)
        result = orc.run(force=bool(force))
        if result.success:
            typer.echo("\n🟢 Onboarding complete — workspace is HEALTHY")
        else:
            for msg in result.messages:
                typer.echo(f"  ERROR: {msg}", err=True)
            raise typer.Exit(2)
    else:
        typer.echo("")
        typer.echo("Next steps:")
        typer.echo("  sdd governance generate --full-bootstrap")
        typer.echo("  sdd skills --full-bootstrap --regenerate-seeds")
        typer.echo("  sdd runtime status")
```

**Step 4: Run new tests**

```bash
pytest packages/interfaces/sdd_cli/tests/test_init.py -v
```

Expected: all pass (including pre-existing tests via `--no-bootstrap` path).

**Step 5: Run full init test suite**

```bash
pytest packages/interfaces/sdd_cli/tests/test_init.py -v
```

Expected: all PASS

**Step 6: Commit**

```
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/init.py \
        packages/interfaces/sdd_cli/tests/test_init.py
git commit -m "feat: make client bootstrap default in sdd init --type client; add --no-bootstrap"
```

---

## Task 8: Integration test — full onboarding in tmp workspace

**Files:**

- Create: `tests/integration/cli/test_onboarding_flow.py`

**Step 1: Write integration test**

Create `tests/integration/cli/test_onboarding_flow.py`:

```python
"""Integration test: OnboardingOrchestrator full flow in a temporary workspace."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_cli.services.onboarding import OnboardingOrchestrator, OnboardingResult

pytestmark = pytest.mark.integration


class TestOnboardingOrchestratorIntegration:
    def test_orchestrator_stops_on_governance_failure(self, tmp_path: Path) -> None:
        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=False):
            result = orc.run(force=True)
        assert result.success is False
        assert result.failed_step == "governance"

    def test_orchestrator_skips_governance_when_artifacts_exist_no_force(
        self, tmp_path: Path
    ) -> None:
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text('{"items":[]}', encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        steps_called: list[str] = []

        original_run_step = orc._run_step

        def spy_run_step(label: str, args: list[str]) -> bool:
            steps_called.append(label)
            return True

        with (
            patch.object(orc, "_run_step", side_effect=spy_run_step),
        ):
            result = orc.run(force=False)

        assert "governance generate" not in steps_called
        assert result.success is True

    def test_orchestrator_reruns_all_with_force(self, tmp_path: Path) -> None:
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text('{"items":[]}', encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        steps_called: list[str] = []

        def spy_run_step(label: str, args: list[str]) -> bool:
            steps_called.append(label)
            return True

        with patch.object(orc, "_run_step", side_effect=spy_run_step):
            result = orc.run(force=True)

        assert "governance generate" in steps_called
        assert result.success is True
```

**Step 2: Run integration tests**

```bash
pytest tests/integration/cli/test_onboarding_flow.py -v
```

Expected: PASS

**Step 3: Commit**

```
git add tests/integration/cli/test_onboarding_flow.py
git commit -m "test: add integration tests for OnboardingOrchestrator flow"
```

---

## Task 9: Run full test suite and verify

**Step 1: Run all unit tests**

```bash
pytest tests/unit/ -x -q
```

Expected: all pass, no regressions.

**Step 2: Run all integration tests**

```bash
pytest tests/integration/ -x -q
```

Expected: all pass.

**Step 3: Run sdd_cli package tests**

```bash
pytest packages/interfaces/sdd_cli/tests/ -x -q
```

Expected: all pass.

**Step 4: Run sdd_core package tests**

```bash
pytest packages/core/sdd_core/tests/ -x -q
```

Expected: all pass.

**Step 5: Smoke test the full onboarding command**

```bash
sdd init --type client --name smoke-test --force --no-bootstrap
sdd runtime status --verbose
```

Expected: diagnostic block shows `workspace root`, no traceback on any exit code.
