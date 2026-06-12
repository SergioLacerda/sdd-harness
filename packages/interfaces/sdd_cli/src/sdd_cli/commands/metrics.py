"""sdd metrics — token economy metrics commands.

Subcommands:
  sdd metrics summary   — print token economy table (rich formatted)
  sdd metrics serve     — start Prometheus scrape endpoint (foreground daemon)
"""

from __future__ import annotations

import http.server
import os
import threading
from pathlib import Path
from typing import Any

import click
import typer
from rich.console import Console

from sdd_cli.services.metrics_handler import (
    _CollectorRef,
    _resolve_jsonl_path,
    _start_reload_worker,
    build_metrics_handler,
    build_summary_json_data,
    build_summary_table,
)
from sdd_cli.shared.contracts import (
    build_error_result,
    build_ok_result,
)
from sdd_cli.utils.output import emit_json, is_json_mode

app = typer.Typer(help="Token economy metrics commands")
console = Console()

_DEFAULT_METRICS_PORT = 9090


@app.callback()
def _() -> None:
    """Token economy metrics and Prometheus exposition."""


def _is_json_mode(ctx: typer.Context) -> bool:
    """Check if --json global flag is set via context params."""
    if ctx is not None and isinstance(getattr(ctx, "obj", None), dict):
        return is_json_mode(ctx)
    return is_json_mode(click.get_current_context(silent=True))


@app.command()
def summary(
    ctx: typer.Context,
    jsonl: Path = typer.Option(
        None, help="Path to events JSONL (auto-detected if omitted)"
    ),
    last_hours: int = typer.Option(
        None, "--last-hours", "-n", help="Limit to last N hours"
    ),
) -> None:
    """Print token economy summary table."""
    from sdd_runtime.metrics import TokenEconomyCollector
    from sdd_runtime.reader import TelemetryReader

    # Resolve JSONL path
    jsonl_path = _resolve_jsonl_path(jsonl)

    output_json = _is_json_mode(ctx)

    if not jsonl_path.exists():
        if output_json:
            data: dict[str, Any] = {"exit_code": 1}
            payload = build_error_result(
                "metrics summary",
                code="events_file_not_found",
                message=f"Events file not found: {jsonl_path}",
                data=data,
            )
            emit_json(payload, err=True)
        else:
            console.print(
                f"[red]Error:[/red] Events file not found: {jsonl_path}", style="bold"
            )
        raise typer.Exit(1)

    # Load and process events
    try:
        reader = TelemetryReader(jsonl_path)
        collector = TokenEconomyCollector.from_reader(reader)
        snap = collector.snapshot()
    except Exception as exc:
        if output_json:
            data = {"exit_code": 1}
            payload = build_error_result(
                "metrics summary",
                code="metrics_load_failed",
                message=f"Error loading events: {exc}",
                data=data,
            )
            emit_json(payload, err=True)
        else:
            console.print(f"[red]Error loading events:[/red] {exc}", style="bold")
        raise typer.Exit(1) from None

    # JSON output mode (machine-readable envelope).
    if output_json:
        data = build_summary_json_data(snap)
        payload = build_ok_result("metrics summary", data)
        emit_json(payload)
        return

    console.print(build_summary_table(snap))

    # Budget utilization indicator
    util_pct = snap.budget_utilization_pct
    if util_pct >= 100:
        color = "red"
        status = "🔴 BREACH"
    elif util_pct >= 90:
        color = "yellow"
        status = "🟡 WARNING (>90%)"
    else:
        color = "green"
        status = "🟢 OK"

    console.print(
        f"\nBudget utilization: [{color}]{util_pct:.1f}%[/{color}] {status}",
        style="bold",
    )

    # Event counts
    console.print(
        f"\nEvent summary: {snap.warn_count} warns | {snap.breach_count} breaches | {snap.retry_cap_count} retry caps",
    )


@app.command()
def serve(  # noqa: C901
    port: int = typer.Option(
        int(os.environ.get("SDD_METRICS_PORT", _DEFAULT_METRICS_PORT)),
        "--port",
        "-p",
        help="Port to expose /metrics on (default: SDD_METRICS_PORT or 9090)",
    ),
    jsonl: Path = typer.Option(
        None, help="Path to events JSONL (auto-detected if omitted)"
    ),
    refresh: int = typer.Option(
        30,
        "--refresh",
        "-r",
        help="Seconds between JSONL reload cycles (default: 30)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        help="Emit canonical JSON envelope for startup failures.",
    ),
) -> None:
    """Start Prometheus metrics scrape endpoint (foreground, Ctrl+C to stop)."""
    from sdd_runtime.metrics import TokenEconomyCollector
    from sdd_runtime.reader import TelemetryReader

    # Resolve JSONL path
    jsonl_path = _resolve_jsonl_path(jsonl)

    if not jsonl_path.exists():
        if json_output:
            data = {"events_file": str(jsonl_path), "port": port, "exit_code": 1}
            payload = build_error_result(
                "metrics serve",
                data,
                code="events_file_not_found",
                message=f"Events file not found: {jsonl_path}",
            )
            emit_json(payload, err=True)
        else:
            console.print(
                f"[red]Error:[/red] Events file not found: {jsonl_path}", style="bold"
            )
        raise typer.Exit(1)

    # Build initial collector
    try:
        reader = TelemetryReader(jsonl_path)
        collector = TokenEconomyCollector.from_reader(reader)
    except Exception as exc:
        if json_output:
            data = {"events_file": str(jsonl_path), "port": port, "exit_code": 1}
            payload = build_error_result(
                "metrics serve",
                data,
                code="metrics_load_failed",
                message=f"Error loading events: {exc}",
            )
            emit_json(payload, err=True)
        else:
            console.print(f"[red]Error loading events:[/red] {exc}", style="bold")
        raise typer.Exit(1) from None

    # Shared runtime state used by HTTP handler and reload worker.
    collector_ref = _CollectorRef(collector)
    stop_event = threading.Event()

    MetricsHandler = build_metrics_handler(collector_ref)

    # Bind first. In restricted environments this can fail (PermissionError/OSError),
    # and we must fail fast before starting background workers.
    try:
        server = http.server.HTTPServer(("", port), MetricsHandler)
    except OSError as exc:
        if json_output:
            data = {"events_file": str(jsonl_path), "port": port, "exit_code": 1}
            payload = build_error_result(
                "metrics serve",
                data,
                code="metrics_bind_failed",
                message=f"Cannot bind to port {port}: {exc}",
            )
            emit_json(payload, err=True)
        else:
            console.print(
                f"[red]Error starting metrics server:[/red] cannot bind to port {port}: {exc}",
                style="bold",
            )
        raise typer.Exit(1) from None

    reload_thread = _start_reload_worker(
        jsonl_path=jsonl_path,
        refresh=refresh,
        collector_ref=collector_ref,
        stop_event=stop_event,
    )
    server.timeout = 1.0
    console.print(
        f"[green][SDD][/green] Metrics endpoint: [cyan]http://localhost:{port}/metrics[/cyan]"
    )
    console.print(
        f"[yellow]Reloading JSONL every {refresh}s. Press Ctrl+C to stop.[/yellow]"
    )

    try:
        while not stop_event.is_set():
            server.handle_request()
    except KeyboardInterrupt:
        console.print("[yellow]\n[SDD] Metrics server stopped.[/yellow]")
        raise typer.Exit(0) from None
    finally:
        stop_event.set()
        server.server_close()
        reload_thread.join(timeout=max(2, refresh + 1))
