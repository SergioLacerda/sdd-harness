"""Unit tests for SourceSpecBootstrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper

pytestmark = pytest.mark.unit


class TestSourceSpecBootstrapperInit:
    """Tests for SourceSpecBootstrapper initialization."""

    def test_init_with_required_params(self, tmp_path: Path) -> None:
        """Should initialize with required parameters."""
        spec_path = tmp_path / "spec"
        repo_root = tmp_path
        bootstrapper = SourceSpecBootstrapper(spec_path, repo_root)
        assert bootstrapper.spec == spec_path
        assert bootstrapper.repo_root == repo_root

    def test_init_with_emit_callback(self, tmp_path: Path) -> None:
        """Should accept optional emit callback."""
        emit_fn = MagicMock()
        spec_path = tmp_path / "spec"
        repo_root = tmp_path
        bootstrapper = SourceSpecBootstrapper(spec_path, repo_root, emit_fn)
        assert bootstrapper._emit == emit_fn


class TestHasSourceSpecs:
    """Tests for has_source_specs() method."""

    def test_has_source_specs_detects_mandate_spec(self, tmp_path: Path) -> None:
        """Should detect mandate.spec file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "mandate.spec").write_text("test", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_has_source_specs_detects_mandate_md(self, tmp_path: Path) -> None:
        """Should detect mandate.md file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "mandate.md").write_text("test", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_has_source_specs_returns_false_when_missing(self, tmp_path: Path) -> None:
        """Should return False when source specs are missing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is False


class TestBootstrapMain:
    """Tests for bootstrap() method."""

    def test_bootstrap_skips_when_specs_exist(self, tmp_path: Path) -> None:
        """Should skip bootstrap when specs already exist."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "mandate.spec").write_text("existing", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Original file should be unchanged
        assert (spec_dir / "mandate.spec").read_text(encoding="utf-8") == "existing"

    def test_bootstrap_creates_spec_directory(self, tmp_path: Path) -> None:
        """Should create spec directory if it doesn't exist."""
        spec_dir = tmp_path / "spec"

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Directory should be created
        assert spec_dir.exists()

    def test_bootstrap_tries_docs_update_first(self, tmp_path: Path) -> None:
        """Should try docs update before falling back to markdown scan."""
        spec_dir = tmp_path / "spec"

        with patch(
            "sdd_core.governance.spec_bootstrapper.SourceSpecBootstrapper._bootstrap_via_docs_update",
            return_value=True,
        ) as mock_docs_update:
            bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
            bootstrapper.bootstrap()

            mock_docs_update.assert_called_once()


class TestBootstrapViaCdosUpdate:
    """Tests for _bootstrap_via_docs_update() method."""

    def test_bootstrap_via_docs_update_success(self, tmp_path: Path) -> None:
        """Should return True when docs update succeeds and creates specs."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)

        with (
            patch(
                "sdd_core.governance.spec_bootstrapper.SafeProcessRunner"
            ) as mock_runner_class,
        ):
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.run.return_value.returncode = 0

            # Create the spec file so has_source_specs returns True
            (spec_dir / "mandate.spec").write_text("generated", encoding="utf-8")

            result = bootstrapper._bootstrap_via_docs_update()
            assert result is True

    def test_bootstrap_via_docs_update_failure_on_nonzero_returncode(
        self, tmp_path: Path
    ) -> None:
        """Should return False when docs update returns non-zero."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)

        with patch(
            "sdd_core.governance.spec_bootstrapper.SafeProcessRunner"
        ) as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.run.return_value.returncode = 1

            result = bootstrapper._bootstrap_via_docs_update()
            assert result is False

    def test_bootstrap_via_docs_update_failure_on_exception(
        self, tmp_path: Path
    ) -> None:
        """Should return False when docs update raises exception."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)

        with patch(
            "sdd_core.governance.spec_bootstrapper.SafeProcessRunner"
        ) as mock_runner_class:
            mock_runner_class.side_effect = RuntimeError("Process error")

            result = bootstrapper._bootstrap_via_docs_update()
            assert result is False


class TestBootstrapFromMarkdown:
    """Tests for _bootstrap_from_markdown() method."""

    def test_bootstrap_from_markdown_extracts_mandate_ids(self, tmp_path: Path) -> None:
        """Should extract mandate IDs from markdown files."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text(
            "# Test\nSee M001 and M002 for details", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        # Should create mandate.spec with extracted IDs
        mandate_spec = spec_dir / "mandate.spec"
        assert mandate_spec.exists()
        content = mandate_spec.read_text(encoding="utf-8")
        assert "M001" in content
        assert "M002" in content

    def test_bootstrap_from_markdown_extracts_guideline_ids(
        self, tmp_path: Path
    ) -> None:
        """Should extract guideline IDs from markdown files when mandates also present."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        # Include both mandate and guideline IDs
        (docs_dir / "test.md").write_text(
            "# Test\nSee M001 and G001 and G002 for details", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        # Should create guidelines.dsl with extracted IDs
        guidelines_dsl = spec_dir / "guidelines.dsl"
        assert guidelines_dsl.exists()
        content = guidelines_dsl.read_text(encoding="utf-8")
        assert "G001" in content
        assert "G002" in content

    def test_bootstrap_from_markdown_skips_unreadable_files(
        self, tmp_path: Path
    ) -> None:
        """Should skip unreadable files without crashing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create a valid markdown file with a mandate
        (docs_dir / "valid.md").write_text("M001", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        # Should still succeed and find M001
        mandate_spec = spec_dir / "mandate.spec"
        assert mandate_spec.exists()
        assert "M001" in mandate_spec.read_text(encoding="utf-8")

    def test_bootstrap_from_markdown_skips_when_no_docs_dir(
        self, tmp_path: Path
    ) -> None:
        """Should exit gracefully when docs directory doesn't exist."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        # Should not create any files
        assert not (spec_dir / "mandate.spec").exists()
        assert not (spec_dir / "guidelines.dsl").exists()

    def test_bootstrap_from_markdown_skips_when_no_ids_found(
        self, tmp_path: Path
    ) -> None:
        """Should exit gracefully when no mandate/guideline IDs found."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text(
            "# Test with no mandates or guidelines", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        # Should not create any files
        assert not (spec_dir / "mandate.spec").exists()
        assert not (spec_dir / "guidelines.dsl").exists()
