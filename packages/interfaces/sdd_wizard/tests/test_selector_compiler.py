from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdd_wizard.orchestration.wizard.selector_compiler import SelectorCompiler


def _write_repo_fixture(
    tmp_path: Path,
    *,
    metadata: dict[str, object],
    mandates_text: str,
) -> Path:
    (tmp_path / ".sdd" / "source" / "mandates").mkdir(parents=True)
    (tmp_path / ".sdd" / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (tmp_path / ".sdd" / "source" / "mandates" / "mandates.md").write_text(
        mandates_text,
        encoding="utf-8",
    )
    return tmp_path


def _write_assets(tmp_path: Path) -> Path:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    for name in ("index.html", "selector.js", "style.css"):
        (asset_dir / name).write_text(name, encoding="utf-8")
    return asset_dir


def test_selector_compiler_builds_payload(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()
    assert payload["version"] == "1.0"
    item = payload["items"][0]
    assert item["id"] == "M001"
    assert item["mandatory"] is True
    assert item["depends_on"] == []


def test_selector_compiler_rejects_duplicate_sections(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

First description.

## M001: Clean Architecture

Second description.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    with pytest.raises(ValueError, match="Duplicate mandate section"):
        compiler.build_payload()


def test_selector_compiler_rejects_unknown_dependencies(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated.

**Depends on:** M999
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    with pytest.raises(ValueError, match="Unknown selector dependency ids: M999"):
        compiler.build_payload()


def test_selector_compiler_build_site_writes_assets(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    output_dir = tmp_path / "site" / "selector"
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    compiler.build_site(output_dir)
    assert (output_dir / "data.json").exists()
    assert (output_dir / "index.html").read_text(encoding="utf-8") == "index.html"


def test_selector_compiler_build_site_with_packaged_assets_has_import_and_export(
    tmp_path: Path,
) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    output_dir = tmp_path / "site" / "selector"
    compiler = SelectorCompiler(repo_root=repo_root)

    compiler.build_site(output_dir)

    html = (output_dir / "index.html").read_text(encoding="utf-8")
    js = (output_dir / "selector.js").read_text(encoding="utf-8")
    assert "Import JSON" in html
    assert "import-file" in html
    assert "function importSelectionFile" in js
    assert "resolved: [...resolved].sort()" in js


# ---------------------------------------------------------------------------
# Guideline support
# ---------------------------------------------------------------------------

_GUIDELINES_DSL = """
guideline G01 {
  type: HARD
  title: "Use typed interfaces"
  description: "All public APIs must use typed interfaces."
  category: quality
  tags: ["typing", "api"]
}

guideline G02 {
  type: SOFT
  title: "Prefer immutable data"
  description: "Prefer immutable data structures where possible."
  category: style
  tags: ["immutability"]
}
""".strip()


def _write_repo_fixture_with_guidelines(
    tmp_path: Path,
    *,
    metadata: dict[str, object],
    mandates_text: str,
    guidelines_dsl: str = _GUIDELINES_DSL,
) -> Path:
    repo_root = _write_repo_fixture(
        tmp_path, metadata=metadata, mandates_text=mandates_text
    )
    (repo_root / ".sdd" / "source" / "guidelines.dsl").write_text(
        guidelines_dsl, encoding="utf-8"
    )
    return repo_root


def test_selector_compiler_includes_guideline_items(tmp_path: Path) -> None:
    """Guidelines from DSL are included as separate items with item_type='guideline'."""
    repo_root = _write_repo_fixture_with_guidelines(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    items = payload["items"]
    ids = {item["id"] for item in items}
    assert "M001" in ids
    assert "G01" in ids
    assert "G02" in ids

    g01 = next(i for i in items if i["id"] == "G01")
    assert g01["item_type"] == "guideline"
    assert g01["mandatory"] is True
    assert g01["title"] == "Use typed interfaces"

    g02 = next(i for i in items if i["id"] == "G02")
    assert g02["item_type"] == "guideline"
    assert g02["mandatory"] is False


def test_selector_compiler_mandate_item_type_is_mandate(tmp_path: Path) -> None:
    """Mandate items always carry item_type='mandate'."""
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    m001 = next(i for i in payload["items"] if i["id"] == "M001")
    assert m001["item_type"] == "mandate"


def test_selector_compiler_mixed_payload_no_duplicate_ids(tmp_path: Path) -> None:
    """Mixed mandate+guideline payload has no duplicate IDs."""
    repo_root = _write_repo_fixture_with_guidelines(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture", "M002": "Testing"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.

## M002: Testing

All changes must include tests.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert len(ids) == len(set(ids)), "Duplicate IDs in mixed payload"
    assert set(ids) == {"M001", "M002", "G01", "G02"}


def test_selector_compiler_no_guidelines_dsl_omits_guideline_items(
    tmp_path: Path,
) -> None:
    """When guidelines.dsl is absent, only mandates are included."""
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert ids == ["M001"]
