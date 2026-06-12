"""Test."""

import sys
from pathlib import Path

import typer

from sdd_cli.services.test_handler import (
    _check_import,
    _run_cli,
    _run_pytest,
    _run_script,
    run_review_golden,
)
from sdd_cli.utils.dev_deps import require_dev_module
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
        require_dev_module("pytest")
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
    cov_fail_under: int | None = typer.Option(  # noqa: UP045
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
        require_dev_module("pytest")
        typer.echo("\n=== Test suite ===")
        script = root / "tools" / "testing" / "run-all-tests.py"
        if not script.exists():
            typer.echo(f"  FAIL: not found at {script}")
            failed = True
        else:
            if _run_script(str(script), [], str(root)) != 0:
                failed = True

    if soak_threads:
        require_dev_module("pytest")
        typer.echo("\n=== Thread soak ===")
        soak_args = [
            "packages/interfaces/sdd_cli/tests/test_metrics_reload_worker.py",
            "-k",
            "soak_restart_cycles",
        ]
        if _run_pytest(soak_args, str(root)) != 0:
            failed = True

    if failed:
        typer.echo("\nERROR: One or more checks failed")
        raise typer.Exit(1)

    typer.echo("\nAll checks passed")


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
    run_review_golden(
        root=detect_repo_root(),
        update=update,
        fail_on_breaking=fail_on_breaking,
        artifact=artifact,
        golden=golden,
    )
