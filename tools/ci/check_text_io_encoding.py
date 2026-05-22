from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROOTS = ("tests", "packages", "tools")
EXCLUDED_PARTS = ("/build/lib/",)

_INGESTION_PATTERNS = ("loader", "reader", "parser", "ingest")


def _is_excluded(path: Path) -> bool:
    as_posix = path.as_posix()
    return any(part in as_posix for part in EXCLUDED_PARTS)


def _is_ingestion_file(path: Path) -> bool:
    name = path.stem.lower()
    return any(pat in name for pat in _INGESTION_PATTERNS)


def _has_encoding_kw(call: ast.Call) -> bool:
    return any(
        isinstance(k, ast.keyword) and k.arg == "encoding" for k in call.keywords
    )


def _has_errors_kw(call: ast.Call) -> bool:
    return any(isinstance(k, ast.keyword) and k.arg == "errors" for k in call.keywords)


def _is_text_open_without_encoding(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Name) or call.func.id != "open":
        return False
    if _has_encoding_kw(call):
        return False

    # Default open() mode is text ("r"), so it requires explicit encoding.
    if len(call.args) < 2:
        return True

    mode_arg = call.args[1]
    if not isinstance(mode_arg, ast.Constant) or not isinstance(mode_arg.value, str):
        # Non-literal mode: enforce explicit encoding to be safe/deterministic.
        return True

    mode = mode_arg.value
    # Binary mode is exempt from text encoding policy.
    return "b" not in mode


def _is_text_open_missing_errors(call: ast.Call) -> bool:
    """Return True for text open() with encoding= but without errors= (ingestion files only)."""
    if not isinstance(call.func, ast.Name) or call.func.id != "open":
        return False
    if not _has_encoding_kw(call):
        return False
    if _has_errors_kw(call):
        return False

    # Check it is text mode (not binary).
    if len(call.args) < 2:
        return True  # default mode is "r" (text)

    mode_arg = call.args[1]
    if not isinstance(mode_arg, ast.Constant) or not isinstance(mode_arg.value, str):
        return True  # non-literal mode: be conservative

    return "b" not in mode_arg.value


def _iter_files(repo_root: Path, paths: list[str] | None) -> list[Path]:
    if paths:
        files: list[Path] = []
        for rel in paths:
            path = (repo_root / rel).resolve()
            if (
                path.exists()
                and path.suffix == ".py"
                and path.is_file()
                and not _is_excluded(path)
            ):
                files.append(path)
        return files

    files = []
    for root_name in ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        files.extend(
            py_file for py_file in root.rglob("*.py") if not _is_excluded(py_file)
        )
    return files


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check text I/O calls enforce explicit UTF-8 encoding."
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Optional repository-relative Python file paths to check.",
    )
    return parser.parse_args()


def main() -> int:  # noqa: C901
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[tuple[str, str]] = []

    for py_file in _iter_files(repo_root, args.paths):
        source = py_file.read_text(encoding="utf-8")
        is_ingestion = _is_ingestion_file(py_file)
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            violations.append((f"{py_file}: syntax-error while scanning ({exc})", ""))
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if _is_text_open_without_encoding(node):
                violations.append(
                    (
                        f"{py_file}:{node.lineno}: open() in text mode without encoding",
                        'Fix: open(path, encoding="utf-8")  or  read_text_utf8(path)',
                    )
                )
                continue

            if is_ingestion and _is_text_open_missing_errors(node):
                violations.append(
                    (
                        f"{py_file}:{node.lineno}: open() in ingestion file without errors=",
                        "Fix: add errors='strict' or errors='replace' to make decode behavior explicit",
                    )
                )
                continue

            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"read_text", "write_text"}:
                continue
            if _has_encoding_kw(node):
                continue
            violations.append(
                (
                    f"{py_file}:{node.lineno}: {node.func.attr} without encoding",
                    "Fix: use read_text_utf8(path) / write_text_utf8(path, content) from the central helper",
                )
            )

    if violations:
        print("Text I/O encoding policy failed. Found calls without explicit encoding:")
        for msg, hint in violations:
            print(f"  - {msg}")
            if hint:
                print(f"    {hint}")
        return 1

    print("Text I/O encoding policy passed: all text I/O calls set explicit encoding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
