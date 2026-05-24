"""Tests for governance_fetcher — compiled defaults bootstrap fetcher."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from sdd_core.utils.text_io import write_text_utf8
from sdd_wizard.orchestration.governance_fetcher import (
    _download_file,
    _validate_governance_file,
    fetch_compiled_defaults,
    get_cli_version,
)

_VALID_CORE = json.dumps({"version": "1.0", "items": []})
_VALID_CLIENT = json.dumps({"version": "1.0", "items": []})


class TestGetCliVersion:
    def test_returns_version_string(self) -> None:
        """Returns a non-empty string (mocked or real package)."""
        with patch(
            "sdd_wizard.orchestration.governance_fetcher.importlib_version",
            return_value="1.2.3",
            create=True,
        ):
            pass
        version = get_cli_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_returns_unknown_on_error(self) -> None:
        """Returns 'unknown' when importlib.metadata raises."""
        with patch(
            "importlib.metadata.version",
            side_effect=Exception("not found"),
        ):
            version = get_cli_version()
        assert version == "unknown"


class TestValidateGovernanceFile:
    def test_valid_file_passes(self, tmp_path: Path) -> None:
        """A file with version and items keys passes validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, json.dumps({"version": "1.0", "items": []}))
        assert _validate_governance_file(p) is True

    def test_missing_required_fields_fails(self, tmp_path: Path) -> None:
        """A file without version or items keys fails validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, json.dumps({"other": "value"}))
        assert _validate_governance_file(p) is False

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        """A file with invalid JSON fails validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, "not-json{{}")
        assert _validate_governance_file(p) is False

    def test_empty_file_fails(self, tmp_path: Path) -> None:
        """An empty file fails validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, "")
        assert _validate_governance_file(p) is False

    def test_non_dict_json_fails(self, tmp_path: Path) -> None:
        """A JSON array at the top level fails validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, json.dumps([{"version": "1.0"}]))
        assert _validate_governance_file(p) is False

    def test_missing_items_field_fails(self, tmp_path: Path) -> None:
        """A file with 'version' but without 'items' fails validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, json.dumps({"version": "1.0"}))
        assert _validate_governance_file(p) is False

    def test_missing_version_field_fails(self, tmp_path: Path) -> None:
        """A file with 'items' but without 'version' fails validation."""
        p = tmp_path / "governance-core.json"
        write_text_utf8(p, json.dumps({"items": []}))
        assert _validate_governance_file(p) is False


class TestDownloadFile:
    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        """_download_file returns True when urlretrieve succeeds."""
        dest = tmp_path / "out.json"
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            result = _download_file("https://example.com/file.json", dest)
        mock_retrieve.assert_called_once()
        assert result is True

    def test_returns_false_on_network_error(self, tmp_path: Path) -> None:
        """_download_file returns False when urlretrieve raises."""
        dest = tmp_path / "out.json"
        with patch(
            "urllib.request.urlretrieve",
            side_effect=OSError("network error"),
        ):
            result = _download_file("https://example.com/file.json", dest)
        assert result is False

    def test_rejects_non_https_schemes(self, tmp_path: Path) -> None:
        """_download_file rejects file:/, http://, and other non-HTTPS schemes."""
        dest = tmp_path / "out.json"
        for url in (
            "file:///etc/passwd",
            "http://example.com/f.json",
            "ftp://x/f.json",
        ):
            assert _download_file(url, dest) is False, f"should reject {url}"

    def test_does_not_call_urlretrieve_for_non_https(self, tmp_path: Path) -> None:
        """urlretrieve is never called when the scheme is not https."""
        dest = tmp_path / "out.json"
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            _download_file("file:///etc/passwd", dest)
        mock_retrieve.assert_not_called()


