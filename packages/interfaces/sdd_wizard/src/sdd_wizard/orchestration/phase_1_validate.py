"""Phase 1 Validate — compiled governance bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sdd_wizard.orchestration.governance_fetcher import (
    fetch_compiled_defaults,
    get_cli_version,
)

_REQUIRED_FILES = ("governance-core.json", "governance-client.json")

_ERROR_MESSAGE = (
    "ERROR: Compiled governance files not found in .sdd/\n\n"
    "Attempted to fetch from GitHub Releases — network unavailable or release not found.\n\n"
    "To fix:\n"
    "  1. Run with network access, or\n"
    "  2. Copy governance-core.json and governance-client.json into .sdd/"
)

_FALLBACK_ADVISORY = (
    "Non-version-pinned fallback: governance files fetched from latest release, "
    "not v{version}. Re-run after version-matched release is published for "
    "deterministic behavior."
)


def phase_1_validate_source(
    repo_root: Path,
    spec_path: Path | None = None,  # noqa: ARG001
) -> tuple[bool, dict[str, Any]]:
    """Phase 1: ensure compiled governance defaults are present in .sdd/.

    For client projects, checks for governance-core.json and governance-client.json.
    If absent, attempts to fetch them from GitHub Releases before failing.
    """
    sdd_dir = repo_root / ".sdd"
    core_path = sdd_dir / "governance-core.json"
    client_path = sdd_dir / "governance-client.json"

    if core_path.exists() and client_path.exists():
        return _build_success_report(source="local", advisory=None)

    cli_version = get_cli_version()
    ok, fetch_source = fetch_compiled_defaults(cli_version, dest=sdd_dir)

    if ok:
        advisory = None
        if fetch_source == "latest_release":
            advisory = _FALLBACK_ADVISORY.format(version=cli_version)
        return _build_success_report(source=fetch_source, advisory=advisory)

    return False, {
        "phase": "PHASE_1_VALIDATE_SOURCE",
        "status": "FAILED",
        "errors": [_ERROR_MESSAGE],
        "checks": {
            "mandate_spec_exists": False,
            "guidelines_dsl_exists": False,
            "mandate_spec_valid": False,
            "guidelines_dsl_valid": False,
        },
        "data": {
            "mandate": {"mandate_count": 0, "fingerprint": None},
            "guidelines": {"guideline_count": 0, "fingerprint": None},
        },
    }


def _build_success_report(
    source: str, advisory: str | None
) -> tuple[bool, dict[str, Any]]:
    report: dict[str, Any] = {
        "phase": "PHASE_1_VALIDATE_SOURCE",
        "status": "SUCCESS",
        "errors": [],
        "checks": {
            "mandate_spec_exists": True,
            "guidelines_dsl_exists": True,
            "mandate_spec_valid": True,
            "guidelines_dsl_valid": True,
        },
        "data": {
            "mandate": {"mandate_count": 0, "fingerprint": None},
            "guidelines": {"guideline_count": 0, "fingerprint": None},
            "source": source,
        },
    }
    if advisory:
        report["advisory"] = advisory
    return True, report
