"""Public wizard contracts and canonical invocation boundary."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class WizardInvocation:
    """Canonical invocation payload for the wizard."""

    project_root: Path
    non_interactive: bool = False
    output_path: Path | None = None
    language: str = "python"


@dataclass(frozen=True)
class GeneratedManifest:
    """Minimal generated artifact summary."""

    files: list[Path]
    mandates_count: int
    guidelines_count: int
    categories: list[str]


@dataclass(frozen=True)
class WizardResult:
    """Canonical wizard execution result."""

    success: bool
    manifest: GeneratedManifest | None = None
    errors: list[str] = field(default_factory=list)


def run_wizard(invocation: WizardInvocation) -> WizardResult:
    """Run the wizard through the canonical application boundary."""
    module = importlib.import_module("sdd_wizard.application.session_bootstrap")
    session_bootstrap_cls = module.SessionBootstrap
    return cast(WizardResult, session_bootstrap_cls(invocation).run())


def generate_agent_instructions_from_config(
    output_base: Path,
    config: dict[str, Any],
) -> bool:
    """Regenerate .sdd/agent-instructions.md from a governance config dict."""
    from sdd_wizard.orchestration.seedlings.governance_seeds import (
        generate_agent_instructions_from_config as _impl,
    )

    return _impl(output_base, config)
