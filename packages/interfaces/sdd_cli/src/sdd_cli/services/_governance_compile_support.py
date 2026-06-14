from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def compliance_components(
    *, compile_ok: bool, consistency_ok: bool, drift_detected: bool
) -> tuple[int, dict[str, bool]]:
    components = {
        "governance_compile": compile_ok,
        "consistency": consistency_ok,
        "drift_detected": not drift_detected,
        "lint_gate": True,
    }
    return sum(25 for value in components.values() if value), components


def resolve_output_base_path(
    output_dir: Path,
    *,
    override: str,
    resolve_workspace_root_fn: Callable[[], Path | None],
) -> Path:
    output = output_dir.resolve()
    if not override:
        return output
    try:
        workspace_root = resolve_workspace_root_fn()
    except Exception:
        workspace_root = None
    if workspace_root is not None and output == workspace_root.resolve():
        redirected = Path(override).resolve()
        redirected.mkdir(parents=True, exist_ok=True)
        return redirected
    return output


def maybe_load_artifact_fingerprint(
    core_fingerprint: str,
    *,
    workspace_root: Path,
    compiled_active_dir_fn: Callable[[Path | None], Path],
) -> str:
    import json

    artifact = compiled_active_dir_fn(workspace_root) / "governance-core.json"
    if not artifact.exists():
        return core_fingerprint
    try:
        artifact_fp = str(
            json.loads(artifact.read_text(encoding="utf-8")).get("fingerprint", "")
        ).strip()
        return artifact_fp or core_fingerprint
    except Exception as exc:
        logger.debug("Failed to read artifact fingerprint from %s: %s", artifact, exc)
        return core_fingerprint


def maybe_regenerate_wizard_contracts(
    output_base: Path, config: dict[str, Any], *, console: Any
) -> None:
    try:
        from sdd_wizard.contracts import generate_agent_instructions_from_config

        generate_agent_instructions_from_config(output_base, config)
        console.print("[cyan].sdd/agent-instructions.md regenerated[/cyan]")
    except ImportError:
        console.print(
            "[yellow]WARN: sdd_wizard not available, skipping agent-instructions.md regeneration[/yellow]"
        )


def normalize_compile_context(
    result: dict[str, Any], *, workspace_root: Path | None
) -> tuple[dict[str, Any], dict[str, Any], str]:
    phase_1 = result.get("phase_1", {})
    phase_2 = result.get("phase_2", {})
    compiled_path = str(workspace_root / ".sdd" / "compiled") if workspace_root else ""
    return phase_1, phase_2, compiled_path


def regenerate_seeds_flow(
    *,
    console: Any,
    resolve_workspace_root_fn: Callable[[], Path | None],
    validate_governance_path_fn: Callable[[str], bool],
    load_governance_config_fn: Callable[[str], dict[str, Any]],
    resolve_output_base_fn: Callable[[Path], Path],
    generate_agent_instruction_files_fn: Callable[[Path, dict[str, Any]], Any],
) -> None:
    if os.environ.get("SDD_SKIP_SEED_REGEN") == "1":
        return
    workspace_root = resolve_workspace_root_fn()
    if workspace_root is None:
        return
    generate_path = str(workspace_root / ".sdd" / "compiled")
    config = (
        load_governance_config_fn(generate_path)
        if validate_governance_path_fn(generate_path)
        else {}
    )
    output_base = resolve_output_base_fn(workspace_root)
    generate_agent_instruction_files_fn(output_base, config)
    console.print("[cyan]Agent instruction files regenerated[/cyan]")
    maybe_regenerate_wizard_contracts(output_base, config, console=console)


def run_compile_flow(
    *,
    profile: str | None,
    output_json: bool,
    console: Any,
    panel_cls: Any,
    run_compilation_fn: Callable[..., dict[str, Any]],
    update_profile_hash_fn: Callable[..., Any],
    resolve_workspace_root_fn: Callable[[], Path | None],
    check_artifact_consistency_fn: Callable[[str], tuple[bool, str]],
    run_governance_compile_json_fn: Callable[..., tuple[dict[str, Any], bool]],
    handle_compile_output_fn: Callable[..., Any],
    emit_compile_telemetry_fn: Callable[..., Any],
    regenerate_seeds_fn: Callable[..., Any],
) -> None:
    if not output_json:
        console.print(
            panel_cls(
                "[bold cyan]Compiling Governance Artifacts[/bold cyan]",
                border_style="cyan",
            )
        )
    if profile is not None and profile not in ("master", "client"):
        import typer as _typer
        from rich.console import Console as _Console

        _Console(stderr=True).print(
            f"[red]ERROR: Invalid profile '{profile}'. Use 'master' or 'client'.[/red]"
        )
        raise _typer.Exit(1)
    result = run_compilation_fn(profile=profile, console=console)
    workspace_root = resolve_workspace_root_fn()
    phase_1, phase_2, compiled_path = normalize_compile_context(
        result, workspace_root=workspace_root
    )
    core_fingerprint = str(phase_1.get("core_fingerprint", ""))
    update_profile_hash_fn(core_fingerprint, console=console)
    consistency_ok, consistency_reason = check_artifact_consistency_fn(compiled_path)
    payload, is_error = run_governance_compile_json_fn(
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
        consistency_ok=consistency_ok,
        consistency_reason=consistency_reason,
    )
    handle_compile_output_fn(
        output_json=output_json,
        payload=payload,
        is_error=is_error,
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
        consistency_reason=consistency_reason,
        console=console,
        artifact_path=compiled_path,
    )
    emit_compile_telemetry_fn(
        core_fingerprint=core_fingerprint,
        is_error=is_error,
        consistency_ok=consistency_ok,
        profile=profile,
    )
    regenerate_seeds_fn(console=console)
