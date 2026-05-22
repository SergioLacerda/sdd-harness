"""
Tests for DSL Compiler

Tests parsing, compilation, and metrics generation.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, cast

import pytest

from sdd_compiler.dsl_compiler import (
    CompilationMetrics,
    DSLCompiler,
    DSLParser,
    DSLValidator,
    StringPool,
    compile_file,
    compile_string,
    render_binary_compile_report,
    render_json_compile_report,
)


class TestDSLValidator:
    """Test DSL validation"""

    def test_valid_mandate_syntax(self) -> None:
        """Test valid mandate syntax passes validation"""
        dsl = """
        - [M001] **Test Mandate** Test description
        """
        errors = DSLValidator.validate_dsl(dsl)
        assert len(errors) == 0

    def test_mandate_id_must_be_sequential(self) -> None:
        """Test mandate IDs must be sequential"""
        dsl = """
        - [M001] **First** Test
        - [M003] **Third** Test
        """
        errors = DSLValidator.validate_dsl(dsl)
        assert any("not sequential" in e for e in errors)

    def test_mandate_missing_required_field(self) -> None:
        """Test mandate must have required fields"""
        dsl = """
        - [M001] **** Test
        """
        errors = DSLValidator.validate_dsl(dsl)
        assert any("missing field" in e for e in errors)

    def test_valid_guideline_syntax(self) -> None:
        """Test valid guideline syntax passes validation"""
        dsl = """
        guideline G01 {
          type: SOFT
          title: "Test Guideline"
          description: "Test description"
          category: general
        }
        """
        errors = DSLValidator.validate_dsl(dsl)
        assert len(errors) == 0

    def test_guideline_id_must_be_sequential(self) -> None:
        """Test guideline IDs must be sequential"""
        dsl = """
        guideline G01 {
          type: SOFT
          title: "First"
          description: "Test"
        }
        guideline G03 {
          type: SOFT
          title: "Third"
          description: "Test"
        }
        """
        errors = DSLValidator.validate_dsl(dsl)
        assert any("not sequential" in e for e in errors)

    def test_detailed_validation_has_position_and_hint(self) -> None:
        dsl = """
        - [M001] **First** Test
        - [M003] **Third** Test
        """
        issues = DSLValidator.validate_dsl_detailed(dsl)
        assert len(issues) > 0
        first = issues[0]
        assert first["code"] == "MANDATE_IDS_NOT_SEQUENTIAL"
        assert first["line"] >= 1
        assert first["column"] >= 1
        assert "M003" in first["snippet"] or "M001" in first["snippet"]
        assert first["hint"] != ""


class TestDSLParser:
    """Test DSL parsing"""

    def test_parse_simple_mandate(self) -> None:
        """Test parsing simple mandate"""
        dsl = """
        - [M001] **Clean Architecture** Applications MUST...
        """
        mandates = DSLParser.parse_mandates(dsl)

        assert len(mandates) == 1
        assert mandates[0]["id"] == "M001"
        assert mandates[0]["type"] == "HARD"
        assert mandates[0]["title"] == "Clean Architecture"
        assert mandates[0]["category"] == "core"

    def test_parse_mandate_with_validation(self) -> None:
        """Test parsing mandate with validation commands"""
        dsl = """
        - [M001] **Test** Test
        Validation: { commands: ["pytest", "coverage"] }
        ---
        """
        mandates = DSLParser.parse_mandates(dsl)

        assert len(mandates) == 1
        assert mandates[0]["validation_commands"] == ["pytest", "coverage"]

    def test_parse_multiple_mandates(self) -> None:
        """Test parsing multiple mandates"""
        dsl = """
        - [M001] **First** Test
        ---
        - [M002] **Second** Test
        ---
        """
        mandates = DSLParser.parse_mandates(dsl)

        assert len(mandates) == 2
        assert mandates[0]["id"] == "M001"
        assert mandates[1]["id"] == "M002"

    def test_parse_simple_guideline(self) -> None:
        """Test parsing simple guideline"""
        dsl = """
        guideline G01 {
          type: SOFT
          title: "Test Guideline"
          description: "Guidelines..."
          category: general
        }
        """
        guidelines = DSLParser.parse_guidelines(dsl)

        assert len(guidelines) == 1
        assert guidelines[0]["id"] == "G01"
        assert guidelines[0]["type"] == "SOFT"
        assert guidelines[0]["title"] == "Test Guideline"

    def test_parse_guideline_with_examples(self) -> None:
        """Test parsing guideline with examples"""
        dsl = """
        guideline G01 {
          type: SOFT
          title: "Test"
          description: "Test"
          examples: ["Example 1", "Example 2"]
        }
        """
        guidelines = DSLParser.parse_guidelines(dsl)

        assert len(guidelines) == 1
        assert guidelines[0]["examples"] == ["Example 1", "Example 2"]

    def test_parse_multiple_guidelines(self) -> None:
        """Test parsing multiple guidelines"""
        dsl = """
        guideline G01 {
          type: SOFT
          title: "First"
          description: "Test"
        }
        guideline G02 {
          type: SOFT
          title: "Second"
          description: "Test"
        }
        """
        guidelines = DSLParser.parse_guidelines(dsl)

        assert len(guidelines) == 2
        assert guidelines[0]["id"] == "G01"
        assert guidelines[1]["id"] == "G02"


class TestStringPool:
    """Test string deduplication"""

    def test_string_deduplication(self) -> None:
        """Test identical strings get same index"""
        pool = cast(Any, StringPool())

        idx1 = pool.add("Common String")
        idx2 = pool.add("Common String")

        assert idx1 == idx2
        assert len(pool.pool) == 1

    def test_different_strings_different_indices(self) -> None:
        """Test different strings get different indices"""
        pool = cast(Any, StringPool())

        idx1 = pool.add("String 1")
        idx2 = pool.add("String 2")

        assert idx1 != idx2
        assert len(pool.pool) == 2

    def test_none_strings_ignored(self) -> None:
        """Test None strings don't get added"""
        pool = cast(Any, StringPool())

        idx = pool.add(None)

        assert idx is None
        assert len(pool.pool) == 0

    def test_empty_strings_ignored(self) -> None:
        """Test empty strings don't get added"""
        pool = cast(Any, StringPool())

        idx = pool.add("")

        assert idx is None
        assert len(pool.pool) == 0

    def test_pool_array_generation(self) -> None:
        """Test pool array generation"""
        pool = cast(Any, StringPool())

        idx1 = pool.add("First")
        idx2 = pool.add("Second")
        assert idx1 is not None
        assert idx2 is not None

        pool_array = pool.get_array()

        assert len(pool_array) == 2
        assert pool_array[idx1] == "First"
        assert pool_array[idx2] == "Second"


