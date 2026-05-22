"""Unit tests for sdd_wizard.orchestration.phase_2_load_compiled_v3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers to build valid governance JSON fixtures
# ---------------------------------------------------------------------------


def _core_fingerprint(data: dict[str, Any]) -> str:
    data_copy = {
        k: v
        for k, v in data.items()
        if k not in ["fingerprint", "fingerprintpackages_salt"]
    }
    return hashlib.sha256(json.dumps(data_copy, sort_keys=True).encode()).hexdigest()


def _client_fingerprint(data: dict[str, Any]) -> str:
    data_copy = {k: v for k, v in data.items() if k not in ["fingerprint"]}
    return hashlib.sha256(json.dumps(data_copy, sort_keys=True).encode()).hexdigest()


def _make_compiled_dir(tmp_path: Path) -> Path:
    compiled_dir = tmp_path / "compiler" / "compiled"
    compiled_dir.mkdir(parents=True)
    return compiled_dir


def _write_governance_files(
    compiled_dir: Path,
    core_items: list[Any] | None = None,
    client_items: list[Any] | None = None,
) -> None:
    core_items = core_items or []
    client_items = client_items or []

    core_data_base = {"items": core_items, "version": "3.0"}
    core_fp = _core_fingerprint(core_data_base)
    core_data = {**core_data_base, "fingerprint": core_fp}
    (compiled_dir / "governance-core.json").write_text(
        json.dumps(core_data), encoding="utf-8"
    )

    client_data_base = {
        "items": client_items,
        "version": "3.0",
        "fingerprintpackages_salt": core_fp,
    }
    client_fp = _client_fingerprint(client_data_base)
    client_data = {**client_data_base, "fingerprint": client_fp}
    (compiled_dir / "governance-client.json").write_text(
        json.dumps(client_data), encoding="utf-8"
    )

    (compiled_dir / "metadata-core.json").write_text(
        json.dumps({"version": "3.0"}), encoding="utf-8"
    )
    (compiled_dir / "metadata-client.json").write_text(
        json.dumps({"version": "3.0"}), encoding="utf-8"
    )


MANDATE_ITEM = {
    "id": "M001",
    "type": "MANDATE",
    "title": "Use type hints",
    "criticality": "OBRIGATÓRIO",
    "category": "architecture",
}

GUIDELINE_ITEM = {
    "id": "G001",
    "type": "GUIDELINE",
    "title": "Conventional commits",
    "criticality": "RECOMENDADO",
    "category": "git",
    "customizable": True,
}


# ---------------------------------------------------------------------------
# GovernanceLoader (internal class)
# ---------------------------------------------------------------------------


class TestGovernanceLoaderV2LoadFiles:
    def test_returns_false_when_no_core_file(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.load_files()
        assert result is False

    def test_returns_false_when_no_client_file(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        (compiled_dir / "governance-core.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )
        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.load_files()
        assert result is False

    def test_returns_true_when_both_files_exist(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.load_files()
        assert result is True

    def test_loads_core_data(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir, core_items=[MANDATE_ITEM])
        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        assert loader.core_data is not None
        assert len(loader.core_data["items"]) == 1

    def test_loads_client_data(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir, client_items=[GUIDELINE_ITEM])
        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        assert loader.client_data is not None

    def test_bad_json_returns_false(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        (compiled_dir / "governance-core.json").write_text(
            "not-json{{{", encoding="utf-8"
        )
        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.load_files()
        assert result is False


class TestGovernanceLoaderV2ValidateFingerprints:
    def test_returns_false_when_not_loaded(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        valid, report = loader.validate_fingerprints()
        assert valid is False

    def test_returns_true_for_valid_fingerprints(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        valid, report = loader.validate_fingerprints()
        assert valid is True

    def test_report_contains_core_fp(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        _, report = loader.validate_fingerprints()
        assert report["core_fp"] is not None


class TestGovernanceLoaderV2ExtractMandates:
    def test_returns_empty_when_no_data(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.extract_mandates()
        assert result == {}

    def test_extracts_mandates(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir, core_items=[MANDATE_ITEM])
        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        mandates = loader.extract_mandates()
        assert "M001" in mandates


class TestGovernanceLoaderV2ExtractGuidelines:
    def test_returns_empty_when_no_data(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        core_g, client_g = loader.extract_guidelines()
        assert core_g == {}
        assert client_g == {}

    def test_extracts_client_guidelines(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir, client_items=[GUIDELINE_ITEM])
        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        _, client_g = loader.extract_guidelines()
        assert "G001" in client_g


class TestGovernanceLoaderV2ExtractAllGovernance:
    def test_returns_structure(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.extract_all_governance()
        assert "core" in result
        assert "client" in result


class TestCalculateFingerprint:
    def test_deterministic(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        data = {"items": [{"id": "M001"}], "version": "3.0"}
        fp1 = loader._calculate_fingerprint(data)
        fp2 = loader._calculate_fingerprint(data)
        assert fp1 == fp2

    def test_excludes_fingerprint_field(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        loader = GovernanceLoader(repo_root=tmp_path)
        data1 = {"items": [], "fingerprint": "abc"}
        data2 = {"items": [], "fingerprint": "xyz"}
        assert loader._calculate_fingerprint(data1) == loader._calculate_fingerprint(
            data2
        )


class TestGovernanceLoaderBadClientJson:
    def test_returns_false_when_client_json_invalid(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        # Valid core, invalid client
        core_data = {"items": [], "version": "3.0"}
        core_fp = _core_fingerprint(core_data)
        (compiled_dir / "governance-core.json").write_text(
            json.dumps({**core_data, "fingerprint": core_fp}), encoding="utf-8"
        )
        (compiled_dir / "governance-client.json").write_text(
            "not-valid-json{{{{", encoding="utf-8"
        )
        loader = GovernanceLoader(repo_root=tmp_path)
        result = loader.load_files()
        assert result is False

    def test_loads_despite_missing_metadata_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        # Remove metadata files to trigger the except branch
        (compiled_dir / "metadata-core.json").unlink()
        (compiled_dir / "metadata-client.json").unlink()
        loader = GovernanceLoader(repo_root=tmp_path)
        # Should still return True (metadata is non-critical)
        result = loader.load_files()
        assert result is True


class TestGovernanceLoaderFingerprintMismatches:
    def test_returns_false_when_core_fingerprint_wrong(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        # Corrupt the stored core fingerprint
        core_path = compiled_dir / "governance-core.json"
        data = json.loads(core_path.read_text(encoding="utf-8"))
        data["fingerprint"] = "a" * 64  # wrong fingerprint
        core_path.write_text(json.dumps(data), encoding="utf-8")

        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        valid, _ = loader.validate_fingerprints()
        assert valid is False

    def test_returns_false_when_client_fingerprint_wrong(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        # Corrupt the stored client fingerprint
        client_path = compiled_dir / "governance-client.json"
        data = json.loads(client_path.read_text(encoding="utf-8"))
        data["fingerprint"] = "b" * 64  # wrong fingerprint
        client_path.write_text(json.dumps(data), encoding="utf-8")

        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        valid, _ = loader.validate_fingerprints()
        assert valid is False

    def test_returns_false_when_salt_mismatch(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import GovernanceLoader

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)

        # Rebuild client data with wrong salt but correct fingerprint for that data
        client_path = compiled_dir / "governance-client.json"
        data = json.loads(client_path.read_text(encoding="utf-8"))
        wrong_salt = "c" * 64
        data["fingerprintpackages_salt"] = wrong_salt
        # Recalculate correct fingerprint for this modified data
        data_copy = {k: v for k, v in data.items() if k != "fingerprint"}
        new_fp = hashlib.sha256(
            json.dumps(data_copy, sort_keys=True).encode()
        ).hexdigest()
        data["fingerprint"] = new_fp
        client_path.write_text(json.dumps(data), encoding="utf-8")

        loader = GovernanceLoader(repo_root=tmp_path)
        loader.load_files()
        valid, _ = loader.validate_fingerprints()
        assert valid is False


class TestPhase2LoadCompiledV3Function:
    def test_returns_false_when_load_fails(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import (
            phase_2_load_compiled_v3,
        )

        # No files → should fail
        success, report = phase_2_load_compiled_v3(repo_root=tmp_path)
        assert success is False
        assert report["status"] == "FAILED"

    def test_returns_false_when_fingerprint_validation_fails(
        self, tmp_path: Path
    ) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import (
            phase_2_load_compiled_v3,
        )

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(compiled_dir)
        # Corrupt core fingerprint
        core_path = compiled_dir / "governance-core.json"
        data = json.loads(core_path.read_text(encoding="utf-8"))
        data["fingerprint"] = "d" * 64
        core_path.write_text(json.dumps(data), encoding="utf-8")

        success, report = phase_2_load_compiled_v3(repo_root=tmp_path)
        assert success is False
        assert report["status"] == "FAILED"

    def test_returns_true_with_valid_files(self, tmp_path: Path) -> None:
        from sdd_wizard.orchestration.phase_2_load_compiled_v3 import (
            phase_2_load_compiled_v3,
        )

        compiled_dir = _make_compiled_dir(tmp_path)
        _write_governance_files(
            compiled_dir,
            core_items=[MANDATE_ITEM],
            client_items=[GUIDELINE_ITEM],
        )
        success, report = phase_2_load_compiled_v3(repo_root=tmp_path)
        assert success is True
        assert report["status"] == "SUCCESS"
        assert report["statistics"]["mandate_count"] == 1
