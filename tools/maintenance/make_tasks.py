#!/usr/bin/env python3
"""Makefile task wrappers with governed process execution."""

from __future__ import annotations

import argparse
import contextlib
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SDD_CORE_SRC = REPO_ROOT / "packages" / "core" / "sdd_core" / "src"
if str(SDD_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(SDD_CORE_SRC))

# Fallback used only if pyproject.toml is missing or has no parseable typer pin.
_FALLBACK_MIN_TYPER_VERSION = (0, 26, 8)


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


def _load_pyproject() -> dict[str, Any] | None:
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        import tomllib  # py311+
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[import-not-found]

    data: dict[str, Any] = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data


def _min_typer_version() -> tuple[int, ...]:
    """Read the minimum typer version from the `typer>=X.Y.Z` pin in pyproject.toml.

    pyproject.toml is the single source of truth for this constraint; keeping a
    second hardcoded copy here risks silently drifting from the real dependency pin.
    """
    data = _load_pyproject()
    if data is None:
        return _FALLBACK_MIN_TYPER_VERSION
    deps = data.get("project", {}).get("dependencies", [])
    for dep in deps:
        if dep.startswith("typer>="):
            return _version_tuple(dep.split(">=", 1)[1])
    return _FALLBACK_MIN_TYPER_VERSION


def _venv_python_path() -> Path:
    candidates = [
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _fail_venv(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    print("Run `make install` to (re)create the project virtualenv.", file=sys.stderr)
    raise SystemExit(1)


def _check_venv() -> Path:
    from sdd_core.utils.process import SafeProcessRunner

    venv_python = _venv_python_path()
    if not venv_python.exists():
        _fail_venv(f".venv not found (expected {venv_python}).")

    probe = Path(__file__).resolve().parent / "_typer_version_probe.py"
    result = SafeProcessRunner().run(
        [str(venv_python), str(probe)], capture_output=True
    )
    if result.returncode != 0:
        _fail_venv("typer is not importable in .venv.")

    installed = result.stdout.strip()
    min_version = _min_typer_version()
    if _version_tuple(installed) < min_version:
        min_str = ".".join(str(p) for p in min_version)
        _fail_venv(f"typer {installed} in .venv is older than required {min_str}.")

    return venv_python


def _python_cmd() -> list[str]:
    return [str(_check_venv())]


def _run(cmd: list[str]) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    result = SafeProcessRunner().run(cmd, cwd=REPO_ROOT, capture_output=False)
    return result.returncode


def _read_project_version() -> str:
    data = _load_pyproject()
    if data is None:
        return "(missing pyproject.toml)"
    return str(data.get("project", {}).get("version", "(dynamic via VCS)"))


def _semver_key(tag: str) -> tuple[int, ...]:
    if tag.startswith("v"):
        tag = tag[1:]
    parts: list[int] = []
    for piece in tag.split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def run_check_venv() -> int:
    """Validate .venv/typer and print the resolved interpreter path.

    Used by git hooks (pre-push, post-merge) so they share the exact same
    guard as the Makefile instead of maintaining their own fallback logic.
    """
    print(str(_check_venv()))
    return 0


def run_check() -> int:
    """Python portion of the `check` target (golden-status stays a Make prerequisite)."""
    rc = _run(_python_cmd() + ["tools/ci/check_golden_policy.py", "--mode", "warn"])
    if rc != 0:
        return rc
    return _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "tests",
            "packages",
            "-m",
            "not perf",
            "--cov=packages",
            "--cov-report=term-missing:skip-covered",
        ]
    )


def run_lint(*, fix: bool) -> int:
    cmd = _python_cmd() + ["tools/maintenance/lint_all.py"]
    if fix:
        cmd.append("--fix")
    return _run(cmd)


def run_test(extra_args: list[str]) -> int:
    return _run(_python_cmd() + ["tools/testing/run-all-tests.py", *extra_args])


def run_test_fast() -> int:
    return _run(_python_cmd() + ["-m", "pytest", "-x", "--ff", "packages/", "tests/"])


