"""Unit tests for tools.guardrails.core.discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.discovery import discover_files

pytestmark = pytest.mark.unit


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A small project tree with source files, tests, and __pycache__."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("b = 2\n", encoding="utf-8")

    (tmp_path / "pkg" / "tests").mkdir()
    (tmp_path / "pkg" / "tests" / "test_a.py").write_text(
        "def test_a(): ...\n", encoding="utf-8"
    )

    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\x00")

    (tmp_path / "pkg" / "notes.txt").write_text("not python\n", encoding="utf-8")

    return tmp_path


class TestDiscoverFiles:
    """discover_files applies include/exclude patterns and sorts output."""

    def test_includes_only_python_files(self, project: Path) -> None:
        config = AnalysisConfig()
        files = discover_files(project, config)

        assert all(f.suffix == ".py" for f in files)

    def test_excludes_tests_and_pycache(self, project: Path) -> None:
        config = AnalysisConfig()
        files = discover_files(project, config)

        names = {f.name for f in files}
        assert names == {"a.py", "b.py"}

    def test_result_is_sorted_and_deduped(self, project: Path) -> None:
        config = AnalysisConfig()
        files = discover_files(project, config)

        assert files == sorted(files)
        assert len(files) == len(set(files))

    def test_custom_include_patterns(self, project: Path) -> None:
        config = AnalysisConfig(include_patterns=["**/*.txt"], exclude_patterns=[])
        files = discover_files(project, config)

        assert [f.name for f in files] == ["notes.txt"]

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        config = AnalysisConfig()
        assert discover_files(tmp_path, config) == []
