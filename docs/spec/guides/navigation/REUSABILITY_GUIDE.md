# 🔄 SPEC Reusability Guide

Como usar o framework SPEC (Sistema de Princípios e Especificações) em múltiplos projetos mantendo qualidade "world-class".

## 🎯 Princípios

1. **CANONICAL/ = Imutável** — Todas as regras, arquitetura, decisões compartilhadas
2. **custom/ = Especialização** — Cada projeto especializa estado e execução
3. **DRY = Verdadeiro** — ~30% duplicação (aceitável), vs 100% alternativas
4. **Zero Degradação de Qualidade** — Todos projetos = mesma qualidade

## 📋 Layers e Reusabilidade

### CANONICAL/ ✅ Reutilização: 100%
**Todos os projetos usam EXATAMENTE IGUAL**

```
/EXECUTION/spec/CANONICAL/
├── rules/                 # Aplicável a TODOS projetos
├── specifications/        # Aplicável a TODOS projetos
└── decisions/            # Histórico de TODOS projetos
```

**O que você PODE fazer:**
- ✅ Adicionar novas regras/specs em CANONICAL/ (todos herdam)
- ✅ Criar novo ADR em CANONICAL/ (aplicável globalmente)
- ✅ Expandir seções (e.g., observability.md para incluir mais projetos)

**O que você NÃO PODE fazer:**
- ❌ Modificar CANONICAL/ por projeto específico
- ❌ Ter "exceções" em um projeto
- ❌ Criar versões diferentes do mesmo arquivo

### custom/ 🎨 Reutilização: ~70%
**Cada projeto especializa conforme necessário**

```
/EXECUTION/spec/custom/
├── _TEMPLATE/           # Modelo para novos projetos (100% reutilizável)
└── [PROJECT_NAME]/      # Implementação específica
    ├── development/     # Estado de execução ativo (muda frequentemente)
    └── reality/         # Estado observado do projeto
```

**O que você PODE fazer:**
- ✅ Criar novo projeto copiando `_TEMPLATE/`
- ✅ Especializar `reality/` conforme estado do projeto
- ✅ Especializar `development/` conforme trabalho ativo

**O que você NÃO PODE fazer:**
- ❌ Contradizer CANONICAL/
- ❌ Copiar arquivos em vez de reutilizar template
- ❌ Criar dependências entre projetos

### ARCHIVE/ 📚 Reutilização: 0% (read-only)
**Histórico. Consultar, não modificar.**

```
/docs/ia/ARCHIVE/
├── working-sessions/     # Análises completadas
├── deprecated-decisions/ # ADRs antigas
└── project-migrations/   # Histórico de integrações
```

## 🚀 Como Iniciar Novo Projeto

### Step 1: Criar estrutura (2 min)
```bash
cp -r docs/ia/custom/_TEMPLATE docs/ia/custom/my-new-project
```

### Step 2: Preencher metadados (5 min)
```bash
# Editar:
# - docs/ia/custom/my-new-project/README.md (nome, descrição)
# - docs/ia/custom/my-new-project/INTEGRATION_RESULTS.md
```

### Step 3: Documentar estado atual (2-4 horas)
```bash
# Documentar:
# - reality/current-system-state/ (como é hoje)
# - reality/limitations/ (o que não funciona)
# - development/execution-state/_current.md (trabalho ativo)
```

### Step 4: Validar herança (30 min)
```bash
# Verificar:
# - Todos CANONICAL/ files presente e igual
# - Caminhos em ia-rules.md apontam para correto projeto
# - _INDEX.md lista novo projeto
```

**Tempo total:** ~4 horas (documentação é o bulk)

## 📊 Matriz de Reutilização

