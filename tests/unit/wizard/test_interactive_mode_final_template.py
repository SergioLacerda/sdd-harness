from pathlib import Path

import pytest

from sdd_wizard.src import interactive_mode
from sdd_wizard.src.interactive_mode import InteractiveWizard


@pytest.fixture
def fake_paths(tmp_path: Path) -> dict[str, Path]:
    client_build = tmp_path / "generated" / "client" / "build"
    client_compiled = tmp_path / "generated" / "client" / "compiled"
    return {
        "root": tmp_path,
        "client_build": client_build,
        "client_compiled": client_compiled,
    }


def test_consolidate_final_template_moves_all_compiled_artifacts(
    monkeypatch: pytest.MonkeyPatch, fake_paths: dict[str, Path]
) -> None:
    monkeypatch.setattr(interactive_mode, "get_sdd_paths", lambda: fake_paths)

    compiled_dir = fake_paths["client_compiled"]
    (compiled_dir / "source").mkdir(parents=True)
    (compiled_dir / "source" / "governance-client.json").write_text(
        "{}", encoding="utf-8"
    )
    (compiled_dir / "backup").mkdir(parents=True)
    (compiled_dir / "backup" / "metadata-core.json.backup").write_text(
        "{}", encoding="utf-8"
    )
    (compiled_dir / ".sdd" / "source").mkdir(parents=True)
    (compiled_dir / "source" / "governance-core.json").write_text(
        "{}", encoding="utf-8"
    )
    (compiled_dir / "source" / "README.md").write_text(
        "new source readme", encoding="utf-8"
    )
    (compiled_dir / ".sdd" / "source" / "README.md").write_text(
        "old source readme", encoding="utf-8"
    )
    (compiled_dir / ".sdd" / "metadata.json").write_text("{}", encoding="utf-8")
    (compiled_dir / "governance-core.compiled.msgpack").write_bytes(b"core")
    (compiled_dir / "governance-client-template.compiled.msgpack").write_bytes(
        b"client"
    )
    (compiled_dir / "metadata-core.json").write_text("{}", encoding="utf-8")
    (compiled_dir / "metadata-client-template.json").write_text("{}", encoding="utf-8")
    (compiled_dir / "DEPLOYMENT_MANIFEST.json").write_text("{}", encoding="utf-8")
    (compiled_dir / "governance-core.json").write_text('{"items":[]}', encoding="utf-8")
    (compiled_dir / "governance-client.json").write_text(
        '{"items":[]}', encoding="utf-8"
    )
    (compiled_dir / "audit").mkdir(parents=True)
    (compiled_dir / "audit" / "metadata-core.json").write_text(
        '{"from":"top-level-audit"}', encoding="utf-8"
    )

    wizard = InteractiveWizard(fake_paths["root"])

    result = wizard._consolidate_final_template()

    assert result["success"] is True
    assert (wizard.final_template_dir / ".sdd" / "metadata.json").exists()
    assert (
        wizard.final_template_dir
        / ".sdd"
        / "compiled"
        / "governance-core.compiled.msgpack"
    ).exists()
    assert (
        wizard.final_template_dir
        / ".sdd"
        / "compiled"
        / "governance-client-template.compiled.msgpack"
    ).exists()
    assert (
        wizard.final_template_dir / ".sdd" / "compiled" / "audit" / "metadata-core.json"
    ).exists()
    assert (
        wizard.final_template_dir
        / ".sdd"
        / "compiled"
        / "audit"
        / "metadata-client-template.json"
    ).exists()
    assert (
        wizard.final_template_dir / ".sdd" / "source" / "governance-core.json"
    ).exists()
    assert (
        wizard.final_template_dir / ".sdd" / "source" / "governance-client.json"
    ).exists()
    assert (
        wizard.final_template_dir / ".sdd" / "audit" / "governance-core.json"
    ).exists()
    assert (
        wizard.final_template_dir / ".sdd" / "audit" / "governance-client.json"
    ).exists()
    assert (
        wizard.final_template_dir / ".sdd" / "audit" / "metadata-core.json"
    ).exists()
    assert (wizard.final_template_dir / ".sdd" / "source" / "README.md").read_text(
        encoding="utf-8"
    ) == "new source readme"
    assert (
        wizard.final_template_dir
        / ".sdd"
        / "compiled"
        / "audit"
        / "DEPLOYMENT_MANIFEST.json"
    ).exists()
    assert (wizard.final_template_dir / ".sdd" / "runtime" / ".sdd-cache.md").exists()
    assert not (wizard.final_template_dir / "governance-core.compiled.msgpack").exists()
    assert not (wizard.final_template_dir / "metadata-core.json").exists()
    assert not (wizard.final_template_dir / "governance-core.json").exists()
    assert not (wizard.final_template_dir / "governance-client.json").exists()
    assert not (wizard.final_template_dir / "audit").exists()
    assert not (wizard.final_template_dir / "source").exists()
    assert not (wizard.final_template_dir / "backup").exists()
    assert wizard.client_compiled_dir.exists()
    assert not any(wizard.client_compiled_dir.iterdir())


def test_consolidate_final_template_reports_counts(
    monkeypatch: pytest.MonkeyPatch, fake_paths: dict[str, Path]
) -> None:
    monkeypatch.setattr(interactive_mode, "get_sdd_paths", lambda: fake_paths)
    messages: list[str] = []

    compiled_dir = fake_paths["client_compiled"]
    compiled_dir.mkdir(parents=True, exist_ok=True)
    (compiled_dir / "foo.txt").write_text("x", encoding="utf-8")

    wizard = InteractiveWizard(fake_paths["root"], emitter=messages.append)
    result = wizard._consolidate_final_template()

    assert result["success"] is True
    assert result["moved_items"] == 1
    assert result["error"] == ""
    assert any("Consolidated 1 artifact(s)" in msg for msg in messages)
