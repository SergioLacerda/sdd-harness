"""Governance footer formatting for skill execution results."""

from __future__ import annotations


def format_governance_footer(
    *,
    drift: str,
    governance: str,
    profile: str,
) -> str:
    """Build the canonical compact governance footer."""
    return (
        f"SDD GOVERNANCE: drift={drift} | governance={governance} | profile={profile}"
    )
