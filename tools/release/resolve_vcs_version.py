#!/usr/bin/env python3
"""Resolve the release version from the exact Git tag on HEAD."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from sdd_core.utils.process import SafeProcessRunner

try:
    from tools.release.sync_versions import normalize_version
except ModuleNotFoundError:  # pragma: no cover - script execution path
    from sync_versions import normalize_version


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
