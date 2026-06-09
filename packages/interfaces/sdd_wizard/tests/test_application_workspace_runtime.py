"""Tests for workspace-facing application helpers."""

from __future__ import annotations

from pathlib import Path

from sdd_wizard.application.workspace_runtime import (
    build_selector_discovery_config,
    cleanup_post_generation_artifacts,
    ensure_docs_meta_ready,
)


def test_build_selector_discovery_config_reports_published_site(tmp_path: Path) -> None:
    selector_site = tmp_path / "site" / "selector" / "index.html"
    selector_site.parent.mkdir(parents=True, exist_ok=True)
    selector_site.write_text("<html></html>", encoding="utf-8")
    result = build_selector_discovery_config(
        selector_output_path=tmp_path / "selector-selection.json",
        selector_site_path=selector_site,
        selector_selection={"selected_ids": ["M001"], "resolved_ids": ["M001"]},
    )
    assert result["published_site_path"] == str(selector_site)
    assert result["resolved_count"] == 1


def test_ensure_docs_meta_ready_bootstraps_missing_files(tmp_path: Path) -> None:
    ok, reason = ensure_docs_meta_ready(
        paths={},
        client_build_dir=tmp_path / "build",
        phase1_choices_dir=tmp_path / "build" / "phase-1-choices",
        phase2_input_dir=tmp_path / "build" / "phase-2-input",
        baseline_mandate="# baseline",
        baseline_guidelines="guideline G001 {}",
    )
    assert ok is True
    assert reason == ""
    assert (tmp_path / "build" / "docs-meta" / "mandate.md").exists()


def test_cleanup_post_generation_artifacts_keeps_final_template(tmp_path: Path) -> None:
    client_build = tmp_path / "build"
    client_compiled = tmp_path / "compiled"
    final_template = client_build / "final-template"
    final_template.mkdir(parents=True, exist_ok=True)
    (final_template / "keep.txt").write_text("ok", encoding="utf-8")
    (client_build / "docs-meta").mkdir(parents=True, exist_ok=True)
    (client_compiled / ".sdd").mkdir(parents=True, exist_ok=True)
    wizard_config = client_build / "wizard-config.json"
    wizard_config.write_text("{}", encoding="utf-8")
    cleaned = cleanup_post_generation_artifacts(
        repo_root=tmp_path,
        client_build_dir=client_build,
        client_compiled_dir=client_compiled,
        final_template_dir=final_template,
        wizard_config_path=wizard_config,
        temp_build_dirs=("docs-meta",),
        temp_compiled_dirs=(".sdd",),
    )
    assert "build/docs-meta" in cleaned
    assert final_template.exists()
