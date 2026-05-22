"""Markdown content parsing for v3.0 governance specifications."""

from __future__ import annotations

import re


class MarkdownParser:
    """Extracts governance item metadata from Markdown content."""

    @staticmethod
    def extract_summary_minimal(content: str, item_id: str) -> str | None:
        """Extract one-line minimal summary for an item from Markdown.

        Looks for pattern: `# ITEM_ID: One-line summary`
        or returns first non-empty line after heading if no colon.

        Args:
            content: Markdown content
            item_id: Item ID to extract summary for (e.g., M001, G002)

        Returns:
            Minimal summary or None if not found
        """
        # Try to extract title from heading
        pattern = rf"^#{{1,3}}\s+{item_id}[:\s]+(.+?)$"
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Validate: reject malformed titles (e.g., "- Status: Accepted")
            if title.startswith("-"):
                return None
            # Reject single-word status keywords
            if title.lower() in ("accepted", "rejected", "pending", "status"):
                return None
            return title
        return None

    @staticmethod
    def extract_summary_runtime(content: str, item_id: str) -> str | None:
        """Extract runtime summary (enforcement rules) for an item from Markdown.

        Looks for content between the item's heading and the next item heading.
        Returns first paragraph or up to 200 chars of description.

        Args:
            content: Markdown content
            item_id: Item ID to extract summary for (e.g., M001, G002)

        Returns:
            Runtime summary or None if not found
        """
        # Find the section for this item (from its heading to next item heading)
        pattern = rf"^#{{1,3}}\s+{item_id}[:\s]+.+?$\n(.*?)(?=^#{{1,3}}\s+[MG]\d+|$)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            section_content = match.group(1).strip()
            # Extract first non-empty line after heading
            lines = [
                line.strip() for line in section_content.split("\n") if line.strip()
            ]
            if lines:
                # Return first line, limited to 200 chars for runtime summary
                first_line = lines[0]
                return first_line[:197] + "..." if len(first_line) > 200 else first_line
        return None
