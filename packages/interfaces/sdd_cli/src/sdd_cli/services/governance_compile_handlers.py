"""Compile-phase governance handlers."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from sdd_cli.services._governance_compile_support import (
    compliance_components,
    maybe_load_artifact_fingerprint,
    regenerate_seeds_flow,
    resolve_output_base_path,
    run_compile_flow,
)
from sdd_cli.utils.sdd_authority import compiled_active_dir, resolve_workspace_root

logger = logging.getLogger(__name__)


def compute_compliance_score(
    *, compile_ok: bool, consistency_ok: bool, drift_detected: bool
) -> tuple[int, dict[str, bool]]:
    """Compute the governance compliance score and its components."""
    return compliance_components(
        compile_ok=compile_ok,
        consistency_ok=consistency_ok,
        drift_detected=drift_detected,
    )


def resolve_output_base(output_dir: Path) -> Path:
    """Resolve the base output directory for compiled governance artifacts."""
    return resolve_output_base_path(
        output_dir,
        override=os.environ.get("SDD_TEST_OUTPUT_DIR", "").strip(),
        resolve_workspace_root_fn=resolve_workspace_root,
    )


def run_compilation(
    profile: str | None = None, *, console: Console | None = None
) -> Any:
    """Run GovernanceOrchestrator full pipeline. Raises typer.Exit(1) on failure."""
    if console is None:
        console = Console()
    from sdd_core.governance_orchestrator import GovernanceOrchestrator, PipelineResult

    orchestrator = GovernanceOrchestrator(profile=profile)
    result: PipelineResult = orchestrator.run_full_pipeline()
    if not result or not result.get("full_pipeline_success"):
        console.print("[red]ERROR: governance compilation failed[/red]")
        console.print(
            "  Next: check .sdd/source artifacts or run 'sdd governance validate'"
        )
        raise typer.Exit(1)
    return result


def update_profile_hash(
    core_fingerprint: str, *, console: Console | None = None
) -> None:
    """Update the `.sdd/profile` core_hash with the given fingerprint."""
    if console is None:
        console = Console()
    if not core_fingerprint:
        return
    try:
        import configparser

        ws_root = resolve_workspace_root()
        core_fingerprint = maybe_load_artifact_fingerprint(
            core_fingerprint,
            workspace_root=ws_root,
            compiled_active_dir_fn=compiled_active_dir,
        )

        profile_path = ws_root / ".sdd" / "profile"
        if profile_path.exists():
            parser = configparser.ConfigParser()
            parser.read(profile_path)
            if "sdd" in parser:
                parser["sdd"]["core_hash"] = core_fingerprint[:16]
                with open(profile_path, "w", encoding="utf-8") as f:
                    parser.write(f)
                console.print(
                    f"[cyan]core_hash updated in .sdd/profile ({core_fingerprint[:16]})[/cyan]"
                )
    except Exception as _e:
        console.print(
            f"[yellow]WARN: could not update core_hash in .sdd/profile: {_e}[/yellow]"
        )


def emit_compile_telemetry(
    *,
    core_fingerprint: str,
    is_error: bool,
    consistency_ok: bool,
    profile: str | None,
) -> None:
    """Emit telemetry events for a governance compile run."""
    try:
        import uuid

        from sdd_runtime.telemetry import RuntimeEvent, TelemetrySink

        from sdd_cli.utils.telemetry_paths import resolve_compliance_events_path
        from sdd_core.utils.environment import find_workspace_root as _fws

        _ws = _fws()
        _events_path = (
            resolve_compliance_events_path(workspace_root=_ws)
            if _ws
            else resolve_compliance_events_path()
        )
        _trace_id = str(uuid.uuid4())
        sink = TelemetrySink(jsonl_path=_events_path, logging_mode="active")
        sink.emit(
            RuntimeEvent(
                event="governance.compile.complete",
                command="governance compile",
                status="ok",
                trace_id=_trace_id,
                details={
                    "core_hash": core_fingerprint[:16] if core_fingerprint else ""
                },
            )
        )

        _score, _components = compute_compliance_score(
            compile_ok=not is_error,
            consistency_ok=consistency_ok,
            drift_detected=not consistency_ok,
        )
        _score_status = "ok" if _score >= 75 else ("warn" if _score >= 50 else "fail")
        sink.emit(
            RuntimeEvent(
                event="governance.compliance.score",
                command="governance compile",
                status=_score_status,
                trace_id=_trace_id,
                details={
                    "score": _score,
                    "components": _components,
                    "profile": profile or "client",
                },
            )
        )
        sink.flush()
    except Exception as _event_err:
        logger.debug("Failed to append governance compile event: %s", _event_err)


def regenerate_seeds(*, console: Console | None = None) -> None:
    """Regenerate agent seed files from the current governance config."""
    if console is None:
        console = Console()
    from sdd_cli.generators.agent_seeds import generate_agent_instruction_files
    from sdd_cli.utils.loader import load_governance_config, validate_governance_path

    try:
        regenerate_seeds_flow(
            console=console,
            resolve_workspace_root_fn=resolve_workspace_root,
            validate_governance_path_fn=validate_governance_path,
            load_governance_config_fn=load_governance_config,
            resolve_output_base_fn=resolve_output_base,
            generate_agent_instruction_files_fn=generate_agent_instruction_files,
        )
    except Exception as _gen_err:
        console.print(
            f"[yellow]WARN: could not auto-regenerate agent files: {_gen_err}[/yellow]"
        )


def run_compile(
    *, profile: str | None, output_json: bool, console: Console | None = None
) -> None:
    """Run the `sdd governance compile` command flow."""
    if console is None:
        console = Console()
    from rich.panel import Panel

    from sdd_cli.services.governance_artifact_handlers import (
        check_artifact_consistency,
        run_governance_compile_json,
    )
    from sdd_cli.services.governance_command_output import handle_compile_output
    from sdd_cli.utils.sdd_authority import resolve_workspace_root

    run_compile_flow(
        profile=profile,
        output_json=output_json,
        console=console,
        panel_cls=Panel,
        run_compilation_fn=run_compilation,
        update_profile_hash_fn=update_profile_hash,
        resolve_workspace_root_fn=resolve_workspace_root,
        check_artifact_consistency_fn=check_artifact_consistency,
        run_governance_compile_json_fn=run_governance_compile_json,
        handle_compile_output_fn=handle_compile_output,
        emit_compile_telemetry_fn=emit_compile_telemetry,
        regenerate_seeds_fn=regenerate_seeds,
    )
