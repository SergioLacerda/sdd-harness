"""Prompter protocol and adapters for interactive wizard."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

try:
    import questionary

    _QUESTIONARY_AVAILABLE = True
except ImportError:
    _QUESTIONARY_AVAILABLE = False


@runtime_checkable
class Prompter(Protocol):
    """Protocol for interactive user prompts."""

    def select(self, question: str, choices: list[Any]) -> str:
        """Present a single-choice menu and return the selected value."""
        pass

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        """Present a multi-choice menu and return the selected values."""
        pass

    def confirm(self, question: str, default: bool = True) -> bool:
        """Present a yes/no question and return the boolean answer."""
        pass


def _real_choices(choices: list[Any]) -> list[tuple[int, str, str]]:
    """Return (index, value, label) for non-separator entries.

    Separators are detected by their truthy `disabled` attribute (questionary 2.x
    sets disabled='-' on Separator objects).
    """
    result: list[tuple[int, str, str]] = []
    idx = 0
    for c in choices:
        if getattr(c, "disabled", None):
            # questionary.Separator — skip
            continue
        if isinstance(c, str):
            result.append((idx, c, c))
            idx += 1
        elif hasattr(c, "value") and c.value is not None:
            label = str(getattr(c, "title", c.value))
            result.append((idx, c.value, label))
            idx += 1
    return result


class PlainPrompter:
    """Input-based prompter for non-interactive environments (CI, pipe)."""

    def select(self, question: str, choices: list[Any]) -> str:
        """Print numbered choices and return the value at the entered index."""
        real = _real_choices(choices)
        for i, _v, label in real:
            print(f"  [{i + 1}] {label}")
        raw = input(f"{question} (1-{len(real)}): ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(real):
                return real[idx][1]
        return real[0][1] if real else ""

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        """Print numbered choices; return selected values or [] for all."""
        real = _real_choices(choices)
        real_idx = 0
        sep_idx = 0
        for c in choices:
            if getattr(c, "disabled", None):
                line = str(getattr(c, "title", f"── Group {sep_idx} ──"))
                print(f"\n  {line}")
                sep_idx += 1
            else:
                _idx, _value, label = real[real_idx]
                print(f"  [{real_idx + 1}] {label}")
                real_idx += 1
        print("  (empty = all, or comma-separated numbers/names)")
        raw = input(f"{question}: ").strip()
        if not raw or raw.lower() == "all":
            return []
        value_set = {v for _, v, _ in real}
        selected: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(real):
                    selected.append(real[idx][1])
            elif token in value_set:
                selected.append(token)
        return selected

    def confirm(self, question: str, default: bool = True) -> bool:
        """Prompt y/n; empty input returns the default."""
        suffix = " [Y/n]" if default else " [y/N]"
        raw = input(f"{question}{suffix}: ").strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes")


class RichPrompter:
    """questionary-based prompter for interactive terminals."""

    def select(self, question: str, choices: list[Any]) -> str:
        """Render an arrow-key single-choice prompt; raise KeyboardInterrupt on Ctrl-C."""
        result = questionary.select(question, choices=choices).ask()
        if result is None:
            raise KeyboardInterrupt
        return str(result)

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        """Render an arrow-key multi-choice prompt; raise KeyboardInterrupt on Ctrl-C."""
        result = questionary.checkbox(question, choices=choices).ask()
        if result is None:
            raise KeyboardInterrupt
        return [str(v) for v in result]

    def confirm(self, question: str, default: bool = True) -> bool:
        """Render a yes/no prompt; raise KeyboardInterrupt on Ctrl-C."""
        result = questionary.confirm(question, default=default).ask()
        if result is None:
            raise KeyboardInterrupt
        return bool(result)


class _CallablePrompter:
    """Backward-compat wrapper: adapts a Callable[[str], str] to the Prompter protocol.

    Used internally so legacy test callables continue to work without changes.
    """

    def __init__(self, fn: Callable[[str], str]) -> None:
        self._fn = fn

    def select(self, question: str, choices: list[Any]) -> str:
        raw = self._fn(question).strip()
        real = _real_choices(choices)
        if not real:
            return ""
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(real):
                return real[idx][1]
        return real[0][1]

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        raw = self._fn(question).strip()
        if not raw or raw.lower() == "all":
            return []
        real = _real_choices(choices)
        value_set = {v for _, v, _ in real}
        selected: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(real):
                    selected.append(real[idx][1])
            elif token in value_set:
                selected.append(token)
        return selected

    def confirm(self, question: str, default: bool = True) -> bool:
        raw = self._fn(question).strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes")


def make_prompter() -> Prompter:
    """Return RichPrompter when stdin is a TTY and questionary is available."""
    if sys.stdin.isatty() and _QUESTIONARY_AVAILABLE:
        return RichPrompter()
    return PlainPrompter()


def _wrap_prompter(prompter: Prompter | Callable[[str], str] | None) -> Prompter:
    """Normalise any prompter value into a Prompter instance."""
    if prompter is None:
        return make_prompter()
    if isinstance(prompter, Prompter):
        return prompter
    if callable(prompter):
        return _CallablePrompter(prompter)
    return make_prompter()
