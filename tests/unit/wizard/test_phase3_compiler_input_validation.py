from pathlib import Path

from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler


def test_phase3_fails_fast_when_phase2_input_is_empty(tmp_path: Path) -> None:
    markdown_input = tmp_path / "generated" / "client" / "build" / "phase-2-input"
    markdown_input.mkdir(parents=True)

    output_path = tmp_path / "generated" / "client" / "compiled"
    compiler = Phase3Compiler(markdown_input, output_path, tmp_path)

    result = compiler.run()

    assert result["success"] is False
    assert "No staged files found" in result["error"]
