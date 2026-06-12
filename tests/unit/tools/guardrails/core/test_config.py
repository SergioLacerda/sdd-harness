"""Unit tests for tools.guardrails.core.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.guardrails.core.config import (
    AnalysisConfig,
    PerformanceConfig,
    RefactoringConfig,
)

pytestmark = pytest.mark.unit


class TestDefaults:
    """Default thresholds match the approved design."""

    def test_refactoring_defaults(self) -> None:
        config = RefactoringConfig()
        assert config.max_file_lines == 200
        assert config.max_function_lines == 30
        assert config.max_function_parameters == 5

    def test_performance_defaults(self) -> None:
        config = PerformanceConfig()
        assert config.max_nested_loops == 2
        assert config.max_append_operations == 50

    def test_analysis_config_defaults(self) -> None:
        config = AnalysisConfig()
        assert config.include_patterns == ["**/*.py"]
        assert config.exclude_patterns == ["tests/", "venv/", "__pycache__/"]
        assert isinstance(config.refactoring, RefactoringConfig)
        assert isinstance(config.performance, PerformanceConfig)


class TestFromDict:
    """from_dict applies partial overrides and falls back to defaults."""

    def test_partial_override(self) -> None:
        config = AnalysisConfig.from_dict(
            {
                "analysis": {
                    "refactoring": {"max_file_lines": 100},
                    "performance": {"max_nested_loops": 3},
                },
                "file_discovery": {"include_patterns": ["src/**/*.py"]},
            }
        )
        assert config.refactoring.max_file_lines == 100
        assert config.refactoring.max_function_lines == 30  # default kept
        assert config.performance.max_nested_loops == 3
        assert config.include_patterns == ["src/**/*.py"]
        assert config.exclude_patterns == ["tests/", "venv/", "__pycache__/"]

    def test_empty_dict_yields_defaults(self) -> None:
        config = AnalysisConfig.from_dict({})
        assert config == AnalysisConfig()


class TestLoadYaml:
    """load_yaml reads a config file or falls back to defaults."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = AnalysisConfig.load_yaml(tmp_path / "missing.yaml")
        assert config == AnalysisConfig()

    def test_loads_overrides_from_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "analysis.yaml"
        config_file.write_text(
            "analysis:\n"
            "  refactoring:\n"
            "    max_file_lines: 150\n"
            "performance:\n"
            "  max_append_operations: 75\n",
            encoding="utf-8",
        )

        config = AnalysisConfig.load_yaml(config_file)

        assert config.refactoring.max_file_lines == 150
        # top-level "performance" (not under "analysis") is ignored, default kept
        assert config.performance.max_append_operations == 50

    def test_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "analysis.yaml"
        config_file.write_text("", encoding="utf-8")

        config = AnalysisConfig.load_yaml(config_file)

        assert config == AnalysisConfig()
