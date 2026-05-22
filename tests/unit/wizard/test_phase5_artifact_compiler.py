"""Unit tests for sdd_wizard.orchestration.phase5_artifact_compiler.ArtifactCompiler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers.text_io import read_text_utf8

pytestmark = pytest.mark.unit


SAMPLE_MANDATES = [
    {"id": "M001", "title": "Use Type Hints"},
    {"id": "M002", "title": "Write Tests"},
]

SAMPLE_GUIDELINES = {
    "G001": {"id": "G001", "title": "Conventional commits", "category": "git"},
}

SAMPLE_BY_CATEGORY = {
    "git": [SAMPLE_GUIDELINES["G001"]],
}


def _make_compiler(
    tmp_path: Path,
    mandates: list[Any] | None = None,
    guidelines: dict[str, dict[str, Any]] | None = None,
    by_category: dict[str, list[Any]] | None = None,
    config: dict[str, Any] | None = None,
) -> Any:
    from sdd_wizard.orchestration.phase5_artifact_compiler import ArtifactCompiler

    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = tmp_path / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    return ArtifactCompiler(
        repo_root=tmp_path,
        sdd_dir=sdd_dir,
        runtime_dir=runtime_dir,
        mandates=mandates if mandates is not None else SAMPLE_MANDATES,
        guidelines=guidelines if guidelines is not None else SAMPLE_GUIDELINES,
        guidelines_by_category=(
            by_category if by_category is not None else SAMPLE_BY_CATEGORY
        ),
        config=config or {"language": "Python", "adoption_level": "FULL"},
        verbose=False,
    )


class TestArtifactCompilerInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler is not None

    def test_initial_fingerprint_unknown(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler.governance_fingerprint == "unknown"

    def test_initial_generated_at_unknown(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        assert compiler.generated_at == "unknown"


class TestGenerateMetadata:
    def test_returns_true(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.generate_metadata()
        assert result is True

    def test_creates_metadata_json(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        compiler.generate_metadata()
        assert (tmp_path / ".sdd" / "metadata.json").exists()

    def test_metadata_json_has_version(self, tmp_path: Path) -> None:
        import json

        compiler = _make_compiler(tmp_path)
        compiler.generate_metadata()
        data = json.loads(read_text_utf8(tmp_path / ".sdd" / "metadata.json"))
        assert "version" in data

    def test_metadata_fingerprint_set(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        compiler.generate_metadata()
        assert compiler.governance_fingerprint != "unknown"

    def test_metadata_generated_at_set(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        compiler.generate_metadata()
        assert compiler.generated_at != "unknown"

    def test_metadata_contains_mandates_count(self, tmp_path: Path) -> None:
        import json

        compiler = _make_compiler(tmp_path)
        compiler.generate_metadata()
        data = json.loads(read_text_utf8(tmp_path / ".sdd" / "metadata.json"))
        assert data["mandates_count"] == 2

    def test_metadata_empty_mandates(self, tmp_path: Path) -> None:
        import json

        compiler = _make_compiler(tmp_path, mandates=[])
        compiler.generate_metadata()
        data = json.loads(read_text_utf8(tmp_path / ".sdd" / "metadata.json"))
        assert data["mandates_count"] == 0


class TestCompileArtifacts:
    def test_returns_true_when_no_spec_dir(self, tmp_path: Path) -> None:
        # No spec directory → logs and returns True (non-critical)
        compiler = _make_compiler(tmp_path)
        result = compiler.compile_artifacts()
        assert result is True

    def test_returns_true_when_spec_dir_exists_but_no_files(
        self, tmp_path: Path
    ) -> None:
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        compiler = _make_compiler(tmp_path)
        result = compiler.compile_artifacts()
        assert result is True

    def test_compiles_mandate_spec_when_present(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "mandate.spec").write_text(
            'mandate M001 { title: "Test" }', encoding="utf-8"
        )
        compiler = _make_compiler(tmp_path)
        result = compiler.compile_artifacts()
        assert result is True

    def test_compiles_guidelines_dsl_when_present(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "guidelines.dsl").write_text(
            'guideline G001 { title: "Test" }', encoding="utf-8"
        )
        compiler = _make_compiler(tmp_path)
        result = compiler.compile_artifacts()
        assert result is True

    def test_verbose_log_called(self, tmp_path: Path, capsys: Any) -> None:
        from sdd_wizard.orchestration.phase5_artifact_compiler import ArtifactCompiler

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir(parents=True, exist_ok=True)
        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        compiler = ArtifactCompiler(
            repo_root=tmp_path,
            sdd_dir=sdd_dir,
            runtime_dir=runtime_dir,
            mandates=[],
            guidelines={},
            guidelines_by_category={},
            config={},
            verbose=True,
        )
        compiler.compile_artifacts()
        captured = capsys.readouterr()
        assert "Compiling" in captured.out or "spec" in captured.out.lower()
