"""Tests for incremental compilation state manager."""

from __future__ import annotations

import json
from pathlib import Path

from sdd_compiler.compile_state import CompileState


def test_loads_fresh_state_when_file_missing(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    state = CompileState(state_file)
    assert state.get_last_compiled_time() is None
    assert state.to_dict()["sources"] == {}
    assert state.to_dict()["artifacts"] == {}


def test_loads_fresh_state_when_file_is_corrupted(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{not-valid-json", encoding="utf-8")

    state = CompileState(state_file)

    assert state.get_last_compiled_time() is None
    assert state.to_dict()["version"] == "1.0"


def test_save_persists_timestamp_and_payload(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    state = CompileState(state_file)
    state.state["sources"]["mandate"] = {"hash": "abc", "size": 1}
    state.save()

    assert state_file.exists()
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload["timestamp"] is not None
    assert payload["sources"]["mandate"]["hash"] == "abc"


def test_update_source_and_detect_changes(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    source_file = tmp_path / "mandate.spec"
    source_file.write_text("first", encoding="utf-8")

    state = CompileState(state_file)
    assert state.source_changed("mandate", source_file) is True

    state.update_source("mandate", source_file)
    assert state.get_source_hash("mandate") is not None
    assert state.source_changed("mandate", source_file) is False

    source_file.write_text("second", encoding="utf-8")
    assert state.source_changed("mandate", source_file) is True


def test_source_changed_when_path_missing_or_hash_absent(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    missing_file = tmp_path / "missing.spec"
    state = CompileState(state_file)

    assert state.source_changed("missing", missing_file) is True

    existing_file = tmp_path / "existing.spec"
    existing_file.write_text("content", encoding="utf-8")
    assert state.source_changed("new-source", existing_file) is True


def test_any_source_changed(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    a = tmp_path / "a.spec"
    b = tmp_path / "b.spec"
    a.write_text("A", encoding="utf-8")
    b.write_text("B", encoding="utf-8")
    state = CompileState(state_file)

    state.update_source("a", a)
    state.update_source("b", b)
    assert state.any_source_changed({"a": a, "b": b}) is False

    b.write_text("B2", encoding="utf-8")
    assert state.any_source_changed({"a": a, "b": b}) is True


def test_update_artifact_and_getters(tmp_path: Path) -> None:
    state_file = tmp_path / ".sdd" / "runtime" / ".compile-state.json"
    artifact = tmp_path / ".sdd" / "compiled" / "out.msgpack"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"\x01\x02\x03")

    state = CompileState(state_file)
    state.update_artifact("mandate_bin", artifact)

    path = state.get_artifact_path("mandate_bin")
    assert path is not None
    assert path.endswith("compiled/out.msgpack")

    # Missing artifact should not create new entry.
    state.update_artifact("missing_bin", tmp_path / "does-not-exist.bin")
    assert state.get_artifact_path("missing_bin") is None
