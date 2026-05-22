# SDD Harness — Documentation

Documentacao estruturada por **papel no sistema**, nao por audiencia. Otimizada para consumo eficiente por agentes de IA com carregamento por demanda.

## Start Here

- **Agentes de IA** → [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md)
- **Master Index** → [`indices/MASTER_INDEX.md`](./indices/MASTER_INDEX.md)
- **AI Agent Index** → [`.ai-index.md`](./.ai-index.md)

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
   - Ponteiros otimizados para reduzir custo de busca. Ver [`indices/MASTER_INDEX.md`](./indices/MASTER_INDEX.md).

> Nunca carregar a documentacao inteira. Sempre usar path-based context loading via Master Index.
