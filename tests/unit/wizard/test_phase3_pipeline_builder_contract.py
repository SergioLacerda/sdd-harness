from pathlib import Path

import pytest

from sdd_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler


class _FakePipelineBuilder:
    """Minimal stub matching PipelineBuilder API used by Phase3Compiler."""

    def __init__(
        self,
        spec_path: str,
        parsed_items: dict[str, list[dict[str, str]]] | None = None,
    ) -> None:
        self.spec_path = spec_path
        self.parsed_items = parsed_items or {"mandates": [], "guidelines": []}

    def build(self) -> dict[str, object]:
        return {
            "governance_core": {"fingerprint": "core", "version": "3.0"},
            "governance_client": {
                "fingerprint": "client",
                "version": "3.0",
                "fingerprint_core_salt": "core",
            },
            "core_items": [{"id": "M001", "type": "MANDATE"}],
            "client_items": [{"id": "G001", "type": "GUIDELINE"}],
        }

    def save_outputs(self, output_dir: str) -> dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "governance-core.json").write_text(
            '{"category":"CORE","version":"3.0","fingerprint":"core","items":[{"id":"M001","type":"MANDATE"}]}',
            encoding="utf-8",
        )
        (out / "governance-client.json").write_text(
            '{"category":"CLIENT","version":"3.0","fingerprint":"client","fingerprint_core_salt":"core","items":[{"id":"G001","type":"GUIDELINE"}]}',
            encoding="utf-8",
        )
        return {
            "governance_core": str(out / "governance-core.json"),
            "governance_client": str(out / "governance-client.json"),
        }


def test_phase3_uses_pipeline_builder_save_outputs_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "sdd_integration.builders.governance.pipeline_builder.PipelineBuilder",
        _FakePipelineBuilder,
    )

    markdown_input = tmp_path / "generated" / "client" / "build" / "phase-2-input"
    markdown_input.mkdir(parents=True)
    output_path = tmp_path / "generated" / "client" / "compiled"

    compiler = Phase3Compiler(markdown_input, output_path, tmp_path)

    success = compiler.compile_with_pipeline_builder({"mandates": [], "guidelines": []})

    assert success is True
    assert (output_path / "source" / "governance-core.json").exists()
    assert (output_path / "source" / "governance-client.json").exists()
