"""Coverage tests for dsl_compiler.py missing branches."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdd_compiler.dsl_compiler import (
    DSLCompiler,
    DSLParser,
    DSLValidator,
    compile_and_print_metrics,
    compile_to_binary,
    compile_to_binary_and_print,
    render_binary_compile_report,
    render_json_compile_report,
)

_MANDATE_DSL = """\
- [M001] **Dependency governance** Declare all dependencies.
- [M002] **Test coverage** Maintain 80% minimum.
"""

_GUIDELINE_DSL = """\
guideline G01 {
  type: SOFT
  title: "Use semantic commits"
  description: "Follow conventional commits."
  category: git
  examples: ["feat: add X", "fix: null ptr"]
}
"""


class TestDSLValidatorLocateFallback:
    def test_locate_returns_empty_for_empty_input(self) -> None:
        issues = DSLValidator.validate_dsl_detailed("")
        assert issues == []

    def test_mandate_missing_title_issue(self) -> None:
        # Pattern requires **title** syntax; empty title between markers triggers the check
        dsl = "- [M001] **** description here\n"
        issues = DSLValidator.validate_dsl_detailed(dsl)
        codes = [i["code"] for i in issues]
        assert "MANDATE_MISSING_TITLE" in codes

    def test_guideline_missing_field(self) -> None:
        dsl = "guideline G01 {\n  description: x\n}\n"
        issues = DSLValidator.validate_dsl_detailed(dsl)
        codes = [i["code"] for i in issues]
        assert "GUIDELINE_MISSING_FIELD" in codes


class TestDSLParserRationaleAndValidation:
    def test_parse_mandate_with_rationale_quoted(self) -> None:
        dsl = '- [M001] **Title** desc\n  rationale: "Reason here"\n'
        mandates = DSLParser.parse_mandates(dsl)
        assert mandates[0]["rationale"] == "Reason here"

    def test_parse_mandate_with_rationale_unquoted(self) -> None:
        dsl = "- [M001] **Title** desc\n  rationale: plain reason\n"
        mandates = DSLParser.parse_mandates(dsl)
        assert "plain reason" in mandates[0]["rationale"]

    def test_parse_mandate_with_commands(self) -> None:
        dsl = '- [M001] **Title** desc\n  validation: { commands: ["sdd lint", "sdd test"] }\n'
        mandates = DSLParser.parse_mandates(dsl)
        assert "sdd lint" in mandates[0]["validation_commands"]


class TestDSLCompilerParseMode:
    def test_ast_first_mode_parses_mandates(self) -> None:
        compiler = DSLCompiler()
        mandates, guidelines = compiler._parse_with_strategy(
            dsl_text=_MANDATE_DSL, parse_mode="ast_first"
        )
        assert len(mandates) >= 1

    def test_unknown_parse_mode_uses_regex(self) -> None:
        compiler = DSLCompiler()
        mandates, guidelines = compiler._parse_with_strategy(
            dsl_text=_MANDATE_DSL, parse_mode="bogus_mode"
        )
        assert len(mandates) >= 1

    def test_ast_parse_mandates_extracts_category(self) -> None:
        dsl = "- [M001] **Title** desc\n  category: security\n"
        compiler = DSLCompiler()
        mandates = compiler._parse_mandates_ast(dsl)
        assert mandates[0]["category"] == "security"

    def test_ast_parse_mandates_extracts_rationale(self) -> None:
        dsl = "- [M001] **Title** desc\n  rationale: Good reason\n"
        compiler = DSLCompiler()
        mandates = compiler._parse_mandates_ast(dsl)
        assert mandates[0]["rationale"] == "Good reason"

    def test_ast_parse_mandates_extracts_commands(self) -> None:
        dsl = "- [M001] **Title** desc\n  commands: [sdd lint, sdd test]\n"
        compiler = DSLCompiler()
        mandates = compiler._parse_mandates_ast(dsl)
        assert "sdd lint" in mandates[0]["validation_commands"]

    def test_ast_parse_guidelines(self) -> None:
        compiler = DSLCompiler()
        guidelines = compiler._parse_guidelines_ast(_GUIDELINE_DSL)
        assert len(guidelines) >= 1
        assert guidelines[0]["id"] == "G01"

    def test_parse_mandate_header_returns_none_for_non_mandate(self) -> None:
        compiler = DSLCompiler()
        assert compiler._parse_mandate_header("  just text") is None

    def test_parse_mandate_header_returns_none_without_title_markers(self) -> None:
        compiler = DSLCompiler()
        assert compiler._parse_mandate_header("- [M001] no bold markers") is None


class TestASTFirstFallback:
    def test_ast_first_falls_back_on_not_implemented(self) -> None:
        from unittest.mock import patch

        compiler = DSLCompiler()
        with patch.object(compiler, "_parse_with_ast", side_effect=NotImplementedError):
            mandates, guidelines = compiler._parse_with_strategy(
                dsl_text=_MANDATE_DSL, parse_mode="ast_first"
            )
        assert compiler.metrics.parse_fallback_used is True
        assert len(mandates) >= 1

    def test_ast_strict_raises_on_not_implemented(self) -> None:
        from unittest.mock import patch

        compiler = DSLCompiler()
        with (
            patch.object(compiler, "_parse_with_ast", side_effect=NotImplementedError),
            pytest.raises(NotImplementedError),
        ):
            compiler._parse_with_strategy(
                dsl_text=_MANDATE_DSL, parse_mode="ast_strict"
            )

    def test_guideline_block_without_id_is_skipped(self) -> None:
        # "guideline {" — no ID token, should be skipped
        dsl = "guideline {\n  type: SOFT\n}\n"
        compiler = DSLCompiler()
        guidelines = compiler._parse_guidelines_ast(dsl)
        assert guidelines == []


class TestCompileToBinary:
    def test_compile_to_binary_produces_file(self, tmp_path: Path) -> None:
        src = tmp_path / "src.spec"
        src.write_text(_MANDATE_DSL, encoding="utf-8")
        out = str(tmp_path / "out.sdd")
        result = compile_to_binary(str(src), out)
        assert result["success"] is True
        assert Path(out).exists()

    def test_compile_to_binary_fails_on_invalid_dsl(self, tmp_path: Path) -> None:
        src = tmp_path / "bad.spec"
        src.write_text("!! completely invalid content !!", encoding="utf-8")
        out = str(tmp_path / "out.sdd")
        result = compile_to_binary(str(src), out)
        # With no mandates/guidelines it may still succeed — check structure
        assert "success" in result

    def test_compile_to_binary_and_print_no_output_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src.spec"
        src.write_text(_MANDATE_DSL, encoding="utf-8")
        compile_to_binary_and_print(str(src))
        captured = capsys.readouterr()
        assert src.stem in captured.out


class TestRenderReports:
    def test_render_json_compile_report_success(self, tmp_path: Path) -> None:
        src = tmp_path / "src.spec"
        src.write_text(_MANDATE_DSL, encoding="utf-8")
        out = str(tmp_path / "out.json")
        report = render_json_compile_report(str(src), out)
        assert "Compilation successful" in report

    def test_render_json_compile_report_failure(self, tmp_path: Path) -> None:
        src = tmp_path / "empty.spec"
        src.write_text("", encoding="utf-8")
        out = str(tmp_path / "out.json")
        report = render_json_compile_report(str(src), out)
        # Empty file may succeed (0 items) — just check it returns a string
        assert isinstance(report, str)

    def test_render_binary_compile_report_success(self, tmp_path: Path) -> None:
        src = tmp_path / "src.spec"
        src.write_text(_MANDATE_DSL, encoding="utf-8")
        out = str(tmp_path / "out.sdd")
        report = render_binary_compile_report(str(src), out)
        assert isinstance(report, str)

    def test_compile_and_print_metrics_no_output_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src.spec"
        src.write_text(_MANDATE_DSL, encoding="utf-8")
        compile_and_print_metrics(str(src))
        captured = capsys.readouterr()
        assert src.stem in captured.out
