"""Compile-phase governance handlers (run_compilation, update_profile_hash, regenerate_seeds)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from sdd_cli.utils.sdd_authority import compiled_active_dir, resolve_workspace_root

logger = logging.getLogger(__name__)


def compute_compliance_score(
    *,
    compile_ok: bool,
    consistency_ok: bool,
    drift_detected: bool,
) -> tuple[int, dict[str, bool]]:
    """Compute governance compliance score (0-100, 25 pts per passing component).

    Components:
      governance_compile -- compilation succeeded without errors
      consistency        -- artifact consistency check passed
      drift_detected     -- no drift detected (True = 25 pts, False = 0 pts)
      lint_gate          -- placeholder; always True here (enforced pre-commit)

    Returns (score, components_dict).
    """
    components = {
        "governance_compile": compile_ok,
        "consistency": consistency_ok,
        "drift_detected": not drift_detected,
        "lint_gate": True,
    }
    score = sum(25 for v in components.values() if v)
    return score, components


def resolve_output_base(output_dir: Path) -> Path:
    """Resolve output base, isolating writes in tests when targeting workspace root."""
    output = output_dir.resolve()
    override = os.environ.get("SDD_TEST_OUTPUT_DIR", "").strip()
    if not override:
        return output
    try:
        ws = resolve_workspace_root()
    except Exception:
        ws = None
    if ws is not None and output == ws.resolve():
        redirected = Path(override).resolve()
        redirected.mkdir(parents=True, exist_ok=True)
        return redirected
    return output


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
    """Persist core_hash into .sdd/profile for AHP Layer 2 verification (C5)."""
    if console is None:
        console = Console()
    if not core_fingerprint:
        return
    try:
        import configparser
        import json as _json

        ws_root = resolve_workspace_root()
        artifact_candidates = [compiled_active_dir(ws_root) / "governance-core.json"]
        art_path = next((p for p in artifact_candidates if p.exists()), None)
        if art_path is not None:
            try:
                artifact_fp = str(
                    _json.loads(art_path.read_text(encoding="utf-8")).get(
                        "fingerprint", ""
                    )
                ).strip()
                if artifact_fp:
                    core_fingerprint = artifact_fp
            except Exception as _artifact_err:
                logger.debug(
                    "Failed to read artifact fingerprint from %s: %s",
                    art_path,
                    _artifact_err,
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
    """Emit compile.complete and compliance.score events to telemetry sink."""
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
    """Auto-regenerate agent instruction files after successful compile (B6)."""
    if console is None:
        console = Console()
    from sdd_cli.generators.agent_seeds import generate_agent_instruction_files
    from sdd_cli.utils.loader import load_governance_config, validate_governance_path

    if os.environ.get("SDD_SKIP_SEED_REGEN") == "1":
        return
    try:
        _ws = resolve_workspace_root()
        if _ws is not None:
            _gen_path = str(_ws / ".sdd" / "compiled")
            _gen_config = (
                load_governance_config(_gen_path)
                if validate_governance_path(_gen_path)
                else {}
            )
            _output_base = resolve_output_base(_ws)
            generate_agent_instruction_files(_output_base, _gen_config)
            console.print("[cyan]Agent instruction files regenerated[/cyan]")
            try:
                from sdd_wizard.contracts import (
                    generate_agent_instructions_from_config,
                )

                generate_agent_instructions_from_config(_output_base, _gen_config)
                console.print("[cyan].sdd/agent-instructions.md regenerated[/cyan]")
            except ImportError:
                console.print(
                    "[yellow]WARN: sdd_wizard not available, skipping agent-instructions.md regeneration[/yellow]"
                )
    except Exception as _gen_err:
        console.print(
            f"[yellow]WARN: could not auto-regenerate agent files: {_gen_err}[/yellow]"
        )
