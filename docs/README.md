# SDD Harness — Documentation

Documentacao estruturada por **papel no sistema**, nao por audiencia. Otimizada para consumo eficiente por agentes de IA com carregamento por demanda.

## Client Onboarding (Official)

Use one cross-platform command as the primary installation path:

```bash
uv tool install sdd-cli
```

Then follow the complete guide:

- [`guides/CLIENT_ONBOARDING.md`](./guides/CLIENT_ONBOARDING.md)

## Start Here

- **Agentes de IA** → [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md)
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

## Quatro pilares

1. **`spec/` — Fonte de Verdade**
   - Conhecimento, mandatos, ADRs e regras de dominio. Contém `canonical/`, `decisions/`, `guides/` e `reference/`.
   - Agentes acessam via indices, raramente diretamente.

2. **`cognition/` — Tomada de Decisao**
   - Como o agente pensa. Contém `context-loading/`, `decision-models/` e `anti-patterns/`.

3. **`runtime/` — Execucao e Acao**
   - Como o agente age. Comece aqui: [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md).
   - Protocolo operacional: [`runtime/protocols/AGENT_RUNTIME_PROTOCOL.md`](./runtime/protocols/AGENT_RUNTIME_PROTOCOL.md).

4. **`indices/` — Recuperacao e Busca**
   - Ponteiros otimizados para reduzir custo de busca. Ver [`guides/TECHNICAL_GUIDE.md`](./guides/TECHNICAL_GUIDE.md).

> Nunca carregar a documentacao inteira. Sempre usar path-based context loading via Master Index.
