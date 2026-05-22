"""Runtime execution helper for Phase 6 seedlings generation."""

import json
from collections.abc import Callable
from pathlib import Path

from sdd_wizard.orchestration.wizard.messages import phase6_seedlings_success_message


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
        config = {"language": "Python", "enforcement_mode": "warn_mode"}

    paths = get_sdd_paths()
    governance_core_path = paths["client_compiled"] / "source" / "governance-core.json"
    governance_client_path = (
        paths["client_compiled"] / "source" / "governance-client.json"
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