class TestFetchCompiledDefaults:
    def _write_valid_files(self, dest: Path) -> None:
        write_text_utf8(dest / "governance-core.json", _VALID_CORE)
        write_text_utf8(dest / "governance-client.json", _VALID_CLIENT)

    def test_versioned_release_success(self, tmp_path: Path) -> None:
        """Returns (True, 'versioned_release') when versioned URLs succeed."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            side_effect=fake_download,
        ):
            ok, source = fetch_compiled_defaults("1.0.0", dest)

        assert ok is True
        assert source == "versioned_release"

    def test_fallback_to_latest_when_versioned_fails(self, tmp_path: Path) -> None:
        """Returns (True, 'latest_release') when versioned URL fails but latest succeeds."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            if "/download/v" in url:
                return False
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            side_effect=fake_download,
        ):
            ok, source = fetch_compiled_defaults("1.0.0", dest)

        assert ok is True
        assert source == "latest_release"

    def test_fails_when_all_urls_fail(self, tmp_path: Path) -> None:
        """Returns (False, 'failed') when all download attempts fail."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            return_value=False,
        ):
            ok, source = fetch_compiled_defaults("1.0.0", dest)

        assert ok is False
        assert source == "failed"

    def test_partial_download_cleaned_up_on_second_file_failure(
        self, tmp_path: Path
    ) -> None:
        """If the second file fails, the first downloaded file is removed."""
        dest = tmp_path / ".sdd"
        dest.mkdir()
        call_count = 0

        def fake_download(url: str, path: Path) -> bool:
            nonlocal call_count
            call_count += 1
            return call_count > 2  # pragma: no branch

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            side_effect=fake_download,
        ):
            ok, source = fetch_compiled_defaults("1.0.0", dest)

        assert ok is False
        assert not (dest / "governance-core.json").exists()

    def test_invalid_json_triggers_cleanup_and_failure(self, tmp_path: Path) -> None:
        """If a downloaded file contains invalid JSON, all files are cleaned up."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            write_text_utf8(path, "NOT VALID JSON")
            return True

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            side_effect=fake_download,
        ):
            ok, source = fetch_compiled_defaults("1.0.0", dest)

        assert ok is False
        assert source == "failed"
        assert not (dest / "governance-core.json").exists()

    def test_dest_directory_created_if_missing(self, tmp_path: Path) -> None:
        """fetch_compiled_defaults creates dest directory if it does not exist."""
        dest = tmp_path / ".sdd" / "nested"

        def fake_download(url: str, path: Path) -> bool:
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            side_effect=fake_download,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        assert dest.exists()

    def test_second_file_failure_removes_first_downloaded_file(
        self, tmp_path: Path
    ) -> None:
        """First successfully downloaded file is cleaned up when second file fails."""
        dest = tmp_path / ".sdd"
        dest.mkdir()
        call_count = 0

        def fake_download(url: str, path: Path) -> bool:
            nonlocal call_count
            call_count += 1
            if "governance-core.json" in url:
                write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
                return True
            return False

        with patch(
            "sdd_wizard.orchestration.governance_fetcher._download_file",
            side_effect=fake_download,
        ):
            ok, _ = fetch_compiled_defaults("1.0.0", dest)

        assert ok is False
        assert not (dest / "governance-core.json").exists()

    def test_telemetry_started_event_emitted(self, tmp_path: Path) -> None:
        """fetch.started log event is emitted at the start of every fetch."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with (
            patch(
                "sdd_wizard.orchestration.governance_fetcher._download_file",
                side_effect=fake_download,
            ),
            patch("sdd_wizard.orchestration.governance_fetcher.logger") as mock_logger,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("started" in c for c in calls)

    def test_telemetry_succeeded_event_emitted(self, tmp_path: Path) -> None:
        """fetch.succeeded log event is emitted when versioned release succeeds."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            if "/download/v" in url:
                write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
                return True
            return False

        with (
            patch(
                "sdd_wizard.orchestration.governance_fetcher._download_file",
                side_effect=fake_download,
            ),
            patch("sdd_wizard.orchestration.governance_fetcher.logger") as mock_logger,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("succeeded" in c for c in calls)

    def test_telemetry_fallback_warning_emitted(self, tmp_path: Path) -> None:
        """fetch.fallback_latest warning is emitted when latest-release fallback occurs."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            if "/download/v" in url:
                return False
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with (
            patch(
                "sdd_wizard.orchestration.governance_fetcher._download_file",
                side_effect=fake_download,
            ),
            patch("sdd_wizard.orchestration.governance_fetcher.logger") as mock_logger,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any("fallback_latest" in c for c in calls)

    def test_telemetry_failed_event_emitted(self, tmp_path: Path) -> None:
        """fetch.failed error event is emitted when all downloads fail."""
        dest = tmp_path / ".sdd"
        dest.mkdir()

        with (
            patch(
                "sdd_wizard.orchestration.governance_fetcher._download_file",
                return_value=False,
            ),
            patch("sdd_wizard.orchestration.governance_fetcher.logger") as mock_logger,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        calls = [str(c) for c in mock_logger.error.call_args_list]
        assert any("failed" in c for c in calls)

    def test_telemetry_events_include_trace_id(self, tmp_path: Path) -> None:
        """All telemetry events include trace_id field with a UUID value."""
        import re

        dest = tmp_path / ".sdd"
        dest.mkdir()

        def fake_download(url: str, path: Path) -> bool:
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with (
            patch(
                "sdd_wizard.orchestration.governance_fetcher._download_file",
                side_effect=fake_download,
            ),
            patch("sdd_wizard.orchestration.governance_fetcher.logger") as mock_logger,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        uuid_pattern = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        )
        all_calls = mock_logger.info.call_args_list + mock_logger.warning.call_args_list
        for call in all_calls:
            kwargs = call.kwargs if call.kwargs else (call[1] if len(call) > 1 else {})
            assert "trace_id" in kwargs, f"trace_id missing from call: {call}"
            assert uuid_pattern.match(kwargs["trace_id"]), (
                f"trace_id is not a UUID: {kwargs['trace_id']}"
            )

    def test_same_trace_id_across_all_events_in_one_fetch(self, tmp_path: Path) -> None:
        """All events within a single fetch share the same trace_id."""
        dest = tmp_path / ".sdd"
        dest.mkdir()
        call_count = 0

        def fake_download(url: str, path: Path) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First file versioned succeeds
                write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
                return True
            # Second file falls back to latest
            if "/download/v" in url:
                return False
            write_text_utf8(path, json.dumps({"version": "1.0", "items": []}))
            return True

        with (
            patch(
                "sdd_wizard.orchestration.governance_fetcher._download_file",
                side_effect=fake_download,
            ),
            patch("sdd_wizard.orchestration.governance_fetcher.logger") as mock_logger,
        ):
            fetch_compiled_defaults("1.0.0", dest)

        trace_ids: list[str] = []
        for call in (
            mock_logger.info.call_args_list + mock_logger.warning.call_args_list
        ):
            kwargs = call.kwargs if call.kwargs else {}
            if "trace_id" in kwargs:
                trace_ids.append(kwargs["trace_id"])

        assert len(trace_ids) >= 2, "Expected at least started + fallback_latest events"
        assert len(set(trace_ids)) == 1, f"trace_ids differ across events: {trace_ids}"
