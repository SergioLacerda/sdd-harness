"""Configuration-oriented governance handlers (load/validate)."""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from sdd_cli.services.governance_config_reader import (
    _build_language_governance_advisories,
    _render_advisory_status,
)
from sdd_cli.services.governance_payloads import (
    build_governance_load_data,
    build_governance_validate_data,
    governance_error,
    governance_ok,
)
from sdd_cli.utils.output import emit_json


def run_governance_load(
    *,
    path: str,
    output_json: bool,
    console: Console,
    validate_path: Any,
    load_config: Any,
    get_summary: Any,
) -> None:
    """Execute governance load flow with JSON/text output modes."""
    if not validate_path(path):
        if output_json:
            data = build_governance_load_data(path=path, summary=None, exit_code=1)
            payload = governance_error(
                "governance load",
                data,
                code="invalid_governance_path",
                message=f"Invalid governance path: {path}",
            )
            emit_json(payload, err=True)
        else:
            console.print(f"[red]ERROR: Invalid governance path: {path}[/red]")
        raise typer.Exit(1)

    config = load_config(path)
    summary = get_summary(path, config=config)

    if output_json:
        data = build_governance_load_data(path=path, summary=summary, exit_code=0)
        payload = governance_ok("governance load", data)
        emit_json(payload)
        return

    table = Table(title="Governance Summary", show_header=True, header_style="bold")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    for key, value in summary.items():
        table.add_row(key, str(value))
    console.print(table)


def run_governance_validate(  # noqa: C901
    *,
    path: str,
    skip_handshake: bool,
    output_json: bool,
    console: Console,
    validate_path: Any,
    load_config: Any,
    check_files_accessible: Any,
    check_fingerprints_valid: Any,
    check_no_conflicts: Any,
    check_artifact_consistency: Any,
    run_runtime_preflight_fn: Any,
) -> None:
    """Execute governance validate flow with JSON/text output modes."""
    structure_ok = validate_path(path)
    config = load_config(path) if structure_ok else None

    checks: list[tuple[str, bool]] = [
        ("Structure validation", structure_ok),
        ("Files accessible", check_files_accessible(path)),
        ("Fingerprints valid", check_fingerprints_valid(config)),
        ("No conflicts", check_no_conflicts(config)),
    ]
    consistency_ok, consistency_reason = check_artifact_consistency(path)
    checks.append(("Artifact consistency", consistency_ok))

    if skip_handshake:
        handshake_active = True
    else:
        from sdd_core.governance.handshake import AgentHandshakeProtocol

        ahp = AgentHandshakeProtocol()
        handshake_active = ahp.is_handshake_valid()
    checks.append(("Active handshake (M015)", handshake_active))

    preflight = run_runtime_preflight_fn(path)
    preflight_ok = preflight.passed
    checks.append(("Runtime preflight", preflight_ok))

    all_passed = True
    check_payload: list[dict[str, Any]] = []
    for check_name, passed in checks:
        check_payload.append({"check": check_name, "passed": bool(passed)})
        if not passed:
            all_passed = False

    advisory_payload = _build_language_governance_advisories(path=path, config=config)

    if output_json:
        data = build_governance_validate_data(
            path=path,
            checks=check_payload,
            advisories=advisory_payload,
            preflight={
                "passed": preflight_ok,
                "reason": preflight.reason,
                "details": preflight.details,
            },
            consistency_reason=consistency_reason,
            exit_code=0 if all_passed else 1,
        )
        if all_passed:
            payload = governance_ok("governance validate", data)
        else:
            payload = governance_error(
                "governance validate",
                data,
                code="governance_validation_failed",
                message="one or more governance checks failed",
            )
        emit_json(payload, err=not all_passed)
        if not all_passed:
            raise typer.Exit(1)
        return

    table = Table(title="Validation Results", show_header=True, header_style="bold")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    for item in check_payload:
        status = "[green]PASS[/green]" if item["passed"] else "[red]FAIL[/red]"
        table.add_row(str(item["check"]), status)
    console.print(table)

    if advisory_payload:
        advisory_table = Table(
            title="Language Governance Advisories",
            show_header=True,
            header_style="bold",
        )
        advisory_table.add_column("Check", style="cyan")
        advisory_table.add_column("Severity", style="yellow")
        advisory_table.add_column("Status", style="green")
        advisory_table.add_column("Message", style="white")
        for item in advisory_payload:
            advisory_table.add_row(
                str(item["check"]),
                str(item["severity"]).upper(),
                _render_advisory_status(str(item["status"])),
                str(item["message"]),
            )
        console.print(advisory_table)

    if not preflight_ok and preflight.reason:
        console.print(f"[yellow]runtime preflight: {preflight.reason}[/yellow]")
    if not consistency_ok:
        console.print(f"[yellow]artifact consistency: {consistency_reason}[/yellow]")

    if all_passed:
        console.print("[green]All validation checks passed[/green]")
    else:
        console.print("[red]ERROR: Some validation checks failed[/red]")
        if not handshake_active:
            console.print(
                "  Next: run 'sdd governance handshake --init' to formalize session"
            )
        if not structure_ok or not consistency_ok or not preflight_ok:
            console.print("  Next: run 'sdd governance compile' to rebuild artifacts")
        raise typer.Exit(1)


def run_governance_load_cmd(*, path: str, output_json: bool, console: Any) -> None:
    """Convenience wrapper for run_governance_load with default dependency injection."""
    from rich.panel import Panel

    from sdd_cli.utils.loader import (
        get_governance_summary,
        load_governance_config,
        validate_governance_path,
    )

    if not output_json:
        console.print(
            Panel(
                f"[bold cyan]Governance Configuration Loaded[/bold cyan]\n{path}",
                border_style="cyan",
            )
        )
    run_governance_load(
        path=path,
        output_json=output_json,
        console=console,
        validate_path=validate_governance_path,
        load_config=load_governance_config,
        get_summary=get_governance_summary,
    )


def run_governance_validate_cmd(
    *,
    path: str,
    signature_mode: str,
    skip_handshake: bool,
    output_json: bool,
    console: Any,
) -> None:
    """Convenience wrapper for run_governance_validate with default dependency injection."""
    import typer
    from rich.panel import Panel

    from sdd_cli.services.governance_artifact_handlers import check_artifact_consistency
    from sdd_cli.services.governance_config_reader import (
        check_files_accessible,
        check_fingerprints_valid,
        check_no_conflicts,
    )
    from sdd_cli.services.runtime_preflight import run_runtime_preflight
    from sdd_cli.utils.loader import load_governance_config, validate_governance_path

    signature_mode = signature_mode.strip().lower()
    if signature_mode not in {"off", "warn", "strict"}:
        raise typer.BadParameter("signature_mode must be off, warn, or strict.")
    if not output_json:
        console.print(
            Panel(
                f"[bold cyan]Validating Governance[/bold cyan]\n{path}",
                border_style="cyan",
            )
        )
    run_governance_validate(
        path=path,
        skip_handshake=skip_handshake,
        output_json=output_json,
        console=console,
        validate_path=validate_governance_path,
        load_config=load_governance_config,
        check_files_accessible=check_files_accessible,
        check_fingerprints_valid=check_fingerprints_valid,
        check_no_conflicts=check_no_conflicts,
        check_artifact_consistency=check_artifact_consistency,
        run_runtime_preflight_fn=run_runtime_preflight,
    )
