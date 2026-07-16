"""CompilerRunner: Python bridge to the Go `sdd-compile` binary.

This is the only Python-facing entrypoint for invoking governance
compilation. It replaces direct imports of `sdd_compiler.governance_compiler`
with subprocess calls to the Go binary, parsing its JSON stdout output.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import sys
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, TypedDict, cast

from sdd_core.utils.environment import detect_repo_root
from sdd_core.utils.process import SafeProcessRunner

__all__ = [
    "CompilationResult",
    "CompilerRunner",
    "CompilerRunnerError",
    "SignResult",
    "ValidationCheck",
    "ValidationResult",
    "VerifyResult",
]

_RELEASE_REPO = "SergioLacerda/sdd-harness"
_DOWNLOAD_TIMEOUT_SECONDS = 30


class CompilerRunnerError(RuntimeError):
    """Raised when the sdd-compile binary cannot be located or fails."""


class CompilationResult(TypedDict, total=False):
    """Mirrors the Go binary's `compile` JSON output."""

    ok: bool
    core_msgpack_file: str
    client_msgpack_file: str
    core_metadata: str
    client_metadata: str
    core_fingerprint: str
    client_fingerprint: str
    core_fingerprint_salt: str | None
    core_item_count: int
    client_item_count: int
    signed: bool
    signer_key_id: str
    signature_files: list[str]
    error: str


class ValidationCheck(TypedDict):
    """A single named validation check result."""

    name: str
    ok: bool
    details: str


class ValidationResult(TypedDict):
    """Mirrors the Go binary's `validate` JSON output."""

    ok: bool
    errors: list[str]
    checks: list[ValidationCheck]


class SignResult(TypedDict, total=False):
    """Mirrors the Go binary's `sign` JSON output."""

    ok: bool
    sig_path: str
    error: str


class VerifyResult(TypedDict, total=False):
    """Mirrors the Go binary's `verify` JSON output."""

    ok: bool
    valid: bool
    error: str


def _cache_dir() -> Path:
    return Path.home() / ".sdd" / "bin"


def _asset_platform() -> tuple[str, str, str]:
    """Return (goos, goarch, ext) for the current platform, matching release asset names."""
    system = platform.system().lower()
    goos = {"linux": "linux", "darwin": "darwin", "windows": "windows"}.get(system)
    if goos is None:
        raise CompilerRunnerError(
            f"Unsupported platform for sdd-compile download: {system}"
        )

    machine = platform.machine().lower()
    goarch = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine)
    if goarch is None:
        raise CompilerRunnerError(
            f"Unsupported architecture for sdd-compile download: {machine}"
        )

    ext = ".exe" if goos == "windows" else ""
    return goos, goarch, ext


def _installed_cli_version() -> str:
    try:
        return _pkg_version("sdd-cli")
    except PackageNotFoundError as exc:
        raise CompilerRunnerError(
            "Cannot determine sdd-cli version to download a matching sdd-compile binary. "
            "Install sdd-cli via pip/uv or set SDD_COMPILE_BIN to a local binary."
        ) from exc


def _debug_downloads_enabled() -> bool:
    return os.environ.get("SDD_COMPILE_DEBUG_DOWNLOADS", "").strip().lower() not in (
        "",
        "0",
        "false",
    )


def _debug_log(message: str) -> None:
    if _debug_downloads_enabled():
        sys.stderr.write(f"[sdd-compile download] {message}\n")


def _download(url: str) -> bytes | None:
    if not url.startswith("https://github.com/"):
        raise CompilerRunnerError(
            f"Refusing to fetch sdd-compile from non-GitHub URL: {url}"
        )
    _debug_log(f"GET {url}")
    try:
        with urllib.request.urlopen(  # nosec B310 -- scheme/host pinned to https://github.com/ above.
            url, timeout=_DOWNLOAD_TIMEOUT_SECONDS
        ) as response:
            payload = cast(bytes, response.read())
            _debug_log(f"200 {url} ({len(payload)} bytes)")
            return payload
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            _debug_log(f"404 {url}")
            return None
        _debug_log(f"error {url}: {exc}")
        raise CompilerRunnerError(
            f"Failed to download sdd-compile from {url}: {exc}"
        ) from exc
    except urllib.error.URLError as exc:
        _debug_log(f"error {url}: {exc}")
        raise CompilerRunnerError(
            f"Failed to download sdd-compile from {url}: {exc}"
        ) from exc


