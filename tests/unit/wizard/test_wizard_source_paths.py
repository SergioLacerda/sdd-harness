from pathlib import Path

import pytest

from sdd_wizard.loader import ArtifactLoader
from sdd_wizard.orchestration import wizard
from sdd_wizard.orchestration.wizard.phase1_generator import Phase1Generator


def test_phase1_resolves_mandate_from_canonical_source_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)
    mandate_file = docs_meta_dir / "mandate.spec"
    mandate_file.write_text("- [M001] **Test**", encoding="utf-8")

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    generator = Phase1Generator(tmp_path / "packages", tmp_path / "out")
    resolved = generator._resolve_source_file("mandate.spec")

    assert resolved == mandate_file


def test_phase1_missing_source_has_canonical_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    generator = Phase1Generator(tmp_path / "packages", tmp_path / "out")
    resolved = generator._resolve_source_file("mandate.spec")

    assert resolved is None
    assert generator.last_error is not None
    assert str(docs_meta_dir / "mandate.spec") in generator.last_error
    assert "sdd docs update" in generator.last_error


def test_phase1_run_returns_root_cause_when_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    generator = Phase1Generator(tmp_path / "packages", tmp_path / "out")
    result = generator.run()

    assert result["success"] is False
    assert "Searched:" in result["error"]


def test_phase1_run_materializes_editable_mandate_in_client_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)
    mandate_content = """mandate M001 {
    title: \"Keep tests close\"
    description: \"Require tests near implementation\"
    type: \"MANDATE\"
    category: \"testing\"
    rationale: \"Improves maintainability\"
}
"""
    guidelines_content = """guideline G001 {
    title: \"Prefer explicit naming\"
    description: \"Use clear names\"
    type: \"GUIDELINE\"
    category: \"style\"
}
"""
    (docs_meta_dir / "mandate.spec").write_text(mandate_content, encoding="utf-8")
    (docs_meta_dir / "guidelines.dsl").write_text(guidelines_content, encoding="utf-8")

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    output_path = tmp_path / "generated" / "client" / "build" / "phase-1-choices"
    generator = Phase1Generator(tmp_path / "packages", output_path)

    result = generator.run()

    mandate_output = docs_meta_dir / "mandate.spec"
    assert result["success"] is True
    assert result["mandate_spec_output"] == str(mandate_output)
    assert mandate_output.read_text(encoding="utf-8") == mandate_content


def test_phase1_prefers_existing_local_mandate_over_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)
    (docs_meta_dir / "mandate.spec").write_text(
        'mandate M001 { title: "Generated" }', encoding="utf-8"
    )

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    output_path = tmp_path / "generated" / "client" / "build" / "phase-1-choices"
    local_mandate = output_path.parent / "mandate.spec"
    local_mandate.parent.mkdir(parents=True, exist_ok=True)
    local_mandate.write_text('mandate M001 { title: "Local" }', encoding="utf-8")

    generator = Phase1Generator(tmp_path / "packages", output_path)
    resolved = generator._resolve_source_file("mandate.spec")

    assert resolved == docs_meta_dir / "mandate.spec"


def test_phase1_materialize_wrapper_resolves_docs_meta_mandate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)
    source_mandate = docs_meta_dir / "mandate.spec"
    source_mandate.write_text('mandate M001 { title: "Generated" }', encoding="utf-8")

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    output_path = tmp_path / "generated" / "client" / "build" / "phase-1-choices"
    generator = Phase1Generator(tmp_path / "packages", output_path)
    materialized = generator._materialize_local_source_file("mandate.spec")

    assert materialized == source_mandate


def test_phase1_materializes_mandate_even_if_parse_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)

    # Invalid for current parser regex, but should still be materialized to client build.
    (docs_meta_dir / "mandate.spec").write_text(
        "- [M001] Markdown mandate format", encoding="utf-8"
    )
    (docs_meta_dir / "guidelines.dsl").write_text(
        'guideline G001 { title: "X" }', encoding="utf-8"
    )

    monkeypatch.setattr(
        wizard.phase1_generator, "get_sdd_paths", lambda: {"docs_meta": docs_meta_dir}
    )

    output_path = tmp_path / "generated" / "client" / "build" / "phase-1-choices"
    generator = Phase1Generator(tmp_path / "packages", output_path)

    result = generator.run()

    assert result["success"] is False


def test_artifact_loader_reads_source_files_from_canonical_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)
    (docs_meta_dir / "mandate.spec").write_text("mandate", encoding="utf-8")
    (docs_meta_dir / "guidelines.dsl").write_text("guidelines", encoding="utf-8")

    monkeypatch.setattr(
        "sdd_wizard.loader.get_sdd_paths",
        lambda: {
            "root": tmp_path,
            "docs_meta": docs_meta_dir,
            "client_build": tmp_path / "generated" / "client" / "build",
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
        },
    )

    loader = ArtifactLoader()
    assert loader.load_source_mandate() == "mandate"
    assert loader.load_source_guidelines() == "guidelines"


def test_artifact_loader_missing_file_error_uses_canonical_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_meta_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    docs_meta_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "sdd_wizard.loader.get_sdd_paths",
        lambda: {
            "root": tmp_path,
            "docs_meta": docs_meta_dir,
            "client_build": tmp_path / "generated" / "client" / "build",
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
        },
    )

    loader = ArtifactLoader()
    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load_source_mandate()

    error_text = str(exc_info.value)
    assert str(docs_meta_dir / "mandate.spec") in error_text
    assert "/core/mandate.spec" not in error_text


def test_phase1_canonical_only_fallback_to_markdown_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_dir = tmp_path / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "mandate.md").write_text(
        "# M001: Canonical Mandate\n", encoding="utf-8"
    )
    (canonical_dir / "guidelines.md").write_text(
        "# G001: Canonical Guideline\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        wizard.phase1_generator,
        "get_sdd_paths",
        lambda: {
            "docs_meta": tmp_path / "missing-docs-meta",
            "source_spec": canonical_dir,
        },
    )

    output_path = tmp_path / "generated" / "client" / "build" / "phase-1-choices"
    generator = Phase1Generator(tmp_path / "packages", output_path)

    result = generator.run()

    assert result["success"] is True
    assert result["mandate_count"] == 1
    assert result["guideline_count"] == 1


def test_phase1_resolves_mandate_md_when_mandate_spec_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_dir = tmp_path / "canonical"
    canonical_dir.mkdir(parents=True)
    mandate_md = canonical_dir / "mandate.md"
    mandate_md.write_text("# M001: Markdown Fallback\n", encoding="utf-8")

    monkeypatch.setattr(
        wizard.phase1_generator,
        "get_sdd_paths",
        lambda: {
            "docs_meta": tmp_path / "missing-docs-meta",
            "source_spec": canonical_dir,
        },
    )

    generator = Phase1Generator(tmp_path / "packages", tmp_path / "out")
    resolved = generator._resolve_source_file("mandate.spec")

    assert resolved == mandate_md
