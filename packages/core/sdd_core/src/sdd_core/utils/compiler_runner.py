"""CompilerRunner: Python bridge to the Go `sdd-compile` binary.

This is the only Python-facing entrypoint for invoking governance
compilation. It replaces direct imports of `sdd_compiler.governance_compiler`
with subprocess calls to the Go binary, parsing its JSON stdout output.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, TypedDict, cast

from sdd_core.utils.environment import detect_repo_root
from sdd_core.utils.process import SafeProcessRunner

__all__ = [
    "CompilationResult",
    "CompilerRunner",
    "CompilerRunnerError",
    "ValidationCheck",
    "ValidationResult",
]


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


def _locate_binary(repo_root: Path | None = None) -> Path:
    """Locate the sdd-compile binary.

    Resolution order:
    1. SDD_COMPILE_BIN environment variable
    2. <repo_root>/tools/sdd-compile/bin/sdd-compile (built by `make build-compiler`)
    3. `sdd-compile` on PATH
    """
    env_override = os.environ.get("SDD_COMPILE_BIN", "").strip()
    if env_override:
        path = Path(env_override)
        if path.exists():
            return path
        raise CompilerRunnerError(
            f"SDD_COMPILE_BIN is set but does not exist: {env_override}"
        )

    root = repo_root or detect_repo_root()
    built_path = root / "tools" / "sdd-compile" / "bin" / "sdd-compile"
    if built_path.exists():
        return built_path

    on_path = shutil.which("sdd-compile")
    if on_path:
        return Path(on_path)

    raise CompilerRunnerError(
        "sdd-compile binary not found. Build it with 'make build-compiler' "
        "or set SDD_COMPILE_BIN to its path."
    )


class CompilerRunner:
    """Invokes the Go sdd-compile binary and parses its JSON output."""

    def __init__(
        self,
        repo_root: str | Path | None = None,
        runner: SafeProcessRunner | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else detect_repo_root()
        self._binary = _locate_binary(self.repo_root)
        self._runner = runner or SafeProcessRunner()

    def version(self) -> str:
        """Return the sdd-compile binary version string."""
        result = self._runner.run([str(self._binary), "version"])
        if not result.success:
            raise CompilerRunnerError(f"sdd-compile version failed: {result.stderr}")
        return result.stdout.strip()

    def compile(self, input_dir: str | Path, output_dir: str | Path) -> CompilationResult:
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
