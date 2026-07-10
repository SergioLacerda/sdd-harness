# `sdd ask` Phase-Level Trace Route Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Give `sdd ask` phase-level latency attribution (child `governance.ask.phase` events under the existing `governance.ask` parent) so operators can tell whether slowness is in local CLI/FS work, governance snapshot loading, response rendering, telemetry emission, or (when observable) external LLM exchange — without changing any existing `sdd ask` policy behavior.

**Architecture:** Add a small `@contextmanager` phase-timer helper used around existing pipeline steps in `_ask_backend/_pipeline_runtime.py` / `_pipeline_session.py`. Each timed phase emits a child `RuntimeEvent` (`event="governance.ask.phase"`) sharing the parent's `trace_id`, with `parent_event_id` set to the parent event's `span_id`. Phase semantics (`phase_id`, `latency_domain`, `measurement_quality`, `observed_by`) live in `RuntimeEvent.details` (no new dataclass fields needed — confirmed `trace_id`/`span_id`/`parent_event_id` already exist on `RuntimeEvent`). A new `AskLatencyCollector` in `sdd_runtime.metrics` (modeled on the existing `TokenEconomyCollector` pattern) aggregates phase events for `sdd telemetry summary`. `governance.ask.phase` must be added to `_MANDATORY_EVENTS` in `sdd_runtime/telemetry/_constants.py` or phase events will be silently dropped in the default `passive` logging mode (verified: `_sink.py:165` only persists events in `_MANDATORY_EVENTS` when in passive mode).

**Tech Stack:** Python 3.10+, typer (CLI), pytest, existing `RuntimeEvent`/`TelemetrySink`/`TelemetryReader` runtime-event infrastructure.

---

## Ground Truth (from codebase investigation — do not re-derive, verify only if suspicious)

- `sdd ask` entry chain: `commands/ask_entry.py` → `_ask_backend/_pipeline.py::ask_cmd()` → `_ask_backend/_pipeline_runtime.py::_ask_cmd_impl()`.
- `_ask_cmd_impl()` steps in order: `normalize_ask_inputs()` → `_start_ask_session(query)` (`_pipeline_session.py:71`, generates `trace_id` via `uuid.uuid4()` at line 98, captures `start_mono = time.monotonic()` at line 74 **before** `_guard_budget_breach()`, `_resolve_workspace_root()`, `_run_organize_intake()`, `_guard_handshake()`, `_get_profile_state()`, `_emit_state_warnings()` all run with **no intermediate timing today**) → `_load_ask_snapshot(inputs, session)` (`_pipeline_session.py:104`, calls `build_governed_ask_snapshot()`) → `_sync_ask_runtime()` (`_pipeline_runtime.py`, computes `duration_ms`, calls `_backend._emit_ask_telemetry("governance.ask", ...)` at line 82) → `emit_ask_response()` (`_pipeline_runtime_support.py:94`, dispatches to `ask_response.py` text or `ask_response_json.py` JSON).
- `RuntimeEvent` (`sdd_runtime/_events/_runtime_event.py:24-91`) already has `trace_id`, `span_id` (auto-generated UUID hex[:16] if unset), `parent_event_id` (defaults to `""`), `duration_ms`, `start_ts`, `end_ts`, `path_id`, `details: dict`. **No schema change needed** for the phase-tree model.
- `TelemetrySink._should_persist()` (`sdd_runtime/telemetry/_sink.py:161-165`): in `passive` mode (the default for `sdd ask`), only events in `_MANDATORY_EVENTS` (`sdd_runtime/telemetry/_constants.py:43-53`) are persisted. Currently contains `"governance.ask"` and `"governance.ask.full"` but not `"governance.ask.phase"` — **must add it** or every phase event silently vanishes.
- Only one metrics collector exists today: `TokenEconomyCollector` (`sdd_runtime/metrics/_collector.py:17`). Pattern: no-arg constructor loads its own config, `ingest(event_or_dict)` filters by `event` field name and mutates an internal dataclass snapshot under a `threading.RLock()`, `from_reader(cls, reader)` classmethod replays a `TelemetryReader`, `snapshot()` returns a deep-copied immutable dataclass, `reset()` clears state.
- `commands/telemetry.py` has `status`, `dump`, `query`, `init` subcommands — **no `summary` subcommand exists**. `query` filters: `--event-type`, `--status`, `--level`, `--trace-id`, `--since`/`--from`, `--until`/`--to`, `--work-item`, `--limit` (via `services/telemetry_handler.py::filter_events()`). No `phase_id`/`latency_domain`/`path_id` filters exist.
- `ask_response_json.py` currently only gates a `steps` array (2 coarse PARSE/CONTEXT_LOAD entries) and `log_format` behind `inputs.full` — no timing breakdown exists in either text or JSON output today.
- **No existing `Stopwatch`/`Timer` utility anywhere in `sdd_core`/`sdd_runtime`/`sdd_cli`.** Must write a small new phase-timer helper from scratch.
- Two separate env vars resolve the compliance-events JSONL path: `SDD_COMPLIANCE_EVENTS_PATH` (used by ask telemetry, via `sdd_cli/services/... /telemetry_paths.py`) and `SDD_TELEMETRY_PATH` (used by `commands/telemetry.py::_default_events_path()`). They can diverge silently today (design doc SQ-002).
- Relevant existing tests to imitate: `test_ask_telemetry_emit.py`, `test_ask_telemetry_path_id.py`, `test_telemetry_dump_query_command.py`, `test_telemetry_init_status_command.py`.

