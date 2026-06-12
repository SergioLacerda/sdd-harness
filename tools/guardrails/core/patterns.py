"""Global pattern registry for detection patterns used by analysis dimensions."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PatternType(Enum):
    """Kind of matcher a Pattern wraps."""

    REGEX = "regex"
    AST = "ast_visitor"
    HEURISTIC = "heuristic"


@dataclass
class Pattern:
    """A single named detection pattern.

    For `PatternType.REGEX`, `matcher` is a regex string matched against
    string content via `re.search`. For `PatternType.AST` and
    `PatternType.HEURISTIC`, `matcher` is a callable taking the content
    (string or AST node) and returning a bool.
    """

    name: str
    pattern_type: PatternType
    matcher: str | Callable[[Any], bool]

    def matches(self, content: Any) -> bool:
        """Return True if this pattern matches the given content."""
        if self.pattern_type is PatternType.REGEX:
            assert isinstance(self.matcher, str)
            return re.search(self.matcher, content) is not None
        assert callable(self.matcher)
        return bool(self.matcher(content))


class PatternRegistry:
    """Global singleton registry for all detection patterns."""

    _instance: PatternRegistry | None = None
    patterns: dict[str, Pattern]
    pattern_groups: dict[str, list[str]]

    def __new__(cls) -> PatternRegistry:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.patterns = {}
            instance.pattern_groups = {}
            cls._instance = instance
        return cls._instance

    def register(self, name: str, pattern: Pattern, group: str | None = None) -> None:
        """Register a new pattern, optionally under a named group."""
        self.patterns[name] = pattern
        if group:
            self.pattern_groups.setdefault(group, []).append(name)

    def find_matches(self, content: Any, group: str | None = None) -> list[str]:
        """Return names of all registered patterns matching `content`."""
        if group is not None and group in self.pattern_groups:
            names = self.pattern_groups[group]
        else:
            names = list(self.patterns)

        return [name for name in names if self.patterns[name].matches(content)]
