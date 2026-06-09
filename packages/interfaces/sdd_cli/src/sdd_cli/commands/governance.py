"""Governance management commands."""

import logging
from pathlib import Path

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table as RichTable

from sdd_cli.services.governance_artifact_handlers import (
    _has_malformed_titles,  # noqa: F401  backward-compat re-export for unit tests
    render_governance_compile_table,  # noqa: F401 - backward-compat symbol for tests/patches
    run_governance_compile_json,
)
from sdd_cli.services.governance_artifact_handlers import (
    check_artifact_consistency as _check_artifact_consistency,
)
from sdd_cli.services.governance_command_output import handle_compile_output
from sdd_cli.services.governance_compile_handlers import (
    emit_compile_telemetry as _emit_compile_telemetry,
)
from sdd_cli.services.governance_compile_handlers import (
    regenerate_seeds as _regenerate_seeds,
)
from sdd_cli.services.governance_compile_handlers import (
    resolve_output_base as _resolve_output_base,  # noqa: F401  backward-compat re-export for unit tests
)
from sdd_cli.services.governance_compile_handlers import (
    run_compilation as _run_compilation,
)
from sdd_cli.services.governance_compile_handlers import (
    update_profile_hash as _update_profile_hash,
)
from sdd_cli.services.governance_config_handlers import (
    check_files_accessible as _check_files_accessible,
)
from sdd_cli.services.governance_config_handlers import (
    check_fingerprints_valid as _check_fingerprints_valid,
)
from sdd_cli.services.governance_config_handlers import (
    check_no_conflicts as _check_no_conflicts,
)
from sdd_cli.services.governance_config_handlers import (
    run_governance_load,
    run_governance_validate,
)
from sdd_cli.services.governance_generate_handlers import (
    complete_bootstrap_handshake as _complete_bootstrap_handshake,
)
from sdd_cli.services.governance_generate_handlers import (
    generate_artifacts as _generate_artifacts,
)
from sdd_cli.services.governance_generate_handlers import (
    generate_seeds as _generate_seeds,  # noqa: F401  backward-compat re-export for unit tests
)
from sdd_cli.services.governance_generate_handlers import (
    resolve_generate_path as _resolve_generate_path,  # noqa: F401  backward-compat re-export for unit tests
)
from sdd_cli.services.governance_generate_handlers import (
    run_bootstrap_signing as _run_bootstrap_signing,
)
from sdd_cli.services.governance_registry_handlers import run_reconcile_registries
from sdd_cli.services.governance_runtime_handlers import (
    run_governance_audit,
    run_governance_handshake,
)
from sdd_cli.services.governance_scoring_output import (
    render_governance_adherence_output,
)
from sdd_cli.services.governance_scoring_output import (
    run_governance_score as _run_governance_score,
)
from sdd_cli.services.governance_security_handlers import (
    resolve_compiled_dir as _resolve_compiled_dir_impl,
)
from sdd_cli.services.governance_security_handlers import (
    run_keygen as _run_keygen_impl,
)
from sdd_cli.services.governance_security_handlers import (
    run_sign as _run_sign_impl,
)
from sdd_cli.services.runtime_preflight import run_runtime_preflight
from sdd_cli.utils.command_errors import handle_cli_errors
from sdd_cli.utils.loader import (
    get_governance_summary,
    load_governance_config,
    validate_governance_path,
)
from sdd_cli.utils.output import is_json_mode
from sdd_cli.utils.sdd_authority import enforce_path_policy, resolve_workspace_root

# Backward-compat re-exports used by tests/patches.
Table = RichTable
__all__ = ["render_governance_compile_table", "Table"]

app = typer.Typer(help="Governance management commands")
console = Console()
logger = logging.getLogger(__name__)


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


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
    profile: str | None = typer.Option(  # noqa: UP045
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

    result = _run_compilation(profile=profile, console=console)
    phase_1 = result.get("phase_1", {})
    phase_2 = result.get("phase_2", {})
    core_fingerprint = str(phase_1.get("core_fingerprint", ""))

    _update_profile_hash(core_fingerprint, console=console)

    ws_root = resolve_workspace_root()
    compiled_path = str(ws_root / ".sdd" / "compiled") if ws_root else ""
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
    _emit_compile_telemetry(
        core_fingerprint=core_fingerprint,
        is_error=is_error,
        consistency_ok=consistency_ok,
        profile=profile,
    )
    _regenerate_seeds(console=console)


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
    ),
    skip_handshake: bool = typer.Option(
        False,
        "--skip-handshake",
        help="Skip M015 handshake check (use in CI pipelines)",
    ),
) -> None:
    """Validate governance integrity (structure + runtime preflight)."""
    signature_mode = signature_mode.strip().lower()
    if signature_mode not in {"off", "warn", "strict"}:
        raise typer.BadParameter("signature_mode must be off, warn, or strict.")
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


@app.command()
@handle_cli_errors(command_name="governance generate")
def generate(
    output_dir: str | None = typer.Option(  # noqa: UP045
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
    if not isinstance(full_bootstrap, bool):
        full_bootstrap = False
    if not isinstance(key_id, str):
        key_id = "dev-01"
    if not isinstance(profile, str):
        profile = "client"

    if not full_bootstrap:
        _generate_artifacts(
            output_dir=output_dir, path=path, output_json=_ctx_json(), console=console
        )
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
    _generate_artifacts(
        output_dir=output_dir, path=path, output_json=_ctx_json(), console=console
    )
    _run_bootstrap_signing(key_id, keygen_fn=keygen, sign_fn=sign)
    _complete_bootstrap_handshake()


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
    ws_root = resolve_workspace_root()
    if ws_root is None:
        Console(stderr=True).print("[red]ERROR: No workspace found.[/red]")
        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    _run_governance_score(
        ws_root=ws_root, verbose=verbose, threshold=threshold, console=console
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
    key_path: str | None = typer.Option(  # noqa: UP045
        None, help="Path to private key (.key file)"
    ),
    compiled_dir: str | None = typer.Option(  # noqa: UP045
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
    response: str | None = typer.Option(  # noqa: UP045
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
