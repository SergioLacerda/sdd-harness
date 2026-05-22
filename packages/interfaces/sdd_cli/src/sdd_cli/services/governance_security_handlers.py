"""Security-oriented handlers for governance commands."""

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


def run_keygen(*, key_id: str, output_dir: str, console: Console) -> None:
    """Generate Ed25519 key pair."""
    from sdd_core.utils.process import SafeProcessRunner

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    priv_path = out / f"{key_id}.key"
    pub_path = out / f"{key_id}.pub.pem"
    if priv_path.exists():
        console.print(f"[yellow]Key {key_id} already exists at {priv_path}[/yellow]")
        raise typer.Exit(0)

    runner = SafeProcessRunner()
    runner.run(
        ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(priv_path)],
        check=True,
    )
    runner.run(
        ["openssl", "pkey", "-in", str(priv_path), "-pubout", "-out", str(pub_path)],
        check=True,
    )

    console.print(
        f"[green]Generated Ed25519 key pair '{key_id}' in {output_dir}[/green]"
    )
    console.print(f"  Private: {priv_path.name} (KEEP SECRET)")
    console.print(f"  Public:  {pub_path.name}")
    console.print(
        "\n[cyan]Next step: sdd governance sign --key-id " + key_id + "[/cyan]"
    )


def resolve_compiled_dir(
    *, ws_root: Path, compiled_dir: str | None, console: Console
) -> Path:
    """Resolve compiled governance directory with profile-aware fallback."""
    from sdd_core.utils.environment import get_sdd_paths, resolve_profile

    c_dir = Path(compiled_dir) if compiled_dir else ws_root / ".sdd" / "compiled"
    if not c_dir.exists():
        try:
            active_profile = resolve_profile(root=ws_root).type
        except Exception:
            active_profile = "master"
        paths = get_sdd_paths()
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


def _perform_artifact_signing(
    *, c_dir: Path, k_path: Path, key_id: str, targets: list[str], console: Console
) -> int:
    from sdd_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()
    signed_count = 0

    for filename in targets:
        target_path = c_dir / filename
        if not target_path.exists():
            continue

        sig_path = target_path.with_suffix(target_path.suffix + ".sig")
        payload = target_path.read_bytes()
        payload_hash = hashlib.sha256(payload).hexdigest()

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


def _update_trusted_keyring(
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
    existing = next((k for k in keys if k.get("key_id") == key_id), None)
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


def run_sign(
    *,
    key_id: str,
    key_path: str | None,
    ws_root: Path,
    target_dir: Path,
    targets: list[str],
    console: Console,
) -> None:
    """Sign governance artifacts and update trusted keyring."""
    k_path = (
        Path(key_path) if key_path else ws_root / ".sdd" / "trust" / f"{key_id}.key"
    )
    if not k_path.exists():
        console.print(f"[red]ERROR: Private key not found: {k_path}[/red]")
        console.print(f"  Hint: Run 'sdd governance keygen --key-id {key_id}'")
        raise typer.Exit(1)

    signed_count = _perform_artifact_signing(
        c_dir=target_dir, k_path=k_path, key_id=key_id, targets=targets, console=console
    )
    _update_trusted_keyring(
        ws_root=ws_root, k_path=k_path, key_id=key_id, console=console
    )

    if signed_count == 0:
        console.print("[yellow]No artifacts found to sign.[/yellow]")
    else:
        console.print(
            f"[bold green]Successfully signed {signed_count} artifacts.[/bold green]"
        )
        console.print("[cyan]Next step: sdd governance audit[/cyan]")
