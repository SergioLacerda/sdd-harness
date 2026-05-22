"""sdd runtime — workspace runtime state commands."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import typer

from sdd_cli.shared.contracts import (
    build_error_result,
    build_ok_result,
)
from sdd_cli.utils.output import emit_json, is_json_mode, is_verbose_mode
from sdd_cli.utils.sdd_authority import (
    compiled_active_dir,
    enforce_path_policy,
    profile_active_path,
    resolve_workspace_root,
)
from sdd_cli.utils.telemetry_paths import resolve_compliance_events_path

logger = logging.getLogger(__name__)

app = typer.Typer()

# Canonical project-scoped paths (§4 Phase 1 — §15.2 Phase 2).
_RUNTIME_DIR = Path(".sdd") / "runtime"
_EVENTS_FILENAME = "compliance-events.jsonl"


@app.callback()
def _() -> None:
    """Workspace runtime operations."""


@app.command()
def status(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full layer-by-layer breakdown."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip cache and run fresh validation."
    ),
) -> None:
    """Show current workspace governance state (AHP + GAP + runtime drift)."""

    try:
        from sdd_runtime import format_governance_footer

        from sdd_core.governance.handshake import AgentHandshakeProtocol
    except ImportError as exc:
        typer.echo(f"ERROR: sdd_core not installed — {exc}", err=True)
        raise typer.Exit(2) from exc

    root = resolve_workspace_root()
    root = enforce_path_policy(root, workspace_root=root, mode="normal")

    effective_verbose = bool(verbose or is_verbose_mode(ctx))
    output_json = is_json_mode(ctx)

    output_mode: Literal["silent", "compact", "verbose"] = (
        "verbose" if effective_verbose else "compact"
    )
    ahp = AgentHandshakeProtocol(project_root=root)
    state, report = ahp.validate(output_mode=output_mode, force_recheck=force)

    if not output_json:
        typer.echo(ahp.format_combined_output(state, report, mode=output_mode))

    _EXIT_CODES = {
        "HEALTHY": 0,
        "PARTIAL": 0,
        "NOT_INITIALIZED": 1,
        "MISCONFIGURED": 2,
        "NOT_CONNECTED": 3,
    }
    code = _EXIT_CODES.get(state, 1)

    # ── sdd_runtime: drift detection + session upsert + telemetry ──────────
    workspace_profile = _read_profile(root)
    current_profile = workspace_profile
    if isinstance(ctx.obj, dict):
        current_profile = str(
            ctx.obj.get("profile", workspace_profile) or workspace_profile
        )

    drift_info = _emit_runtime_status(
        root=root,
        ahp_state=state,
        workspace_profile=workspace_profile,
        current_profile=current_profile,
    )

    # D3: show ask_confidence block if last_ask is present
    ask_confidence = _show_ask_confidence(root, emit=not output_json)
    governance_footer = format_governance_footer(
        drift=_footer_drift_status(drift_info),
        governance=state.lower(),
        profile=ahp.skill_profile,
    )

    if output_json:
        data = {
            "state": state,
            "exit_code": code,
            "report": _normalize_report(report),
            "drift": drift_info,
            "ask_confidence": ask_confidence,
            "governance_footer": governance_footer,
        }
        if code == 0:
            payload = build_ok_result("runtime status", data)
        else:
            payload = build_error_result(
                "runtime status",
                data,
                code="runtime_state_not_healthy",
                message=f"runtime status returned non-success state '{state}'",
            )
        emit_json(payload, err=code != 0)
    else:
        typer.echo(governance_footer)

    if code != 0:
        raise typer.Exit(code)


def _footer_drift_status(drift_info: dict[str, Any]) -> str:
    """Map runtime drift payload to canonical compact footer drift status."""
    drift_type = str(drift_info.get("type", "none")).strip().lower() or "none"
    if bool(drift_info.get("detected")):
        return drift_type
    return "none"


# ---------------------------------------------------------------------------
# sdd_runtime integration helpers
# ---------------------------------------------------------------------------


def _emit_runtime_status(
    *,
    root: Path,
    ahp_state: str,
    workspace_profile: str,
    current_profile: str,
) -> dict[str, Any]:
    """Load compiled artifact, classify drift, upsert session, emit telemetry.

    All sdd_runtime calls are best-effort — a failure here must never crash
    the status command.
    """
    import os
    import uuid

    drift_info: dict[str, Any] = {"detected": False, "type": "none", "reason": ""}

    try:
        from sdd_runtime import (
            CompiledArtifact,
            DriftDetector,
            GovernanceInjector,
            RuntimeEvent,
            SessionManager,
            SessionState,
            TelemetrySink,
        )
    except ImportError as exc:
        typer.echo(f"ERROR: sdd_runtime not installed — {exc}", err=True)
        raise typer.Exit(2) from exc

    try:
        agent_id = os.environ.get("SDD_AGENT_ID", "unknown")
        workspace_id = _read_workspace_id(root)
        trace_id = str(uuid.uuid4())
        runtime_dir = root / _RUNTIME_DIR

        # ── 1. Load compiled artifact ──────────────────────────────────────
        compiled_dir = compiled_active_dir(root)
        if not compiled_dir.exists():
            raise FileNotFoundError(
                f"compiled governance not found at '{compiled_dir}'"
            )

        injection = GovernanceInjector().inject_from_path(compiled_dir)
        has_artifact = injection.loaded
        artifact: CompiledArtifact | None = None
        if has_artifact:
            # We want to fail hard if artifact parsing fails, no more silent except
            artifact = CompiledArtifact.from_sdd_compiled_dir(
                compiled_dir, profile=workspace_profile
            )

        # ── 2. Upsert session at canonical path (GAP 4) ───────────────────
        session_manager = SessionManager(state_dir=runtime_dir)
        session = SessionState(
            workspace_id=workspace_id,
            agent_id=agent_id,
            work_item_id="runtime-status",
            artifact_fingerprint=injection.artifact_fingerprint,
            schema_version=injection.schema_version,
            policy_set_version=injection.schema_version,
        )
        session_manager.upsert(session)

        # ── 3. Classify drift ──────────────────────────────────────────────
        drift_type = "none"
        drift_detected = False
        if artifact is not None:
            drift_report = DriftDetector().classify(
                session=session,
                artifact=artifact,
                current_profile=current_profile,
            )
            drift_detected = drift_report.drift_detected
            drift_type = drift_report.drift_type
            if drift_detected:
                drift_info = {
                    "detected": True,
                    "type": drift_type,
                    "remediation_command": drift_report.remediation_command,
                }
                typer.echo(
                    f"\n[runtime] drift detected: {drift_type}"
                    f"  →  {drift_report.remediation_command}",
                    err=False,
                )
            else:
                drift_info = {"detected": False, "type": drift_type, "reason": ""}

        # ── 4. Emit RuntimeEvent to canonical JSONL sink ───────────────────
        sink = TelemetrySink(
            jsonl_path=resolve_compliance_events_path(workspace_root=root),
            logging_mode="passive",
        )
        sink.emit(
            RuntimeEvent(
                event="runtime.session.start",
                command="runtime status",
                status="ok" if ahp_state in ("HEALTHY", "PARTIAL") else "warn",
                trace_id=trace_id,
                workspace_id=workspace_id,
                agent_id=agent_id,
                artifact_fingerprint=injection.artifact_fingerprint,
                schema_version=injection.schema_version,
                decision_source_refs=["ADR-001-runtime-authority-boundary"],
                path_id=os.environ.get("SDD_PATH_ID", ""),
                details={
                    "ahp_state": ahp_state,
                    "mandates_loaded": injection.mandates_loaded,
                    "drift_detected": drift_detected,
                    "drift_type": drift_type,
                },
            )
        )
        if drift_detected:
            sink.emit(
                RuntimeEvent(
                    event="runtime.drift.detected",
                    command="runtime status",
                    status="warn",
                    trace_id=trace_id,
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    artifact_fingerprint=injection.artifact_fingerprint,
                    schema_version=injection.schema_version,
                    decision_source_refs=[
                        "§12.5-anti-drift-strategy",
                        "ADR-001-runtime-authority-boundary",
                    ],
                    details={"drift_type": drift_type},
                )
            )

    except FileNotFoundError as exc:
        # Compiled governance not yet generated — workspace not initialised.
        # This is an expected state (NOT_CONNECTED), not an error.
        logger.debug("sdd_runtime: compiled artifact not found — %s", exc)

    except Exception as exc:  # noqa: BLE001
        # Best-effort contract: operational telemetry failures must never crash
        # the status command. Log at debug level; the AHP state already
        # captured above is the authoritative exit code.
        logger.debug("sdd_runtime: non-critical failure in status emit — %s", exc)

    return drift_info


def _read_workspace_id(root: Path) -> str:
    """Extract workspace_id from .sdd/profile, best-effort."""
    import configparser

    profile_path = profile_active_path(root)
    if not profile_path.exists():
        return "unknown"
    try:
        parser = configparser.ConfigParser()
        parser.read(profile_path)
        return parser.get("sdd", "workspace_id", fallback="unknown")
    except Exception:
        return "unknown"


def _read_profile(root: Path) -> str:
    """Extract profile type from .sdd/profile, best-effort."""
    import configparser

    profile_path = profile_active_path(root)
    if not profile_path.exists():
        return ""
    try:
        parser = configparser.ConfigParser()
        parser.read(profile_path)
        return parser.get("sdd", "type", fallback="")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _show_ask_confidence(
    workspace_root: Path, *, emit: bool = True
) -> dict[str, Any] | None:
    """Display ask_confidence block derived from last_ask in governance-state.json."""
    import json

    state_path = Path(workspace_root) / ".sdd" / "runtime" / "governance-state.json"
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    last_ask = data.get("last_ask")
    if not last_ask:
        return None

    payload = {
        "last_ask_ts": last_ask.get("ts", "n/a"),
        "context_source": last_ask.get("context_source", "n/a"),
        "fingerprint_used": last_ask.get("compiled_fingerprint_used", "n/a"),
    }

    trace_id = last_ask.get("trace_id")
    if trace_id:
        payload["trace_id"] = trace_id[:8]

    if emit:
        typer.echo("")
        typer.echo("=== ask_confidence ===")
        typer.echo(f"  last_ask_ts        : {payload['last_ask_ts']}")
        typer.echo(f"  context_source     : {payload['context_source']}")
        typer.echo(f"  fingerprint_used   : {payload['fingerprint_used']}")
        if "trace_id" in payload:
            typer.echo(f"  trace_id           : {payload['trace_id']}")
    return payload


def _normalize_report(report: Any) -> dict[str, Any]:
    """Best-effort conversion of handshake report object to JSON-safe dict."""
    data = dict(report.__dict__) if hasattr(report, "__dict__") else {}
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str | int | float | bool | list | dict) or value is None:
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized
