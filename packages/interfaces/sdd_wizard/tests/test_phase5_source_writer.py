"""Tests for SddSourceWriter — Phase 5 .sdd/source and .sdd/runtime generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sdd_core.utils.text_io import read_text_utf8
from sdd_wizard.orchestration.phase5_source_writer import SddSourceWriter

_SAMPLE_MANDATES = [
    {
        "id": "M001",
        "title": "Validate First",
        "criticality": "OBRIGATÓRIO",
        "content": "Always validate.",
    },
    {
        "id": "M002",
        "title": None,
        "criticality": "OBRIGATÓRIO",
        "description": "Use descriptions.",
        "summary_minimal": None,
    },
    {"id": "M003", "title": "No Desc", "criticality": "OBRIGATÓRIO"},
]

_SAMPLE_GUIDELINES: dict[str, Any] = {
    "G001": {
        "id": "G001",
        "title": "Test Coverage",
        "type": "GUIDELINE",
        "status": "required",
        "customizable": True,
        "content": "Write tests.",
    },
    "G002": {
        "id": "G002",
        "title": None,
        "type": "GUIDELINE",
        "status": "optional",
        "customizable": False,
        "content": "",
    },
}

_SAMPLE_BY_CATEGORY = {
    "testing": [
        {
            "id": "G001",
            "title": "Test Coverage",
            "type": "GUIDELINE",
            "status": "required",
            "customizable": True,
            "content": "Write tests.",
        },
    ],
    "custom_cat": [
        {
            "id": "G002",
            "title": "Custom",
            "type": "GUIDELINE",
            "status": "optional",
            "customizable": True,
            "content": "Custom content.",
        },
    ],
}


def _make_writer(
    tmp_path: Path,
    mandates: list | None = None,
    guidelines: dict | None = None,
    guidelines_by_category: dict | None = None,
    verbose: bool = False,
) -> SddSourceWriter:
    output_base = tmp_path / "out"
    source_dir = output_base / ".sdd" / "source"
    runtime_dir = output_base / ".sdd" / "runtime"
    mandates_dir = source_dir / "mandates"
    guidelines_dir = source_dir / "guidelines"
    return SddSourceWriter(
        output_base=output_base,
        source_dir=source_dir,
        runtime_dir=runtime_dir,
        mandates_dir=mandates_dir,
        guidelines_dir=guidelines_dir,
        mandates=mandates if mandates is not None else list(_SAMPLE_MANDATES),
        guidelines=guidelines if guidelines is not None else dict(_SAMPLE_GUIDELINES),
        guidelines_by_category=guidelines_by_category
        if guidelines_by_category is not None
        else dict(_SAMPLE_BY_CATEGORY),
        config={
            "language": "Python",
            "adoption_level": "FULL",
            "locale": "en",
            "docs_language": "English",
            "docs_locale": "en",
            "language_context": {
                "preferred_human_language": "English",
                "preferred_chat_language": "English",
                "preferred_ui_language": "English",
                "preferred_local_docs_language": "English",
            },
        },
        verbose=verbose,
    )


class TestInit:
    def test_normal_init_sets_attributes(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        assert writer.output_base == tmp_path / "out"
        assert writer.mandates == list(_SAMPLE_MANDATES)
        assert writer.verbose is False

    def test_verbose_attribute(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, verbose=True)
        assert writer.verbose is True

    def test_test_output_dir_not_set_allows_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_TEST_OUTPUT_DIR", raising=False)
        writer = _make_writer(tmp_path)
        assert writer is not None

    def test_test_output_dir_set_not_repo_root_allows_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        with patch("sdd_core.utils.environment.is_repo_root", return_value=False):
            writer = _make_writer(tmp_path)
        assert writer is not None

    def test_test_output_dir_set_repo_root_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        with (
            patch("sdd_core.utils.environment.is_repo_root", return_value=True),
            pytest.raises(PermissionError, match="SDD_ISOLATION_ERROR"),
        ):
            _make_writer(tmp_path)

    def test_test_output_dir_oserror_in_is_repo_root_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        with patch(
            "sdd_core.utils.environment.is_repo_root", side_effect=OSError("disk error")
        ):
            writer = _make_writer(tmp_path)
        assert writer is not None

    def test_test_output_dir_valueerror_in_is_repo_root_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        with patch(
            "sdd_core.utils.environment.is_repo_root",
            side_effect=ValueError("bad path"),
        ):
            writer = _make_writer(tmp_path)
        assert writer is not None


class TestLog:
    def test_silent_when_not_verbose(self, tmp_path: Path, capsys) -> None:
        writer = _make_writer(tmp_path, verbose=False)
        writer._log("hello")
        assert "hello" not in capsys.readouterr().out

    def test_prints_when_verbose(self, tmp_path: Path, capsys) -> None:
        writer = _make_writer(tmp_path, verbose=True)
        writer._log("hello verbose")
        assert "hello verbose" in capsys.readouterr().out


class TestCreateDirectories:
    def test_creates_required_dirs(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        result = writer.create_directories()
        assert result is True
        assert (tmp_path / "out" / ".sdd" / "source" / "mandates").exists()
        assert (tmp_path / "out" / ".sdd" / "runtime").exists()
        assert (tmp_path / "out" / ".github" / "workflows").exists()

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        with patch("pathlib.Path.mkdir", side_effect=OSError("no space")):
            result = writer.create_directories()
        assert result is False

    def test_verbose_logs_message(self, tmp_path: Path, capsys) -> None:
        writer = _make_writer(tmp_path, verbose=True)
        writer.create_directories()
        assert "Creating directory" in capsys.readouterr().out


class TestGenerateMandatesFile:
    def test_creates_mandates_md(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.generate_mandates_file()
        assert result is True
        mandates_file = (
            tmp_path / "out" / ".sdd" / "source" / "mandates" / "mandates.md"
        )
        assert mandates_file.exists()

    def test_content_includes_mandate_ids(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_mandates_file()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "mandates" / "mandates.md"
        )
        assert "M001" in content
        assert "M002" in content

    def test_mandate_with_content_field(self, tmp_path: Path) -> None:
        writer = _make_writer(
            tmp_path,
            mandates=[
                {
                    "id": "M001",
                    "title": "T",
                    "criticality": "HIGH",
                    "content": "my content",
                }
            ],
        )
        writer.create_directories()
        writer.generate_mandates_file()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "mandates" / "mandates.md"
        )
        assert "my content" in content

    def test_mandate_with_description_fallback(self, tmp_path: Path) -> None:
        writer = _make_writer(
            tmp_path,
            mandates=[
                {
                    "id": "M001",
                    "title": "T",
                    "criticality": "HIGH",
                    "description": "desc fallback",
                }
            ],
        )
        writer.create_directories()
        writer.generate_mandates_file()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "mandates" / "mandates.md"
        )
        assert "desc fallback" in content

    def test_m011_renders_language_policy_summary(self, tmp_path: Path) -> None:
        writer = _make_writer(
            tmp_path,
            mandates=[
                {
                    "id": "M011",
                    "title": "English Language Standard",
                    "criticality": "HIGH",
                    "content": "English is mandatory for technical artifacts.",
                }
            ],
        )
        writer.create_directories()
        writer.generate_mandates_file()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "mandates" / "mandates.md"
        )
        assert "Mandatory surfaces" in content
        assert "technical_docs" in content
        assert "Contextual surfaces" in content
        assert "workspace_local_docs" in content
        assert "Guideline anchors" in content

    def test_mandate_missing_title_uses_default(self, tmp_path: Path) -> None:
        writer = _make_writer(
            tmp_path, mandates=[{"id": "M001", "criticality": "HIGH"}]
        )
        writer.create_directories()
        writer.generate_mandates_file()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "mandates" / "mandates.md"
        )
        assert "Mandate M001" in content

    def test_empty_mandates_list(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path, mandates=[])
        writer.create_directories()
        result = writer.generate_mandates_file()
        assert result is True

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = writer.generate_mandates_file()
        assert result is False


class TestGenerateGuidelinesFiles:
    def test_creates_category_files(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.generate_guidelines_files()
        assert result is True
        assert (
            tmp_path / "out" / ".sdd" / "source" / "guidelines" / "testing.md"
        ).exists()

    def test_known_category_uses_friendly_name(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_guidelines_files()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "guidelines" / "testing.md"
        )
        assert "Testing" in content

    def test_unknown_category_uses_title_case(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_guidelines_files()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "guidelines" / "custom_cat.md"
        )
        assert "Custom_Cat" in content

    def test_guideline_with_no_title_uses_default(self, tmp_path: Path) -> None:
        by_cat = {
            "testing": [
                {
                    "id": "G001",
                    "content": "c",
                    "type": "T",
                    "status": "s",
                    "customizable": True,
                }
            ]
        }
        writer = _make_writer(tmp_path, guidelines_by_category=by_cat)
        writer.create_directories()
        writer.generate_guidelines_files()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "guidelines" / "testing.md"
        )
        assert "Guideline G001" in content

    def test_guideline_not_customizable(self, tmp_path: Path) -> None:
        by_cat = {
            "testing": [
                {
                    "id": "G001",
                    "title": "T",
                    "content": "c",
                    "type": "T",
                    "status": "s",
                    "customizable": False,
                }
            ]
        }
        writer = _make_writer(tmp_path, guidelines_by_category=by_cat)
        writer.create_directories()
        writer.generate_guidelines_files()
        content = read_text_utf8(
            tmp_path / "out" / ".sdd" / "source" / "guidelines" / "testing.md"
        )
        assert "No" in content

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = writer.generate_guidelines_files()
        assert result is False


class TestGenerateSourceReadme:
    def test_creates_readme(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.generate_source_readme()
        assert result is True
        readme = tmp_path / "out" / ".sdd" / "source" / "README.md"
        assert readme.exists()

    def test_readme_contains_mandate_count(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_source_readme()
        content = read_text_utf8(tmp_path / "out" / ".sdd" / "source" / "README.md")
        assert str(len(_SAMPLE_MANDATES)) in content

    def test_readme_contains_categories(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_source_readme()
        content = read_text_utf8(tmp_path / "out" / ".sdd" / "source" / "README.md")
        assert "testing" in content.lower() or "Testing" in content

    def test_readme_contains_language_context(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_source_readme()
        content = read_text_utf8(tmp_path / "out" / ".sdd" / "source" / "README.md")
        assert "Wizard Language Context" in content
        assert "Interaction locale: en" in content
        assert "Docs locale: en" in content
        assert "Local docs: English" in content
        assert "guidelines.dsl" in content
        assert ".analysis/" in content

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = writer.generate_source_readme()
        assert result is False


class TestGenerateRuntimeReadme:
    def test_creates_readme(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        result = writer.generate_runtime_readme()
        assert result is True
        readme = tmp_path / "out" / ".sdd" / "runtime" / "README.md"
        assert readme.exists()

    def test_readme_has_pre_cache_content(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        writer.generate_runtime_readme()
        content = read_text_utf8(tmp_path / "out" / ".sdd" / "runtime" / "README.md")
        assert "Pre-Cache" in content or "pre-cache" in content.lower()
        assert "Interaction locale: en" in content
        assert "Docs locale: en" in content

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = writer.generate_runtime_readme()
        assert result is False


class TestGeneratePluginWorkspace:
    def test_success(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        mock_plugins = MagicMock(return_value={"registry_path": "/fake/plugins.yaml"})
        mock_contracts = MagicMock(return_value={"files_written": 3})
        with (
            patch(
                "sdd_cli.generators._plugins.generate_plugins_registry", mock_plugins
            ),
            patch("sdd_cli.generators._contracts.generate_contracts", mock_contracts),
        ):
            result = writer.generate_plugin_workspace()
        assert result is True

    def test_creates_analysis_subdirs(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with (
            patch(
                "sdd_cli.generators._plugins.generate_plugins_registry", return_value={}
            ),
            patch(
                "sdd_cli.generators._contracts.generate_contracts",
                return_value={"files_written": 0},
            ),
        ):
            writer.generate_plugin_workspace()
        for state in ("todo", "pending", "refined", "done"):
            assert (tmp_path / "out" / ".sdd" / "analysis" / state).exists()

    def test_creates_docs_dir(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with (
            patch(
                "sdd_cli.generators._plugins.generate_plugins_registry", return_value={}
            ),
            patch(
                "sdd_cli.generators._contracts.generate_contracts",
                return_value={"files_written": 0},
            ),
        ):
            writer.generate_plugin_workspace()
        assert (tmp_path / "out" / ".sdd" / "docs").exists()

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        writer = _make_writer(tmp_path)
        writer.create_directories()
        with patch(
            "sdd_cli.generators._plugins.generate_plugins_registry",
            side_effect=RuntimeError("boom"),
        ):
            result = writer.generate_plugin_workspace()
        assert result is False

    def test_verbose_logs_paths(self, tmp_path: Path, capsys) -> None:
        writer = _make_writer(tmp_path, verbose=True)
        writer.create_directories()
        with (
            patch(
                "sdd_cli.generators._plugins.generate_plugins_registry",
                return_value={"registry_path": "/p.yaml"},
            ),
            patch(
                "sdd_cli.generators._contracts.generate_contracts",
                return_value={"files_written": 2},
            ),
        ):
            writer.generate_plugin_workspace()
        out = capsys.readouterr().out
        assert (
            "plugin" in out.lower()
            or "contract" in out.lower()
            or "analysis" in out.lower()
        )