def run_test_perf() -> int:
    rc = _run(_python_cmd() + ["-m", "pytest", "-m", "perf", "-q", "packages", "tests"])
    if rc != 0:
        return rc
    return _run(_python_cmd() + ["tests/perf/benchmark_wizard_pipeline.py"])


def run_coverage() -> int:
    rc = _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "tests",
            "packages",
            "--cov=packages",
            "--cov-report=html",
            "--cov-report=term-missing:skip-covered",
        ]
    )
    print("HTML report: build/coverage/html/index.html")
    return rc


def run_coverage_strict() -> int:
    layers = [
        ("core packages", "packages/core", 90),
        ("feature packages", "packages/features", 70),
        ("interface packages", "packages/interfaces", 70),
    ]
    for label, path, threshold in layers:
        print(f"=== {label} (threshold: {threshold}%) ===")
        rc = _run(
            _python_cmd()
            + [
                "-m",
                "pytest",
                path,
                f"--cov={path}",
                f"--cov-fail-under={threshold}",
                "-q",
                "--tb=short",
            ]
        )
        if rc != 0:
            return rc
    return 0


def run_ci_pr() -> int:
    rc = _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "-q",
            "tests/contract/test_governance_schema.py::TestGovernanceCoreGoldenFile::test_structure_matches_golden",
        ]
    )
    if rc != 0:
        return rc
    rc = _run(_python_cmd() + ["tools/ci/check_golden_policy.py", "--mode", "block"])
    if rc != 0:
        return rc
    return _run(
        _python_cmd()
        + ["tools/ci/check_core_compiler_runtime_contract.py", "--mode", "enforce"]
    )


def run_golden_policy_check(*, strict: bool) -> int:
    mode = "strict" if strict else "block"
    return _run(_python_cmd() + ["tools/ci/check_golden_policy.py", "--mode", mode])


def run_enforcement_ladder_consistency() -> int:
    return _run(_python_cmd() + ["tools/ci/check_enforcement_ladder_consistency.py"])


def run_enforcement_ladder_digest() -> int:
    return _run(
        _python_cmd()
        + [
            "tools/ci/enforcement_ladder_digest.py",
            "--json-out",
            ".artifacts/enforcement_ladder_digest.json",
            "--md-out",
            ".artifacts/enforcement_ladder_digest.md",
        ]
    )


def run_enforcement_threshold_signoff() -> int:
    return _run(_python_cmd() + ["tools/ci/check_enforcement_threshold_signoff.py"])


def run_core_compiler_runtime_contract() -> int:
    return _run(
        _python_cmd()
        + ["tools/ci/check_core_compiler_runtime_contract.py", "--mode", "enforce"]
    )


def run_observability_contract_check() -> int:
    return _run(_python_cmd() + ["tools/ci/check_observability_contract.py"])


def run_release_readiness_v1_check() -> int:
    return _run(_python_cmd() + ["tools/ci/check_release_readiness_v1.py"])


def run_runbook_hardening_check() -> int:
    return _run(_python_cmd() + ["tools/ci/check_runbook_hardening_protocol.py"])


def run_update_golden_snapshots() -> int:
    return _run(_python_cmd() + ["tools/testing/update-golden-snapshots.py"])


def run_generate_schemas() -> int:
    return _run(_python_cmd() + ["tools/testing/generate-schemas.py"])


def run_governance_bootstrap() -> int:
    return _run(
        _python_cmd() + ["-m", "sdd_cli", "governance", "generate", "--full-bootstrap"]
    )


def run_docs_link_check() -> int:
    return _run(_python_cmd() + ["tools/docs/check_links.py", "--mode", "ci"])


def run_docs_link_fix() -> int:
    return _run(_python_cmd() + ["tools/docs/check_links.py", "--mode", "fix"])


