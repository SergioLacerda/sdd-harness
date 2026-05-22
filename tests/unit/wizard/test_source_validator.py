"""Unit tests for sdd_wizard.validator.SourceValidator."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


VALID_MANDATE_SPEC = """
mandate M001 {
  type: HARD
  title: "First Mandate"
  description: "Description of mandate one"
  criticality: OBRIGATÓRIO
}

mandate M002 {
  type: SOFT
  title: "Second Mandate"
  description: "Description of mandate two"
  criticality: RECOMENDADO
}
"""

VALID_GUIDELINES_DSL = """
guideline G001 {
  type: SOFT
  title: "First Guideline"
  description: "Description of guideline one"
  category: quality
}

guideline G002 {
  type: SOFT
  title: "Second Guideline"
  description: "Description of guideline two"
  category: security
}
"""


# ---------------------------------------------------------------------------
# validate_dsl_syntax
# ---------------------------------------------------------------------------


class TestValidateDslSyntax:
    def test_empty_text_reports_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        errors = SourceValidator.validate_dsl_syntax("", "dsl")
        assert any("empty" in e.lower() for e in errors)

    def test_balanced_braces_no_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = 'guideline G001 { title: "X" }'
        errors = SourceValidator.validate_dsl_syntax(text, "dsl")
        assert not any("brace" in e.lower() for e in errors)

    def test_unbalanced_braces_reports_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = 'guideline G001 { title: "X"'  # missing closing brace
        errors = SourceValidator.validate_dsl_syntax(text, "dsl")
        assert any("brace" in e.lower() for e in errors)

    def test_odd_quotes_reports_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = 'guideline G001 { title: "X }'  # odd number of double quotes
        errors = SourceValidator.validate_dsl_syntax(text, "dsl")
        assert any("quote" in e.lower() for e in errors)

    def test_mandate_type_validates_pattern(self) -> None:
        from sdd_wizard.validator import SourceValidator

        # A line that starts with a mandate marker but is incomplete
        text = "- [M001] incomplete"
        errors = SourceValidator.validate_dsl_syntax(text, "mandate")
        assert len(errors) > 0

    def test_valid_mandate_line_no_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = "- [M001] **Valid Mandate Title**"
        errors = SourceValidator.validate_dsl_syntax(text, "mandate")
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# validate_mandate_spec
# ---------------------------------------------------------------------------


class TestValidateMandateSpec:
    def test_valid_spec_returns_valid_true(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_mandate_spec(VALID_MANDATE_SPEC)
        assert result["valid"] is True
        assert result["statistics"]["mandate_count"] == 2

    def test_empty_spec_returns_valid_false(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_mandate_spec("")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_no_mandates_returns_valid_false(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_mandate_spec("# Just a header\n\nSome text")
        assert result["valid"] is False
        assert any("No mandates" in e for e in result["errors"])

    def test_parses_mandate_ids(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_mandate_spec(VALID_MANDATE_SPEC)
        ids = result["statistics"]["mandate_ids"]
        assert "M001" in ids
        assert "M002" in ids

    def test_duplicate_ids_reported_as_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = (
            VALID_MANDATE_SPEC
            + """
mandate M001 {
  title: "Duplicate"
}
"""
        )
        result = SourceValidator.validate_mandate_spec(text)
        assert result["valid"] is False
        assert any("Duplicate" in e for e in result["errors"])

    def test_non_sequential_ids_generate_warning(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = """
