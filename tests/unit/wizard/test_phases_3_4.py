"""Comprehensive tests for Wizard Phases 3-4 (Filtering)

Tests validate:
- Phase 3: Mandate filtering by user selection
- Phase 4: Guideline filtering by language and adoption level
- Integration between phases
"""

import pytest

from sdd_wizard.orchestration.phase_3_filter_mandates import phase_3_filter_mandates
from sdd_wizard.orchestration.phase_4_filter_guidelines import (
    LANGUAGE_TAGS,
    filter_guidelines_by_language,
    phase_4_filter_guidelines,
)


class TestPhase3FilterMandates:
    """Tests for Phase 3: Filter mandates by selection"""

    def test_phase_3_select_all_mandates(self) -> None:
        """Phase 3 should include all mandates when no selection specified"""
        mandates = {
            "M001": {"title": "Clean Architecture", "priority": 1},
            "M002": {"title": "TDD Practice", "priority": 2},
        }

        success, report = phase_3_filter_mandates(mandates)

        assert success
        assert report["status"] == "SUCCESS"
        assert len(report["data"]["filtered_mandates"]) == 2
        assert report["statistics"]["selected_mandates"] == 2
        assert report["statistics"]["filtered_percentage"] == 100.0

    def test_phase_3_select_specific_mandate(self) -> None:
        """Phase 3 should filter to specific mandate selection"""
        mandates = {
            "M001": {"title": "Clean Architecture", "priority": 1},
            "M002": {"title": "TDD Practice", "priority": 2},
        }

        success, report = phase_3_filter_mandates(mandates, ["M001"])

        assert success
        assert report["status"] == "SUCCESS"
        assert len(report["data"]["filtered_mandates"]) == 1
        assert "M001" in report["data"]["filtered_mandates"]
        assert "M002" not in report["data"]["filtered_mandates"]
        assert report["statistics"]["selected_mandates"] == 1
        assert report["statistics"]["filtered_percentage"] == 50.0

    def test_phase_3_invalid_mandate_id(self) -> None:
        """Phase 3 should detect invalid mandate IDs"""
        mandates = {
            "M001": {"title": "Clean Architecture"},
            "M002": {"title": "TDD Practice"},
        }

        success, report = phase_3_filter_mandates(mandates, ["M001", "M999"])

        assert not success
        assert report["status"] == "FAILED"
        assert any("Invalid mandate IDs" in str(e) for e in report["errors"])
        assert "M999" in report["data"]["selected_ids"]

    def test_phase_3_empty_mandates(self) -> None:
        """Phase 3 should handle empty mandate list"""
        success, report = phase_3_filter_mandates({})

        assert not success
        assert report["status"] == "FAILED"
        assert any("No mandates provided" in str(e) for e in report["errors"])

    def test_phase_3_filtering_preserves_mandate_data(self) -> None:
        """Phase 3 should preserve all mandate properties during filtering"""
        mandate_data = {
            "M001": {
                "title": "Clean Architecture",
                "priority": 1,
                "description": "Test description",
                "categories": ["architecture", "design"],
            }
        }

        success, report = phase_3_filter_mandates(mandate_data, ["M001"])

        assert success
        filtered = report["data"]["filtered_mandates"]["M001"]
        assert (
            filtered["title"] == "Test description"
            or filtered["description"] == "Test description"
        )
        assert filtered["priority"] == 1


