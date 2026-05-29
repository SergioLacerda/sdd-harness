#!/usr/bin/env python3
"""
Verify MkDocs navigation paths — all files referenced in mkdocs.yml must exist.

Also checks that the governance source_root (from pyproject.toml) is mapped in nav.

Usage:
    python tools/verify_mkdocs_paths.py [mkdocs.yml]

Exit codes:
    0  All paths valid
    1  One or more broken paths found
"""

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from yaml import SafeLoader


class _MkDocsLoader(SafeLoader):
    """SafeLoader extended to ignore !!python/name: tags in mkdocs.yml."""


# Treat any !!python/name: tag as a plain string — the tool only reads
# nav and docs_dir, so it never needs the actual Python callables.
_MkDocsLoader.add_multi_constructor(  # type: ignore[no-untyped-call]
    "tag:yaml.org,2002:python/name:",
    lambda loader, tag, node: loader.construct_scalar(node),
)

tomllib: ModuleType | None
try:
    import tomllib as _tomllib  # stdlib on 3.11+

    tomllib = _tomllib
except ImportError:
    try:
        import tomli as _tomllib  # type: ignore[import-not-found]

        tomllib = _tomllib
    except ImportError:
        tomllib = None


def _collect_nav_paths(item: Any, paths: list[str]) -> None:
    """Recursively collect all file path strings from a mkdocs nav structure."""
    if isinstance(item, str):
        # Raw string entries are paths (rare but valid)
        paths.append(item)
    elif isinstance(item, dict):
        for value in item.values():
            if isinstance(value, str):
                paths.append(value)
            elif isinstance(value, list):
                for sub in value:
                    _collect_nav_paths(sub, paths)
    elif isinstance(item, list):
        for sub in item:
            _collect_nav_paths(sub, paths)


def _load_gov_source_root(pyproject_path: Path) -> str:
    """Read sdd.governance.source_root from pyproject.toml, or return ''."""
    if not pyproject_path.is_file():
        return ""
    if tomllib is None:
        print(
            "WARNING: tomli/tomllib not available — skipping pyproject.toml governance check."
        )
        print("  Install: pip install tomli  (Python < 3.11)")
        return ""
    with open(pyproject_path, "rb") as f:
        py_data: dict[str, Any] = tomllib.load(f)
    value = (
        py_data.get("tool", {})
        .get("sdd", {})
        .get("governance", {})
        .get("source_root", "")
    )
    return str(value) if value else ""


def _check_nav_paths(nav: list[Any], docs_dir: Path) -> tuple[list[str], list[str]]:
    """Return (errors, nav_paths) for each nav path that does not exist on disk."""
    nav_paths: list[str] = []
    for entry in nav:
        _collect_nav_paths(entry, nav_paths)

    errors: list[str] = []
    for rel_path in nav_paths:
        if rel_path.startswith(("http://", "https://")):
            continue
        if not (docs_dir / rel_path).exists():
            errors.append(
                f"Missing file: {rel_path}  (expected at {docs_dir / rel_path})"
            )
    return errors, nav_paths


def verify_mkdocs_integrity(config_path: str = "mkdocs.yml") -> int:
    root_dir = Path(__file__).resolve().parent.parent
    mkdocs_path = root_dir / config_path

    gov_source_root = _load_gov_source_root(root_dir / "pyproject.toml")

    if not mkdocs_path.is_file():
        print(f"ERROR: {config_path} not found at {mkdocs_path}")
        return 1

    with open(mkdocs_path, encoding="utf-8") as f:
        config = yaml.load(f, Loader=_MkDocsLoader)  # nosec B506

    docs_dir = root_dir / config.get("docs_dir", "docs")
    errors, nav_paths = _check_nav_paths(config.get("nav", []), docs_dir)

    # ── Check governance source_root is mapped in nav ────────────────────────
    if gov_source_root:
        docs_dir_str = str(docs_dir.relative_to(root_dir)).rstrip("/")
        gov_relative = gov_source_root.removeprefix(docs_dir_str + "/")
        if not any(gov_relative in p or gov_source_root in p for p in nav_paths):
            errors.append(
                f"Governance source_root '{gov_source_root}' (from pyproject.toml) is not mapped in mkdocs.yml nav."
            )

    if errors:
        print(f"ERROR: {len(errors)} broken path(s) in {config_path}:\n")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"OK: All {len(nav_paths)} nav paths in {config_path} are valid.")
    return 0


def main() -> int:
    config = sys.argv[1] if len(sys.argv) > 1 else "mkdocs.yml"
    return verify_mkdocs_integrity(config)


if __name__ == "__main__":
    sys.exit(main())
