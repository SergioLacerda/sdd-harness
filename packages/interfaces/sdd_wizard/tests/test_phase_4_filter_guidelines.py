"""Tests for Phase 4: Filter guidelines by language and adoption level.

Covers:
- Language-based filtering (java, python, js)
- Universal guidelines (no tags)
- Language tag matching
- Invalid language error handling
- Empty guidelines error handling
- Report structure validation
- Statistics calculation
"""

from __future__ import annotations

from typing import Any

import pytest

from sdd_wizard.orchestration.phase_4_filter_guidelines import (
    LANGUAGE_TAGS,
    filter_guidelines_by_language,
    phase_4_filter_guidelines,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _guideline(
    guide_id: str, title: str = "Test", tags: list[str] | None = None
) -> dict[str, Any]:
    """Create a sample guideline dict."""
    result = {
        "id": guide_id,
        "title": title,
        "description": f"Guideline {guide_id}",
    }
    if tags:
        result["tags"] = tags
    return result


def _guidelines_dict(
    *ids: str, tags: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """Create guidelines dict from IDs and optional tags."""
    tags = tags or {}
    return {gid: _guideline(gid, tags=tags.get(gid)) for gid in ids}


# ---------------------------------------------------------------------------
# filter_guidelines_by_language — Basic Functionality
# ---------------------------------------------------------------------------


class TestFilterGuidelinesByLanguageBasic:
    def test_filter_python_guidelines(self) -> None:
        """Should filter to python-related guidelines."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            tags={"G001": ["python"], "G002": ["java"], "G003": ["python", "testing"]},
        )
        filtered, removed = filter_guidelines_by_language(guidelines, "python")
        assert len(filtered) == 2
        assert "G001" in filtered
        assert "G003" in filtered
        assert "G002" not in filtered
        assert removed == ["G002"]

    def test_filter_java_guidelines(self) -> None:
        """Should filter to java-related guidelines."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            tags={"G001": ["java", "maven"], "G002": ["python"]},
        )
        filtered, removed = filter_guidelines_by_language(guidelines, "java")
        assert "G001" in filtered
        assert "G002" not in filtered

    def test_filter_js_guidelines(self) -> None:
        """Should filter to javascript-related guidelines."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            tags={"G001": ["javascript", "react"], "G002": ["python"]},
        )
        filtered, removed = filter_guidelines_by_language(guidelines, "js")
        assert "G001" in filtered
        assert "G002" not in filtered

    def test_universal_guidelines_always_included(self) -> None:
        """Guidelines without tags should be included for all languages."""
        guidelines = {
            "G001": _guideline("G001"),  # No tags
            "G002": _guideline("G002", tags=["python"]),
        }
        for lang in ["python", "java", "js"]:
            filtered, removed = filter_guidelines_by_language(guidelines, lang)
            assert "G001" in filtered  # Universal always included


class TestFilterGuidelinesByLanguageTags:
    def test_multiple_tag_matching(self) -> None:
        """Should match any tag in language set."""
        guidelines = _guidelines_dict(
            "G001",
            tags={"G001": ["pytest", "django", "flask"]},  # All python-related
        )
        filtered, removed = filter_guidelines_by_language(guidelines, "python")
        assert "G001" in filtered

    def test_case_insensitive_tags(self) -> None:
        """Should match tags case-insensitively."""
        guidelines = _guidelines_dict("G001", tags={"G001": ["PYTHON", "Flask"]})
        filtered, removed = filter_guidelines_by_language(guidelines, "python")
        assert "G001" in filtered

    def test_partial_tag_match(self) -> None:
        """Should match if any tag is in language set."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            tags={
                "G001": ["unrelated", "python", "other"],
                "G002": ["unrelated", "other"],
            },
        )
        filtered, removed = filter_guidelines_by_language(guidelines, "python")
        assert "G001" in filtered
        assert "G002" not in filtered


