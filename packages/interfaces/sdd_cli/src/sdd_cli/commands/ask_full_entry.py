"""Top-level `sdd ask-full` command entrypoint (no duplicated subcommand token)."""

import typer

from sdd_cli.utils.output import is_json_mode

app = typer.Typer(help="Query SDD governance context with full telemetry.")


@app.callback(invoke_without_command=True)
def ask_full(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    log_path: str | None = typer.Option(
        None, "--log-path", help="Custom compliance log path."
    ),
    log_format: str = typer.Option(
        "jsonl", "--log-format", help="Log format: jsonl or compact."
    ),
    tokens_input: int | None = typer.Option(
        None,
        "--tokens-input",
        help="LLM API input tokens (overrides SDD_TOKENS_INPUT).",
    ),
    tokens_output: int | None = typer.Option(
        None,
        "--tokens-output",
        help="LLM API output tokens (overrides SDD_TOKENS_OUTPUT).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        help="Emit canonical JSON envelope instead of plain-text output.",
    ),
) -> None:
    """Run governed ask-full query."""
    from sdd_cli.commands._ask_backend import ask_full_cmd

    ask_full_cmd(
        query=query,
        log_path=log_path,
        log_format=log_format,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        json_output=json_output or is_json_mode(ctx),
    )
