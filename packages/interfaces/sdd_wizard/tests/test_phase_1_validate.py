"""Tests for Phase 1 validation — compiled defaults bootstrap."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sdd_core.utils.text_io import write_text_utf8
from sdd_wizard.orchestration.phase_1_validate import phase_1_validate_source


class TestPhase1LocalFilesPresent:
    """When both governance files already exist, no fetch should occur."""

    def test_success_when_files_exist(self, tmp_path: Path) -> None:
        """Returns SUCCESS without network access when both files are present."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        write_text_utf8(sdd_dir / "governance-core.json", "{}")
        write_text_utf8(sdd_dir / "governance-client.json", "{}")

        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults"
        ) as mock_fetch:
            success, report = phase_1_validate_source(tmp_path)

        mock_fetch.assert_not_called()
        assert success is True
        assert report["status"] == "SUCCESS"
        assert report["data"]["source"] == "local"

    def test_report_structure_on_local_success(self, tmp_path: Path) -> None:
        """Report contains all required keys on local success."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        write_text_utf8(sdd_dir / "governance-core.json", "{}")
        write_text_utf8(sdd_dir / "governance-client.json", "{}")

        with patch("sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults"):
            _, report = phase_1_validate_source(tmp_path)

        assert report["phase"] == "PHASE_1_VALIDATE_SOURCE"
        assert report["errors"] == []
        assert "mandate_spec_exists" in report["checks"]
        assert "guidelines_dsl_exists" in report["checks"]
        assert "mandate_spec_valid" in report["checks"]
        assert "guidelines_dsl_valid" in report["checks"]
        assert "mandate" in report["data"]
        assert "guidelines" in report["data"]

    def test_no_advisory_on_local_source(self, tmp_path: Path) -> None:
        """No advisory field emitted when files are local."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        write_text_utf8(sdd_dir / "governance-core.json", "{}")
        write_text_utf8(sdd_dir / "governance-client.json", "{}")

        with patch("sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults"):
            _, report = phase_1_validate_source(tmp_path)

        assert "advisory" not in report

    def test_only_core_missing_triggers_fetch(self, tmp_path: Path) -> None:
        """If only one file is present the fetch path is still triggered."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        write_text_utf8(sdd_dir / "governance-client.json", "{}")

        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(True, "versioned_release"),
        ) as mock_fetch:
            success, _ = phase_1_validate_source(tmp_path)

        mock_fetch.assert_called_once()
        assert success is True

    def test_only_client_missing_triggers_fetch(self, tmp_path: Path) -> None:
        """If only governance-client.json is missing the fetch path is triggered."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        write_text_utf8(sdd_dir / "governance-core.json", "{}")

        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(True, "versioned_release"),
        ) as mock_fetch:
            success, _ = phase_1_validate_source(tmp_path)

        mock_fetch.assert_called_once()
        assert success is True


class TestPhase1FetchVersionedRelease:
    """When files are absent and fetch succeeds via versioned release."""

    def test_success_via_versioned_release(self, tmp_path: Path) -> None:
        """Returns SUCCESS with source=versioned_release when fetch works."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(True, "versioned_release"),
        ):
            success, report = phase_1_validate_source(tmp_path)

        assert success is True
        assert report["status"] == "SUCCESS"
        assert report["data"]["source"] == "versioned_release"
        assert "advisory" not in report

    def test_fetch_called_with_cli_version(self, tmp_path: Path) -> None:
        """fetch_compiled_defaults receives the installed CLI version and sdd_dir."""
        with (
            patch(
                "sdd_wizard.orchestration.phase_1_validate.get_cli_version",
                return_value="1.2.3",
            ),
            patch(
                "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
                return_value=(True, "versioned_release"),
            ) as mock_fetch,
        ):
            phase_1_validate_source(tmp_path)

        mock_fetch.assert_called_once_with("1.2.3", dest=tmp_path / ".sdd")


class TestPhase1FetchLatestFallback:
    """When versioned asset misses and latest fallback is used."""

    def test_success_via_latest_includes_advisory(self, tmp_path: Path) -> None:
        """Returns SUCCESS with advisory text when latest-release fallback is used."""
        with (
            patch(
                "sdd_wizard.orchestration.phase_1_validate.get_cli_version",
                return_value="1.2.3",
            ),
            patch(
                "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
                return_value=(True, "latest_release"),
            ),
        ):
            success, report = phase_1_validate_source(tmp_path)

        assert success is True
        assert report["status"] == "SUCCESS"
        assert report["data"]["source"] == "latest_release"
        assert "advisory" in report
        assert "1.2.3" in report["advisory"]


class TestPhase1FetchFailure:
    """When all fetch attempts fail."""

    def test_failure_returns_false_with_error_message(self, tmp_path: Path) -> None:
        """Returns FAILED with actionable error when network is unavailable."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(False, "failed"),
        ):
            success, report = phase_1_validate_source(tmp_path)

        assert success is False
        assert report["status"] == "FAILED"
        assert len(report["errors"]) == 1
        assert "governance-core.json" in report["errors"][0]
        assert "governance-client.json" in report["errors"][0]

    def test_failure_report_all_checks_false(self, tmp_path: Path) -> None:
        """All checks are False on fetch failure."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(False, "failed"),
        ):
            _, report = phase_1_validate_source(tmp_path)

        for key, value in report["checks"].items():
            assert value is False, f"check '{key}' should be False"

    def test_failure_report_zero_counts(self, tmp_path: Path) -> None:
        """Counts default to zero on fetch failure."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(False, "failed"),
        ):
            _, report = phase_1_validate_source(tmp_path)

        assert report["data"]["mandate"]["mandate_count"] == 0
        assert report["data"]["guidelines"]["guideline_count"] == 0

    def test_failure_report_structure(self, tmp_path: Path) -> None:
        """Failure report has same top-level keys as success report."""
        with patch(
            "sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults",
            return_value=(False, "failed"),
        ):
            _, report = phase_1_validate_source(tmp_path)

        for key in ("phase", "status", "errors", "checks", "data"):
            assert key in report


class TestPhase1SpecPathIgnored:
    """spec_path parameter is accepted but ignored for client profile."""

    def test_spec_path_override_accepted(self, tmp_path: Path) -> None:
        """phase_1_validate_source accepts spec_path without raising."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        write_text_utf8(sdd_dir / "governance-core.json", "{}")
        write_text_utf8(sdd_dir / "governance-client.json", "{}")

        spec_path = tmp_path / "custom_spec"

        with patch("sdd_wizard.orchestration.phase_1_validate.fetch_compiled_defaults"):
            success, _ = phase_1_validate_source(tmp_path, spec_path=spec_path)

        assert success is True
