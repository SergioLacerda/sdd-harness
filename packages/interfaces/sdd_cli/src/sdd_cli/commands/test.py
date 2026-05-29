"""Test."""

import json
import os
import sys
from pathlib import Path
from typing import Any

import typer

from sdd_cli.utils.environment import detect_repo_root

app = typer.Typer()


@app.callback()
def _() -> None:
    """Run test pipeline."""


class TestCommand:
    """TestCommand."""

    def run(
        self,
        verbose: bool,
        fail_fast: bool,
        coverage: bool,
        cov_fail_under: int | None,
    ) -> None:
        """Run."""
        root = detect_repo_root()
        script = root / "tools" / "testing" / "run-all-tests.py"

        if not script.exists():
            typer.echo(f"ERROR: Script not found: {script}")
            raise typer.Exit(1)

        cmd = [sys.executable, str(script)]

        if verbose:
            cmd.append("--verbose")
        if fail_fast:
            cmd.append("--fail-fast")
        if not coverage:
            cmd.append("--no-coverage")
        if cov_fail_under is not None:
            cmd.extend(["--cov-fail-under", str(cov_fail_under)])

        typer.echo(f"Running tests from: {script}")

        from sdd_core.utils.process import (
            ProcessAuthorizationError,
            ProcessNonZeroExitError,
            ProcessSpawnError,
            ProcessTimeoutError,
            SafeProcessRunner,
        )

        try:
            runner = SafeProcessRunner()
            runner.run(cmd, cwd=root, check=True, capture_output=False)
        except ProcessNonZeroExitError as err:
            typer.echo(f"ERROR: test pipeline failed: {err}", err=True)
            raise typer.Exit(1) from None
        except ProcessAuthorizationError as err:
            typer.echo(f"ERROR: execution blocked by policy: {err}", err=True)
            raise typer.Exit(2) from None
        except ProcessTimeoutError:
            typer.echo("ERROR: test pipeline timed out", err=True)
            raise typer.Exit(124) from None
        except ProcessSpawnError as err:
            typer.echo(f"ERROR: could not start test pipeline: {err}", err=True)
            raise typer.Exit(127) from None


@app.command()
def run(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose pytest output"
    ),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", "-x", help="Stop on first failure"
    ),
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Show project coverage summary"
    ),
    cov_fail_under: int | None = typer.Option(
        None,
        "--cov-fail-under",
        help="Fail when coverage is below this percentage (default: 80)",
    ),
) -> None:
    """Run full test pipeline"""
    TestCommand().run(
        verbose=verbose,
        fail_fast=fail_fast,
        coverage=coverage,
        cov_fail_under=cov_fail_under,
    )


def _check_import(module: str) -> bool:
    """Try a real import (not just find_spec) to catch broken packages."""
    try:
        __import__(module)
        return True
    except Exception:
        return False


def _run_script(script_path: str, extra_args: list[str], cwd: str) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    # Match CI behavior on Windows consoles with limited encodings.
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run(
        [sys.executable, script_path] + extra_args,
        cwd=cwd,
        env=env,
    )
    return result.returncode


def _run_cli(args: list[str], cwd: str) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run([sys.executable, "-m", "sdd_cli"] + args, cwd=cwd, env=env)
    return result.returncode


def _run_pytest(args: list[str], cwd: str) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run([sys.executable, "-m", "pytest"] + args, cwd=cwd, env=env)
    return result.returncode


