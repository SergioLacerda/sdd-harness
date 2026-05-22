"""Pydantic contract models for governance compiled artifacts.

These models are the source of truth for the JSON schema committed at
tests/contract/schemas/governance_core.schema.json.

To regenerate the schema after changing a model:
    make generate-schemas
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator

_ITEM_ID_RE = re.compile(r"^[A-Z]\d{3}$")


class GovernanceItem(BaseModel):
    id: str
    title: str
    type: str
    status: str
    criticality: str
    summary_minimal: str | None = None
    summary_runtime: str | None = None

    @field_validator("id")
    @classmethod
    def id_matches_pattern(cls, v: str) -> str:
        if not _ITEM_ID_RE.match(v):
            raise ValueError(f"id {v!r} does not match [A-Z]\\d{{3}}")
        return v


class GovernanceCoreArtifact(BaseModel):
    category: Literal["CORE"]
    version: str
    fingerprint: str
    items: list[GovernanceItem]

    model_config = {"extra": "allow"}  # tolerates volatile fields (generated_at, etc.)
