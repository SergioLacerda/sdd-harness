# CompilerRunner Sign Diagnostics Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Replace the opaque `"sdd-compile {context} produced no output"` error with a
diagnosis that includes the real process stderr/returncode, and detect the specific case
of an out-of-date `sdd-compile` binary missing a subcommand (e.g. `sign`), giving the user
actionable remediation instead of a dead end.

**Architecture:** `CompilerRunner._parse_json` currently takes only `stdout` and is a
`@staticmethod`. It becomes an instance method that takes the full process `result`
object (which already carries `stdout`, `stderr`, `returncode`, `success` — see
`packages/core/sdd_core/src/sdd_core/utils/_process_runner.py:119-125`). On empty/invalid
stdout it includes stderr/returncode in the raised `CompilerRunnerError`. A new helper,
`_unsupported_subcommand_error`, detects Cobra's `unknown command "<subcommand>"` pattern
in stderr and raises a distinct error naming the resolved binary path, its version (queried
via the already-existing `self.version()`), and two remediation steps.

**Tech Stack:** Python 3.10, pytest, `sdd_core.utils.compiler_runner`.

---

### Task 1: Change `_parse_json` to accept the full process result and surface stderr/returncode

**Files:**
- Modify: `packages/core/sdd_core/src/sdd_core/utils/compiler_runner.py:399-410`
- Modify (call sites): `packages/core/sdd_core/src/sdd_core/utils/compiler_runner.py:325,336,366,390`
- Test: `packages/core/sdd_core/tests/test_compiler_runner.py`

**Step 1: Write the failing tests**

Replace the two existing `_parse_json` tests (lines 340-347) — they call `_parse_json` as
a static method with a bare string, which will no longer be the signature — with tests
against the new signature:

```python
def test_parse_json_raises_on_empty_stdout_includes_stderr_and_returncode() -> None:
    result = SimpleNamespace(stdout="   ", stderr="boom", returncode=7)

    with pytest.raises(CompilerRunnerError) as exc_info:
        CompilerRunner._parse_json(result, context="compile")

    message = str(exc_info.value)
    assert "sdd-compile compile produced no output" in message
    assert "stderr: boom" in message
    assert "returncode: 7" in message


def test_parse_json_raises_on_invalid_json_includes_stderr_and_returncode() -> None:
    result = SimpleNamespace(stdout="not json", stderr="parse issue", returncode=1)

    with pytest.raises(CompilerRunnerError) as exc_info:
        CompilerRunner._parse_json(result, context="validate")

    message = str(exc_info.value)
    assert "sdd-compile validate produced invalid JSON" in message
    assert "stderr: parse issue" in message
    assert "returncode: 1" in message


def test_parse_json_empty_stdout_with_no_stderr_omits_stderr_line() -> None:
    result = SimpleNamespace(stdout="", stderr="", returncode=0)

    with pytest.raises(CompilerRunnerError) as exc_info:
        CompilerRunner._parse_json(result, context="compile")

    assert "stderr:" not in str(exc_info.value)
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core/sdd_core && python -m pytest tests/test_compiler_runner.py -k parse_json -v`
Expected: FAIL — old tests calling `_parse_json("   ", context="compile")` with a bare
string either raise `AttributeError` (no `.strip()` path change) or the new tests fail
because `_parse_json` doesn't yet read `.stderr`/`.returncode`.

**Step 3: Write minimal implementation**

Replace `_parse_json` (lines 399-410 in `compiler_runner.py`):

```python
    @staticmethod
    def _parse_json(result: Any, *, context: str) -> dict[str, Any]:
        text = result.stdout.strip()
        if not text:
            raise CompilerRunnerError(
                CompilerRunner._diagnostic_message(
                    f"sdd-compile {context} produced no output", result
                )
            )
        try:
            return cast(dict[str, Any], json.loads(text))
        except json.JSONDecodeError as exc:
            raise CompilerRunnerError(
                CompilerRunner._diagnostic_message(
                    f"sdd-compile {context} produced invalid JSON: {exc}", result
                )
            ) from exc

    @staticmethod
    def _diagnostic_message(headline: str, result: Any) -> str:
        parts = [headline]
        stderr = (getattr(result, "stderr", "") or "").strip()
        if stderr:
            parts.append(f"stderr: {stderr}")
        returncode = getattr(result, "returncode", None)
        if returncode is not None:
            parts.append(f"returncode: {returncode}")
        return " | ".join(parts)
```

Update the four call sites to pass `result` instead of `result.stdout`:
- Line 325: `payload = self._parse_json(result, context="compile")`
- Line 336: `payload = self._parse_json(result, context="validate")`
- Line 366: `payload = self._parse_json(result, context="sign")`
- Line 390: `payload = self._parse_json(result, context="verify")`

**Step 4: Run tests to verify they pass**

Run: `cd packages/core/sdd_core && python -m pytest tests/test_compiler_runner.py -v`
Expected: PASS (full file — this also confirms no other test relied on the old
`_parse_json(str, ...)` signature).

**Step 5: Commit**

```bash
git add packages/core/sdd_core/src/sdd_core/utils/compiler_runner.py packages/core/sdd_core/tests/test_compiler_runner.py
git commit -m "fix: surface stderr/returncode in CompilerRunner parse errors"
```

---

### Task 2: Detect unsupported-subcommand failures and raise actionable guidance

**Files:**
- Modify: `packages/core/sdd_core/src/sdd_core/utils/compiler_runner.py` (`sign`, `compile`, `validate_compilation_detailed` methods; add new helper)
- Test: `packages/core/sdd_core/tests/test_compiler_runner.py`

**Step 1: Write the failing test**

