"""Tests for sdd_cli.services.governance_artifact_handlers."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from sdd_cli.services.governance_artifact_handlers import (
    _count_items_by_type,
    _has_malformed_titles,
    _load_consistency_artifacts,
    _safe_json,
    _validate_payload_vs_metadata,
    check_artifact_consistency,
    emit_generate_invalid_path_error,
    emit_generate_missing_items_error,
    render_generate_table,
    render_governance_compile_table,
    run_governance_compile_json,
    run_governance_generate_json,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestSafeJson:
    def test_valid_dict_returns_data(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text(json.dumps({"a": 1}), encoding="utf-8")
        assert _safe_json(path) == {"a": 1}

    def test_list_payload_returns_none(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        assert _safe_json(path) is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text("not valid json", encoding="utf-8")
        assert _safe_json(path) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _safe_json(tmp_path / "missing.json") is None


class TestCountItemsByType:
    def test_empty_list_returns_empty_dict(self) -> None:
        assert _count_items_by_type([]) == {}

    def test_counts_grouped_by_uppercased_type(self) -> None:
        items = [
            {"type": "mandate"},
            {"type": "MANDATE"},
            {"type": "skill"},
        ]
        assert _count_items_by_type(items) == {"MANDATE": 2, "SKILL": 1}

    def test_missing_type_key_counts_as_unknown(self) -> None:
        items = [{"id": "x"}]
        assert _count_items_by_type(items) == {"UNKNOWN": 1}

    def test_none_type_value_counts_as_none(self) -> None:
        items = [{"type": None}]
        assert _count_items_by_type(items) == {"NONE": 1}


class TestHasMalformedTitles:
    def test_no_items_returns_false(self) -> None:
        assert _has_malformed_titles([]) is False

    def test_normal_titles_return_false(self) -> None:
        items = [{"title": "Mandate One"}, {"title": "Mandate Two"}]
        assert _has_malformed_titles(items) is False

    def test_status_prefixed_title_returns_true(self) -> None:
        items = [{"title": "- Status: active"}]
        assert _has_malformed_titles(items) is True

    def test_missing_title_is_tolerated(self) -> None:
        items = [{"id": "x"}, {"title": None}]
        assert _has_malformed_titles(items) is False


class TestValidatePayloadVsMetadata:
    def test_items_not_a_list_returns_error(self) -> None:
        payload = {"items": "not-a-list"}
        result = _validate_payload_vs_metadata(payload, {}, "core")
        assert result == "invalid payload schema: items must be a list"

    def test_fingerprint_mismatch_returns_error(self) -> None:
        payload = {"items": [], "fingerprint": "abc"}
        metadata = {"fingerprint": "def", "item_count": 0, "items_by_type": {}}
        result = _validate_payload_vs_metadata(payload, metadata, "core")
        assert result == "core fingerprint mismatch between payload and metadata"

    def test_item_count_mismatch_returns_error(self) -> None:
        payload = {"items": [{"type": "mandate"}], "fingerprint": "abc"}
        metadata = {"fingerprint": "abc", "item_count": 5, "items_by_type": {}}
        result = _validate_payload_vs_metadata(payload, metadata, "client")
        assert result == "client item_count mismatch"

    def test_items_by_type_mismatch_returns_error(self) -> None:
        payload = {"items": [{"type": "mandate"}], "fingerprint": "abc"}
        metadata = {
            "fingerprint": "abc",
            "item_count": 1,
            "items_by_type": {"SKILL": 1},
        }
        result = _validate_payload_vs_metadata(payload, metadata, "client")
        assert result == "client items_by_type mismatch"

    def test_core_malformed_title_returns_error(self) -> None:
        payload = {
            "items": [{"type": "mandate", "title": "- Status: active"}],
            "fingerprint": "abc",
        }
        metadata = {
            "fingerprint": "abc",
            "item_count": 1,
            "items_by_type": {"MANDATE": 1},
        }
        result = _validate_payload_vs_metadata(payload, metadata, "core")
        assert result == "malformed mandate title detected"

    def test_client_malformed_title_is_not_checked(self) -> None:
        payload = {
            "items": [{"type": "mandate", "title": "- Status: active"}],
            "fingerprint": "abc",
        }
        metadata = {
            "fingerprint": "abc",
            "item_count": 1,
            "items_by_type": {"MANDATE": 1},
        }
        result = _validate_payload_vs_metadata(payload, metadata, "client")
        assert result is None

    def test_valid_payload_returns_none(self) -> None:
        payload = {
            "items": [{"type": "mandate", "title": "Mandate One"}],
            "fingerprint": "abc",
        }
        metadata = {
            "fingerprint": "abc",
            "item_count": 1,
            "items_by_type": {"MANDATE": 1},
        }
        assert _validate_payload_vs_metadata(payload, metadata, "core") is None


def _write_artifacts(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "governance-core.json").write_text(
        json.dumps({"items": [], "fingerprint": "core-fp"}), encoding="utf-8"
    )
    (directory / "governance-client.json").write_text(
        json.dumps(
            {"items": [], "fingerprint": "client-fp", "fingerprint_core_salt": "salt"}
        ),
        encoding="utf-8",
    )
    (directory / "metadata-core.json").write_text(
        json.dumps({"fingerprint": "core-fp", "item_count": 0, "items_by_type": {}}),
        encoding="utf-8",
    )
    (directory / "metadata-client-template.json").write_text(
        json.dumps(
            {
                "fingerprint": "client-fp",
                "item_count": 0,
                "items_by_type": {},
                "fingerprint_core_salt": "salt",
            }
        ),
        encoding="utf-8",
    )


class TestLoadConsistencyArtifacts:
    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        assert _load_consistency_artifacts(tmp_path) is None

    def test_loads_from_compiled_dir_directly(self, tmp_path: Path) -> None:
        _write_artifacts(tmp_path)
        loaded = _load_consistency_artifacts(tmp_path)
        assert loaded is not None
        core_json, client_json, core_meta, client_meta = loaded
        assert core_json["fingerprint"] == "core-fp"
        assert client_json["fingerprint"] == "client-fp"
        assert core_meta["fingerprint"] == "core-fp"
        assert client_meta["fingerprint"] == "client-fp"

    def test_loads_from_audit_dir_fallback(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        _write_artifacts(audit_dir)
        loaded = _load_consistency_artifacts(tmp_path)
        assert loaded is not None


class TestCheckArtifactConsistency:
    def test_unresolvable_path_returns_false(self) -> None:
        with patch(
            "sdd_cli.services.governance_artifact_handlers.resolve_governance_compiled_dir",
            return_value=None,
        ):
            ok, reason = check_artifact_consistency("/bogus/path")
        assert ok is False
        assert "could not resolve compiled governance directory" in reason

    def test_missing_artifacts_returns_false(self, tmp_path: Path) -> None:
        with patch(
            "sdd_cli.services.governance_artifact_handlers.resolve_governance_compiled_dir",
            return_value=tmp_path,
        ):
            ok, reason = check_artifact_consistency(str(tmp_path))
        assert ok is False
        assert reason == "missing governance JSON or metadata artifacts"

    def test_core_issue_returns_false(self, tmp_path: Path) -> None:
        _write_artifacts(tmp_path)
        (tmp_path / "metadata-core.json").write_text(
            json.dumps(
                {"fingerprint": "different", "item_count": 0, "items_by_type": {}}
            ),
            encoding="utf-8",
        )
        with patch(
            "sdd_cli.services.governance_artifact_handlers.resolve_governance_compiled_dir",
            return_value=tmp_path,
        ):
            ok, reason = check_artifact_consistency(str(tmp_path))
        assert ok is False
        assert reason == "core fingerprint mismatch between payload and metadata"

    def test_client_issue_returns_false(self, tmp_path: Path) -> None:
        _write_artifacts(tmp_path)
        (tmp_path / "metadata-client-template.json").write_text(
            json.dumps(
                {
                    "fingerprint": "different",
                    "item_count": 0,
                    "items_by_type": {},
                    "fingerprint_core_salt": "salt",
                }
            ),
            encoding="utf-8",
        )
        with patch(
            "sdd_cli.services.governance_artifact_handlers.resolve_governance_compiled_dir",
            return_value=tmp_path,
        ):
            ok, reason = check_artifact_consistency(str(tmp_path))
        assert ok is False
        assert reason == "client fingerprint mismatch between payload and metadata"

    def test_salt_mismatch_returns_false(self, tmp_path: Path) -> None:
        _write_artifacts(tmp_path)
        client_json_path = tmp_path / "governance-client.json"
        data = json.loads(client_json_path.read_text(encoding="utf-8"))
        data["fingerprint_core_salt"] = "different-salt"
        client_json_path.write_text(json.dumps(data), encoding="utf-8")
        with patch(
            "sdd_cli.services.governance_artifact_handlers.resolve_governance_compiled_dir",
            return_value=tmp_path,
        ):
            ok, reason = check_artifact_consistency(str(tmp_path))
        assert ok is False
        assert reason == "client fingerprint_core_salt mismatch"

    def test_all_consistent_returns_true(self, tmp_path: Path) -> None:
        _write_artifacts(tmp_path)
        with patch(
            "sdd_cli.services.governance_artifact_handlers.resolve_governance_compiled_dir",
            return_value=tmp_path,
        ):
            ok, reason = check_artifact_consistency(str(tmp_path))
        assert ok is True
        assert reason == "ok"


class TestRunGovernanceCompileJson:
    def test_consistency_failure_returns_error_payload(self) -> None:
        payload, is_error = run_governance_compile_json(
            phase_1={"core_item_count": 5, "client_item_count": 2},
            phase_2={
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
            core_fingerprint="abc123",
            consistency_ok=False,
            consistency_reason="boom",
        )
        assert is_error is True
        assert payload["ok"] is False
        assert payload["error"]["code"] == "artifact_consistency_failed"
        assert "boom" in payload["error"]["message"]
        assert payload["data"]["exit_code"] == 1

    def test_consistency_success_returns_ok_payload(self) -> None:
        payload, is_error = run_governance_compile_json(
            phase_1={"core_item_count": 5, "client_item_count": 2},
            phase_2={
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
            core_fingerprint="abc123",
            consistency_ok=True,
            consistency_reason="ok",
        )
        assert is_error is False
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0


class TestRenderGovernanceCompileTable:
    def test_renders_expected_rows(self) -> None:
        console = _console()
        render_governance_compile_table(
            console=console,
            phase_1={"core_item_count": 3, "client_item_count": 1},
            phase_2={
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
            core_fingerprint="abc123",
        )
        output = console.file.getvalue()
        assert "Compilation Summary" in output
        assert "Core items" in output
        assert "core.msgpack" in output


class TestRunGovernanceGenerateJson:
    def test_returns_ok_payload(self, tmp_path: Path) -> None:
        payload = run_governance_generate_json(
            resolved_path=str(tmp_path),
            output_base=tmp_path,
            seeds_dir=tmp_path / "seeds",
            rows=[{"agent_template": "copilot", "location": "x", "status": "ok"}],
            skills_generated=True,
            skill_index_generated=True,
            cli_index_generated=False,
        )
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0


class TestEmitGenerateInvalidPathError:
    def test_emits_error_and_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.services.governance_artifact_handlers.emit_json"
            ) as mock_emit,
            pytest.raises(typer.Exit) as exc_info,
        ):
            emit_generate_invalid_path_error(
                resolved_path=str(tmp_path), output_dir=str(tmp_path)
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_called_once()
        payload, kwargs = mock_emit.call_args
        assert payload[0]["error"]["code"] == "invalid_governance_path"
        assert kwargs["err"] is True


class TestEmitGenerateMissingItemsError:
    def test_emits_error_and_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.services.governance_artifact_handlers.emit_json"
            ) as mock_emit,
            pytest.raises(typer.Exit) as exc_info,
        ):
            emit_generate_missing_items_error(
                resolved_path=str(tmp_path), output_dir=str(tmp_path)
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_called_once()
        payload, kwargs = mock_emit.call_args
        assert payload[0]["error"]["code"] == "missing_governance_items"
        assert kwargs["err"] is True


class TestRenderGenerateTable:
    def test_renders_rows_and_panel(self, tmp_path: Path) -> None:
        console = _console()
        rows = [{"agent_template": "copilot", "location": "x.md", "status": "ok"}]
        render_generate_table(console=console, rows=rows, seeds_dir=tmp_path)
        output = console.file.getvalue()
        assert "Generated Files" in output
        assert "copilot" in output
        assert "Agent seeds generated to" in output
