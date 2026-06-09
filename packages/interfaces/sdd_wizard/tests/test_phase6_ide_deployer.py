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

    deployer._deployer._template_base_candidates = lambda: [preferred, fallback]  # type: ignore[method-assign]
    assert deployer._template_base == preferred


def test_create_ide_templates_reports_missing_base(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=output_base)
    deployer._deployer._template_base_candidates = lambda: [  # type: ignore[method-assign]
        tmp_path / "missing-a",
        tmp_path / "missing-b",
    ]
    assert deployer.create_ide_templates() is False


def test_create_ide_templates_copies_optional_hooks_when_enabled(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    deployer = IdeTemplateDeployer(
        repo_root=tmp_path,
        output_base=output_base,
        config={"include_optional_hooks": True},
    )
    template_base = tmp_path / "templates"
    (template_base / ".github").mkdir(parents=True)
    (template_base / ".github" / "setup-precommit-hook.sh").write_text(
        "#!/bin/sh\n", encoding="utf-8"
    )
    (template_base / ".pre-commit-config.yaml").write_text(
        "repos: []\n", encoding="utf-8"
    )
    (template_base / ".vscode").mkdir(parents=True)
    (template_base / ".vscode" / "ai-rules.md").write_text("x", encoding="utf-8")
    (template_base / ".cursor" / "rules").mkdir(parents=True)
    (template_base / ".cursor" / "spec.mdc").write_text("x", encoding="utf-8")
    (template_base / ".claude").mkdir(parents=True)
    (template_base / ".claude" / "claude-instructions.md").write_text(
        "x", encoding="utf-8"
    )
    (template_base / ".gemini").mkdir(parents=True)
    (template_base / ".gemini" / "gemini-instructions.md").write_text(
        "x", encoding="utf-8"
    )
    (template_base / ".sdd" / "templates").mkdir(parents=True)
    deployer._deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.create_ide_templates() is True
    assert (output_base / ".github" / "setup-precommit-hook.sh").exists()
    assert (output_base / ".pre-commit-config.yaml").exists()
