"""Unit tests for tools.guardrails.core.patterns."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tools.guardrails.core.patterns import Pattern, PatternRegistry, PatternType

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    """Reset the PatternRegistry singleton between tests."""
    PatternRegistry._instance = None
    yield
    PatternRegistry._instance = None


class TestSingleton:
    """PatternRegistry is a global singleton."""

    def test_returns_same_instance(self) -> None:
        assert PatternRegistry() is PatternRegistry()

    def test_state_shared_across_instances(self) -> None:
        first = PatternRegistry()
        first.register(
            "bare_except", Pattern("bare_except", PatternType.REGEX, r"except\s*:")
        )

        second = PatternRegistry()

        assert "bare_except" in second.patterns


class TestPatternMatches:
    """Pattern.matches dispatches on pattern_type."""

    def test_regex_pattern_matches(self) -> None:
        pattern = Pattern("magic_number", PatternType.REGEX, r"\b\d{3,}\b")
        assert pattern.matches("x = 1000") is True
        assert pattern.matches("x = 1") is False

    def test_heuristic_pattern_matches(self) -> None:
        pattern = Pattern(
            "many_appends",
            PatternType.HEURISTIC,
            lambda content: content.count(".append(") > 2,
        )
        assert pattern.matches("a.append(1)\na.append(2)\na.append(3)") is True
        assert pattern.matches("a.append(1)") is False


class TestRegistry:
    """register/find_matches behavior, including group filtering."""

    def test_find_matches_without_group(self) -> None:
        registry = PatternRegistry()
        registry.register(
            "bare_except", Pattern("bare_except", PatternType.REGEX, r"except\s*:")
        )
        registry.register(
            "magic_number", Pattern("magic_number", PatternType.REGEX, r"\b\d{3,}\b")
        )

        matches = registry.find_matches("try:\n    pass\nexcept:\n    pass\nx = 42")

        assert matches == ["bare_except"]

    def test_find_matches_with_group_filters(self) -> None:
        registry = PatternRegistry()
        registry.register(
            "bare_except",
            Pattern("bare_except", PatternType.REGEX, r"except\s*:"),
            group="gaps",
        )
        registry.register(
            "magic_number",
            Pattern("magic_number", PatternType.REGEX, r"\b\d{3,}\b"),
            group="refactoring",
        )

        content = "except:\n    pass\nx = 1000"

        assert registry.find_matches(content, group="gaps") == ["bare_except"]
        assert registry.find_matches(content, group="refactoring") == ["magic_number"]

    def test_unknown_group_falls_back_to_all_patterns(self) -> None:
        registry = PatternRegistry()
        registry.register(
            "bare_except", Pattern("bare_except", PatternType.REGEX, r"except\s*:")
        )

        matches = registry.find_matches("except:\n    pass", group="does_not_exist")

        assert matches == ["bare_except"]
