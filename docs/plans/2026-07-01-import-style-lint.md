# Import Style Lint Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a lint-time architecture guardrail that rejects files importing the same module with both `import module` and `from module import name`.

**Architecture:** Implement a standalone AST validator under `tools/architecture/` and register it in the existing `make lint` architecture step list. Keep parsing logic independent from Ruff so the rule remains explicit and testable.

**Tech Stack:** Python `ast`, existing `tools/maintenance/lint_all.py`, pytest architecture tests.

---

### Task 1: Add Failing Tests

**Files:**
- Create: `tests/unit/architecture/test_validate_import_style.py`

**Steps:**
1. Load `tools/architecture/validate_import_style.py` with `importlib`.
2. Create a temporary repo with `pyproject.toml`, `packages/`, `tools/`, and `tests/`.
3. Assert no violation for a file that imports a module using one style.
4. Assert a violation for a file that uses both `import sdd_core.foo` and `from sdd_core.foo import Bar`.
5. Assert relative imports under `packages/*/src` are resolved before comparison.

### Task 2: Implement Validator

**Files:**
- Create: `tools/architecture/validate_import_style.py`

**Steps:**
1. Detect repo root from `pyproject.toml`.
2. Collect Python files under `packages/`, `tools/`, and `tests/`, excluding generated/build/cache directories.
3. Parse each file with `ast`.
4. For each file, collect modules imported by `ast.Import` and `ast.ImportFrom`.
5. Resolve relative `ImportFrom` modules when the current module name can be derived from `packages/*/src`.
6. Return violations when the same module appears in both collections.
7. Print deterministic CLI output and return non-zero on violations or parse errors.

### Task 3: Wire Into Lint

**Files:**
- Modify: `tools/maintenance/lint_all.py`

**Steps:**
1. Add `tools/architecture/validate_import_style.py` to `_run_arch_steps()`.
2. Keep it before cycle validation so style issues surface before graph-level checks.

### Task 4: Verify

**Commands:**
- `uv run python -m pytest -q tests/unit/architecture/test_validate_import_style.py`
- `uv run python tools/architecture/validate_import_style.py`
- `uv run python tools/maintenance/lint_all.py --check-only`

**Expected:** New unit tests pass, the validator reports either zero violations or actionable existing violations, and lint reaches the normal quality gates.