@app.command(name="ci-validate")
def ci_validate(  # noqa: C901
    health: bool = typer.Option(
        True,
        "--health/--no-health",
        help="Run health check (tools/health/health_check.py)",
    ),
    governance: bool = typer.Option(
        True,
        "--governance/--no-governance",
        help="Run governance compliance + integrity (tools/governance/compliance.py)",
    ),
    tests: bool = typer.Option(
        True,
        "--tests/--no-tests",
        help="Run full test suite (tools/testing/run-all-tests.py)",
    ),
    soak_threads: bool = typer.Option(
        False,
        "--soak-threads/--no-soak-threads",
        help="Run slow thread lifecycle soak test for metrics service",
    ),
) -> None:
    """Preflight CI validation: import checks + CI-like governance + tests."""
    root = detect_repo_root()
    failed = False

    modules = [
        "yaml",
        "typer",
        "rich",
        "msgpack",
        "sdd_core",
        "sdd_compiler",
        "sdd_integration",
        "sdd_cli",
    ]
    typer.echo("=== Import checks ===")
    for mod in modules:
        ok = _check_import(mod)
        typer.echo(f"  {'PASS' if ok else 'FAIL'}: {mod}")
        if not ok:
            failed = True

    if health:
        typer.echo("\n=== Health check ===")
        script = root / "tools" / "health" / "health_check.py"
        if not script.exists():
            typer.echo(f"  FAIL: not found at {script}")
            failed = True
        else:
            if _run_script(str(script), ["--verbose"], str(root)) != 0:
                failed = True

    if governance:
        typer.echo("\n=== Governance compliance ===")
        typer.echo("  Running governance compile...")
        if _run_cli(["governance", "compile"], str(root)) != 0:
            failed = True

        typer.echo("  Running runtime status...")
        runtime_rc = _run_cli(["runtime", "status", "--force"], str(root))
        # CI accepts NOT_CONNECTED (rc=3) in some contexts.
        if runtime_rc not in (0, 3):
            failed = True

        typer.echo("  Running governance score/adherence/validate...")
        if _run_cli(["governance", "score", "--threshold", "0"], str(root)) != 0:
            failed = True
        if _run_cli(["governance", "adherence", "--threshold", "0"], str(root)) != 0:
            failed = True
        if _run_cli(["governance", "validate"], str(root)) != 0:
            failed = True

        script = root / "tools" / "governance" / "compliance.py"
        if not script.exists():
            typer.echo(f"  FAIL: not found at {script}")
            failed = True
        else:
            if (
                _run_script(str(script), ["--verify", "--check-integrity"], str(root))
                != 0
            ):
                failed = True

    if tests:
        typer.echo("\n=== Test suite ===")
        script = root / "tools" / "testing" / "run-all-tests.py"
        if not script.exists():
            typer.echo(f"  FAIL: not found at {script}")
            failed = True
        else:
            if _run_script(str(script), [], str(root)) != 0:
                failed = True

    if soak_threads:
        typer.echo("\n=== Thread soak ===")
        soak_args = [
            "packages/interfaces/sdd_cli/tests/test_metrics_commands.py",
            "-k",
            "soak_restart_cycles",
        ]
        if _run_pytest(soak_args, str(root)) != 0:
            failed = True

    if failed:
        typer.echo("\nERROR: One or more checks failed")
        raise typer.Exit(1)

    typer.echo("\nAll checks passed")


# ---------------------------------------------------------------------------
# review-golden — AST diff against golden snapshot (Phase 2 §4)
# ---------------------------------------------------------------------------

_GOLDEN_FILENAME = "golden-ast.json"


def _resolve_golden_path(root: Path) -> Path:
    return root / ".sdd" / "runtime" / _GOLDEN_FILENAME


def _find_artifact(root: Path) -> Path | None:
    """Return the compiled governance-core.json from canonical .sdd location."""
    candidate = root / ".sdd" / "compiled" / "governance-core.json"
    return candidate if candidate.exists() else None


def _save_golden(golden_path: Path, current_ast: Any) -> None:
    """Save the current AST as the golden snapshot."""
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(current_ast.to_json(), encoding="utf-8")
    typer.echo(f"Golden snapshot updated: {golden_path}")
    typer.echo(
        f"  Items: {len(current_ast.items)}, fingerprint: {current_ast.source_fingerprint[:12]}…"
    )