def _fetch_release_binary(version: str, asset_name: str) -> tuple[bytes, str]:
    """Fetch the asset bytes and its expected sha256 for a given release version.

    Tries both the lowercase-v and uppercase-V tag conventions used by this
    project's release workflow.
    """
    for tag in (f"v{version}", f"V{version}"):
        base = f"https://github.com/{_RELEASE_REPO}/releases/download/{tag}"
        payload = _download(f"{base}/{asset_name}")
        if payload is None:
            continue
        checksums = _download(f"{base}/SHA256SUMS")
        if checksums is None:
            raise CompilerRunnerError(
                f"sdd-compile release asset found for tag {tag} but SHA256SUMS is missing; "
                "refusing to use an unverified binary."
            )
        expected = None
        for line in checksums.decode("utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == asset_name:
                expected = parts[0]
                break
        if expected is None:
            raise CompilerRunnerError(
                f"SHA256SUMS for tag {tag} does not list {asset_name}; "
                "refusing to use an unverified binary."
            )
        return payload, expected

    raise CompilerRunnerError(
        f"No sdd-compile release binary found for version {version} "
        f"(asset {asset_name}; tried tags v{version} and V{version}). "
        "Standalone installs need a release asset matching the installed "
        "sdd-cli version, or a local binary provided via SDD_COMPILE_BIN."
    )


def _download_and_cache_binary(version: str) -> Path:
    goos, goarch, ext = _asset_platform()
    asset_name = f"sdd-compile-{goos}-{goarch}{ext}"
    cached_path = _cache_dir() / version / asset_name
    if cached_path.exists():
        return cached_path

    payload, expected_sha256 = _fetch_release_binary(version, asset_name)
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise CompilerRunnerError(
            f"sdd-compile download checksum mismatch for {asset_name} "
            f"(expected {expected_sha256}, got {actual_sha256})"
        )

    cached_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cached_path.with_suffix(cached_path.suffix + ".tmp")
    tmp_path.write_bytes(payload)
    if goos != "windows":
        tmp_path.chmod(
            tmp_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    tmp_path.replace(cached_path)
    return cached_path


def _locate_binary(repo_root: Path | None = None) -> Path:
    """Locate the sdd-compile binary.

    Resolution order:
    1. SDD_COMPILE_BIN environment variable
    2. <repo_root>/tools/sdd-compile/bin/sdd-compile (built by `make build-compiler`)
    3. `sdd-compile` on PATH
    4. Cached/downloaded release binary matching the installed sdd-cli version
       (skipped when SDD_COMPILE_NO_DOWNLOAD is set)
    """
    env_override = os.environ.get("SDD_COMPILE_BIN", "").strip()
    if env_override:
        path = Path(env_override)
        if path.exists():
            return path
        raise CompilerRunnerError(
            f"SDD_COMPILE_BIN is set but does not exist: {env_override}"
        )

    root = repo_root or _try_detect_repo_root()
    if root is not None:
        binary_name = (
            "sdd-compile.exe" if platform.system() == "Windows" else "sdd-compile"
        )
        built_path = root / "tools" / "sdd-compile" / "bin" / binary_name
        if built_path.exists():
            return built_path

    on_path = shutil.which("sdd-compile")
    if on_path:
        return Path(on_path)

    if not os.environ.get("SDD_COMPILE_NO_DOWNLOAD", "").strip():
        version = _installed_cli_version()
        return _download_and_cache_binary(version)

    raise CompilerRunnerError(
        "sdd-compile binary not found. Build it with 'make build-compiler', "
        "set SDD_COMPILE_BIN to its path, or unset SDD_COMPILE_NO_DOWNLOAD to "
        "allow fetching the matching release binary."
    )


def _try_detect_repo_root() -> Path | None:
    try:
        return detect_repo_root()
    except RuntimeError:
        return None


class CompilerRunner:
    """Invokes the Go sdd-compile binary and parses its JSON output."""

    def __init__(
        self,
        repo_root: str | Path | None = None,
        runner: SafeProcessRunner | None = None,
    ) -> None:
        self.repo_root = (
            Path(repo_root).resolve() if repo_root else _try_detect_repo_root()
        )
        self._binary = _locate_binary(self.repo_root)
        self._runner = runner or SafeProcessRunner()

    def version(self) -> str:
        """Return the sdd-compile binary version string."""
        result = self._runner.run([str(self._binary), "version"])
        if not result.success:
            raise CompilerRunnerError(f"sdd-compile version failed: {result.stderr}")
        return result.stdout.strip()

    def compile(
        self, input_dir: str | Path, output_dir: str | Path
    ) -> CompilationResult:
        """Compile governance JSON to msgpack artifacts via the Go binary."""
        result = self._runner.run(
            [
                str(self._binary),
                "compile",
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
            ]
        )
        payload = self._parse_json(result.stdout, context="compile")
        if not result.success or not payload.get("ok", False):
            error = payload.get("error") or result.stderr.strip() or "compile failed"
            raise CompilerRunnerError(f"sdd-compile compile failed: {error}")
        return payload  # type: ignore[return-value]

    def validate_compilation_detailed(self, output_dir: str | Path) -> ValidationResult:
        """Validate compiled artifacts via the Go binary, returning structured diagnostics."""
        result = self._runner.run(
            [str(self._binary), "validate", "--dir", str(output_dir)]
        )
        payload = self._parse_json(result.stdout, context="validate")
        return payload  # type: ignore[return-value]

    def validate_compilation(self, output_dir: str | Path) -> bool:
        """Backward-compatible boolean validation entrypoint."""
        return self.validate_compilation_detailed(output_dir).get("ok", False)

    def sign(
        self,
        *,
        artifact_path: str | Path,
        key_path: str | Path,
        key_id: str,
        profile: str,
    ) -> SignResult:
        """Sign an artifact with a native Ed25519 key via the Go binary."""
        result = self._runner.run(
            [
                str(self._binary),
                "sign",
                "--artifact",
                str(artifact_path),
                "--key",
                str(key_path),
                "--key-id",
                key_id,
                "--profile",
                profile,
            ]
        )
        payload = self._parse_json(result.stdout, context="sign")
        if not payload.get("ok", False):
            error = payload.get("error") or result.stderr.strip() or "sign failed"
            raise CompilerRunnerError(f"sdd-compile sign failed: {error}")
        return payload  # type: ignore[return-value]

    def verify(
        self,
        *,
        public_key_pem: str,
        message: str,
        signature_b64: str,
    ) -> VerifyResult:
        """Verify an Ed25519 signature via the Go binary. Never raises for an
        invalid/malformed signature; returns valid=False instead."""
        request = json.dumps(
            {
                "public_key_pem": public_key_pem,
                "message": message,
                "signature_b64": signature_b64,
            }
        )
        result = self._runner.run([str(self._binary), "verify"], input_data=request)
        try:
            payload = self._parse_json(result.stdout, context="verify")
        except CompilerRunnerError as exc:
            return {
                "ok": False,
                "valid": False,
                "error": result.stderr.strip() or str(exc),
            }
        return payload  # type: ignore[return-value]

    @staticmethod
    def _parse_json(stdout: str, *, context: str) -> dict[str, Any]:
        text = stdout.strip()
        if not text:
            raise CompilerRunnerError(f"sdd-compile {context} produced no output")
        try:
            return cast(dict[str, Any], json.loads(text))
        except json.JSONDecodeError as exc:
            raise CompilerRunnerError(
                f"sdd-compile {context} produced invalid JSON: {exc}"
            ) from exc
