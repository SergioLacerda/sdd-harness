"""Tests for Phase 3: Filter mandates by user selection.

Covers:
- Basic filtering with selected mandate IDs
- No selection specified (use all)
- Invalid mandate IDs error handling
- Empty mandates error handling
- Zero mandates after filtering error
- Report structure validation
- Statistics calculation
"""

from __future__ import annotations

from typing import Any

import pytest

from sdd_wizard.orchestration.phase_3_filter_mandates import phase_3_filter_mandates

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mandate(mandate_id: str, title: str = "Test") -> dict[str, Any]:
    """Create a sample mandate dict."""
    return {
        "id": mandate_id,
        "title": title,
        "description": f"Mandate {mandate_id}",
    }


def _mandates_dict(*ids: str) -> dict[str, Any]:
    """Create a mandates dict from IDs."""
    return {mid: _mandate(mid) for mid in ids}


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Basic Functionality
# ---------------------------------------------------------------------------


class TestPhase3FilterBasic:
    def test_filter_with_selection(self) -> None:
        """Should filter to only selected mandate IDs."""
        mandates = _mandates_dict("M001", "M002", "M003")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001", "M003"]
        )
        assert success is True
        assert report["status"] == "SUCCESS"
        assert report["statistics"]["selected_mandates"] == 2
        assert "M001" in report["data"]["filtered_mandates"]
        assert "M003" in report["data"]["filtered_mandates"]
        assert "M002" not in report["data"]["filtered_mandates"]

    def test_filter_all_mandates(self) -> None:
        """Should include all mandates when none specified."""
        mandates = _mandates_dict("M001", "M002", "M003")
        success, report = phase_3_filter_mandates(mandates, selected_mandate_ids=None)
        assert success is True
        assert report["status"] == "SUCCESS"
        assert report["statistics"]["selected_mandates"] == 3
        assert len(report["data"]["filtered_mandates"]) == 3

    def test_filter_single_mandate(self) -> None:
        """Should filter to single mandate correctly."""
        mandates = _mandates_dict("M001", "M002", "M003")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M002"]
        )
        assert success is True
        assert report["statistics"]["selected_mandates"] == 1
        assert list(report["data"]["filtered_mandates"].keys()) == ["M002"]

    def test_filter_empty_selection_list(self) -> None:
        """Should handle empty selection list by using all."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(mandates, selected_mandate_ids=[])
        assert success is True
        assert report["statistics"]["selected_mandates"] == 2


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Error Handling
# ---------------------------------------------------------------------------


class TestPhase3FilterErrors:
    def test_no_mandates_provided(self) -> None:
        """Should fail when no mandates provided."""
        success, report = phase_3_filter_mandates({}, selected_mandate_ids=["M001"])
        assert success is False
        assert report["status"] == "FAILED"
        assert "No mandates provided" in report["errors"][0]

    def test_invalid_mandate_ids(self) -> None:
        """Should fail with invalid mandate IDs."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001", "M999"]
        )
        assert success is False
        assert report["status"] == "FAILED"
        assert "Invalid mandate IDs" in report["errors"][0]
        assert "M999" in report["errors"][0]

    def test_all_mandates_invalid(self) -> None:
        """Should fail when all selected IDs are invalid."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M999", "M888"]
        )
        assert success is False
        assert report["status"] == "FAILED"

    def test_filtering_results_in_zero_mandates(self) -> None:
        """Should fail when filtering results in zero mandates."""
        # First invalid because M999 doesn't exist
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M999"]
        )
        assert success is False
        # Error is about invalid IDs, not zero result
        assert "Invalid mandate IDs" in report["errors"][0]


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Report Structure
# ---------------------------------------------------------------------------


class TestPhase3FilterReportStructure:
    def test_report_has_required_keys(self) -> None:
        """Report should have all required keys."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert "phase" in report
        assert "status" in report
        assert "checks" in report
        assert "data" in report
        assert "statistics" in report
        assert "errors" in report
        assert "warnings" in report

    def test_phase_name_correct(self) -> None:
        """Phase name should be correct."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert report["phase"] == "PHASE_3_FILTER_MANDATES"

    def test_checks_structure(self) -> None:
        """Checks should have correct structure."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert "mandates_provided" in report["checks"]
        assert "valid_selection" in report["checks"]
        assert "filtering_applied" in report["checks"]

    def test_data_structure(self) -> None:
        """Data should have correct structure."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert "filtered_mandates" in report["data"]
        assert "selected_ids" in report["data"]

    def test_statistics_structure(self) -> None:
        """Statistics should have correct structure."""
        mandates = _mandates_dict("M001", "M002", "M003")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert "total_mandates" in report["statistics"]
        assert "selected_mandates" in report["statistics"]
        assert "filtered_percentage" in report["statistics"]


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Statistics
# ---------------------------------------------------------------------------


class TestPhase3FilterStatistics:
    def test_total_mandates_count(self) -> None:
        """Total mandates should match input."""
        mandates = _mandates_dict("M001", "M002", "M003", "M004")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert report["statistics"]["total_mandates"] == 4

    def test_selected_mandates_count(self) -> None:
        """Selected mandates should be counted correctly."""
        mandates = _mandates_dict("M001", "M002", "M003")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001", "M002"]
        )
        assert report["statistics"]["selected_mandates"] == 2

    def test_filtered_percentage_calculation(self) -> None:
        """Percentage should be calculated correctly."""
        mandates = _mandates_dict("M001", "M002", "M003", "M004")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001", "M002"]
        )
        # 2/4 = 50%
        assert report["statistics"]["filtered_percentage"] == 50.0

    def test_filtered_percentage_rounding(self) -> None:
        """Percentage should be rounded to 1 decimal."""
        # 1/3 = 33.333...%
        mandates = _mandates_dict("M001", "M002", "M003")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert isinstance(report["statistics"]["filtered_percentage"], float)
        assert report["statistics"]["filtered_percentage"] == pytest.approx(
            33.3, abs=0.1
        )

    def test_percentage_with_single_total(self) -> None:
        """Should handle single mandate correctly."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert report["statistics"]["filtered_percentage"] == 100.0


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Warnings
# ---------------------------------------------------------------------------


