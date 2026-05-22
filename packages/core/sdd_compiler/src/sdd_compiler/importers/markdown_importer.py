"""
Markdown Importer: Extract governance items from structured Markdown files.
Useful for classic ingestion and importing from external documentation sources.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportedItem:
    """Represents a governance item extracted from Markdown"""

    id: str
    title: str
    description: str
    type: str  # MANDATE or GUIDELINE
    category: str = "general"
    rationale: str = ""
    validation_commands: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


class MarkdownImporter:
    """Ingeests governance from Markdown sources (Lists, Headers, Blocks)"""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def import_from_file(self, file_path: Path) -> list[ImportedItem]:
        """Auto-detect format and extract items from a markdown file"""
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding="utf-8")

        # Try Header-based parsing (Constitution style)
        items = self._parse_header_based(content)

        # If no items found, try List-based parsing
        if not items:
            items = self._parse_list_based(content)

        return items

    def _parse_header_based(self, content: str) -> list[ImportedItem]:
        """Extract items from H2/H3 headers (Classic style)"""
        items: list[ImportedItem] = []
        # Pattern: ## ... PRINCIPLE: <Title>
        pattern = r"##\s+.*?(?:PRINCIPLE|MANDATE|GUIDELINE):\s+(.+?)\n"
        matches = list(re.finditer(pattern, content))

        for idx, match in enumerate(matches):
            title = match.group(1).strip()
            start_pos = match.start()
            end_pos = (
                matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
            )

            block = content[start_pos:end_pos]

            # Extract sections
            description = self._extract_section(block, "(?:THE PRINCIPLE|DESCRIPTION)")
            rationale = self._extract_section(block, "RATIONALE")
            validation = self._extract_code_blocks(block)

            item_id = f"IMP{str(len(items) + 1).zfill(3)}"

            items.append(
                ImportedItem(
                    id=item_id,
                    title=title,
                    description=description,
                    type=(
                        "MANDATE"
                        if "PRINCIPLE" in match.group(0) or "MANDATE" in match.group(0)
                        else "GUIDELINE"
                    ),
                    category=self._infer_category(title),
                    rationale=rationale,
                    validation_commands=validation,
                )
            )

        return items

    def _parse_list_based(self, content: str) -> list[ImportedItem]:
        """Extract items from Markdown lists (- [ID] **Title**)"""
        items = []
        pattern = r"-\s*\[([MPG]\d+)\]\s+\*\*([^*]+)\*\*(.*?)(?=\n-|\n---|\Z)"

        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            raw_id = match.group(1)
            title = match.group(2).strip()
            body = match.group(3).strip()

            item_type = (
                "MANDATE"
                if raw_id.startswith("M") or raw_id.startswith("P")
                else "GUIDELINE"
            )

            items.append(
                ImportedItem(
                    id=raw_id,
                    title=title,
                    description=body[:500],  # Truncate if too long
                    type=item_type,
                    category=self._infer_category(title),
                )
            )

        return items

    def _extract_section(self, text: str, section_name_pattern: str) -> str:
        """Extract content of a named section using Regex"""
        pattern = rf"\*\*{section_name_pattern}\*\*\s*\n(.*?)(?=\n\*\*|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            return re.sub(r"```.*?```", "", content, flags=re.DOTALL).strip()
        return ""

    def _extract_code_blocks(self, text: str) -> list[str]:
        """Extract commands from markdown code blocks"""
        commands = []
        code_pattern = r"```(?:bash|shell|sh)?\n(.*?)\n```"
        matches = re.findall(code_pattern, text, re.DOTALL)
        for match in matches:
            for line in match.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    commands.append(line)
        return commands

    def _infer_category(self, title: str) -> str:
        """Heuristic to infer category from title keywords"""
        title_l = title.lower()
        if any(w in title_l for w in ["arch", "layer", "structure"]):
            return "architecture"
        if any(w in title_l for w in ["test", "tdd", "quality"]):
            return "quality"
        if any(w in title_l for w in ["security", "auth", "secret"]):
            return "security"
        if any(w in title_l for w in ["perf", "speed", "fast"]):
            return "performance"
        return "general"
