"""Tests for sdd_cli.commands.lint — pure helpers and command coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.commands.lint import (
    _check_legacy_patterns,
    _check_project_leaks,
    _collect_active_markdown_files,
    _collect_anchor_files,
    _extract_file_anchors,
    _filter_code_blocks,
    _resolve_link_target,
    _run_step,
    _slugify_anchor,
    _validate_anchor_style,
    _validate_link_fragment_style,
    _validate_markdown_anchors,
)
from sdd_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _slugify_anchor
# ---------------------------------------------------------------------------


class TestSlugifyAnchor:
    def test_basic_heading(self) -> None:
        assert _slugify_anchor("Hello World") == "hello-world"

    def test_strips_leading_hash(self) -> None:
        assert _slugify_anchor("# My Section") == "my-section"

    def test_removes_inline_code(self) -> None:
        assert _slugify_anchor("`code`") == "code"

    def test_removes_markdown_link(self) -> None:
        assert _slugify_anchor("[text](url)") == "text"

    def test_removes_html_tags(self) -> None:
        assert _slugify_anchor("<em>bold</em>") == "bold"

    def test_collapses_spaces_to_dashes(self) -> None:
        result = _slugify_anchor("one  two   three")
        assert result == "one-two-three"

    def test_strips_explicit_id_suffix(self) -> None:
        result = _slugify_anchor("My Heading {#custom-id}")
        assert "custom-id" not in result
        assert "my-heading" in result

    def test_empty_string(self) -> None:
        assert _slugify_anchor("") == ""

    def test_special_chars_stripped(self) -> None:
        result = _slugify_anchor("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_removes_asterisks_and_underscores(self) -> None:
        result = _slugify_anchor("**bold** _italic_")
        assert "*" not in result
        assert "_" not in result


# ---------------------------------------------------------------------------
# _filter_code_blocks
# ---------------------------------------------------------------------------


class TestFilterCodeBlocks:
    def test_blanks_fenced_code_content(self) -> None:
        content = "before\n```\ncode line\n```\nafter"
        result = _filter_code_blocks(content)
        assert result[0] == "before"
        assert result[2] == ""
        assert result[4] == "after"

    def test_preserves_fence_markers(self) -> None:
        content = "```\ncode\n```"
        result = _filter_code_blocks(content)
        assert result[0] == "```"
        assert result[2] == "```"

    def test_tilde_fences(self) -> None:
        content = "~~~\nhidden\n~~~"
        result = _filter_code_blocks(content)
        assert result[1] == ""

    def test_normal_lines_unchanged(self) -> None:
        content = "line1\nline2"
        result = _filter_code_blocks(content)
        assert result == ["line1", "line2"]

    def test_nested_code_toggle(self) -> None:
        content = "```\na\n```\nb\n```\nc\n```"
        result = _filter_code_blocks(content)
        assert result[1] == ""
        assert result[3] == "b"
        assert result[5] == ""


# ---------------------------------------------------------------------------
# _extract_file_anchors
# ---------------------------------------------------------------------------


class TestExtractFileAnchors:
    def test_extracts_heading_slugs(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# My Section\n## Another One\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "my-section" in anchors
        assert "another-one" in anchors

    def test_extracts_explicit_id(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# Title {#custom-id}\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "custom-id" in anchors

    def test_ignores_headings_in_code_blocks(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\n# fake heading\n```\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "fake-heading" not in anchors

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        assert _extract_file_anchors(f) == set()

    def test_multiple_explicit_ids(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("{#id-one}\n{#id-two}\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "id-one" in anchors
        assert "id-two" in anchors


# ---------------------------------------------------------------------------
# _resolve_link_target
# ---------------------------------------------------------------------------


class TestResolveLinkTarget:
    def test_empty_target_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _resolve_link_target(f, "") is None

    def test_http_link_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _resolve_link_target(f, "https://example.com") is None

    def test_mailto_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _resolve_link_target(f, "mailto:x@y.com") is None

    def test_anchor_only_returns_source_and_fragment(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        result = _resolve_link_target(f, "#my-anchor")
        assert result == (f, "my-anchor")

    def test_relative_with_fragment(self, tmp_path: Path) -> None:
        source = tmp_path / "source.md"
        target = tmp_path / "other.md"
        source.write_text("", encoding="utf-8")
        target.write_text("", encoding="utf-8")
        result = _resolve_link_target(source, "other.md#section")
        assert result is not None
        assert result[1] == "section"

    def test_relative_file_not_exists_returns_none(self, tmp_path: Path) -> None:
        source = tmp_path / "source.md"
        source.write_text("", encoding="utf-8")
        result = _resolve_link_target(source, "nonexistent.md#section")
        assert result is None

    def test_relative_no_fragment(self, tmp_path: Path) -> None:
        source = tmp_path / "source.md"
        target = tmp_path / "other.md"
        source.write_text("", encoding="utf-8")
        target.write_text("", encoding="utf-8")
        result = _resolve_link_target(source, "other.md")
        assert result is not None
        assert result[1] == ""

    def test_angle_bracket_link_stripped(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        result = _resolve_link_target(f, "<#my-anchor>")
        assert result == (f, "my-anchor")


# ---------------------------------------------------------------------------
# _validate_link_fragment_style
# ---------------------------------------------------------------------------


class TestValidateLinkFragmentStyle:
    def test_empty_target_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _validate_link_fragment_style(f, "", tmp_path) == 0

    def test_http_link_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _validate_link_fragment_style(f, "https://example.com#ok", tmp_path) == 0

    def test_no_fragment_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "other.md", tmp_path) == 0

    def test_url_encoded_fragment_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "other.md#my%20section", tmp_path) == 1

    def test_empty_slug_fragment_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "#,,,", tmp_path) == 1

    def test_valid_fragment_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "#valid-anchor", tmp_path) == 0

    def test_anchor_only_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "#my-section", tmp_path) == 0


# ---------------------------------------------------------------------------
# _validate_markdown_anchors
# ---------------------------------------------------------------------------


class TestValidateMarkdownAnchors:
    def test_valid_anchor_returns_0(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# My Section\n[link](#my-section)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 0

    def test_missing_anchor_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# My Section\n[link](#missing-anchor)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 1

    def test_cross_file_anchor_valid(self, tmp_path: Path) -> None:
        target = tmp_path / "target.md"
        target.write_text("# Target Section\n", encoding="utf-8")
        source = tmp_path / "source.md"
        source.write_text("[link](target.md#target-section)\n", encoding="utf-8")
        assert _validate_markdown_anchors([source], tmp_path) == 0

    def test_no_fragment_link_skipped(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("[link](other.md)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 0

    def test_http_link_skipped(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("[link](https://example.com#section)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 0


# ---------------------------------------------------------------------------
# _validate_anchor_style
# ---------------------------------------------------------------------------


class TestValidateAnchorStyle:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# Clean Heading\n[link](#clean-heading)\n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 0

    def test_url_encoded_fragment_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("[link](#my%20section)\n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 1

    def test_trailing_whitespace_heading_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# Heading   \n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 1

    def test_heading_in_code_block_not_flagged(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("```\n# Heading   \n```\n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 0


# ---------------------------------------------------------------------------
# _check_legacy_patterns
# ---------------------------------------------------------------------------


class TestCheckLegacyPatterns:
    def test_no_legacy_returns_0(self, tmp_path: Path) -> None:
        doc = tmp_path / "clean.md"
        doc.write_text("# Clean doc\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 0

    def test_legacy_docs_specs_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("See docs/specs/some-file.md\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_runtime_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("path is /runtime/something\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_reality_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("/REALITY/something\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_development_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("/DEVELOPMENT/foo\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_sdd_generated_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("see sdd-generated/file\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1


# ---------------------------------------------------------------------------
# _check_project_leaks
# ---------------------------------------------------------------------------


class TestCheckProjectLeaks:
    def test_no_leaks_returns_0(self, tmp_path: Path) -> None:
        core = tmp_path / "core"
        core.mkdir()
        (core / "doc.md").write_text("# Clean\n", encoding="utf-8")
        assert _check_project_leaks(tmp_path, tmp_path) == 0

    def test_rpg_narrative_leak_returns_1(self, tmp_path: Path) -> None:
        core = tmp_path / "core"
        core.mkdir()
        (core / "doc.md").write_text("rpg-narrative-server\n", encoding="utf-8")
        assert _check_project_leaks(tmp_path, tmp_path) == 1

    def test_game_master_leak_returns_1(self, tmp_path: Path) -> None:
        core = tmp_path / "core"
        core.mkdir()
        (core / "doc.md").write_text("game-master rules\n", encoding="utf-8")
        assert _check_project_leaks(tmp_path, tmp_path) == 1

    def test_no_core_dir_returns_0(self, tmp_path: Path) -> None:
        assert _check_project_leaks(tmp_path, tmp_path) == 0


# ---------------------------------------------------------------------------
# _collect_active_markdown_files
# ---------------------------------------------------------------------------


class TestCollectActiveMarkdownFiles:
    def test_collects_docs_markdown(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert any(f.name == "guide.md" for f in files)

    def test_excludes_archive(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        archive = docs / "archive"
        archive.mkdir(parents=True)
        (archive / "old.md").write_text("", encoding="utf-8")
        (docs / "current.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert not any(f.name == "old.md" for f in files)
        assert any(f.name == "current.md" for f in files)

    def test_collects_readme(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert any(f.name == "README.md" for f in files)

    def test_collects_readme_detailed(self, tmp_path: Path) -> None:
        (tmp_path / "readme-detailed.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert any(f.name == "readme-detailed.md" for f in files)


# ---------------------------------------------------------------------------
# _collect_anchor_files
# ---------------------------------------------------------------------------


class TestCollectAnchorFiles:
    def test_validate_all_anchors_true(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "doc.md").write_text("", encoding="utf-8")
        files = _collect_anchor_files(tmp_path, validate_all_anchors=True)
        assert any(f.name == "doc.md" for f in files)

    def test_validate_all_false_wizard_dir_not_exists(self, tmp_path: Path) -> None:
        files = _collect_anchor_files(tmp_path, validate_all_anchors=False)
        assert files == []

    def test_validate_all_false_wizard_candidates(self, tmp_path: Path) -> None:
        wizard_dir = (
            tmp_path
            / "docs"
            / "spec"
            / "reality"
            / "implementation-analyses"
            / "wizard"
        )
        wizard_dir.mkdir(parents=True)
        start_here = wizard_dir / "START_HERE_FOR_DOCUMENTATION.md"
        start_here.write_text("", encoding="utf-8")
        files = _collect_anchor_files(tmp_path, validate_all_anchors=False)
        assert any(f.name == "START_HERE_FOR_DOCUMENTATION.md" for f in files)


# ---------------------------------------------------------------------------
# _run_step
# ---------------------------------------------------------------------------


class TestRunStep:
    def test_returns_0_on_success(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True, returncode=0)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_step("mycheck", ["echo", "ok"], fix=False)
        assert result == 0

    def test_returns_nonzero_on_failure(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=False, returncode=1)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_step("mycheck", ["false"], fix=False)
        assert result == 1

    def test_fix_mode_prints_warn_not_error(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=False, returncode=1)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            _run_step("mycheck", ["false"], fix=True)


# ---------------------------------------------------------------------------
# spec command
# ---------------------------------------------------------------------------


class TestSpecCommand:
    def test_no_canonical_dir_exits_1(self, tmp_path: Path) -> None:
        with patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["lint", "spec"])
        assert result.exit_code == 1
        assert "Canonical directory not found" in result.output

    def test_clean_canonical_dir_exits_0(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        with patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["lint", "spec", "--no-strict-anchor-style"])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_legacy_pattern_in_canonical_exits_1(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        (canonical / "doc.md").write_text("docs/specs/something\n", encoding="utf-8")
        with patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["lint", "spec"])
        assert result.exit_code == 1

    def test_anchor_errors_exits_1(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        doc = tmp_path / "docs" / "README.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("[broken](#nonexistent)\n", encoding="utf-8")
        with patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "spec",
                    "--validate-all-anchors",
                    "--no-strict-anchor-style",
                ],
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# _validate_markdown_anchors — empty-fragment branch (line 144)
# ---------------------------------------------------------------------------


class TestValidateMarkdownAnchorsEmptyFragment:
    def test_link_with_existing_target_no_fragment_returns_0(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "target.md"
        target.write_text("# Section\n", encoding="utf-8")
        source = tmp_path / "source.md"
        source.write_text("[link](target.md)\n", encoding="utf-8")
        assert _validate_markdown_anchors([source], tmp_path) == 0


# ---------------------------------------------------------------------------
# _run_ruff
# ---------------------------------------------------------------------------


class TestRunRuff:
    def test_run_ruff_no_fix_all_pass(self) -> None:
        from sdd_cli.commands.lint import _run_ruff

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True, returncode=0)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_ruff(fix=False)
        assert result is False

    def test_run_ruff_no_fix_check_fails(self) -> None:
        from sdd_cli.commands.lint import _run_ruff

        call_count = [0]

        mock_runner = MagicMock()

        def alternate_results(cmd, **kwargs):  # noqa: ANN001
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(success=False, returncode=1)
            return MagicMock(success=True, returncode=0)

        mock_runner.run.side_effect = alternate_results
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_ruff(fix=False)
        assert result is True

    def test_run_ruff_fix_mode(self) -> None:
        from sdd_cli.commands.lint import _run_ruff

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True, returncode=0)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_ruff(fix=True)
        assert result is False
        calls = mock_runner.run.call_args_list
        assert any("--fix" in str(c) for c in calls)


# ---------------------------------------------------------------------------
# lint run command
# ---------------------------------------------------------------------------


class TestLintRunCommand:
    def _make_mock_runner(self, returncode: int = 0) -> MagicMock:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(
            success=(returncode == 0), returncode=returncode
        )
        return mock_runner

    def test_run_all_pass_exits_0(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "run",
                    "--skip-mypy",
                    "--skip-bandit",
                ],
            )
        assert result.exit_code == 0

    def test_run_step_failure_exits_1(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(1)
        with (
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "run",
                    "--skip-mypy",
                    "--skip-bandit",
                    "--skip-spec",
                ],
            )
        assert result.exit_code == 1

    def test_run_with_fix_flag(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "run",
                    "--fix",
                    "--skip-mypy",
                    "--skip-bandit",
                    "--skip-spec",
                ],
            )
        assert result.exit_code == 0

    def test_run_includes_mypy_by_default(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(
                app,
                ["lint", "run", "--skip-bandit", "--skip-spec"],
            )
        assert result.exit_code == 0
        calls_str = str(mock_runner.run.call_args_list)
        assert "mypy" in calls_str

    def test_run_includes_bandit_by_default(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(
                app,
                ["lint", "run", "--skip-mypy", "--skip-spec"],
            )
        assert result.exit_code == 0
        calls_str = str(mock_runner.run.call_args_list)
        assert "bandit" in calls_str
