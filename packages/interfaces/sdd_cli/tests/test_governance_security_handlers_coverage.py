"""Tests for sdd_cli.services.governance_security_handlers — full coverage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from sdd_cli.services.governance_security_handlers import (
    _perform_artifact_signing,
    _update_trusted_keyring,
    resolve_compiled_dir,
    run_keygen,
    run_sign,
)

pytestmark = pytest.mark.unit

_CONSOLE = Console(highlight=False)


# ---------------------------------------------------------------------------
# run_keygen
# ---------------------------------------------------------------------------


class TestRunKeygen:
    def test_key_already_exists_exits_0(self, tmp_path: Path) -> None:
        out = tmp_path / "keys"
        out.mkdir()
        (out / "mykey.key").write_text("existing", encoding="utf-8")
        with pytest.raises(typer.Exit) as exc_info:
            run_keygen(key_id="mykey", output_dir=str(out), console=_CONSOLE)
        assert exc_info.value.exit_code == 0

    def test_generates_key_pair(self, tmp_path: Path) -> None:
        out = tmp_path / "keys"
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            run_keygen(key_id="newkey", output_dir=str(out), console=_CONSOLE)
        assert mock_runner.run.call_count == 2
        calls = mock_runner.run.call_args_list
        assert any("genpkey" in str(c) for c in calls)
        assert any("pkey" in str(c) for c in calls)

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "deep" / "keys"
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            run_keygen(key_id="mykey", output_dir=str(out), console=_CONSOLE)
        assert out.exists()


# ---------------------------------------------------------------------------
# resolve_compiled_dir
# ---------------------------------------------------------------------------


class TestResolveCompiledDir:
    def test_explicit_path_returned(self, tmp_path: Path) -> None:
        compiled = tmp_path / "compiled"
        compiled.mkdir()
        result = resolve_compiled_dir(
            ws_root=tmp_path, compiled_dir=str(compiled), console=_CONSOLE
        )
        assert result == compiled

    def test_default_path_used_when_exists(self, tmp_path: Path) -> None:
        compiled = tmp_path / ".sdd" / "compiled"
        compiled.mkdir(parents=True)
        result = resolve_compiled_dir(
            ws_root=tmp_path, compiled_dir=None, console=_CONSOLE
        )
        assert result == compiled

    def test_fallback_to_sdd_paths_when_default_missing(self, tmp_path: Path) -> None:
        master_compiled = tmp_path / "master_compiled"
        master_compiled.mkdir()
        mock_profile = MagicMock(type="master")
        mock_paths = {
            "master_compiled": master_compiled,
            "client_compiled": tmp_path / "nope",
        }
        with (
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=mock_profile
            ),
            patch("sdd_core.utils.environment.get_sdd_paths", return_value=mock_paths),
        ):
            result = resolve_compiled_dir(
                ws_root=tmp_path, compiled_dir=None, console=_CONSOLE
            )
        assert result == master_compiled

    def test_fallback_profile_exception_defaults_to_master(
        self, tmp_path: Path
    ) -> None:
        master_compiled = tmp_path / "master_compiled"
        master_compiled.mkdir()
        mock_paths = {
            "master_compiled": master_compiled,
            "client_compiled": tmp_path / "nope",
        }
        with (
            patch(
                "sdd_core.utils.environment.resolve_profile",
                side_effect=Exception("fail"),
            ),
            patch("sdd_core.utils.environment.get_sdd_paths", return_value=mock_paths),
        ):
            result = resolve_compiled_dir(
                ws_root=tmp_path, compiled_dir=None, console=_CONSOLE
            )
        assert result == master_compiled

    def test_not_found_exits_1(self, tmp_path: Path) -> None:
        mock_paths = {
            "master_compiled": tmp_path / "nope1",
            "client_compiled": tmp_path / "nope2",
        }
        with (
            patch("sdd_core.utils.environment.resolve_profile", side_effect=Exception),
            patch("sdd_core.utils.environment.get_sdd_paths", return_value=mock_paths),
            pytest.raises(typer.Exit) as exc_info,
        ):
            resolve_compiled_dir(ws_root=tmp_path, compiled_dir=None, console=_CONSOLE)
        assert exc_info.value.exit_code == 1


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


# ---------------------------------------------------------------------------
# run_sign
# ---------------------------------------------------------------------------


class TestRunSign:
    def test_key_not_found_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_sign(
                key_id="missing",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=["artifact.json"],
                console=_CONSOLE,
            )
        assert exc_info.value.exit_code == 1

    def test_explicit_key_path_used(self, tmp_path: Path) -> None:
        k_path = tmp_path / "custom.key"
        k_path.write_text("priv", encoding="utf-8")

        with (
            patch(
                "sdd_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=0,
            ),
            patch(
                "sdd_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="custom",
                key_path=str(k_path),
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=[],
                console=_CONSOLE,
            )

    def test_no_artifacts_prints_warning(self, tmp_path: Path) -> None:
        k_path = tmp_path / ".sdd" / "trust" / "nokey.key"
        k_path.parent.mkdir(parents=True)
        k_path.write_text("priv", encoding="utf-8")

        with (
            patch(
                "sdd_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=0,
            ),
            patch(
                "sdd_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="nokey",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=[],
                console=_CONSOLE,
            )

    def test_success_prints_summary(self, tmp_path: Path) -> None:
        k_path = tmp_path / ".sdd" / "trust" / "testkey.key"
        k_path.parent.mkdir(parents=True)
        k_path.write_text("priv", encoding="utf-8")

        with (
            patch(
                "sdd_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=2,
            ),
            patch(
                "sdd_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="testkey",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=["a.json", "b.json"],
                console=_CONSOLE,
            )
