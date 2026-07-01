#!/usr/bin/env python3
"""
Validate consistent module import style within each Python file.

Reject files that import the same module with both:
    import module
    from module import name

Usage:
    python tools/architecture/validate_import_style.py [--root <path>] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

SCAN_ROOTS = ("packages", "tools", "tests")
SKIP_MARKERS = (
    ".egg",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "generated",
    "site-packages",
)
IGNORED_MODULES = {"__future__"}


@dataclass(frozen=True)
class ImportUse:
    module: str
    lineno: int


@dataclass(frozen=True)
class ImportStyleViolation:
    path: str
    module: str
    import_lines: tuple[int, ...]
    import_from_lines: tuple[int, ...]


def _is_repo_root(path: Path) -> bool:
    return (path / "pyproject.toml").exists()


def _detect_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if _is_repo_root(candidate):
            return candidate
    raise RuntimeError("Could not detect repo root. Use --root.")


def _module_name(file: Path, root: Path) -> str | None:
    try:
        rel = file.relative_to(root / "packages")
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 4 or parts[2] != "src":
        return None
    mod_parts = list(parts[3:])
    if not mod_parts[-1].endswith(".py"):
        return None
    if mod_parts[-1] == "__init__.py":
        mod_parts = mod_parts[:-1]
    else:
        mod_parts = [*mod_parts[:-1], mod_parts[-1][:-3]]
    if not mod_parts:
        return None
    return ".".join(mod_parts)


def _resolve_relative(base_module: str, level: int, imported: str | None) -> str | None:
    base_parts = base_module.split(".")
    if level > len(base_parts):
        return None
    prefix = base_parts[:-level]
    if imported:
        return ".".join([*prefix, *imported.split(".")])
    return ".".join(prefix)


def _import_from_module(node: ast.ImportFrom, current_module: str | None) -> str | None:
    if node.level > 0:
        if current_module is None:
            return None
        return _resolve_relative(current_module, node.level, node.module)
    return node.module


def _collect_import_uses(
    tree: ast.AST, current_module: str | None
) -> tuple[list[ImportUse], list[ImportUse]]:
    import_uses: list[ImportUse] = []
    import_from_uses: list[ImportUse] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in IGNORED_MODULES:
                    import_uses.append(ImportUse(module=alias.name, lineno=node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = _import_from_module(node, current_module)
            if module and module not in IGNORED_MODULES:
                import_from_uses.append(ImportUse(module=module, lineno=node.lineno))

    return import_uses, import_from_uses


def _group_lines(uses: list[ImportUse]) -> dict[str, tuple[int, ...]]:
    grouped: dict[str, set[int]] = {}
    for use in uses:
        grouped.setdefault(use.module, set()).add(use.lineno)
    return {
        module: tuple(sorted(lines))
        for module, lines in sorted(grouped.items(), key=lambda item: item[0])
    }


def _check_file(
    file: Path, root: Path
) -> tuple[list[ImportStyleViolation], str | None]:
    rel = file.relative_to(root).as_posix()
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    except SyntaxError:
        return [], rel

    current_module = _module_name(file, root)
    import_uses, import_from_uses = _collect_import_uses(tree, current_module)
    imports_by_module = _group_lines(import_uses)
    import_froms_by_module = _group_lines(import_from_uses)

    violations: list[ImportStyleViolation] = []
    for module in sorted(set(imports_by_module) & set(import_froms_by_module)):
        violations.append(
            ImportStyleViolation(
                path=rel,
                module=module,
                import_lines=imports_by_module[module],
                import_from_lines=import_froms_by_module[module],
            )
        )
    return violations, None


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.exists():
            continue
        for file in base.rglob("*.py"):
            rel = file.relative_to(root).as_posix()
            if any(marker in rel.split("/") for marker in SKIP_MARKERS):
                continue
            files.append(file)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def validate(root: Path) -> tuple[list[ImportStyleViolation], list[str]]:
    violations: list[ImportStyleViolation] = []
    parse_errors: list[str] = []
    for file in _iter_python_files(root):
        file_violations, parse_error = _check_file(file, root)
        violations.extend(file_violations)
        if parse_error is not None:
            parse_errors.append(parse_error)
    return violations, parse_errors


def _as_payload(
    violations: list[ImportStyleViolation], parse_errors: list[str]
) -> dict[str, object]:
    return {
        "ok": not violations and not parse_errors,
        "violations_count": len(violations),
        "violations": [
            {
                "path": item.path,
                "module": item.module,
                "import_lines": list(item.import_lines),
                "import_from_lines": list(item.import_from_lines),
            }
            for item in violations
        ],
        "parse_errors": parse_errors,
    }


def _print_text_report(
    violations: list[ImportStyleViolation], parse_errors: list[str]
) -> None:
    if violations:
        print(f"ERROR: {len(violations)} mixed import style violation(s) detected:\n")
        for item in violations:
            import_lines = ", ".join(str(line) for line in item.import_lines)
            import_from_lines = ", ".join(str(line) for line in item.import_from_lines)
            print(
                f"  {item.path}: Module is imported with both 'import' and "
                f"'from import': {item.module} "
                f"(import lines: {import_lines}; from-import lines: {import_from_lines})"
            )
        print()
    if parse_errors:
        print(f"ERROR: {len(parse_errors)} file(s) could not be parsed:")
        for path in parse_errors:
            print(f"  - {path}")
        print("\nFix syntax errors before running import style validation.")
    if not violations and not parse_errors:
        print("Import style OK: no mixed import/from-import modules found.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate module import style")
    parser.add_argument("--root", type=Path, default=None, help="Repo root")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        root = _detect_root(args.root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    violations, parse_errors = validate(root)
    if args.json:
        print(json.dumps(_as_payload(violations, parse_errors), indent=2))
    else:
        _print_text_report(violations, parse_errors)
    return 0 if not violations and not parse_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
