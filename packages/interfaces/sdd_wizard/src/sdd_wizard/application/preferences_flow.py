"""Prompt and preference collection boundary for the wizard shell."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sdd_wizard.application.prompter import Prompter, make_prompter


class PreferencesFlow:
    """Encapsulate shell prompts behind the application layer."""

    def __init__(
        self,
        prompter: Prompter | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._prompter = prompter or make_prompter()
        self._emit = emitter or (lambda _: None)

    def build_prompter(self) -> Prompter:
        """Return the active prompter instance."""
        return self._prompter

    def select_phase(self, choices_map: dict[str, str]) -> str:
        """Prompt for the starting phase and return the matching key."""
        selected = self._prompter.select(
            "Which phase would you like to run?", list(choices_map.values())
        )
        return self._resolve_choice_key(selected, choices_map)

    def collect_preferences(
        self,
        *,
        enforcement_choices: list[str],
        enforcement_map: dict[str, str],
        language_choices: list[str],
        interaction_language_choices: list[str],
        local_docs_language_choices: list[str],
        locale_by_language: dict[str, str],
        handshake_choices: list[str],
        handshake_map: dict[str, str],
    ) -> dict[str, Any]:
        """Collect wizard preferences and return the persisted config payload."""
        enforcement = self._select_enforcement(enforcement_choices, enforcement_map)
        language = self._select_language(language_choices)
        interaction_language = self._select_interaction_language(
            interaction_language_choices
        )
        docs_language = self._select_docs_language(
            interaction_language, local_docs_language_choices
        )
        handshake = self._select_handshake_mode(handshake_choices, handshake_map)
        return self._build_config(
            enforcement_mode=enforcement,
            language=language,
            interaction_language=interaction_language,
            docs_language=docs_language,
            locale_by_language=locale_by_language,
            handshake_mode=handshake,
        )

    def _select_enforcement(
        self, enforcement_choices: list[str], enforcement_map: dict[str, str]
    ) -> str:
        self._emit("\n1️⃣  How should governance violations be handled?")
        selected = self._prompter.select("Select enforcement:", enforcement_choices)
        self._emit(f"   ✅ Selected: {selected}")
        return enforcement_map.get(selected, "warn_mode")

    def _select_language(self, language_choices: list[str]) -> str:
        self._emit(
            "\n2️⃣  Which language would you like examples in?"
            "\n(This is for code examples only - governance applies to all languages)"
        )
        selected = self._prompter.select("Select language:", language_choices)
        self._emit(f"   ✅ Selected: {selected}")
        return selected

    def _select_interaction_language(
        self, interaction_language_choices: list[str]
    ) -> str:
        self._emit(
            "\n3️⃣  Which language should the wizard prefer for chat and operational prompts?"
        )
        selected = self._prompter.select(
            "Select interaction language:", interaction_language_choices
        )
        self._emit(f"   ✅ Selected: {selected}")
        return selected

    def _select_docs_language(
        self, interaction_language: str, local_docs_language_choices: list[str]
    ) -> str:
        self._emit(
            "\n4️⃣  Which language should local workspace notes prefer when the workspace allows it?"
        )
        selected = self._prompter.select(
            "Select local docs preference:", local_docs_language_choices
        )
        self._emit(f"   ✅ Selected: {selected}")
        if selected == "Same as interaction":
            return interaction_language
        return selected

    def _select_handshake_mode(
        self, handshake_choices: list[str], handshake_map: dict[str, str]
    ) -> str:
        self._emit(
            "\n5️⃣  Prefere que todo prompt seja filtrado pela governança (hook) OU"
            " invocar a governança seletivamente (slash commands, CLI)?"
            "\n   (modo hook pode ser desativado a qualquer momento com"
            " 'sdd governance hook disable')"
        )
        selected = self._prompter.select("Selecione o handshake:", handshake_choices)
        self._emit(f"   ✅ Selecionado: {selected}")
        return handshake_map.get(selected, "standard")

    def _build_config(
        self,
        *,
        enforcement_mode: str,
        language: str,
        interaction_language: str,
        docs_language: str,
        locale_by_language: dict[str, str],
        handshake_mode: str,
    ) -> dict[str, Any]:
        return {
            "language": language,
            "locale": locale_by_language.get(interaction_language, "en"),
            "docs_language": docs_language,
            "docs_locale": locale_by_language.get(docs_language, "en"),
            "enforcement_mode": enforcement_mode,
            "handshake_mode": handshake_mode,
            "language_context": self._build_language_context(
                interaction_language, docs_language
            ),
            "generated_at": datetime.now().isoformat(),
        }

    def _build_language_context(
        self, interaction_language: str, docs_language: str
    ) -> dict[str, str]:
        return {
            "preferred_human_language": interaction_language,
            "preferred_chat_language": interaction_language,
            "preferred_ui_language": interaction_language,
            "preferred_local_docs_language": docs_language,
        }

    def _resolve_choice_key(self, selected: str, choices_map: dict[str, str]) -> str:
        for key, value in choices_map.items():
            if value == selected:
                return key
        return "1"
