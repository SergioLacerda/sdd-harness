from __future__ import annotations

from pathlib import Path

from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper


def test_bootstrap_source_specs_from_markdown_when_docs_meta_missing(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "seed.md").write_text(
        "# Governance\n\n- Mandate M001\n- Mandate M002\n- Guideline G001\n",
        encoding="utf-8",
    )

    spec_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)

    bootstrapper.bootstrap()

    mandate_spec = spec_dir / "mandate.spec"
    guidelines_dsl = spec_dir / "guidelines.dsl"

    assert mandate_spec.exists()
    assert guidelines_dsl.exists()
    assert "[M001]" in mandate_spec.read_text(encoding="utf-8")
    assert "guideline G001" in guidelines_dsl.read_text(encoding="utf-8")