Cobra's unsupported-subcommand stderr looks like: `Error: unknown command "sign" for "sdd-compile"`.
Add a test exercising `sign()` end-to-end through this path:

```python
def test_sign_raises_actionable_error_when_binary_missing_subcommand() -> None:
    call_log: list[list[str]] = []

    def _fake_run(args: list[str]) -> SimpleNamespace:
        call_log.append(args)
        if "version" in args:
            return SimpleNamespace(success=True, stdout="1.0.0\n", stderr="", returncode=0)
        return SimpleNamespace(
            success=False,
            stdout="",
            stderr='Error: unknown command "sign" for "sdd-compile"',
            returncode=1,
        )

    runner = CompilerRunner.__new__(CompilerRunner)
    runner._binary = Path("/fake/sdd-compile")  # type: ignore[attr-defined]
    runner._runner = SimpleNamespace(run=_fake_run)  # type: ignore[attr-defined]

    with pytest.raises(CompilerRunnerError) as exc_info:
        runner.sign(
            artifact_path="a.json", key_path="k.key", key_id="k1", profile="master"
        )

    message = str(exc_info.value)
    assert "does not support the 'sign' subcommand" in message
    assert "/fake/sdd-compile" in message
    assert "version 1.0.0" in message
    assert "~/.sdd/bin/1.0.0" in message
    assert "SDD_COMPILE_BIN" in message
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core/sdd_core && python -m pytest tests/test_compiler_runner.py -k missing_subcommand -v`
Expected: FAIL — currently this raises the generic "produced no output" error (stdout is
empty), not the actionable one.

**Step 3: Write minimal implementation**

Add a regex-based detector and wire it into `_parse_json`'s empty-stdout branch (only
reachable for exactly the empty-stdout Cobra-usage-error case; non-empty invalid JSON
stays as-is):

```python
import re

_UNKNOWN_COMMAND_RE = re.compile(r'unknown command "([^"]+)" for')
```

In `_parse_json`, before raising the generic "produced no output" error, check for the
pattern and raise a distinct error instead. Since `_parse_json` is a `@staticmethod` and
doesn't have access to `self` (needed for `self.version()` and `self._binary`), move the
unsupported-subcommand check into the calling instance methods instead, immediately after
`self._runner.run(...)`, before calling `_parse_json`:

```python
    def sign(
        self,
        *,
        artifact_path: str | Path,
        key_path: str | Path,
        key_id: str,
        profile: str,
    ) -> SignResult:
        """Sign an artifact with a native Ed25519 key via the Go binary."""
        result = self._runner.run(
            [
                str(self._binary),
                "sign",
                "--artifact",
                str(artifact_path),
                "--key",
                str(key_path),
                "--key-id",
                key_id,
                "--profile",
                profile,
            ]
        )
        self._raise_if_unsupported_subcommand(result, subcommand="sign")
        payload = self._parse_json(result, context="sign")
        if not payload.get("ok", False):
            error = payload.get("error") or result.stderr.strip() or "sign failed"
            raise CompilerRunnerError(f"sdd-compile sign failed: {error}")
        return payload  # type: ignore[return-value]
```

Add the helper (near `_parse_json`):

```python
    def _raise_if_unsupported_subcommand(self, result: Any, *, subcommand: str) -> None:
        match = _UNKNOWN_COMMAND_RE.search(result.stderr or "")
        if not match or match.group(1) != subcommand:
            return
        try:
            binary_version = self.version()
        except CompilerRunnerError:
            binary_version = "unknown"
        raise CompilerRunnerError(
            f"sdd-compile at {self._binary} (version {binary_version}) does not "
            f"support the '{subcommand}' subcommand — it is likely older than the "
            "installed sdd-cli. Fix by clearing the cached binary "
            f"(rm -rf ~/.sdd/bin/{binary_version} then retry) or by setting "
            "SDD_COMPILE_BIN to a compatible local binary."
        )
```

Apply the same `self._raise_if_unsupported_subcommand(result, subcommand="...")` call
before `_parse_json` in `compile` and `validate_compilation_detailed` too, for
consistency (same class of failure can happen for any subcommand as binaries age).

**Step 4: Run tests to verify they pass**

Run: `cd packages/core/sdd_core && python -m pytest tests/test_compiler_runner.py -v`
Expected: PASS (full file).

**Step 5: Commit**

```bash
git add packages/core/sdd_core/src/sdd_core/utils/compiler_runner.py packages/core/sdd_core/tests/test_compiler_runner.py
git commit -m "fix: detect unsupported sdd-compile subcommands with actionable guidance"
```

---

### Task 3: Full regression pass and archive the analysis package

**Files:**
- Test: `packages/core/sdd_core/tests/test_compiler_runner.py` (whole file)
- Move: `.analysis/pending/20260715-fix-compiler-runner-sign-diagnostics/` → `.analysis/done/20260715-fix-compiler-runner-sign-diagnostics/`

**Step 1: Run the full sdd_core test suite**

Run: `cd packages/core/sdd_core && python -m pytest tests/ -v`
Expected: PASS, all tests green, including the untouched existing tests
(`test_compile_raises_when_result_reports_not_ok`, `test_version_raises_on_process_failure`,
etc.) to confirm no regression in unrelated call sites.

**Step 2: Move the analysis package to done**

```bash
mkdir -p .analysis/done
git mv .analysis/pending/20260715-fix-compiler-runner-sign-diagnostics .analysis/done/20260715-fix-compiler-runner-sign-diagnostics
```

**Step 3: Commit**

```bash
git commit -m "docs: archive compiler-runner sign diagnostics analysis package"
```
