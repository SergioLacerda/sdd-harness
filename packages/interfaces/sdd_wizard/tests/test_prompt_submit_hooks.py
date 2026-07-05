"""Tests for prompt-submit governance hook generation."""

from __future__ import annotations

import json
from pathlib import Path

from sdd_wizard.orchestration.prompt_submit_hooks import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
    CENTRAL_PROMPT_SUBMIT_HOOK,
    PromptSubmitHookGenerator,
    resolve_prompt_submit_hook_agents,
)


def test_resolve_prompt_submit_hook_agents_defaults_to_all_supported() -> None:
    assert resolve_prompt_submit_hook_agents(None) == {"claude", "codex", "gemini"}


def test_resolve_prompt_submit_hook_agents_filters_selection() -> None:
    selected = {"governance", "claude", "verify"}

    assert resolve_prompt_submit_hook_agents(selected) == {"claude"}


def test_prompt_submit_hook_generator_writes_central_hook_and_selected_adapter(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})

    assert generator.generate() is True

    central_hook = tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK
    assert central_hook.exists()
    assert ".sdd/runtime/hook-disabled" in central_hook.read_text(encoding="utf-8")
    codex_config = tmp_path / ".codex" / "config.toml"
    assert CENTRAL_PROMPT_SUBMIT_COMMAND in codex_config.read_text(encoding="utf-8")
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


def test_prompt_submit_hook_generator_merges_gemini_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"contextFileName": "GEMINI.md"}', encoding="utf-8")
    generator = PromptSubmitHookGenerator(tmp_path, {"gemini"})

    assert generator.generate() is True

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["contextFileName"] == "GEMINI.md"
    assert CENTRAL_PROMPT_SUBMIT_COMMAND in json.dumps(settings)


def test_prompt_submit_hook_generator_writes_claude_settings(tmp_path: Path) -> None:
    """Regression (SQ-001): Claude adapter generation, not previously covered here."""
    generator = PromptSubmitHookGenerator(tmp_path, {"claude"})

    assert generator.generate() is True

    claude_settings = tmp_path / ".claude" / "settings.json"
    assert claude_settings.exists()
    assert CENTRAL_PROMPT_SUBMIT_COMMAND in claude_settings.read_text(encoding="utf-8")
    assert not (tmp_path / ".codex" / "config.toml").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


def test_prompt_submit_hook_generator_all_three_agents_together(
    tmp_path: Path,
) -> None:
    """Regression (SQ-001): default (no restriction) generates all three adapters."""
    generator = PromptSubmitHookGenerator(
        tmp_path, resolve_prompt_submit_hook_agents(None)
    )

    assert generator.generate() is True

    assert CENTRAL_PROMPT_SUBMIT_COMMAND in (
        tmp_path / ".claude" / "settings.json"
    ).read_text(encoding="utf-8")
    assert CENTRAL_PROMPT_SUBMIT_COMMAND in (
        tmp_path / ".codex" / "config.toml"
    ).read_text(encoding="utf-8")
    assert CENTRAL_PROMPT_SUBMIT_COMMAND in (
        tmp_path / ".gemini" / "settings.json"
    ).read_text(encoding="utf-8")


def test_phase6_output_validator_imports_stay_in_sync_with_prompt_submit_hooks() -> (
    None
):
    """Regression (SQ-001): guards the hidden cross-module coupling Ranger found —
    phase6_output_validator.py imports these three names directly from
    prompt_submit_hooks.py; if they were ever renamed here without updating that
    import, this test fails loudly instead of the coupling breaking silently."""
    from sdd_wizard.orchestration import phase6_output_validator as validator_mod
    from sdd_wizard.orchestration import prompt_submit_hooks as hooks_mod

    assert (
        validator_mod.CENTRAL_PROMPT_SUBMIT_COMMAND
        is hooks_mod.CENTRAL_PROMPT_SUBMIT_COMMAND
    )
    assert (
        validator_mod.CENTRAL_PROMPT_SUBMIT_HOOK is hooks_mod.CENTRAL_PROMPT_SUBMIT_HOOK
    )
    assert (
        validator_mod.SUPPORTED_PROMPT_HOOK_AGENTS
        is hooks_mod.SUPPORTED_PROMPT_HOOK_AGENTS
    )
