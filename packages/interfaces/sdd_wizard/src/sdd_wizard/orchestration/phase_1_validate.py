"""Phase 1 Validate."""

from pathlib import Path
from typing import Any

from sdd_core.governance_orchestrator import GovernanceOrchestrator


def phase_1_validate_source(
    repo_root: Path, spec_path: Path | None = None
) -> tuple[bool, dict[str, Any]]:
    """
    Executes Phase 1: Validating governance source files and building the pipeline.

    Args:
        repo_root: The root path of the repository.
        spec_path: Optional override for the directory containing source specifications.

    Returns:
        A tuple of (success, report_dictionary).
    """
    orchestrator = GovernanceOrchestrator(
        repo_root=str(repo_root), spec_path=str(spec_path) if spec_path else None
    )

    # Run the orchestrator pipeline.
    # We use run_full_pipeline to ensure that artifacts are generated for Phase 2.
    result = orchestrator.run_full_pipeline()

    success = result.get("full_pipeline_success", False)
    p1_data = result.get("phase_1", {})

    report = {
        "phase": "PHASE_1_VALIDATE_SOURCE",
        "status": "SUCCESS" if success else "FAILED",
        "errors": [p1_data.get("error")] if p1_data.get("error") else [],
        "checks": {
            "mandate_spec_exists": success,
            "guidelines_dsl_exists": success,
            "mandate_spec_valid": success,
            "guidelines_dsl_valid": success,
        },
        "data": {
            "mandate": {
                "mandate_count": p1_data.get("core_item_count", 0),
                "fingerprint": p1_data.get("core_fingerprint"),
            },
            "guidelines": {
                "guideline_count": p1_data.get("client_item_count", 0),
                "fingerprint": p1_data.get("client_fingerprint"),
            },
        },
    }

    return success, report
