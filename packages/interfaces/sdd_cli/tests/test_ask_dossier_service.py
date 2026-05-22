from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sdd_cli.services.ask_dossier import load_dossier_artifact


def test_load_dossier_artifact_passes_compiled_path(tmp_path: Path) -> None:
    compiled_dir = tmp_path / ".sdd" / "compiled"
    compiled_dir.mkdir(parents=True)
    artifact_path = compiled_dir / "governance-core.json"
    artifact_path.write_text('{"items": [], "version": "3.0"}', encoding="utf-8")

    def _compiled_active_dir(_workspace_root: Path) -> Path:
        return compiled_dir

    with patch(
        "sdd_runtime.artifacts.CompiledArtifact.from_governance_json"
    ) as mock_loader:
        mock_loader.return_value = object()
        result = load_dossier_artifact(
            tmp_path, compiled_active_dir_fn=_compiled_active_dir
        )

    assert result is not None
    mock_loader.assert_called_once_with(artifact_path)
