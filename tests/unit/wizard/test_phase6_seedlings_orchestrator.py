"""Unit tests for sdd_wizard.orchestration.phase6_seedlings_orchestrator.SeedlingsOrchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_orchestrator(tmp_path: Path, verbose: bool = False) -> Any:
    from sdd_wizard.orchestration.phase6_seedlings_orchestrator import (
        SeedlingsOrchestrator,
    )

    output_base = tmp_path / "output"
    output_base.mkdir(parents=True, exist_ok=True)
    governance_core_path = tmp_path / "governance-core.json"
    governance_core_path.write_text(json.dumps({"items": []}), encoding="utf-8")

    return SeedlingsOrchestrator(
        output_base=output_base,
        mandates=[{"id": "M001", "title": "Test Mandate"}],
        guidelines_by_category={
            "git": [{"id": "G001", "title": "Conventional commits"}]
        },
        config={"language": "Python"},
        governance_core_path=governance_core_path,
        paths={},
        verbose=verbose,
    )


class TestSeedlingsOrchestratorInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        assert orch is not None

    def test_verbose_false_by_default(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        assert orch.verbose is False


class TestResolveGovernancePath:
    def test_returns_existing_governance_path(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        result = orch._resolve_governance_path()
        assert result.exists()

    def test_falls_back_to_core_path_when_nothing_found(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase6_seedlings_orchestrator import (
            SeedlingsOrchestrator,
        )

        output_base = tmp_path / "output"
        output_base.mkdir(parents=True, exist_ok=True)
        nonexistent = tmp_path / "does-not-exist.json"

        orch = SeedlingsOrchestrator(
            output_base=output_base,
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=nonexistent,
            paths={},
            verbose=False,
        )
        result = orch._resolve_governance_path()
        # Falls back to governance_core_path (best-effort)
        assert result == nonexistent

    def test_uses_client_compiled_path_when_available(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase6_seedlings_orchestrator import (
            SeedlingsOrchestrator,
        )

        output_base = tmp_path / "output"
        output_base.mkdir(parents=True, exist_ok=True)

        # Create a valid client compiled path
        client_dir = tmp_path / "generated" / "client" / "compiled" / "source"
        client_dir.mkdir(parents=True, exist_ok=True)
        client_governance = client_dir / "governance-core.json"
        client_governance.write_text(json.dumps({"items": []}), encoding="utf-8")

        nonexistent_core = tmp_path / "does-not-exist.json"
        orch = SeedlingsOrchestrator(
            output_base=output_base,
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=nonexistent_core,
            paths={
                "client_compiled": str(tmp_path / "generated" / "client" / "compiled")
            },
            verbose=False,
        )
        result = orch._resolve_governance_path()
        assert result == client_governance


class TestGenerate:
    def test_returns_false_when_generator_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            mock_instance = MagicMock()
            mock_instance.generate_all.return_value = False
            MockGen.return_value = mock_instance

            result = orch.generate()
            assert result is False

    def test_returns_true_when_generator_succeeds(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            mock_instance = MagicMock()
            mock_instance.generate_all.return_value = True
            mock_instance.get_summary.return_value = {
                "count": 5,
                "fingerprint": "abc123",
                "mandates": ["M001"],
                "guidelines": ["git"],
            }
            MockGen.return_value = mock_instance

            result = orch.generate()
            assert result is True

    def test_passes_selected_set_to_generator(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            mock_instance = MagicMock()
            mock_instance.generate_all.return_value = True
            mock_instance.get_summary.return_value = {
                "count": 1,
                "fingerprint": "x",
                "mandates": [],
                "guidelines": [],
            }
            MockGen.return_value = mock_instance

            selected = {"copilot", "claude"}
            orch.generate(selected=selected)
            mock_instance.generate_all.assert_called_once_with(selected=selected)

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            MockGen.side_effect = RuntimeError("unexpected error")
            result = orch.generate()
            assert result is False

    def test_verbose_logs_success(self, tmp_path: Path, capsys: Any) -> None:
        orch = _make_orchestrator(tmp_path, verbose=True)
        with patch(
            "sdd_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator"
        ) as MockGen:
            mock_instance = MagicMock()
            mock_instance.generate_all.return_value = True
            mock_instance.get_summary.return_value = {
                "count": 3,
                "fingerprint": "fp999",
                "mandates": ["M001"],
                "guidelines": ["git"],
            }
            MockGen.return_value = mock_instance

            orch.generate()
            captured = capsys.readouterr()
            assert "seedlings" in captured.out.lower() or "Generated" in captured.out
