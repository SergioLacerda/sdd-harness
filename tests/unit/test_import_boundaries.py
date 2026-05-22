from __future__ import annotations

from pathlib import Path


def test_production_code_does_not_import_test_helpers() -> None:
    """Keep test-only helpers out of production runtime code."""
    repo_root = Path(__file__).resolve().parents[2]
    package_roots = [
        repo_root / "packages" / "core",
        repo_root / "packages" / "interfaces",
    ]
    violations: list[str] = []

    for package_root in package_roots:
        for src_dir in package_root.rglob("src"):
            for py_file in src_dir.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                if "from tests.helpers" in content or "import tests.helpers" in content:
                    violations.append(str(py_file.relative_to(repo_root)))

    assert not violations, (
        "Production code must not import tests.helpers:\n - " + "\n - ".join(violations)
    )
