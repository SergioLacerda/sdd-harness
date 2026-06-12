"""Configuration dataclasses for the guardrails framework.

All configurable thresholds live here, loadable from a YAML file
(`analysis.yaml`) with sensible defaults when the file is absent or empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RefactoringConfig:
    """Thresholds for the refactoring dimension."""

    max_file_lines: int = 200
    max_function_lines: int = 30
    max_function_parameters: int = 5

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RefactoringConfig:
        """Build from a (possibly partial) dict, falling back to defaults."""
        defaults = cls()
        return cls(
            max_file_lines=data.get("max_file_lines", defaults.max_file_lines),
            max_function_lines=data.get(
                "max_function_lines", defaults.max_function_lines
            ),
            max_function_parameters=data.get(
                "max_function_parameters", defaults.max_function_parameters
            ),
        )


@dataclass
class PerformanceConfig:
    """Thresholds for the performance dimension."""

    max_nested_loops: int = 2
    max_append_operations: int = 50

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerformanceConfig:
        """Build from a (possibly partial) dict, falling back to defaults."""
        defaults = cls()
        return cls(
            max_nested_loops=data.get("max_nested_loops", defaults.max_nested_loops),
            max_append_operations=data.get(
                "max_append_operations", defaults.max_append_operations
            ),
        )


@dataclass
class AnalysisConfig:
    """All configurable thresholds and file-discovery patterns."""

    refactoring: RefactoringConfig = field(default_factory=RefactoringConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    include_patterns: list[str] = field(default_factory=lambda: ["**/*.py"])
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["tests/", "venv/", "__pycache__/"]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisConfig:
        """Build from a parsed YAML dict, falling back to defaults."""
        defaults = cls()
        analysis = data.get("analysis", {}) or {}
        discovery = data.get("file_discovery", {}) or {}
        return cls(
            refactoring=RefactoringConfig.from_dict(
                analysis.get("refactoring", {}) or {}
            ),
            performance=PerformanceConfig.from_dict(
                analysis.get("performance", {}) or {}
            ),
            include_patterns=discovery.get(
                "include_patterns", defaults.include_patterns
            ),
            exclude_patterns=discovery.get(
                "exclude_patterns", defaults.exclude_patterns
            ),
        )

    @staticmethod
    def load_yaml(path: str | Path) -> AnalysisConfig:
        """Load configuration from a YAML file, defaulting if missing/empty."""
        config_path = Path(path)
        if not config_path.exists():
            return AnalysisConfig()
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return AnalysisConfig.from_dict(data)