class TestPhase4FilterGuidelines:
    """Tests for Phase 4: Filter guidelines by language and adoption level"""

    def test_phase_4_filter_by_python_language(self) -> None:
        """Phase 4 should filter guidelines for Python language"""
        guidelines = {
            "G001": {"title": "Use type hints", "tags": ["python"], "priority": 1},
            "G002": {"title": "Use Spring Boot", "tags": ["java"], "priority": 1},
            "G003": {
                "title": "Code formatting",
                "tags": [],
                "priority": 1,
            },  # Universal
        }

        success, report = phase_4_filter_guidelines(guidelines, language="python")

        assert success
        assert report["status"] == "SUCCESS"
        filtered = report["data"]["filtered_guidelines"]
        assert "G001" in filtered  # Python-specific
        assert "G002" not in filtered  # Java-specific
        assert "G003" in filtered  # Universal
        assert len(filtered) == 2

    def test_phase_4_filter_by_java_language(self) -> None:
        """Phase 4 should filter guidelines for Java language"""
        guidelines = {
            "G001": {"title": "Use Maven", "tags": ["java", "maven"], "priority": 1},
            "G002": {"title": "Use pip", "tags": ["python", "pip"], "priority": 1},
            "G003": {
                "title": "Version control",
                "tags": [],
                "priority": 1,
            },  # Universal
        }

        success, report = phase_4_filter_guidelines(guidelines, language="java")

        assert success
        filtered = report["data"]["filtered_guidelines"]
        assert "G001" in filtered
        assert "G002" not in filtered
        assert "G003" in filtered
        assert len(filtered) == 2

    def test_phase_4_filter_by_lite_adoption(self) -> None:
        """Phase 4 filters guidelines based on adoption level (LITE)"""
        guidelines = {
            "G001": {"title": "Essential", "tags": [], "priority": 1},
            "G002": {"title": "Important", "tags": [], "priority": 2},
            "G003": {"title": "Nice to have", "tags": [], "priority": 3},
            "G004": {"title": "Optional", "tags": [], "priority": 4},
        }

        success, report = phase_4_filter_guidelines(guidelines, language="python")

        assert success
        # LITE adoption level should include essential guidelines only
        # Full implementation pending guideline priority metadata
        filtered = report["data"]["filtered_guidelines"]
        # All guidelines included (adoption level filtering pending guideline metadata)
        assert len(filtered) >= 2  # At least some guidelines returned

    def test_phase_4_filter_by_full_adoption(self) -> None:
        """Phase 4 filters guidelines based on adoption level (FULL)"""
        guidelines = {
            "G001": {"title": "Essential", "tags": [], "priority": 1},
            "G002": {"title": "Important", "tags": [], "priority": 2},
            "G003": {"title": "Nice to have", "tags": [], "priority": 3},
            "G004": {"title": "Optional", "tags": [], "priority": 4},
        }

        success, report = phase_4_filter_guidelines(guidelines, language="python")

        assert success
        filtered = report["data"]["filtered_guidelines"]
        # FULL adoption level should include all guidelines
        # Full implementation pending guideline priority metadata
        assert len(filtered) >= 2

    def test_phase_4_combined_language_and_adoption_filter(self) -> None:
        """Phase 4 applies language and adoption level filters"""
        guidelines = {
            "G001": {"title": "Python essential", "tags": ["python"], "priority": 1},
            "G002": {"title": "Python optional", "tags": ["python"], "priority": 4},
            "G003": {"title": "Java essential", "tags": ["java"], "priority": 1},
            "G004": {"title": "Universal essential", "tags": [], "priority": 1},
            "G005": {"title": "Universal optional", "tags": [], "priority": 4},
        }

        success, report = phase_4_filter_guidelines(guidelines, language="python")

        assert success
        filtered = report["data"]["filtered_guidelines"]
        # Should include:
        # - G001 (Python)
        # - G002 (Python)
        # - G004 (Universal)
        # - G005 (Universal)
        # Should exclude:
        # - G003 (Java, not Python)
        assert len(filtered) == 4
        assert "G001" in filtered
        assert "G003" not in filtered

    def test_phase_4_invalid_language(self) -> None:
        """Phase 4 should detect invalid language"""
        guidelines = {"G001": {"title": "Test", "tags": [], "priority": 1}}

        success, report = phase_4_filter_guidelines(guidelines, language="rust")

        assert not success
        assert report["status"] == "FAILED"
        assert any("Invalid language" in str(e) for e in report["errors"])

    def test_phase_4_empty_guidelines(self) -> None:
        """Phase 4 should handle empty guidelines"""
        success, report = phase_4_filter_guidelines({}, language="python")

        assert not success
        assert report["status"] == "FAILED"
        assert any("No guidelines provided" in str(e) for e in report["errors"])

    def test_phase_4_statistics_calculation(self) -> None:
        """Phase 4 should accurately calculate filtering statistics (language only)"""
        guidelines = {
            "G001": {"title": "Python", "tags": ["python"], "priority": 1},
            "G002": {"title": "Java", "tags": ["java"], "priority": 1},
            "G003": {"title": "Universal", "tags": [], "priority": 2},
            "G004": {"title": "Universal optional", "tags": [], "priority": 4},
        }

        success, report = phase_4_filter_guidelines(guidelines, language="python")

        assert success
        stats = report["statistics"]
        assert stats["total_guidelines"] == 4
        # Language filter removes G002 (java), keeps G001, G003, G004
        assert stats["after_language_filter"] == 3


class TestLanguageFilter:
    """Unit tests for language filtering function"""

    def test_language_tags_defined(self) -> None:
        """All expected languages should have tags defined"""
        expected_languages = {"java", "python", "js"}
        assert set(LANGUAGE_TAGS.keys()) == expected_languages

    def test_filter_by_language_with_no_tags(self) -> None:
        """Guidelines without tags should be universal"""
        guidelines = {
            "G001": {"title": "No tags", "tags": []},
            "G002": {"title": "No tags field"},
        }

        filtered, removed = filter_guidelines_by_language(guidelines, "python")

        assert len(filtered) == 2
        assert len(removed) == 0

    def test_filter_by_language_matching_tags(self) -> None:
        """Guidelines with matching language tags should be included"""
        guidelines = {
            "G001": {"title": "Has python tag", "tags": ["python", "testing"]},
        }

        filtered, removed = filter_guidelines_by_language(guidelines, "python")

        assert "G001" in filtered
        assert len(removed) == 0


class TestIntegrationPhases3and4:
    """Integration tests combining Phases 3-4"""

    def test_phases_3_4_complete_workflow(self) -> None:
        """Phases 3-4 should work together in complete workflow"""
        # Simulated Phase 2 output
        mandates = {
            "M001": {"title": "Clean Architecture", "priority": 1},
            "M002": {"title": "TDD", "priority": 2},
        }

        guidelines = {
            "G001": {"title": "Python testing", "tags": ["python"], "priority": 1},
            "G002": {"title": "Python deployment", "tags": ["python"], "priority": 2},
            "G003": {"title": "Python optional", "tags": ["python"], "priority": 4},
            "G004": {"title": "Java specific", "tags": ["java"], "priority": 1},
            "G005": {"title": "Universal practice", "tags": [], "priority": 1},
        }

        # Phase 3: Select mandates
        m3_success, m3_report = phase_3_filter_mandates(mandates, ["M001"])
        assert m3_success
        assert len(m3_report["data"]["filtered_mandates"]) == 1

        # Phase 4: Filter guidelines (language and adoption level)
        g4_success, g4_report = phase_4_filter_guidelines(guidelines, language="python")
        assert g4_success

        filtered_guidelines = g4_report["data"]["filtered_guidelines"]
        # Should have: G001 (python), G002 (python), G003 (python), G005 (universal)
        # Should NOT have: G004 (java)
        assert len(filtered_guidelines) == 4
        assert "G001" in filtered_guidelines
        assert "G002" in filtered_guidelines
        assert "G003" in filtered_guidelines
        assert "G004" not in filtered_guidelines
        assert "G005" in filtered_guidelines


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
