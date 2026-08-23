# ADR-017: Token Economy Evolution (Hybrid Accounting)

## Status

Accepted

## Context

The SDD Governance framework previously used a simplistic token-count model for budget enforcement. However, this model does not reflect the economic reality of different LLM providers (OpenAI, Anthropic) where input and output tokens have different costs. Furthermore, it lacked observability into the actual USD spend, making it difficult for teams to manage costs across high-volume agentic sessions.

## Decision

We will evolve the `Token Economy` into a **Hybrid Accounting Model**.

### 1. Hybrid Tracking

The system will now track:

- **Input Tokens**: Tokens sent to the provider.
- **Output Tokens**: Tokens received from the provider.
- **Estimated Cost (USD)**: Calculated based on a per-model pricing registry.

### 2. Token Ledger

A stateful `TokenLedger` will be introduced to maintain a transactional history of consumption, categorized by purpose (e.g., `reasoning`, `tool_call`, `reflection`).

### 3. Graceful Degradation

Enforcement will move from a binary "fail-hard" to a tiered response:

- **Warning Zone (80%)**: Emit warning events and signal agents to be concise.
- **Critical Zone (95%)**: Enforce strict conciseness and potentially switch to lighter models (future expansion).
- **Breach Zone (100%)**: Halt execution and return a `BudgetBreachError` with partial results.

### 4. Integration

Budget limits will be formalized in the M015 Handshake Protocol, ensuring that agents are aware of their economic boundaries before execution starts.

## Consequences

- Increased precision in cost management.
- Better observability via OpenTelemetry (exporting USD costs).
- Slight overhead in tracking metadata for every LLM call.
