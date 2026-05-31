from pathlib import Path

from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler


def _make_compiler(tmp_path: Path, verbose: bool = False) -> Phase3Compiler:
    markdown_input = tmp_path / "phase-2-input"
    markdown_input.mkdir(parents=True, exist_ok=True)
    output_path = tmp_path / "compiled"
    return Phase3Compiler(markdown_input, output_path, tmp_path, verbose=verbose)


def test_phase3_fails_fast_when_phase2_input_is_empty(tmp_path: Path) -> None:
    markdown_input = tmp_path / "generated" / "client" / "build" / "phase-2-input"
    markdown_input.mkdir(parents=True)

    output_path = tmp_path / "generated" / "client" / "compiled"
    compiler = Phase3Compiler(markdown_input, output_path, tmp_path)

    result = compiler.run()

    assert result["success"] is False
    assert "No staged files found" in result["error"]


class TestHasStagedInputFiles:
    def test_false_when_directory_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        compiler = Phase3Compiler(missing, tmp_path / "out", tmp_path)
        assert compiler.has_staged_input_files() is False

    def test_false_when_directory_empty(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "phase-2-input"
        empty_dir.mkdir()
        compiler = Phase3Compiler(empty_dir, tmp_path / "out", tmp_path)
        assert compiler.has_staged_input_files() is False

    def test_true_when_file_present(self, tmp_path: Path) -> None:
        d = tmp_path / "phase-2-input"
        d.mkdir()
        (d / "mandate.md").write_text("# test", encoding="utf-8")
        compiler = Phase3Compiler(d, tmp_path / "out", tmp_path)
        assert compiler.has_staged_input_files() is True


class TestLog:
    def test_log_silent_when_verbose_false(self, tmp_path: Path) -> None:
        logs: list[str] = []
        compiler = _make_compiler(tmp_path, verbose=False)
        compiler._emit = logs.append
        compiler.log("should not appear")
        assert logs == []

    def test_log_emits_when_verbose_true(self, tmp_path: Path) -> None:
        logs: list[str] = []
        compiler = _make_compiler(tmp_path, verbose=True)
        compiler._emit = logs.append
        compiler.log("hello world")
        assert any("hello world" in m for m in logs)


class TestLoadWizardConfig:
    def test_returns_true_when_file_missing(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler.load_wizard_config() is True
        assert compiler.language == "Python"

    def test_loads_language_from_config(self, tmp_path: Path) -> None:
        import json

        compiler = _make_compiler(tmp_path)
        compiler.client_build_dir.mkdir(parents=True, exist_ok=True)
        compiler.wizard_config_path.write_text(
            json.dumps({"language": "TypeScript"}), encoding="utf-8"
        )
        result = compiler.load_wizard_config()
        assert result is True
        assert compiler.language == "TypeScript"

    def test_returns_false_on_corrupt_json(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        compiler.client_build_dir.mkdir(parents=True, exist_ok=True)
        compiler.wizard_config_path.write_text("{bad}", encoding="utf-8")
        assert compiler.load_wizard_config() is False


class TestCreateStructure:
    def test_creates_source_directory(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.create_structure()
        assert result is True
        assert (compiler.output_path / "source").exists()


class TestCopyLanguageTemplates:
    def test_is_noop_and_returns_true(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler.copy_language_templates() is True


class TestParseMarkdownStatus:
    def test_required_status(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        content = "**Status:** `required: true`"
        assert compiler.parse_markdown_status(content) == "required"

    def test_optional_status(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        content = "**Status:** `optional: true`"
        assert compiler.parse_markdown_status(content) == "optional"

    def test_custom_status(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        content = "**Status:** `custom: true`"
        assert compiler.parse_markdown_status(content) == "custom"

    def test_defaults_to_required_when_no_match(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler.parse_markdown_status("no status here") == "required"


class TestParseMarkdownItems:
    def test_empty_directory_returns_empty_parsed_items(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.parse_markdown_items()
        assert result["mandates"] == []
        assert result["guidelines"] == []

    def test_parses_mandate_from_md_file(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        (compiler.markdown_input_path / "mandates.md").write_text(
            "## M001: Test Mandate\n**Status:** `required: true`\nSome content.\n",
            encoding="utf-8",
        )
        result = compiler.parse_markdown_items()
        assert len(result["mandates"]) == 1
        assert result["mandates"][0]["id"] == "M001"

    def test_skips_optional_items(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        (compiler.markdown_input_path / "mandates.md").write_text(
            "## M001: Required One\n**Status:** `required: true`\n\n"
            "## M002: Optional One\n**Status:** `optional: true`\n",
            encoding="utf-8",
        )
        result = compiler.parse_markdown_items()
        assert len(result["mandates"]) == 1
        assert result["mandates"][0]["id"] == "M001"

    def test_parses_guideline_from_md_file(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        (compiler.markdown_input_path / "guidelines.md").write_text(
            "## G001: Test Guideline\n**Status:** `required: true`\nContent.\n",
            encoding="utf-8",
        )
        result = compiler.parse_markdown_items()
        assert len(result["guidelines"]) == 1
        assert result["guidelines"][0]["id"] == "G001"


class TestGenerateMandatesFile:
    def test_creates_mandates_md(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        mandates = [
            {
                "id": "M001",
                "title": "Test Mandate",
                "criticality": "MANDATORY",
                "description": "A test mandate.",
            }
        ]
        result = compiler.generate_mandates_file(mandates)
        assert result is True
        mandates_file = compiler.output_path / "source" / "mandates" / "mandates.md"
        assert mandates_file.exists()
        content = mandates_file.read_text(encoding="utf-8")
        assert "M001" in content
        assert "Test Mandate" in content

    def test_returns_false_on_permission_error(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        from unittest.mock import patch

        with patch("builtins.open", side_effect=OSError("no write")):
            result = compiler.generate_mandates_file([])
        assert result is False


class TestGenerateGuidelinesFiles:
    def test_creates_guideline_files_by_category(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        guidelines = [
            {
                "id": "G001",
                "title": "Git Guideline",
                "category": "git",
                "description": "Use feature branches.",
            }
        ]
        result = compiler.generate_guidelines_files(guidelines)
        assert result is True
        assert (compiler.output_path / "source" / "guidelines" / "git.md").exists()

    def test_empty_guidelines_returns_true(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler.generate_guidelines_files([]) is True


class TestGenerateSourceReadme:
    def test_creates_readme(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        (compiler.output_path / "source").mkdir(parents=True, exist_ok=True)
        result = compiler.generate_source_readme([], [])
        assert result is True
        assert (compiler.output_path / "source" / "README.md").exists()

    def test_readme_includes_mandate_count(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        (compiler.output_path / "source").mkdir(parents=True, exist_ok=True)
        mandates = [{"id": "M001", "title": "T"}] * 3
        result = compiler.generate_source_readme(mandates, [])
        assert result is True
        content = (compiler.output_path / "source" / "README.md").read_text(
            encoding="utf-8"
        )
        assert "3" in content


class TestGenerateSourceFiles:
    def test_returns_none_on_success(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        (compiler.output_path / "source").mkdir(parents=True, exist_ok=True)
        err = compiler._generate_source_files([], [])
        assert err is None

    def test_returns_error_string_on_mandates_failure(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        compiler = _make_compiler(tmp_path)
        with patch.object(compiler, "generate_mandates_file", return_value=False):
            err = compiler._generate_source_files([], [])
        assert err == "Failed to generate mandates.md"


class TestResolveTemplatesDir:
    def test_returns_none_when_templates_missing(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler._resolve_templates_dir()
        assert result is None

    def test_returns_path_when_templates_exist(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        templates_dir = (
            tmp_path
            / "packages"
            / "interfaces"
            / "sdd_wizard"
            / "src"
            / "sdd_wizard"
            / "templates"
        )
        templates_dir.mkdir(parents=True)
        result = compiler._resolve_templates_dir()
        assert result == templates_dir
