from __future__ import annotations

import ast
from pathlib import Path

ROOT = "tests"
REQUIRED_MARKER = "encoding_edge"
TARGET_CALL = "read_text_utf8_replace"


def _has_required_marker(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in fn.decorator_list:
        # @pytest.mark.encoding_edge
        if isinstance(dec, ast.Attribute) and dec.attr == REQUIRED_MARKER:
            return True
        if (
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and dec.func.attr == REQUIRED_MARKER
        ):
            return True
    return False


def main() -> int:  # noqa: C901
    repo_root = Path(__file__).resolve().parents[2]
    root = repo_root / ROOT
    violations: list[str] = []

    for py_file in root.rglob("test_*.py"):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            violations.append(f"{py_file}: syntax-error while scanning ({exc})")
            continue

        rel = py_file.relative_to(repo_root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            uses_replace = False
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == TARGET_CALL
                ):
                    uses_replace = True
                    break
            if uses_replace and not _has_required_marker(node):
                violations.append(
                    f"{rel}:{node.lineno}: uses {TARGET_CALL} without @pytest.mark.{REQUIRED_MARKER}"
                )

    if violations:
        print("Encoding edge marker policy failed:")
        for item in violations:
            print(f" - {item}")
        return 1

    print("Encoding edge marker policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
