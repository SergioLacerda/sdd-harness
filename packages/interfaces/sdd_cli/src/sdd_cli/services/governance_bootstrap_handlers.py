"""Bootstrap handshake and signing handlers for `sdd governance generate`."""

from __future__ import annotations

from typing import Any

from sdd_cli.services._governance_generate_support import (
    bootstrap_response,
    run_bootstrap_signing_flow,
)
from sdd_cli.utils.sdd_authority import resolve_workspace_root


def complete_bootstrap_handshake() -> None:
    """Run and complete the agent handshake protocol for bootstrap."""
    from sdd_core.governance.handshake import AgentHandshakeProtocol

    ahp = AgentHandshakeProtocol()
    challenge = ahp.generate_challenge(task_description="Bootstrap Session")
    ahp.complete_handshake(bootstrap_response(challenge))


def run_bootstrap_signing(key_id: str, *, keygen_fn: Any, sign_fn: Any) -> None:
    """Run the bootstrap key generation and signing flow."""
    run_bootstrap_signing_flow(
        key_id,
        keygen_fn=keygen_fn,
        sign_fn=sign_fn,
        resolve_workspace_root_fn=resolve_workspace_root,
    )
