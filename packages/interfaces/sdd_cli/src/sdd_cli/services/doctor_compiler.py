"""Read-only compiler toolchain diagnostics for `sdd doctor compiler`.

Builds a stable JSON-serializable report about the sdd-compile binary: how it
was resolved, its version, the CLI<->binary handshake state, the download
cache, the packaged native assets, and a dry validation of compiled artifacts.
Every probe is best-effort — failures are reported as strings inside the
report, never raised, so the doctor can always print a full picture.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any

REPORT_SCHEMA_VERSION = "1.0"


def _probe_cli_version() -> tuple[str | None, str | None]:
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("sdd-cli"), None
    except Exception as exc:
        return None, str(exc)


def _probe_cache(cache_dir: Path) -> dict[str, Any]:
    if not cache_dir.exists():
        return {"dir": str(cache_dir), "entries": []}
    entries = sorted(
        str(path.relative_to(cache_dir))
        for path in cache_dir.rglob("*")
        if path.is_file()
    )
    return {"dir": str(cache_dir), "entries": entries}


def _probe_packaged_native() -> dict[str, Any]:
    try:
        native = resources.files("sdd_core") / "_native"
        if not native.is_dir():
            return {"present": False, "assets": []}
        assets = sorted(entry.name for entry in native.iterdir() if entry.is_file())
        return {"present": bool(assets), "assets": assets}
    except Exception as exc:
        return {"present": False, "assets": [], "error": str(exc)}


def _probe_validate(runner: Any, workspace_root: Path) -> dict[str, Any]:
    compiled_dir = workspace_root / ".sdd" / "compiled"
    if not compiled_dir.exists():
        return {"ran": False, "compiled_dir": str(compiled_dir)}
    try:
        result = runner.validate_compilation_detailed(str(compiled_dir))
        return {
            "ran": True,
            "compiled_dir": str(compiled_dir),
            "ok": result.get("ok", False),
            "errors": result.get("errors", []),
        }
    except Exception as exc:
        return {"ran": True, "compiled_dir": str(compiled_dir), "error": str(exc)}


def build_compiler_report(workspace_root: Path | None = None) -> dict[str, Any]:
    """Build the full read-only compiler diagnostics report."""
    from sdd_core.utils.compiler_runner import CompilerRunner, _cache_dir

    cli_version, cli_error = _probe_cli_version()
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "cli_version": cli_version,
        "binary": {},
        "handshake": {},
        "cache": _probe_cache(_cache_dir()),
        "packaged_native": _probe_packaged_native(),
        "validate": {"ran": False},
    }
    if cli_error:
        report["cli_version_error"] = cli_error

    try:
        runner = CompilerRunner()
    except Exception as exc:
        report["binary"] = {"resolved": False, "error": str(exc)}
        report["handshake"] = {"status": "unavailable"}
        return report

    report["binary"] = {
        "resolved": True,
        "path": str(runner._binary),
        "resolution_rule": runner.resolution_rule,
    }
    try:
        report["binary"]["version"] = runner.version()
    except Exception as exc:
        report["binary"]["version_error"] = str(exc)

    try:
        report["handshake"] = dict(runner.verify_version_handshake())
    except Exception as exc:
        report["handshake"] = {"status": "skew", "error": str(exc)}

    root = workspace_root or Path.cwd()
    report["validate"] = _probe_validate(runner, root)
    return report
