"""Deterministic fingerprinting for governance artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class GovernanceFingerprinter:
    """Generates deterministic SHA-256 fingerprints for governance items."""

    HASH_ALGORITHM = "sha256"

    @staticmethod
    def generate(items: list[dict[str, Any]], salt: str = "") -> str:
        """Generate a deterministic SHA-256 hash using canonical JSON serialization.

        Args:
            items: List of governance items to hash
            salt: Optional salt string to mix into the hash

        Returns:
            SHA-256 hex digest, or "empty" if no items and no salt
        """
        if not items and not salt:
            return "empty"

        # Ensure deterministic order
        sorted_items = sorted(items, key=lambda x: x.get("id", ""))

        # Canonical JSON string (sorted keys, fixed separators)
        canonical_json = json.dumps(
            sorted_items, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

        payload = canonical_json + salt
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
