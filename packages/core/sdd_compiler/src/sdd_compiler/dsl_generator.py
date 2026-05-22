"""
DSL Generator: Programmatic generation of SDD v3.0 DSL files (.spec/.dsl)
"""

from datetime import datetime, timezone
from typing import Any


def _utc_now_iso_z() -> str:
    """Return current UTC timestamp as ISO 8601 with trailing Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DSLGenerator:
    """Generates SDD v3.0 DSL strings from structured governance items"""

    @staticmethod
    def generate_mandate_spec(
        mandates: list[dict[str, Any]], header: str = "SDD v3.0 - MANDATE Specification"
    ) -> str:
        """
        Generate .spec DSL content from a list of mandates

        Args:
            mandates: List of mandate dictionaries with keys:
                     id, title, description, category, rationale, validation (optional)
            header: Custom header for the file
        """
        lines = [
            f"# {header}",
            f"# Generated: {_utc_now_iso_z()}",
            "",
        ]

        for mandate in mandates:
            lines.extend(DSLGenerator._format_mandate(mandate))
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_guidelines_dsl(
        guidelines: list[dict[str, Any]],
        header: str = "SDD v3.0 - GUIDELINES Specification",
    ) -> str:
        """
        Generate .dsl content from a list of guidelines

        Args:
            guidelines: List of guideline dictionaries with keys:
                       id, title, description, category, examples (optional)
            header: Custom header for the file
        """
        lines = [
            f"# {header}",
            f"# Generated: {_utc_now_iso_z()}",
            "",
        ]

        for guideline in guidelines:
            lines.extend(DSLGenerator._format_guideline(guideline))
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_mandate(mandate: dict[str, Any]) -> list[str]:
        """Format a single mandate in DSL syntax"""
        lines = []

        m_id = mandate.get("id", "M000")
        title = mandate.get("title", "Untitled Mandate")
        description = mandate.get("description", "")
        category = mandate.get("category", "general")
        rationale = mandate.get("rationale", "")
        validation = mandate.get("validation", [])

        lines.append(f"mandate {m_id} {{")
        lines.append(f"  type: {mandate.get('type', 'HARD')}")
        lines.append(f'  title: "{DSLGenerator._escape(title)}"')
        lines.append(f'  description: "{DSLGenerator._escape(description)}"')
        lines.append(f"  category: {category}")

        if rationale:
            lines.append(f'  rationale: "{DSLGenerator._escape(rationale)}"')

        if validation:
            lines.append("  validation: {")
            lines.append("    commands: [")
            for cmd in validation:
                lines.append(f'      "{DSLGenerator._escape(cmd)}",')
            lines.append("    ]")
            lines.append("  }")

        lines.append("}")
        return lines

    @staticmethod
    def _format_guideline(guideline: dict[str, Any]) -> list[str]:
        """Format a single guideline in DSL syntax"""
        lines = []

        g_id = guideline.get("id", "G000")
        title = guideline.get("title", "Untitled Guideline")
        description = guideline.get("description", "")
        category = guideline.get("category", "general")
        examples = guideline.get("examples", [])

        lines.append(f"guideline {g_id} {{")
        lines.append(f"  type: {guideline.get('type', 'SOFT')}")
        lines.append(f'  title: "{DSLGenerator._escape(title)}"')
        lines.append(f'  description: "{DSLGenerator._escape(description)}"')
        lines.append(f"  category: {category}")

        if examples:
            lines.append("  examples: [")
            for example in examples:
                lines.append(f'    "{DSLGenerator._escape(example)}",')
            lines.append("  ]")

        lines.append("}")
        return lines

    @staticmethod
    def _escape(s: str) -> str:
        """Escape special characters for DSL strings"""
        if not isinstance(s, str):
            return str(s)
        s = s.replace("\\", "\\\\")
        s = s.replace('"', '\\"')
        s = s.replace("\n", "\\n")
        return s
