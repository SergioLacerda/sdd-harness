"""Tests for Phase456Generator seedling generation and entry points."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sdd_wizard.orchestration.phase_4_5_6_generator import (
    Phase456Generator,
    run_phase_4_5_6_generator,
)

_CONFIG: dict = {"language": "Python"}


def _make_generator(tmp_path: Path) -> Phase456Generator:
    fake_paths = {
        "root": tmp_path,
        "client_compiled": tmp_path / "build",
    }
    with patch(
        "sdd_wizard.orchestration.phase_4_5_6_generator.get_sdd_paths",
        return_value=fake_paths,
    ):
        return Phase456Generator(
            repo_root=tmp_path,
            output_base=tmp_path / "out",
            config=_CONFIG,
        )


class TestGenerateSeedlings:
    def test_returns_true_when_seedlings_generate_succeeds(
        self, tmp_path: Path
    ) -> None:
        generator = _make_generator(tmp_path)
        result: dict = {"errors": []}
        fake_orchestrator = MagicMock()
        fake_orchestrator.generate.return_value = True

        with patch(
            "sdd_wizard.orchestration.phase_4_5_6_generator.SeedlingsOrchestrator",
            return_value=fake_orchestrator,
        ):
            assert generator._generate_seedlings([], {}, result) is True

        assert result["errors"] == []
        fake_orchestrator.generate.assert_called_once_with(
            selected=generator.selected_seedlings
        )

    def test_returns_false_and_records_error_when_seedlings_generate_fails(
        self, tmp_path: Path
    ) -> None:
        generator = _make_generator(tmp_path)
        result: dict = {"errors": []}
        fake_orchestrator = MagicMock()
        fake_orchestrator.generate.return_value = False

        with patch(
            "sdd_wizard.orchestration.phase_4_5_6_generator.SeedlingsOrchestrator",
            return_value=fake_orchestrator,
        ):
            assert generator._generate_seedlings([], {}, result) is False

        assert result["errors"] == ["Failed to generate intelligent seedlings"]


class TestRunEntryPoints:
    def test_run_delegates_to_pipeline(self, tmp_path: Path) -> None:
        generator = _make_generator(tmp_path)
        sentinel = {"success": True}

        with patch(
            "sdd_wizard.orchestration.phase_4_5_6_generator.run_phase456_pipeline",
            return_value=sentinel,
        ) as fake_run:
            assert generator.run() is sentinel

        fake_run.assert_called_once_with(generator)

    def test_run_phase_4_5_6_generator_builds_generator_and_runs_it(
        self, tmp_path: Path
    ) -> None:
        fake_paths = {
            "root": tmp_path,
            "client_compiled": tmp_path / "build",
        }
        sentinel = {"success": True}

        with (
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.get_sdd_paths",
                return_value=fake_paths,
            ),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.run_phase456_pipeline",
                return_value=sentinel,
            ) as fake_run,
        ):
            result = run_phase_4_5_6_generator(tmp_path, tmp_path / "out", _CONFIG)

        assert result is sentinel
        fake_run.assert_called_once()
        called_generator = fake_run.call_args[0][0]
        assert isinstance(called_generator, Phase456Generator)
        assert called_generator.verbose is True