class TestFilterGuidelinesByLanguageEdgeCases:
    def test_empty_guidelines(self) -> None:
        """Should handle empty guidelines dict."""
        filtered, removed = filter_guidelines_by_language({}, "python")
        assert filtered == {}
        assert removed == []

    def test_unknown_language(self) -> None:
        """Should have no matches for unknown language."""
        guidelines = _guidelines_dict("G001", tags={"G001": ["python"]})
        filtered, removed = filter_guidelines_by_language(guidelines, "ruby")
        assert "G001" not in filtered
        assert "G001" in removed

    def test_removed_list_correct(self) -> None:
        """Removed list should contain all non-matching guideline IDs."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            tags={"G001": ["python"], "G002": ["java"], "G003": ["java"]},
        )
        filtered, removed = filter_guidelines_by_language(guidelines, "python")
        assert sorted(removed) == ["G002", "G003"]


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Basic Functionality
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesBasic:
    def test_filter_with_python_language(self) -> None:
        """Should filter guidelines by python language."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            tags={"G001": ["python"], "G002": ["java"], "G003": None},
        )
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert success is True
        assert report["status"] == "SUCCESS"
        filtered = report["data"]["filtered_guidelines"]
        assert "G001" in filtered
        assert "G003" in filtered
        assert "G002" not in filtered

    def test_filter_with_java_language(self) -> None:
        """Should filter guidelines by java language."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            tags={"G001": ["java"], "G002": ["python"]},
        )
        success, report = phase_4_filter_guidelines(guidelines, language="java")
        assert success is True
        assert "G001" in report["data"]["filtered_guidelines"]
        assert "G002" not in report["data"]["filtered_guidelines"]

    def test_filter_with_js_language(self) -> None:
        """Should filter guidelines by js language."""
        guidelines = _guidelines_dict(
            "G001",
            tags={"G001": ["javascript", "typescript"]},
        )
        success, report = phase_4_filter_guidelines(guidelines, language="js")
        assert success is True
        assert "G001" in report["data"]["filtered_guidelines"]


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Error Handling
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesErrors:
    def test_no_guidelines_provided(self) -> None:
        """Should fail when no guidelines provided."""
        success, report = phase_4_filter_guidelines({}, language="python")
        assert success is False
        assert report["status"] == "FAILED"
        assert "No guidelines provided" in report["errors"][0]

    def test_invalid_language(self) -> None:
        """Should fail with invalid language."""
        guidelines = _guidelines_dict("G001", tags={"G001": ["python"]})
        success, report = phase_4_filter_guidelines(guidelines, language="ruby")
        assert success is False
        assert report["status"] == "FAILED"
        assert "Invalid language" in report["errors"][0]
        assert "ruby" in report["errors"][0]

    def test_filtering_results_in_zero_guidelines(self) -> None:
        """Should fail when filtering results in zero guidelines."""
        guidelines = _guidelines_dict("G001", tags={"G001": ["python"]})
        success, report = phase_4_filter_guidelines(guidelines, language="java")
        assert success is False
        assert "Filtering resulted in zero guidelines" in report["errors"]


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Report Structure
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesReportStructure:
    def test_report_has_required_keys(self) -> None:
        """Report should have all required keys."""
        guidelines = _guidelines_dict("G001", tags={"G001": ["python"]})
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert "phase" in report
        assert "status" in report
        assert "checks" in report
        assert "data" in report
        assert "statistics" in report
        assert "errors" in report
        assert "warnings" in report

    def test_phase_name_correct(self) -> None:
        """Phase name should be correct."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert report["phase"] == "PHASE_4_FILTER_GUIDELINES"

    def test_checks_structure(self) -> None:
        """Checks should have correct structure."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert "guidelines_provided" in report["checks"]
        assert "language_valid" in report["checks"]
        assert "language_filtering_applied" in report["checks"]

    def test_data_structure(self) -> None:
        """Data should have correct structure."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert "filtered_guidelines" in report["data"]
        assert "language" in report["data"]
        assert "filtering_details" in report["data"]
        assert "language_removed" in report["data"]["filtering_details"]

    def test_statistics_structure(self) -> None:
        """Statistics should have correct structure."""
        guidelines = _guidelines_dict("G001", "G002")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert "total_guidelines" in report["statistics"]
        assert "after_language_filter" in report["statistics"]
        assert "language_filter_percentage" in report["statistics"]


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Statistics
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesStatistics:
    def test_total_guidelines_count(self) -> None:
        """Total guidelines should match input."""
        guidelines = _guidelines_dict("G001", "G002", "G003", "G004")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert report["statistics"]["total_guidelines"] == 4

    def test_after_language_filter_count(self) -> None:
        """Should count correctly after language filter."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            tags={"G001": ["python"], "G002": ["java"], "G003": ["python"]},
        )
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert report["statistics"]["after_language_filter"] == 2

    def test_language_filter_percentage(self) -> None:
        """Percentage should be calculated correctly."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            "G004",
            tags={
                "G001": ["python"],
                "G002": ["java"],
                "G003": ["python"],
                "G004": None,
            },
        )
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        # 3/4 = 75%
        assert report["statistics"]["language_filter_percentage"] == 75.0

    def test_percentage_rounding(self) -> None:
        """Percentage should be rounded correctly."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            tags={"G001": ["python"], "G002": ["java"], "G003": ["java"]},
        )
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        # 1/3 = 33.333...%
        assert isinstance(report["statistics"]["language_filter_percentage"], float)
        assert report["statistics"]["language_filter_percentage"] == pytest.approx(
            33.3, abs=0.1
        )


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Language Validation
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesLanguageValidation:
    def test_valid_languages_accepted(self) -> None:
        """All valid languages should be accepted."""
        guidelines = _guidelines_dict("G001")
        for language in LANGUAGE_TAGS:
            success, report = phase_4_filter_guidelines(guidelines, language=language)
            assert report["checks"]["language_valid"] is True

    def test_check_guidelines_provided_false_empty(self) -> None:
        """guidelines_provided check should be false for empty input."""
        success, report = phase_4_filter_guidelines({})
        assert report["checks"]["guidelines_provided"] is False

    def test_check_guidelines_provided_true_non_empty(self) -> None:
        """guidelines_provided check should be true for non-empty input."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert report["checks"]["guidelines_provided"] is True

    def test_check_language_valid_true(self) -> None:
        """language_valid check should be true for valid language."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert report["checks"]["language_valid"] is True

    def test_check_language_valid_false_invalid(self) -> None:
        """language_valid check should be false for invalid language."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="ruby")
        assert report["checks"]["language_valid"] is False


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Filtering Details
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesFilteringDetails:
    def test_language_removed_list(self) -> None:
        """Should list removed guidelines in filtering details."""
        guidelines = _guidelines_dict(
            "G001",
            "G002",
            "G003",
            tags={"G001": ["python"], "G002": ["java"], "G003": ["java"]},
        )
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        removed = report["data"]["filtering_details"]["language_removed"]
        assert "G002" in removed
        assert "G003" in removed
        assert "G001" not in removed

    def test_language_stored_in_report(self) -> None:
        """Selected language should be stored in report."""
        guidelines = _guidelines_dict("G001")
        success, report = phase_4_filter_guidelines(guidelines, language="java")
        assert report["data"]["language"] == "java"


