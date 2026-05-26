# SDD Harness — Examples

Runnable demos showing SDD drift prevention with popular agentic frameworks.

Each demo uses real framework code with optional dependencies. They are not part of the CI test suite — run them locally after installing the relevant extras.

---

## LangGraph — Tool Guardrail

**What it shows:** An agent declares a tool (`send_email`) that is not authorized in the active SDD mandate. The SDD runtime API blocks execution before the graph runs, printing the mandate violation.

**Prerequisites:**

```bash
# From the repo root
uv run --extra examples-langgraph python examples/langgraph/demo_tool_guardrail.py
```

Expected output: `BLOCKED` with the violated mandate reference.

---

## CrewAI — Spec Drift Detection

**What it shows:** A CrewAI crew is initialized, then the governance fingerprint is tampered (simulating artifact drift). SDD `governance validate` detects the mismatch before the crew runs and prints the diff.

**Prerequisites:**

```bash
# From the repo root
uv run --extra examples-crewai python examples/crewai/demo_spec_drift.py
```

Expected output: `DRIFT_DETECTED` with expected vs found fingerprint diff.

---

## Notes

- Both demos exit with code `0` — the block/detection is the expected, correct behavior.
- Demos read from `.sdd/` in the repo root. Run them from the repo root directory.
- Optional extras are defined in `pyproject.toml` under `[project.optional-dependencies]`.
