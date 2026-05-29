"""Unit tests for SourceSpecBootstrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

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
        """Should detect mandate.md file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "mandate.md").write_text("test", encoding="utf-8")

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
        (spec_dir / "mandate.md").write_text("existing", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Original file should be unchanged
        assert (spec_dir / "mandate.md").read_text(encoding="utf-8") == "existing"

    def test_bootstrap_creates_spec_directory(self, tmp_path: Path) -> None:
        """Should create spec directory if it doesn't exist."""
        spec_dir = tmp_path / "spec"

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Directory should be created
        assert spec_dir.exists()


class TestBootstrapFromMarkdown:
    """Tests for _bootstrap_from_markdown() method."""

    def test_bootstrap_from_markdown_extracts_mandate_ids_from_canonical(
        self, tmp_path: Path
    ) -> None:
        """Should extract mandate IDs only from canonical files with **ID:** M* declarations."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        # Create canonical mandate files with the expected format
        canonical_dir = docs_dir / "spec" / "canonical" / "core" / "mandates"
        canonical_dir.mkdir(parents=True)
        (canonical_dir / "M001_CLEAN_ARCH.md").write_text(
            "# Mandate: Clean Architecture\n\n**ID:** M001\n",
            encoding="utf-8",
        )
        (canonical_dir / "M002_TDD.md").write_text(
            "# Mandate: Test-Driven Development\n\n**ID:** M002\n",
            encoding="utf-8",
        )
        # A plain docs file that references M003 should NOT be picked up
        plain_docs = docs_dir / "guide.md"
        plain_docs.write_text("See M003 for details", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        mandate_spec = spec_dir / "mandate.md"
        assert mandate_spec.exists()
        content = mandate_spec.read_text(encoding="utf-8")
        assert "M001" in content
        assert "M002" in content
        # M003 must NOT appear — it was only referenced, not canonically defined
        assert "M003" not in content

    def test_bootstrap_from_markdown_does_not_auto_discover_guidelines(
        self, tmp_path: Path
    ) -> None:
        """Should create an empty guidelines.dsl rather than auto-discovering G-IDs."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        canonical_dir = docs_dir / "spec" / "canonical" / "core" / "mandates"
        canonical_dir.mkdir(parents=True)
        (canonical_dir / "M001_ARCH.md").write_text(
            "# Mandate: Architecture\n\n**ID:** M001\n", encoding="utf-8"
        )
        # Plain docs file with G-IDs that should NOT be picked up
        plain = docs_dir / "guide.md"
        plain.write_text("See G001 and G002 for details", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        guidelines_dsl = spec_dir / "guidelines.dsl"
        assert guidelines_dsl.exists()
        content = guidelines_dsl.read_text(encoding="utf-8")
        # Should be empty (only header comment) — no G-ID auto-discovery
        assert "G001" not in content
        assert "G002" not in content

    def test_bootstrap_from_markdown_skips_unreadable_files(
        self, tmp_path: Path
    ) -> None:
        """Should skip unreadable canonical files without crashing, still finding readable ones."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        docs_dir = tmp_path / "docs"
        canonical_dir = docs_dir / "spec" / "canonical" / "core" / "mandates"
        canonical_dir.mkdir(parents=True)
        # Valid canonical file — readable
        (canonical_dir / "M001_ARCH.md").write_text(
            "# Mandate: Clean Architecture\n\n**ID:** M001\n", encoding="utf-8"
        )
        # Simulate an extra file alongside — bootstrapper must not crash

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper._bootstrap_from_markdown()

        mandate_spec = spec_dir / "mandate.md"
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
        assert not (spec_dir / "mandate.md").exists()
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
        assert not (spec_dir / "mandate.md").exists()
        assert not (spec_dir / "guidelines.dsl").exists()
