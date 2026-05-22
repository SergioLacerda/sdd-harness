#!/usr/bin/env python3
"""Makefile task wrappers with governed process execution."""

from __future__ import annotations

import argparse
import contextlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SDD_CORE_SRC = REPO_ROOT / "packages" / "core" / "sdd_core" / "src"
if str(SDD_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(SDD_CORE_SRC))


def _python_cmd() -> list[str]:
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return [str(venv_python)]
    return [sys.executable]


def _run(cmd: list[str]) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    result = SafeProcessRunner().run(cmd, cwd=REPO_ROOT, capture_output=False)
    return result.returncode


def _read_project_version() -> str:
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return "(missing pyproject.toml)"
    try:
        import tomllib  # py310+
    except ImportError:  # pragma: no cover
        import tomli as tomllib
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
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


def run_lint(*, fix: bool) -> int:
    cmd = _python_cmd() + ["tools/maintenance/lint_all.py"]
    if fix:
        cmd.append("--fix")
    return _run(cmd)


def run_test(extra_args: list[str]) -> int:
    return _run(_python_cmd() + ["tools/testing/run-all-tests.py", *extra_args])


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

    sub.add_parser("lint")
    sub.add_parser("lint-fix")
    test_p = sub.add_parser("test")
    test_p.add_argument("args", nargs="*")
    sub.add_parser("release-dry-run")
    sub.add_parser("clean")

    args = parser.parse_args(argv)
    if args.task == "lint":
        return run_lint(fix=False)
    if args.task == "lint-fix":
        return run_lint(fix=True)
    if args.task == "test":
        return run_test(args.args)
    if args.task == "release-dry-run":
        return run_release_dry_run()
    if args.task == "clean":
        return run_clean()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
