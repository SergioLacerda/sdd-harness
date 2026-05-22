"""Tests for GovernanceCompiler (PHASE 2 compilation)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdd_compiler.governance_compiler import GovernanceCompiler, _is_valid_fingerprint

_FP_CORE = "a" * 64
_FP_CLIENT = "b" * 64


def _write_governance_json(
    path: Path, profile: str, fp: str, fp_core: str | None = None
) -> None:
    data: dict = {
        "fingerprint": fp,
        "items": [
            {"type": "MANDATE", "id": "M001", "criticality": "HIGH", "title": "T"},
        ],
    }
    if fp_core:
        data["fingerprint_core_salt"] = fp_core
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_compiler(tmp_path: Path) -> GovernanceCompiler:
    _write_governance_json(tmp_path / "governance-core.json", "core", _FP_CORE)
    _write_governance_json(
        tmp_path / "governance-client.json", "client", _FP_CLIENT, fp_core=_FP_CORE
    )
    return GovernanceCompiler(str(tmp_path))


class TestGovernanceCompilerCompile:
    def test_compile_creates_msgpack_files(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.compile(str(tmp_path))
        assert Path(result["core_msgpack_file"]).exists()
        assert Path(result["client_msgpack_file"]).exists()

    def test_compile_result_has_fingerprints(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.compile(str(tmp_path))
        assert result["core_fingerprint"] == _FP_CORE
        assert result["client_fingerprint"] == _FP_CLIENT

    def test_compile_counts_items(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.compile(str(tmp_path))
        assert result["core_item_count"] == 1
        assert result["client_item_count"] == 1

    def test_compile_creates_metadata_files(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.compile(str(tmp_path))
        assert Path(result["core_metadata"]).exists()
        assert Path(result["client_metadata"]).exists()

    def test_compile_raises_when_json_missing(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))  # no JSON files
        with pytest.raises(ValueError, match="Could not load"):
            compiler.compile(str(tmp_path))

    def test_compile_raises_when_signing_required_but_no_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_SIGNING_REQUIRED", "1")
        monkeypatch.delenv("SDD_SIGNING_PRIVATE_KEY_FILE", raising=False)
        compiler = _make_compiler(tmp_path)
        with pytest.raises(RuntimeError, match="Signing is required"):
            compiler.compile(str(tmp_path))

    def test_compile_not_signed_by_default(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.compile(str(tmp_path))
        assert result["signed"] is False
        assert result["core_signature_file"] is None


class TestGovernanceCompilerValidation:
    def _setup_output(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        compiler.compile(str(tmp_path))

    def test_validate_compilation_passes_on_valid_output(self, tmp_path: Path) -> None:
        self._setup_output(tmp_path)
        compiler = _make_compiler(tmp_path)
        assert compiler.validate_compilation(str(tmp_path)) is True

    def test_validate_detailed_ok_on_valid_output(self, tmp_path: Path) -> None:
        self._setup_output(tmp_path)
        compiler = _make_compiler(tmp_path)
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is True
        assert result.errors == []

    def test_validate_fails_when_msgpack_missing(self, tmp_path: Path) -> None:
        compiler = _make_compiler(tmp_path)
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False
        assert any("not found" in e for e in result.errors)

    def test_validate_fails_when_metadata_missing(self, tmp_path: Path) -> None:
        self._setup_output(tmp_path)
        (tmp_path / "metadata-core.json").unlink()
        compiler = _make_compiler(tmp_path)
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_fails_on_invalid_fingerprint(self, tmp_path: Path) -> None:
        self._setup_output(tmp_path)
        # Corrupt the core metadata fingerprint
        meta = json.loads((tmp_path / "metadata-core.json").read_text(encoding="utf-8"))
        meta["fingerprint"] = "short"
        (tmp_path / "metadata-core.json").write_text(json.dumps(meta), encoding="utf-8")
        compiler = _make_compiler(tmp_path)
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_fails_when_fingerprints_identical(self, tmp_path: Path) -> None:
        # Make both JSONs use the same fingerprint
        _write_governance_json(tmp_path / "governance-core.json", "core", _FP_CORE)
        _write_governance_json(
            tmp_path / "governance-client.json", "client", _FP_CORE, fp_core=_FP_CORE
        )
        compiler = GovernanceCompiler(str(tmp_path))
        compiler.compile(str(tmp_path))
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_detects_missing_core_salt(self, tmp_path: Path) -> None:
        self._setup_output(tmp_path)
        meta = json.loads(
            (tmp_path / "metadata-client-template.json").read_text(encoding="utf-8")
        )
        meta["fingerprint_core_salt"] = "wrong" * 16  # valid length but wrong value
        (tmp_path / "metadata-client-template.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        compiler = _make_compiler(tmp_path)
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False


class TestGovernanceCompilerHelpers:
    def test_load_json_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        assert compiler._load_json(tmp_path / "nonexistent.json") is None

    def test_load_json_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json{{{", encoding="utf-8")
        compiler = GovernanceCompiler(str(tmp_path))
        assert compiler._load_json(bad) is None

    def test_serialize_to_msgpack_returns_bytes(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        result = compiler._serialize_to_msgpack({"key": "value"})
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_count_items_by_type(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        data = {
            "items": [{"type": "MANDATE"}, {"type": "mandate"}, {"type": "GUIDELINE"}]
        }
        counts = compiler._count_items_by_type(data)
        assert counts["MANDATE"] == 2
        assert counts["GUIDELINE"] == 1

    def test_count_items_by_criticality(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        data = {
            "items": [
                {"criticality": "HIGH"},
                {"criticality": "LOW"},
                {"criticality": "HIGH"},
            ]
        }
        counts = compiler._count_items_by_criticality(data)
        assert counts["HIGH"] == 2
        assert counts["LOW"] == 1

    def test_resolve_trust_dir_finds_sdd(self, tmp_path: Path) -> None:
        (tmp_path / ".sdd").mkdir()
        compiler = GovernanceCompiler(str(tmp_path))
        result = compiler._resolve_trust_dir(tmp_path)
        assert result == tmp_path / ".sdd" / "trust"

    def test_resolve_trust_dir_fallback(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        # No .sdd dir anywhere in tmp_path ancestors (normally)
        result = compiler._resolve_trust_dir(tmp_path / "deep" / "nested")
        assert "trust" in str(result)


class TestValidationEdgeCases:
    def _setup_output(self, tmp_path: Path) -> GovernanceCompiler:
        _write_governance_json(tmp_path / "governance-core.json", "core", _FP_CORE)
        _write_governance_json(
            tmp_path / "governance-client.json", "client", _FP_CLIENT, fp_core=_FP_CORE
        )
        compiler = GovernanceCompiler(str(tmp_path))
        compiler.compile(str(tmp_path))
        return compiler

    def test_validate_fails_on_unparseable_client_metadata(
        self, tmp_path: Path
    ) -> None:
        compiler = self._setup_output(tmp_path)
        (tmp_path / "metadata-client-template.json").write_text(
            "not json", encoding="utf-8"
        )
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_fails_on_core_not_readonly(self, tmp_path: Path) -> None:
        compiler = self._setup_output(tmp_path)
        meta = json.loads((tmp_path / "metadata-core.json").read_text(encoding="utf-8"))
        meta["readonly"] = False
        (tmp_path / "metadata-core.json").write_text(json.dumps(meta), encoding="utf-8")
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_fails_on_client_not_customizable(self, tmp_path: Path) -> None:
        compiler = self._setup_output(tmp_path)
        meta = json.loads(
            (tmp_path / "metadata-client-template.json").read_text(encoding="utf-8")
        )
        meta["customizable"] = False
        (tmp_path / "metadata-client-template.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_invalid_client_fingerprint(self, tmp_path: Path) -> None:
        compiler = self._setup_output(tmp_path)
        meta = json.loads(
            (tmp_path / "metadata-client-template.json").read_text(encoding="utf-8")
        )
        meta["fingerprint"] = "tooshort"
        (tmp_path / "metadata-client-template.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False

    def test_validate_partial_signature_reports_error(self, tmp_path: Path) -> None:
        compiler = self._setup_output(tmp_path)
        # Create only the core sig file (client is missing) to trigger inconsistency check
        core_sig = tmp_path / "governance-core.json.sig"
        core_sig.write_text("{}", encoding="utf-8")
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False


class TestIsValidFingerprint:
    def test_valid_64_char_hex(self) -> None:
        assert _is_valid_fingerprint("a" * 64) is True

    def test_too_short(self) -> None:
        assert _is_valid_fingerprint("abc") is False

    def test_none_is_invalid(self) -> None:
        assert _is_valid_fingerprint(None) is False

    def test_integer_is_invalid(self) -> None:
        assert _is_valid_fingerprint(12345) is False