## Non-Goals (do not do these)

- Do not optimize the ask pipeline itself — this plan only instruments it.
- Do not merge latency aggregation into `TokenEconomyCollector` — build a separate `AskLatencyCollector`.
- Do not treat estimated token counts as evidence of LLM latency.
- Do not change `intake_index_mode: none` semantics — `light_input` + `execution_gate=allowed` stays allowed; add a regression test, don't touch the logic unless a test proves it's broken.
- Do not infer `ask.external.llm_exchange` timing when no real exchange/adapter timing is observable — omit the phase or mark `measurement_quality="not_observed"`, never fabricate `0ms`.

---

### Task 1: Phase timer helper

**Files:**
- Create: `packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_phase_timer.py`
- Test: `packages/interfaces/sdd_cli/tests/test_ask_phase_timer.py`

**Step 1: Write the failing test**

```python
"""Tests for the ask-pipeline phase timer helper."""
from __future__ import annotations

import time

from sdd_cli.commands._ask_backend._phase_timer import PhaseRecord, PhaseTimer


def test_phase_timer_records_single_phase():
    timer = PhaseTimer()
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        time.sleep(0.01)

    records = timer.records()
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, PhaseRecord)
    assert record.phase_id == "ask.workspace.resolve"
    assert record.latency_domain == "local_fs"
    assert record.duration_ms >= 10
    assert record.start_ts < record.end_ts
    assert record.measurement_quality == "measured"
    assert record.observed_by == "sdd_cli"
    assert record.failed is False


def test_phase_timer_records_multiple_phases_in_order():
    timer = PhaseTimer()
    with timer.phase("ask.cli.entry", latency_domain="local_cli"):
        pass
    with timer.phase("ask.response.render", latency_domain="rendering"):
        pass

    ids = [r.phase_id for r in timer.records()]
    assert ids == ["ask.cli.entry", "ask.response.render"]


def test_phase_timer_marks_failed_phase_and_reraises():
    timer = PhaseTimer()
    try:
        with timer.phase("ask.governance.snapshot", latency_domain="governance"):
            raise ValueError("boom")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError to propagate")

    records = timer.records()
    assert len(records) == 1
    assert records[0].failed is True


def test_phase_timer_total_and_unattributed_ms():
    timer = PhaseTimer()
    with timer.phase("ask.cli.entry", latency_domain="local_cli"):
        time.sleep(0.01)

    total_ms = timer.phase_total_ms()
    assert total_ms >= 10

    unattributed = timer.unattributed_ms(session_duration_ms=total_ms + 50)
    assert unattributed == 50
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_phase_timer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sdd_cli.commands._ask_backend._phase_timer'`

**Step 3: Write minimal implementation**

```python
"""Phase timer helper for `sdd ask` trace-route instrumentation.

Records wall-clock timing for named pipeline phases without changing the
behavior of the phases themselves. See
.analysis/refined/sdd-ask-traceroute-20260709/design.md for the event model
this feeds into.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PhaseRecord:
    """A single measured phase in an `sdd ask` invocation."""

    phase_id: str
    latency_domain: str
    duration_ms: int
    start_ts: str
    end_ts: str
    measurement_quality: str = "measured"
    observed_by: str = "sdd_cli"
    failed: bool = False


@dataclass
class PhaseTimer:
    """Collects `PhaseRecord`s for the phases of one `sdd ask` invocation."""

    _records: list[PhaseRecord] = field(default_factory=list)

    @contextmanager
    def phase(
        self,
        phase_id: str,
        *,
        latency_domain: str,
        measurement_quality: str = "measured",
        observed_by: str = "sdd_cli",
    ) -> Iterator[None]:
        start_mono = time.monotonic()
        start_ts = _utc_now_iso()
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            end_ts = _utc_now_iso()
            duration_ms = int((time.monotonic() - start_mono) * 1000)
            self._records.append(
                PhaseRecord(
                    phase_id=phase_id,
                    latency_domain=latency_domain,
                    duration_ms=duration_ms,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    measurement_quality=measurement_quality,
                    observed_by=observed_by,
                    failed=failed,
                )
            )

    def records(self) -> list[PhaseRecord]:
        return list(self._records)

    def phase_total_ms(self) -> int:
        return sum(r.duration_ms for r in self._records)

    def unattributed_ms(self, *, session_duration_ms: int) -> int:
        return max(0, session_duration_ms - self.phase_total_ms())
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_phase_timer.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_phase_timer.py packages/interfaces/sdd_cli/tests/test_ask_phase_timer.py
git commit -m "feat(ask): add phase timer helper for trace-route instrumentation"
```

---

### Task 2: Add `governance.ask.phase` to mandatory events (so it isn't dropped in passive mode)

