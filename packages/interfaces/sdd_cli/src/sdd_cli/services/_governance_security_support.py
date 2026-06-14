"""Support helpers for governance security handlers."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json as _json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console


def resolve_compiled_dir_path(
    *,
    ws_root: Path,
    compiled_dir: str | None,
    console: Console,
    resolve_profile_fn: Any,
    get_sdd_paths_fn: Any,
) -> Path:
    c_dir = Path(compiled_dir) if compiled_dir else ws_root / ".sdd" / "compiled"
    if not c_dir.exists():
        try:
            active_profile = resolve_profile_fn(root=ws_root).type
        except Exception:
            active_profile = "master"
        paths = get_sdd_paths_fn()
        c_dir = (
            paths["master_compiled"]
            if active_profile == "master"
            else paths["client_compiled"]
        )
    if not c_dir.exists():
        console.print(f"[red]ERROR: Compiled directory not found: {c_dir}[/red]")
        console.print("  Hint: Run 'sdd governance compile' first.")
        raise typer.Exit(1)
    return c_dir


def perform_artifact_signing_flow(
    *,
    c_dir: Path,
    k_path: Path,
    key_id: str,
    targets: list[str],
    console: Console,
    runner: Any,
) -> int:
    signed_count = 0
    for filename in targets:
        target_path = c_dir / filename
        if not target_path.exists():
            continue
        sig_path = target_path.with_suffix(target_path.suffix + ".sig")
        payload_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="sdd-sign-") as td:
            msg_path = Path(td) / "msg.bin"
            sig_raw_path = Path(td) / "sig.bin"
            msg_path.write_bytes(payload_hash.encode("utf-8"))
            runner.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-sign",
                    "-inkey",
                    str(k_path),
                    "-rawin",
                    "-in",
                    str(msg_path),
                    "-out",
                    str(sig_raw_path),
                ],
                check=True,
            )
            signature_b64 = base64.b64encode(sig_raw_path.read_bytes()).decode("utf-8")
        manifest = {
            "schema_version": "1.0",
            "algorithm": "ed25519",
            "key_id": key_id,
            "artifact_name": filename,
            "profile": "master" if "core" in filename else "client",
            "payload_hash": payload_hash,
            "signature": signature_b64,
            "signed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        sig_path.write_text(_json.dumps(manifest, indent=2), encoding="utf-8")
        console.print(f"[green]Signed {filename} -> {sig_path.name}[/green]")
        signed_count += 1
    return signed_count


def update_trusted_keyring_flow(
    *, ws_root: Path, k_path: Path, key_id: str, console: Console
) -> None:
    trust_dir = ws_root / ".sdd" / "trust"
    trust_dir.mkdir(parents=True, exist_ok=True)
    keyring_path = trust_dir / "trusted-keys.json"
    pub_key_path = k_path.with_suffix(".pub.pem")
    if not pub_key_path.exists():
        return
    pub_pem = pub_key_path.read_text(encoding="utf-8")
    keyring: dict[str, Any] = {"keys": []}
    if keyring_path.exists():
        with contextlib.suppress(Exception):
            keyring = _json.loads(keyring_path.read_text(encoding="utf-8"))
    keys = keyring.setdefault("keys", [])
    existing = next((item for item in keys if item.get("key_id") == key_id), None)
    if existing:
        existing["public_key_pem"] = pub_pem
        existing["status"] = "active"
    else:
        keys.append(
            {
                "key_id": key_id,
                "public_key_pem": pub_pem,
                "status": "active",
                "not_before": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )
    keyring_path.write_text(_json.dumps(keyring, indent=2), encoding="utf-8")
    console.print(f"[green]Updated keyring at {keyring_path}[/green]")


def resolve_sign_targets(
    *,
    ws_root: Path,
    source: bool,
    compiled_dir: str | None,
    console: Console,
    resolve_compiled_dir_fn: Any,
) -> tuple[Path, list[str]]:
    if source:
        return ws_root / ".sdd" / "source", ["governance-core.json"]
    return resolve_compiled_dir_fn(
        ws_root=ws_root, compiled_dir=compiled_dir, console=console
    ), ["governance-core.json", "governance-client.json"]
