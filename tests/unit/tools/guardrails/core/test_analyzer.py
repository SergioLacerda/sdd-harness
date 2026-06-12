"""Unit tests for tools.guardrails.core.analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.guardrails.core.analyzer import GuardrailAnalyzer
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.dimension import AnalysisDimension
from tools.guardrails.core.metrics import (
    AnalysisResult,
    DimensionResult,
    FileMetrics,
    compute_base_metrics,
)
from tools.guardrails.reporters.template import ReportTemplate

pytestmark = pytest.mark.unit


def _scoring_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    findings = ["too long"] if metrics.lines > 5 else []
    score = 50.0 if findings else 100.0
    return DimensionResult(name="refactoring", findings=findings, score=score)


def _reporter(result: DimensionResult, template: ReportTemplate) -> str:
    return template.section(result.name, template.bullet_list(result.findings))


class _StubAnalyzer(GuardrailAnalyzer):
    """Minimal concrete analyzer used for testing the pipeline."""

    def __init__(
        self, target_dir: Path, config: AnalysisConfig, output_dir: Path
    ) -> None:
        self._target_dir = target_dir
        self.reports_generated = False
        super().__init__(config, output_dir)

    def get_target_directory(self) -> Path:
        return self._target_dir

    def get_analysis_name(self) -> str:
        return "stub_analyzer"

    def get_dimensions(self) -> list[AnalysisDimension]:
        return [AnalysisDimension("refactoring", _scoring_detector, _reporter)]

    def create_file_metrics(self, file_path: Path, content: str) -> FileMetrics:
        return compute_base_metrics(file_path, content)

    def _generate_reports(self) -> None:
        self.reports_generated = True


@pytest.fixture
def project(tmp_path: Path) -> Path:
    target = tmp_path / "pkg"
    target.mkdir()
    # Short file -> no findings, score 100
    (target / "short.py").write_text("x = 1\n", encoding="utf-8")
    # Long file -> findings, score 50
    (target / "long.py").write_text("x = 1\n" * 10, encoding="utf-8")
    return target


class TestAnalyzeAll:
    """analyze_all runs the full pipeline end-to-end."""

    def test_populates_files(self, project: Path, tmp_path: Path) -> None:
        analyzer = _StubAnalyzer(project, AnalysisConfig(), tmp_path / "out")

        analyzer.analyze_all()

        assert len(analyzer.files) == 2
        names = {f.name for f in analyzer.files}
        assert names == {"short.py", "long.py"}

    def test_runs_dimensions_on_each_file(self, project: Path, tmp_path: Path) -> None:
        analyzer = _StubAnalyzer(project, AnalysisConfig(), tmp_path / "out")

        analyzer.analyze_all()

        by_name = {f.name: f for f in analyzer.files}
        assert by_name["short.py"].dimension_results["refactoring"].score == 100.0
        assert by_name["long.py"].dimension_results["refactoring"].score == 50.0
        assert by_name["long.py"].dimension_results["refactoring"].findings == [
            "too long"
        ]

    def test_aggregates_summary(self, project: Path, tmp_path: Path) -> None:
        analyzer = _StubAnalyzer(project, AnalysisConfig(), tmp_path / "out")

        result = analyzer.analyze_all()

        assert result.summary["total_files"] == 2
        refactoring_summary = result.summary["refactoring"]
        assert refactoring_summary["avg_score"] == 75.0
        assert refactoring_summary["files_with_issues"] == 1
        assert refactoring_summary["total_findings"] == 1

    def test_calls_generate_reports(self, project: Path, tmp_path: Path) -> None:
        analyzer = _StubAnalyzer(project, AnalysisConfig(), tmp_path / "out")

        analyzer.analyze_all()

        assert analyzer.reports_generated is True

    def test_returns_analysis_result(self, project: Path, tmp_path: Path) -> None:
        analyzer = _StubAnalyzer(project, AnalysisConfig(), tmp_path / "out")

        result = analyzer.analyze_all()

        assert isinstance(result, AnalysisResult)
        assert result.analyzer_name == "stub_analyzer"
        assert result is analyzer.results

    def test_empty_directory(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        analyzer = _StubAnalyzer(empty, AnalysisConfig(), tmp_path / "out")

        result = analyzer.analyze_all()

        assert result.files == []
        assert result.summary == {"total_files": 0}


class TestDefaultOutputDir:
    """_default_output_dir follows the .analysis/pending/<name>/ convention."""

    def test_default_output_dir(self, project: Path) -> None:
        analyzer = _StubAnalyzer(project, AnalysisConfig(), output_dir=None)  # type: ignore[arg-type]
        assert analyzer.output_dir == Path(".analysis/pending/stub_analyzer")
