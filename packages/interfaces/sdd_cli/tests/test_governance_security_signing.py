"""Tests for sdd_cli.services.governance_security_handlers — artifact signing and keyring."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from sdd_cli.services.governance_security_handlers import (
    _perform_artifact_signing,
    _update_trusted_keyring,
)

pytestmark = pytest.mark.unit

_CONSOLE = Console(highlight=False)


# ---------------------------------------------------------------------------
# _perform_artifact_signing
# ---------------------------------------------------------------------------


class TestPerformArtifactSigning:
    def test_signs_existing_artifact(self, tmp_path: Path) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text('{"key": "value"}', encoding="utf-8")

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        # Fake the sig.bin output from openssl pkeyutl
        def fake_run(cmd, **kwargs):  # noqa: ANN001
            if "-out" in cmd:
                out_idx = cmd.index("-out") + 1
                Path(cmd[out_idx]).write_bytes(b"fake-signature")
            return MagicMock(success=True)

        mock_runner.run.side_effect = fake_run

        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            count = _perform_artifact_signing(
                c_dir=tmp_path,
                k_path=tmp_path / "mykey.key",
                key_id="mykey",
                targets=["governance-core.json"],
                console=_CONSOLE,
            )

        assert count == 1
        sig_file = tmp_path / "governance-core.json.sig"
        assert sig_file.exists()
        manifest = json.loads(sig_file.read_text(encoding="utf-8"))
        assert manifest["key_id"] == "mykey"
        assert manifest["algorithm"] == "ed25519"

    def test_skips_missing_artifact(self, tmp_path: Path) -> None:
        mock_runner = MagicMock()
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            count = _perform_artifact_signing(
                c_dir=tmp_path,
                k_path=tmp_path / "key.key",
                key_id="k",
                targets=["nonexistent.json"],
                console=_CONSOLE,
            )
        assert count == 0
        mock_runner.run.assert_not_called()

    def test_profile_uses_core_in_name(self, tmp_path: Path) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")

        def fake_run(cmd, **kwargs):  # noqa: ANN001
            if "-out" in cmd:
                Path(cmd[cmd.index("-out") + 1]).write_bytes(b"sig")
            return MagicMock(success=True)

        mock_runner = MagicMock()
        mock_runner.run.side_effect = fake_run

        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            _perform_artifact_signing(
                c_dir=tmp_path,
                k_path=tmp_path / "k.key",
                key_id="k",
                targets=["governance-core.json"],
                console=_CONSOLE,
            )

        sig = json.loads(
            (tmp_path / "governance-core.json.sig").read_text(encoding="utf-8")
        )
        assert sig["profile"] == "master"

    def test_profile_client_for_non_core(self, tmp_path: Path) -> None:
        artifact = tmp_path / "skill-registry.json"
        artifact.write_text("{}", encoding="utf-8")

        def fake_run(cmd, **kwargs):  # noqa: ANN001
            if "-out" in cmd:
                Path(cmd[cmd.index("-out") + 1]).write_bytes(b"sig")
            return MagicMock(success=True)

        mock_runner = MagicMock()
        mock_runner.run.side_effect = fake_run

        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            _perform_artifact_signing(
                c_dir=tmp_path,
                k_path=tmp_path / "k.key",
                key_id="k",
                targets=["skill-registry.json"],
                console=_CONSOLE,
            )

        sig = json.loads(
            (tmp_path / "skill-registry.json.sig").read_text(encoding="utf-8")
        )
        assert sig["profile"] == "client"


# ---------------------------------------------------------------------------
# _update_trusted_keyring
# ---------------------------------------------------------------------------


class TestUpdateTrustedKeyring:
    def test_creates_keyring_with_new_key(self, tmp_path: Path) -> None:
        k_path = tmp_path / "mykey.key"
        pub_path = tmp_path / "mykey.pub.pem"
        k_path.write_text("priv", encoding="utf-8")
        pub_path.write_text("-----BEGIN PUBLIC KEY-----\n", encoding="utf-8")

        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )

        keyring_path = tmp_path / ".sdd" / "trust" / "trusted-keys.json"
        assert keyring_path.exists()
        data = json.loads(keyring_path.read_text(encoding="utf-8"))
        assert any(k["key_id"] == "mykey" for k in data["keys"])

    def test_updates_existing_key(self, tmp_path: Path) -> None:
        trust_dir = tmp_path / ".sdd" / "trust"
        trust_dir.mkdir(parents=True)
        keyring_path = trust_dir / "trusted-keys.json"
        keyring_path.write_text(
            json.dumps({"keys": [{"key_id": "mykey", "status": "retired"}]}),
            encoding="utf-8",
        )
        k_path = tmp_path / "mykey.key"
        pub_path = tmp_path / "mykey.pub.pem"
        k_path.write_text("priv", encoding="utf-8")
        pub_path.write_text("-----BEGIN PUBLIC KEY-----\n", encoding="utf-8")

        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )

        data = json.loads(keyring_path.read_text(encoding="utf-8"))
        entry = next(k for k in data["keys"] if k["key_id"] == "mykey")
        assert entry["status"] == "active"

    def test_no_pub_key_returns_early(self, tmp_path: Path) -> None:
        k_path = tmp_path / "mykey.key"
        k_path.write_text("priv", encoding="utf-8")
        # No .pub.pem file

        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )

        keyring_path = tmp_path / ".sdd" / "trust" / "trusted-keys.json"
        assert not keyring_path.exists()

    def test_handles_corrupted_keyring(self, tmp_path: Path) -> None:
        trust_dir = tmp_path / ".sdd" / "trust"
        trust_dir.mkdir(parents=True)
        keyring_path = trust_dir / "trusted-keys.json"
        keyring_path.write_text("not valid json", encoding="utf-8")

        k_path = tmp_path / "mykey.key"
        pub_path = tmp_path / "mykey.pub.pem"
        k_path.write_text("priv", encoding="utf-8")
        pub_path.write_text("-----BEGIN PUBLIC KEY-----\n", encoding="utf-8")

        # Should not raise
        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )
