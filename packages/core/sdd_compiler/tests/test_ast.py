"""Tests for sdd_compiler.ast — Phase 2 §4 AST layer.

Covers:
- GovernanceItem: construction and serialisation
- GovernanceAST: from_compiled_json, from_dict, to_dict, round-trip
- GovernanceAST.diff: clean, added, removed (breaking), modified (non-breaking)
- ASTDiff: summary, has_breaking_changes, is_clean
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sdd_compiler.ast import (
    AST_VERSION,
    GovernanceAST,
    GovernanceItem,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _artifact_json(items: list[dict], fingerprint: str = "deadbeef") -> dict:
    return {
        "category": "CORE",
        "version": "3.0",
        "fingerprint": fingerprint,
        "items": items,
    }


def _item_dict(
    id: str, title: str, item_type: str = "MANDATE", description: str = ""
) -> dict:
    return {
        "id": id,
        "title": title,
        "metadata": {"type": item_type, "description": description},
    }


def _make_ast(
    items: list[GovernanceItem], fingerprint: str = "fp-base"
) -> GovernanceAST:
    return GovernanceAST(
        ast_version=AST_VERSION,
        source_fingerprint=fingerprint,
        generated_at="2026-05-10T00:00:00+00:00",
        profile="master",
        items=items,
    )


def _item(
    id: str, title: str, item_type: str = "MANDATE", description: str = ""
) -> GovernanceItem:
    return GovernanceItem(
        id=id, title=title, item_type=item_type, description=description
    )


# ---------------------------------------------------------------------------
# GovernanceItem
# ---------------------------------------------------------------------------


class TestGovernanceItem:
    def test_to_dict_round_trip(self) -> None:
        item = _item("M001", "Clean Architecture", "MANDATE", "CA description")
        restored = GovernanceItem.from_dict(item.to_dict())
        assert restored.id == "M001"
        assert restored.title == "Clean Architecture"
        assert restored.item_type == "MANDATE"
        assert restored.description == "CA description"

    def test_from_dict_flat_with_type_key(self) -> None:
        # Some older artifact formats use "type" instead of "item_type"
        raw = {"id": "P001", "title": "Human Review", "type": "POLICY"}
        item = GovernanceItem.from_dict(raw)
        assert item.id == "P001"
        assert item.item_type == "POLICY"

    def test_from_dict_flat_schema(self) -> None:
        raw = {"id": "M002", "title": "TDD", "item_type": "MANDATE"}
        item = GovernanceItem.from_dict(raw)
        assert item.item_type == "MANDATE"


# ---------------------------------------------------------------------------
# GovernanceAST.from_compiled_json
# ---------------------------------------------------------------------------


class TestGovernanceASTFromCompiledJson:
    def test_loads_items_from_artifact(self) -> None:
        artifact = _artifact_json(
            [
                _item_dict("M001", "Clean Architecture"),
                _item_dict("P001", "Human Review", "POLICY"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governance-core.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            ast = GovernanceAST.from_compiled_json(path)

        assert len(ast.items) == 2
        assert ast.items[0].id == "M001"
        assert ast.items[1].item_type == "POLICY"

    def test_fingerprint_extracted_from_artifact(self) -> None:
        artifact = _artifact_json([], fingerprint="abc123")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governance-core.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            ast = GovernanceAST.from_compiled_json(path)
        assert ast.source_fingerprint == "abc123"

    def test_ast_version_set(self) -> None:
        artifact = _artifact_json([])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governance-core.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            ast = GovernanceAST.from_compiled_json(path)
        assert ast.ast_version == AST_VERSION

    def test_raises_on_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            GovernanceAST.from_compiled_json(Path("/nonexistent/path.json"))


# ---------------------------------------------------------------------------
# GovernanceAST serialisation round-trip
# ---------------------------------------------------------------------------


class TestGovernanceASTRoundTrip:
    def test_to_dict_from_dict_round_trip(self) -> None:
        original = _make_ast(
            [_item("M001", "Clean Arch"), _item("P001", "Review", "POLICY")]
        )
        restored = GovernanceAST.from_dict(original.to_dict())
        assert restored.ast_version == original.ast_version
        assert restored.source_fingerprint == original.source_fingerprint
        assert len(restored.items) == 2
        assert restored.items[0].id == "M001"

    def test_to_json_is_valid(self) -> None:
        ast = _make_ast([_item("M001", "Clean Arch")])
        parsed = json.loads(ast.to_json())
        assert parsed["ast_version"] == AST_VERSION
        assert len(parsed["items"]) == 1

    def test_item_by_id_case_insensitive(self) -> None:
        ast = _make_ast([_item("M001", "Clean Arch")])
        assert ast.item_by_id("m001") is not None
        assert ast.item_by_id("M001") is not None
        assert ast.item_by_id("X999") is None

    def test_items_by_type_filter(self) -> None:
        ast = _make_ast(
            [
                _item("M001", "A", "MANDATE"),
                _item("P001", "B", "POLICY"),
                _item("M002", "C", "MANDATE"),
            ]
        )
        mandates = ast.items_by_type("MANDATE")
        assert len(mandates) == 2
        assert all(i.item_type == "MANDATE" for i in mandates)


# ---------------------------------------------------------------------------
# GovernanceAST.diff — clean
# ---------------------------------------------------------------------------


class TestASTDiffClean:
    def test_identical_asts_produce_clean_diff(self) -> None:
        items = [_item("M001", "Clean Arch"), _item("P001", "Review", "POLICY")]
        baseline = _make_ast(items)
        current = _make_ast(items)
        diff = baseline.diff(current)
        assert diff.is_clean is True
        assert diff.has_breaking_changes is False
        assert diff.summary() == "No changes detected."


# ---------------------------------------------------------------------------
# GovernanceAST.diff — added (non-breaking)
# ---------------------------------------------------------------------------


class TestASTDiffAdded:
    def test_new_item_is_non_breaking(self) -> None:
        baseline = _make_ast([_item("M001", "Clean Arch")])
        current = _make_ast([_item("M001", "Clean Arch"), _item("M002", "TDD")])
        diff = baseline.diff(current)
        assert diff.is_clean is False
        assert diff.has_breaking_changes is False
        assert len(diff.added_items) == 1
        assert diff.added_items[0].item_id == "M002"
        assert diff.added_items[0].breaking is False

    def test_added_item_in_summary(self) -> None:
        baseline = _make_ast([])
        current = _make_ast([_item("M001", "Clean Arch")])
        diff = baseline.diff(current)
        assert "added" in diff.summary()


# ---------------------------------------------------------------------------
# GovernanceAST.diff — removed (breaking)
# ---------------------------------------------------------------------------


class TestASTDiffRemoved:
    def test_removed_item_is_breaking(self) -> None:
        baseline = _make_ast([_item("M001", "Clean Arch"), _item("M002", "TDD")])
        current = _make_ast([_item("M001", "Clean Arch")])
        diff = baseline.diff(current)
        assert diff.has_breaking_changes is True
        assert len(diff.removed_items) == 1
        assert diff.removed_items[0].item_id == "M002"
        assert diff.removed_items[0].breaking is True

    def test_removed_item_in_summary(self) -> None:
        baseline = _make_ast([_item("M001", "A")])
        current = _make_ast([])
        diff = baseline.diff(current)
        assert "breaking" in diff.summary()
        assert "removed" in diff.summary()


# ---------------------------------------------------------------------------
# GovernanceAST.diff — modified (non-breaking)
# ---------------------------------------------------------------------------


class TestASTDiffModified:
    def test_title_change_is_non_breaking(self) -> None:
        baseline = _make_ast([_item("M001", "Old Title")])
        current = _make_ast([_item("M001", "New Title")])
        diff = baseline.diff(current)
        assert diff.has_breaking_changes is False
        assert len(diff.non_breaking_changes) == 1
        assert diff.non_breaking_changes[0].field == "title"
        assert diff.non_breaking_changes[0].before == "Old Title"
        assert diff.non_breaking_changes[0].after == "New Title"

    def test_description_change_is_non_breaking(self) -> None:
        baseline = _make_ast([_item("M001", "A", description="old desc")])
        current = _make_ast([_item("M001", "A", description="new desc")])
        diff = baseline.diff(current)
        assert diff.has_breaking_changes is False
        assert any(e.field == "description" for e in diff.non_breaking_changes)

    def test_mixed_breaking_and_non_breaking(self) -> None:
        baseline = _make_ast([_item("M001", "Old"), _item("M002", "Removed")])
        current = _make_ast([_item("M001", "New"), _item("M003", "Added")])
        diff = baseline.diff(current)
        assert diff.has_breaking_changes is True  # M002 removed
        assert len(diff.added_items) == 1  # M003 added
        assert len(diff.non_breaking_changes) >= 1  # M001 title changed


# ---------------------------------------------------------------------------
# ASTDiff.to_dict
# ---------------------------------------------------------------------------


class TestASTDiffToDict:
    def test_to_dict_structure(self) -> None:
        baseline = _make_ast([_item("M001", "A"), _item("M002", "B")])
        current = _make_ast([_item("M001", "A"), _item("M003", "C")])
        diff = baseline.diff(current)
        d = diff.to_dict()
        assert "has_breaking_changes" in d
        assert "breaking_changes" in d
        assert "non_breaking_changes" in d
        assert "added_items" in d
        assert "removed_items" in d
        assert d["has_breaking_changes"] is True
