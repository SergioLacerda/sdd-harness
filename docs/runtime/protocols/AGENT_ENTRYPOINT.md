> Layer: runtime - operational agent instructions

# AI Agent Entry Point

Guia operacional para Copilot e outros agentes que atuam neste workspace com governança SDD.

## Bootstrap mínimo (quando contexto está baixo)

Carregar nesta ordem:

1. **`.sdd/agent-instructions.md`** ← Fonte primária de governança (mandatos + autoavaliação)
2. [docs/guides/TECHNICAL_GUIDE.md](../../guides/TECHNICAL_GUIDE.md)
3. [docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md](./AGENT_RUNTIME_PROTOCOL.md)

---

## Mandatos obrigatórios

O arquivo `.sdd/agent-instructions.md` fornece o **índice de mandatos com micro-descrição**.

| Mandato | Resumo | Detalhes completos (sob demanda) |
|---------|--------|----------------------------------|
| M001 — Clean Architecture | Layers obrigatórias, sem imports cruzados | [CLEAN_ARCHITECTURE.md](../../spec/canonical/features/CLEAN_ARCHITECTURE.md) |
| M002 — TDD | Cobertura > 80%, pytest, mocks só na infra | [TDD.md](../../spec/canonical/features/TDD.md) |
| M003 — Context Awareness | Leitura sob demanda, contexto mínimo | `docs/spec/canonical/core/mandates/M003_CONTEXT_AWARENESS.md` |

> **Padrão de leitura sob demanda:** Leia o índice em `.sdd/agent-instructions.md`. Se o resumo do mandato **não** for suficiente para a sua tarefa atual → execute uma tool call para ler o detalhamento no arquivo de referência acima.

## SELF-EVALUATION (auto-avaliação obrigatória)

Antes de executar qualquer ação no workspace:

- **Confiante** que a ação respeita os mandatos listados acima → **Proceda.**
- **NÃO confiante** ou sem certeza sobre os detalhes técnicos → **Leia `.sdd/compiled/governance-core.json` antes de continuar.**

## Strict Auto-Fix Hygiene (Mandatory)

```bash
ruff check --fix .
ruff format .
ruff check .
mypy .
pytest
```

Revalidação pós auto-fix é obrigatória antes de entrega.

## Navegação adicional

- Navegação mestre: [docs/guides/TECHNICAL_GUIDE.md](../../guides/TECHNICAL_GUIDE.md)
- Cognição e modelos de decisão: `docs/cognition/INDEX.md`
- Protocolo de runtime: [docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md](./AGENT_RUNTIME_PROTOCOL.md)
