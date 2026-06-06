"""Runtime execution helper for Phase 6 seedlings generation."""

import json
from collections.abc import Callable
from pathlib import Path

from sdd_wizard.orchestration.wizard.messages import phase6_seedlings_success_message


def _resolve_governance_paths(
    paths: dict[str, Path], output_base: Path
) -> tuple[Path, Path]:
    """Resolve governance JSON paths with .sdd-first precedence."""
    root = paths.get("root", Path.cwd())
    client_compiled = paths.get(
        "client_compiled", root / "generated" / "client" / "compiled"
    )
    core_candidates = [
        root / ".sdd" / "compiled" / "governance-core.json",
        root / ".sdd" / "source" / "governance-core.json",
        client_compiled / "source" / "governance-core.json",
        output_base / ".sdd" / "source" / "governance-core.json",
    ]
    client_candidates = [
        root / ".sdd" / "compiled" / "governance-client.json",
        root / ".sdd" / "source" / "governance-client.json",
        client_compiled / "source" / "governance-client.json",
        output_base / ".sdd" / "source" / "governance-client.json",
    ]

    core_path = next((p for p in core_candidates if p.exists()), core_candidates[0])
    client_path = next(
        (p for p in client_candidates if p.exists()), client_candidates[0]
    )
    return core_path, client_path


def run_phase6_seedlings_generation(
    *,
    wizard_config_path: Path,
    output_base: Path,
    emitter: Callable[[str], None],
) -> bool:
    """Run Phase 6 governance loading + seedlings generation."""
    from sdd_core.utils.environment import get_sdd_paths
    from sdd_wizard.orchestration.phase4_governance_loader import GovernanceLoader
    from sdd_wizard.orchestration.phase6_seedlings_orchestrator import (
        SeedlingsOrchestrator,
    )

    if wizard_config_path.exists():
        with open(wizard_config_path, encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "language": "Python",
            "enforcement_mode": "warn_mode",
            "language_context": {
                "preferred_human_language": "English",
                "preferred_chat_language": "English",
                "preferred_ui_language": "English",
                "preferred_local_docs_language": "English",
            },
        }

    paths = get_sdd_paths()
    governance_core_path, governance_client_path = _resolve_governance_paths(
        paths, output_base
    )

    loader = GovernanceLoader(
        governance_core_path, governance_client_path, verbose=True
    )
    if not loader.load():
        emitter("  ❌ Failed to load governance")
        return False

    orchestrator = SeedlingsOrchestrator(
        output_base=output_base,
        mandates=loader.mandates,
        guidelines_by_category=loader.guidelines_by_category,
        config=config,
        governance_core_path=governance_core_path,
        paths=paths,
        verbose=True,
    )
    if not orchestrator.generate():
        emitter("  ❌ Failed to generate intelligent seedlings")
        return False

    emitter(phase6_seedlings_success_message(output_base))
    return True
