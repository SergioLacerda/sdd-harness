"""Tests for WizardOrchestrator — 7-phase pipeline and CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_SDD_PATHS = {
    "root": Path("/fake/root"),
    "client_build": Path("/fake/build"),
    "client_compiled": Path("/fake/compiled"),
    "master_compiled": Path("/fake/master"),
    "packages": Path("/fake/packages"),
    "source_spec": Path("/fake/spec"),
}


def _report(
    name: str,
    success: bool = True,
    data: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> tuple[bool, dict[str, Any]]:
    return success, {
        "phase": name,
        "status": "SUCCESS" if success else "FAILED",
        "data": data or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "checks": {},
    }


def _p2_data(
    mandates: dict | None = None,
    guidelines: dict | None = None,
    artifacts: dict | None = None,
) -> dict[str, Any]:
    return {
        "mandate": mandates if mandates is not None else {"M001": {}},
        "guidelines": guidelines if guidelines is not None else {"G001": {}},
        "_artifacts": artifacts or {},
        "metadata": {"version": "3.0"},
    }


@pytest.fixture
def orch():
    with patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS):
        from sdd_wizard.src.wizard import WizardOrchestrator

        return WizardOrchestrator()


@pytest.fixture
def orch_verbose():
    with patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS):
        from sdd_wizard.src.wizard import WizardOrchestrator

        return WizardOrchestrator(verbose=True)


class TestInit:
    def test_repo_root_from_sdd_paths(self) -> None:
        with patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS):
            from sdd_wizard.src.wizard import WizardOrchestrator

            orch = WizardOrchestrator()
        assert orch.repo_root == Path("/fake/root")

    def test_explicit_repo_root_overrides(self, tmp_path: Path) -> None:
        with patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS):
            from sdd_wizard.src.wizard import WizardOrchestrator

            orch = WizardOrchestrator(repo_root=tmp_path)
        assert orch.repo_root == tmp_path

    def test_verbose_defaults_false(self, orch) -> None:
        assert orch.verbose is False

    def test_verbose_true(self, orch_verbose) -> None:
        assert orch_verbose.verbose is True

    def test_phases_and_artifacts_empty_on_init(self, orch) -> None:
        assert orch.phases_results == {}
        assert orch.artifacts == {}


class TestLog:
    def test_info_always_prints(self, orch, capsys) -> None:
        orch.log("INFO", "test message")
        assert "test message" in capsys.readouterr().out

    def test_debug_silent_when_not_verbose(self, orch, capsys) -> None:
        orch.log("DEBUG", "should not appear")
        assert "should not appear" not in capsys.readouterr().out

    def test_debug_prints_when_verbose(self, orch_verbose, capsys) -> None:
        orch_verbose.log("DEBUG", "verbose message")
        assert "verbose message" in capsys.readouterr().out

    def test_timestamp_present_in_info(self, orch, capsys) -> None:
        orch.log("INFO", "msg")
        out = capsys.readouterr().out
        assert "INFO" in out


class TestPrintPhaseHeader:
    def test_outputs_phase_number_and_name(self, orch, capsys) -> None:
        orch.print_phase_header(3, "Filter Mandates")
        out = capsys.readouterr().out
        assert "Phase 3" in out
        assert "Filter Mandates" in out


class TestPrintPhaseResult:
    def test_success_status(self, orch, capsys) -> None:
        orch.print_phase_result(
            True, {"phase": "P1", "data": None, "warnings": [], "errors": []}
        )
        assert "SUCCESS" in capsys.readouterr().out

    def test_failure_status(self, orch, capsys) -> None:
        orch.print_phase_result(
            False, {"phase": "P1", "data": None, "warnings": [], "errors": []}
        )
        assert "FAILED" in capsys.readouterr().out

    def test_data_printed_when_truthy(self, orch, capsys) -> None:
        orch.print_phase_result(
            True, {"phase": "P1", "data": {"k": "v"}, "warnings": [], "errors": []}
        )
        assert "Data" in capsys.readouterr().out

    def test_no_data_section_for_empty_dict(self, orch, capsys) -> None:
        orch.print_phase_result(
            True, {"phase": "P1", "data": {}, "warnings": [], "errors": []}
        )
        assert "Data:" not in capsys.readouterr().out

    def test_warnings_are_printed(self, orch, capsys) -> None:
        orch.print_phase_result(
            True, {"phase": "P1", "data": {}, "warnings": ["w1", "w2"], "errors": []}
        )
        out = capsys.readouterr().out
        assert "Warning" in out
        assert "w1" in out

    def test_errors_suppressed_when_not_verbose(self, orch, capsys) -> None:
        orch.print_phase_result(
            False, {"phase": "P1", "data": {}, "warnings": [], "errors": ["err1"]}
        )
        assert "err1" not in capsys.readouterr().out

    def test_errors_printed_when_verbose(self, orch_verbose, capsys) -> None:
        orch_verbose.print_phase_result(
            False, {"phase": "P1", "data": {}, "warnings": [], "errors": ["err1"]}
        )
        assert "err1" in capsys.readouterr().out


class TestRunPhase1:
    def test_success(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_1_validate_source",
            return_value=_report("P1", True),
        ):
            assert orch.run_phase_1() is True

    def test_failure(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_1_validate_source",
            return_value=_report("P1", False),
        ):
            assert orch.run_phase_1() is False

    def test_stores_report(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_1_validate_source",
            return_value=_report("P1", True),
        ):
            orch.run_phase_1()
        assert "phase_1" in orch.phases_results


class TestRunPhase2:
    def test_success_without_artifacts(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_2_load_compiled",
            return_value=_report("P2", True),
        ):
            assert orch.run_phase_2() is True
        assert orch.artifacts == {}

    def test_artifacts_stored_when_present(self, orch) -> None:
        # _artifacts is a top-level key in the report dict, not nested inside data
        _, base_report = _report("P2", True)
        report_with_artifacts = {**base_report, "_artifacts": {"key": "val"}}
        with patch(
            "sdd_wizard.src.wizard.phase_2_load_compiled",
            return_value=(True, report_with_artifacts),
        ):
            orch.run_phase_2()
        assert orch.artifacts == {"key": "val"}

    def test_failure(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_2_load_compiled",
            return_value=_report("P2", False),
        ):
            assert orch.run_phase_2() is False


class TestRunPhase3:
    def test_success_with_mandates(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"mandate": {"M001": {}}}}
        with patch(
            "sdd_wizard.src.wizard.phase_3_filter_mandates",
            return_value=_report("P3", True),
        ):
            assert orch.run_phase_3() is True

    def test_fails_when_no_mandates(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"mandate": {}}}
        assert orch.run_phase_3() is False

    def test_fails_when_no_phase_2_data(self, orch) -> None:
        assert orch.run_phase_3() is False

    def test_failure_from_filter(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"mandate": {"M001": {}}}}
        with patch(
            "sdd_wizard.src.wizard.phase_3_filter_mandates",
            return_value=_report("P3", False),
        ):
            assert orch.run_phase_3() is False

    def test_passes_mandate_ids(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"mandate": {"M001": {}}}}
        with patch(
            "sdd_wizard.src.wizard.phase_3_filter_mandates",
            return_value=_report("P3", True),
        ) as mock:
            orch.run_phase_3(mandates=["M001"])
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs.get("selected_mandate_ids") == ["M001"] or mock.call_args[0][
            1
        ] == ["M001"]


class TestRunPhase4:
    def test_success_with_guidelines(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"guidelines": {"G001": {}}}}
        with patch(
            "sdd_wizard.src.wizard.phase_4_filter_guidelines",
            return_value=_report("P4", True),
        ):
            assert orch.run_phase_4() is True

    def test_fails_when_no_guidelines(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"guidelines": {}}}
        assert orch.run_phase_4() is False

    def test_failure_from_filter(self, orch) -> None:
        orch.phases_results["phase_2"] = {"data": {"guidelines": {"G001": {}}}}
        with patch(
            "sdd_wizard.src.wizard.phase_4_filter_guidelines",
            return_value=_report("P4", False),
        ):
            assert orch.run_phase_4() is False


class TestRunPhase5:
    def test_success_with_explicit_output_dir(self, orch, tmp_path: Path) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_5_apply_template",
            return_value=_report("P5", True),
        ):
            assert orch.run_phase_5(output_dir=tmp_path) is True

    def test_success_with_default_output_dir(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_5_apply_template",
            return_value=_report("P5", True),
        ):
            assert orch.run_phase_5() is True

    def test_failure(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_5_apply_template",
            return_value=_report("P5", False),
        ):
            assert orch.run_phase_5() is False


class TestRunPhase6:
    def _setup(self, orch) -> None:
        orch.phases_results["phase_1"] = {
            "data": {"mandate_text": "mt", "guidelines_text": "gt"}
        }
        orch.phases_results["phase_2"] = {"data": {"metadata": {"version": "3.0"}}}
        orch.phases_results["phase_3"] = {"data": {"filtered_mandates": {"M001": {}}}}
        orch.phases_results["phase_4"] = {"data": {"filtered_guidelines": {"G001": {}}}}

    def test_success_with_output_dir(self, orch, tmp_path: Path) -> None:
        self._setup(orch)
        with patch(
            "sdd_wizard.src.wizard.phase_6_generate_project",
            return_value=_report("P6", True),
        ):
            assert orch.run_phase_6(output_dir=tmp_path) is True

    def test_success_default_output_dir(self, orch) -> None:
        self._setup(orch)
        with patch(
            "sdd_wizard.src.wizard.phase_6_generate_project",
            return_value=_report("P6", True),
        ):
            assert orch.run_phase_6() is True

    def test_failure(self, orch) -> None:
        self._setup(orch)
        with patch(
            "sdd_wizard.src.wizard.phase_6_generate_project",
            return_value=_report("P6", False),
        ):
            assert orch.run_phase_6() is False

    def test_missing_prior_phase_data_uses_defaults(self, orch) -> None:
        with patch(
            "sdd_wizard.src.wizard.phase_6_generate_project",
            return_value=_report("P6", True),
        ):
            assert orch.run_phase_6() is True


class TestRunPhase7:
    def test_success_with_project_dir(self, orch, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_wizard.src.wizard.phase_7_validate_output",
                return_value=_report("P7", True),
            ),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            assert orch.run_phase_7(project_dir=tmp_path) is True

    def test_success_default_project_dir(self, orch) -> None:
        with (
            patch(
                "sdd_wizard.src.wizard.phase_7_validate_output",
                return_value=_report("P7", True),
            ),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            assert orch.run_phase_7() is True

    def test_failure(self, orch) -> None:
        with (
            patch(
                "sdd_wizard.src.wizard.phase_7_validate_output",
                return_value=_report("P7", False),
            ),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            assert orch.run_phase_7() is False

    def test_ensure_context_cache_always_called(self, orch, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_wizard.src.wizard.phase_7_validate_output",
                return_value=_report("P7", True),
            ),
            patch("sdd_wizard.src.wizard.ensure_context_cache") as mock_cache,
        ):
            orch.run_phase_7(project_dir=tmp_path)
        mock_cache.assert_called_once()


class TestRunFullPipeline:
    def _all_pass(self) -> tuple:
        p1 = _report("P1", True)
        p2 = _report("P2", True, data=_p2_data())
        p3 = _report("P3", True, data={"filtered_mandates": {"M001": {}}})
        p4 = _report("P4", True, data={"filtered_guidelines": {"G001": {}}})
        p5 = _report("P5", True)
        p6 = _report("P6", True)
        p7 = _report("P7", True)
        return p1, p2, p3, p4, p5, p6, p7

    def _pipeline_patches(self, p1, p2, p3, p4, p5, p6, p7):
        return (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
            patch("sdd_wizard.src.wizard.phase_7_validate_output", return_value=p7),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        )

    def test_full_success(self, orch) -> None:
        patches = self._pipeline_patches(*self._all_pass())
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            assert orch.run_full_pipeline() is True

    def test_stops_at_phase_1(self, orch) -> None:
        p1 = _report("P1", False)
        with patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1):
            assert orch.run_full_pipeline() is False

    def test_stops_at_phase_2(self, orch) -> None:
        p1 = _report("P1", True)
        p2 = _report("P2", False)
        with (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
        ):
            assert orch.run_full_pipeline() is False

    def test_stops_at_phase_3(self, orch) -> None:
        p1 = _report("P1", True)
        p2 = _report("P2", True, data=_p2_data())
        p3 = _report("P3", False)
        with (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
        ):
            assert orch.run_full_pipeline() is False

    def test_stops_at_phase_4(self, orch) -> None:
        p1 = _report("P1", True)
        p2 = _report("P2", True, data=_p2_data())
        p3 = _report("P3", True, data={"filtered_mandates": {}})
        p4 = _report("P4", False)
        with (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
        ):
            assert orch.run_full_pipeline() is False

    def test_phase_5_failure_is_warning_continues(self, orch) -> None:
        p1, p2, p3, p4, _, p6, p7 = self._all_pass()
        p5_fail = _report("P5", False)
        with (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5_fail),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
            patch("sdd_wizard.src.wizard.phase_7_validate_output", return_value=p7),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            assert orch.run_full_pipeline() is True

    def test_stops_at_phase_6(self, orch) -> None:
        p1, p2, p3, p4, p5, _, _ = self._all_pass()
        p6 = _report("P6", False)
        with (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
        ):
            assert orch.run_full_pipeline() is False

    def test_phase_7_failure_is_warning_continues(self, orch) -> None:
        p1, p2, p3, p4, p5, p6, _ = self._all_pass()
        p7_fail = _report("P7", False)
        with (
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
            patch(
                "sdd_wizard.src.wizard.phase_7_validate_output", return_value=p7_fail
            ),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            assert orch.run_full_pipeline() is True

    def test_passes_language_and_mandates(self, orch) -> None:
        patches = self._pipeline_patches(*self._all_pass())
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            result = orch.run_full_pipeline(language="java", mandates=["M001", "M002"])
        assert result is True


class TestMainCommand:
    def test_interactive_mode_when_no_args(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch(
                "sdd_wizard.src.interactive_mode.run_interactive_wizard",
                return_value=True,
            ),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 0

    def test_interactive_mode_failure_exit_1(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch(
                "sdd_wizard.src.interactive_mode.run_interactive_wizard",
                return_value=False,
            ),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 1

    def test_interactive_flag_triggers_interactive(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch(
                "sdd_wizard.src.interactive_mode.run_interactive_wizard",
                return_value=True,
            ),
        ):
            result = runner.invoke(app, ["--interactive", "--language", "python"])
        assert result.exit_code == 0

    def test_import_error_falls_back_to_full_pipeline(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        p1, p2, p3, p4, p5, p6, p7 = (
            _report("P1", True),
            _report("P2", True, data=_p2_data()),
            _report("P3", True, data={"filtered_mandates": {}}),
            _report("P4", True, data={"filtered_guidelines": {}}),
            _report("P5", True),
            _report("P6", True),
            _report("P7", True),
        )
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch(
                "sdd_wizard.src.interactive_mode.run_interactive_wizard",
                side_effect=ImportError,
            ),
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
            patch("sdd_wizard.src.wizard.phase_7_validate_output", return_value=p7),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 0

    def test_non_interactive_with_language(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        p1, p2, p3, p4, p5, p6, p7 = (
            _report("P1", True),
            _report("P2", True, data=_p2_data()),
            _report("P3", True, data={"filtered_mandates": {}}),
            _report("P4", True, data={"filtered_guidelines": {}}),
            _report("P5", True),
            _report("P6", True),
            _report("P7", True),
        )
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
            patch("sdd_wizard.src.wizard.phase_7_validate_output", return_value=p7),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            result = runner.invoke(app, ["--language", "python"])
        assert result.exit_code == 0

    def test_non_interactive_with_mandates(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        p1, p2, p3, p4, p5, p6, p7 = (
            _report("P1", True),
            _report("P2", True, data=_p2_data()),
            _report("P3", True, data={"filtered_mandates": {}}),
            _report("P4", True, data={"filtered_guidelines": {}}),
            _report("P5", True),
            _report("P6", True),
            _report("P7", True),
        )
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch("sdd_wizard.src.wizard.phase_1_validate_source", return_value=p1),
            patch("sdd_wizard.src.wizard.phase_2_load_compiled", return_value=p2),
            patch("sdd_wizard.src.wizard.phase_3_filter_mandates", return_value=p3),
            patch("sdd_wizard.src.wizard.phase_4_filter_guidelines", return_value=p4),
            patch("sdd_wizard.src.wizard.phase_5_apply_template", return_value=p5),
            patch("sdd_wizard.src.wizard.phase_6_generate_project", return_value=p6),
            patch("sdd_wizard.src.wizard.phase_7_validate_output", return_value=p7),
            patch("sdd_wizard.src.wizard.ensure_context_cache"),
        ):
            result = runner.invoke(
                app, ["--language", "python", "--mandates", "M001,M002"]
            )
        assert result.exit_code == 0

    def test_non_interactive_pipeline_failure_exit_1(self) -> None:
        from typer.testing import CliRunner

        from sdd_wizard.src.wizard import app

        runner = CliRunner()
        with (
            patch("sdd_wizard.src.wizard.get_sdd_paths", return_value=_SDD_PATHS),
            patch(
                "sdd_wizard.src.wizard.phase_1_validate_source",
                return_value=_report("P1", False),
            ),
        ):
            result = runner.invoke(app, ["--language", "python"])
        assert result.exit_code == 1
