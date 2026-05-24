from __future__ import annotations

from pathlib import Path

from tools.ci.check_enforcement_ladder_consistency import _contains


def test_contains_false_when_file_missing(tmp_path: Path) -> None:
    assert _contains(tmp_path / "missing.txt", "abc") is False


def test_contains_true_when_pattern_exists(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("hello strict world", encoding="utf-8")
    assert _contains(p, "strict") is True
