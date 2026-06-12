"""Core metrics dataclasses shared across all guardrail analyzers."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DimensionResult:
    """Result of running one analysis dimension on one file."""

    name: str
    findings: list[str] = field(default_factory=list)
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileMetrics:
    """Base file metrics shared by all analyzers.

    Subclasses (or `custom_metrics`) hold analyzer-specific fields.
    """

    name: str
    path: str
    lines: int
    classes: int
    functions: int
    imports: int
    has_issues: bool = False
    dimension_results: dict[str, DimensionResult] = field(default_factory=dict)
    custom_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Aggregated result of an `analyze_all()` run."""

    analyzer_name: str
    timestamp: str
    files: list[FileMetrics] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def compute_base_metrics(path: Path, content: str) -> FileMetrics:
    """Compute the shared AST-derived base metrics for a Python file."""
    tree = ast.parse(content)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]
    return FileMetrics(
        name=path.name,
        path=str(path),
        lines=len(content.splitlines()),
        classes=len(classes),
        functions=len(functions),
        imports=len(imports),
    )
