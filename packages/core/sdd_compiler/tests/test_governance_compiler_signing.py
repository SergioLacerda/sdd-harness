"""Tests for GovernanceCompiler signing and remaining validation paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_compiler.governance_compiler import GovernanceCompiler

_FP_CORE = "a" * 64
_FP_CLIENT = "b" * 64


def _write_governance_json(path: Path, fp: str, fp_core: str | None = None) -> None:
    data: dict = {
        "fingerprint": fp,
        "items": [
            {"type": "MANDATE", "criticality": "HIGH", "id": "M001", "title": "T"}
        ],
    }
    if fp_core:
        data["fingerprint_core_salt"] = fp_core
    path.write_text(json.dumps(data), encoding="utf-8")


def _setup_compiled(tmp_path: Path) -> GovernanceCompiler:
    _write_governance_json(tmp_path / "governance-core.json", _FP_CORE)
    _write_governance_json(
        tmp_path / "governance-client.json", _FP_CLIENT, fp_core=_FP_CORE
    )
    compiler = GovernanceCompiler(str(tmp_path))
    compiler.compile(str(tmp_path))
    return compiler


class TestCompileWithSigning:
    def test_signing_path_with_mocked_runner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        key_file = tmp_path / "signing.key"
        key_file.write_text("dummy-private-key", encoding="utf-8")
        monkeypatch.setenv("SDD_SIGNING_PRIVATE_KEY_FILE", str(key_file))
        monkeypatch.setenv("SDD_SIGNING_KEY_ID", "test-key-id")

        _write_governance_json(tmp_path / "governance-core.json", _FP_CORE)
        _write_governance_json(
            tmp_path / "governance-client.json", _FP_CLIENT, fp_core=_FP_CORE
        )
        compiler = GovernanceCompiler(str(tmp_path))

        # Mock SafeProcessRunner to simulate successful signing
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner = MagicMock()

        def _fake_run(cmd, **kwargs):  # noqa: ANN001
            # Write a fake signature file to the sig_path (3rd-to-last arg is -out)
            sig_path = Path(cmd[cmd.index("-out") + 1])
            sig_path.write_bytes(b"fake-signature-bytes")
            return mock_result

        mock_runner.run.side_effect = _fake_run
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = compiler.compile(str(tmp_path))

        assert result["signed"] is True
        assert result["signer_key_id"] == "test-key-id"
        assert result["core_signature_file"] is not None

    def test_signing_key_not_found_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "SDD_SIGNING_PRIVATE_KEY_FILE", str(tmp_path / "nonexistent.key")
        )
        _write_governance_json(tmp_path / "governance-core.json", _FP_CORE)
        _write_governance_json(
            tmp_path / "governance-client.json", _FP_CLIENT, fp_core=_FP_CORE
        )
        compiler = GovernanceCompiler(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            compiler.compile(str(tmp_path))

    def test_sign_hash_ed25519_runner_failure_raises(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        key_file = tmp_path / "key.pem"
        key_file.write_text("key", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "signing error"
        mock_result.stdout = ""
        mock_runner = MagicMock()
        mock_runner.run.return_value = mock_result

        with (
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            pytest.raises(RuntimeError, match="OpenSSL signing failed"),
        ):
            compiler._sign_hash_ed25519(
                payload_hash="abc123", private_key_file=key_file
            )

    def test_maybe_write_trusted_keyring_with_public_key(self, tmp_path: Path) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        pub_key = tmp_path / "public.pem"
        pub_key.write_text(
            "-----BEGIN PUBLIC KEY-----\nfake\n-----END PUBLIC KEY-----\n",
            encoding="utf-8",
        )
        compiler._maybe_write_trusted_keyring(
            output_path=tmp_path,
            key_id="test-key",
            public_key_file=str(pub_key),
        )
        assert (tmp_path / "trusted-keys.json").exists()
        keyring = json.loads(
            (tmp_path / "trusted-keys.json").read_text(encoding="utf-8")
        )
        assert keyring["keys"][0]["key_id"] == "test-key"

    def test_maybe_write_trusted_keyring_no_public_key_is_noop(
        self, tmp_path: Path
    ) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        compiler._maybe_write_trusted_keyring(
            output_path=tmp_path, key_id="k", public_key_file=""
        )
        assert not (tmp_path / "trusted-keys.json").exists()

    def test_maybe_write_trusted_keyring_missing_public_key_raises(
        self, tmp_path: Path
    ) -> None:
        compiler = GovernanceCompiler(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            compiler._maybe_write_trusted_keyring(
                output_path=tmp_path,
                key_id="k",
                public_key_file=str(tmp_path / "nonexistent.pem"),
            )


class TestValidationRemainingEdgeCases:
    def test_load_metadata_fails_on_unparseable_core_metadata(
        self, tmp_path: Path
    ) -> None:
        compiler = _setup_compiled(tmp_path)
        (tmp_path / "metadata-core.json").write_text("invalid json", encoding="utf-8")
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False
        assert any(
            "core_metadata_parse" in c["name"] for c in result.checks if not c["ok"]
        )

    def test_validate_fingerprints_skipped_when_meta_none(self, tmp_path: Path) -> None:
        # When both metadata files fail to parse, _validate_fingerprints gets None metas
        compiler = _setup_compiled(tmp_path)
        (tmp_path / "metadata-core.json").write_text("bad", encoding="utf-8")
        (tmp_path / "metadata-client-template.json").write_text("bad", encoding="utf-8")
        result = compiler.validate_compilation_detailed(str(tmp_path))
        # Should fail but not crash — no fingerprint validation errors expected
        assert result.ok is False

    def test_validate_signature_with_both_sigs_present(self, tmp_path: Path) -> None:
        compiler = _setup_compiled(tmp_path)
        # Create both sig files
        (tmp_path / "governance-core.json.sig").write_text("{}", encoding="utf-8")
        (tmp_path / "governance-client.json.sig").write_text("{}", encoding="utf-8")
        result = compiler.validate_compilation_detailed(str(tmp_path))
        sig_checks = [c for c in result.checks if "signature" in c["name"]]
        assert all(c["ok"] for c in sig_checks)

    def test_validate_core_sig_missing_client_present(self, tmp_path: Path) -> None:
        compiler = _setup_compiled(tmp_path)
        (tmp_path / "governance-client.json.sig").write_text("{}", encoding="utf-8")
        result = compiler.validate_compilation_detailed(str(tmp_path))
        assert result.ok is False
