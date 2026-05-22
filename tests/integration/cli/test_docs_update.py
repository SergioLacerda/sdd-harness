"""
Integration tests for `sdd docs update` command.

Covers:
- Basic discovery: valid markdown with ID produces mandate.spec output
- Blacklist exclusion: files in archive/ and spec/reality/ are skipped
- Determinism: running the command twice produces identical artifacts
- Dry-run: --dry-run flag suppresses file writes
"""

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sdd_cli.commands import docs as docs_module
from sdd_cli.commands.docs import app

pytestmark = pytest.mark.integration


def _fake_paths(tmp_path: Path) -> dict[str, Any]:
    return {
        "root": tmp_path,
        "client_build": tmp_path / "generated" / "client" / "build",
    }


def _write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal fake /docs tree with one canonical mandate file."""
    docs = tmp_path / "docs"

    _write_md(
        docs / "spec" / "canonical" / "features" / "CLEAN_ARCHITECTURE.md",
        "# Clean Architecture\n\n**ID:** M001\n\nEnforce separation of concerns.\n",
    )

    monkeypatch.setattr(docs_module, "get_sdd_paths", lambda: _fake_paths(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


runner = CliRunner()


class TestDocsUpdateDiscovery:
    """sdd docs update discovers items and writes mandate.spec / guidelines.dsl."""

    def test_discovers_mandate_and_writes_mandate_spec(self, repo: Path) -> None:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0, result.output

        mandate_spec = (
            repo / "generated" / "client" / "build" / "docs-meta" / "mandate.spec"
        )
        assert mandate_spec.exists(), "mandate.spec not created"

        content = mandate_spec.read_text(encoding="utf-8")
        assert "mandate M001" in content
        assert 'title: "Clean Architecture"' in content

    def test_writes_guidelines_dsl(self, repo: Path) -> None:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0, result.output

        guidelines_dsl = (
            repo / "generated" / "client" / "build" / "docs-meta" / "guidelines.dsl"
        )
        assert guidelines_dsl.exists(), "guidelines.dsl not created"

    def test_writes_discovery_index_json(self, repo: Path) -> None:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0, result.output

        index = (
            repo
            / "generated"
            / "client"
            / "build"
            / "docs-meta"
            / "discovery-index.json"
        )
        assert index.exists(), "discovery-index.json not created"

        import json

        data = json.loads(index.read_text(encoding="utf-8"))
        ids = [item["id"] for item in data["items"]]
        assert "M001" in ids


class TestDocsUpdateBlacklist:
    """Files under blacklisted paths must be excluded from discovery."""

    def test_archive_files_excluded(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        docs = repo / "docs"

        # A file inside archive/ should NOT be discovered.
        _write_md(
            docs / "archive" / "old_mandate.md",
            "# Old Mandate\n\n**ID:** M099\n\nObsolete rule.\n",
        )

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0, result.output

        mandate_spec = (
            repo / "generated" / "client" / "build" / "docs-meta" / "mandate.spec"
        )
        content = mandate_spec.read_text(encoding="utf-8")
        assert "M099" not in content, (
            "Blacklisted file (archive/) must not appear in mandate.spec"
        )

    def test_spec_reality_files_excluded(self, repo: Path) -> None:
        docs = repo / "docs"

        _write_md(
            docs / "spec" / "reality" / "current_state.md",
            "# Current State\n\n**ID:** M098\n\nReality capture.\n",
        )

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0, result.output

        mandate_spec = (
            repo / "generated" / "client" / "build" / "docs-meta" / "mandate.spec"
        )
        content = mandate_spec.read_text(encoding="utf-8")
        assert "M098" not in content, (
            "Blacklisted file (spec/reality/) must not appear in mandate.spec"
        )

    def test_spec_reference_files_excluded(self, repo: Path) -> None:
        docs = repo / "docs"

        _write_md(
            docs / "spec" / "reference" / "api.md",
            "# API Reference\n\n**ID:** M097\n\nAPI docs.\n",
        )

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0, result.output

        mandate_spec = (
            repo / "generated" / "client" / "build" / "docs-meta" / "mandate.spec"
        )
        content = mandate_spec.read_text(encoding="utf-8")
        assert "M097" not in content, (
            "Blacklisted file (spec/reference/) must not appear in mandate.spec"
        )


class TestDocsUpdateDeterminism:
    """Two consecutive runs on the same input must produce byte-identical artifacts."""

    def test_two_runs_produce_identical_mandate_spec(self, repo: Path) -> None:
        runner.invoke(app, ["update"])
        first = (
            repo / "generated" / "client" / "build" / "docs-meta" / "mandate.spec"
        ).read_bytes()

        runner.invoke(app, ["update"])
        second = (
            repo / "generated" / "client" / "build" / "docs-meta" / "mandate.spec"
        ).read_bytes()

        assert first == second, "mandate.spec is not deterministic across runs"

    def test_two_runs_produce_identical_discovery_index(self, repo: Path) -> None:
        runner.invoke(app, ["update"])
        first = (
            repo
            / "generated"
            / "client"
            / "build"
            / "docs-meta"
            / "discovery-index.json"
        ).read_bytes()

        runner.invoke(app, ["update"])
        second = (
            repo
            / "generated"
            / "client"
            / "build"
            / "docs-meta"
            / "discovery-index.json"
        ).read_bytes()

        assert first == second, "discovery-index.json is not deterministic across runs"


class TestDocsUpdateDryRun:
    """--dry-run must not write any files."""

    def test_dry_run_writes_no_files(self, repo: Path) -> None:
        output_dir = repo / "generated" / "client" / "build" / "docs-meta"

        result = runner.invoke(app, ["update", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "Dry-run enabled" in result.output

        # None of the three artifacts should exist after a dry-run.
        assert not (output_dir / "mandate.spec").exists(), (
            "mandate.spec must not be written on dry-run"
        )
        assert not (output_dir / "guidelines.dsl").exists(), (
            "guidelines.dsl must not be written on dry-run"
        )
        assert not (output_dir / "discovery-index.json").exists(), (
            "discovery-index.json must not be written on dry-run"
        )

    def test_dry_run_does_not_overwrite_existing_artifacts(self, repo: Path) -> None:
        """A dry-run on top of existing artifacts must leave them unchanged."""
        # Populate artifacts first.
        runner.invoke(app, ["update"])

        output_dir = repo / "generated" / "client" / "build" / "docs-meta"
        before = (output_dir / "mandate.spec").read_bytes()

        # Inject a new file to docs — dry-run should NOT pick it up into the file.
        _write_md(
            repo / "docs" / "spec" / "canonical" / "new.md",
            "# New\n\n**ID:** M002\n\nNew mandate.\n",
        )

        runner.invoke(app, ["update", "--dry-run"])
        after = (output_dir / "mandate.spec").read_bytes()

        assert before == after, "dry-run must not modify existing artifacts"