mandate M001 {
  title: "First"
}
mandate M003 {
  title: "Third"
}
"""
        result = SourceValidator.validate_mandate_spec(text)
        assert any("Non-sequential" in w for w in result["warnings"])

    def test_statistics_contains_mandates_list(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_mandate_spec(VALID_MANDATE_SPEC)
        mandates = result["statistics"]["mandates"]
        assert len(mandates) == 2
        assert mandates[0]["id"] == "M001"


# ---------------------------------------------------------------------------
# validate_guidelines_dsl
# ---------------------------------------------------------------------------


class TestValidateGuidelinesDsl:
    def test_valid_dsl_returns_valid_true(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_guidelines_dsl(VALID_GUIDELINES_DSL)
        assert result["valid"] is True
        assert result["statistics"]["guideline_count"] == 2

    def test_empty_dsl_returns_valid_false(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_guidelines_dsl("")
        assert result["valid"] is False

    def test_empty_guideline_block_reports_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = "guideline G001 {}"
        result = SourceValidator.validate_guidelines_dsl(text)
        assert result["valid"] is False
        assert any("Empty" in e for e in result["errors"])

    def test_duplicate_guideline_ids_report_error(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = VALID_GUIDELINES_DSL + 'guideline G001 { title: "dup" }'
        result = SourceValidator.validate_guidelines_dsl(text)
        assert result["valid"] is False

    def test_no_guidelines_generates_warning(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = "# No guidelines here just text"
        result = SourceValidator.validate_guidelines_dsl(text)
        assert any("No guidelines" in w for w in result["warnings"])

    def test_parses_guideline_ids(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator.validate_guidelines_dsl(VALID_GUIDELINES_DSL)
        ids = result["statistics"]["guideline_ids"]
        assert "G001" in ids
        assert "G002" in ids

    def test_syntax_error_early_returns(self) -> None:
        from sdd_wizard.validator import SourceValidator

        # Unbalanced braces
        text = 'guideline G001 { title: "X"'
        result = SourceValidator.validate_guidelines_dsl(text)
        assert result["valid"] is False


# ---------------------------------------------------------------------------
# validate_source_files
# ---------------------------------------------------------------------------


class TestValidateSourceFiles:
    def test_both_valid_returns_true(self) -> None:
        from sdd_wizard.validator import SourceValidator

        valid, combined = SourceValidator.validate_source_files(
            VALID_MANDATE_SPEC, VALID_GUIDELINES_DSL
        )
        assert valid is True
        assert combined["valid"] is True

    def test_one_invalid_returns_false(self) -> None:
        from sdd_wizard.validator import SourceValidator

        valid, combined = SourceValidator.validate_source_files(
            "", VALID_GUIDELINES_DSL
        )
        assert valid is False
        assert combined["valid"] is False

    def test_combined_errors_merged(self) -> None:
        from sdd_wizard.validator import SourceValidator

        valid, combined = SourceValidator.validate_source_files("", "")
        assert len(combined["errors"]) > 0

    def test_result_has_mandate_and_guidelines_keys(self) -> None:
        from sdd_wizard.validator import SourceValidator

        _, combined = SourceValidator.validate_source_files(
            VALID_MANDATE_SPEC, VALID_GUIDELINES_DSL
        )
        assert "mandate" in combined
        assert "guidelines" in combined


# ---------------------------------------------------------------------------
# _extract_block_field
# ---------------------------------------------------------------------------


class TestExtractBlockField:
    def test_extracts_field(self) -> None:
        from sdd_wizard.validator import SourceValidator

        block = 'title: "My Title"'
        result = SourceValidator._extract_block_field(block, "title")
        assert result == "My Title"

    def test_returns_empty_when_not_found(self) -> None:
        from sdd_wizard.validator import SourceValidator

        result = SourceValidator._extract_block_field("", "title")
        assert result == ""


# ---------------------------------------------------------------------------
# _parse_block_format
# ---------------------------------------------------------------------------


class TestParseBlockFormat:
    def test_parses_multiple_mandates(self) -> None:
        from sdd_wizard.validator import SourceValidator

        mandates, ids = SourceValidator._parse_block_format(VALID_MANDATE_SPEC)
        assert len(mandates) == 2
        assert "M001" in ids

    def test_empty_text_returns_empty(self) -> None:
        from sdd_wizard.validator import SourceValidator

        mandates, ids = SourceValidator._parse_block_format("")
        assert mandates == []
        assert ids == []

    def test_mandate_without_title_uses_id(self) -> None:
        from sdd_wizard.validator import SourceValidator

        text = 'mandate M005 { description: "no title" }'
        mandates, ids = SourceValidator._parse_block_format(text)
        assert mandates[0]["title"] == "M005"
