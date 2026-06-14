"""Result of loading a compiled artifact with authentication metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._compiled_artifact import CompiledArtifact


@dataclass
class ArtifactLoadResult:
    """Result of loading a compiled artifact with authentication metadata."""

    artifact: CompiledArtifact
    auth_state: str = "unverified"  # "verified" | "degraded" | "unverified"
    trust_source: str = "none"  # "canonical" | "legacy" | "override" | "none"