| Componente | Reuso | Nível | Projeto A | Projeto B | Projeto C |
|-----------|-------|-------|----------|----------|----------|
| ADRs | 100% | CANONICAL | ✅ Igual | ✅ Igual | ✅ Igual |
| Architecture | 100% | CANONICAL | ✅ Igual | ✅ Igual | ✅ Igual |
| Definition of Done | 100% | CANONICAL | ✅ Igual | ✅ Igual | ✅ Igual |
| Testing patterns | 100% | CANONICAL | ✅ Igual | ✅ Igual | ✅ Igual |
| Services description | ~30% | custom/ | ⚠️ Similar | ⚠️ Similar | ⚠️ Similar |
| Limitations | ~20% | custom/ | ❌ Diferente | ❌ Diferente | ❌ Diferente |
| Current work | 0% | custom/ | 🔄 Ativo | ⚠️ Pausado | ❌ Parado |

## 🔐 Enforcement Rules

### Regra 1: CANONICAL é imutável
```
❌ NÃO faça: git rm CANONICAL/rules/constitution.md
✅ FAÇA: Estender constitution.md com novas seções
```

### Regra 2: Cada projeto tem seu custom/
```
❌ NÃO faça: custom/[PROJECT_NAME]/reality/another-project-notes.md
✅ FAÇA: custom/[PROJECT_NAME]/reality/ SOMENTE [PROJECT_NAME]
```

### Regra 3: Template é sagrado
```
❌ NÃO faça: Modificar custom/_TEMPLATE/ para teste
✅ FAÇA: Usar custom/_TEMPLATE/ como modelo (cp -r)
```

### Regra 4: ARCHIVE nunca sofre push mutação
```
❌ NÃO faça: git push com mudanças em ARCHIVE/
✅ FAÇA: Mover arquivos de DEVELOPMENT/ → ARCHIVE/ (apenas completados)
```

### Regra 5: Melhorias vão em CANONICAL primeiro
```
❌ NÃO faça: Adicionar observability.md em custom/[PROJECT_NAME]/
✅ FAÇA: Adicionar CANONICAL/specifications/observability.md (todos herdam)
```

## 🎓 Exemplo: Integração Passo-a-Passo

### Novo projeto: "[PROJECT_NAME]"

#### 1. Setup
```bash
cd /home/my-projects/[PROJECT_NAME]

# Copiar SPEC
cp -r /home/[PROJECT_NAME]/docs/ia /docs/ia

# Estruturar para reutilização
mkdir -p /EXECUTION/spec/custom/_TEMPLATE/{development,reality}
```

#### 2. Herdar CANONICAL
```bash
# CANONICAL é 100% compartilhado (não altere!)
ls /EXECUTION/spec/CANONICAL/
# rules/ specifications/ decisions/
```

#### 3. Especializar custom/
```bash
# Documentar estado específico
echo "Game Master API - Serviços..." > /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/services.md

# Documentar trabalho ativo
echo "Thread 1: Implementar..." > /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md
```

#### 4. Validar
```bash
# Verificar que CANONICAL é igual
diff /EXECUTION/spec/CANONICAL/ /path/to/[PROJECT_NAME]/EXECUTION/spec/CANONICAL/
# Resultado: devem ser idênticos!
```

## ⚡ Melhorias World-Class (Roadmap)

Quando implementar melhorias em CANONICAL/, todos projetos herdam automaticamente:

- 🔄 Observabilidade: `CANONICAL/specifications/observability.md` (novo)
- 🔒 Segurança: `CANONICAL/rules/security-model.md` (novo)
- ⚡ Performance: `CANONICAL/specifications/performance.md` (novo)
- ✅ Compliance: `CANONICAL/specifications/compliance.md` (novo)

**Todos os projetos ganham isso de graça!**

## 📞 Suporte

### "Tenho dúvida sobre um ADR"
→ Veja `CANONICAL/decisions/ADR-*.md`

### "Preciso estender a arquitetura"
→ Leia `CANONICAL/specifications/architecture.md` first

### "Encontrei um bug/limitation"
→ Document em `custom/[PROJECT_NAME]/reality/limitations/`

### "Tenho uma melhoria global"
→ Propose ADR em `CANONICAL/decisions/` (aplica a todos)

---

**Framework:** SPEC v1.0
**Autoridade:** ADR + CANONICAL
**Última revisão:** 2026-04-19
