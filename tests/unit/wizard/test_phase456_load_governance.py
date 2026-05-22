"""
Tests for governance loading and file generation — updated to use extracted classes.
"""

import json
from pathlib import Path
from typing import Any

from sdd_wizard.orchestration.phase4_governance_loader import GovernanceLoader
from sdd_wizard.orchestration.phase5_source_writer import SddSourceWriter
from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer


def _make_sdd_paths(tmp_path: Path) -> dict[str, Any]:
    client_compiled = tmp_path / "generated" / "client" / "compiled"
    return {"root": tmp_path, "client_compiled": client_compiled}


def test_load_governance_handles_missing_item_type(tmp_path: Path) -> None:
    paths = _make_sdd_paths(tmp_path)
    source_dir = paths["client_compiled"] / "source"
    source_dir.mkdir(parents=True)

    core_json = {
        "category": "CORE",
        "version": "3.0",
        "items": [
            {
                "id": "M001",
                "title": "Clean Architecture",
                "category": "architecture",
                "content": "Do X",
            }
        ],
    }
    client_json = {
        "category": "CLIENT",
        "version": "3.0",
        "items": [
            {"id": "G001", "title": "Testing", "category": "testing", "content": "Do Y"}
        ],
    }
    (source_dir / "governance-core.json").write_text(
        json.dumps(core_json), encoding="utf-8"
    )
    (source_dir / "governance-client.json").write_text(
        json.dumps(client_json), encoding="utf-8"
    )

    loader = GovernanceLoader(
        source_dir / "governance-core.json",
        source_dir / "governance-client.json",
        verbose=False,
    )
    assert loader.load() is True
    assert len(loader.mandates) == 1
    assert "G001" in loader.guidelines
    assert "testing" in loader.guidelines_by_category


def test_generate_guidelines_files_handles_missing_title(tmp_path: Path) -> None:
    output_base = tmp_path / "project"
    sdd = output_base / ".sdd"
    source = sdd / "source"
    writer = SddSourceWriter(
        output_base=output_base,
        source_dir=source,
        runtime_dir=sdd / "runtime",
        mandates_dir=source / "mandates",
        guidelines_dir=source / "guidelines",
        mandates=[],
        guidelines={"G001": {"id": "G001"}},
        guidelines_by_category={
            "testing": [
                {
                    "id": "G001",
                    "type": "GUIDELINE",
                    "status": "required",
                    "content": "Keep tests deterministic",
                }
            ]
        },
        config={},
        verbose=False,
    )
    assert writer.create_directories() is True
    assert writer.generate_guidelines_files() is True
    content = (source / "guidelines" / "testing.md").read_text(encoding="utf-8")
    assert "Guideline G001" in content


def test_create_ide_templates_copies_agent_directories(tmp_path: Path) -> None:
    template_base = (
        tmp_path
        / "packages"
        / "features"
        / "sdd_integration"
        / "src"
        / "sdd_integration"
        / "templates"
    )
    for d in [
        ".github",
        ".vscode",
        ".cursor/rules",
        ".claude",
        ".gemini",
    ]:
        (template_base / d).mkdir(parents=True, exist_ok=True)

    (template_base / ".pre-commit-config.yaml").write_text(
        "repos: []\n", encoding="utf-8"
    )
    (template_base / ".github" / "setup-precommit-hook.sh").write_text(
        "#!/bin/sh\n", encoding="utf-8"
    )
    (template_base / ".github" / "copilot-instructions.md").write_text(
        "copilot\n", encoding="utf-8"
    )
    (template_base / ".vscode" / "ai-rules.md").write_text("vscode\n", encoding="utf-8")
    (template_base / ".vscode" / "settings.json").write_text("{}\n", encoding="utf-8")
    (template_base / ".cursor" / "rules" / "spec.mdc").write_text(
        "cursor\n", encoding="utf-8"
    )
    (template_base / ".claude" / "claude-instructions.md").write_text(
        "claude\n", encoding="utf-8"
    )
    (template_base / ".gemini" / "gemini-instructions.md").write_text(
        "gemini\n", encoding="utf-8"
    )

    deployer = IdeTemplateDeployer(repo_root=tmp_path, output_base=tmp_path / "project")
    assert deployer.create_ide_templates() is True
    assert (deployer.output_base / ".github" / "copilot-instructions.md").exists()
    assert (deployer.output_base / ".vscode" / "ai-rules.md").exists()
    assert (deployer.output_base / ".cursor" / "rules" / "spec.mdc").exists()
    assert (deployer.output_base / ".claude" / "claude-instructions.md").exists()
    assert (deployer.output_base / ".gemini" / "gemini-instructions.md").exists()
