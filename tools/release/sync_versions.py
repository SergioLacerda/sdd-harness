#!/usr/bin/env python3
"""
Synchronize sub-package versions to match the root version.

This script updates all sub-package pyproject.toml files to have the same
version as the root package, ensuring consistency across the monorepo.

Usage:
    python tools/release/sync_versions.py <version>

Example:
    python tools/release/sync_versions.py 0.2.0
"""

import re
import sys
from pathlib import Path

# Sub-packages to update
SUB_PACKAGES = [
    "packages/core/sdd_core",
    "packages/core/sdd_runtime",
    "packages/core/sdd_compiler",
    "packages/core/sdd_telemetry",
    "packages/features/sdd_integration",
    "packages/interfaces/sdd_wizard",
    "packages/interfaces/sdd_cli",
]


def sync_version(version: str) -> None:
    """
    Update all sub-package versions to match the provided version.

    Args:
        version: Version string (e.g., "0.2.0")

    Raises:
        SystemExit: If any package update fails
    """
    # Validate version format (basic semver check)
    if not re.match(r"^\d+\.\d+\.\d+", version):
        print(f"ERROR: Invalid version format '{version}' (expected: X.Y.Z)")
        sys.exit(1)

    workspace_root = Path(__file__).parent.parent.parent

    updated = []
    failed = []

    for pkg_path in SUB_PACKAGES:
        full_path = workspace_root / pkg_path
        pyproject = full_path / "pyproject.toml"

        if not pyproject.exists():
            failed.append(f"{pkg_path}: pyproject.toml not found")
            continue

        try:
            # Read the file
            content = pyproject.read_text(encoding="utf-8")

            # Replace version line (handles various formats)
            # Matches: version = "..." (with optional whitespace)
            new_content = re.sub(
                r'^version\s*=\s*"[^"]*"',
                f'version = "{version}"',
                content,
                count=1,
                flags=re.MULTILINE,
            )

            if new_content == content:
                failed.append(f"{pkg_path}: no version line found")
                continue

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
        print("Usage: python sync_versions.py <version>")
        print("Example: python sync_versions.py 0.2.0")
        sys.exit(1)

    sync_version(sys.argv[1])
