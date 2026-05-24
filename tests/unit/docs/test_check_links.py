from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "tools" / "docs" / "check_links.py"
    spec = importlib.util.spec_from_file_location("check_links", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_resolve_target_files_filters_to_changed_docs(tmp_path: Path) -> None:
    m = _load_module()
    repo = tmp_path
    docs = repo / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("[x](./missing.md)\n", encoding="utf-8")
    (docs / "b.md").write_text("[x](./missing.md)\n", encoding="utf-8")
    (repo / "README.md").write_text("x\n", encoding="utf-8")

    files = m._resolve_target_files(
        repo,
        docs,
        ["docs/a.md", "README.md", "docs/missing.md"],
    )
    assert [p.relative_to(repo).as_posix() for p in files] == ["docs/a.md"]


def test_resolve_target_files_all_docs_when_no_changed(tmp_path: Path) -> None:
    m = _load_module()
    repo = tmp_path
    docs = repo / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("x\n", encoding="utf-8")
    (docs / "b.md").write_text("x\n", encoding="utf-8")

    files = m._resolve_target_files(repo, docs, [])
    assert sorted(p.name for p in files) == ["a.md", "b.md"]