class TestPhase3FilterWarnings:
    def test_warning_when_no_selection_provided(self) -> None:
        """Should warn when no mandate selection specified."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(mandates, selected_mandate_ids=None)
        assert len(report["warnings"]) > 0
        assert "No mandate selection specified" in report["warnings"][0]

    def test_no_warning_when_selection_provided(self) -> None:
        """Should not warn when selection is provided."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert len(report["warnings"]) == 0


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Checks Progression
# ---------------------------------------------------------------------------


class TestPhase3FilterChecks:
    def test_checks_false_on_failure(self) -> None:
        """Checks should be false when failures occur."""
        success, report = phase_3_filter_mandates({})
        assert report["checks"]["mandates_provided"] is False

    def test_checks_true_on_success(self) -> None:
        """All checks should be true on success."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert report["checks"]["mandates_provided"] is True
        assert report["checks"]["valid_selection"] is True
        assert report["checks"]["filtering_applied"] is True

    def test_check_mandates_provided_false_empty(self) -> None:
        """mandates_provided check should be false for empty input."""
        success, report = phase_3_filter_mandates({})
        assert report["checks"]["mandates_provided"] is False

    def test_check_mandates_provided_true_non_empty(self) -> None:
        """mandates_provided check should be true for non-empty input."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert report["checks"]["mandates_provided"] is True

    def test_check_valid_selection_false_invalid_ids(self) -> None:
        """valid_selection check should be false for invalid IDs."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M999"]
        )
        assert report["checks"]["valid_selection"] is False


# ---------------------------------------------------------------------------
# Phase 3 Filter Mandates - Edge Cases
# ---------------------------------------------------------------------------


class TestPhase3FilterEdgeCases:
    def test_duplicate_selected_ids(self) -> None:
        """Should handle duplicate IDs in selection."""
        mandates = _mandates_dict("M001", "M002")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001", "M001"]
        )
        assert success is True
        assert len(report["data"]["filtered_mandates"]) == 1

    def test_case_sensitive_mandate_ids(self) -> None:
        """Should be case-sensitive when checking IDs."""
        mandates = _mandates_dict("M001")
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["m001"]
        )
        assert success is False

    def test_mandate_with_complex_content(self) -> None:
        """Should preserve mandate content through filtering."""
        mandates = {
            "M001": {
                "id": "M001",
                "title": "Mandate 1",
                "description": "Complex desc",
                "nested": {"key": "value"},
            }
        }
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=["M001"]
        )
        assert success is True
        filtered = report["data"]["filtered_mandates"]["M001"]
        assert filtered["nested"]["key"] == "value"

    def test_selected_ids_stored_in_report(self) -> None:
        """Selected IDs should be stored in report."""
        mandates = _mandates_dict("M001", "M002")
        selection = ["M001"]
        success, report = phase_3_filter_mandates(
            mandates, selected_mandate_ids=selection
        )
        assert report["data"]["selected_ids"] == selection
