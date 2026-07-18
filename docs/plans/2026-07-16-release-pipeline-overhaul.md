# Release Pipeline Overhaul Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Fix the `ModuleNotFoundError` breaking every release build, eliminate the
duplicated/fragile workflow logic that let the bug hide in two places, make the
release dry-run a mandatory gate before tagging, unify the workspace on a single
dynamic (Git-tag-derived) versioning strategy, and stop `container-release.yml`
from being able to publish an image for a release that never succeeded.

**Architecture:** Five independent-but-sequenced fixes, applied in the order the
design doc lays out (each is self-contained enough to ship and verify on its own,
but later parts assume earlier parts landed): (A) fix the script-vs-module import
bug and add a regression test for the whole class of bug, (B) extract the
duplicated build steps from `release.yml`/`release-dry-run.yml` into one reusable
workflow, (C) make the dry-run run automatically on every push to `main`, (D)
migrate all 7 remaining workspace packages from static `setuptools` versioning to
`hatch-vcs` dynamic versioning (matching `sdd_cli`), (E) add a cross-workflow
success gate to `container-release.yml`.

**Tech Stack:** Python 3.10, GitHub Actions (reusable `workflow_call`), hatchling,
hatch-vcs, uv workspaces, pytest, PyYAML (for workflow-policy tests).

**Design doc:** `.analysis/pending/2026-07-16-release-pipeline-overhaul-design.md`
(read this first — it has the full rationale and empirical evidence behind every
decision below).

---

## Part A — Fix the import bug (Causa Raiz #1)

This part alone unblocks publishing. It should be committed and verified before
moving to Part B.

### Task A1: Write a failing test that pins the correct invocation mode

**Files:**
- Test: `tests/unit/ci/test_release_workflow_policy.py`

**Step 1: Read the existing test file in full**

Already done during design — the file lives at
`tests/unit/ci/test_release_workflow_policy.py` and has a `_load_workflow(path)`
helper (parses YAML with a patched bool constructor) and a
`_step_run_block(steps, name)` helper (takes a job's `steps` list and a step
`name`, returns its `run:` string). Reuse both.

**Step 2: Add the failing test**

Add this test to the end of the file:

```python
def test_release_workflows_invoke_tools_release_scripts_as_modules() -> None:
    """tools/release/*.py scripts do package-relative imports (e.g.
    stage_packaged_compiler_assets.py imports validate_release_assets). Invoking
    them as bare scripts (`python path/to/script.py`) puts the script's own
    directory on sys.path instead of the repo root, so the import fails with
    ModuleNotFoundError. They must be invoked as modules (`python -m
    tools.release.<name>`), which puts the repo root (cwd) on sys.path."""
    for path, job_name in (
        (RELEASE_WORKFLOW, "build"),
        (RELEASE_DRY_RUN_WORKFLOW, "dry-run"),
    ):
        workflow = _load_workflow(path)
        steps = "\n".join(
            step.get("run", "") for step in _jobs(workflow)[job_name]["steps"]
        )
        assert "python tools/release/stage_packaged_compiler_assets.py" not in steps
        assert "python -m tools.release.stage_packaged_compiler_assets" in steps
```

**Step 3: Run it to verify it fails**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -k invoke_tools_release_scripts_as_modules -v`
Expected: FAIL — both workflows currently use
`python tools/release/stage_packaged_compiler_assets.py dist`.

**Step 4: Commit the failing test**

```bash
git add tests/unit/ci/test_release_workflow_policy.py
git commit -m "test: pin -m invocation contract for tools/release scripts (red)"
```

### Task A2: Create `tools/release/__init__.py` and fix `release.yml`

**Files:**
- Create: `tools/release/__init__.py`
- Modify: `.github/workflows/release.yml:98,157,210,419`

**Step 1: Create the package init file**

```bash
touch /home/sergio/dev/sdd-harness/tools/release/__init__.py
```

(Empty file, mirroring the existing empty `tools/__init__.py`.)

**Step 2: Fix the 4 invocation sites in `release.yml`**

Line 98 — inside the "Verify version matches tag" step:
```diff
-          PKG_VERSION=$(uv run python tools/release/resolve_vcs_version.py)
+          PKG_VERSION=$(uv run python -m tools.release.resolve_vcs_version)
```

Line 157 — "Sync sub-package versions to tag" step:
```diff
-        run: python tools/release/sync_versions.py "${{ steps.version.outputs.tag }}"
+        run: python -m tools.release.sync_versions "${{ steps.version.outputs.tag }}"
```

Line 210 — "Stage packaged compiler assets for sdd-core wheel" step:
```diff
-        run: python tools/release/stage_packaged_compiler_assets.py dist
+        run: python -m tools.release.stage_packaged_compiler_assets dist
```

Line 419 — "Verify release assets are staged" step (note: `python3`, not `python`):
```diff
-        run: python3 tools/release/validate_release_assets.py dist
+        run: python3 -m tools.release.validate_release_assets dist
```

**Step 3: Run the Task A1 test to verify the `release.yml` half passes**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -k invoke_tools_release_scripts_as_modules -v`
Expected: still FAIL (the assertion loop also checks `release-dry-run.yml`,
fixed in Task A3) — but confirm no new error, just the same assertion failing
now only on the dry-run half. If your test runner supports it, temporarily
comment out the `RELEASE_DRY_RUN_WORKFLOW` tuple entry to confirm the
`release.yml` half alone is green, then restore it.

**Step 4: Commit**

```bash
git add tools/release/__init__.py .github/workflows/release.yml
git commit -m "fix: invoke tools/release scripts as modules in release.yml"
```