class TestDSLCompiler:
    """Test DSL compiler"""

    def test_compile_single_mandate(self) -> None:
        """Test compiling single mandate"""
        dsl = """
        - [M001] **Clean Architecture** Applications MUST...
        ---
        """
        compiler = cast(Any, DSLCompiler())
        output = compiler.compile(dsl)

        assert output is not None
        assert len(output["mandates"]) == 1
        assert output["mandates"][0]["id"] == 1

    def test_compile_single_guideline(self) -> None:
        """Test compiling single guideline"""
        dsl = """
        guideline G01 {
          type: SOFT
          title: "Test Guideline"
          description: "Guidelines..."
          category: general
        }
        """
        compiler = cast(Any, DSLCompiler())
        output = compiler.compile(dsl)

        assert output is not None
        assert len(output["guidelines"]) == 1
        assert output["guidelines"][0]["id"] == 1

    def test_compile_with_string_deduplication(self) -> None:
        """Test string deduplication during compilation"""
        dsl = """
        - [M001] **Shared Title** Shared Title
        ---
        """
        compiler = cast(Any, DSLCompiler())
        compiler.compile(dsl)

        # "Shared Title" should only appear once in pool
        assert len(compiler.string_pool.pool) == 1

    def test_compilation_metrics(self) -> None:
        """Test compilation metrics"""
        dsl = """
        - [M001] **Test** Test
        ---
        """
        compiler = cast(Any, DSLCompiler())
        compiler.compile(dsl)

        metrics = compiler.get_metrics()

        assert metrics.input_size > 0
        assert metrics.output_size > 0
        assert metrics.compilation_time_ms >= 0
        assert metrics.mandates_compiled == 1
        assert metrics.success

    def test_compression_ratio(self) -> None:
        """Test compression ratio calculation"""
        metrics = CompilationMetrics(input_size=1000, output_size=400)

        assert metrics.compression_ratio == 0.6  # 60%

    def test_validation_error_handling(self) -> None:
        """Test validation errors are caught"""
        dsl = """
        - [M001] **** Test
        ---
        """
        compiler = cast(Any, DSLCompiler())
        output = compiler.compile(dsl, validate=True)

        assert output is None
        assert len(compiler.metrics.errors) > 0
        assert len(compiler.metrics.structured_errors) > 0

    def test_parse_mode_ast_first_uses_ast_backend(self) -> None:
        dsl = """
        - [M001] **Test** Test
        ---
        """
        compiler = cast(Any, DSLCompiler())
        output = compiler.compile(dsl, parse_mode="ast_first")
        assert output is not None
        assert compiler.metrics.parse_mode == "ast_first"
        assert compiler.metrics.parse_backend == "ast"
        assert compiler.metrics.parse_fallback_used is False

    def test_parse_mode_ast_strict_uses_ast_backend(self) -> None:
        dsl = """
        - [M001] **Test** Test
        ---
        """
        compiler = cast(Any, DSLCompiler())
        output = compiler.compile(dsl, parse_mode="ast_strict")
        assert output is not None
        assert compiler.metrics.parse_backend == "ast"
        assert compiler.metrics.parse_fallback_used is False

    def test_parse_mode_unknown_defaults_to_regex(self) -> None:
        dsl = """
        - [M001] **Test** Test
        ---
        """
        compiler = cast(Any, DSLCompiler())
        output = compiler.compile(dsl, parse_mode="invalid_mode")
        assert output is not None
        assert compiler.metrics.parse_backend == "regex"
        assert any("Unknown parse mode" in w for w in compiler.metrics.warnings)


