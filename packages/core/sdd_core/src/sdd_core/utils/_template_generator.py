"""Customization template generation from governance data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sdd_core.utils.loader import GovernanceLoader


class TemplateGenerator:
    """Generate customization templates from governance."""

    def __init__(self, loader: GovernanceLoader) -> None:
        self.loader = loader

    def generate_basic_template(self) -> dict[str, Any]:
        client_items = self.loader.load_client().get("items", [])
        return {
            "version": "3.0",
            "type": "customization-template",
            "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "customizations": self._prepare_items(client_items),
        }

    def _prepare_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "type": item.get("type"),
                "customizable": item.get("customizable", False),
            }
            for item in items
        ]