### Task A3: Fix `release-dry-run.yml`

**Files:**
- Modify: `.github/workflows/release-dry-run.yml:122,151`

**Step 1: Fix the 2 invocation sites**

Line 122 — "Sync sub-package versions (dry run)" step:
```diff
-        run: python tools/release/sync_versions.py "$TAG"
+        run: python -m tools.release.sync_versions "$TAG"
```

Line 151 — "Stage packaged compiler assets for sdd-core wheel (dry run)" step:
```diff
-        run: python tools/release/stage_packaged_compiler_assets.py dist
+        run: python -m tools.release.stage_packaged_compiler_assets dist
```

**Step 2: Run the Task A1 test to verify it fully passes**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -k invoke_tools_release_scripts_as_modules -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add .github/workflows/release-dry-run.yml
git commit -m "fix: invoke tools/release scripts as modules in release-dry-run.yml"
```

### Task A4: Remove the now-unnecessary import fallback in `resolve_vcs_version.py`

**Files:**
- Modify: `tools/release/resolve_vcs_version.py:12-15`
- Modify: `tests/unit/ci/test_release_workflow_policy.py` (existing test needs a
  literal-string update, not new logic)

**Step 1: Simplify the import**

```diff
-try:
-    from tools.release import sync_versions
-except ModuleNotFoundError:  # pragma: no cover - script execution path
-    import sync_versions  # type: ignore[import-not-found,no-redef]
+from tools.release import sync_versions
```

**Step 2: Update the existing workflow-policy assertion**

`test_release_workflow_is_tag_driven_and_accepts_uppercase_v` (already in the
file, around line 44) asserts:
```python
assert "tools/release/resolve_vcs_version.py" in validate_steps
```
This string is now wrong (Task A2 changed it to
`-m tools.release.resolve_vcs_version`). Update the assertion to:
```python
assert "tools.release.resolve_vcs_version" in validate_steps
```

**Step 3: Run the full policy test file**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -v`
Expected: PASS for every test except `test_release_build_syncs_versions_from_git_tag`
and `test_release_dry_run_syncs_versions_from_git_tag`, which still assert the
literal string `"tools/release/sync_versions.py"` — fix those the same way:

```python
# test_release_build_syncs_versions_from_git_tag
assert "tools.release.sync_versions" in build_steps

# test_release_dry_run_syncs_versions_from_git_tag
assert 'tools.release.sync_versions "$TAG"' in dry_run_steps
```

**Step 4: Run the full policy test file again**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -v`
Expected: PASS (all tests).

**Step 5: Run the existing `resolve_vcs_version` unit tests, if any, plus a manual smoke check**

Run: `cd /home/sergio/dev/sdd-harness && uv run python -m tools.release.resolve_vcs_version 2>&1 | head -5`
Expected: either prints a resolved version or the "HEAD is not exactly on a
release tag" error — either way, **not** `ModuleNotFoundError`.

**Step 6: Commit**

```bash
git add tools/release/resolve_vcs_version.py tests/unit/ci/test_release_workflow_policy.py
git commit -m "refactor: drop import fallback hack now that -m invocation is standard"
```

### Task A5: Update `sync_versions.py`'s usage docstring

**Files:**
- Modify: `tools/release/sync_versions.py:8-14`

**Step 1: Update the docstring**

```diff
 Usage:
-    python tools/release/sync_versions.py <version-or-tag>
+    python -m tools.release.sync_versions <version-or-tag>

 Example:
-    python tools/release/sync_versions.py 0.2.0
-    python tools/release/sync_versions.py v0.2.0
-    python tools/release/sync_versions.py V0.2.0
+    python -m tools.release.sync_versions 0.2.0
+    python -m tools.release.sync_versions v0.2.0
+    python -m tools.release.sync_versions V0.2.0
```

Also update the runtime usage message at the bottom of the file (inside
`if __name__ == "__main__":`):
```diff
-        print("Usage: python sync_versions.py <version-or-tag>")
-        print("Example: python sync_versions.py v0.2.0")
+        print("Usage: python -m tools.release.sync_versions <version-or-tag>")
+        print("Example: python -m tools.release.sync_versions v0.2.0")
```

**Step 2: Commit**

```bash
git add tools/release/sync_versions.py
git commit -m "docs: update sync_versions.py usage strings to -m invocation"
```

### Task A6: Add the systematic regression test (SafeProcessRunner, all `tools/release/*.py` scripts)

**Files:**
- Create: `tests/unit/tools/test_release_scripts_module_invocation.py`

**Step 1: Write the test**

```python
"""Regression test for the whole class of bug fixed in Part A of the release
pipeline overhaul: any tools/release/*.py script that does a package-relative
import (e.g. `from tools.release.x import y`) must be safely invocable as a
module (`python -m tools.release.<name>`) from the repo root, because that is
how the release workflows call them. This test exercises every script in the
directory the same way CI does, using the repo's governed subprocess runner
instead of raw subprocess."""

from __future__ import annotations

import sys
from pathlib import Path

from sdd_core.utils.process import SafeProcessRunner

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_SCRIPTS_DIR = REPO_ROOT / "tools" / "release"

# Each script's minimal argv to reach the import statements without requiring
# real release state (git tags, a populated dist/, etc). We only care that the
# module resolves and starts running — not that it succeeds end-to-end.
SCRIPT_MODULES_AND_ARGS = {
    "resolve_vcs_version": [],
    "sync_versions": ["0.0.0"],
    "stage_packaged_compiler_assets": ["/nonexistent-dist-dir"],
    "validate_release_assets": ["/nonexistent-dist-dir"],
}


def test_every_release_script_is_discovered() -> None:
    """Guard against this test silently going stale if a script is added."""
    on_disk = {
        path.stem
        for path in RELEASE_SCRIPTS_DIR.glob("*.py")
        if path.stem != "__init__"
    }
    assert on_disk == set(SCRIPT_MODULES_AND_ARGS)


def test_release_scripts_run_as_modules_without_import_errors() -> None:
    runner = SafeProcessRunner()
    for module_name, args in SCRIPT_MODULES_AND_ARGS.items():
        result = runner.run(
            [sys.executable, "-m", f"tools.release.{module_name}", *args],
            cwd=REPO_ROOT,
            capture_output=True,
        )
        combined_output = f"{result.stdout}\n{result.stderr}"
        assert "ModuleNotFoundError" not in combined_output, (
            f"tools.release.{module_name} failed to import when run as a "
            f"module:\n{combined_output}"
        )
```

**Step 2: Run it to verify it passes (this is a safety-net test, not a red/green
for an existing bug — it should already be green after Tasks A2-A4)**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/tools/test_release_scripts_module_invocation.py -v`
Expected: PASS. If `test_every_release_script_is_discovered` fails, the
`SCRIPT_MODULES_AND_ARGS` dict above is out of sync with the directory — update
it to match.

**Step 3: Confirm it would have caught the original bug**

Temporarily revert Task A2's diff on `stage_packaged_compiler_assets.py`'s
import (i.e. locally re-add the missing `__init__.py` removal is not needed —
instead, temporarily rename `tools/release/__init__.py` aside and re-run):
Run: `mv tools/release/__init__.py /tmp/__init__.py.bak && uv run pytest tests/unit/tools/test_release_scripts_module_invocation.py -v; mv /tmp/__init__.py.bak tools/release/__init__.py`
This step is a manual sanity check, not a permanent change — restore the file
immediately after observing the result either way.

**Step 4: Commit**

```bash
git add tests/unit/tools/test_release_scripts_module_invocation.py
git commit -m "test: add systematic -m invocation regression test for tools/release scripts"
```

### Task A7: Full regression pass for Part A

**Step 1: Run the full unit test suite**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit -q --tb=short`
Expected: PASS, no new failures.

**Step 2: Run the local dry-run Makefile target as an extra sanity check**

Run: `cd /home/sergio/dev/sdd-harness && make release-dry-run`
Expected: PASS (this target reads version/tag state locally; unaffected by Part
A's changes, but confirms nothing else broke).

**Step 3: Report status**

Run: `git status --short && git log --oneline -8`
Confirm the 5 commits from Tasks A2-A6 are present and the tree is clean before
moving to Part B. **Stop here and check in with the user** — Part A alone is
enough to unblock a real release if they want to cut `v1.0.4` before continuing
with the larger, higher-risk Parts B-E.

---

## Part B — Unify `release.yml` and `release-dry-run.yml` (Causa Raiz #2)

### Task B1: Extract the shared build steps into a reusable workflow

**Files:**
- Create: `.github/workflows/reusable-release-build.yml`
- Reference pattern: `.github/workflows/reusable-test.yml` (read this first for
  the repo's existing `workflow_call` conventions — input/output declaration
  style, `permissions:` block placement)

**Step 1: Read the reference reusable workflow**

Run: `cat .github/workflows/reusable-test.yml | head -40` to see the
`on: workflow_call:` input declaration style used elsewhere in this repo, and
match it exactly (input names, `required`/`default`, secrets passthrough if
any).

**Step 2: Create the reusable workflow**

Move the following step blocks out of `release.yml`'s `build` job (lines
106-291) into `.github/workflows/reusable-release-build.yml`, parameterized by
a `version` and `tag` input (passed in by the caller instead of computed from
`GITHUB_REF`):

- "Set up Python", "Install build tools", "Set up Go"
- "Sync sub-package versions to tag" (uses `inputs.tag`)
- "Verify all package versions match tag" (uses `inputs.version`)
- "Cross-compile sdd-compile release binaries"
- "Stage packaged compiler assets for sdd-core wheel"
- "Build packages" (uses `inputs.version` for the `SETUPTOOLS_SCM_PRETEND_VERSION`
  env and the wheel-filename check — this env var is removed entirely once Part
  D lands; for Part B alone, keep it wired through as an input so Part B doesn't
  block on Part D)
- "Download runtime dependency wheelhouse"
- "Install packages for compile step"
- "Compile governance artifacts"

End the reusable workflow with an `actions/upload-artifact` step uploading
`dist/` under a name the caller can pick via an input (default `dist`), so both
callers can name their artifact independently (`dist` for the real release,
`release-dry-run-dist` for the dry run, matching current names).

**Step 3: Verify the reusable workflow is syntactically valid**

Run: `cd /home/sergio/dev/sdd-harness && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/reusable-release-build.yml'))"`
Expected: no exception.

**Step 4: Commit**

```bash
git add .github/workflows/reusable-release-build.yml
git commit -m "feat: extract shared release build steps into a reusable workflow"
```

### Task B2: Wire `release.yml`'s `build` job to call the reusable workflow

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `tests/unit/ci/test_release_workflow_policy.py` (several existing
  tests assert against the `build` job's inline `steps` list — after this
  change, those steps live in the reusable workflow instead, so the tests need
  to load and assert against `reusable-release-build.yml` for build-step
  content, and against `release.yml`'s `build` job only for the `uses:` /
  `with:` call itself)

**Step 1: Replace the `build` job body**

Replace the `build` job's `steps:` list in `release.yml` with:
```yaml
  build:
    name: Build Distribution
    needs: validate
    uses: ./.github/workflows/reusable-release-build.yml
    with:
      version: ${{ needs.validate.outputs.version }}
      tag: ${{ needs.validate.outputs.tag }}
      artifact-name: dist
```
(This requires the `validate` job to expose `version`/`tag` as job `outputs:` —
add an `outputs:` block to the `validate` job mirroring what `build`'s
"Extract version from tag" step already computes, or keep computing it
independently inside `reusable-release-build.yml` from the tag ref passed in —
pick whichever avoids duplicating the tag-parsing `sed`/`grep` logic in a third
place. Prefer computing it once in `validate` and passing the output down, since
`validate` already parses the tag.)

**Step 2: Update the affected workflow-policy tests**

Every existing test in `tests/unit/ci/test_release_workflow_policy.py` that does
`_jobs(workflow)["build"]["steps"]` against `RELEASE_WORKFLOW` now finds an
empty/absent `steps` list (the job uses `uses:` instead). Update each to load
`.github/workflows/reusable-release-build.yml` and read its `on.workflow_call`
job's steps instead. Run the full file after each edit to catch stragglers:

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -v`
Fix every failure by redirecting the assertion to the reusable workflow file
until all pass.

**Step 3: Commit**

```bash
git add .github/workflows/release.yml tests/unit/ci/test_release_workflow_policy.py
git commit -m "refactor: release.yml build job delegates to reusable-release-build.yml"
```

### Task B3: Wire `release-dry-run.yml`'s `dry-run` job to call the reusable workflow

**Files:**
- Modify: `.github/workflows/release-dry-run.yml`
- Modify: `tests/unit/ci/test_release_workflow_policy.py` (same class of update
  as Task B2, for the `RELEASE_DRY_RUN_WORKFLOW` / `dry-run` job assertions)

**Step 1: Replace the `dry-run` job's shared-step portion**

Keep `release-dry-run.yml`'s own steps for: checkout, tag validation, changelog
validation, dependency install (`uv sync`), running the test suite and golden
policy checks (these are dry-run-only pre-checks, not part of the shared build).
Replace everything from "Install build tools" through "Compile governance
artifacts" with a call to the same reusable workflow:
```yaml
      - name: Call shared release build
        uses: ./.github/workflows/reusable-release-build.yml
        with:
          version: ${{ env.VERSION }}
          tag: ${{ env.TAG }}
          artifact-name: release-dry-run-dist
```
Note: `workflow_call` usage inside a job's `steps:` list is not valid GitHub
Actions syntax — reusable workflows are only callable at the **job** level
(`jobs.<id>.uses:`), not as a step. Restructure `release-dry-run.yml` so the
shared-build portion becomes its own job (e.g. `dry-run-build`) that `uses:`
the reusable workflow, with the existing pre-checks (tag/changelog validation,
tests, golden policy) staying in a separate job that `dry-run-build` `needs:`.
Adjust `release-install-smoke`'s `needs:` accordingly.

**Step 2: Update the affected workflow-policy tests**

Same approach as Task B2, Step 2, but for `RELEASE_DRY_RUN_WORKFLOW`.

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -v`
Expected: PASS after all assertions are redirected correctly.

**Step 3: Commit**

```bash
git add .github/workflows/release-dry-run.yml tests/unit/ci/test_release_workflow_policy.py
git commit -m "refactor: release-dry-run.yml delegates shared build steps to reusable-release-build.yml"
```

### Task B4: Full regression pass for Part B

**Step 1: Run the full unit test suite**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit -q --tb=short`
Expected: PASS.

**Step 2: Validate both workflow files parse and reference a real reusable workflow path**

Run:
```bash
cd /home/sergio/dev/sdd-harness
python3 -c "
import yaml
for f in ['release.yml', 'release-dry-run.yml', 'reusable-release-build.yml']:
    yaml.safe_load(open(f'.github/workflows/{f}'))
    print(f, 'OK')
"
```
Expected: three `OK` lines.

**Step 3: Report status and stop for user review**

This is the highest-risk mechanical change so far (GitHub Actions reusable
workflow syntax can't be fully validated without actually running it in GitHub
Actions). Recommend the user push this to a branch and manually trigger
`release-dry-run.yml` via `workflow_dispatch` in the GitHub UI before merging,
since local YAML parsing only catches syntax errors, not `workflow_call`
wiring mistakes (bad `needs:`, missing `outputs:`, etc).

---

## Part C — Make the dry-run mandatory on `main` (Causa Raiz #3)

### Task C1: Add an automatic `push` trigger to `release-dry-run.yml`

**Files:**
- Modify: `.github/workflows/release-dry-run.yml`

**Step 1: Add the trigger**

```diff
 on:
   workflow_dispatch:
     inputs:
       tag:
         description: "SemVer tag to validate (example: v1.2.3 or V1.2.3)"
         required: true
         type: string
+  push:
+    branches: [main]
```

**Step 2: Make tag/version resolution work for both trigger types**

The existing "Validate semver tag format" and "Validate changelog entry exists"
steps read `${{ inputs.tag }}`, which is empty on a `push` trigger. Add a new
first step, gated to only the push path, that derives a version from HEAD
instead of a manual tag input:

```yaml
      - name: Resolve version for automatic (push) trigger
        if: github.event_name == 'push'
        shell: bash
        run: |
          set -euo pipefail
          # On a plain push to main (no tag yet), there is no release version to
          # validate against the changelog — this run only needs to prove the
          # build steps succeed, so use a synthetic version for
          # reusable-release-build.yml's version/tag inputs.
          echo "TAG=v0.0.0-dry-run" >> "$GITHUB_ENV"
          echo "VERSION=0.0.0-dry-run" >> "$GITHUB_ENV"
```
Adjust the existing "Validate semver tag format" and "Validate changelog entry
exists" steps to `if: github.event_name == 'workflow_dispatch'` (skip them on
the automatic push trigger, since there's no real tag or changelog entry to
check yet — those checks stay meaningful only for a deliberate dry-run against
a specific candidate tag).

**Step 3: Verify YAML validity**

Run: `cd /home/sergio/dev/sdd-harness && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release-dry-run.yml'))"`
Expected: no exception.

**Step 4: Add a workflow-policy test**

```python
def test_release_dry_run_triggers_on_push_to_main() -> None:
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    assert workflow["on"]["push"]["branches"] == ["main"]
```

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_release_workflow_policy.py -k triggers_on_push_to_main -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/release-dry-run.yml tests/unit/ci/test_release_workflow_policy.py
git commit -m "feat: run release dry-run automatically on every push to main"
```

### Task C2: Document the required branch-protection prerequisite

**Files:**
- Modify: `.github/workflows/release-dry-run.yml` (top-of-file comment) or
  `CONTRIBUTING.md`/`docs/` — pick whichever file already documents release
  process steps for this repo (search first).

**Step 1: Find the right place**

Run: `grep -rl "release" docs/ CONTRIBUTING.md README.md 2>/dev/null | head -5`
to find where release process steps are already documented, if anywhere.

**Step 2: Add a note**

Wherever the release process is documented (or, if nowhere, add a comment block
at the top of `release-dry-run.yml`), record:

> This workflow's `Validate & Build Dry Run` job (or, after Part B,
> `dry-run-build`) should be marked as a required status check on the `main`
> branch protection rule in GitHub repo settings. This is a one-time manual
> configuration step (Settings → Branches → main → require status checks) — it
> is not enforced by any file in this repository.

**Step 3: Commit**

```bash
git add <the file you edited>
git commit -m "docs: document required branch-protection setup for release dry-run gate"
```

---

## Part D — Migrate all packages to `hatch-vcs` dynamic versioning (Causa Raiz #4)

This is the highest-risk part. Do it on its own branch/checkpoint if possible,
and run the full `release-install-smoke` equivalent locally before considering
it done.

### Task D1: Migrate `sdd_core` (highest-risk package — has packaged native binaries)

**Files:**
- Modify: `packages/core/sdd_core/pyproject.toml`

**Step 1: Observe current behavior**

Run: `cd /home/sergio/dev/sdd-harness && uv run python -c "from importlib.metadata import version; print(version('sdd-core'))"`
Expected: `1.0.0` (hardcoded, confirms the bug being fixed).

**Step 2: Rewrite `pyproject.toml`**

Replace the full contents of `packages/core/sdd_core/pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "sdd-core"
dynamic = ["version"]
description = "Core domain model and contracts for SDD governance"
requires-python = ">=3.10"
license = {text = "Proprietary"}
authors = [
    {name = "Sergio Lacerda", email = "sergio.lacerda.vieira@gmail.com"},
]

dependencies = [
    "msgpack>=1.2.1",
    "structlog>=23.0",
]

[project.urls]
Repository = "https://github.com/SergioLacerda/sdd-harness"

[tool.hatch.version]
source = "vcs"
tag-pattern = "[vV](?P<version>[0-9]+\\.[0-9]+\\.[0-9]+)"
fallback-version = "0.0.0+unknown"

[tool.hatch.build.targets.wheel]
packages = ["src/sdd_core"]
artifacts = [
    "src/sdd_core/_native/*",
]
```

The `artifacts` key is required here because `_native/*` is generated at build
time (populated by `stage_packaged_compiler_assets.py`, not checked into git) —
hatchling's default inclusion only picks up files already tracked/present at
build time under the package dir, and `artifacts` explicitly force-includes
generated files that would otherwise be excluded by `.gitignore`-based
filtering. `mandate.spec` and `guidelines.dsl` (previously listed in
`[tool.setuptools.package-data]`) are checked-in files inside `src/sdd_core/`,
so hatchling includes them automatically as part of the package directory —
no extra config needed for those two.

**Step 3: Re-sync and verify dynamic version resolution**

Run: `cd /home/sergio/dev/sdd-harness && uv sync --all-groups --all-packages --extra test`
Expected: completes without error.

Run: `uv run python -c "from importlib.metadata import version; print(version('sdd-core'))"`
Expected: a version derived from `git describe`, not `1.0.0`.

**Step 4: Verify `py.typed`, `mandate.spec`, `guidelines.dsl` survived**

Run:
```bash
uv run python -c "
import importlib.resources as r
pkg = r.files('sdd_core')
for name in ('py.typed', 'mandate.spec', 'guidelines.dsl'):
    print(name, (pkg / name).is_file())
"
```
Expected: `True` for all three.

**Step 5: Verify the `_native` build-time artifact inclusion works end-to-end**

This can't be fully verified until Part A's `stage_packaged_compiler_assets.py`
has actually populated `_native/` with real binaries (a CI-only step, since it
needs cross-compiled Go binaries in `dist/`). As a local approximation:

Run:
```bash
cd /home/sergio/dev/sdd-harness
mkdir -p packages/core/sdd_core/src/sdd_core/_native
echo "fake binary for local wheel-build smoke test" > packages/core/sdd_core/src/sdd_core/_native/sdd-compile-linux-amd64
uv run python -m build packages/core/sdd_core --outdir /tmp/sdd-core-wheel-check
python3 -c "
import zipfile, glob
whl = glob.glob('/tmp/sdd-core-wheel-check/*.whl')[0]
names = zipfile.ZipFile(whl).namelist()
assert any('_native/sdd-compile-linux-amd64' in n for n in names), names
print('native asset present in wheel: OK')
"
rm -rf packages/core/sdd_core/src/sdd_core/_native /tmp/sdd-core-wheel-check
```
Expected: `native asset present in wheel: OK`. The `rm -rf` at the end is
important — the fake binary must not be left behind (it's not a real
`_native/` output and would confuse a later real CI build if committed).

**Step 6: Commit**

```bash
git add packages/core/sdd_core/pyproject.toml uv.lock
git commit -m "fix: migrate sdd_core to hatch-vcs dynamic versioning"
```

### Task D2: Migrate the remaining 6 packages

**Files:**
- Modify: `packages/core/sdd_runtime/pyproject.toml`
- Modify: `packages/core/sdd_telemetry/pyproject.toml`
- Modify: `packages/features/sdd_adapters/pyproject.toml`
- Modify: `packages/features/sdd_integration/pyproject.toml`
- Modify: `packages/features/sdd_pages/pyproject.toml`
- Modify: `packages/features/sdd_skills/pyproject.toml`
- Modify: `packages/interfaces/sdd_wizard/pyproject.toml`

None of these have build-time-generated files like `sdd_core`'s `_native/` —
their `[tool.setuptools.package-data]` entries only list checked-in files, which
hatchling includes automatically. For each package, apply this transformation:

1. Replace:
   ```toml
   [build-system]
   requires = ["setuptools>=61.0"]
   build-backend = "setuptools.build_meta"
   ```
   with:
   ```toml
   [build-system]
   requires = ["hatchling", "hatch-vcs"]
   build-backend = "hatchling.build"
   ```
2. Replace `version = "1.0.0"` with `dynamic = ["version"]` in `[project]`.
3. Add at the end:
   ```toml
   [tool.hatch.version]
   source = "vcs"
   tag-pattern = "[vV](?P<version>[0-9]+\\.[0-9]+\\.[0-9]+)"
   fallback-version = "0.0.0+unknown"

   [tool.hatch.build.targets.wheel]
   packages = ["src/<package_dir_name>"]
   ```
   (`<package_dir_name>` is each package's actual `src/` subdirectory — e.g.
   `sdd_runtime`, `sdd_telemetry`, `sdd_adapters`, `sdd_integration`,
   `sdd_pages`, `sdd_skills`, `sdd_wizard` — matches the value already used in
   each file's `[tool.setuptools.package-data]` key.)
4. Remove the `[tool.setuptools]`, `[tool.setuptools.package-data]`, and
   `[tool.setuptools.packages.find]` sections entirely.

Do this one package at a time, and after each one:

Run: `cd /home/sergio/dev/sdd-harness && uv sync --all-groups --all-packages --extra test`
Expected: no error.

Run: `uv run python -c "from importlib.metadata import version; print(version('<dist-name>'))"`
(substitute the package's `[project].name`, e.g. `sdd-runtime`)
Expected: a git-derived version, not `1.0.0`.

After all 6 are migrated:

**Step: Commit**

```bash
git add packages/core/sdd_runtime/pyproject.toml packages/core/sdd_telemetry/pyproject.toml packages/features/sdd_adapters/pyproject.toml packages/features/sdd_integration/pyproject.toml packages/features/sdd_pages/pyproject.toml packages/features/sdd_skills/pyproject.toml packages/interfaces/sdd_wizard/pyproject.toml uv.lock
git commit -m "fix: migrate remaining 6 workspace packages to hatch-vcs dynamic versioning"
```

### Task D3: Remove `sync_versions.py` and its invocations

**Files:**
- Delete: `tools/release/sync_versions.py`
- Delete: `tests/unit/tools/test_release_sync_versions.py` (if it exists — check
  first; it was referenced in an earlier, separate analysis package for
  `sdd_cli`'s migration)
- Modify: `.github/workflows/reusable-release-build.yml` (remove the "Sync
  sub-package versions to tag" step and the "Verify all package versions match
  tag" step's static-version grep logic — see Step 2)
- Modify: `tools/release/resolve_vcs_version.py` (drop its `sync_versions`
  import — it only used `sync_versions.normalize_version`; inline that small
  regex function directly, or move `normalize_version` to
  `validate_release_assets.py` if that file is kept as the shared home for
  release-tag-format helpers — pick whichever avoids resurrecting a
  cross-script import for a single 6-line function. Simplest: inline
  `normalize_version`'s body directly into `resolve_vcs_version.py`, since after
  D1-D2 no script actually needs to *write* a version into any `pyproject.toml`
  anymore — validating/normalizing the tag string is the only remaining need.)
- Modify: `tests/unit/tools/*` — remove or update any test importing
  `tools.release.sync_versions`

**Step 1: Find every reference**

Run: `cd /home/sergio/dev/sdd-harness && grep -rln "sync_versions" --include="*.py" --include="*.yml" --include="*.md" .`

**Step 2: Remove the "Sync sub-package versions to tag" step from the reusable workflow**

Delete that step entirely from `reusable-release-build.yml` (Part B put it
there). Replace the "Verify all package versions match tag" step's body with:
```yaml
      - name: Verify all package versions resolve via VCS
        shell: bash
        run: |
          VERSION="${{ inputs.version }}"
          echo "Verifying all package versions resolve to $VERSION via hatch-vcs"
          for pkg_dir in packages/core/* packages/features/* packages/interfaces/*; do
            if [ -f "$pkg_dir/pyproject.toml" ]; then
              if ! grep -q '^dynamic = \[.*"version".*\]' "$pkg_dir/pyproject.toml"; then
                echo "❌ ERROR: $pkg_dir does not use dynamic (VCS) versioning"
                exit 1
              fi
              echo "✓ $pkg_dir uses dynamic (VCS) versioning"
            fi
          done
```
The actual per-package version-vs-tag match is verified later, per package, by
checking each built wheel's filename in the "Build packages" step (same pattern
already used for `sdd_cli` at `release.yml:229-235` before Part B moved it into
the reusable workflow) — extend that existing wheel-filename check to loop over
**all** built wheels, not just `sdd_cli`'s:
```yaml
          VERSION="${{ inputs.version }}"
          for pkg_dir in packages/core/* packages/features/* packages/interfaces/*; do
            if [ -f "$pkg_dir/pyproject.toml" ]; then
              echo "Building $pkg_dir"
              python -m build "$pkg_dir" --outdir dist/
            fi
          done
          for pkg_dir in packages/core/* packages/features/* packages/interfaces/*; do
            [ -f "$pkg_dir/pyproject.toml" ] || continue
            pkg_name=$(grep -E '^name = ' "$pkg_dir/pyproject.toml" | head -1 | sed 's/name = "\(.*\)"/\1/' | tr '-' '_')
            if ! ls dist/"$pkg_name"-"$VERSION"-*.whl >/dev/null 2>&1; then
              echo "❌ ERROR: built $pkg_name wheel does not match tag version $VERSION"
              ls dist/"$pkg_name"-*.whl || true
              exit 1
            fi
            echo "✓ $pkg_name wheel matches tag version $VERSION"
          done
```

**Step 3: Remove `SETUPTOOLS_SCM_PRETEND_VERSION`**

Now that no step rewrites `pyproject.toml` files in place, the working tree
stays clean through the build, so `hatch-vcs` resolves the exact tag without
needing the pin. Remove the `env:` block (and its long explanatory comment)
from the "Build packages" step in `reusable-release-build.yml`.

**Step 4: Delete `sync_versions.py` and inline `normalize_version` into `resolve_vcs_version.py`**

```bash
rm /home/sergio/dev/sdd-harness/tools/release/sync_versions.py
```

In `resolve_vcs_version.py`, replace the import and its one call site:
```diff
-try:
-    from tools.release import sync_versions
-except ModuleNotFoundError:  # pragma: no cover - script execution path
-    import sync_versions  # type: ignore[import-not-found,no-redef]
+import re
+
+_SEMVER_TAG_RE = re.compile(r"^[vV]?(?P<version>\d+\.\d+\.\d+)$")
+
+
+def normalize_version(value: str) -> str:
+    """Return the plain semver version from a version or Git tag string."""
+    match = _SEMVER_TAG_RE.match(value)
+    if match is None:
+        print(f"ERROR: Invalid version/tag '{value}' (expected [v|V]X.Y.Z)")
+        sys.exit(1)
+    return match.group("version")
```
and:
```diff
-    print(sync_versions.normalize_version(resolve_head_tag(repo_root)))
+    print(normalize_version(resolve_head_tag(repo_root)))
```
(Note: this duplicates Task A4's earlier simplification of this file's imports
— that's expected, since Part D removes the whole module Part A's fix was
importing from. If executing sequentially, this Task D3 edit supersedes Task
A4's version.)

**Step 5: Remove/update dependent tests**

Delete `tests/unit/tools/test_release_sync_versions.py` if present. Remove the
now-stale `test_release_build_step_pins_setuptools_scm_version` test from
`tests/unit/ci/test_release_workflow_policy.py` (asserts a env var that no
longer exists). Update `test_release_build_syncs_versions_from_git_tag` and
`test_release_dry_run_syncs_versions_from_git_tag` — both assert
`sync_versions` invocation, which no longer exists; replace with an assertion
that the wheel-filename verification loop is present instead:
```python
def test_release_build_verifies_all_wheels_match_tag_version() -> None:
    workflow = _load_workflow(Path(".github/workflows/reusable-release-build.yml"))
    steps = "\n".join(
        step.get("run", "")
        for job in workflow["jobs"].values()
        for step in job["steps"]
    )
    assert "sync_versions" not in steps
    assert "does not match tag version" in steps
```
(Adjust the job-traversal to match however Task B1 actually named the job(s)
inside the reusable workflow.)

**Step 6: Run the full test suite**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit -q --tb=short`
Expected: PASS, no references to `sync_versions` remain anywhere in test
failures.

**Step 7: Commit**

```bash
git add -A tools/release .github/workflows/reusable-release-build.yml tests/unit
git commit -m "refactor: remove sync_versions.py, verify versions via built wheel filenames only"
```

### Task D4: Full regression pass for Part D

**Step 1: Run the full test suite**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest -v`
Expected: all pass, matching or exceeding the pre-change baseline count.

**Step 2: Build every package locally and confirm each wheel's version matches HEAD's resolved version**

```bash
cd /home/sergio/dev/sdd-harness
rm -rf /tmp/full-dist-check && mkdir -p /tmp/full-dist-check
for pkg_dir in packages/core/* packages/features/* packages/interfaces/*; do
  [ -f "$pkg_dir/pyproject.toml" ] || continue
  uv run python -m build "$pkg_dir" --outdir /tmp/full-dist-check
done
ls /tmp/full-dist-check
```
Expected: 8 wheels (7 migrated + `sdd_cli`), all sharing the same version
suffix (derived from the same HEAD commit).

**Step 3: Report status and stop for user review**

This is the riskiest part of the whole plan. Recommend the user runs
`make release-dry-run` and, if comfortable, manually triggers
`release-dry-run.yml` in GitHub Actions before proceeding to Part E, since local
`python -m build` can't fully replicate the CI cross-compile + wheel-house
download + install-smoke sequence.

---

## Part E — Gate `container-release.yml` on `release.yml` success (Causa Raiz #5)

### Task E1: Add the cross-workflow success check

**Files:**
- Modify: `.github/workflows/container-release.yml`

**Step 1: Add the gate step**

Insert a new step immediately before "Login to GHCR (retry)" (currently line
62), guarded by the same `if:` condition as the publish steps around it:

```yaml
      - name: Verify a successful release.yml run exists for this tag
        if: ${{ github.event_name == 'workflow_dispatch' && inputs.publish == 'true' && startsWith(github.ref, 'refs/tags/') }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        shell: bash
        run: |
          set -euo pipefail
          python3 - <<'PY'
          import json
          import os
          import sys
          import urllib.request

          tag = os.environ["GITHUB_REF_NAME"]
          url = (
              "https://api.github.com/repos/"
              f"{os.environ['GITHUB_REPOSITORY']}/releases/tags/{tag}"
          )
          request = urllib.request.Request(
              url,
              headers={
                  "Accept": "application/vnd.github+json",
                  "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                  "X-GitHub-Api-Version": "2022-11-28",
              },
          )
          try:
              with urllib.request.urlopen(request, timeout=30) as response:
                  payload = json.load(response)
          except urllib.error.HTTPError as exc:
              print(f"ERROR: no GitHub Release found for tag {tag} ({exc})")
              sys.exit(1)
          if payload.get("draft", True):
              print(f"ERROR: GitHub Release for tag {tag} is still a draft")
              sys.exit(1)
          print(f"GitHub Release for tag {tag} confirmed published: {payload['html_url']}")
          PY
```
This reuses the exact API-call pattern already present in
`release.yml:470-516` ("Verify GitHub Release exposes standalone compiler
assets") — a published (non-draft) GitHub Release only exists once
`release.yml`'s `release` job has completed successfully, so this is a reliable
proxy for "the release build succeeded."

Note this only guards the **tag-triggered manual-publish** path
(`startsWith(github.ref, 'refs/tags/')`); a `workflow_dispatch` publish from a
branch (not a tag) has no corresponding `release.yml` run to check against by
design (container-release.yml's own trigger config allows publishing test
images from `main` too) — the `if:` condition above correctly skips the check
in that case.

**Step 2: Verify YAML validity**

Run: `cd /home/sergio/dev/sdd-harness && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/container-release.yml'))"`
Expected: no exception.

**Step 3: Add a workflow-policy test**

Create `tests/unit/ci/test_container_release_workflow_policy.py` (new file,
mirroring the loading pattern from `test_release_workflow_policy.py`):

```python
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTAINER_RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "container-release.yml"


def _load_workflow(path: Path) -> dict:
    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_constructor(
        "tag:yaml.org,2002:bool",
        lambda loader, node: loader.construct_scalar(node),
    )
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)


def test_container_release_verifies_release_success_before_publishing() -> None:
    workflow = _load_workflow(CONTAINER_RELEASE_WORKFLOW)
    steps = workflow["jobs"]["build-scan-sign-push"]["steps"]
    step_names = [step.get("name") for step in steps]
    assert "Verify a successful release.yml run exists for this tag" in step_names

    verify_index = step_names.index(
        "Verify a successful release.yml run exists for this tag"
    )
    login_index = step_names.index("Login to GHCR (retry)")
    assert verify_index < login_index, (
        "the release-success check must run before GHCR login/publish steps"
    )
```

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest tests/unit/ci/test_container_release_workflow_policy.py -v`
Expected: PASS.

**Step 4: Commit**

```bash
git add .github/workflows/container-release.yml tests/unit/ci/test_container_release_workflow_policy.py
git commit -m "feat: gate container-release publish on a successful release.yml run"
```

---

## Final: Full regression pass and archive the design doc

### Task F1: Full suite + archive

**Step 1: Run the full test suite one more time**

Run: `cd /home/sergio/dev/sdd-harness && uv run pytest -v`
Expected: all pass.

**Step 2: Run local release-readiness checks**

Run:
```bash
cd /home/sergio/dev/sdd-harness
uv run python tools/ci/check_golden_policy.py --mode strict
uv run python tools/ci/check_release_readiness_v1.py
make release-dry-run
```
Expected: all pass.

**Step 3: Report final diff summary**

Run: `git status --short && git log --oneline -25`
Report back to the user with the full list of commits from this plan before
any push, and explicitly flag that Part B and Part D should be validated with
a real `workflow_dispatch` run of `release-dry-run.yml` in GitHub Actions
before the user cuts the next real tag (per this repo's git protocol, tag
creation itself stays the user's action, not something this plan executes).

**Step 4: Archive the design doc (filesystem move, not a git operation)**

```bash
mkdir -p /home/sergio/dev/sdd-harness/.analysis/done
mv /home/sergio/dev/sdd-harness/.analysis/pending/2026-07-16-release-pipeline-overhaul-design.md \
   /home/sergio/dev/sdd-harness/.analysis/done/2026-07-16-release-pipeline-overhaul-design.md
```
(`.analysis/` is gitignored — plain filesystem move, no `git mv` needed.)
