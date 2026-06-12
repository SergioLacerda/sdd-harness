"""CLI entry point for the guardrails framework.

Usage:
    uv run python -m tools.guardrails.cli --analyzer runtime
    uv run python -m tools.guardrails.cli --analyzer telemetry
    uv run python -m tools.guardrails.cli --analyzer all
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from tools.guardrails.analyzers.runtime import RuntimeAnalyzer
from tools.guardrails.analyzers.telemetry import TelemetryAnalyzer
from tools.guardrails.core.analyzer import GuardrailAnalyzer
from tools.guardrails.core.config import AnalysisConfig

ANALYZERS: dict[str, Callable[..., GuardrailAnalyzer]] = {
    "runtime": RuntimeAnalyzer,
    "telemetry": TelemetryAnalyzer,
}

DEFAULT_CONFIG_PATH = Path(__file__).parent / "analysis.yaml"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the guardrails CLI."""
    parser = argparse.ArgumentParser(description="Run guardrails analyzers")
    parser.add_argument(
        "--analyzer",
        choices=[*ANALYZERS, "all"],
        default="all",
        help="Which analyzer(s) to run (default: all)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to analysis.yaml config file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory (default: .analysis/pending/<analyzer-name>)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="Override the directory to analyze (default: the analyzer's own package)",
    )
    return parser


def run(
    analyzer_name: str,
    config: AnalysisConfig,
    output_dir: Path | None,
    target_dir: Path | None,
) -> None:
    """Run a single analyzer and print a one-line summary."""
    analyzer_cls = ANALYZERS[analyzer_name]
    analyzer = analyzer_cls(config, output_dir=output_dir, target_dir=target_dir)
    result = analyzer.analyze_all()
    print(
        f"{analyzer_name}: analyzed {result.summary['total_files']} file(s) "
        f"-> {analyzer.output_dir}"
    )


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the selected analyzer(s)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AnalysisConfig.load_yaml(args.config)

    names = list(ANALYZERS) if args.analyzer == "all" else [args.analyzer]
    for name in names:
        output_dir = (
            args.output_dir / name
            if args.output_dir and len(names) > 1
            else args.output_dir
        )
        run(name, config, output_dir, args.target_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
