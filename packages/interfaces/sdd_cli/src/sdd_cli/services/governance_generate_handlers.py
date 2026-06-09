"""Generate-phase governance handlers (generate_artifacts, bootstrap sequence)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from sdd_cli.generators.agent_seeds import (
    generate_agent_instruction_files,
    generate_agent_prompt_commands,
    generate_agent_seeds,
)
from sdd_cli.services.governance_artifact_handlers import (
    render_generate_table,
    run_governance_generate_json,
)
from sdd_cli.services.governance_command_output import fail_generate_precondition
from sdd_cli.services.governance_compile_handlers import resolve_output_base
from sdd_cli.utils.loader import load_governance_config, validate_governance_path
from sdd_cli.utils.output import emit_json
from sdd_cli.utils.sdd_authority import enforce_path_policy, resolve_workspace_root

logger = logging.getLogger(__name__)


def resolve_generate_path(path: str) -> str:
    """Resolve governance config path for generate; source of truth is .sdd/compiled."""
    if path:
        return path
    ws_root = resolve_workspace_root()
    if ws_root is None:
        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    return str(ws_root / ".sdd" / "compiled")


def generate_seeds(
    output_dir: str, config: dict[str, Any]
) -> tuple[list[tuple[str, Path, str]], Path]:
    """Generate agent seeds at canonical output path."""
    seeds_dir = Path(output_dir) / ".vscode" / "agents"
    seeds_info = generate_agent_seeds(seeds_dir, config)
    return seeds_info, seeds_dir


def write_instruction_files_safe(
    output_base: Path, config: dict[str, Any], *, console: Console
) -> None:
    """Attempt to write agent instruction files; log warnings on failure."""
    try:
        for label, target in generate_agent_instruction_files(output_base, config):
            console.print(f"[green]{label} instructions written to {target}[/green]")
    except Exception as _e:
        console.print(f"[yellow]WARN: could not write instruction files: {_e}[/yellow]")


def write_prompt_commands_safe(
    output_base: Path, config: dict[str, Any], *, console: Console
) -> None:
    """Attempt to write agent prompt command files; log warnings on failure."""
    try:
        for label, target in generate_agent_prompt_commands(output_base, config):
            console.print(f"[green]{label} prompt commands written to {target}[/green]")
    except Exception as _e:
        console.print(
            f"[yellow]WARN: could not write prompt command files: {_e}[/yellow]"
        )


def generate_adapters_safe(output_base: Path, *, console: Console) -> None:
    """Generate agent adapter files (skills + commands) for all targets."""
    try:
        from sdd_adapters.adapter_generator import AdapterGenerator

        adapter_gen = AdapterGenerator()
        results = adapter_gen.generate(output_dir=output_base)
        for target, result in results.items():
            if result.success and result.files_written:
                console.print(
                    f"[green]Adapters ({target}): {len(result.files_written)} files written[/green]"
                )
            elif result.errors:
                for err in result.errors:
                    console.print(f"[yellow]WARN: adapter {target}: {err}[/yellow]")
    except Exception as _e:
        console.print(f"[yellow]WARN: could not generate adapter files: {_e}[/yellow]")


def run_generate_phases(
    output_base: str, config: dict[str, Any]
) -> tuple[bool, bool, bool]:
    """Run skill registry, commands registry, and index generation phases.

    Returns:
        Tuple of (skills_generated, skill_index_generated, cli_index_generated).
    """
    from sdd_cli.generators._commands import generate_commands_registry
    from sdd_cli.generators._indices import (
        generate_cli_commands_index,
        generate_skill_index,
    )
    from sdd_cli.generators._skills import generate_skills_registry

    try:
        skills_result = generate_skills_registry(output_base, config)
        skills_generated = skills_result.get("skill_count", 0) > 0
    except Exception as e:
        logger.debug(f"Skills registry generation failed: {e}")
        skills_generated = False

    try:
        generate_commands_registry(output_base, config)
    except Exception as e:
        logger.debug(f"Commands registry generation failed: {e}")

    try:
        skill_index_result = generate_skill_index(output_base, config)
        skill_index_generated = skill_index_result.get("skill_count", 0) > 0
    except Exception as e:
        logger.debug(f"Skill index generation failed: {e}")
        skill_index_generated = False

    try:
        cli_index_result = generate_cli_commands_index(output_base, config)
        cli_index_generated = cli_index_result.get("command_count", 0) > 0
    except Exception as e:
        logger.debug(f"CLI commands index generation failed: {e}")
        cli_index_generated = False

    return skills_generated, skill_index_generated, cli_index_generated


def complete_bootstrap_handshake() -> None:
    """Create a default handshake response after successful bootstrap."""
    import os

    from sdd_core.governance.handshake import AgentHandshakeProtocol

    ahp = AgentHandshakeProtocol()
    challenge = ahp.generate_challenge(task_description="Bootstrap Session")
    skills = [
        s.get("name")
        for s in challenge.available_skills
        if isinstance(s, dict) and isinstance(s.get("name"), str)
    ]
    response = {
        "agent_id": os.environ.get("SDD_AGENT_ID", "bootstrap"),
        "understood_mandates": challenge.active_mandates,
        "skills_to_use": skills,
        "acknowledged_signature": True,
        "plan_summary": "bootstrap handshake auto-registered",
        "compliance_declaration": True,
    }
    ahp.complete_handshake(response)


def run_bootstrap_signing(key_id: str, *, keygen_fn: Any, sign_fn: Any) -> None:
    """Run keygen/sign sequence for full bootstrap, tolerating existing keys."""
    try:
        keygen_fn(key_id=key_id, output_dir=".sdd/trust")
    except typer.Exit as exc:
        # keygen exits(0) when key already exists; continue bootstrap.
        if int(exc.exit_code or 0) != 0:
            raise

    sign_fn(key_id=key_id, key_path=None, compiled_dir=None, source=False)
    ws_root = resolve_workspace_root()
    if (
        ws_root is not None
        and (ws_root / ".sdd" / "source" / "governance-core.json").exists()
    ):
        sign_fn(key_id=key_id, key_path=None, compiled_dir=None, source=True)


def generate_artifacts(
    *,
    output_dir: str | None,
    path: str,
    output_json: bool,
    console: Console,
) -> None:
    """Generate templates and agent seeds from compiled governance artifacts."""
    if output_dir is None:
        ws_root = resolve_workspace_root()
        output_dir = str(ws_root)

    resolved_path = resolve_generate_path(path)

    if not validate_governance_path(resolved_path):
        fail_generate_precondition(
            output_json=output_json,
            code="invalid_governance_path",
            message=f"Invalid governance path: {resolved_path}",
            data={
                "resolved_path": resolved_path,
                "output_dir": str(output_dir) if output_dir is not None else "",
            },
            console=console,
        )

    if not output_json:
        console.print(
            Panel("[bold cyan]Generating Agent Seeds[/bold cyan]", border_style="cyan")
        )

    config = load_governance_config(resolved_path)
    items = config.get("items", []) if isinstance(config, dict) else []
    if not isinstance(items, list) or len(items) == 0:
        fail_generate_precondition(
            output_json=output_json,
            code="missing_governance_items",
            message=(
                "No governance items loaded. "
                "Run 'sdd governance compile' before 'sdd governance generate'."
            ),
            data={
                "resolved_path": resolved_path,
                "output_dir": str(output_dir) if output_dir is not None else "",
            },
            console=console,
        )

    output_base = resolve_output_base(Path(output_dir))
    seeds_info, seeds_dir = generate_seeds(str(output_base), config)

    skills_generated, skill_index_generated, cli_index_generated = run_generate_phases(
        str(output_base), config
    )

    rows = [
        {"agent_template": agent, "location": str(file_path), "status": status}
        for agent, file_path, status in seeds_info
    ]
    if output_json:
        payload = run_governance_generate_json(
            resolved_path=resolved_path,
            output_base=output_base,
            seeds_dir=seeds_dir,
            rows=rows,
            skills_generated=skills_generated,
            skill_index_generated=skill_index_generated,
            cli_index_generated=cli_index_generated,
        )
        emit_json(payload)
    else:
        render_generate_table(console=console, rows=rows, seeds_dir=seeds_dir)
        write_instruction_files_safe(output_base, config, console=console)
        write_prompt_commands_safe(output_base, config, console=console)
        generate_adapters_safe(output_base, console=console)
