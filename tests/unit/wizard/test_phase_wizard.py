"""Unit tests for sdd_wizard.orchestration.wizard.phase1_generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

MANDATE_SPEC = """
mandate M001 {
  type: HARD
  title: "First Mandate"
  description: "Do the right thing"
  category: governance
  rationale: "Because it matters"
}

mandate M002 {
  type: SOFT
  title: "Second Mandate"
  description: "Be careful"
  category: quality
  rationale: ""
}
"""

GUIDELINES_DSL = """
guideline G001 {
  type: SOFT
  title: "First Guideline"
  description: "Keep it simple"
  category: quality
}

guideline G002 {
  type: SOFT
  title: "Second Guideline"
  description: "Test everything"
  category: testing
}
"""


def _make_phase1(tmp_path: Path, verbose: bool = False) -> Any:
    from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator

    core_path = tmp_path / "core"
    output_path = tmp_path / "output"

    mock_paths = {
        "root": tmp_path,
        "docs_meta": tmp_path / "docs_meta",
        "source_spec": tmp_path / "docs_meta",
    }
    with patch(
        "sdd_wizard.orchestration.wizard.phase1_generator.get_sdd_paths",
        return_value=mock_paths,
    ):
        gen = Phase1Generator(
            core_path=core_path, output_path=output_path, verbose=verbose
        )
    return gen


def _setup_source_files(tmp_path: Path) -> None:
    docs_meta = tmp_path / "docs_meta"
    docs_meta.mkdir(parents=True, exist_ok=True)
    (docs_meta / "mandate.spec").write_text(MANDATE_SPEC, encoding="utf-8")
    (docs_meta / "guidelines.dsl").write_text(GUIDELINES_DSL, encoding="utf-8")


# ---------------------------------------------------------------------------
# Mandate dataclass
# ---------------------------------------------------------------------------


class TestMandate:
    def test_to_dict_contains_required_keys(self) -> None:
        from sdd_wizard.orchestration.wizard.models import Mandate

        m = Mandate(
            id="M001",
            type="HARD",
            title="Test",
            description="desc",
            category="governance",
            rationale="reason",
        )
        d = m.to_dict()
        assert d["id"] == "M001"
        assert d["type"] == "HARD"
        assert d["title"] == "Test"


class TestGuideline:
    def test_to_dict_contains_required_keys(self) -> None:
        from sdd_wizard.orchestration.wizard.models import Guideline

        g = Guideline(
            id="G001",
            type="SOFT",
            title="Guide",
            description="desc",
            category="quality",
        )
        d = g.to_dict()
        assert d["id"] == "G001"
        assert d["category"] == "quality"


# ---------------------------------------------------------------------------
# Phase1Generator
# ---------------------------------------------------------------------------


class TestPhase1GeneratorInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        assert gen is not None

    def test_source_spec_dirs_populated(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        assert len(gen.source_spec_dirs) >= 1

    def test_config_defaults(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        assert gen.language == "Python"
        assert gen.adoption_level == "FULL"

    def test_custom_config(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator

        mock_paths = {
            "root": tmp_path,
            "docs_meta": tmp_path / "docs_meta",
            "source_spec": tmp_path / "docs_meta",
        }
        with patch(
            "sdd_wizard.orchestration.wizard.phase1_generator.get_sdd_paths",
            return_value=mock_paths,
        ):
            gen = Phase1Generator(
                core_path=tmp_path / "core",
                output_path=tmp_path / "output",
                config={"language": "TypeScript", "adoption_level": "PARTIAL"},
            )
        assert gen.language == "TypeScript"
        assert gen.adoption_level == "PARTIAL"

    def test_runtime_error_in_get_sdd_paths_handled(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator

        with patch(
            "sdd_wizard.orchestration.wizard.phase1_generator.get_sdd_paths",
            side_effect=RuntimeError("no repo"),
        ):
            gen = Phase1Generator(
                core_path=tmp_path / "core",
                output_path=tmp_path / "output",
            )
        assert len(gen.source_spec_dirs) >= 1


class TestCandidateNames:
    def test_mandate_spec_returns_two_options(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        names = gen._candidate_names("mandate.spec")
        assert "mandate.spec" in names
        assert "mandate.md" in names

    def test_guidelines_dsl_returns_two_options(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        names = gen._candidate_names("guidelines.dsl")
        assert "guidelines.dsl" in names
        assert "guidelines.md" in names

    def test_other_filename_returns_itself(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        names = gen._candidate_names("other.txt")
        assert names == ["other.txt"]


class TestExtractField:
    def test_extracts_quoted_field(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        content = 'title: "My Title"\ntype: "HARD"'
        assert gen._extract_field(content, "title") == "My Title"

    def test_returns_empty_when_field_missing(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        assert gen._extract_field("some content", "title") == ""


class TestResolveSourceFile:
    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        result = gen._resolve_source_file("mandate.spec")
        assert result is None
        assert gen.last_error is not None

    def test_returns_path_when_found(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        result = gen._resolve_source_file("mandate.spec")
        assert result is not None
        assert result.exists()


class TestParseMandateSpec:
    def test_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        result = gen.parse_mandate_spec()
        assert result is False

    def test_parses_spec_format(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        result = gen.parse_mandate_spec()
        assert result is True
        assert len(gen.mandates) == 2
        assert gen.mandates[0].id == "M001"

    def test_parses_markdown_format(self, tmp_path: Path) -> None:
        docs_meta = tmp_path / "docs_meta"
        docs_meta.mkdir(parents=True, exist_ok=True)
        (docs_meta / "mandate.md").write_text(
            "# M001: First Mandate\n\n## M002: Second Mandate\n", encoding="utf-8"
        )
        gen = _make_phase1(tmp_path)
        result = gen.parse_mandate_spec()
        assert result is True
        assert len(gen.mandates) >= 1

    def test_verbose_log_called(self, tmp_path: Path, capsys: Any) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path, verbose=True)
        gen.parse_mandate_spec()
        capsys.readouterr()  # consume output
        assert len(gen.mandates) > 0


class TestParseGuidelinesDsl:
    def test_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        gen = _make_phase1(tmp_path)
        result = gen.parse_guidelines_dsl()
        assert result is False

    def test_parses_dsl_format(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        result = gen.parse_guidelines_dsl()
        assert result is True
        assert len(gen.guidelines) == 2

    def test_parses_markdown_guidelines(self, tmp_path: Path) -> None:
        docs_meta = tmp_path / "docs_meta"
        docs_meta.mkdir(parents=True, exist_ok=True)
        (docs_meta / "guidelines.md").write_text(
            "# G001: First Guideline\n\n## G002: Second Guideline\n", encoding="utf-8"
        )
        gen = _make_phase1(tmp_path)
        result = gen.parse_guidelines_dsl()
        assert result is True

    def test_empty_guidelines_is_valid(self, tmp_path: Path) -> None:
        docs_meta = tmp_path / "docs_meta"
        docs_meta.mkdir(parents=True, exist_ok=True)
        (docs_meta / "guidelines.dsl").write_text("# No guidelines\n", encoding="utf-8")
        gen = _make_phase1(tmp_path)
        result = gen.parse_guidelines_dsl()
        assert result is True


class TestGenerateMarkdownTemplates:
    def test_creates_output_directory(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        gen.parse_mandate_spec()
        gen.parse_guidelines_dsl()
        result = gen.generate_markdown_templates()
        assert result is True
        assert gen.output_path.exists()

    def test_creates_mandate_files(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        gen.parse_mandate_spec()
        gen.parse_guidelines_dsl()
        gen.generate_markdown_templates()
        mandate_files = list(gen.output_path.glob("mandates-*.md"))
        assert len(mandate_files) > 0

    def test_creates_guidelines_files(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        gen.parse_mandate_spec()
        gen.parse_guidelines_dsl()
        gen.generate_markdown_templates()
        guideline_files = list(gen.output_path.glob("guidelines-*.md"))
        assert len(guideline_files) > 0

    def test_creates_readme(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        gen.parse_mandate_spec()
        gen.parse_guidelines_dsl()
        gen.generate_markdown_templates()
        readme = gen.output_path / "README.md"
        assert readme.exists()

    def test_removes_stale_files_before_generation(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        gen.output_path.mkdir(parents=True, exist_ok=True)
        # Create a stale file
        stale = gen.output_path / "mandates-old.md"
        stale.write_text("stale content", encoding="utf-8")
        gen.parse_mandate_spec()
        gen.parse_guidelines_dsl()
        gen.generate_markdown_templates()
        # Stale file should be gone
        assert not stale.exists()


class TestPhase1Run:
    def test_returns_success_true(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        result = gen.run()
        assert result["success"] is True
        assert result["mandate_count"] == 2
        assert result["guideline_count"] == 2

    def test_returns_success_false_when_mandate_spec_missing(
        self, tmp_path: Path
    ) -> None:
        gen = _make_phase1(tmp_path)
        result = gen.run()
        assert result["success"] is False
        assert "error" in result

    def test_result_contains_mandates_and_guidelines(self, tmp_path: Path) -> None:
        _setup_source_files(tmp_path)
        gen = _make_phase1(tmp_path)
        result = gen.run()
        assert "mandates" in result
        assert "guidelines" in result
        assert len(result["mandates"]) == 2


# ---------------------------------------------------------------------------
# Phase3Compiler
# ---------------------------------------------------------------------------


def _make_phase3(tmp_path: Path) -> Any:
    from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler

    markdown_input = tmp_path / "phase-2-input"
    output_path = tmp_path / "compiled"
    repo_root = tmp_path
    markdown_input.mkdir(parents=True, exist_ok=True)
    return Phase3Compiler(
        markdown_input_path=markdown_input,
        output_path=output_path,
        repo_root=repo_root,
    )


class TestPhase3CompilerInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        assert c is not None
        assert c.language == "Python"

    def test_last_error_is_none_initially(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        assert c.last_error is None


class TestHasStagedInputFiles:
    def test_returns_false_when_dir_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler

        c = Phase3Compiler(
            markdown_input_path=tmp_path / "nonexistent",
            output_path=tmp_path / "out",
            repo_root=tmp_path,
        )
        assert c.has_staged_input_files() is False

    def test_returns_false_when_dir_empty(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        assert c.has_staged_input_files() is False

    def test_returns_true_when_files_present(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.markdown_input_path / "mandates.md").write_text("# test", encoding="utf-8")
        assert c.has_staged_input_files() is True


class TestLoadWizardConfig:
    def test_returns_true_when_no_config_file(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.load_wizard_config()
        assert result is True
        assert c.language == "Python"

    def test_loads_language_from_config(self, tmp_path: Path) -> None:
        import json

        c = _make_phase3(tmp_path)
        config = {"language": "TypeScript"}
        c.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        c.wizard_config_path.write_text(json.dumps(config), encoding="utf-8")
        result = c.load_wizard_config()
        assert result is True
        assert c.language == "TypeScript"


class TestCreateStructure:
    def test_creates_output_and_source_dirs(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.create_structure()
        assert result is True
        assert (c.output_path / "source").exists()


class TestParseMarkdownStatus:
    def test_returns_required_by_default(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        assert c.parse_markdown_status("no status here") == "required"

    def test_parses_required_status(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        content = "**Status:** `required: true`"
        assert c.parse_markdown_status(content) == "required"

    def test_parses_optional_status(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        content = "**Status:** `optional: true`"
        assert c.parse_markdown_status(content) == "optional"

    def test_parses_custom_status(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        content = "**Status:** `custom: true`"
        assert c.parse_markdown_status(content) == "custom"


class TestParseMarkdownItems:
    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.parse_markdown_items()
        assert result == {"mandates": [], "guidelines": []}

    def test_parses_mandate_and_guideline(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        content = """## M001: First Mandate\n\n**Status:** `required: true`\n\n---\n\n## G001: First Guideline\n\n**Status:** `required: true`\n"""
        (c.markdown_input_path / "items.md").write_text(content, encoding="utf-8")
        result = c.parse_markdown_items()
        assert len(result["mandates"]) == 1
        assert len(result["guidelines"]) == 1
        assert result["mandates"][0]["id"] == "M001"

    def test_skips_optional_items(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        content = """## M001: Mandatory\n\n**Status:** `required: true`\n\n---\n\n## G001: Optional Guide\n\n**Status:** `optional: true`\n"""
        (c.markdown_input_path / "items.md").write_text(content, encoding="utf-8")
        result = c.parse_markdown_items()
        assert len(result["mandates"]) == 1
        assert len(result["guidelines"]) == 0

    def test_stores_selected_guideline_ids(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        content = "## G151: CI Guidelines\n\n**Status:** `required: true`\n"
        (c.markdown_input_path / "guide.md").write_text(content, encoding="utf-8")
        c.parse_markdown_items()
        assert "G151" in c.selected_guidelines


SAMPLE_MANDATES_LIST = [
    {
        "id": "M001",
        "title": "Use type hints",
        "criticality": "OBRIGATÓRIO",
        "content": "All code must use type hints.",
    },
]

SAMPLE_GUIDELINES_LIST = [
    {
        "id": "G001",
        "title": "Conventional commits",
        "type": "GUIDELINE",
        "category": "git",
        "customizable": True,
    },
    {
        "id": "G002",
        "title": "Test coverage",
        "type": "GUIDELINE",
        "category": "testing",
        "customizable": False,
    },
]


class TestLoadCompiledGovernance:
    def test_returns_empty_lists_when_no_files(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        mandates, guidelines = c.load_compiled_governance()
        assert mandates == []
        assert guidelines == []

    def test_loads_mandates_from_core_json(self, tmp_path: Path) -> None:
        import json

        c = _make_phase3(tmp_path)
        source_dir = c.output_path / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        core_data = {"items": [{"id": "M001", "type": "MANDATE", "title": "Test"}]}
        (source_dir / "governance-core.json").write_text(
            json.dumps(core_data), encoding="utf-8"
        )

        mandates, _ = c.load_compiled_governance()
        assert len(mandates) == 1
        assert mandates[0]["id"] == "M001"

    def test_loads_guidelines_from_client_json(self, tmp_path: Path) -> None:
        import json

        c = _make_phase3(tmp_path)
        source_dir = c.output_path / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        client_data = {"items": [{"id": "G001", "type": "GUIDELINE", "title": "Guide"}]}
        (source_dir / "governance-core.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )
        (source_dir / "governance-client.json").write_text(
            json.dumps(client_data), encoding="utf-8"
        )

        _, guidelines = c.load_compiled_governance()
        assert len(guidelines) == 1

    def test_skips_non_mandate_in_core(self, tmp_path: Path) -> None:
        import json

        c = _make_phase3(tmp_path)
        source_dir = c.output_path / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        core_data = {"items": [{"id": "G001", "type": "GUIDELINE", "title": "Guide"}]}
        (source_dir / "governance-core.json").write_text(
            json.dumps(core_data), encoding="utf-8"
        )

        mandates, _ = c.load_compiled_governance()
        assert mandates == []


class TestGenerateMandatesFile:
    def test_creates_mandates_md(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source" / "mandates").mkdir(parents=True, exist_ok=True)
        result = c.generate_mandates_file(SAMPLE_MANDATES_LIST)
        assert result is True
        assert (c.output_path / "source" / "mandates" / "mandates.md").exists()

    def test_mandates_file_contains_id(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source" / "mandates").mkdir(parents=True, exist_ok=True)
        c.generate_mandates_file(SAMPLE_MANDATES_LIST)
        content = (c.output_path / "source" / "mandates" / "mandates.md").read_text(
            encoding="utf-8"
        )
        assert "M001" in content

    def test_empty_mandates_creates_file(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source" / "mandates").mkdir(parents=True, exist_ok=True)
        result = c.generate_mandates_file([])
        assert result is True


class TestGenerateGuidelinesFiles:
    def test_creates_category_file(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source" / "guidelines").mkdir(parents=True, exist_ok=True)
        result = c.generate_guidelines_files(SAMPLE_GUIDELINES_LIST)
        assert result is True
        assert (c.output_path / "source" / "guidelines" / "git.md").exists()

    def test_groups_by_category(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source" / "guidelines").mkdir(parents=True, exist_ok=True)
        c.generate_guidelines_files(SAMPLE_GUIDELINES_LIST)
        assert (c.output_path / "source" / "guidelines" / "testing.md").exists()

    def test_empty_guidelines_returns_true(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source" / "guidelines").mkdir(parents=True, exist_ok=True)
        result = c.generate_guidelines_files([])
        assert result is True


class TestGenerateSourceReadme:
    def test_creates_readme(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source").mkdir(parents=True, exist_ok=True)
        result = c.generate_source_readme(SAMPLE_MANDATES_LIST, SAMPLE_GUIDELINES_LIST)
        assert result is True
        assert (c.output_path / "source" / "README.md").exists()

    def test_readme_contains_agent_instructions(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        (c.output_path / "source").mkdir(parents=True, exist_ok=True)
        c.generate_source_readme(SAMPLE_MANDATES_LIST, SAMPLE_GUIDELINES_LIST)
        content = (c.output_path / "source" / "README.md").read_text(encoding="utf-8")
        assert "AI Agents" in content


class TestCopyLanguageTemplates:
    def test_returns_true_when_no_templates_dir(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.copy_language_templates()
        assert result is True

    def test_does_not_generate_templates_output(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.copy_language_templates()
        assert result is True
        assert not (c.output_path / "templates").exists()

    def test_does_not_generate_templates_with_go_selected(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        c.language = "Go"
        result = c.copy_language_templates()
        assert result is True
        assert not (c.output_path / "templates").exists()

    def test_does_not_generate_workflow_templates(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        c.selected_guidelines.append("G151")
        result = c.copy_language_templates()
        assert result is True
        assert not (c.output_path / "templates").exists()


class TestCopySeedlings:
    def test_returns_true_when_no_source_dir(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.copy_seedlings()
        assert result is True

    def test_copies_seedling_directories(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        source = (
            c.repo_root
            / "packages"
            / "features"
            / "sdd_integration"
            / "src"
            / "sdd_integration"
            / "templates"
        )
        github_dir = source / ".github"
        github_dir.mkdir(parents=True, exist_ok=True)
        (github_dir / "seed.md").write_text("# seed", encoding="utf-8")
        result = c.copy_seedlings()
        assert result is True
        assert (c.output_path / ".github" / "seed.md").exists()
        assert not (c.output_path / ".ia" / "seed.md").exists()


class TestPhase3CompilerRun:
    def test_returns_error_when_no_staged_files(self, tmp_path: Path) -> None:
        c = _make_phase3(tmp_path)
        result = c.run()
        assert result["success"] is False
        assert "No staged files" in result["error"]

    def test_returns_error_when_pipeline_builder_fails(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        c = _make_phase3(tmp_path)
        (c.markdown_input_path / "items.md").write_text(
            "## M001: Test\n\n**Status:** `required: true`\n", encoding="utf-8"
        )
        with patch(
            "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler.compile_with_pipeline_builder",
            return_value=False,
        ):
            result = c.run()
        assert result["success"] is False

    def test_run_with_successful_pipeline(self, tmp_path: Path) -> None:
        import json
        from unittest.mock import MagicMock, patch

        c = _make_phase3(tmp_path)
        (c.markdown_input_path / "items.md").write_text(
            "## M001: Mandate\n\n**Status:** `required: true`\n", encoding="utf-8"
        )

        # Create fake compiled output in source/ so load_compiled_governance has data
        source_dir = c.output_path / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "governance-core.json").write_text(
            json.dumps({"items": [{"id": "M001", "type": "MANDATE", "title": "Test"}]}),
            encoding="utf-8",
        )
        (source_dir / "governance-client.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )

        mock_builder = MagicMock()
        mock_builder.build.return_value = {}
        mock_builder.save_outputs.return_value = None

        with (
            patch(
                "sdd_wizard.orchestration.wizard.phase1_generator.get_sdd_paths"
            ) as mock_paths,
            patch(
                "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler.compile_with_pipeline_builder",
                return_value=True,
            ),
            patch(
                "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler.copy_seedlings",
                return_value=True,
            ),
        ):
            mock_paths.return_value = {
                "client_build": tmp_path / "build",
                "docs_meta": tmp_path / "docs-meta",
            }
            result = c.run()
            assert result["success"] is True


class TestWizardEmitters:
    def test_phase1_uses_injected_emitter(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator

        _setup_source_files(tmp_path)
        messages: list[str] = []
        mock_paths = {
            "root": tmp_path,
            "docs_meta": tmp_path / "docs_meta",
            "source_spec": tmp_path / "docs_meta",
        }
        with patch(
            "sdd_wizard.orchestration.wizard.phase1_generator.get_sdd_paths",
            return_value=mock_paths,
        ):
            gen = Phase1Generator(
                core_path=tmp_path / "core",
                output_path=tmp_path / "output",
                emitter=messages.append,
            )
        result = gen.run()
        assert result["success"] is True
        assert any("PHASE 1" in msg for msg in messages)

    def test_phase3_uses_injected_emitter(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler

        messages: list[str] = []
        c = Phase3Compiler(
            markdown_input_path=tmp_path / "phase-2-input",
            output_path=tmp_path / "compiled",
            repo_root=tmp_path,
            emitter=messages.append,
        )
        result = c.run()
        assert result["success"] is False
        assert any("PHASE 3" in msg for msg in messages)
