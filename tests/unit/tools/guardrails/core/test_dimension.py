"""Unit tests for tools.guardrails.core.dimension."""

from __future__ import annotations

import pytest

from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.dimension import AnalysisDimension
from tools.guardrails.core.metrics import DimensionResult, FileMetrics
from tools.guardrails.reporters.template import ReportTemplate

pytestmark = pytest.mark.unit


def _detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    findings = ["too long"] if metrics.lines > config.refactoring.max_file_lines else []
    return DimensionResult(name="refactoring", findings=findings, score=80.0)


def _reporter(result: DimensionResult, template: ReportTemplate) -> str:
    return template.section(result.name, template.bullet_list(result.findings))


class TestAnalysisDimension:
    """detect/report delegate to the provided callables."""

    def test_detect_delegates_to_detector(self) -> None:
        dimension = AnalysisDimension("refactoring", _detector, _reporter)
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=250, classes=0, functions=1, imports=0
        )

        result = dimension.detect(metrics, "content", AnalysisConfig())

        assert result.name == "refactoring"
        assert result.findings == ["too long"]
        assert result.score == 80.0

    def test_report_delegates_to_reporter(self) -> None:
        dimension = AnalysisDimension("refactoring", _detector, _reporter)
        result = DimensionResult(name="refactoring", findings=["too long"], score=80.0)

        rendered = dimension.report(result, ReportTemplate())

        assert rendered == "## refactoring\n\n- too long"

    def test_defaults(self) -> None:
        dimension = AnalysisDimension("refactoring", _detector, _reporter)
        assert dimension.description == ""
        assert dimension.icon == "\U0001f4ca"
