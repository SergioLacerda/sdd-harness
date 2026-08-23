#!/usr/bin/env python3
"""Run Python mutation testing (mutmut) against a critical module.

`mutmut` (3.7.0) only recognizes `.`/`src`/`source` as the source-root
convention for both its `sys.path` injection and its mutant-identity key
computation (`path.relative_to(Path(".").absolute())` — relative to the real
CWD at run time, not to its own `source_paths` config). This repo's
`packages/<name>/src/<name>` layout only works if `mutmut` is invoked with
CWD set to the target package's own `src/` directory.

That, in turn, needs the package's `src/` to reach the repo-root `tests/` and
`docs/` directories (for shared test helpers and the governance-compile
bootstrap other tests need) — `mutmut`'s `also_copy` mechanism only copies
paths that are forward-relative to CWD, so this script creates temporary
symlinks for the duration of the run and always removes them afterward
(this repo bans tracked git symlinks — see
`tests/unit/ci/test_repo_portability.py` — so these must never be committed).

Usage:
    make mutation-python                                  # run all registered targets
    uv run python tools/testing/run_mutation_python.py     # same, direct invocation
    uv run python tools/testing/run_mutation_python.py --target sdd_runtime_gate_evaluation
"""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pinned to match the version validated in this repo (no @latest — see the
# no-floating-tool-versions policy already applied to govulncheck).
_MUTMUT_VERSION = "3.7.0"


@dataclass(frozen=True)
class MutationTarget:
    """One package + file scoped for mutation testing.

    `package_dir` is repo-root-relative (e.g. "packages/core/sdd_runtime").
    `only_mutate` entries are relative to that package's own `src/`.
    `ignore_test_files` lists repo-root-relative test files to exclude from
    this run — reserve this for files that genuinely misbehave under
    mutmut's multi-phase re-invocation (e.g. real `@given`/Hypothesis
    property tests), not as a blanket exclusion. Excluding a file that
    happens to be the *only* coverage for the mutated code silently produces
    a false "no test covers this mutant" result — verify with
    `grep -n "@given\\|^from hypothesis"` before adding an entry here.
    """

    name: str
    package_dir: str
    only_mutate: list[str]
    ignore_test_files: list[str] = field(default_factory=list)
    extra_deselect: list[str] = field(default_factory=list)


TARGETS: dict[str, MutationTarget] = {
    "sdd_runtime_gate_evaluation": MutationTarget(
        name="sdd_runtime_gate_evaluation",
        package_dir="packages/core/sdd_runtime",
        only_mutate=["sdd_runtime/_skill_executor/_gate_rules/_evaluation.py"],
        ignore_test_files=["test_properties.py"],
        extra_deselect=[
            "test_skills_runtime_does_not_fallback_to_subprocess_run",
        ],
    ),
}


def _run(cmd: list[str], *, cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}  (cwd={cwd})")
    result = subprocess.run(cmd, cwd=cwd)  # nosec B603 — fixed argv, no shell
    return result.returncode


def _write_mutmut_config(src_dir: Path, target: MutationTarget) -> Path:
    config_path = src_dir / "pyproject.toml"
    if config_path.exists():
        raise FileExistsError(
            f"{config_path} already exists — refusing to overwrite. "
            "Remove it manually if a previous run left it behind."
        )
    test_selection = "../../tests"
    deselect_expr = " and ".join(f"not {name}" for name in target.extra_deselect)
    lines = [
        "[tool.mutmut]",
        'source_paths = ["."]',
        f"only_mutate = {target.only_mutate!r}",
        f'pytest_add_cli_args_test_selection = ["{test_selection}"]',
    ]
    args_list = []
    if deselect_expr:
        args_list += ["-k", deselect_expr]
    for ignored in target.ignore_test_files:
        args_list.append(f"--ignore=../../tests/{ignored}")
    if args_list:
        lines.append(f"pytest_add_cli_args = {args_list!r}")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def run_target(target: MutationTarget) -> int:
    package_dir = REPO_ROOT / target.package_dir
    src_dir = package_dir / "src"
    if not src_dir.is_dir():
        print(f"ERROR: {src_dir} is not a directory", file=sys.stderr)
        return 1

    tests_link = src_dir / "tests"
    docs_link = src_dir / "docs"
    config_path: Path | None = None
    mutants_dir = src_dir / "mutants"

    try:
        if tests_link.exists() or tests_link.is_symlink():
            raise FileExistsError(f"{tests_link} already exists — aborting")
        if docs_link.exists() or docs_link.is_symlink():
            raise FileExistsError(f"{docs_link} already exists — aborting")

        tests_link.symlink_to(REPO_ROOT / "tests")
        docs_link.symlink_to(REPO_ROOT / "docs")
        config_path = _write_mutmut_config(src_dir, target)

        return _run(
            [
                "uv",
                "run",
                "--project",
                str(REPO_ROOT),
                "mutmut",
                "run",
            ],
            cwd=src_dir,
        )
    finally:
        for link in (tests_link, docs_link):
            if link.is_symlink():
                link.unlink()
        if config_path is not None and config_path.exists():
            config_path.unlink()
        if mutants_dir.exists():
            shutil.rmtree(mutants_dir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=sorted(TARGETS),
        help="Run only this target (default: run all registered targets).",
    )
    args = parser.parse_args(argv)

    selected = [TARGETS[args.target]] if args.target else list(TARGETS.values())
    worst_rc = 0
    for target in selected:
        print(f"=== mutation-python: {target.name} ===")
        rc = run_target(target)
        worst_rc = max(worst_rc, rc)
    return worst_rc


if __name__ == "__main__":
    raise SystemExit(main())
