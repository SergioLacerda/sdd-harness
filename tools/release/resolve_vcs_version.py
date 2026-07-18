#!/usr/bin/env python3
"""Resolve the release version from the exact Git tag on HEAD."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from sdd_core.utils.process import SafeProcessRunner

_SEMVER_TAG_RE = re.compile(r"^[vV]?(?P<version>\d+\.\d+\.\d+)$")


def normalize_version(value: str) -> str:
    """Return the plain semver version from a version or Git tag string."""
    match = _SEMVER_TAG_RE.match(value)
    if match is None:
        print(f"ERROR: Invalid version/tag '{value}' (expected [v|V]X.Y.Z)")
        sys.exit(1)
    return match.group("version")


def resolve_head_tag(repo_root: Path, *, runner: Any | None = None) -> str:
    """Return the exact Git tag attached to HEAD."""
    process_runner = runner or SafeProcessRunner()
    result = process_runner.run(
        ["git", "describe", "--tags", "--exact-match", "HEAD"],
        cwd=repo_root,
        capture_output=True,
    )
    if result.returncode != 0:
        print("ERROR: HEAD is not exactly on a release tag", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    print(normalize_version(resolve_head_tag(repo_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
