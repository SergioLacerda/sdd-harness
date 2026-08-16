from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import datetime, timezone
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
    redirected = Path(override).resolve()
    env_workspace = os.environ.get("SDD_WORKSPACE_ROOT", "").strip()
    if env_workspace:
        try:
            workspace_root = Path(env_workspace).expanduser().resolve()
        except Exception:
            workspace_root = None
    else:
        workspace_root = None
    try:
        resolved_workspace = resolve_workspace_root_fn()
    except Exception:
        resolved_workspace = None
    if workspace_root is None:
        workspace_root = resolved_workspace
    if workspace_root is not None and output == workspace_root.resolve():
        redirected.mkdir(parents=True, exist_ok=True)
        return redirected
    if (
        env_workspace
        and resolved_workspace is not None
        and output == resolved_workspace.resolve()
        and not _is_session_default_override(redirected)
    ):
        redirected.mkdir(parents=True, exist_ok=True)
        return redirected
    return output


def _is_session_default_override(path: Path) -> bool:
    return path.name == f"sdd-test-output-{os.getpid()}"


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
        from sdd_wizard.contracts import (
            generate_agent_instructions_from_config,
            generate_root_bootstrap_from_config,
        )

        generate_agent_instructions_from_config(output_base, config)
        console.print("[cyan].sdd/agent-instructions.md regenerated[/cyan]")
        generate_root_bootstrap_from_config(output_base, config)
        console.print("[cyan]Root bootstrap files regenerated[/cyan]")
    except ImportError:
        console.print(
            "[yellow]WARN: sdd_wizard not available, skipping agent-instructions.md regeneration[/yellow]"
        )


def _bridge_client_language_context(
    workspace_root: Path, metadata: dict[str, Any]
) -> dict[str, str] | None:
    """Synthesize `language_context` from `.sdd/profile`'s `language` key.

    Only applies when the wizard hasn't already populated `language_context`
    — wizard output always wins (it may distinguish interaction vs. docs
    language, which a bare client `language` value cannot). Returns None when
    there is nothing to bridge (no client `language` key, or wizard data
    already present), so the caller leaves `metadata["language_context"]`
    untouched in either case.
    """
    existing = metadata.get("language_context")
    if isinstance(existing, dict) and existing:
        return None

    from sdd_core.utils.environment import (
        WorkspaceNotInitializedError,
        resolve_profile,
    )

    try:
        profile = resolve_profile(root=workspace_root)
    except WorkspaceNotInitializedError:
        return None

    if not profile.language:
        return None

    return {
        "preferred_human_language": profile.language,
        "preferred_chat_language": profile.language,
        "preferred_ui_language": profile.language,
        "preferred_local_docs_language": profile.language,
    }


def sync_workspace_metadata_from_config(
    workspace_root: Path, config: dict[str, Any]
) -> bool:
    """Align `.sdd/metadata.json` with the compiled governance snapshot."""
    import hashlib
    import json

    items = config.get("items", [])
    if not isinstance(items, list) or not items:
        return False

    fingerprint = str(config.get("core_fingerprint") or config.get("fingerprint") or "")
    if not fingerprint:
        return False

    metadata_path = workspace_root / ".sdd" / "metadata.json"
    try:
        metadata = (
            json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.exists()
            else {}
        )
    except json.JSONDecodeError:
        metadata = {}

    mandates = [
        item for item in items if str(item.get("type", "")).strip().upper() == "MANDATE"
    ]
    guidelines = [
        item
        for item in items
        if str(item.get("type", "")).strip().upper() in {"GUIDELINE", "RULE"}
    ]
    mandate_map = {
        str(item.get("id")): str(item.get("title") or item.get("name") or "Unknown")
        for item in mandates
        if item.get("id")
    }
    mandate_fingerprints = {
        str(item.get("id")): hashlib.sha256(
            json.dumps(item, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        for item in mandates
        if item.get("id")
    }

    existing_fingerprints = metadata.get("fingerprints")
    fingerprints_base: dict[str, Any] = (
        existing_fingerprints if isinstance(existing_fingerprints, dict) else {}
    )

    language_context_update = _bridge_client_language_context(workspace_root, metadata)

    metadata.update(
        {
            "version": str(metadata.get("version") or "3.0"),
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "mandates_count": len(mandates),
            "guidelines_count": len(guidelines),
            "governance_fingerprint": fingerprint[:16],
            "fingerprints": {
                **fingerprints_base,
                "combined": fingerprint[:16],
                "mandates": mandate_fingerprints,
            },
            "mandates": mandate_map,
        }
    )
    if language_context_update is not None:
        metadata["language_context"] = language_context_update
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


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
    generate_runtime_handbook_fn: Callable[..., list[Path]] | None = None,
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
    if sync_workspace_metadata_from_config(output_base, config):
        console.print("[cyan].sdd/metadata.json synchronized[/cyan]")
    generate_agent_instruction_files_fn(output_base, config)
    console.print("[cyan]Agent instruction files regenerated[/cyan]")
    maybe_regenerate_wizard_contracts(output_base, config, console=console)
    if generate_runtime_handbook_fn is not None:
        written = generate_runtime_handbook_fn(workspace_root, runtime_root=output_base)
        if written:
            console.print(
                f"[cyan]Runtime handbook regenerated ({len(written)} files)[/cyan]"
            )


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
