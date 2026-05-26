# LangGraph Demo — Tool Guardrail

Shows SDD blocking an unauthorized tool before a LangGraph graph executes.

## Run

```bash
# From repo root
uv run --extra examples-langgraph python examples/langgraph/demo_tool_guardrail.py
```

## What happens

1. A LangGraph agent node binds the `send_email` tool
2. SDD runtime API validates the tool list against the active mandate
3. `send_email` is not in the authorized tool set → `BLOCKED`
4. The graph is never invoked — demo exits 0

## Expected output

```
[SDD] Checking tool authorization...
[SDD] BLOCKED: tool 'send_email' violates mandate M-TOOLS-001 (unauthorized_tool_use)
[SDD] Graph execution prevented. Governance enforced.
```
