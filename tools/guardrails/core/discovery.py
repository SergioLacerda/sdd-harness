"""File discovery for guardrail analyzers."""

from __future__ import annotations

from pathlib import Path

from tools.guardrails.core.config import AnalysisConfig


def discover_files(root: Path, config: AnalysisConfig) -> list[Path]:
    """Discover files under `root` matching `config.include_patterns`.

    Files whose path contains any of `config.exclude_patterns` as a
    substring are skipped. The result is deduplicated and sorted for
    deterministic output.
    """
    discovered: set[Path] = set()
    for include_pattern in config.include_patterns:
        discovered.update(root.glob(include_pattern))

    files = [
        path
        for path in discovered
        if path.is_file()
        and not any(excluded in str(path) for excluded in config.exclude_patterns)
    ]
    return sorted(files)
