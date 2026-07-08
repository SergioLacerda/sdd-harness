"""Governance footer formatting for skill execution results."""

from __future__ import annotations


def format_governance_footer(
    *,
    drift: str,
    governance: str,
    profile: str,
    root_seed_drift: str | None = None,
) -> str:
    """Build the canonical compact governance footer.

    `root_seed_drift` is a separate, optional field — distinct from `drift`
    (which reflects in-session cached-state drift). It is only appended when
    explicitly provided, so existing callers are unaffected.
    """
    footer = (
        f"SDD GOVERNANCE: drift={drift} | governance={governance} | profile={profile}"
    )
    if root_seed_drift is not None:
        footer += f" | root_seed_drift={root_seed_drift}"
    return footer
