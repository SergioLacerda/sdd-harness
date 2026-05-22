"""Unit tests for sdd_wizard.loader.ArtifactLoader and load_artifacts_safe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _make_loader(tmp_path: Path) -> Any:
    """Create an ArtifactLoader with paths set to tmp_path subtree."""
    from sdd_wizard.loader import ArtifactLoader

    # Patch get_sdd_paths to return tmp_path-based paths
    mock_paths = {
        "root": tmp_path,
        "master_compiled": tmp_path / "generated" / "master" / "compiled",
        "client_compiled": tmp_path / "generated" / "client" / "compiled",
        "client_build": tmp_path / "generated" / "client" / "build",
        "docs_meta": tmp_path / "generated" / "client" / "build" / "docs-meta",
    }
    with patch("sdd_wizard.loader.get_sdd_paths", return_value=mock_paths):
        loader = ArtifactLoader(repo_root=tmp_path)
    return loader, mock_paths


class TestArtifactLoaderLoadSourceMandate:
    def test_raises_file_not_found_when_missing(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        with pytest.raises(FileNotFoundError, match="mandate.spec"):
            loader.load_source_mandate()

    def test_loads_mandate_text(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        docs_meta = paths["docs_meta"]
        docs_meta.mkdir(parents=True)
        (docs_meta / "mandate.spec").write_text("mandate M001 {}", encoding="utf-8")

        result = loader.load_source_mandate()
        assert "M001" in result


class TestArtifactLoaderLoadSourceGuidelines:
    def test_raises_file_not_found_when_missing(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        with pytest.raises(FileNotFoundError, match="guidelines.dsl"):
            loader.load_source_guidelines()

    def test_loads_guidelines_text(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        docs_meta = paths["docs_meta"]
        docs_meta.mkdir(parents=True)
        (docs_meta / "guidelines.dsl").write_text("guideline G001 {}", encoding="utf-8")

        result = loader.load_source_guidelines()
        assert "G001" in result


class TestArtifactLoaderLoadMetadata:
    def test_raises_file_not_found_when_missing(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        with pytest.raises(FileNotFoundError, match="metadata-core.json"):
            loader.load_metadata()

    def test_loads_metadata_json(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        master_compiled = paths["master_compiled"]
        master_compiled.mkdir(parents=True)
        (master_compiled / "audit").mkdir(parents=True)
        (master_compiled / "audit" / "metadata-core.json").write_text(
            json.dumps({"version": "3.1", "items": []}), encoding="utf-8"
        )

        result = loader.load_metadata()
        assert result["version"] == "3.1"


class TestArtifactLoaderLoadCompiledMandate:
    def test_raises_when_no_compiled_files(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load_compiled_mandate()

    def test_loads_from_json_fallback(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        master_compiled = paths["master_compiled"]
        master_compiled.mkdir(parents=True)
        data = {"items": [{"id": "M001", "type": "MANDATE"}], "fingerprint": "abc"}
        (master_compiled / "governance-core.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        result = loader.load_compiled_mandate()
        assert result["items"][0]["id"] == "M001"


class TestArtifactLoaderLoadCompiledGuidelines:
    def test_raises_when_no_compiled_files(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load_compiled_guidelines()

    def test_loads_from_json_fallback(self, tmp_path: Path) -> None:
        loader, paths = _make_loader(tmp_path)
        master_compiled = paths["master_compiled"]
        master_compiled.mkdir(parents=True)
        data = {"items": [], "fingerprint": "def"}
        (master_compiled / "audit").mkdir(parents=True)
        (master_compiled / "audit" / "metadata-client-template.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        result = loader.load_compiled_guidelines()
        assert "items" in result or "fingerprint" in result


class TestLoadArtifactsSafe:
    def test_returns_false_when_files_missing(self, tmp_path: Path) -> None:
        from sdd_wizard.loader import load_artifacts_safe

        mock_paths = {
            "root": tmp_path,
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
            "client_build": tmp_path / "generated" / "client" / "build",
            "docs_meta": tmp_path / "generated" / "client" / "build" / "docs-meta",
        }
        with patch("sdd_wizard.loader.get_sdd_paths", return_value=mock_paths):
            success, data, errors = load_artifacts_safe(repo_root=tmp_path)
        assert success is False
        assert len(errors) > 0
        assert data == {}

    def test_returns_true_when_all_files_present(self, tmp_path: Path) -> None:
        from sdd_wizard.loader import load_artifacts_safe

        mock_paths = {
            "root": tmp_path,
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
            "client_build": tmp_path / "generated" / "client" / "build",
            "docs_meta": tmp_path / "generated" / "client" / "build" / "docs-meta",
        }
        # Create all required files
        docs_meta = mock_paths["docs_meta"]
        docs_meta.mkdir(parents=True)
        (docs_meta / "mandate.spec").write_text("mandate M001 {}", encoding="utf-8")
        (docs_meta / "guidelines.dsl").write_text("guideline G001 {}", encoding="utf-8")

        master_compiled = mock_paths["master_compiled"]
        master_compiled.mkdir(parents=True)
        governance_data = {"items": [], "fingerprint": "abc"}
        (master_compiled / "governance-core.json").write_text(
            json.dumps(governance_data), encoding="utf-8"
        )
        (master_compiled / "audit").mkdir(parents=True)
        (master_compiled / "audit" / "metadata-client-template.json").write_text(
            json.dumps(governance_data), encoding="utf-8"
        )
        (master_compiled / "audit" / "metadata-core.json").write_text(
            json.dumps({"version": "3.1"}), encoding="utf-8"
        )

        with patch("sdd_wizard.loader.get_sdd_paths", return_value=mock_paths):
            success, data, errors = load_artifacts_safe(repo_root=tmp_path)

        assert success is True
        assert errors == []
        assert "source" in data
        assert "compiled" in data
        assert "metadata" in data


class TestArtifactLoaderMsgpack:
    def test_loads_compiled_mandate_from_msgpack(self, tmp_path: Path) -> None:
        import msgpack

        from sdd_wizard.loader import ArtifactLoader

        mock_paths = {
            "root": tmp_path,
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
            "client_build": tmp_path / "generated" / "client" / "build",
            "docs_meta": tmp_path / "generated" / "client" / "build" / "docs-meta",
        }
        master_compiled = tmp_path / "generated" / "master" / "compiled"
        master_compiled.mkdir(parents=True)
        # Create a valid msgpack file
        data = {"items": [{"id": "M001", "type": "MANDATE"}], "fingerprint": "abc"}
        from typing import cast as tcast

        packed: bytes = tcast(bytes, msgpack.packb(data))
        (master_compiled / "governance-core.compiled.msgpack").write_bytes(packed)

        with patch("sdd_wizard.loader.get_sdd_paths", return_value=mock_paths):
            loader = ArtifactLoader(repo_root=tmp_path)

        result = loader.load_compiled_mandate()
        assert isinstance(result, dict)

    def test_loads_compiled_guidelines_from_msgpack(self, tmp_path: Path) -> None:
        import msgpack

        from sdd_wizard.loader import ArtifactLoader

        mock_paths = {
            "root": tmp_path,
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
            "client_build": tmp_path / "generated" / "client" / "build",
            "docs_meta": tmp_path / "generated" / "client" / "build" / "docs-meta",
        }
        master_compiled = tmp_path / "generated" / "master" / "compiled"
        master_compiled.mkdir(parents=True)
        data = {"items": [], "fingerprint": "abc"}
        packed: bytes = msgpack.packb(data)
        (master_compiled / "governance-client-template.compiled.msgpack").write_bytes(
            packed
        )

        with patch("sdd_wizard.loader.get_sdd_paths", return_value=mock_paths):
            loader = ArtifactLoader(repo_root=tmp_path)

        result = loader.load_compiled_guidelines()
        assert isinstance(result, dict)


class TestLoadArtifactsSafeErrors:
    def test_returns_false_on_json_decode_error(self, tmp_path: Path) -> None:
        from sdd_wizard.loader import load_artifacts_safe

        mock_paths = {
            "root": tmp_path,
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
            "client_build": tmp_path / "generated" / "client" / "build",
            "docs_meta": tmp_path / "generated" / "client" / "build" / "docs-meta",
        }

        docs_meta = tmp_path / "generated" / "client" / "build" / "docs-meta"
        docs_meta.mkdir(parents=True)
        (docs_meta / "mandate.spec").write_text("mandate M001 {}", encoding="utf-8")
        (docs_meta / "guidelines.dsl").write_text("guideline G001 {}", encoding="utf-8")

        master_compiled = tmp_path / "generated" / "master" / "compiled"
        master_compiled.mkdir(parents=True)
        # Write invalid JSON to trigger JSONDecodeError
        (master_compiled / "governance-core.json").write_text(
            "not-json{{{", encoding="utf-8"
        )

        with patch("sdd_wizard.loader.get_sdd_paths", return_value=mock_paths):
            success, data, errors = load_artifacts_safe(repo_root=tmp_path)

        assert success is False
        assert any("JSON" in e or "json" in e.lower() for e in errors)