def _load_golden_ast(golden_path: Path) -> Any:
    """Load golden AST from file; raise typer.Exit(1) on error."""
    from sdd_compiler.ast import GovernanceAST

    try:
        return GovernanceAST.from_dict(
            json.loads(golden_path.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        typer.echo(f"ERROR: Failed to load golden snapshot: {exc}", err=True)
        raise typer.Exit(1) from exc


def _print_diff(diff: Any) -> None:
    """Print a formatted diff report of breaking/non-breaking/added changes."""
    if diff.breaking_changes:
        typer.echo(f"\n  BREAKING changes ({len(diff.breaking_changes)}):")
        for entry in diff.breaking_changes:
            typer.echo(
                f"    [{entry.item_id}] {entry.change_type}: {entry.before!r} → {entry.after!r}"
            )

    if diff.non_breaking_changes:
        typer.echo(f"\n  Non-breaking changes ({len(diff.non_breaking_changes)}):")
        for entry in diff.non_breaking_changes:
            field_info = f" ({entry.field})" if entry.field else ""
            typer.echo(
                f"    [{entry.item_id}]{field_info}: {entry.before!r} → {entry.after!r}"
            )

    if diff.added_items:
        typer.echo(f"\n  Added ({len(diff.added_items)}):")
        for entry in diff.added_items:
            typer.echo(f"    + [{entry.item_id}] {entry.after}")


@app.command(name="review-golden")
def review_golden(
    update: bool = typer.Option(
        False,
        "--update",
        help="Update the golden snapshot with the current artifact.",
    ),
    fail_on_breaking: bool = typer.Option(
        True,
        "--fail-on-breaking/--no-fail-on-breaking",
        help="Exit 1 when breaking changes are detected (default: true).",
    ),
    artifact: Path = typer.Option(  # noqa: B008
        None,
        "--artifact",
        help="Path to governance-core.json artifact (auto-detected if omitted).",
    ),
    golden: Path = typer.Option(  # noqa: B008
        None,
        "--golden",
        help="Path to golden snapshot JSON (default: .sdd/runtime/golden-ast.json).",
    ),
) -> None:
    """Compare current compiled artifact against the golden AST snapshot.

    On first run (no snapshot yet) the current artifact is saved as the golden
    baseline and the command exits 0.  On subsequent runs the diff is reported
    and the command exits 1 when breaking changes are found (unless
    --no-fail-on-breaking is set).

    Use --update to refresh the golden baseline intentionally.
    """
    try:
        from sdd_compiler.ast import GovernanceAST
    except ImportError:
        typer.echo(
            "ERROR: sdd_compiler is not installed. Run 'sdd setup run'.",
            err=True,
        )
        raise typer.Exit(1) from None

    root = detect_repo_root()
    golden_path = golden or _resolve_golden_path(root)
    artifact_path = artifact or _find_artifact(root)

    if artifact_path is None:
        typer.echo(
            "ERROR: No compiled artifact found. Run 'sdd governance compile' first.",
            err=True,
        )
        typer.echo("  Next: run 'sdd governance compile' to build artifacts", err=True)
        raise typer.Exit(1)

    try:
        current_ast = GovernanceAST.from_compiled_json(artifact_path)
    except Exception as exc:
        typer.echo(f"ERROR: Failed to load artifact: {exc}", err=True)
        raise typer.Exit(1) from exc

    # --update: overwrite golden and exit
    if update:
        _save_golden(golden_path, current_ast)
        return

    # First run: initialise golden
    if not golden_path.exists():
        _save_golden(golden_path, current_ast)
        typer.echo(f"Golden baseline initialised: {golden_path} (status: new)")
        return

    # Load golden and diff
    golden_ast = _load_golden_ast(golden_path)
    diff = golden_ast.diff(current_ast)

    typer.echo(
        f"Comparing artifact ({artifact_path.name}) against golden ({golden_path.name}):"
    )
    typer.echo(f"  Summary: {diff.summary()}")

    if diff.is_clean:
        typer.echo("  Status: CLEAN — no changes detected.")
        return

    _print_diff(diff)

    if diff.has_breaking_changes and fail_on_breaking:
        typer.echo(
            "\n  Next: review breaking changes above, then run 'sdd test review-golden --update' to accept",
            err=True,
        )
        raise typer.Exit(1)
