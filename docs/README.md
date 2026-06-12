# SDD Harness — Documentation

Documentation structured by **role in the system**, not by audience. Optimized for efficient consumption by AI agents with on-demand loading.

## Client Onboarding (Official)

Use one cross-platform command as the primary installation path (no clone required —
uv fetches the source directly):

```bash
uv tool install "git+https://github.com/SergioLacerda/sdd-harness#subdirectory=packages/interfaces/sdd_cli"
```

Then follow the complete guide:

- [`guides/CLIENT_ONBOARDING.md`](./guides/CLIENT_ONBOARDING.md)

## Start Here

- **AI agents** → [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md)
- **Master navigation** → [`guides/TECHNICAL_GUIDE.md`](./guides/TECHNICAL_GUIDE.md)
- **AI agent bootstrap** → [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md)

## Navigation by intent

| You want to... | Start here |
|---|---|
| understand the system architecture | [`architecture/README.md`](./architecture/README.md) |
| read canonical contracts and mandates | [`guides/TECHNICAL_GUIDE.md`](./guides/TECHNICAL_GUIDE.md) |
| follow runtime entrypoints and protocol | [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md) |
| troubleshoot an operational issue | [`guides/TECHNICAL_GUIDE.md`](./guides/TECHNICAL_GUIDE.md) and [`guides/FAQ.md`](./guides/FAQ.md) |
| find a decision or history item | [`adr/INDEX.md`](./adr/INDEX.md) |

## Four pillars

1. **`spec/` — Source of Truth**
   - Knowledge, mandates, ADRs and domain rules. Contains `canonical/`, `decisions/`, `guides/` and `reference/`.
   - Agents access it via indices, rarely directly.

2. **`cognition/` — Decision Making**
   - How the agent thinks. Contains `context-loading/`, `decision-models/` and `anti-patterns/`.

3. **`runtime/` — Execution and Action**
   - How the agent acts. Start here: [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md).
   - Operational protocol: [`runtime/protocols/AGENT_RUNTIME_PROTOCOL.md`](./runtime/protocols/AGENT_RUNTIME_PROTOCOL.md).

4. **`indices/` — Retrieval and Search**
   - Optimized pointers to reduce search cost. See [`guides/TECHNICAL_GUIDE.md`](./guides/TECHNICAL_GUIDE.md).

> Never load the entire documentation. Always use path-based context loading via the Master Index.