**Files:**
- Modify: `packages/core/sdd_runtime/src/sdd_runtime/telemetry/_constants.py:43-53`
- Test: `packages/core/sdd_runtime/tests/test_telemetry_constants.py` (create if it doesn't exist — check first: `find packages/core/sdd_runtime/tests -iname "*constants*"`)

**Step 1: Write the failing test**

```python
"""Tests for telemetry constants — mandatory event allowlist."""
from sdd_runtime.telemetry._constants import _MANDATORY_EVENTS


def test_governance_ask_phase_is_mandatory():
    assert "governance.ask.phase" in _MANDATORY_EVENTS


def test_existing_mandatory_events_unchanged():
    assert "governance.ask" in _MANDATORY_EVENTS
    assert "governance.ask.full" in _MANDATORY_EVENTS
    assert "governance.violation" in _MANDATORY_EVENTS
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/sdd_runtime/tests/test_telemetry_constants.py -v`
Expected: FAIL — `test_governance_ask_phase_is_mandatory` fails, `AssertionError`

**Step 3: Write minimal implementation**

Edit `_constants.py` line 43-53:

```python
_MANDATORY_EVENTS = frozenset(
    {
        "governance.violation",
        "runtime.drift.detected",
        "policy.validation.fail",
        "runtime.session.start",
        "governance.ask",
        "governance.ask.full",
        "governance.ask.phase",
        ECONOMY_BUDGET_BREACH,
    }
)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/sdd_runtime/tests/test_telemetry_constants.py -v`
Expected: PASS (2 tests)

Also run the full existing telemetry sink test suite to confirm no regression:

Run: `uv run pytest packages/core/sdd_runtime/tests -k telemetry -q`
Expected: all PASS

**Step 5: Commit**

```bash
git add packages/core/sdd_runtime/src/sdd_runtime/telemetry/_constants.py packages/core/sdd_runtime/tests/test_telemetry_constants.py
git commit -m "feat(telemetry): persist governance.ask.phase events in passive mode"
```

---

### Task 3: Emit child phase events with parent/child trace linkage

**Files:**
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_pipeline_runtime.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_pipeline_session.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_telemetry.py`
- Test: `packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py`

**Read first:** `_pipeline_runtime.py` (`_ask_cmd_impl`, `_sync_ask_runtime`), `_pipeline_session.py` (`_start_ask_session`, `_load_ask_snapshot`), `_telemetry.py` (`_emit_ask_telemetry`), and `services/ask_telemetry.py::emit_ask_telemetry` signature — reuse it, do not fork it.

**Step 1: Write the failing test**

Model this on `test_ask_telemetry_emit.py`. The exact fixture setup (workspace tmp dir, monkeypatching `TelemetrySink`/env) must match the existing pattern in that file — read it first and copy its fixtures rather than reinventing them.

```python
"""Tests for governance.ask.phase child event emission and trace linkage."""
from __future__ import annotations

# NOTE: adapt imports/fixtures to match test_ask_telemetry_emit.py's existing
# pattern (workspace_root tmp path, monkeypatched TelemetrySink capturing
# emitted events into a list). Do not reinvent fixtures already defined there;
# import/share them if pytest fixtures are already suitable, otherwise mirror
# the pattern exactly.


def test_phase_events_share_parent_trace_id(ask_pipeline_env, captured_events):
    # ask_pipeline_env / captured_events are illustrative fixture names —
    # replace with whatever test_ask_telemetry_emit.py actually uses.
    run_ask_pipeline(query="hello")  # replace with actual entrypoint used in existing tests

    parent = next(e for e in captured_events if e.event == "governance.ask")
    phases = [e for e in captured_events if e.event == "governance.ask.phase"]

    assert len(phases) > 0
    for phase in phases:
        assert phase.trace_id == parent.trace_id
        assert phase.parent_event_id == parent.span_id
        assert phase.span_id != parent.span_id


def test_phase_events_have_required_detail_fields(ask_pipeline_env, captured_events):
    run_ask_pipeline(query="hello")
    phases = [e for e in captured_events if e.event == "governance.ask.phase"]

    for phase in phases:
        assert "phase_id" in phase.details
        assert "latency_domain" in phase.details
        assert "measurement_quality" in phase.details
        assert "observed_by" in phase.details


def test_parent_governance_ask_still_emits_current_payload(ask_pipeline_env, captured_events):
    # Regression: parent event fields unaffected by phase instrumentation.
    run_ask_pipeline(query="hello")
    parent = next(e for e in captured_events if e.event == "governance.ask")
    assert parent.duration_ms is not None
    assert parent.trace_id
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py -v`
Expected: FAIL (no phase events emitted yet, `phases` list empty → `assert len(phases) > 0` fails)

**Step 3: Write minimal implementation**

3a. In `_pipeline_session.py`, thread a `PhaseTimer` through `_AskSessionContext` (add `phase_timer: PhaseTimer = field(default_factory=PhaseTimer)` to the dataclass) and wrap the existing sequential steps in `_start_ask_session` with `timer.phase(...)` blocks matching the design's minimum taxonomy:

```python
from sdd_cli.commands._ask_backend._phase_timer import PhaseTimer

def _start_ask_session(query: str) -> _AskSessionContext:
    timer = PhaseTimer()
    start_mono = time.monotonic()
    trace_id = str(uuid.uuid4())

    with timer.phase("ask.budget.guard", latency_domain="governance"):
        _guard_budget_breach()

    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        workspace_root = _backend._resolve_workspace_root()

    with timer.phase("ask.organize.intake", latency_domain="local_cli"):
        _run_organize_intake(workspace_root, query)

    with timer.phase("ask.handshake.guard", latency_domain="governance"):
        _guard_handshake(workspace_root)

    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        state = _backend._get_profile_state()

    _emit_state_warnings(state)

    return _AskSessionContext(
        # ... existing fields ...
        trace_id=trace_id,
        start_mono=start_mono,
        phase_timer=timer,
    )
```

(Exact phase placement must match what each helper actually does — re-read the current body of `_start_ask_session` line-by-line before editing; do not guess field/parameter names, copy them from the real function signature.)

3b. In `_pipeline_runtime.py::_sync_ask_runtime`, after the parent event is emitted (line 82 area) and its `span_id` is known, emit one child event per `PhaseRecord`:

```python
parent_event = _backend._emit_ask_telemetry("governance.ask", ...)  # capture return value — check emit_ask_telemetry returns the RuntimeEvent; if it doesn't today, that's a small additive change to services/ask_telemetry.py (return the constructed event instead of None)

for record in session.phase_timer.records():
    _backend._emit_ask_telemetry(
        "governance.ask.phase",
        command="ask",
        workspace_root=...,
        trace_id=session.trace_id,
        # ... required positional/keyword args matching emit_ask_telemetry's signature ...
        duration_ms=record.duration_ms,
        start_ts=record.start_ts,
        end_ts=record.end_ts,
        path_id=path_id,
        extra_details={
            "phase_id": record.phase_id,
            "latency_domain": record.latency_domain,
            "measurement_quality": record.measurement_quality,
            "observed_by": record.observed_by,
            "failed": record.failed,
        },
    )
    # set parent_event_id on the child — check whether emit_ask_telemetry
    # accepts parent_event_id as a kwarg already; if not, add it as a new
    # optional kwarg defaulting to "" (backwards compatible).
```

3c. `services/ask_telemetry.py::emit_ask_telemetry` needs two additive, backwards-compatible changes:
   - Accept an optional `parent_event_id: str = ""` kwarg, pass through to `RuntimeEvent(...)`.
   - Return the constructed `RuntimeEvent` (currently likely returns `None` implicitly — check the actual current return statement before assuming) so the caller can read `.span_id` for linking children to the parent.

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py -v`
Expected: PASS (3 tests)

Then run the full existing ask telemetry suite to confirm zero regressions:

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_telemetry_*.py -v`
Expected: all PASS (this is the critical regression gate — parent `governance.ask` payload must be byte-for-byte compatible with before)

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_pipeline_runtime.py packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_pipeline_session.py packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_telemetry.py packages/interfaces/sdd_cli/src/sdd_cli/services/ask_telemetry.py packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py
git commit -m "feat(ask): emit governance.ask.phase child events with trace linkage"
```

---

### Task 4: `ask.external.llm_exchange` — only when observable

**Files:**
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_pipeline_runtime.py` (or wherever adapter-supplied timing, if any, is currently surfaced — search for existing adapter/IDE timing fields before assuming none exist)
- Test: `packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py` (extend)

**Step 1: Write the failing test**

```python
def test_llm_exchange_phase_absent_when_not_observable(ask_pipeline_env, captured_events):
    run_ask_pipeline(query="hello")  # no adapter timing supplied in this env
    phases = [e for e in captured_events if e.event == "governance.ask.phase"]
    llm_phases = [p for p in phases if p.details.get("phase_id") == "ask.external.llm_exchange"]
    assert llm_phases == []


def test_llm_exchange_phase_present_when_adapter_reports_timing(ask_pipeline_env, captured_events, monkeypatch):
    # Simulate adapter-supplied timing via whatever mechanism the codebase
    # actually uses to receive adapter/IDE timing (check for an env var or
    # input field first — do not invent a new one if one already exists).
    monkeypatch.setenv("SDD_ADAPTER_LLM_EXCHANGE_MS", "42")
    run_ask_pipeline(query="hello")
    phases = [e for e in captured_events if e.event == "governance.ask.phase"]
    llm_phase = next(p for p in phases if p.details.get("phase_id") == "ask.external.llm_exchange")
    assert llm_phase.duration_ms == 42
    assert llm_phase.details["measurement_quality"] == "adapter_reported"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py -v -k llm_exchange`
Expected: FAIL (phase not implemented yet)

**Step 3: Write minimal implementation**

Before writing this, grep the codebase for any existing adapter-timing input (`SDD_ADAPTER`, `llm_exchange`, `external_latency`, IDE-supplied timing fields in `_AskInputs`). If nothing exists, introduce a single new optional env var (e.g. `SDD_ADAPTER_LLM_EXCHANGE_MS`) as the minimal viable "adapter-reported" channel, matching the proposal's requirement that this phase must be `not_observed`/absent rather than inferred as zero:

```python
def _maybe_llm_exchange_phase(timer: PhaseTimer) -> None:
    raw = os.environ.get("SDD_ADAPTER_LLM_EXCHANGE_MS", "").strip()
    if not raw:
        return
    try:
        duration_ms = int(raw)
    except ValueError:
        return
    # Record directly as a PhaseRecord since this isn't locally measured —
    # PhaseTimer.phase() context manager assumes local measurement; add a
    # PhaseTimer.record_external(...) method for adapter-reported phases:
    timer.record_external(
        "ask.external.llm_exchange",
        latency_domain="external_llm",
        duration_ms=duration_ms,
        measurement_quality="adapter_reported",
        observed_by="adapter",
    )
```

Add `PhaseTimer.record_external(...)` to `_phase_timer.py` (Task 1's file) — a non-context-manager append matching `PhaseRecord`'s shape, with `start_ts`/`end_ts` computed as `now - duration_ms` / `now` for consistency.

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py -v -k llm_exchange`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/_ask_backend/_pipeline_runtime.py packages/interfaces/sdd_cli/commands/_ask_backend/_phase_timer.py packages/interfaces/sdd_cli/tests/test_ask_telemetry_phase_events.py
git commit -m "feat(ask): surface ask.external.llm_exchange only when adapter-reported"
```

---

### Task 5: `--full` timing breakdown in JSON and text output

**Files:**
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/services/ask_response.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/services/ask_response_json.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/services/ask_payload.py` (if `build_ask_json_data` needs a new `timing` field)
- Test: `packages/interfaces/sdd_cli/tests/test_ask_response_timing.py`

**Step 1: Write the failing test**

```python
"""Tests for --full timing breakdown in sdd ask output."""


def test_json_full_mode_includes_timing_block(...):
    # Build inputs with full=True and a PhaseTimer with 2 recorded phases,
    # call emit_ask_json_response, assert result JSON has:
    #   data["timing"]["total_ms"], data["timing"]["phase_total_ms"],
    #   data["timing"]["unattributed_ms"], data["timing"]["phases"] (list of
    #   {phase_id, duration_ms, latency_domain, measurement_quality})
    ...


def test_json_normal_mode_omits_timing_block(...):
    # full=False → data does not contain "timing" key at all
    ...


def test_text_full_mode_prints_timing_block(capsys, ...):
    # full=True → stdout contains "timing:" and at least one "phase_id=Nms" line
    ...


def test_text_normal_mode_omits_timing_block(capsys, ...):
    # full=False → stdout does not contain "timing:"
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_response_timing.py -v`
Expected: FAIL (`timing` key/text block doesn't exist)

**Step 3: Write minimal implementation**

In `ask_response_json.py`, alongside the existing `steps=[...] if inputs.full else None` gate (lines ~123-138), add:

```python
timing = None
if inputs.full and session.phase_timer.records():
    records = session.phase_timer.records()
    phase_total_ms = session.phase_timer.phase_total_ms()
    timing = {
        "total_ms": duration_ms,
        "phase_total_ms": phase_total_ms,
        "unattributed_ms": session.phase_timer.unattributed_ms(session_duration_ms=duration_ms),
        "phases": [
            {
                "phase_id": r.phase_id,
                "duration_ms": r.duration_ms,
                "latency_domain": r.latency_domain,
                "measurement_quality": r.measurement_quality,
            }
            for r in records
        ],
    }
```
and thread `timing` into `build_ask_json_data(...)`'s existing `extra={...}` dict (matching how `log_format` is already conditionally added) or as a new top-level parameter — check `build_ask_json_data`'s actual signature first and follow its existing convention rather than inventing a new one.

In `ask_response.py`, add a compact text block gated the same way, matching the design doc's example format:

```python
if inputs.full and phase_timer.records():
    typer.echo("timing:")
    typer.echo(
        f"  total_ms={duration_ms} phase_total_ms={phase_timer.phase_total_ms()} "
        f"unattributed_ms={phase_timer.unattributed_ms(session_duration_ms=duration_ms)}"
    )
    for r in phase_timer.records():
        typer.echo(f"  {r.phase_id}={r.duration_ms}ms {r.latency_domain} {r.measurement_quality}")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_response_timing.py -v`
Expected: PASS (4 tests)

Also run full ask response test suites to confirm normal-mode output byte-compatibility:

Run: `uv run pytest packages/interfaces/sdd_cli/tests -k "ask_response" -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/services/ask_response.py packages/interfaces/sdd_cli/src/sdd_cli/services/ask_response_json.py packages/interfaces/sdd_cli/src/sdd_cli/services/ask_payload.py packages/interfaces/sdd_cli/tests/test_ask_response_timing.py
git commit -m "feat(ask): add --full phase timing breakdown to text and JSON output"
```

---

### Task 6: `AskLatencyCollector` for phase aggregation

**Files:**
- Create: `packages/core/sdd_runtime/src/sdd_runtime/metrics/_ask_latency_collector.py`
- Modify: `packages/core/sdd_runtime/src/sdd_runtime/metrics/__init__.py` (export the new collector)
- Test: `packages/core/sdd_runtime/tests/test_ask_latency_collector.py`

**Read first:** `packages/core/sdd_runtime/src/sdd_runtime/metrics/_collector.py` (full file) and `_economy_snapshot.py` — copy the constructor/`ingest`/`from_reader`/`snapshot`/`reset` pattern exactly, do not deviate in shape.

**Step 1: Write the failing test**

```python
"""Tests for AskLatencyCollector — governance.ask.phase aggregation."""
from sdd_runtime.metrics._ask_latency_collector import AskLatencyCollector


def _phase_event(phase_id, latency_domain, duration_ms, path_id="PATH_A"):
    return {
        "event": "governance.ask.phase",
        "duration_ms": duration_ms,
        "path_id": path_id,
        "details": {"phase_id": phase_id, "latency_domain": latency_domain},
    }


def test_ingest_ignores_non_phase_events():
    collector = AskLatencyCollector()
    collector.ingest({"event": "governance.ask", "duration_ms": 100})
    snapshot = collector.snapshot()
    assert snapshot.groups == {}


def test_ingest_aggregates_by_phase_id():
    collector = AskLatencyCollector()
    collector.ingest(_phase_event("ask.governance.snapshot", "governance", 50))
    collector.ingest(_phase_event("ask.governance.snapshot", "governance", 70))
    snapshot = collector.snapshot()
    group = snapshot.groups[("ask.governance.snapshot", "governance", "PATH_A")]
    assert group.count == 2
    assert group.min_ms == 50
    assert group.max_ms == 70
    assert group.avg_ms == 60


def test_percentiles_p50_p95():
    collector = AskLatencyCollector()
    for ms in [10, 20, 30, 40, 100]:
        collector.ingest(_phase_event("ask.response.render", "rendering", ms))
    group = collector.snapshot().groups[("ask.response.render", "rendering", "PATH_A")]
    assert group.p50_ms in (30, 20, 40)  # exact value depends on percentile method chosen; document the method
    assert group.p95_ms >= group.p50_ms


def test_from_reader_replays_events(tmp_path):
    from sdd_runtime.telemetry import TelemetryReader  # confirm actual import path before writing

    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"event": "governance.ask.phase", "duration_ms": 15, "path_id": "PATH_B", '
        '"details": {"phase_id": "ask.workspace.resolve", "latency_domain": "local_fs"}}\n'
    )
    reader = TelemetryReader(events_path)  # confirm actual constructor signature first
    collector = AskLatencyCollector.from_reader(reader)
    snapshot = collector.snapshot()
    assert snapshot.groups[("ask.workspace.resolve", "local_fs", "PATH_B")].count == 1


def test_reset_clears_state():
    collector = AskLatencyCollector()
    collector.ingest(_phase_event("ask.cli.entry", "local_cli", 5))
    collector.reset()
    assert collector.snapshot().groups == {}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/sdd_runtime/tests/test_ask_latency_collector.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Ask phase-latency collector — aggregates governance.ask.phase events.

Kept separate from TokenEconomyCollector per the trace-route design's
"Recommended Ownership" decision: governance latency and token/budget/retry
economy are distinct metric domains.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LatencyGroup:
    count: int
    min_ms: int
    max_ms: int
    avg_ms: float
    p50_ms: int
    p95_ms: int


@dataclass(frozen=True)
class AskLatencySnapshot:
    groups: dict[tuple[str, str, str], LatencyGroup] = field(default_factory=dict)


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (pct / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    lower = sorted_values[f] * (c - k)
    upper = sorted_values[c] * (k - f)
    return round(lower + upper)


class AskLatencyCollector:
    """Aggregates `governance.ask.phase` events by (phase_id, latency_domain, path_id)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._durations: dict[tuple[str, str, str], list[int]] = {}

    def ingest(self, event: Any) -> None:
        event_dict = event if isinstance(event, dict) else event.to_dict()
        if event_dict.get("event") != "governance.ask.phase":
            return
        details = event_dict.get("details") or {}
        phase_id = details.get("phase_id", "unknown")
        latency_domain = details.get("latency_domain", "unknown")
        path_id = event_dict.get("path_id") or "unknown"
        duration_ms = event_dict.get("duration_ms")
        if duration_ms is None:
            return
        key = (phase_id, latency_domain, path_id)
        with self._lock:
            self._durations.setdefault(key, []).append(int(duration_ms))

    @classmethod
    def from_reader(cls, reader: Any) -> "AskLatencyCollector":
        collector = cls()
        for event in reader.list_events():
            collector.ingest(event)
        return collector

    def snapshot(self) -> AskLatencySnapshot:
        with self._lock:
            groups: dict[tuple[str, str, str], LatencyGroup] = {}
            for key, values in self._durations.items():
                sorted_values = sorted(values)
                groups[key] = LatencyGroup(
                    count=len(sorted_values),
                    min_ms=sorted_values[0],
                    max_ms=sorted_values[-1],
                    avg_ms=sum(sorted_values) / len(sorted_values),
                    p50_ms=_percentile(sorted_values, 50),
                    p95_ms=_percentile(sorted_values, 95),
                )
            return AskLatencySnapshot(groups=groups)

    def reset(self) -> None:
        with self._lock:
            self._durations.clear()
```

Confirm the actual `TelemetryReader` import path and `list_events()` method name before finalizing `from_reader` — check `sdd_runtime/metrics/_collector.py`'s own `from_reader` for the exact import.

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/sdd_runtime/tests/test_ask_latency_collector.py -v`
Expected: PASS (5 tests) — adjust the `p50_ms` assertion in the test once you've picked/confirmed the percentile method (linear interpolation, as coded above).

**Step 5: Commit**

```bash
git add packages/core/sdd_runtime/src/sdd_runtime/metrics/_ask_latency_collector.py packages/core/sdd_runtime/src/sdd_runtime/metrics/__init__.py packages/core/sdd_runtime/tests/test_ask_latency_collector.py
git commit -m "feat(metrics): add AskLatencyCollector for governance.ask.phase aggregation"
```

---

### Task 7: `sdd telemetry summary` command

**Files:**
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/telemetry.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/_telemetry_command_support.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/services/telemetry_handler.py` (extend `filter_events` with `phase_id`/`latency_domain`/`path_id` predicates, additive kwargs with defaults)
- Test: `packages/interfaces/sdd_cli/tests/test_telemetry_summary_command.py`

**Read first:** `commands/telemetry.py`'s `query` subcommand implementation end-to-end (path resolution, filter application, output envelope) — the `summary` subcommand should reuse the same path-resolution and JSON-envelope helpers (`build_ok_result`/`build_error_result`), not duplicate them.

**Step 1: Write the failing test**

```python
"""Tests for `sdd telemetry summary` — phase latency aggregation."""
import json


def test_summary_aggregates_phase_events(tmp_path, cli_runner):
    events_path = tmp_path / "compliance-events.jsonl"
    events_path.write_text(
        "\n".join(
            [
                json.dumps({"event": "governance.ask.phase", "duration_ms": 10, "path_id": "PATH_A",
                            "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"}}),
                json.dumps({"event": "governance.ask.phase", "duration_ms": 20, "path_id": "PATH_A",
                            "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"}}),
                json.dumps({"event": "governance.ask", "duration_ms": 999}),  # must be excluded
            ]
        )
    )
    result = cli_runner.invoke(app, ["telemetry", "summary", "--events-path", str(events_path), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    groups = payload["data"]["groups"]
    assert len(groups) == 1
    assert groups[0]["phase_id"] == "ask.cli.entry"
    assert groups[0]["count"] == 2


def test_summary_filters_by_path_id(tmp_path, cli_runner):
    # two path_ids present, --path-id PATH_B should only aggregate PATH_B rows
    ...


def test_summary_empty_file_returns_empty_groups(tmp_path, cli_runner):
    ...
```

(Match `cli_runner`/`app` fixture names to whatever `test_telemetry_dump_query_command.py` already uses — copy its fixture setup exactly.)

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_telemetry_summary_command.py -v`
Expected: FAIL — no `summary` subcommand

**Step 3: Write minimal implementation**

Add a `summary` subcommand to `commands/telemetry.py` following the exact structure of `query` (same options for `--events-path`/path resolution, `--json`/`--format`, plus new `--phase-id`, `--latency-domain`, `--path-id` filters), delegating aggregation to `AskLatencyCollector` from Task 6:

```python
@app.command("summary")
def summary_cmd(
    phase_id: str | None = typer.Option(None, "--phase-id"),
    latency_domain: str | None = typer.Option(None, "--latency-domain"),
    path_id: str | None = typer.Option(None, "--path-id"),
    events_path: Path | None = typer.Option(None, "--events-path"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    from sdd_cli.commands._telemetry_command_support import emit_summary
    emit_summary(
        phase_id=phase_id,
        latency_domain=latency_domain,
        path_id=path_id,
        events_path=events_path,
        json_output=json_output,
    )
```

In `_telemetry_command_support.py`, add `emit_summary(...)`: resolve events path the same way `emit_query` does, read events via `_read_events`, filter to `event == "governance.ask.phase"` plus any `phase_id`/`latency_domain`/`path_id` filters, feed into a fresh `AskLatencyCollector`, call `.snapshot()`, render as JSON envelope (`build_ok_result`) or text table matching the existing `status`/`query` text rendering conventions.

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_telemetry_summary_command.py -v`
Expected: PASS (3 tests)

Run the broader telemetry command suite for regressions:

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_telemetry_*.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/telemetry.py packages/interfaces/sdd_cli/src/sdd_cli/commands/_telemetry_command_support.py packages/interfaces/sdd_cli/src/sdd_cli/services/telemetry_handler.py packages/interfaces/sdd_cli/tests/test_telemetry_summary_command.py
git commit -m "feat(telemetry): add sdd telemetry summary for phase latency aggregation"
```

---

### Task 8: Warn on `SDD_COMPLIANCE_EVENTS_PATH` / `SDD_TELEMETRY_PATH` divergence (SQ-002)

**Files:**
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/commands/telemetry.py` (`_default_events_path()`)
- Test: `packages/interfaces/sdd_cli/tests/test_telemetry_path_divergence_warning.py`

**Step 1: Write the failing test**

```python
def test_warns_when_paths_diverge(monkeypatch, capsys, cli_runner):
    monkeypatch.setenv("SDD_COMPLIANCE_EVENTS_PATH", "/tmp/a.jsonl")
    monkeypatch.setenv("SDD_TELEMETRY_PATH", "/tmp/b.jsonl")
    cli_runner.invoke(app, ["telemetry", "status"])
    captured = capsys.readouterr()
    assert "SDD_COMPLIANCE_EVENTS_PATH" in captured.err
    assert "SDD_TELEMETRY_PATH" in captured.err


def test_no_warning_when_paths_match(monkeypatch, capsys, cli_runner):
    monkeypatch.setenv("SDD_COMPLIANCE_EVENTS_PATH", "/tmp/same.jsonl")
    monkeypatch.setenv("SDD_TELEMETRY_PATH", "/tmp/same.jsonl")
    cli_runner.invoke(app, ["telemetry", "status"])
    captured = capsys.readouterr()
    assert "diverge" not in captured.err.lower()


def test_no_warning_when_only_one_set(monkeypatch, capsys, cli_runner):
    monkeypatch.delenv("SDD_COMPLIANCE_EVENTS_PATH", raising=False)
    monkeypatch.setenv("SDD_TELEMETRY_PATH", "/tmp/b.jsonl")
    cli_runner.invoke(app, ["telemetry", "status"])
    captured = capsys.readouterr()
    assert "diverge" not in captured.err.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_telemetry_path_divergence_warning.py -v`
Expected: FAIL — no warning emitted today

**Step 3: Write minimal implementation**

In `commands/telemetry.py`, add a check called once at the top of each subcommand (or via a shared typer callback) that compares both env vars when both are set and non-empty, and if they resolve to different absolute paths, emit a `typer.echo(..., err=True)` warning — must not raise/exit, this is soft-warning only per the design's "Error Handling" section (no new hard failures).

```python
def _warn_if_telemetry_paths_diverge() -> None:
    compliance_path = os.environ.get("SDD_COMPLIANCE_EVENTS_PATH", "").strip()
    telemetry_path = os.environ.get("SDD_TELEMETRY_PATH", "").strip()
    if not compliance_path or not telemetry_path:
        return
    if Path(compliance_path).resolve() != Path(telemetry_path).resolve():
        typer.echo(
            f"WARN: SDD_COMPLIANCE_EVENTS_PATH ({compliance_path}) and "
            f"SDD_TELEMETRY_PATH ({telemetry_path}) point to different files; "
            "sdd ask and sdd telemetry may read/write different event logs.",
            err=True,
        )
```

Call this at the start of each subcommand implementation (or wherever the existing per-command setup already runs, e.g. right after path resolution in `status`/`query`/`summary`).

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_telemetry_path_divergence_warning.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/telemetry.py packages/interfaces/sdd_cli/tests/test_telemetry_path_divergence_warning.py
git commit -m "feat(telemetry): warn when compliance-events path env vars diverge"
```

---

### Task 9: Regression tests for `intake_index_mode: none`

**Files:**
- Test: `packages/interfaces/sdd_cli/tests/test_ask_intake_index_mode_none_regression.py`

**Step 1: Write the failing test (should already pass — this is a lock-in regression test, not new behavior)**

```python
"""Lock-in regression tests: intake_index_mode: none semantics must not change
while adding phase-level trace-route instrumentation (design doc SQ-001)."""


def test_light_input_with_execution_gate_allowed_is_not_blocked(...):
    # Construct/execute an ask invocation matching the light_input path
    # (find the existing fixture/helper used for this in
    # test_ask_telemetry_path_id.py's PATH_A tests) and assert
    # execution_gate == "allowed" and intake_index_mode == "none" together
    # do not raise/exit non-zero.
    ...


def test_non_light_input_missing_organize_index_remains_blocked(...):
    # Construct a non-light-input scenario without organize/indexing and
    # assert it is still blocked exactly as before (find the existing
    # blocking behavior/exit-code assertion pattern in the budget/handshake
    # guard tests and mirror it).
    ...
```

**Step 2: Run test to verify it currently passes (this locks in existing behavior)**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/test_ask_intake_index_mode_none_regression.py -v`
Expected: PASS immediately — if it fails, **stop** (this is the `scope_drift`/`ambiguity` stop condition from tasks.md; instrumentation must not have changed this behavior across Tasks 1-8. Bisect which prior task introduced the regression before continuing).

**Step 3–4: N/A** (no new implementation — this task is pure regression locking)

**Step 5: Commit**

```bash
git add packages/interfaces/sdd_cli/tests/test_ask_intake_index_mode_none_regression.py
git commit -m "test(ask): lock in intake_index_mode:none semantics across trace-route instrumentation"
```

---

### Task 10: Document token source semantics

**Files:**
- Modify: `docs/` — find the existing doc describing `token_source`/telemetry fields (search `grep -rl "token_source" docs/`) and extend it; if none exists, create `docs/guides/ask-telemetry-token-source.md`.

**Step 1: Locate existing docs**

Run: `grep -rl "token_source" docs/ .sdd/source 2>/dev/null`

**Step 2: Write/extend documentation**

Add a short section (no more than ~30 lines) clarifying:
- `token_source` values: `env` (from `SDD_ASK_TOKENS_IN`/`OUT` env vars, i.e. CLI/environment-provided), `estimated` (local heuristic estimate).
- There is currently no `actual`/API-metered token source wired into `sdd ask` telemetry — do not claim one exists.
- Token count source alone must not be read as evidence of LLM latency; see `ask.external.llm_exchange`'s `measurement_quality` field for that.

**Step 3: Commit**

```bash
git add docs/<the file you edited or created>
git commit -m "docs(ask): clarify token_source semantics vs LLM latency evidence"
```

---

## Final Verification (run after Task 10)

Run the complete affected test surface plus the golden/lint gates this repo enforces before considering the feature done:

```bash
uv run pytest packages/interfaces/sdd_cli/tests -k "ask or telemetry" -q
uv run pytest packages/core/sdd_runtime/tests -k "telemetry or metrics" -q
uv run bandit -q -r packages/interfaces/sdd_cli/src packages/core/sdd_runtime/src
```

Confirm against `tasks.md`'s **Acceptance Checks**:
- [ ] `sdd ask` emits parent `governance.ask` as before (byte-identical payload shape).
- [ ] Phase-level `governance.ask.phase` events are emitted under the same trace.
- [ ] Operators can identify dominant local phase for a slow `sdd ask` (via `--full` or `sdd telemetry summary`).
- [ ] External LLM latency is only reported when directly measured or adapter-reported.
- [ ] `sdd telemetry summary` can aggregate ask latency by phase and path.
- [ ] Existing ask behavior and policy semantics are unchanged (Task 9 regression suite green).
