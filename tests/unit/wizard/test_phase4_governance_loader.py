"""Unit tests for sdd_wizard.orchestration.phase4_governance_loader.GovernanceLoader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _make_loader(
    tmp_path: Path,
    core_data: dict[str, Any] | None = None,
    client_data: dict[str, Any] | None = None,
    verbose: bool = False,
) -> Any:
    from sdd_wizard.orchestration.phase4_governance_loader import GovernanceLoader

    core_path = tmp_path / "governance-core.json"
    client_path = tmp_path / "governance-client.json"

    if core_data is not None:
        core_path.write_text(json.dumps(core_data), encoding="utf-8")
    if client_data is not None:
        client_path.write_text(json.dumps(client_data), encoding="utf-8")

    return GovernanceLoader(
        governance_core_path=core_path,
        governance_client_path=client_path,
        verbose=verbose,
    )


CORE_WITH_MANDATES = {
    "items": [
        {
            "id": "M001",
            "type": "MANDATE",
            "title": "Use type hints",
            "category": "architecture",
        },
        {"id": "M002", "type": "MANDATE", "title": "Write tests"},
    ]
}

CORE_WITH_GUIDELINES = {
    "items": [
        {
            "id": "G001",
            "type": "GUIDELINE",
            "title": "Conventional commits",
            "category": "git",
        },
        {
            "id": "G002",
            "type": "GUIDELINE",
            "title": "100% test coverage",
            "category": "testing",
        },
    ]
}

MIXED_CORE = {
    "items": [
        {"id": "M001", "type": "MANDATE", "title": "Use type hints"},
        {
            "id": "G001",
            "type": "GUIDELINE",
            "title": "Conventional commits",
            "category": "git",
        },
    ]
}


class TestGovernanceLoaderInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        assert loader is not None

    def test_initial_mandates_empty(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        assert loader.mandates == []

    def test_initial_guidelines_empty(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        assert loader.guidelines == {}


class TestGovernanceLoaderLoad:
    def test_returns_false_when_no_core_file(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        result = loader.load()
        assert result is False

    def test_returns_true_when_core_exists(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data=CORE_WITH_MANDATES)
        result = loader.load()
        assert result is True

    def test_loads_mandates(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data=CORE_WITH_MANDATES)
        loader.load()
        assert len(loader.mandates) == 2

    def test_loads_guidelines(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data=CORE_WITH_GUIDELINES)
        loader.load()
        assert "G001" in loader.guidelines
        assert "G002" in loader.guidelines

    def test_organizes_by_category(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data=CORE_WITH_GUIDELINES)
        loader.load()
        assert "git" in loader.guidelines_by_category
        assert "testing" in loader.guidelines_by_category

    def test_loads_mixed_core(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data=MIXED_CORE)
        loader.load()
        assert len(loader.mandates) == 1
        assert "G001" in loader.guidelines

    def test_deduplicates_mandates(self, tmp_path: Path) -> None:
        core = {"items": [{"id": "M001", "type": "MANDATE", "title": "First"}]}
        client = {"items": [{"id": "M001", "type": "MANDATE", "title": "Duplicate"}]}
        loader = _make_loader(tmp_path, core_data=core, client_data=client)
        loader.load()
        # M001 should appear only once
        assert len([m for m in loader.mandates if m["id"] == "M001"]) == 1

    def test_loads_client_guidelines(self, tmp_path: Path) -> None:
        core: dict[str, Any] = {"items": []}
        client = {
            "items": [
                {"id": "G010", "title": "Client guideline", "category": "security"}
            ]
        }
        loader = _make_loader(tmp_path, core_data=core, client_data=client)
        loader.load()
        assert "G010" in loader.guidelines

    def test_verbose_logs(self, tmp_path: Path, capsys: Any) -> None:
        loader = _make_loader(tmp_path, core_data=CORE_WITH_MANDATES, verbose=True)
        loader.load()
        captured = capsys.readouterr()
        assert "Loading" in captured.out or "mandates" in captured.out.lower()


class TestNormalizeItemType:
    def test_mandate_string_normalized(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        result = loader._normalize_item_type({"type": "mandate"})
        assert result == "MANDATE"

    def test_guideline_string_normalized(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        result = loader._normalize_item_type({"type": "GUIDELINE"})
        assert result == "GUIDELINE"

    def test_unknown_type_defaults_to_empty(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        result = loader._normalize_item_type({"type": "UNKNOWN"})
        assert result == ""

    def test_id_starting_with_m_infers_mandate(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        result = loader._normalize_item_type({"id": "M001", "type": "RANDOM"})
        assert result == "MANDATE"

    def test_id_starting_with_g_infers_guideline(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        result = loader._normalize_item_type({"id": "G001", "type": "RANDOM"})
        assert result == "GUIDELINE"

    def test_default_type_used_when_type_missing(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        result = loader._normalize_item_type({"id": "X001"}, default_type="MANDATE")
        assert result == "MANDATE"

    def test_items_without_id_skipped(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path, core_data={"items": []})
        # item with empty id should be skipped in _ingest_items
        seen: set[str] = set()
        loader._ingest_items([{"type": "MANDATE"}], seen)
        assert loader.mandates == []
