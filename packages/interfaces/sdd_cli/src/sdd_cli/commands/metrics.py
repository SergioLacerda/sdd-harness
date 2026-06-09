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
from rich.table import Table

from sdd_cli.services.metrics_handler import (
    _CollectorRef,
    _resolve_jsonl_path,
    _start_reload_worker,
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
        data = {
            "summary": {
                "total_tokens": snap.total_tokens_total,
                "total_cost_usd": round(snap.total_cost_usd, 4),
                "budget_utilization_pct": snap.budget_utilization_pct,
                "total_calls": snap.total_calls,
                "warn_count": snap.warn_count,
                "breach_count": snap.breach_count,
                "retry_cap_count": snap.retry_cap_count,
                "per_model": {
                    model: {
                        "tokens_input": m.tokens_input,
                        "tokens_output": m.tokens_output,
                        "tokens_total": m.tokens_total,
                        "cost_usd": round(m.cost_usd, 4),
                        "call_count": m.call_count,
                    }
                    for model, m in snap.per_model.items()
                },
            },
            "exit_code": 0,
        }
        payload = build_ok_result("metrics summary", data)
        emit_json(payload)
        return

    # Build summary table
    table = Table(title="Token Economy Summary")
    table.add_column("Model", style="cyan")
    table.add_column("Input Tokens", justify="right", style="magenta")
    table.add_column("Output Tokens", justify="right", style="magenta")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (USD)", justify="right", style="green")
    table.add_column("Calls", justify="right")

    # Per-model rows
    for model in sorted(snap.per_model.keys()):
        m = snap.per_model[model]
        table.add_row(
            model,
            str(m.tokens_input),
            str(m.tokens_output),
            str(m.tokens_total),
            f"${m.cost_usd:.4f}",
            str(m.call_count),
        )

    # Totals row
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{snap.total_tokens_input}[/bold]",
        f"[bold]{snap.total_tokens_output}[/bold]",
        f"[bold]{snap.total_tokens_total}[/bold]",
        f"[bold green]${snap.total_cost_usd:.4f}[/bold green]",
        f"[bold]{snap.total_calls}[/bold]",
    )

    console.print(table)

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
    from sdd_runtime.metrics import PrometheusTextRenderer, TokenEconomyCollector
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

    # HTTP request handler
    class MetricsHandler(http.server.BaseHTTPRequestHandler):
        def do_get(self) -> None:
            if self.path == "/metrics":
                # Render Prometheus text format
                snap = collector_ref.snapshot()
                renderer = PrometheusTextRenderer()
                prometheus_text = renderer.render(snap)

                self.send_response(200)
                self.send_header(
                    "Content-Type", "text/plain; version=0.0.4; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(prometheus_text)))
                self.end_headers()
                self.wfile.write(prometheus_text.encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Found\n")

        def log_message(self, format: str, *args: object) -> None:
            # Suppress default logging
            pass

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
