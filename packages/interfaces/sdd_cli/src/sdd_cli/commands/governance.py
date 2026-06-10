"""Governance management commands."""

import logging

import click
import typer
from rich.console import Console
from rich.table import Table as RichTable

from sdd_cli.services.governance_artifact_handlers import (
    _has_malformed_titles,  # noqa: F401  backward-compat re-export for unit tests
    render_governance_compile_table,  # noqa: F401 - backward-compat symbol for tests/patches
)
from sdd_cli.services.governance_compile_handlers import (
    resolve_output_base,  # noqa: F401  backward-compat re-export for unit tests
    run_compile,
)
from sdd_cli.services.governance_config_handlers import (
    run_governance_load_cmd,
    run_governance_validate_cmd,
)
from sdd_cli.services.governance_generate_handlers import (
    generate_seeds,  # noqa: F401  backward-compat re-export for unit tests
    resolve_generate_path,  # noqa: F401  backward-compat re-export for unit tests
    run_generate,
)
from sdd_cli.services.governance_registry_handlers import run_reconcile_registries
from sdd_cli.services.governance_runtime_handlers import (
    run_governance_audit,
    run_governance_handshake,
)
from sdd_cli.services.governance_scoring_output import (
    run_governance_adherence_cmd,
    run_governance_score_cmd,
)
from sdd_cli.services.governance_security_handlers import run_keygen, run_sign_cmd
from sdd_cli.utils.command_errors import handle_cli_errors
from sdd_cli.utils.output import is_json_mode
from sdd_cli.utils.sdd_authority import resolve_workspace_root

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
    run_compile(profile=profile, output_json=_ctx_json(), console=console)


@app.command()
@handle_cli_errors(command_name="governance load")
def load(
    path: str = typer.Option(
        ".sdd/compiled",
        help="Path to governance configuration (default: .sdd/compiled)",
    ),
) -> None:
    """Load and display governance configuration summary."""
    run_governance_load_cmd(path=path, output_json=_ctx_json(), console=console)


@app.command()
@handle_cli_errors(
    command_name="governance validate",
    next_hint="run 'sdd governance compile' to rebuild artifacts",
)
def validate(
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
    run_governance_validate_cmd(
        path=path,
        signature_mode=signature_mode,
        skip_handshake=skip_handshake,
        output_json=_ctx_json(),
        console=console,
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
    run_generate(
        output_dir=output_dir,
        path=path,
        full_bootstrap=full_bootstrap,
        key_id=key_id,
        profile=profile,
        output_json=_ctx_json(),
        console=console,
        compile_fn=compile,
        keygen_fn=keygen,
        sign_fn=sign,
    )


@app.command()
def score(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show per-check breakdown."
    ),
    threshold: int = typer.Option(
        80, "--threshold", "-t", help="Minimum passing score (0-100)."
    ),
) -> None:
    """Compute governance health score (0-100)."""
    run_governance_score_cmd(verbose=verbose, threshold=threshold, console=console)


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
    """Compute governance adherence score (0-100)."""
    run_governance_adherence_cmd(
        verbose=verbose, threshold=threshold, window=window, console=console
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
    """Generate a new Ed25519 key pair for signing governance artifacts."""
    run_keygen(key_id=key_id, output_dir=output_dir, console=console)


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
    """Sign governance artifacts (JSON) with an Ed25519 private key."""
    run_sign_cmd(
        key_id=key_id,
        key_path=key_path,
        compiled_dir=compiled_dir,
        source=source,
        console=console,
    )


@app.command()
@handle_cli_errors(command_name="governance audit")
def audit(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed issues and remediations"
    ),
) -> None:
    """Perform a Security Audit of the governance runtime."""
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
    """Bidirectional handshake protocol (M015)."""
    run_governance_handshake(
        response=response,
        init=init,
        task_desc=task_desc,
        output_mode=output_mode,
        output_json=_ctx_json(),
        console=console,
    )
