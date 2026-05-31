from __future__ import annotations

from pathlib import Path

from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer


def test_template_base_prefers_existing_candidate(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=output_base)

    preferred = tmp_path / "preferred" / "templates"
    preferred.mkdir(parents=True)

    fallback = tmp_path / "fallback" / "templates"
    fallback.mkdir(parents=True)

    deployer._template_base_candidates = lambda: [preferred, fallback]  # type: ignore[method-assign]
    assert deployer._template_base == preferred


def test_create_ide_templates_reports_missing_base(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=output_base)
    deployer._template_base_candidates = lambda: [  # type: ignore[method-assign]
        tmp_path / "missing-a",
        tmp_path / "missing-b",
    ]
    assert deployer.create_ide_templates() is False
