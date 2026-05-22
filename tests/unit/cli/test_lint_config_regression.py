from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_toml(path: Path) -> dict:
    try:
        import tomllib  # py311+
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[import-not-found]
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_ruff_f401_rule_remains_enabled() -> None:
    cfg = _load_toml(Path("pyproject.toml"))
    lint_cfg = cfg["tool"]["ruff"]["lint"]
    selected = set(lint_cfg.get("select", []))
    ignored = set(lint_cfg.get("ignore", []))

    assert "F" in selected
    assert "F401" not in ignored


def test_mccabe_max_complexity_is_guarded() -> None:
    cfg = _load_toml(Path("pyproject.toml"))
    complexity = cfg["tool"]["ruff"]["lint"]["mccabe"]["max-complexity"]
    assert isinstance(complexity, int)
    assert complexity <= 10