# ---------------------------------------------------------------------------
# phase_4_filter_guidelines — Edge Cases
# ---------------------------------------------------------------------------


class TestPhase4FilterGuidelinesEdgeCases:
    def test_guideline_with_many_tags(self) -> None:
        """Should handle guidelines with many tags."""
        guidelines = {
            "G001": _guideline(
                "G001",
                tags=["python", "java", "javascript", "testing", "performance"],
            )
        }
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert "G001" in report["data"]["filtered_guidelines"]

    def test_guideline_with_empty_tags_list(self) -> None:
        """Should treat empty tags list as universal."""
        guidelines = {"G001": _guideline("G001", tags=[])}
        success, report = phase_4_filter_guidelines(guidelines, language="python")
        assert "G001" in report["data"]["filtered_guidelines"]

    def test_language_tags_coverage(self) -> None:
        """Should have language tags for all supported languages."""
        assert "python" in LANGUAGE_TAGS
        assert "java" in LANGUAGE_TAGS
        assert "js" in LANGUAGE_TAGS

    def test_default_language_is_python(self) -> None:
        """Default language should be python."""
        guidelines = _guidelines_dict("G001", tags={"G001": ["python"]})
        success, report = phase_4_filter_guidelines(guidelines)
        assert report["data"]["language"] == "python"
        assert success is True
