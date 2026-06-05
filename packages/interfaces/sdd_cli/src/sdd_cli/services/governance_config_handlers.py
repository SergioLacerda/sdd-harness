"""Configuration-oriented governance handlers (load/validate)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from sdd_cli.services.governance_payloads import (
    build_governance_load_data,
    build_governance_validate_data,
    governance_error,
    governance_ok,
)
from sdd_cli.utils.output import emit_json

_PORTUGUESE_MARKER_RE = re.compile(
    r"\b(não|para|como|uma|idioma|português|governança|artefatos|deve|pode|documentação|estruturada)\b",
    re.IGNORECASE,
)


def _workspace_root_from_governance_path(path: str) -> Path:
    """Best-effort workspace root resolution from a governance path."""
    resolved = Path(path).resolve()
    if resolved.name == "compiled" and resolved.parent.name == ".sdd":
        return resolved.parent.parent
    if resolved.name == ".sdd":
        return resolved.parent
    return resolved.parent


def _detect_non_english_markers(root: Path, *, limit: int = 5) -> list[str]:
    """Return a small sample of files containing obvious Portuguese markers."""
    matches: list[str] = []
    if not root.exists():
        return matches
    for file_path in sorted(root.rglob("*.md")):
        if len(matches) >= limit:
            break
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _PORTUGUESE_MARKER_RE.search(content):
            matches.append(str(file_path))
    return matches


def _build_language_governance_advisories(
    *, path: str, config: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Build non-blocking language governance advisories from mandates/guidelines/context."""
    advisories: list[dict[str, Any]] = []
    config = config or {}
    mandates = config.get("mandates", {})
    language_context = config.get("language_context", {})
    workspace_root = _workspace_root_from_governance_path(path)
    docs_root = workspace_root / "docs"
    analysis_root = workspace_root / ".analysis"

    m011_active = isinstance(mandates, dict) and "M011" in mandates
    advisories.append(
        {
            "check": "Language mandate core (M011)",
            "severity": "info" if m011_active else "warn",
            "status": "pass" if m011_active else "warn",
            "message": "M011 is active for mandatory language surfaces."
            if m011_active
            else "M011 was not found in compiled mandate metadata.",
        }
    )

    source_guidelines = Path(path).resolve().parent / "source" / "guidelines.dsl"
    has_language_guidelines = False
    if source_guidelines.exists():
        content = source_guidelines.read_text(encoding="utf-8")
        has_language_guidelines = all(gid in content for gid in ("G021", "G022"))
    advisories.append(
        {
            "check": "Language preference guidelines",
            "severity": "info" if has_language_guidelines else "warn",
            "status": "pass" if has_language_guidelines else "warn",
            "message": "Universal language preference guidelines are present."
            if has_language_guidelines
            else "Language preference guidelines were not found in .sdd/source/guidelines.dsl.",
        }
    )

    analysis_classified = (analysis_root / "README.md").exists()
    advisories.append(
        {
            "check": "Analysis workspace classification",
            "severity": "info" if analysis_classified else "warn",
            "status": "pass" if analysis_classified else "warn",
            "message": ".analysis/ is documented as workspace-local documentation under contextual language guidance."
            if analysis_classified
            else ".analysis/ classification is not explicitly documented; local language handling may be ambiguous.",
            "surface": "workspace_local_docs",
        }
    )

    mandatory_docs_samples = _detect_non_english_markers(docs_root)
    if m011_active and mandatory_docs_samples:
        advisories.append(
            {
                "check": "Mandatory docs surface language drift",
                "severity": "warn",
                "status": "warn",
                "message": "Possible non-English markers were found under docs/. Review canonical technical documentation for M011 alignment.",
                "surface": "technical_docs",
                "samples": mandatory_docs_samples,
            }
        )
    else:
        advisories.append(
            {
                "check": "Mandatory docs surface language drift",
                "severity": "info",
                "status": "pass" if m011_active else "info",
                "message": "No obvious non-English markers were sampled under docs/."
                if m011_active
                else "Docs surface sampling skipped because M011 is not active.",
                "surface": "technical_docs",
            }
        )

    local_analysis_samples = _detect_non_english_markers(analysis_root)
    if local_analysis_samples:
        advisories.append(
            {
                "check": "Local analysis language context",
                "severity": "info",
                "status": "info",
                "message": "Non-English content exists under .analysis/ and is treated as contextual workspace-local documentation unless promoted to canonical docs.",
                "surface": "workspace_local_docs",
                "samples": local_analysis_samples,
            }
        )

    if isinstance(language_context, dict) and language_context:
        advisories.append(
            {
                "check": "Wizard language context captured",
                "severity": "info",
                "status": "pass",
                "message": "Wizard language preference context is available to governed tooling.",
            }
        )
        local_docs_language = language_context.get("preferred_local_docs_language")
        if m011_active and local_docs_language and local_docs_language != "English":
            advisories.append(
                {
                    "check": "Local docs preference under M011",
                    "severity": "warn",
                    "status": "warn",
                    "message": "Local documentation preference is non-English; this may guide local-only notes but does not override M011 for technical documentation or governance artifacts.",
                }
            )
    else:
        advisories.append(
            {
                "check": "Wizard language context captured",
                "severity": "info",
                "status": "info",
                "message": "No wizard language preference context was found; contextual language guidance may be unavailable.",
            }
        )

    return advisories


def _render_advisory_status(status: str) -> str:
    """Render advisory status with Rich markup."""
    normalized = status.lower()
    if normalized == "pass":
        return "[green]PASS[/green]"
    if normalized == "warn":
        return "[yellow]WARN[/yellow]"
    if normalized == "info":
        return "[blue]INFO[/blue]"
    return status.upper()


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
