"""
SDD v3.0 Wizard - Phase 1: Validate SOURCE (core/)

Validates that source DSL files have correct syntax and structure
"""

import re
from typing import Any


class SourceValidator:
    """Validate SOURCE files (mandate.spec, guidelines.dsl)"""

    MANDATE_PATTERN = r"-\s*\[\s*([MP]\d{3})\s*\]\s*\*\*\s*([^*]+?)\s*\*\*"
    MANDATE_BLOCK_PATTERN = r"mandate\s+([MP]\d{3})\s*\{([^}]*)\}"
    GUIDELINE_PATTERN = r"guideline\s+(G\d+)\s*\{"

    @staticmethod
    def _extract_block_field(block_text: str, field: str) -> str:
        match = re.search(rf'{field}:\s*"([^"]*)"', block_text)
        return match.group(1) if match else ""

    @staticmethod
    def validate_dsl_syntax(text: str, file_type: str = "dsl") -> list[str]:
        """Validate basic DSL syntax"""
        errors = []

        if file_type == "mandate":
            # Check for lines that look like mandates but are incomplete
            for i, line in enumerate(text.split("\n"), 1):
                line = line.strip()
                if re.match(r"-\s*\[\s*[MP]", line) and not re.search(
                    SourceValidator.MANDATE_PATTERN, line
                ):
                    errors.append(
                        f"Line {i}: Incomplete mandate definition. Expected '- [ID] **Title**'"
                    )
        else:
            # Check for balanced braces (for guidelines.dsl)
            if text.count("{") != text.count("}"):
                errors.append(
                    f"Unbalanced braces: {text.count('{')} opening, {text.count('}')} closing"
                )

            # Check for balanced quotes
            double_quotes = text.count('"')
            if double_quotes % 2 != 0:
                errors.append(f"Odd number of double quotes: {double_quotes}")

        # Basic sanity: should not be empty
        if not text.strip():
            errors.append("File is empty")

        return errors

    @staticmethod
    def _parse_block_format(
        mandate_text: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Parse block DSL format: mandate M001 { title: "..." ... }

        Returns (mandates, mandate_ids).
        """
        mandates: list[dict[str, Any]] = []
        mandate_ids: list[str] = []
        for match in re.finditer(
            SourceValidator.MANDATE_BLOCK_PATTERN,
            mandate_text,
            re.MULTILINE | re.DOTALL,
        ):
            m_id, block_text = match.groups()
            mandate_ids.append(m_id)
            title = SourceValidator._extract_block_field(block_text, "title") or m_id
            metadata = {
                "category": SourceValidator._extract_block_field(
                    block_text, "category"
                ),
                "rationale": SourceValidator._extract_block_field(
                    block_text, "rationale"
                ),
                "type": SourceValidator._extract_block_field(block_text, "type"),
                "description": SourceValidator._extract_block_field(
                    block_text, "description"
                ),
            }
            metadata = {key: value for key, value in metadata.items() if value}
            mandates.append({"id": m_id, "title": title, "metadata": metadata})
        return mandates, mandate_ids

    @staticmethod
    def validate_mandate_spec(mandate_text: str) -> dict[str, Any]:
        """Validate mandate.spec structure (Markdown format)"""
        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {
                "mandate_count": 0,
                "mandate_ids": [],
                "mandates": [],
                "lines": len(mandate_text.split("\n")),
                "bytes": len(mandate_text.encode("utf-8")),
            },
        }

        # Syntax validation
        syntax_errors = SourceValidator.validate_dsl_syntax(mandate_text, "mandate")
        if syntax_errors:
            result["valid"] = False
            result["errors"].extend(syntax_errors)

        # Block DSL format: mandate M001 { title: "..." ... }
        mandates, mandate_ids = SourceValidator._parse_block_format(mandate_text)

        result["statistics"]["mandates"] = mandates
        result["statistics"]["mandate_count"] = len(mandates)
        result["statistics"]["mandate_ids"] = list(dict.fromkeys(mandate_ids))

        if not mandates:
            result["valid"] = False
            result["errors"].append("No mandates found in specification file")

        if len(mandate_ids) != len(set(mandate_ids)):
            duplicates = [
                m_id for m_id in set(mandate_ids) if mandate_ids.count(m_id) > 1
            ]
            result["errors"].append(f"Duplicate mandate IDs: {duplicates}")
            result["valid"] = False

        if mandate_ids:
            numeric_ids = sorted(
                [
                    int(m_id[1:])
                    for m_id in mandate_ids
                    if len(m_id) > 1 and m_id[1:].isdigit()
                ]
            )
            if len(numeric_ids) > 1:
                expected_ids = list(
                    range(min(numeric_ids), min(numeric_ids) + len(numeric_ids))
                )
                if numeric_ids != expected_ids:
                    result["warnings"].append(
                        f"Non-sequential mandate IDs. Found: {mandate_ids}"
                    )

        return result

    @staticmethod
    def validate_guidelines_dsl(guidelines_text: str) -> dict[str, Any]:
        """Validate guidelines.dsl structure"""
        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {
                "guideline_count": 0,
                "guideline_ids": [],
                "lines": len(guidelines_text.split("\n")),
                "bytes": len(guidelines_text.encode("utf-8")),
            },
        }

        # Syntax validation
        syntax_errors = SourceValidator.validate_dsl_syntax(
            guidelines_text, "guidelines"
        )
        if syntax_errors:
            result["valid"] = False
            result["errors"].extend(syntax_errors)
            return result

        # Find all guidelines
        guidelines = re.findall(r"guideline\s+(G\d+)", guidelines_text)
        result["statistics"]["guideline_count"] = len(guidelines)
        result["statistics"]["guideline_ids"] = list(dict.fromkeys(guidelines))

        # Check for duplicates
        if len(guidelines) != len(set(guidelines)):
            duplicates = [g for g in set(guidelines) if guidelines.count(g) > 1]
            result["errors"].append(f"Duplicate guideline IDs: {duplicates}")
            result["valid"] = False

        # Check for empty guidelines
        empty_guidelines = re.findall(r"guideline\s+G\d+\s*\{\s*\}", guidelines_text)
        if empty_guidelines:
            result["errors"].append(f"Empty guidelines found: {len(empty_guidelines)}")
            result["valid"] = False

        # Warning if no guidelines found (but file exists, might be template)
        if not guidelines:
            result["warnings"].append("No guidelines found in file")

        return result

    @staticmethod
    def validate_source_files(
        mandate_text: str, guidelines_text: str
    ) -> tuple[bool, dict[str, Any]]:
        """Validate both source files together"""
        mandate_result = SourceValidator.validate_mandate_spec(mandate_text)
        guidelines_result = SourceValidator.validate_guidelines_dsl(guidelines_text)

        # Combine results
        combined: dict[str, Any] = {
            "valid": mandate_result["valid"] and guidelines_result["valid"],
            "mandate": mandate_result,
            "guidelines": guidelines_result,
            "errors": mandate_result["errors"] + guidelines_result["errors"],
            "warnings": mandate_result["warnings"] + guidelines_result["warnings"],
        }

        return (combined["valid"], combined)
