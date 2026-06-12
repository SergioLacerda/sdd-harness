"""AnalysisDimension: a named pair of detector/reporter callables."""

from __future__ import annotations

from collections.abc import Callable

from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.metrics import DimensionResult, FileMetrics
from tools.guardrails.reporters.template import ReportTemplate

Detector = Callable[[FileMetrics, str, AnalysisConfig], DimensionResult]
Reporter = Callable[[DimensionResult, ReportTemplate], str]


class AnalysisDimension:
    """One analysis dimension (e.g., refactoring, performance, security)."""

    def __init__(
        self,
        name: str,
        detector: Detector,
        reporter: Reporter,
        description: str = "",
        icon: str = "\U0001f4ca",
    ) -> None:
        self.name = name
        self.detector = detector
        self.reporter = reporter
        self.description = description
        self.icon = icon

    def detect(
        self, metrics: FileMetrics, content: str, config: AnalysisConfig
    ) -> DimensionResult:
        """Run this dimension's detector against a file's metrics/content."""
        return self.detector(metrics, content, config)

    def report(self, result: DimensionResult, template: ReportTemplate) -> str:
        """Render this dimension's result using the given report template."""
        return self.reporter(result, template)
