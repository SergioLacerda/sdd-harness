"""Tests for DSLGenerator — generate .spec/.dsl content from structured data."""

from __future__ import annotations

from sdd_compiler.dsl_generator import DSLGenerator

_MANDATE = {
    "id": "M001",
    "type": "HARD",
    "title": "Dependency governance",
    "description": "All deps must be declared.",
    "category": "architecture",
    "rationale": "Prevents drift.",
    "validation": ["sdd lint run", "sdd doctor run"],
}

_GUIDELINE = {
    "id": "G01",
    "type": "SOFT",
    "title": "Use semantic commits",
    "description": "Follow conventional commits.",
    "category": "git",
    "examples": ["feat: add login", "fix: null pointer"],
}


class TestGenerateMandateSpec:
    def test_output_contains_mandate_block(self) -> None:
        out = DSLGenerator.generate_mandate_spec([_MANDATE])
        assert "mandate M001 {" in out

    def test_output_contains_title(self) -> None:
        out = DSLGenerator.generate_mandate_spec([_MANDATE])
        assert "Dependency governance" in out

    def test_output_contains_rationale(self) -> None:
        out = DSLGenerator.generate_mandate_spec([_MANDATE])
        assert "Prevents drift." in out

    def test_output_contains_validation_commands(self) -> None:
        out = DSLGenerator.generate_mandate_spec([_MANDATE])
        assert "sdd lint run" in out
        assert "sdd doctor run" in out

    def test_custom_header_included(self) -> None:
        out = DSLGenerator.generate_mandate_spec([_MANDATE], header="My Custom Header")
        assert "My Custom Header" in out

    def test_empty_mandates_returns_header_only(self) -> None:
        out = DSLGenerator.generate_mandate_spec([])
        assert "SDD v3.0" in out

    def test_mandate_without_rationale(self) -> None:
        m = {**_MANDATE, "rationale": ""}
        out = DSLGenerator.generate_mandate_spec([m])
        assert "rationale" not in out

    def test_mandate_without_validation(self) -> None:
        m = {**_MANDATE, "validation": []}
        out = DSLGenerator.generate_mandate_spec([m])
        assert "commands:" not in out

    def test_multiple_mandates(self) -> None:
        m2 = {**_MANDATE, "id": "M002", "title": "Second mandate"}
        out = DSLGenerator.generate_mandate_spec([_MANDATE, m2])
        assert "M001" in out
        assert "M002" in out

    def test_mandate_missing_optional_fields_uses_defaults(self) -> None:
        out = DSLGenerator.generate_mandate_spec([{"id": "M001"}])
        assert "Untitled Mandate" in out


class TestGenerateGuidelinesDsl:
    def test_output_contains_guideline_block(self) -> None:
        out = DSLGenerator.generate_guidelines_dsl([_GUIDELINE])
        assert "guideline G01 {" in out

    def test_output_contains_title(self) -> None:
        out = DSLGenerator.generate_guidelines_dsl([_GUIDELINE])
        assert "Use semantic commits" in out

    def test_output_contains_examples(self) -> None:
        out = DSLGenerator.generate_guidelines_dsl([_GUIDELINE])
        assert "feat: add login" in out

    def test_guideline_without_examples(self) -> None:
        g = {**_GUIDELINE, "examples": []}
        out = DSLGenerator.generate_guidelines_dsl([g])
        assert "examples:" not in out

    def test_custom_header(self) -> None:
        out = DSLGenerator.generate_guidelines_dsl([], header="Custom Header")
        assert "Custom Header" in out

    def test_guideline_missing_fields_uses_defaults(self) -> None:
        out = DSLGenerator.generate_guidelines_dsl([{}])
        assert "Untitled Guideline" in out


class TestEscape:
    def test_escapes_double_quotes(self) -> None:
        assert DSLGenerator._escape('say "hi"') == 'say \\"hi\\"'

    def test_escapes_backslash(self) -> None:
        assert DSLGenerator._escape("path\\to\\file") == "path\\\\to\\\\file"

    def test_escapes_newline(self) -> None:
        assert DSLGenerator._escape("line1\nline2") == "line1\\nline2"

    def test_non_string_converted(self) -> None:
        assert DSLGenerator._escape(42) == "42"  # type: ignore[arg-type]

    def test_empty_string(self) -> None:
        assert DSLGenerator._escape("") == ""
