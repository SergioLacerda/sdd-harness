"""SafeProcessRunner: governed subprocess execution with telemetry."""

from __future__ import annotations

import logging
import subprocess  # nosec B404
import time
from pathlib import Path
from typing import Any

from sdd_core.utils._process_auth import AUTHORIZED_BINARIES, ProcessAuthorizer
from sdd_core.utils._process_types import (
    ProcessAuthorizationError,
    ProcessNonZeroExitError,
    ProcessResult,
    ProcessRunnerError,
    ProcessSpawnError,
    ProcessTimeoutError,
    _coerce_output,
)

logger = logging.getLogger(__name__)


class SafeProcessRunner:
    """
    Governed wrapper for external process execution.

    Enforces:
    - shell=False
    - Binary allow-listing (via ProcessAuthorizer)
    - Automatic telemetry (via provided sink)
    """

    def __init__(
        self,
        authorized_binaries: set[str] | frozenset[str] | None = None,
        telemetry_sink: Any | None = None,
        authorizer: ProcessAuthorizer | None = None,
    ) -> None:
        self._authorizer = authorizer or ProcessAuthorizer(
            authorized_binaries
            if authorized_binaries is not None
            else AUTHORIZED_BINARIES
        )
        if telemetry_sink is not None:
            self._sink = telemetry_sink
        else:
            # Lazy default: wire a TelemetrySink automatically when available.
            # Uses a lazy import to avoid circular dependency (sdd_core ← sdd_runtime).
            try:
                from sdd_runtime.telemetry import TelemetrySink

                self._sink = TelemetrySink()
            except Exception:  # nosec B110 — optional dependency, graceful fallback
                self._sink = None

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | str | None = None,
        input_data: str | bytes | None = None,
        capture_output: bool = True,
        check: bool = False,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        """
        Execute a command securely.

        Args:
            args: Command arguments (first item must be the binary name/path)
            cwd: Working directory
            input_data: Data to send to stdin
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise an error on failure
            env: Environment variables
            timeout: Execution timeout in seconds

        Raises:
            ProcessAuthorizationError: If binary/arguments are not permitted.
            ProcessTimeoutError: If execution exceeds timeout.
            ProcessSpawnError: If process cannot be started.
            ProcessNonZeroExitError: If check=True and returncode != 0.
        """
        self._authorizer.validate_args(args)
        trace_id = self._new_trace_id()
        try:
            binary_name = self._authorizer.authorize(args)
        except ProcessAuthorizationError:
            self._emit_telemetry(
                "error",
                args,
                duration_ms=0,
                error_kind="auth",
                binary_name=self._authorizer.resolve_binary_name(args[0]),
                trace_id=trace_id,
            )
            raise

        started = time.perf_counter()
        self._emit_telemetry("start", args, binary_name=binary_name, trace_id=trace_id)

        try:
            proc = subprocess.run(  # nosec B603
                args,
                shell=False,
                cwd=cwd,
                input=input_data,
                capture_output=capture_output,
                check=False,
                env=env,
                timeout=timeout,
                text=isinstance(input_data, str) if input_data is not None else True,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)

            result = ProcessResult(
                command=args,
                returncode=proc.returncode,
                stdout=_coerce_output(proc.stdout),
                stderr=_coerce_output(proc.stderr),
                success=proc.returncode == 0,
                duration_ms=duration_ms,
                status="ok" if proc.returncode == 0 else "error",
                error_kind=None if proc.returncode == 0 else "non_zero",
            )

            self._emit_telemetry(
                "finish",
                args,
                result.returncode,
                duration_ms=duration_ms,
                error_kind=result.error_kind,
                binary_name=binary_name,
                trace_id=trace_id,
            )
            if check and not result.success:
                raise ProcessNonZeroExitError(
                    f"Command failed with exit code {result.returncode}: {' '.join(args)}"
                )
            return result

        except subprocess.TimeoutExpired as exc:
            logger.error("Process timeout: %s", " ".join(args))
            self._emit_telemetry(
                "timeout",
                args,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_kind="timeout",
                binary_name=binary_name,
                trace_id=trace_id,
            )
            raise ProcessTimeoutError(args, timeout) from exc
        except ProcessRunnerError:
            raise
        except Exception as exc:
            logger.error("Process execution error: %s", str(exc))
            self._emit_telemetry(
                "error",
                args,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_kind="spawn",
                binary_name=binary_name,
                trace_id=trace_id,
            )
            raise ProcessSpawnError(
                f"Could not execute process: {' '.join(args)} ({exc})"
            ) from exc

    def run_interactive(
        self,
        args: list[str],
        *,
        cwd: Path | str | None = None,
        stdin_text: str | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        """
        Execute a command interactively with Popen (for stdin/stdout interaction).

        This method is less safe than run() because it requires interaction.
        Use only when interactive input is necessary (e.g., wizards).

        Args:
            args: Command arguments (first item must be the binary name/path)
            cwd: Working directory
            stdin_text: Text to write to stdin (if provided, pipes are used)
            timeout: Execution timeout in seconds

        Returns:
            ProcessResult with interactive execution details.

        Raises:
            ProcessAuthorizationError: If binary/arguments are not permitted.
            ProcessTimeoutError: If timeout is exceeded.
            ProcessSpawnError: If process startup fails.
        """
        self._authorizer.validate_args(args)
        trace_id = self._new_trace_id()
        try:
            binary_name = self._authorizer.authorize(args)
        except ProcessAuthorizationError:
            self._emit_telemetry(
                "error",
                args,
                duration_ms=0,
                error_kind="auth",
                binary_name=self._authorizer.resolve_binary_name(args[0]),
                trace_id=trace_id,
            )
            raise

        started = time.perf_counter()
        self._emit_telemetry("start", args, binary_name=binary_name, trace_id=trace_id)
        proc: subprocess.Popen[str] | None = None

        try:
            # nosec B603 - Arguments validated against allow-list, shell is False
            proc = subprocess.Popen(  # nosec B603
                args,
                shell=False,
                cwd=cwd,
                stdin=subprocess.PIPE if stdin_text is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
            returncode = proc.returncode
            duration_ms = int((time.perf_counter() - started) * 1000)
            result = ProcessResult(
                command=args,
                returncode=returncode,
                stdout=stdout or "",
                stderr=stderr or "",
                success=returncode == 0,
                duration_ms=duration_ms,
                status="ok" if returncode == 0 else "error",
                error_kind=None if returncode == 0 else "non_zero",
            )

            self._emit_telemetry(
                "finish",
                args,
                returncode,
                duration_ms=duration_ms,
                error_kind=result.error_kind,
                binary_name=binary_name,
                trace_id=trace_id,
            )
            return result

        except subprocess.TimeoutExpired as exc:
            logger.error("Process timeout: %s", " ".join(args))
            if proc is not None:
                proc.kill()
            self._emit_telemetry(
                "timeout",
                args,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_kind="timeout",
                binary_name=binary_name,
                trace_id=trace_id,
            )
            raise ProcessTimeoutError(args, timeout) from exc
        except ProcessRunnerError:
            raise
        except Exception as exc:
            logger.error("Process execution error: %s", str(exc))
            self._emit_telemetry(
                "error",
                args,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_kind="spawn",
                binary_name=binary_name,
                trace_id=trace_id,
            )
            raise ProcessSpawnError(
                f"Could not execute interactive process: {' '.join(args)} ({exc})"
            ) from exc

    def _emit_telemetry(
        self,
        event_type: str,
        args: list[str],
        returncode: int | None = None,
        *,
        duration_ms: int | None = None,
        error_kind: str | None = None,
        binary_name: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        if not self._sink:
            return

        try:
            from sdd_runtime.telemetry import RuntimeEvent

            event_name = (
                "governance.process.run"
                if event_type == "finish"
                else f"governance.process.{event_type}"
            )
            status = self._normalize_status(
                event_type=event_type, returncode=returncode, error_kind=error_kind
            )

            self._sink.emit(
                RuntimeEvent(
                    event=event_name,
                    command=" ".join(args),
                    status=status,
                    trace_id=trace_id or self._new_trace_id(),
                    duration_ms=duration_ms,
                    details={
                        "binary": binary_name
                        or self._authorizer.resolve_binary_name(args[0]),
                        "arg_count": len(args) - 1,
                        "returncode": returncode,
                        "error_kind": error_kind,
                    },
                )
            )
        except Exception:  # nosec B110 — telemetry emission is best-effort, non-critical
            pass

    def _new_trace_id(self) -> str:
        import uuid

        return str(uuid.uuid4())

    def _normalize_status(
        self, *, event_type: str, returncode: int | None, error_kind: str | None
    ) -> str:
        if event_type == "timeout" or error_kind == "timeout":
            return "timeout"
        if error_kind == "auth":
            return "blocked"
        if event_type == "error":
            return "error"
        if event_type in {"start", "finish"} and returncode in (None, 0):
            return "ok"
        if returncode is not None and returncode != 0:
            return "error"
        return "error"