class TestIntegration:
    """Integration tests"""

    def test_compile_mixed_mandates_and_guidelines(self) -> None:
        """Test compiling mixed content"""
        dsl = """
        - [M001] **Mandate One** Description one
        ---
        - [M002] **Mandate Two** Description two
        ---
        guideline G01 {
          type: SOFT
          title: "Guideline One"
          description: "Description one"
          category: git
        }
        guideline G02 {
          type: SOFT
          title: "Guideline Two"
          description: "Description two"
          category: general
        }
        """
        output, metrics = compile_string(dsl)

        assert output is not None
        assert len(output["mandates"]) == 2
        assert len(output["guidelines"]) == 2
        assert metrics.mandates_compiled == 2
        assert metrics.guidelines_compiled == 2

    def test_compile_to_file(self) -> None:
        """Test compiling to file"""
        dsl = """
        - [M001] **Test** Test
        ---
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.spec"
            output_file = Path(tmpdir) / "test.compiled.json"

            input_file.write_text(dsl, encoding="utf-8")

            metrics = compile_file(str(input_file), str(output_file))

            assert metrics.success
            assert output_file.exists()

            with open(output_file, encoding="utf-8") as f:
                output = json.load(f)

            assert len(output["mandates"]) == 1

    def test_compile_complex_structure(self) -> None:
        """Test compiling complex structure"""
        dsl = """
        - [M001] **Complex Mandate** This is a complex description with multiple sentences and details.
        ---
        guideline G01 {
          type: SOFT
          title: "Complex Guideline"
          description: "This is a complex guideline with detailed information."
          category: general
          examples: ["Example 1 with details", "Example 2 with more details", "Example 3"]
        }
        """
        output, metrics = compile_string(dsl)

        assert output is not None
        assert metrics.success
        # Note: Small test cases may have negative compression due to JSON overhead
        # Real data (mandate.spec + guidelines.dsl) will show >65% compression

    def test_render_json_compile_report_success(self) -> None:
        dsl = """
        - [M001] **Test** Test
        ---
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.spec"
            output_file = Path(tmpdir) / "test.compiled.json"
            input_file.write_text(dsl, encoding="utf-8")
            report = render_json_compile_report(str(input_file), str(output_file))
            assert "Compilation successful" in report
            assert f"Output: {output_file}" in report

    def test_render_json_compile_report_failure(self) -> None:
        dsl = """
        - [M001] **** Test
        ---
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "bad.spec"
            output_file = Path(tmpdir) / "bad.compiled.json"
            input_file.write_text(dsl, encoding="utf-8")
            report = render_json_compile_report(str(input_file), str(output_file))
            assert "Compilation FAILED" in report

    def test_render_binary_compile_report_success(self) -> None:
        dsl = """
        - [M001] **Test** Test
        ---
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.spec"
            output_file = Path(tmpdir) / "test.compiled.msgpack"
            input_file.write_text(dsl, encoding="utf-8")
            report = render_binary_compile_report(str(input_file), str(output_file))
            if "msgpack not installed" in report:
                assert "ERROR" in report
            else:
                assert "Binary compilation successful" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
