"""Governance Compiler."""

import base64
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast

import msgpack

"""
PHASE 2: Governance Compiler
Converts governance-core.json and governance-client.json to msgpack format

Input:  governance-core.json + governance-client.json (from PHASE 1 pipeline)
Output: governance-core.compiled.msgpack + governance-client-template.compiled.msgpack

Process:
1. Load JSON files (with fingerprints already calculated)
2. Serialize to msgpack binary format
3. Generate metadata with fingerprints and item counts
4. Save msgpack files for runtime use

Note: This is a SIMPLE compiler - no complex logic, just serialization and fingerprints.
"""


class GovernanceCompiler:
    """Compiles governance JSON files to msgpack format"""

    def __init__(self, compiled_dir: str = "compiled"):
        """
        Initialize compiler with path to compiled JSONs

        Args:
            compiled_dir: Directory containing governance-core.json and governance-client.json
        """
        self.compiled_dir = Path(compiled_dir)
        self.core_json_file = self.compiled_dir / "governance-core.json"
        self.client_json_file = self.compiled_dir / "governance-client.json"

    def compile(self, output_dir: str = "compiled") -> "CompilationResult":
        """
        Main compilation process

        Returns:
            Typed compilation result (file paths, fingerprints, etc)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        audit_dir = output_path / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        # Load JSON files
        core_data = self._load_json(self.core_json_file)
        client_data = self._load_json(self.client_json_file)

        if not core_data or not client_data:
            raise ValueError("Could not load governance JSON files")

        # Serialize to msgpack
        core_msgpack = self._serialize_to_msgpack(core_data)
        client_msgpack = self._serialize_to_msgpack(client_data)

        # Save msgpack files
        core_msgpack_file = output_path / "governance-core.compiled.msgpack"
        client_msgpack_file = (
            output_path / "governance-client-template.compiled.msgpack"
        )

        core_msgpack_file.write_bytes(core_msgpack)
        client_msgpack_file.write_bytes(client_msgpack)

        # Canonical decision payloads (runtime-consumed JSON DTOs)
        core_json_out = output_path / "governance-core.json"
        client_json_out = output_path / "governance-client.json"
        core_json_out.write_text(
            json.dumps(core_data, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        client_json_out.write_text(
            json.dumps(client_data, indent=2, ensure_ascii=True), encoding="utf-8"
        )

        # Optional signature emission (Ed25519 via OpenSSL).
        core_sig_file: str | None = None
        client_sig_file: str | None = None
        signed = False
        signer_key_id = ""
        signature_files: list[str] = []
        signing_required = os.environ.get(
            "SDD_SIGNING_REQUIRED", ""
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        signing_key = os.environ.get("SDD_SIGNING_PRIVATE_KEY_FILE", "").strip()
        if signing_required and not signing_key:
            raise RuntimeError(
                "Signing is required but SDD_SIGNING_PRIVATE_KEY_FILE is not set"
            )
        if signing_key:
            signer_key_id = (
                os.environ.get("SDD_SIGNING_KEY_ID", "dev-key").strip() or "dev-key"
            )
            core_sig_file = str(
                self._sign_artifact(
                    artifact_path=core_json_out,
                    profile="master",
                    key_id=signer_key_id,
                    private_key_file=Path(signing_key),
                )
            )
            client_sig_file = str(
                self._sign_artifact(
                    artifact_path=client_json_out,
                    profile="client",
                    key_id=signer_key_id,
                    private_key_file=Path(signing_key),
                )
            )
            self._maybe_write_trusted_keyring(
                output_path=output_path,
                key_id=signer_key_id,
                public_key_file=os.environ.get(
                    "SDD_SIGNING_PUBLIC_KEY_FILE", ""
                ).strip(),
            )
            signed = True
            signature_files.extend([core_sig_file, client_sig_file])

        # Extract fingerprints from JSON (already calculated by pipeline)
        core_fingerprint: str = str(core_data.get("fingerprint") or "")
        client_fingerprint: str = str(client_data.get("fingerprint") or "")
        core_fingerprint_salt = client_data.get("fingerprint_core_salt")

        # Generate metadata files
        self._generate_metadata(
            audit_dir,
            "core",
            core_data,
            core_fingerprint,
        )
        self._generate_metadata(
            audit_dir,
            "client-template",
            client_data,
            client_fingerprint,
        )

        # Backward compatibility: keep legacy metadata files at compiled root.
        for name in ("metadata-core.json", "metadata-client-template.json"):
            src = audit_dir / name
            dst = output_path / name
            shutil.copy2(src, dst)

        return {
            "core_msgpack_file": str(core_msgpack_file),
            "client_msgpack_file": str(client_msgpack_file),
            "core_metadata": str(audit_dir / "metadata-core.json"),
            "client_metadata": str(audit_dir / "metadata-client-template.json"),
            "core_fingerprint": core_fingerprint,
            "client_fingerprint": client_fingerprint,
            "core_fingerprint_salt": core_fingerprint_salt,
            "core_item_count": len(core_data.get("items", [])),
            "client_item_count": len(client_data.get("items", [])),
            "core_signature_file": core_sig_file,
            "client_signature_file": client_sig_file,
            "signed": signed,
            "signer_key_id": signer_key_id,
            "signature_files": signature_files,
            "legacy_trust_migration": {
                "window_releases": 2,
                "legacy_keyring_paths": [
                    str(output_path / "trusted-keys.json"),
                    str(output_path / "audit" / "trusted-keys.json"),
                ],
                "canonical_keyring_path": ".sdd/trust/trusted-keys.json",
                "removal_timeline": "remove legacy trust path fallback after 2 releases",
            },
        }

    def _sign_artifact(
        self,
        *,
        artifact_path: Path,
        profile: str,
        key_id: str,
        private_key_file: Path,
    ) -> Path:
        payload_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        signature_b64 = self._sign_hash_ed25519(
            payload_hash=payload_hash, private_key_file=private_key_file
        )
        manifest = {
            "schema_version": "1.0",
            "algorithm": "ed25519",
            "key_id": key_id,
            "artifact_name": artifact_path.name,
            "profile": profile,
            "payload_hash": payload_hash,
            "signature": signature_b64,
            "signed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        sig_path = artifact_path.with_suffix(artifact_path.suffix + ".sig")
        sig_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        return sig_path

    def _sign_hash_ed25519(self, *, payload_hash: str, private_key_file: Path) -> str:
        if not private_key_file.exists():
            raise FileNotFoundError(f"Signing key not found: {private_key_file}")
        with tempfile.TemporaryDirectory(prefix="sdd-sign-") as td:
            root = Path(td)
            msg_path = root / "msg.bin"
            sig_path = root / "sig.bin"
            msg_path.write_bytes(payload_hash.encode("utf-8"))

            # Use governed SafeProcessRunner for OpenSSL signing
            try:
                from sdd_core.utils.process import SafeProcessRunner

                runner = SafeProcessRunner()
                cmd = [
                    "openssl",
                    "pkeyutl",
                    "-sign",
                    "-inkey",
                    str(private_key_file),
                    "-rawin",
                    "-in",
                    str(msg_path),
                    "-out",
                    str(sig_path),
                ]
                result = runner.run(cmd, capture_output=True)
                if not result.success:
                    stderr = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(f"OpenSSL signing failed: {stderr}")
                return base64.b64encode(sig_path.read_bytes()).decode("ascii")
            except (ImportError, ValueError) as exc:
                # Fallback: if SafeProcessRunner unavailable, raise error
                raise RuntimeError(f"Failed to execute OpenSSL: {exc}") from exc

    def _maybe_write_trusted_keyring(
        self,
        *,
        output_path: Path,
        key_id: str,
        public_key_file: str,
    ) -> None:
        if not public_key_file:
            return
        pub = Path(public_key_file)
        if not pub.exists():
            raise FileNotFoundError(f"Public key file not found: {pub}")

        pub_pem = pub.read_text(encoding="utf-8")
        record = {
            "key_id": key_id,
            "algorithm": "ed25519",
            "status": "active",
            "public_key_pem": pub_pem,
            "not_before": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        keyring = {"version": "1.0", "keys": [record]}
        trust_dir = self._resolve_trust_dir(output_path)
        targets = [
            trust_dir / "trusted-keys.json",
            output_path / "trusted-keys.json",  # legacy compatibility
            output_path / "audit" / "trusted-keys.json",  # legacy compatibility
        ]
        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(keyring, indent=2, ensure_ascii=True), encoding="utf-8"
            )

    def _resolve_trust_dir(self, output_path: Path) -> Path:
        for parent in [output_path, *output_path.parents]:
            sdd_dir = parent / ".sdd" / "trust"
            if (parent / ".sdd").exists():
                return sdd_dir
        # Keep writes scoped to the requested output tree. Falling back to a
        # CWD-relative ".sdd/trust" can mutate repository state during tests.
        return output_path / ".sdd" / "trust"

    def _load_json(self, file_path: Path) -> dict[str, Any] | None:
        """Load JSON file"""
        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        except Exception:
            return None

    def _serialize_to_msgpack(self, data: dict[str, Any]) -> bytes:
        """
        Serialize dictionary to msgpack binary format

        Args:
            data: Dictionary to serialize

        Returns:
            msgpack binary data
        """
        return bytes(msgpack.packb(data, use_bin_type=True))

    def _generate_metadata(
        self,
        output_dir: Path,
        file_type: str,
        data: dict[str, Any],
        fingerprint: str,
    ) -> None:
        """
        Generate metadata JSON file for compiled file

        Args:
            output_dir: Directory to save metadata
            file_type: "core" or "client-template"
            data: Original JSON data
            fingerprint: SHA-256 fingerprint
        """
        metadata = {
            "version": "3.0",
            "type": file_type,
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "fingerprint": fingerprint,
            "item_count": len(data.get("items", [])),
            "items_by_type": self._count_items_by_type(data),
            "items_by_criticality": self._count_items_by_criticality(data),
            "readonly": file_type
            == "core",  # Core is immutable, client is customizable
            "customizable": file_type == "client-template",
        }

        # Add core salt for client metadata
        if file_type == "client-template":
            metadata["fingerprint_core_salt"] = data.get("fingerprint_core_salt")

        metadata_file = output_dir / f"metadata-{file_type}.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=True)

    def _count_items_by_type(self, data: dict[str, Any]) -> dict[str, int]:
        """Count items by type (normalized to uppercase)"""
        counts: dict[str, int] = {}
        for item in data.get("items", []):
            item_type = item.get("type", "UNKNOWN").upper()
            counts[item_type] = counts.get(item_type, 0) + 1
        return counts

    def _count_items_by_criticality(self, data: dict[str, Any]) -> dict[str, int]:
        """Count items by criticality level"""
        counts: dict[str, int] = {}
        for item in data.get("items", []):
            criticality = item.get("criticality", "UNKNOWN")
            counts[criticality] = counts.get(criticality, 0) + 1
        return counts

    def validate_compilation_detailed(
        self, output_dir: str = "compiled"
    ) -> "ValidationResult":
        """
        Validate compilation and return structured diagnostics.
        """
        output_path = Path(output_dir)
        checks: list[ValidationCheck] = []
        errors: list[str] = []
        context = _ValidationContext(output_path=output_path)

        self._validate_artifacts_presence(context, checks, errors)
        if not errors:
            self._validate_metadata_presence(context, checks, errors)
        if not errors:
            self._load_metadata(context, checks, errors)
        if not errors:
            self._validate_fingerprints(context, checks, errors)
            self._validate_flags(context, checks, errors)
            self._validate_signatures(context, checks, errors)
        return ValidationResult(ok=not errors, errors=errors, checks=checks)

    def validate_compilation(self, output_dir: str = "compiled") -> bool:
        """
        Backward-compatible boolean validation entrypoint.
        """
        return self.validate_compilation_detailed(output_dir).ok

    def _validate_artifacts_presence(
        self,
        context: "_ValidationContext",
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        for label, path in (
            ("core_msgpack_exists", context.core_msgpack),
            ("client_msgpack_exists", context.client_msgpack),
        ):
            self._assert_path_exists(
                label=label,
                path=path,
                checks=checks,
                errors=errors,
            )

    def _validate_metadata_presence(
        self,
        context: "_ValidationContext",
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        for label, path in (
            ("core_metadata_exists", context.core_metadata),
            ("client_metadata_exists", context.client_metadata),
        ):
            self._assert_path_exists(
                label=label,
                path=path,
                checks=checks,
                errors=errors,
            )

    def _load_metadata(
        self,
        context: "_ValidationContext",
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        context.core_meta = self._load_json(context.core_metadata)
        context.client_meta = self._load_json(context.client_metadata)
        if context.core_meta is None:
            self._fail(
                check="core_metadata_parse",
                message=f"Could not parse metadata JSON: {context.core_metadata}",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append({"name": "core_metadata_parse", "ok": True, "details": "ok"})
        if context.client_meta is None:
            self._fail(
                check="client_metadata_parse",
                message=f"Could not parse metadata JSON: {context.client_metadata}",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {"name": "client_metadata_parse", "ok": True, "details": "ok"}
            )

    def _validate_fingerprints(
        self,
        context: "_ValidationContext",
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        if context.core_meta is None or context.client_meta is None:
            return
        core_fp = context.core_meta.get("fingerprint")
        client_fp = context.client_meta.get("fingerprint")

        if not _is_valid_fingerprint(core_fp):
            self._fail(
                check="core_fingerprint_valid",
                message=f"Invalid core fingerprint: {core_fp}",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {
                    "name": "core_fingerprint_valid",
                    "ok": True,
                    "details": str(core_fp),
                }
            )

        if not _is_valid_fingerprint(client_fp):
            self._fail(
                check="client_fingerprint_valid",
                message=f"Invalid client fingerprint: {client_fp}",
                checks=checks,
                errors=errors,
            )
            return
        checks.append(
            {
                "name": "client_fingerprint_valid",
                "ok": True,
                "details": str(client_fp),
            }
        )

        if core_fp == client_fp:
            self._fail(
                check="fingerprints_different",
                message="Core and client fingerprints are identical (should be different)",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {"name": "fingerprints_different", "ok": True, "details": "ok"}
            )

        core_salt = context.client_meta.get("fingerprint_core_salt")
        if core_salt != core_fp:
            self._fail(
                check="client_uses_core_salt",
                message="Core fingerprint not used as salt for client",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {"name": "client_uses_core_salt", "ok": True, "details": "ok"}
            )

    def _validate_flags(
        self,
        context: "_ValidationContext",
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        if context.core_meta is None or context.client_meta is None:
            return
        if context.core_meta.get("readonly") is not True:
            self._fail(
                check="core_readonly_true",
                message="Core metadata readonly flag not True",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append({"name": "core_readonly_true", "ok": True, "details": "ok"})

        if context.client_meta.get("customizable") is not True:
            self._fail(
                check="client_customizable_true",
                message="Client metadata customizable flag not True",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {"name": "client_customizable_true", "ok": True, "details": "ok"}
            )

    def _validate_signatures(
        self,
        context: "_ValidationContext",
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        any_sig = context.core_sig.exists() or context.client_sig.exists()
        if not any_sig:
            checks.append(
                {"name": "signatures_consistent", "ok": True, "details": "n/a"}
            )
            return

        if not context.core_sig.exists():
            self._fail(
                check="core_signature_exists",
                message=f"Missing core signature file: {context.core_sig}",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {"name": "core_signature_exists", "ok": True, "details": "ok"}
            )
        if not context.client_sig.exists():
            self._fail(
                check="client_signature_exists",
                message=f"Missing client signature file: {context.client_sig}",
                checks=checks,
                errors=errors,
            )
        else:
            checks.append(
                {"name": "client_signature_exists", "ok": True, "details": "ok"}
            )

    def _assert_path_exists(
        self,
        *,
        label: str,
        path: Path,
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        if not path.exists():
            self._fail(
                check=label,
                message=f"File not found: {path}",
                checks=checks,
                errors=errors,
            )
            return
        checks.append({"name": label, "ok": True, "details": str(path)})

    def _fail(
        self,
        *,
        check: str,
        message: str,
        checks: list["ValidationCheck"],
        errors: list[str],
    ) -> None:
        checks.append({"name": check, "ok": False, "details": message})
        errors.append(message)


class LegacyTrustMigration(TypedDict):
    """LegacyTrustMigration."""

    window_releases: int
    legacy_keyring_paths: list[str]
    canonical_keyring_path: str
    removal_timeline: str


class CompilationResult(TypedDict):
    """CompilationResult."""

    core_msgpack_file: str
    client_msgpack_file: str
    core_metadata: str
    client_metadata: str
    core_fingerprint: str
    client_fingerprint: str
    core_fingerprint_salt: str | None
    core_item_count: int
    client_item_count: int
    core_signature_file: str | None
    client_signature_file: str | None
    signed: bool
    signer_key_id: str
    signature_files: list[str]
    legacy_trust_migration: LegacyTrustMigration


class ValidationCheck(TypedDict):
    """ValidationCheck."""

    name: str
    ok: bool
    details: str


@dataclass(frozen=True)
class ValidationResult:
    """ValidationResult."""

    ok: bool
    errors: list[str]
    checks: list[ValidationCheck]


@dataclass
class _ValidationContext:
    output_path: Path
    core_meta: dict[str, Any] | None = None
    client_meta: dict[str, Any] | None = None

    @property
    def core_msgpack(self) -> Path:
        return self.output_path / "governance-core.compiled.msgpack"

    @property
    def client_msgpack(self) -> Path:
        return self.output_path / "governance-client-template.compiled.msgpack"

    @property
    def core_metadata(self) -> Path:
        return self.output_path / "metadata-core.json"

    @property
    def client_metadata(self) -> Path:
        return self.output_path / "metadata-client-template.json"

    @property
    def core_json(self) -> Path:
        return self.output_path / "governance-core.json"

    @property
    def client_json(self) -> Path:
        return self.output_path / "governance-client.json"

    @property
    def core_sig(self) -> Path:
        return self.core_json.with_suffix(self.core_json.suffix + ".sig")

    @property
    def client_sig(self) -> Path:
        return self.client_json.with_suffix(self.client_json.suffix + ".sig")


def _is_valid_fingerprint(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64


if __name__ == "__main__":
    # Example usage
    compiler = GovernanceCompiler("compiled")
    result = compiler.compile("compiled")

    print("✅ PHASE 2: Compilation completed")  # noqa: T201
    print(f"  Core msgpack: {result['core_msgpack_file']}")  # noqa: T201
    print(f"  Client msgpack: {result['client_msgpack_file']}")  # noqa: T201
    print(f"  Core fingerprint: {result['core_fingerprint']}")  # noqa: T201
    print(f"  Client fingerprint: {result['client_fingerprint']}")  # noqa: T201
    print(f"  Core items: {result['core_item_count']}")  # noqa: T201
    print(f"  Client items: {result['client_item_count']}")  # noqa: T201

    # Validate
    if compiler.validate_compilation("compiled"):
        print("✅ All validations passed")  # noqa: T201
    else:
        print("❌ Validation failed")  # noqa: T201
