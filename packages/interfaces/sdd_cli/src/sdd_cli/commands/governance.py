"""Governance management commands."""

import json
import logging
import os
from pathlib import Path
from typing import Any

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table  # noqa: F401 - backward-compat symbol for tests/patches

from sdd_cli.generators.agent_seeds import (
    generate_agent_instruction_files,
    generate_agent_prompt_commands,
    generate_agent_seeds,
)
from sdd_cli.services.governance_artifact_handlers import (
    render_generate_table,
    render_governance_compile_table,  # noqa: F401 - backward-compat symbol for tests/patches
    run_governance_compile_json,
    run_governance_generate_json,
)
from sdd_cli.services.governance_command_output import (
    fail_generate_precondition,
    handle_compile_output,
)
from sdd_cli.services.governance_config_handlers import (
    run_governance_load,
    run_governance_validate,
)
from sdd_cli.services.governance_registry_handlers import run_reconcile_registries
from sdd_cli.services.governance_runtime_handlers import (
    run_governance_audit,
    run_governance_handshake,
)
from sdd_cli.services.governance_scoring_output import (
    render_governance_adherence_output,
    render_governance_score_output,
)
from sdd_cli.services.governance_security_handlers import (
    resolve_compiled_dir as _resolve_compiled_dir_impl,
)
from sdd_cli.services.governance_security_handlers import (
    run_keygen as _run_keygen_impl,
)
from sdd_cli.services.governance_security_handlers import run_sign as _run_sign_impl
from sdd_cli.services.runtime_preflight import run_runtime_preflight
from sdd_cli.utils.command_errors import handle_cli_errors
from sdd_cli.utils.loader import (
    get_governance_summary,
    load_governance_config,
    resolve_governance_compiled_dir,
    validate_governance_path,
)
from sdd_cli.utils.output import emit_json, is_json_mode
from sdd_cli.utils.sdd_authority import (
    compiled_active_dir,
    enforce_path_policy,
    resolve_workspace_root,
)
from sdd_cli.utils.telemetry_paths import resolve_compliance_events_path

app = typer.Typer(help="Governance management commands")
console = Console()
logger = logging.getLogger(__name__)


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _compute_compliance_score(
    *,
    compile_ok: bool,
    consistency_ok: bool,
    drift_detected: bool,
) -> tuple[int, dict[str, bool]]:
    """Compute governance compliance score (0–100, 25 pts per passing component).

    Components:
      governance_compile  — compilation succeeded without errors
      consistency         — artifact consistency check passed
      drift_detected      — no drift detected (True = 25 pts, False = 0 pts)
      lint_gate           — placeholder; always True here (enforced pre-commit)

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


def _resolve_output_base(output_dir: Path) -> Path:
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


def _run_compilation(profile: str | None = None) -> Any:
    """Run GovernanceOrchestrator full pipeline. Raises typer.Exit(1) on failure."""
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


def _update_profile_hash(core_fingerprint: str) -> None:
    """Persist core_hash into .sdd/profile for AHP Layer 2 verification (C5)."""
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


def _regenerate_seeds() -> None:
    """Auto-regenerate agent instruction files after successful compile (B6)."""
    import os

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
            # Test isolation: allow redirecting generated instruction files
            # to a temporary directory to avoid mutating repository files.
            _output_base = _resolve_output_base(_ws)
            generate_agent_instruction_files(_output_base, _gen_config)
            console.print("[cyan]Agent instruction files regenerated[/cyan]")
            try:
                from sdd_wizard.orchestration.seedlings.governance_seeds import (
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


@app.command("reconcile-registries")
@handle_cli_errors(command_name="governance reconcile-registries")
def reconcile_registries_cmd(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable reconciliation summary."
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Check drift without rewriting registries. Exits non-zero when drift exists.",
    ),
) -> None:
    """Rebuild commands/skills registries from canonical .sdd disk artifacts."""
    ws_root = resolve_workspace_root()
    run_reconcile_registries(
        ws_root=ws_root,
        check=check,
        json_output=bool(json_output or _ctx_json()),
        console=console,
    )


@app.command()
@handle_cli_errors(
    command_name="governance compile",
    next_hint="check .sdd/source artifacts or run 'sdd governance validate'",
)
def compile(
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to compile for: 'master' or 'client'. Defaults to active workspace profile.",
    ),
) -> None:
    """Compile governance artifacts (phase 1 + phase 2) and validate output."""
    if not isinstance(profile, str | type(None)):
        profile = None
    if profile is not None and profile not in ("master", "client"):
        console.print(
            f"[red]ERROR: Invalid profile '{profile}'. Use 'master' or 'client'.[/red]"
        )
        raise typer.Exit(1)

    if not _ctx_json():
        console.print(
            Panel(
                "[bold cyan]Compiling Governance Artifacts[/bold cyan]",
                border_style="cyan",
            )
        )

    result = _run_compilation(profile=profile)
    phase_1 = result.get("phase_1", {})
    phase_2 = result.get("phase_2", {})
    core_fingerprint = str(phase_1.get("core_fingerprint", ""))

    _update_profile_hash(core_fingerprint)
    compiled_path = _resolve_generate_path("")
    consistency_ok, consistency_reason = _check_artifact_consistency(compiled_path)
    payload, is_error = run_governance_compile_json(
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
        consistency_ok=consistency_ok,
        consistency_reason=consistency_reason,
    )
    handle_compile_output(
        output_json=_ctx_json(),
        payload=payload,
        is_error=is_error,
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
        consistency_reason=consistency_reason,
        console=console,
    )

    try:
        import uuid

        from sdd_runtime.telemetry import RuntimeEvent, TelemetrySink

        from sdd_core.utils.environment import find_workspace_root as _fws_compile

        _ws_compile = _fws_compile()
        _events_path = (
            resolve_compliance_events_path(workspace_root=_ws_compile)
            if _ws_compile
            else resolve_compliance_events_path()
        )
        _compile_trace_id = str(uuid.uuid4())
        sink = TelemetrySink(jsonl_path=_events_path, logging_mode="active")
        sink.emit(
            RuntimeEvent(
                event="governance.compile.complete",
                command="governance compile",
                status="ok",
                trace_id=_compile_trace_id,
                details={
                    "core_hash": core_fingerprint[:16] if core_fingerprint else ""
                },
            )
        )

        # Emit compliance score event (governance.compliance.score)
        _score, _components = _compute_compliance_score(
            compile_ok=not is_error,
            consistency_ok=consistency_ok,
            drift_detected=not consistency_ok,
        )
        _score_status = "ok" if _score >= 75 else ("warn" if _score >= 50 else "fail")
        _active_profile = profile or "client"
        sink.emit(
            RuntimeEvent(
                event="governance.compliance.score",
                command="governance compile",
                status=_score_status,
                trace_id=_compile_trace_id,
                details={
                    "score": _score,
                    "components": _components,
                    "profile": _active_profile,
                },
            )
        )
        sink.flush()
    except Exception as _event_err:
        logger.debug("Failed to append governance compile event: %s", _event_err)

    _regenerate_seeds()


@app.command()
@handle_cli_errors(command_name="governance load")
def load(
    path: str = typer.Option(
        ".sdd/compiled",
        help="Path to governance configuration (default: .sdd/compiled)",
    ),
) -> None:
    """Load and display governance configuration summary."""
    if not _ctx_json():
        console.print(
            Panel(
                f"[bold cyan]Governance Configuration Loaded[/bold cyan]\n{path}",
                border_style="cyan",
            )
        )
    run_governance_load(
        path=path,
        output_json=_ctx_json(),
        console=console,
        validate_path=validate_governance_path,
        load_config=load_governance_config,
        get_summary=get_governance_summary,
    )


@app.command()
@handle_cli_errors(
    command_name="governance validate",
    next_hint="run 'sdd governance compile' to rebuild artifacts",
)
def validate(  # noqa: C901
    path: str = typer.Option(
        ".sdd/compiled",
        help="Path to governance configuration (default: .sdd/compiled)",
    ),
    signature_mode: str = typer.Option(
        "warn",
        help="Signature enforcement mode: off|warn|strict",
        click_type=click.Choice(["off", "warn", "strict"], case_sensitive=False),
    ),
    skip_handshake: bool = typer.Option(
        False,
        "--skip-handshake",
        help="Skip M015 handshake check (use in CI pipelines)",
    ),
) -> None:
    """Validate governance integrity (structure + runtime preflight)."""
    if not _ctx_json():
        console.print(
            Panel(
                f"[bold cyan]Validating Governance[/bold cyan]\n{path}",
                border_style="cyan",
            )
        )
    run_governance_validate(
        path=path,
        skip_handshake=skip_handshake,
        output_json=_ctx_json(),
        console=console,
        validate_path=validate_governance_path,
        load_config=load_governance_config,
        check_files_accessible=_check_files_accessible,
        check_fingerprints_valid=_check_fingerprints_valid,
        check_no_conflicts=_check_no_conflicts,
        check_artifact_consistency=_check_artifact_consistency,
        run_runtime_preflight_fn=run_runtime_preflight,
    )


def _resolve_generate_path(path: str) -> str:
    """Resolve the governance config path for generate.

    Source of truth: .sdd/compiled only.
    """
    if path:
        return path
    ws_root = resolve_workspace_root()
    if ws_root is None:
        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    return str(ws_root / ".sdd" / "compiled")


def _generate_seeds(
    output_dir: str, config: dict[str, Any]
) -> tuple[list[tuple[str, Path, str]], Path]:
    """Generate agent seeds at canonical output path."""
    seeds_dir = Path(output_dir) / ".vscode" / "agents"
    seeds_info = generate_agent_seeds(seeds_dir, config)
    return seeds_info, seeds_dir


def _write_instruction_files_safe(output_base: Path, config: dict[str, Any]) -> None:
    """Attempt to write agent instruction files; log warnings on failure."""
    try:
        for label, target in generate_agent_instruction_files(output_base, config):
            console.print(f"[green]{label} instructions written to {target}[/green]")
    except Exception as _e:
        console.print(f"[yellow]WARN: could not write instruction files: {_e}[/yellow]")


def _write_prompt_commands_safe(output_base: Path, config: dict[str, Any]) -> None:
    """Attempt to write agent prompt command files; log warnings on failure."""
    try:
        for label, target in generate_agent_prompt_commands(output_base, config):
            console.print(f"[green]{label} prompt commands written to {target}[/green]")
    except Exception as _e:
        console.print(
            f"[yellow]WARN: could not write prompt command files: {_e}[/yellow]"
        )


def _generate_adapters_safe(output_base: Path) -> None:
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


def _run_generate_phases(
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


def _complete_bootstrap_handshake() -> None:
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


def _run_bootstrap_signing(key_id: str) -> None:
    """Run keygen/sign sequence for full bootstrap, tolerating existing keys."""
    try:
        keygen(key_id=key_id, output_dir=".sdd/trust")
    except typer.Exit as exc:
        # keygen exits(0) when key already exists; continue bootstrap.
        if int(exc.exit_code or 0) != 0:
            raise

    sign(
        key_id=key_id,
        key_path=None,
        compiled_dir=None,
        source=False,
    )
    ws_root = resolve_workspace_root()
    if (
        ws_root is not None
        and (ws_root / ".sdd" / "source" / "governance-core.json").exists()
    ):
        sign(
            key_id=key_id,
            key_path=None,
            compiled_dir=None,
            source=True,
        )


def _generate_artifacts(
    *,
    output_dir: str | None,
    path: str,
) -> None:
    """Generate templates and agent seeds from compiled governance artifacts."""
    # Resolve output_dir: if not provided, use workspace root
    if output_dir is None:
        ws_root = resolve_workspace_root()
        output_dir = str(ws_root)

    resolved_path = _resolve_generate_path(path)

    if not validate_governance_path(resolved_path):
        fail_generate_precondition(
            output_json=_ctx_json(),
            code="invalid_governance_path",
            message=f"Invalid governance path: {resolved_path}",
            data={
                "resolved_path": resolved_path,
                "output_dir": str(output_dir) if output_dir is not None else "",
            },
            console=console,
        )

    if not _ctx_json():
        console.print(
            Panel("[bold cyan]Generating Agent Seeds[/bold cyan]", border_style="cyan")
        )

    config = load_governance_config(resolved_path)
    items = config.get("items", []) if isinstance(config, dict) else []
    if not isinstance(items, list) or len(items) == 0:
        fail_generate_precondition(
            output_json=_ctx_json(),
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

    output_base = _resolve_output_base(Path(output_dir))
    seeds_info, seeds_dir = _generate_seeds(str(output_base), config)

    skills_generated, skill_index_generated, cli_index_generated = _run_generate_phases(
        str(output_base), config
    )

    rows = [
        {"agent_template": agent, "location": str(file_path), "status": status}
        for agent, file_path, status in seeds_info
    ]
    if _ctx_json():
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

        _write_instruction_files_safe(output_base, config)
        _write_prompt_commands_safe(output_base, config)
        _generate_adapters_safe(output_base)


@app.command()
@handle_cli_errors(command_name="governance generate")
def generate(
    output_dir: str | None = typer.Option(
        None, help="Output directory for generated files (defaults to workspace root)"
    ),
    path: str = typer.Option(
        "",
        help="Path to governance configuration (defaults to .sdd/compiled)",
    ),
    full_bootstrap: bool = typer.Option(
        False,
        "--full-bootstrap",
        help=(
            "Run onboarding bootstrap sequence: compile, generate, keygen, "
            "sign compiled artifacts and sign source governance."
        ),
    ),
    key_id: str = typer.Option(
        "dev-01",
        help="Key ID used in full bootstrap signing steps.",
    ),
    profile: str = typer.Option(
        "client",
        "--profile",
        "-p",
        help="Profile to compile for: 'master' or 'client'. Defaults to 'client'.",
    ),
) -> None:
    """Generate templates and agent seeds."""
    # When command function is called directly in unit tests, Typer may pass
    # OptionInfo defaults instead of concrete values.
    if not isinstance(full_bootstrap, bool):
        full_bootstrap = False
    if not isinstance(key_id, str):
        key_id = "dev-01"
    if not isinstance(profile, str):
        profile = "client"

    if not full_bootstrap:
        _generate_artifacts(output_dir=output_dir, path=path)
        return

    if not _ctx_json():
        console.print(
            Panel(
                "[bold cyan]Full Bootstrap[/bold cyan]\n"
                "Running compile + generate + keygen + sign steps",
                border_style="cyan",
            )
        )

    compile(profile=profile)
    _generate_artifacts(output_dir=output_dir, path=path)
    _run_bootstrap_signing(key_id)
    _complete_bootstrap_handshake()


def _check_files_accessible(path: str) -> bool:
    """Check if all required governance files are accessible."""
    return validate_governance_path(path)


def _check_fingerprints_valid(config: dict[str, Any] | None) -> bool:
    """Check if governance fingerprints are valid."""
    try:
        if config is None:
            return False
        return (
            config.get("core_fingerprint") is not None
            and config.get("client_fingerprint") is not None
        )
    except Exception:
        return False


def _check_no_conflicts(config: dict[str, Any] | None) -> bool:
    """Check for conflicts in governance configuration."""
    try:
        if config is None:
            return False
        # Check that core and client fingerprints are different
        return config.get("core_fingerprint") != config.get("client_fingerprint")
    except Exception:
        return False


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_consistency_artifacts(
    compiled_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    audit_dir = compiled_dir / "audit"
    core_json = _safe_json(compiled_dir / "governance-core.json") or _safe_json(
        audit_dir / "governance-core.json"
    )
    client_json = _safe_json(compiled_dir / "governance-client.json") or _safe_json(
        audit_dir / "governance-client.json"
    )
    core_meta = _safe_json(audit_dir / "metadata-core.json") or _safe_json(
        compiled_dir / "metadata-core.json"
    )
    client_meta = _safe_json(audit_dir / "metadata-client-template.json") or _safe_json(
        compiled_dir / "metadata-client-template.json"
    )
    if any(x is None for x in (core_json, client_json, core_meta, client_meta)):
        return None
    # Type assertion: guard above guarantees all values are non-None
    assert core_json is not None
    assert client_json is not None
    assert core_meta is not None
    assert client_meta is not None
    return core_json, client_json, core_meta, client_meta


def _count_items_by_type(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        item_type = str(item.get("type", "UNKNOWN")).upper()
        counts[item_type] = counts.get(item_type, 0) + 1
    return counts


def _has_malformed_titles(items: list[dict[str, Any]]) -> bool:
    for item in items:
        title = str(item.get("title") or "").strip().lower()
        if title.startswith("- status:"):
            return True
    return False


def _validate_payload_vs_metadata(
    payload: dict[str, Any], metadata: dict[str, Any], label: str
) -> str | None:
    items = payload.get("items", [])
    if not isinstance(items, list):
        return "invalid payload schema: items must be a list"
    if payload.get("fingerprint") != metadata.get("fingerprint"):
        return f"{label} fingerprint mismatch between payload and metadata"
    if int(metadata.get("item_count", -1)) != len(items):
        return f"{label} item_count mismatch"
    if _count_items_by_type(items) != dict(metadata.get("items_by_type", {})):
        return f"{label} items_by_type mismatch"
    if label == "core" and _has_malformed_titles(items):
        return "malformed mandate title detected"
    return None


def _check_artifact_consistency(path: str) -> tuple[bool, str]:
    """Cross-check compiled governance JSON and metadata consistency."""
    compiled_dir = resolve_governance_compiled_dir(path)
    if compiled_dir is None:
        return (
            False,
            f"could not resolve compiled governance directory at {path} (check path policy or missing artifacts)",
        )
    loaded = _load_consistency_artifacts(compiled_dir)
    if loaded is None:
        return False, "missing governance JSON or metadata artifacts"
    core_json, client_json, core_meta, client_meta = loaded

    core_issue = _validate_payload_vs_metadata(core_json, core_meta, "core")
    if core_issue:
        return False, core_issue
    client_issue = _validate_payload_vs_metadata(client_json, client_meta, "client")
    if client_issue:
        return False, client_issue
    if client_json.get("fingerprint_core_salt") != client_meta.get(
        "fingerprint_core_salt"
    ):
        return False, "client fingerprint_core_salt mismatch"

    return True, "ok"


@app.command()
def score(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show per-check breakdown."
    ),
    threshold: int = typer.Option(
        80, "--threshold", "-t", help="Minimum passing score (0-100)."
    ),
) -> None:
    """Compute governance health score (0-100).

    Formula:
        score = (weighted_passed / weighted_total) * 100

    Weights:
        - .sdd/profile present + valid:     30
        - governance artifacts compiled:    30
        - AHP confidence >= 50%:            20
        - core_hash in profile matches:     20
    """

    from sdd_core.governance.handshake import AgentHandshakeProtocol
    from sdd_core.utils.environment import WorkspaceNotInitializedError, resolve_profile

    ws_root = resolve_workspace_root()
    if ws_root is None:
        Console(stderr=True).print("[red]ERROR: No workspace found.[/red]")
        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")

    checks: list[tuple[str, bool, int]] = []  # (label, passed, weight)

    # Check 1 (30): .sdd/profile present + valid type
    try:
        profile_ctx = resolve_profile(root=ws_root)
        checks.append((".sdd/profile valid", True, 30))
    except WorkspaceNotInitializedError:
        checks.append((".sdd/profile valid", False, 30))
        profile_ctx = None

    # Check 2 (30): governance artifacts compiled
    artifact_candidates = [compiled_active_dir(ws_root) / "governance-core.json"]
    artifacts_ok = any(p.exists() for p in artifact_candidates)
    checks.append(("governance artifacts compiled", artifacts_ok, 30))

    # Check 3 (20): AHP confidence >= 50%
    ahp = AgentHandshakeProtocol(project_root=ws_root)
    ahp_state, ahp_report = ahp.validate(output_mode="silent", force_recheck=True)
    confidence_ok = ahp_report.confidence >= 50.0
    checks.append(
        (
            f"AHP confidence >= 50% (actual: {ahp_report.confidence:.1f}%)",
            confidence_ok,
            20,
        )
    )

    # Check 4 (20): core_hash in profile matches compiled artifact
    hash_ok = False
    if profile_ctx is not None and profile_ctx.core_hash and artifacts_ok:
        try:
            import hashlib
            import json as _json

            art_path = next(p for p in artifact_candidates if p.exists())
            raw = art_path.read_bytes()
            data = _json.loads(raw)
            artifact_fp = str(data.get("fingerprint", "")).strip()

            if artifact_fp:
                hash_ok = artifact_fp[:16] == profile_ctx.core_hash
            else:
                # Backward compatibility for artifacts without embedded fingerprint.
                clean = {
                    k: v
                    for k, v in data.items()
                    if k not in {"_signature", "fingerprint"}
                }
                computed = hashlib.sha256(
                    _json.dumps(clean, sort_keys=True).encode()
                ).hexdigest()[:16]
                hash_ok = computed == profile_ctx.core_hash
        except Exception:
            hash_ok = False
    checks.append(("core_hash matches artifact", hash_ok, 20))

    # Compute weighted score using centralized function
    from sdd_core.governance.scoring import compute_governance_score

    final_score = compute_governance_score(checks)

    render_governance_score_output(
        checks=checks,
        final_score=final_score,
        threshold=threshold,
        verbose=verbose,
        console=console,
    )


@app.command()
def adherence(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show per-dimension breakdown."
    ),
    threshold: int = typer.Option(
        80, "--threshold", "-t", help="Minimum passing score (0-100)."
    ),
    window: int = typer.Option(
        24, "--window", "-w", help="Time window in hours for behavioral events."
    ),
) -> None:
    """Compute governance adherence score (0-100).

    Formula:
        score = behavioral(50) + structural(30) + freshness(20)

    Dimensions:
        behavioral (50): allow / (allow + warn + block) from compliance events.
        structural (30): fingerprint match between state cache and compiled artifact.
        freshness  (20): linear decay from last_check vs TTL (client=30m, master=8h).
    """
    from sdd_core.governance.compliance import compute_governance_adherence

    ws_root = resolve_workspace_root()

    try:
        result = compute_governance_adherence(
            workspace_root=ws_root, window_hours=window
        )
    except Exception as exc:
        Console(stderr=True).print(
            f"[red]ERROR computing governance adherence: {exc}[/red]"
        )
        raise typer.Exit(1) from exc

    render_governance_adherence_output(
        result=result,
        threshold=threshold,
        window=window,
        verbose=verbose,
        console=console,
    )


@app.command()
@handle_cli_errors(command_name="governance keygen")
def keygen(
    key_id: str = typer.Option(
        "auditor-01", help="Key ID for the new key (e.g. dev-01, prod-01)"
    ),
    output_dir: str = typer.Option(
        ".sdd/trust", help="Where to save the keys (should be git-ignored)"
    ),
) -> None:
    """
    Generate a new Ed25519 key pair for signing governance artifacts.
    This is the first step in the 007 Security Workflow. It generates a private key
    used for signing and a public key used for verification.
    """
    _run_keygen_impl(key_id=key_id, output_dir=output_dir, console=console)


@app.command()
@handle_cli_errors(command_name="governance sign")
def sign(
    key_id: str = typer.Option("auditor-01", help="Key ID to use for signing"),
    key_path: str | None = typer.Option(None, help="Path to private key (.key file)"),
    compiled_dir: str | None = typer.Option(
        None, help="Directory containing artifacts to sign (default: .sdd/compiled)"
    ),
    source: bool = typer.Option(
        False,
        "--source",
        help="Sign the source governance file (.sdd/source/governance-core.json)",
    ),
) -> None:
    """
    Sign governance artifacts (JSON) with an Ed25519 private key.
    This ensures that artifacts have not been tampered with and come from a trusted source.
    Generates .sig files for governance-core.json and governance-client.json.

    Use --source to sign the source governance configuration (.sdd/source/governance-core.json).
    """
    ws_root = resolve_workspace_root()
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")

    if source:
        target_dir = ws_root / ".sdd" / "source"
        targets = ["governance-core.json"]
    else:
        target_dir = _resolve_compiled_dir(ws_root, compiled_dir)
        targets = ["governance-core.json", "governance-client.json"]

    _run_sign_impl(
        key_id=key_id,
        key_path=key_path,
        ws_root=ws_root,
        target_dir=target_dir,
        targets=targets,
        console=console,
    )


def _resolve_compiled_dir(ws_root: Path, compiled_dir: str | None) -> Path:
    return _resolve_compiled_dir_impl(
        ws_root=ws_root,
        compiled_dir=compiled_dir,
        console=console,
    )


@app.command()
@handle_cli_errors(command_name="governance audit")
def audit(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed issues and remediations"
    ),
) -> None:
    """
    Perform a Security Audit of the governance runtime.
    Verifies artifact signatures, keyring trust, workspace integrity, and configuration safety.
    A score below 70 is considered failing and will block production deployments in strict mode.
    """
    run_governance_audit(verbose=verbose, output_json=_ctx_json(), console=console)


@app.command()
@handle_cli_errors(command_name="governance handshake")
def handshake(
    response: str | None = typer.Option(
        None, "--response", "-r", help="Agent Handshake Response (JSON string)"
    ),
    init: bool = typer.Option(
        False, "--init", help="Generate a Handshake Challenge for the agent"
    ),
    task_desc: str = typer.Option(
        "General Task", "--task", help="Task description for the challenge"
    ),
    output_mode: str = typer.Option(
        "compact", "--mode", help="Output mode: silent, compact, verbose"
    ),
) -> None:
    """
    Bidirectional handshake protocol (M015).

    Use --init to generate a challenge for the agent, or --response to submit
     the agent's acknowledgment and declared skills.
    """
    run_governance_handshake(
        response=response,
        init=init,
        task_desc=task_desc,
        output_mode=output_mode,
        output_json=_ctx_json(),
        console=console,
    )
