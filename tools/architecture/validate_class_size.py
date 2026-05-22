#!/usr/bin/env python3
"""
Validate class size guardrail for Python source files.

Usage:
    python tools/architecture/validate_class_size.py [--root <path>] [--max-lines 400] [--show-module-warnings] [--module-warning-lines 400] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, cast

SKIP_MARKERS = ("site-packages", ".venv", "__pycache__", ".egg", "generated", "tests")
ALLOWLIST_FILE = "tools/architecture/class_size_allowlist.json"


def _path_sort_key(path: str) -> tuple[str, ...]:
    """Sort by module/file path segments for deterministic grouping."""
    return tuple(path.split("/"))


def _is_repo_root(path: Path) -> bool:
    return (path / "pyproject.toml").exists() and (path / "packages").exists()


def _detect_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if _is_repo_root(candidate):
            return candidate
    raise RuntimeError("Could not detect repo root. Use --root.")


def _load_allowlist(root: Path) -> dict[str, str]:
    path = root / ALLOWLIST_FILE
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("allowlist", {})
    if not isinstance(entries, dict):
        return {}
    return {str(k).replace("\\", "/"): str(v) for k, v in entries.items()}


def _scan_classes(
    root: Path, max_lines: int, allowlist: dict[str, str]
) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    scanned = 0

    for file in (root / "packages").rglob("*.py"):
        if any(marker in str(file) for marker in SKIP_MARKERS):
            continue
        try:
            src = file.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(file))
        except (UnicodeDecodeError, SyntaxError):
            continue
        rel = file.relative_to(root).as_posix()
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            scanned += 1
            end = getattr(node, "end_lineno", None)
            if end is None:
                continue
            start = node.lineno
            length = end - start + 1
            class_id = f"{rel}:{node.name}"
            if length > max_lines and class_id not in allowlist:
                violations.append(
                    {
                        "class_id": class_id,
                        "path": rel,
                        "class_name": node.name,
                        "start": start,
                        "end": end,
                        "line_count": length,
                    }
                )

    violations.sort(key=lambda x: _path_sort_key(str(x["path"])))
    return {
        "ok": len(violations) == 0,
        "max_lines": max_lines,
        "violations": violations,
        "violations_count": len(violations),
        "classes_scanned": scanned,
        "allowlist_count": len(allowlist),
    }


def _scan_modules(root: Path, warning_lines: int) -> dict[str, object]:
    warnings: list[dict[str, object]] = []
    scanned = 0

    for file in (root / "packages").rglob("*.py"):
        if any(marker in str(file) for marker in SKIP_MARKERS):
            continue
        try:
            src = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        line_count = src.count("\n") + (1 if src else 0)
        if line_count > warning_lines:
            rel = file.relative_to(root).as_posix()
            warnings.append({"path": rel, "line_count": line_count})

    warnings.sort(key=lambda x: _path_sort_key(str(x["path"])))
    return {
        "warning_lines": warning_lines,
        "warnings": warnings,
        "warnings_count": len(warnings),
        "modules_scanned": scanned,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate class size guardrail")
    parser.add_argument("--root", type=Path, default=None, help="Repo root")
    parser.add_argument(
        "--max-lines", type=int, default=400, help="Maximum lines per class"
    )
    parser.add_argument(
        "--module-warning-lines",
        type=int,
        default=400,
        help="Warn when a Python module exceeds this line count (non-blocking)",
    )
    parser.add_argument(
        "--show-module-warnings",
        action="store_true",
        help="Show non-blocking module size warnings in text output",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        root = _detect_root(args.root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    allowlist = _load_allowlist(root)
    report = _scan_classes(root, args.max_lines, allowlist)
    violations = cast(list[dict[str, Any]], report.get("violations", []))
    module_report: dict[str, object] = {}
    module_warnings: list[dict[str, Any]] = []
    if args.show_module_warnings or args.json:
        module_report = _scan_modules(root, args.module_warning_lines)
        module_warnings = cast(list[dict[str, Any]], module_report.get("warnings", []))

    if args.json:
        payload: dict[str, object] = {"class_report": report}
        if module_report:
            payload["module_report"] = module_report
        print(json.dumps(payload, indent=2))
    elif report["ok"]:
        print(
            f"Class size OK: scanned {report['classes_scanned']} classes with max {report['max_lines']} lines."
        )
    else:
        print(
            f"ERROR: {report['violations_count']} class(es) exceed {report['max_lines']} lines (excluding allowlist):\n"
        )
        for item in violations:
            print(
                f"  - {item['class_id']} lines={item['line_count']} ({item['start']}-{item['end']})"
            )
        print(
            f"\nTo allow temporary exceptions, add class ids to {ALLOWLIST_FILE} with a justification."
        )

    if args.show_module_warnings and module_warnings:
        print(
            f"WARNING: {module_report['warnings_count']} module(s) exceed {module_report['warning_lines']} lines (non-blocking):"
        )
        for item in module_warnings[:20]:
            print(f"  - {item['path']} lines={item['line_count']}")
        if len(module_warnings) > 20:
            print(f"  ... +{len(module_warnings) - 20} more")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
