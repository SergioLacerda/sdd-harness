# Context Loader Strategy (PATH Routing)

## Regra de Ouro
> Nunca carregue documentação completa.
> Sempre use context loading baseado em PATH.

---

## Classificação de Tarefa → PATH

| Situação | PATH | Carga de Contexto |
|---|---|---|
| Bug isolado e reproduzível | PATH A | Mínima (1 camada) |
| Feature nova, escopo simples (1-2 módulos) | PATH B | Canônico + guias relevantes |
| Feature complexa, cross-layer, ADR necessário | PATH C | Completo |
| Dois trabalhos independentes simultâneos | PATH D | Isolada por thread |
| Bug crítico em produção, precisa de hotfix | PATH E | Emergência mínima |
| Melhoria interna sem mudança de comportamento | PATH F | Canônico + convenções |

---

## Estratégia de Carga por PATH

### PATH A (Bugfix)
```
if PATH_A:
    load spec/canonical/<affected_layer>
    load indices/search-keywords.md
```

### PATH B (Simple Feature)
```
if PATH_B:
    load spec/canonical/  # core do domínio alvo
    load spec/guides/<relevant_area>
    load indices/spec-canonical-index.md
```

### PATH C (Complex Feature)
```
if PATH_C:
    load spec/canonical/  # completo
    load spec/decisions/  # ADRs relevantes
    load cognition/decision-models/
    load indices/  # todos
```

### PATH D (Parallel)
```
if PATH_D:
    thread_1: load spec/canonical/<domain_A>
    thread_2: load spec/canonical/<domain_B>
    # Contextos isolados — sem sobreposição
```

### PATH E (Hotfix)
```
if PATH_E:
    load spec/canonical/<affected_layer>  # mínimo absoluto
    load runtime/emergency/<runbook>
    # Prioridade: velocidade + segurança
```

### PATH F (Refactor)
```
if PATH_F:
    load spec/canonical/<scope>
    load spec/decisions/  # verificar ADRs protegidos
    # Baseline de testes ANTES de qualquer mudança
```

---

## Heurísticas de Decisão

- **Teste falhou?** → PATH A
- **Feature nova, apenas 1 módulo?** → PATH B
- **Feature nova, múltiplos módulos ou decisão arquitetural?** → PATH C
- **Dois trabalhos com zero sobreposição?** → PATH D
- **Produção quebrada agora?** → PATH E
- **Código funciona, mas precisa de clareza?** → PATH F

---

## 🛠️ World-Class Context Management

To ensure maximum reasoning quality, follow these advanced protocols:

| Framework | Purpose | Key Metric |
|---|---|---|
| [CONTEXT_BUDGET.md](./CONTEXT_BUDGET.md) | Token economy & Reasoning space | Keep Docs+Code < 70% |
| [CONTEXT_POISONING.md](./CONTEXT_POISONING.md) | Conflict & Stale doc prevention | Prioritize `spec/canonical/` |
| [CONTEXT_VERIFICATION.md](./CONTEXT_VERIFICATION.md) | Sufficiency & Blind spot check | Pass the "Anchor Test" |

---

## 🚦 Implementation Heurísticas

- **Rule of Thumb**: It is better to load too little context and expand later, than to load too much and "poison" the reasoning window.
- **Dynamic Expansion**: If a missing dependency is found during execution, pause and load only that specific file (see `CONTEXT_VERIFICATION.md`).

---

## Referências
- PATHs detalhados: [`runtime/paths/`](../../runtime/paths/)
- Índice de PATHs: [`indices/path-index.md`](../../indices/path-index.md)
- Anti-Overload: [`../anti-patterns/COGNITIVE_OVERLOAD.md`](../anti-patterns/COGNITIVE_OVERLOAD.md)
