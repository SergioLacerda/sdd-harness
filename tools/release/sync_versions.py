#!/usr/bin/env python3
"""
Synchronize workspace package versions to match a release tag.

This script updates every uv workspace member pyproject.toml file to have the
same version as the release tag, ensuring consistency across the monorepo.

Usage:
    python tools/release/sync_versions.py <version-or-tag>

Example:
    python tools/release/sync_versions.py 0.2.0
    python tools/release/sync_versions.py v0.2.0
    python tools/release/sync_versions.py V0.2.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[import-not-found]


SEMVER_TAG_RE = re.compile(r"^[vV]?(?P<version>\d+\.\d+\.\d+)$")


def normalize_version(value: str) -> str:
    """Return the plain semver version from a version or Git tag string."""
    match = SEMVER_TAG_RE.match(value)
    if match is None:
        print(f"ERROR: Invalid version/tag '{value}' (expected [v|V]X.Y.Z)")
        sys.exit(1)
    return match.group("version")


def discover_workspace_packages(workspace_root: Path) -> list[str]:
    """Read uv workspace members from the root pyproject.toml."""
    pyproject = workspace_root / "pyproject.toml"
    if not pyproject.exists():
        print(f"ERROR: {pyproject} not found")
        sys.exit(1)

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    members = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members")
    if not isinstance(members, list) or not members:
        print("ERROR: [tool.uv.workspace].members is missing or empty")
        sys.exit(1)

    return [str(member) for member in members]


def sync_version(version_or_tag: str, *, workspace_root: Path | None = None) -> None:
    """
    Update all workspace package versions to match the provided version or tag.

    Args:
        version_or_tag: Version or Git tag string (e.g., "0.2.0" or "v0.2.0")
        workspace_root: Repository root. Defaults to the current script's repo.

    Raises:
        SystemExit: If any package update fails
    """
    version = normalize_version(version_or_tag)
    workspace_root = workspace_root or Path(__file__).parent.parent.parent
    workspace_members = discover_workspace_packages(workspace_root)

    updated = []
    failed = []

    for pkg_path in workspace_members:
        full_path = workspace_root / pkg_path
        pyproject = full_path / "pyproject.toml"

        if not pyproject.exists():
            failed.append(f"{pkg_path}: pyproject.toml not found")
            continue

        try:
            # Read the file
            content = pyproject.read_text(encoding="utf-8")

            # Matches: version = "..." (with optional whitespace)
            version_line_re = re.compile(r'^version\s*=\s*"([^"]*)"', re.MULTILINE)
            match = version_line_re.search(content)
            if match is None:
                failed.append(f"{pkg_path}: no version line found")
                continue

            if match.group(1) == version:
                # Already at the target version: nothing to write, not a failure.
                updated.append(pkg_path)
                print(f"✓ {pkg_path} already at {version}")
                continue

            new_content = version_line_re.sub(
                f'version = "{version}"', content, count=1
            )

            # Write back
            pyproject.write_text(new_content, encoding="utf-8")
            updated.append(pkg_path)
            print(f"✓ Updated {pkg_path} → {version}")

        except Exception as e:
            failed.append(f"{pkg_path}: {str(e)}")

    # Summary
    print()
    print("=" * 60)
    if updated:
        print(f"✓ Successfully updated {len(updated)} package(s)")
    if failed:
        print(f"✗ Failed to update {len(failed)} package(s):")
        for msg in failed:
            print(f"  - {msg}")
        sys.exit(1)

    print(f"✓ All packages synchronized to version {version}")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_versions.py <version-or-tag>")
        print("Example: python sync_versions.py v0.2.0")
        sys.exit(1)

    sync_version(sys.argv[1])
