> Layer: runtime - operational agent instructions

# Agent Runtime Protocol

Protocolo operacional obrigatório para qualquer agente de IA que execute tarefas neste workspace.

## Fluxo de 7 fases

Todo trabalho — bug fix, feature, refactor, documentação — segue este fluxo. Não é opcional.

```
FASE 0: Verificar contexto e estado inicial
   ↓
FASE 1: Carregar regras e mandatos
   ↓
FASE 2: Verificar estado de execução (detectar conflitos)
   ↓
FASE 3: Escolher caminho: bug=A | simples=B | complexo=C | multi=D
   ↓
FASE 4: Carregar contexto específico da tarefa
   ↓
FASE 5: Implementar (código + testes, TDD)
   ↓
FASE 6: Validar (testes + definition of done)
   ↓
FASE 7: Checkpoint (documentar + entregar)
```

## Comandos obrigatórios por fase

### Fase 0 — Estado inicial

```bash
sdd runtime status --verbose   # Verificar saúde do workspace
sdd governance validate        # Confirmar integridade de governança
```

### Fase 1 — Regras e mandatos

**Bootstrap obrigatório:** Leia `.sdd/agent-instructions.md` primeiro.
Ele contém o índice de mandatos com micro-descrição e o bloco de **SELF-EVALUATION**.

- ✅ Confiante com os resumos → Proceda diretamente.
- ❌ Não confiante → Leia o detalhamento sob demanda:
  - [M001](../../spec/canonical/features/CLEAN_ARCHITECTURE.md) — Clean Architecture
  - [M002](../../spec/canonical/features/TDD.md) — TDD obrigatório
  - [M003](../../spec/canonical/core/mandates/M003_CONTEXT_AWARENESS.md) — Context Awareness

### Fase 5 — Implementação

```bash
sdd test run          # Rodar testes a cada mudança significativa
sdd lint run          # Lint antes de declarar pronto
```

### Fase 6 — Validação final

```bash
sdd test run                    # Suíte completa
sdd lint run                    # Qualidade estática
sdd governance validate         # Integridade de governança
sdd runtime status --verbose    # Estado final do workspace
```

## Gerenciamento de contexto (memória LLM)

| Fase | O que carregar | Propósito |
|------|---------------|-----------|
| Planejamento | [cognition/decision-models/](../../cognition/decision-models/) | Avaliar riscos e confiança |
| Execução | [cognition/decision-models/TASK_CLASSIFICATION.md](../../cognition/decision-models/TASK_CLASSIFICATION.md) | Selecionar PATH (A-F) adequado |
| Validação | [spec/canonical/specifications/definition_of_done.md](../../spec/canonical/specifications/definition_of_done.md) | Critérios de qualidade |

> Nunca carregar a documentação inteira. Usar sempre path-based context loading via Master Index.

## Referências

- Entrypoint: [AGENT_ENTRYPOINT.md](./AGENT_ENTRYPOINT.md)
- CLI Reference: [docs/spec/reference/commands/cli.md](../../spec/reference/commands/cli.md)
- Master Index: [docs/indices/MASTER_INDEX.md](../../indices/MASTER_INDEX.md)
- Definition of Done: [docs/spec/canonical/specifications/definition_of_done.md](../../spec/canonical/specifications/definition_of_done.md)
- PATHs operacionais: [docs/runtime/paths/](../paths/)
