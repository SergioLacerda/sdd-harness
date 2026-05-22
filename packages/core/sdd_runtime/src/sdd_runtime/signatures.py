"""Signature validation for compiled governance artifacts.

This module provides a deterministic verification contract with canonical
result codes while keeping backward compatibility for unsigned legacy artifacts.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

_KEY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]{3,128}$")
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SignatureCheckResult:
    """SignatureCheckResult."""

    code: str
    ok: bool
    blocking: bool
    reason: str
    remediation: str = ""
    trust_source: str = "none"
    deprecation_warning: str = ""


def _remediation_for(code: str) -> str:
    mapping = {
        "SIG_MISSING": "sdd governance compile",
        "SIG_PARSE_ERROR": "sdd governance compile",
        "SIG_SCHEMA_ERROR": "sdd governance compile",
        "SIG_UNTRUSTED_KEY": "refresh trusted keyring and re-run validation",
        "SIG_INVALID": "rebuild signed artifacts with valid signer key",
        "SIG_PAYLOAD_HASH_MISMATCH": "recompile artifacts and investigate tampering",
    }
    return mapping.get(code, "review governance artifact signatures")


def _ok(
    *,
    trust_source: str = "none",
    deprecation_warning: str = "",
) -> SignatureCheckResult:
    return SignatureCheckResult(
        code="OK",
        ok=True,
        blocking=False,
        reason="ok",
        trust_source=trust_source,
        deprecation_warning=deprecation_warning,
    )


def _fail(
    code: str,
    reason: str,
    strict: bool,
    *,
    trust_source: str = "none",
    deprecation_warning: str = "",
) -> SignatureCheckResult:
    return SignatureCheckResult(
        code=code,
        ok=False,
        blocking=bool(strict),
        reason=reason,
        remediation=_remediation_for(code),
        trust_source=trust_source,
        deprecation_warning=deprecation_warning,
    )


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path}")
    return cast(dict[str, Any], loaded)


def _resolve_keyring_path(
    compiled_dir: Path, *, strict: bool, workspace_root: Path | None = None
) -> tuple[Path | None, str, str]:
    override = os.environ.get("SDD_TRUSTED_KEYRING", "").strip()
    # If workspace_root not provided, try to find it
    if workspace_root is None:
        from sdd_core.utils.environment import find_workspace_root

        workspace_root = find_workspace_root(compiled_dir) or Path.cwd()
    canonical = workspace_root / ".sdd" / "trust" / "trusted-keys.json"
    if strict:
        if canonical.exists():
            return canonical, "canonical", ""
        return (
            None,
            "none",
            "strict mode requires canonical keyring at .sdd/trust/trusted-keys.json",
        )

    candidates: list[tuple[Path, str]] = [
        # Canonical governed path always takes priority.
        (canonical, "canonical"),
    ]
    if override:
        candidates.append((Path(override), "override"))
    for candidate, source in candidates:
        if candidate.exists():
            warning = ""
            if source == "override":
                warning = (
                    "canonical keyring not found at .sdd/trust/trusted-keys.json; "
                    "using SDD_TRUSTED_KEYRING override as fallback"
                )
            return candidate, source, warning
    return None, "none", ""


def _resolve_public_key_pem(key_record: dict[str, Any]) -> str | None:
    pem = str(key_record.get("public_key_pem", "")).strip()
    if pem:
        return pem

    b64 = str(key_record.get("public_key", "")).strip()
    if not b64:
        return None
    try:
        decoded = base64.b64decode(b64)
    except Exception:
        return None
    try:
        return decoded.decode("utf-8")
    except Exception:
        return None


def _verify_ed25519_signature(
    *,
    public_key_pem: str,
    message: bytes,
    signature_b64: str,
) -> bool:
    try:
        sig_bytes = base64.b64decode(signature_b64)
    except Exception:
        return False

    with tempfile.TemporaryDirectory(prefix="sdd-sig-") as td:
        root = Path(td)
        pub_path = root / "pub.pem"
        msg_path = root / "msg.bin"
        sig_path = root / "sig.bin"
        pub_path.write_text(public_key_pem, encoding="utf-8")
        msg_path.write_bytes(message)
        sig_path.write_bytes(sig_bytes)

        # OpenSSL verification (Ed25519) via governed SafeProcessRunner
        try:
            from sdd_core.utils.process import SafeProcessRunner

            runner = SafeProcessRunner()
            cmd = [
                "openssl",
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(pub_path),
                "-rawin",
                "-in",
                str(msg_path),
                "-sigfile",
                str(sig_path),
            ]
            result = runner.run(cmd, capture_output=True)
            return result.success
        except Exception:
            # If governed execution fails, fall back to False (signature invalid)
            return False


def _validate_manifest_schema(sig: dict[str, Any]) -> str | None:
    required = {
        "schema_version",
        "algorithm",
        "key_id",
        "artifact_name",
        "profile",
        "payload_hash",
        "signature",
        "signed_at",
    }
    missing = sorted(required - set(sig.keys()))
    if missing:
        return f"missing required fields: {missing}"
    if str(sig.get("schema_version")) != "1.0":
        return "schema_version must be '1.0'"
    if str(sig.get("algorithm")) != "ed25519":
        return "algorithm must be 'ed25519'"
    key_id = str(sig.get("key_id", ""))
    if not _KEY_ID_PATTERN.match(key_id):
        return "invalid key_id pattern"
    profile = str(sig.get("profile", ""))
    if profile not in {"master", "client"}:
        return "profile must be master|client"
    payload_hash = str(sig.get("payload_hash", ""))
    if not _HEX64_PATTERN.match(payload_hash):
        return "payload_hash must be lowercase hex sha256"
    if not str(sig.get("signature", "")).strip():
        return "signature must be non-empty base64"
    if not str(sig.get("signed_at", "")).endswith("Z"):
        return "signed_at must be RFC3339 UTC timestamp ending with Z"
    return None


def _is_key_time_valid(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    not_before = str(record.get("not_before", "")).strip()
    not_after = str(record.get("not_after", "")).strip()
    try:
        if not_before:
            nb = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
            if now < nb:
                return False
        if not_after:
            na = datetime.fromisoformat(not_after.replace("Z", "+00:00"))
            if now > na:
                return False
    except Exception:
        return False
    return True


def validate_artifact_signature(  # noqa: C901
    *,
    artifact_path: Path,
    sig_path: Path,
    strict: bool = False,
    workspace_root: Path | None = None,
) -> SignatureCheckResult:
    """Validate Artifact Signature."""
    if not sig_path.exists():
        return _fail("SIG_MISSING", f"missing signature file: {sig_path}", strict)

    try:
        sig = _load_json(sig_path)
    except Exception as exc:
        return _fail("SIG_PARSE_ERROR", f"invalid signature json: {exc}", strict)

    schema_error = _validate_manifest_schema(sig)
    if schema_error:
        return _fail("SIG_SCHEMA_ERROR", schema_error, strict)

    expected_name = artifact_path.name
    actual_name = str(sig.get("artifact_name", ""))
    if expected_name != actual_name:
        return _fail(
            "SIG_SCHEMA_ERROR",
            f"artifact_name mismatch: expected {expected_name}, got {actual_name}",
            strict,
        )

    payload_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    signed_hash = str(sig.get("payload_hash", ""))
    if payload_hash != signed_hash:
        return _fail(
            "SIG_PAYLOAD_HASH_MISMATCH",
            "artifact bytes do not match signed payload hash",
            strict,
        )

    keyring_path, trust_source, trust_warning = _resolve_keyring_path(
        artifact_path.parent, strict=strict, workspace_root=workspace_root
    )
    if keyring_path is None:
        reason = "trusted keyring not found"
        if trust_warning:
            reason = trust_warning
        return _fail(
            "SIG_UNTRUSTED_KEY",
            reason,
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    try:
        keyring = _load_json(keyring_path)
    except Exception as exc:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"could not load trusted keyring: {exc}",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    records = keyring.get("keys", [])
    if not isinstance(records, list):
        return _fail(
            "SIG_UNTRUSTED_KEY",
            "invalid keyring format",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    key_id = str(sig.get("key_id", ""))
    record = next((r for r in records if str(r.get("key_id")) == key_id), None)
    if record is None:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' not trusted",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    status = str(record.get("status", "active")).lower()
    if status == "revoked":
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' is revoked",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )
    if status not in {"active", "deprecated"}:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' invalid status",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )
    if not _is_key_time_valid(record):
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' outside validity window",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    public_key_pem = _resolve_public_key_pem(record)
    if not public_key_pem:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            "trusted key missing public key",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    ok = _verify_ed25519_signature(
        public_key_pem=public_key_pem,
        message=signed_hash.encode("utf-8"),
        signature_b64=str(sig.get("signature", "")),
    )
    if not ok:
        return _fail(
            "SIG_INVALID",
            "ed25519 verification failed",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    return _ok(trust_source=trust_source, deprecation_warning=trust_warning)


def validate_compiled_signatures(
    compiled_dir: Path, *, strict: bool = False, workspace_root: Path | None = None
) -> list[SignatureCheckResult]:
    """Validate signatures for known governance compiled artifacts."""
    targets = [
        compiled_dir / "governance-core.json",
        compiled_dir / "governance-client.json",
    ]
    results: list[SignatureCheckResult] = []
    for artifact in targets:
        if not artifact.exists():
            # Existing structural checks already handle this case.
            continue
        results.append(
            validate_artifact_signature(
                artifact_path=artifact,
                sig_path=artifact.with_suffix(artifact.suffix + ".sig"),
                strict=strict,
                workspace_root=workspace_root,
            )
        )
    return results
