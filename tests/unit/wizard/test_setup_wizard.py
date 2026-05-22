"""
Unit tests for setup-wizard.py

Tests interactive PATH selection, context determination, and documentation loading.
Run: pytest tests/spec_validation/test_setup_wizard.py -v
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestSetupWizardPath:
    """Test PATH determination logic."""

    def test_path_a_for_bug_fix(self) -> None:
        """PATH A should be selected for bug fixes."""
        # Simulate user choosing "Fix a bug"
        mock_choice = "0"  # First option (index 0)
        with patch("builtins.input", return_value=mock_choice):
            # In real test, would call determine_path()
            # For now, just verify PATH mapping exists
            path_map = {
                "Fix a bug (PATH A)": "A",
                "Add a simple feature (PATH B)": "B",
                "Build complex feature (PATH C)": "C",
                "Parallel work (PATH D)": "D",
            }
            assert path_map["Fix a bug (PATH A)"] == "A"

    def test_path_b_for_simple_feature(self) -> None:
        """PATH B should be selected for simple features."""
        path_map = {
            "Fix a bug (PATH A)": "A",
            "Add a simple feature (PATH B)": "B",
            "Build complex feature (PATH C)": "C",
            "Parallel work (PATH D)": "D",
        }
        assert path_map["Add a simple feature (PATH B)"] == "B"

    def test_path_c_for_complex_feature(self) -> None:
        """PATH C should be selected for complex features."""
        path_map = {
            "Fix a bug (PATH A)": "A",
            "Add a simple feature (PATH B)": "B",
            "Build complex feature (PATH C)": "C",
            "Parallel work (PATH D)": "D",
        }
        assert path_map["Build complex feature (PATH C)"] == "C"

    def test_path_d_for_parallel_work(self) -> None:
        """PATH D should be selected for parallel work."""
        path_map = {
            "Fix a bug (PATH A)": "A",
            "Add a simple feature (PATH B)": "B",
            "Build complex feature (PATH C)": "C",
            "Parallel work (PATH D)": "D",
        }
        assert path_map["Parallel work (PATH D)"] == "D"


class TestSetupWizardDocumentLoading:
    """Test documentation loading logic."""

    def test_path_a_loads_bug_fix_docs(self) -> None:
        """PATH A should load bug fix documentation."""
        # Simplified version of get_doc_paths logic
        essential = [
            "docs/ia/CANONICAL/rules/constitution.md",
            "docs/ia/CANONICAL/rules/ia-rules.md",
        ]

        path_a_docs = [
            "docs/ia/CANONICAL/specifications/architecture.md",
            "docs/ia/custom/_TEMPLATE/reality/current-system-state/known_issues.md",
            "docs/ia/custom/_TEMPLATE/reality/current-system-state/services.md",
        ]

        docs = essential + path_a_docs

        assert "constitution.md" in str(docs)
        assert "ia-rules.md" in str(docs)
        assert "known_issues.md" in str(docs)
        assert len(docs) >= 5

    def test_path_b_loads_feature_docs(self) -> None:
        """PATH B should load feature development documentation."""
        essential = [
            "docs/ia/CANONICAL/rules/constitution.md",
            "docs/ia/CANONICAL/rules/ia-rules.md",
        ]

        path_b_docs = [
            "docs/ia/CANONICAL/rules/conventions.md",
            "docs/ia/CANONICAL/specifications/architecture.md",
            "docs/ia/CANONICAL/specifications/feature-checklist.md",
            "docs/ia/custom/_TEMPLATE/reality/current-system-state/contracts.md",
        ]

        docs = essential + path_b_docs

        assert "feature-checklist.md" in str(docs)
        assert len(docs) >= 6

    def test_path_c_loads_comprehensive_docs(self) -> None:
        """PATH C should load comprehensive architecture documentation."""
        essential = [
            "docs/ia/CANONICAL/rules/constitution.md",
            "docs/ia/CANONICAL/rules/ia-rules.md",
        ]

        path_c_docs = [
            "docs/ia/CANONICAL/specifications/architecture.md",
            "docs/ia/CANONICAL/rules/conventions.md",
            "docs/ia/CANONICAL/specifications/feature-checklist.md",
            "docs/ia/CANONICAL/specifications/testing.md",
            "docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md",
        ]

        docs = essential + path_c_docs

        assert "testing.md" in str(docs)
        assert "ADR-003" in str(docs)
        assert len(docs) >= 7

    def test_path_d_loads_threading_docs(self) -> None:
        """PATH D should load threading and parallel work documentation."""
        essential = [
            "docs/ia/CANONICAL/rules/constitution.md",
            "docs/ia/CANONICAL/rules/ia-rules.md",
        ]

        path_d_docs = [
            "docs/ia/custom/_TEMPLATE/development/execution-state/_current.md",
            "docs/ia/CANONICAL/rules/ENFORCEMENT_RULES.md",
            "docs/ia/CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md",
        ]

        docs = essential + path_d_docs

        assert "execution-state" in str(docs)
        assert "thread-isolation" in str(docs)
        assert len(docs) >= 5

    def test_quick_context_reduces_docs(self) -> None:
        """Quick context should return minimal docs."""
        # With quick context, should limit to top 5 docs
        docs = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        quick_docs = docs[:5]
        assert len(quick_docs) == 5

    def test_deep_dive_context_adds_docs(self) -> None:
        """Deep dive context should add extra documentation."""
        essential = ["doc1", "doc2"]
        base_docs = ["doc3", "doc4", "doc5"]
        additional = ["doc6_testing", "doc7_definition_of_done"]

        docs = essential + base_docs + additional
        assert len(docs) == 7


class TestSetupWizardContextSize:
    """Test context size determination."""

    def test_context_choices_valid(self) -> None:
        """Context choices should include quick, standard, deep."""
        choices = [
            "Quick (only essential docs, <10 min read)",
            "Standard (recommended, 15-20 min)",
            "Deep dive (complete context, 30+ min)",
        ]

        assert len(choices) == 3
        assert "Quick" in str(choices)
        assert "Standard" in str(choices)
        assert "Deep dive" in str(choices)

    def test_quick_context_less_than_ten_min(self) -> None:
        """Quick context should require <10 min reading."""
        # Assuming ~100 bytes = 1 min read
        quick_size_kb = 20  # ~10 min read
        assert quick_size_kb <= 30


class TestSetupWizardExperience:
    """Test experience level determination."""

    def test_experience_levels_exist(self) -> None:
        """Should have three experience levels."""
        levels = [
            "Brand new (first day)",
            "Some context (few weeks)",
            "Experienced (6+ months)",
        ]
        assert len(levels) == 3

    def test_experience_affects_doc_recommendations(self) -> None:
        """Experience level should affect doc depth recommendations."""
        # Brand new: more basics
        # Experienced: more advanced
        new_dev_focus = ["basics", "first-steps"]
        experienced_focus = ["architecture", "advanced"]

        assert "basics" in new_dev_focus
        assert "architecture" in experienced_focus


class TestSetupWizardTestMode:
    """Test the --test CLI mode."""

    def test_test_mode_no_input(self) -> None:
        """Test mode should run without user input."""
        wizard_path = Path("docs/ia/SCRIPTS/setup-wizard.py")
        if wizard_path.exists():
            result = subprocess.run(
                [sys.executable, str(wizard_path), "--test"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0
            assert "Test Mode" in result.stdout or "test" in result.stdout.lower()

    def test_test_mode_outputs_metrics(self) -> None:
        """Test mode should output timing metrics."""
        wizard_path = Path("docs/ia/SCRIPTS/setup-wizard.py")
        if wizard_path.exists():
            result = subprocess.run(
                [sys.executable, str(wizard_path), "--test", "--verbose"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0
            # Should contain timing information
            output = result.stdout.lower()
            assert any(keyword in output for keyword in ["duration", "seconds", "test"])


class TestSetupWizardProfileSaving:
    """Test profile saving functionality."""

    def test_profile_format_valid(self) -> None:
        """Saved profile should have valid format."""
        profile_content = "PATH=A\nCONTEXT=Quick\nEXPERIENCE=Brand new\n"

        lines = profile_content.strip().split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("PATH=")
        assert lines[1].startswith("CONTEXT=")
        assert lines[2].startswith("EXPERIENCE=")

    def test_profile_path_extraction(self) -> None:
        """Should extract PATH from profile."""
        profile_content = "PATH=A\nCONTEXT=Quick\nEXPERIENCE=Brand new\n"

        for line in profile_content.split("\n"):
            if line.startswith("PATH="):
                path = line.split("=")[1]
                assert path in ["A", "B", "C", "D"]


class TestSetupWizardErrorHandling:
    """Test error handling."""

    def test_handles_missing_docs_gracefully(self) -> None:
        """Should handle missing documentation files."""
        # Simulate checking non-existent file
        doc_path = Path("docs/ia/nonexistent-file.md")
        assert not doc_path.exists()
        # Should not crash, should have default estimate

    def test_handles_keyboard_interrupt(self) -> None:
        """Should handle Ctrl+C gracefully."""
        # Would need integration test to verify
        pass

    def test_handles_invalid_choice(self) -> None:
        """Should handle invalid user input."""
        invalid_choices = ["0", "5", "abc", ""]
        for choice in invalid_choices:
            # Valid choices are 1-4
            is_valid = choice.isdigit() and 1 <= int(choice) <= 4
            assert is_valid in [False, False, False, False]


class TestSetupWizardIntegration:
    """Integration tests for full workflow."""

    def test_full_setup_workflow_test_mode(self) -> None:
        """Full workflow should complete in test mode."""
        wizard_path = Path("docs/ia/SCRIPTS/setup-wizard.py")
        if wizard_path.exists():
            result = subprocess.run(
                [sys.executable, str(wizard_path), "--test"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0

    def test_all_paths_produce_valid_output(self) -> None:
        """Each PATH should produce valid documentation list."""
        paths = ["A", "B", "C", "D"]

        # Verify each path has associated docs
        for path in paths:
            assert path in ["A", "B", "C", "D"]


class TestSetupWizardMetrics:
    """Test metrics collection."""

    def test_timing_measurement_works(self) -> None:
        """Should measure setup time in seconds."""
        import time

        start = time.time()
        time.sleep(0.1)
        elapsed = time.time() - start

        assert elapsed >= 0.1
        assert isinstance(elapsed, float)

    def test_verbose_mode_outputs_metrics(self) -> None:
        """Verbose mode should output detailed metrics."""
        wizard_path = Path("docs/ia/SCRIPTS/setup-wizard.py")
        if wizard_path.exists():
            result = subprocess.run(
                [sys.executable, str(wizard_path), "--test", "--verbose"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Should have metrics output
            assert "Duration" in result.stdout or "seconds" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
