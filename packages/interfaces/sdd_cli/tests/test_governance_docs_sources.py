"""Tests for docs-first governance source registry validation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from sdd_cli.services.governance_docs_sources import (
    generate_runtime_handbook,
    lookup_runtime_handbook,
    validate_governance_sources,
)


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _runtime(root: Path) -> None:
    _write_json(root / ".sdd" / "metadata.json", {"mandates": {"M001": "One"}})
    _write_json(
        root / ".sdd" / "compiled" / "governance-core.json",
        {"items": [{"id": "M001", "type": "MANDATE"}]},
    )
    _write_json(
        root / ".sdd" / "compiled" / "governance-client.json",
        {"items": [{"id": "G01", "type": "GUIDELINE"}]},
    )


def _registry(root: Path, sources: list[dict[str, object]]) -> None:
    path = root / "docs" / "spec" / "canonical" / "governance-sources.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump({"schema_version": "1", "sources": sources}, sort_keys=False),
        encoding="utf-8",
    )


def test_validate_governance_sources_passes_for_matching_runtime(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    (tmp_path / "docs" / "m001.md").parent.mkdir()
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is True
    assert report.mandate_ids == ["M001"]
    assert report.guideline_ids == ["G01"]


def test_validate_governance_sources_detects_duplicate_active_id(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A", encoding="utf-8")
    (docs / "b.md").write_text("# B", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {"id": "M001", "type": "mandate", "status": "active", "path": "docs/a.md"},
            {"id": "M001", "type": "mandate", "status": "active", "path": "docs/b.md"},
            {"id": "G01", "type": "guideline", "status": "active", "path": "docs/a.md"},
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("duplicate active mandate id M001" in error for error in report.errors)


def test_validate_governance_sources_detects_runtime_drift(tmp_path: Path) -> None:
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "m001.md").write_text("# M001", encoding="utf-8")
    _registry(
        tmp_path,
        [{"id": "M001", "type": "mandate", "status": "active", "path": "docs/m001.md"}],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("guideline registry drift" in error for error in report.errors)


def test_generate_runtime_handbook_writes_index_and_item(tmp_path: Path) -> None:
    _runtime(tmp_path)
    source = tmp_path / "docs" / "cognition" / "context-loading" / "context_flow.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "---",
                "governance_source:",
                "  id: HBK-CONTEXT-LOADING",
                "  title: Context Flow",
                "  summary: Select minimal relevant context.",
                "---",
                "# Context Flow",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "HBK-CONTEXT-LOADING",
                "type": "handbook",
                "kind": "decision_model",
                "status": "active",
                "path": "docs/cognition/context-loading/context_flow.md",
                "refs": ["M001"],
                "task_types": ["planning"],
                "operation_phases": ["context_loading"],
                "load_policy": {"mode": "selective", "max_tokens": 700},
                "outputs": [".sdd/source/handbook/context-loading/context-flow.yaml"],
            },
        ],
    )

    written = generate_runtime_handbook(tmp_path)

    assert tmp_path / ".sdd/source/handbook/index.yaml" in written
    item = yaml.safe_load(
        (tmp_path / ".sdd/source/handbook/context-loading/context-flow.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert item["id"] == "HBK-CONTEXT-LOADING"
    assert item["source_doc"] == "docs/cognition/context-loading/context_flow.md"


def test_generate_runtime_handbook_skips_when_registry_is_absent(
    tmp_path: Path,
) -> None:
    existing = tmp_path / ".sdd/source/handbook/index.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("schema_version: '1'\nitems: []\n", encoding="utf-8")

    written = generate_runtime_handbook(tmp_path)

    assert written == []
    assert existing.read_text(encoding="utf-8") == "schema_version: '1'\nitems: []\n"


def test_validate_governance_sources_detects_missing_handbook_output(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    source = tmp_path / "docs" / "cognition" / "context-loading" / "context_flow.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Context Flow", encoding="utf-8")
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "HBK-CONTEXT-LOADING",
                "type": "handbook",
                "status": "active",
                "path": "docs/cognition/context-loading/context_flow.md",
                "refs": ["M001"],
                "load_policy": {"max_tokens": 700},
                "outputs": [".sdd/source/handbook/context-loading/context-flow.yaml"],
            },
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("handbook runtime output missing" in error for error in report.errors)


def test_validate_governance_sources_detects_handbook_id_collision(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "m001.md").write_text("# M001", encoding="utf-8")
    (docs / "g01.md").write_text("# G01", encoding="utf-8")
    (docs / "hbk.md").write_text("# Handbook", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "M001",
                "type": "handbook",
                "status": "active",
                "path": "docs/hbk.md",
                "task_types": ["planning"],
                "load_policy": {"max_tokens": 700},
            },
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("handbook id collision" in error for error in report.errors)


def test_lookup_runtime_handbook_matches_generated_index(tmp_path: Path) -> None:
    test_generate_runtime_handbook_writes_index_and_item(tmp_path)

    report = lookup_runtime_handbook(
        tmp_path,
        task_type="planning",
        mandate_refs=["M001"],
        operation_phase="context_loading",
    )

    assert report.status == "matched"
    assert report.diagnostic == "handbook_match=1"
    assert report.matches[0]["id"] == "HBK-CONTEXT-LOADING"


def test_lookup_runtime_handbook_reports_none_without_docs_scan(tmp_path: Path) -> None:
    test_generate_runtime_handbook_writes_index_and_item(tmp_path)

    report = lookup_runtime_handbook(tmp_path, task_type="diagnosis")

    assert report.status == "none"
    assert report.diagnostic == "handbook_match=none"
