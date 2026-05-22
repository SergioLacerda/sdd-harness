from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_wizard.src import interactive_mode
from sdd_wizard.src.interactive_mode import InteractiveWizard


def _patched_input(prompt: str) -> str:
    return input(prompt)


@pytest.fixture
def fake_paths(tmp_path: Path) -> dict[str, Path]:
    client_build = tmp_path / "generated" / "client" / "build"
    client_compiled = tmp_path / "generated" / "client" / "compiled"
    return {
        "root": tmp_path,
        "client_build": client_build,
        "client_compiled": client_compiled,
    }


def test_wizard_uses_standardized_phase_directories(
    monkeypatch: pytest.MonkeyPatch, fake_paths: dict[str, Path]
) -> None:
    monkeypatch.setattr(interactive_mode, "get_sdd_paths", lambda: fake_paths)

    wizard = InteractiveWizard(fake_paths["root"], prompter=_patched_input)

    assert wizard.client_build_dir == fake_paths["client_build"]
    assert wizard.client_compiled_dir == fake_paths["client_compiled"]
    assert wizard.phase1_choices_dir == fake_paths["client_build"] / "phase-1-choices"
    assert wizard.phase2_input_dir == fake_paths["client_build"] / "phase-2-input"
    assert (
        wizard.wizard_config_path == fake_paths["client_build"] / "wizard-config.json"
    )


def test_phase2_stages_supported_review_files(
    monkeypatch: pytest.MonkeyPatch, fake_paths: dict[str, Path]
) -> None:
    monkeypatch.setattr(interactive_mode, "get_sdd_paths", lambda: fake_paths)

    phase1_dir = fake_paths["client_build"] / "phase-1-choices"
    phase1_dir.mkdir(parents=True)

    (phase1_dir / "mandates-testing.md").write_text("# Mandates", encoding="utf-8")
    (phase1_dir / "mandate.spec").write_text(
        'mandate M001 { title: "X" }', encoding="utf-8"
    )
    (phase1_dir / "guidelines.dsl").write_text(
        'guideline G001 { title: "Y" }', encoding="utf-8"
    )

    wizard = InteractiveWizard(fake_paths["root"], prompter=_patched_input)

    with patch("builtins.input", return_value=""):
        result = wizard.phase_2_show_instructions()

    phase2_dir = fake_paths["client_build"] / "phase-2-input"

    assert result["success"] is True
    assert (phase2_dir / "mandates-testing.md").exists()
    assert (phase2_dir / "mandate.spec").exists()
    assert (phase2_dir / "guidelines.dsl").exists()
