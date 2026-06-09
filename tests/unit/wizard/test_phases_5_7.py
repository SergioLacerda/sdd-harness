"""Test suite for Wizard Phases 5-7"""

import tempfile
from pathlib import Path

import pytest

from sdd_wizard.orchestration.phase_5_apply_template import phase_5_apply_template
from sdd_wizard.orchestration.phase_6_generate_project import phase_6_generate_project
from sdd_wizard.orchestration.phase_7_validate_output import phase_7_validate_output


class TestPhase5ApplyTemplate:
    """Test Phase 5: Apply template"""

    def test_phase_5_basic_execution(self) -> None:
        """Phase 5 should execute without errors"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "scaffold"
            _, report = phase_5_apply_template(output_dir, language="python")

            assert "phase" in report
            assert report["phase"] == "PHASE_5_APPLY_TEMPLATE"
            assert "status" in report
            assert "statistics" in report

    def test_phase_5_creates_directories(self) -> None:
        """Phase 5 should create project directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "scaffold"
            phase_5_apply_template(output_dir)

            # Check that directories were created
            assert (output_dir / ".sdd" / "CANONICAL").exists()
            assert (output_dir / "core").exists()
            assert (output_dir / "src").exists()

    def test_phase_5_supports_multiple_languages(self) -> None:
        """Phase 5 should support java, python, js"""
        languages = ["java", "python", "js"]

        for language in languages:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_dir = Path(tmpdir) / "scaffold"
                _, report = phase_5_apply_template(output_dir, language=language)

                assert report["data"]["language"] == language

    def test_phase_5_handles_nonexistent_template_gracefully(self) -> None:
        """Phase 5 should handle missing templates gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "scaffold"
            _, report = phase_5_apply_template(output_dir, language="rust")

            # Should not crash, but may have warnings
            assert "phase" in report


class TestPhase6GenerateProject:
    """Test Phase 6: Generate project"""

    def test_phase_6_basic_execution(self) -> None:
        """Phase 6 should execute without errors"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"

            # Minimal test data
            mandates = {"M001": {"title": "Test mandate"}}
            guidelines = {"G001": {"title": "Test guideline"}}
            metadata = {"version": "3.0.0", "description": "Test"}

            _success, report = phase_6_generate_project(
                mandates,
                guidelines,
                "mandate test",
                "guideline test",
                metadata,
                project_dir,
                language="python",
            )

            assert "phase" in report
            assert report["phase"] == "PHASE_6_GENERATE_PROJECT"

    def test_phase_6_creates_project_directories(self) -> None:
        """Phase 6 should create all project directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"

            mandates = {"M001": {"title": "Test"}}
            guidelines = {"G001": {"title": "Test"}}
            metadata = {"version": "3.0.0"}

            _ = phase_6_generate_project(
                mandates, guidelines, "mandate", "guideline", metadata, project_dir
            )

            # Check directories
            assert (project_dir / ".sdd" / "CANONICAL").exists()
            assert (project_dir / "guidelines").exists()
            assert (project_dir / "src").exists()
            assert (project_dir / "tests").exists()

    def test_phase_6_creates_specification_files(self) -> None:
        """Phase 6 should write specification files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"

            mandate_text = "mandate M001 { title: Test }"
            guideline_text = "guideline G001 { title: Test }"

            _ = phase_6_generate_project(
                {"M001": {}},
                {"G001": {}},
                mandate_text,
                guideline_text,
                {"version": "3.0.0"},
                project_dir,
            )

            assert (project_dir / ".sdd" / "CANONICAL" / "mandate.spec").exists()
            assert (project_dir / ".sdd" / "CANONICAL" / "guidelines.dsl").exists()
            assert (project_dir / ".sdd" / "CANONICAL" / "metadata.json").exists()

    def test_phase_6_generates_readme(self) -> None:
        """Phase 6 should generate README.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"

            _ = phase_6_generate_project(
                {"M001": {"title": "Test mandate"}},
                {"G001": {"title": "Test guideline"}},
                "mandate test",
                "guideline test",
                {"version": "3.0.0"},
                project_dir,
                language="python",
            )

            assert (project_dir / "README.md").exists()
            readme_content = (project_dir / "README.md").read_text(encoding="utf-8")
            assert "Test mandate" in readme_content

    def test_phase_6_generates_language_specific_build_files(self) -> None:
        """Phase 6 should generate build files for target language"""
        languages_and_files = [
            ("java", "pom.xml"),
            ("python", "requirements.txt"),
            ("js", "package.json"),
            ("go", "go.mod"),
        ]

        for language, expected_file in languages_and_files:
            with tempfile.TemporaryDirectory() as tmpdir:
                project_dir = Path(tmpdir) / "project"

                _ = phase_6_generate_project(
                    {"M001": {}},
                    {"G001": {}},
                    "mandate",
                    "guideline",
                    {"version": "3.0.0"},
                    project_dir,
                    language=language,
                )

                assert (project_dir / expected_file).exists()


class TestPhase7ValidateOutput:
    """Test Phase 7: Validate output"""

    def test_phase_7_validates_complete_project(self) -> None:
        """Phase 7 should validate a complete project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First, generate a project using Phase 6
            project_dir = Path(tmpdir) / "project"

            _success, _ = phase_6_generate_project(
                {"M001": {"title": "Test"}},
                {"G001": {"title": "Test"}},
                "mandate test",
                "guideline test",
                {"version": "3.0.0"},
                project_dir,
            )

            # Then validate it
            _, report = phase_7_validate_output(project_dir)

            assert "phase" in report
            assert report["phase"] == "PHASE_7_VALIDATE_OUTPUT"

    def test_phase_7_checks_directory_structure(self) -> None:
        """Phase 7 should verify directory structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"

            # Generate project
            phase_6_generate_project(
                {"M001": {}},
                {"G001": {}},
                "mandate",
                "guideline",
                {"version": "3.0.0"},
                project_dir,
            )

            # Validate
            _, report = phase_7_validate_output(project_dir)

            # Check that validation results exist
            assert "validation_results" in report
            assert report["validation_results"]["directory_structure"] in [True, False]

    def test_phase_7_detects_missing_files(self) -> None:
        """Phase 7 should detect missing required files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "empty_project"
            project_dir.mkdir()

            _, report = phase_7_validate_output(project_dir)

            # Should detect missing files
            assert len(report["errors"]) > 0 or len(report["warnings"]) > 0

    def test_phase_7_validates_metadata_json(self) -> None:
        """Phase 7 should validate metadata.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"

            # Generate project
            phase_6_generate_project(
                {"M001": {}},
                {"G001": {}},
                "mandate",
                "guideline",
                {"version": "3.0.0"},
                project_dir,
            )

            # Validate
            _, report = phase_7_validate_output(project_dir)

            # Check metadata validation
            assert report["validation_results"]["metadata_integrity"] in [True, False]


class TestPhase5to7Integration:
    """Integration tests for Phases 5-7"""

    def test_full_phases_5_6_7_workflow(self) -> None:
        """Phases 5-7 should work together end-to-end"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # Phase 5: Apply template
            scaffold_dir = base_dir / "scaffold"
            _, report_5 = phase_5_apply_template(scaffold_dir, language="python")
            assert report_5["status"] == "SUCCESS"

            # Phase 6: Generate project
            project_dir = base_dir / "project"
            _, report_6 = phase_6_generate_project(
                {"M001": {"title": "Clean Code"}},
                {
                    "G001": {"title": "Use type hints"},
                    "G002": {"title": "Document functions"},
                },
                "mandate M001 { title: Clean Code }",
                "guideline G001 { title: Use type hints }",
                {"version": "3.0.0"},
                project_dir,
                language="python",
            )
            assert report_6["status"] == "SUCCESS"

            # Phase 7: Validate output
            phase_7_validate_output(project_dir)

            # Should have generated files
            assert (project_dir / "README.md").exists()
            assert (project_dir / "requirements.txt").exists()
            assert (project_dir / ".sdd" / "CANONICAL" / "mandate.spec").exists()

    def test_phases_5_6_7_with_all_languages(self) -> None:
        """Test workflow with all supported languages"""
        languages = ["java", "python", "js"]

        for language in languages:
            with tempfile.TemporaryDirectory() as tmpdir:
                base_dir = Path(tmpdir)
                project_dir = base_dir / f"project_{language}"

                # Phase 6: Generate project
                _success, report = phase_6_generate_project(
                    {"M001": {}},
                    {"G001": {}},
                    "mandate",
                    "guideline",
                    {"version": "3.0.0"},
                    project_dir,
                    language=language,
                )

                assert report["status"] == "SUCCESS"
                assert (project_dir / "README.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
