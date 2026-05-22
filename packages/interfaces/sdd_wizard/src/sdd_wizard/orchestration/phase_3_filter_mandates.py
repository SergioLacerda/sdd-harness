"""Phase 3 Filter Mandates."""

from pathlib import Path
from typing import Any

"""Phase 3: Filter mandates by user selection

This phase takes the compiled mandates loaded in Phase 2 and filters them
based on user selection from the CLI. Users can select specific mandates
using the --mandates flag.
"""


def phase_3_filter_mandates(
    mandates: dict[str, Any],
    selected_mandate_ids: list[str] | None = None,
    repo_root: Path | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Filter compiled mandates to only selected ones

    Args:
        mandates: Dictionary of all mandates from Phase 2
        selected_mandate_ids: List of mandate IDs to include (e.g., ['M001', 'M002'])
        repo_root: Repository root (for logging context)

    Returns:
        (success: bool, report: Dict)
        report contains:
            - phase: 'PHASE_3_FILTER_MANDATES'
            - status: 'SUCCESS' | 'WARNING' | 'FAILED'
            - checks: dict of validation checks performed
            - data: dict with filtered_mandates
            - statistics: count of selected vs total
            - errors: list of error messages
            - warnings: list of warning messages
    """

    report: dict[str, Any] = {
        "phase": "PHASE_3_FILTER_MANDATES",
        "status": "PENDING",
        "checks": {
            "mandates_provided": False,
            "valid_selection": False,
            "filtering_applied": False,
        },
        "data": {
            "filtered_mandates": {},
            "selected_ids": selected_mandate_ids or [],
        },
        "statistics": {
            "total_mandates": len(mandates),
            "selected_mandates": 0,
            "filtered_percentage": 0.0,
        },
        "errors": [],
        "warnings": [],
    }

    # Step 1: Check input
    if not mandates:
        report["errors"].append("No mandates provided from Phase 2")
        report["status"] = "FAILED"
        return (False, report)

    report["checks"]["mandates_provided"] = True

    # Step 2: Determine selection strategy
    # If no selection specified, include all mandates
    if not selected_mandate_ids:
        selected_mandate_ids = list(mandates.keys())
        report["data"]["selected_ids"] = selected_mandate_ids
        report["warnings"].append(
            f"No mandate selection specified, using all {len(selected_mandate_ids)} mandates"
        )

    # Step 3: Validate selected IDs exist
    all_mandate_ids = set(mandates.keys())
    selected_ids_set = set(selected_mandate_ids)
    invalid_ids = selected_ids_set - all_mandate_ids

    if invalid_ids:
        report["errors"].append(f"Invalid mandate IDs: {list(invalid_ids)}")
        report["errors"].append(f"Valid IDs are: {sorted(all_mandate_ids)}")
        report["status"] = "FAILED"
        return (False, report)

    report["checks"]["valid_selection"] = True

    # Step 4: Apply filtering
    filtered_mandates = {}
    for mandate_id in selected_mandate_ids:
        if mandate_id in mandates:
            filtered_mandates[mandate_id] = mandates[mandate_id]

    report["checks"]["filtering_applied"] = True
    report["data"]["filtered_mandates"] = filtered_mandates
    report["statistics"]["selected_mandates"] = len(filtered_mandates)

    # Calculate percentage
    if report["statistics"]["total_mandates"] > 0:
        percentage = (
            len(filtered_mandates) / report["statistics"]["total_mandates"]
        ) * 100
        report["statistics"]["filtered_percentage"] = round(percentage, 1)

    # Step 5: Validate result
    if not filtered_mandates:
        report["errors"].append("Filtering resulted in zero mandates")
        report["status"] = "FAILED"
        return (False, report)

    # Success
    report["status"] = "SUCCESS"

    return (True, report)
