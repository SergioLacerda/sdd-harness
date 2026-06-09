"""Tests for the application-level preference flow."""

from __future__ import annotations

from sdd_wizard.application.preferences_flow import PreferencesFlow
from sdd_wizard.application.prompter import _CallablePrompter


def test_select_phase_returns_matching_key() -> None:
    flow = PreferencesFlow(_CallablePrompter(lambda _: "2"))
    choice = flow.select_phase({"1": "Phase 1", "2": "Phase 2"})
    assert choice == "2"


def test_collect_preferences_builds_language_context() -> None:
    responses = iter(["2", "4", "2", "3"])
    flow = PreferencesFlow(_CallablePrompter(lambda _: next(responses)))
    config = flow.collect_preferences(
        enforcement_choices=["Sem Alertas", "Alertas", "Bloquear"],
        enforcement_map={
            "Sem Alertas": "silent_mode",
            "Alertas": "warn_mode",
            "Bloquear": "strict_mode",
        },
        language_choices=["Python", "Java", "TypeScript", "Go"],
        interaction_language_choices=["English", "Português (Brasil)"],
        local_docs_language_choices=[
            "English",
            "Português (Brasil)",
            "Same as interaction",
        ],
        locale_by_language={"English": "en", "Português (Brasil)": "pt-BR"},
    )
    assert config["enforcement_mode"] == "warn_mode"
    assert config["language"] == "Go"
    assert config["locale"] == "pt-BR"
    assert config["docs_language"] == "Português (Brasil)"
    assert config["docs_locale"] == "pt-BR"
    assert config["language_context"]["preferred_local_docs_language"] == (
        "Português (Brasil)"
    )