def run_release_dry_run() -> int:
    print("=== Version check ===")
    print(f"root: {_read_project_version()}")

    print("=== Git tags (semver) ===")
    from sdd_core.utils.process import SafeProcessRunner

    tags_rc = SafeProcessRunner().run(
        ["git", "tag", "--list", "v[0-9]*"], cwd=REPO_ROOT, capture_output=True
    )
    if tags_rc.returncode == 0:
        tags = [t.strip() for t in tags_rc.stdout.splitlines() if t.strip()]
        for tag in sorted(tags, key=_semver_key)[-5:]:
            print(tag)
    else:
        print("(unable to list tags)")

    print("=== CHANGELOG.md present ===")
    if (REPO_ROOT / "CHANGELOG.md").exists():
        print("✓ CHANGELOG.md found")
    else:
        print("✗ CHANGELOG.md missing")

    print("=== README sync check ===")
    for rel in ["README.md"]:
        if (REPO_ROOT / rel).exists():
            print(f"✓ {rel} present")
        else:
            print(f"✗ {rel} missing")

    print("=== Tests pass (no coverage gate) ===")
    return run_test(["--no-coverage"])


def run_clean() -> int:
    for p in REPO_ROOT.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    for p in REPO_ROOT.rglob("*.pyc"):
        with contextlib.suppress(FileNotFoundError):
            p.unlink()
    shutil.rmtree(REPO_ROOT / "build", ignore_errors=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Governed wrappers for Makefile tasks")
    sub = parser.add_subparsers(dest="task", required=True)

    sub.add_parser("check-venv")
    sub.add_parser("check")
    sub.add_parser("lint")
    sub.add_parser("lint-fix")
    test_p = sub.add_parser("test")
    test_p.add_argument("args", nargs="*")
    sub.add_parser("test-fast")
    sub.add_parser("test-perf")
    sub.add_parser("coverage")
    sub.add_parser("coverage-strict")
    sub.add_parser("release-dry-run")
    sub.add_parser("clean")
    sub.add_parser("ci-pr")
    sub.add_parser("golden-policy-check")
    sub.add_parser("golden-policy-check-strict")
    sub.add_parser("enforcement-ladder-consistency")
    sub.add_parser("enforcement-ladder-digest")
    sub.add_parser("enforcement-threshold-signoff")
    sub.add_parser("core-compiler-runtime-contract")
    sub.add_parser("observability-contract-check")
    sub.add_parser("release-readiness-v1-check")
    sub.add_parser("runbook-hardening-check")
    sub.add_parser("update-golden-snapshots")
    sub.add_parser("generate-schemas")
    sub.add_parser("governance-bootstrap")
    sub.add_parser("docs-link-check")
    sub.add_parser("docs-link-fix")

    args = parser.parse_args(argv)
    if args.task == "test":
        return run_test(args.args)

    dispatch: dict[str, Any] = {
        "check-venv": run_check_venv,
        "check": run_check,
        "lint": lambda: run_lint(fix=False),
        "lint-fix": lambda: run_lint(fix=True),
        "test-fast": run_test_fast,
        "test-perf": run_test_perf,
        "coverage": run_coverage,
        "coverage-strict": run_coverage_strict,
        "release-dry-run": run_release_dry_run,
        "clean": run_clean,
        "ci-pr": run_ci_pr,
        "golden-policy-check": lambda: run_golden_policy_check(strict=False),
        "golden-policy-check-strict": lambda: run_golden_policy_check(strict=True),
        "enforcement-ladder-consistency": run_enforcement_ladder_consistency,
        "enforcement-ladder-digest": run_enforcement_ladder_digest,
        "enforcement-threshold-signoff": run_enforcement_threshold_signoff,
        "core-compiler-runtime-contract": run_core_compiler_runtime_contract,
        "observability-contract-check": run_observability_contract_check,
        "release-readiness-v1-check": run_release_readiness_v1_check,
        "runbook-hardening-check": run_runbook_hardening_check,
        "update-golden-snapshots": run_update_golden_snapshots,
        "generate-schemas": run_generate_schemas,
        "governance-bootstrap": run_governance_bootstrap,
        "docs-link-check": run_docs_link_check,
        "docs-link-fix": run_docs_link_fix,
    }
    handler = dispatch.get(args.task)
    return handler() if handler is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
