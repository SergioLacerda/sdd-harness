"""Small stateless markdown-building helpers shared by report renderers."""

from __future__ import annotations


class ReportTemplate:
    """Markdown-building helpers used by dimension reporters."""

    def header(self, text: str, level: int = 1) -> str:
        """Render a markdown header at the given level (1-6)."""
        return f"{'#' * level} {text}"

    def section(self, title: str, body: str, level: int = 2) -> str:
        """Render a header followed by a body, separated by a blank line."""
        return f"{self.header(title, level)}\n\n{body}"

    def bullet_list(self, items: list[str]) -> str:
        """Render items as a markdown bullet list."""
        return "\n".join(f"- {item}" for item in items)

    def code_block(self, code: str, lang: str = "python") -> str:
        """Render code wrapped in a fenced markdown code block."""
        return f"```{lang}\n{code}\n```"

    def table(self, headers: list[str], rows: list[list[str]]) -> str:
        """Render a markdown table from headers and row data."""
        header_line = f"| {' | '.join(headers)} |"
        separator_line = f"| {' | '.join('---' for _ in headers)} |"
        row_lines = [f"| {' | '.join(row)} |" for row in rows]
        return "\n".join([header_line, separator_line, *row_lines])
