"""Tests for CLI prompt command generator contracts."""

from pathlib import Path

from sdd_cli.generators._prompt_commands import generate_agent_prompt_commands


def test_sdd_ask_prompt_includes_preflight_and_500_fallback(tmp_path: Path) -> None:
    """sdd-ask prompt must include HARD preflight contract and 5xx fallback note."""
    generate_agent_prompt_commands(tmp_path, config={})
    ask_prompt = (tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "sdd runtime status" in ask_prompt
    assert "sdd governance validate" in ask_prompt
    assert 'sdd ask --full "$QUERY"' in ask_prompt
    assert "fingerprint`, `context_source`, and `mandates_loaded`" in ask_prompt
    assert "API Error: 5xx" in ask_prompt
    assert "request_id" in ask_prompt
    assert (
        "SDD GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}"
        in ask_prompt
    )


def test_generated_command_surfaces_never_emit_duplicated_ask_full(
    tmp_path: Path,
) -> None:
    """Generated command helper files must not duplicate the full ask variant."""
    generate_agent_prompt_commands(tmp_path, config={})
    files = [
        tmp_path / ".cursor" / "rules" / "sdd-commands.mdc",
        tmp_path / ".gemini" / "commands.md",
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert content.count('sdd ask --full "$QUERY"') <= 1
        assert "/sdd-ask-full" not in content
