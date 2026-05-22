# SDD — FAQ de Posicionamento

---

## O que é o SDD?

SDD (Spec-Driven Development) é uma plataforma de **governança executável para agentes de IA**.

Ela atua na camada entre o input e o output do agente — antes que uma decisão se consolide em código, infraestrutura ou artefato — garantindo que o agente opere com o contexto correto, em conformidade com a arquitetura definida, e dentro dos mandates estabelecidos pelo time.

O problema que ele resolve é simples de enunciar e difícil de ignorar: **agentes sem governança executável tomam decisões inconsistentes entre sessões, ignoram ADRs já decididas, e acumulam drift arquitetural de forma silenciosa e progressiva.** O SDD torna esse drift detectável, auditável, e rejeitável automaticamente no CI.

---

## Com o que o SDD compete?

O SDD **não compete** com:
- Frameworks de gerenciamento de estado (Redux, RTK, Zustand)
- Ferramentas de scaffolding de CRUD (Rails, Django, CAVEMAN)
- Orquestradores de fluxo de agente (LangChain, AutoGen, CAMEL)
- Frameworks de componentes de UI

O SDD compete em um espaço específico e distinto:

| Domínio | O que o SDD entrega |
|---|---|
| **Governance executável** | Mandates compilados e validáveis, não apenas documentação |
| **Runtime awareness** | O agente conhece o estado do ambiente antes de agir |
| **Context routing** | Documentação indexada e servida sob demanda, não carregada em bloco |
| **Workflow orchestration** | CLI que abstrai e automatiza o setup completo do ambiente |
| **Architecture compliance** | Guardrails que detectam e registram desvios em tempo real |
| **Multi-agent operational alignment** | Todos os agentes e humanos operam sob o mesmo conjunto de regras |

---

## Como o SDD atua na prática?

O SDD opera **entre as iterações internas do agente** — entre input e output — em quatro eixos:

### 1. Governança forte
Mandates, guardrails, guidelines e ADRs são compilados em artefatos validáveis. O sistema detecta drift automaticamente e registra cada evento com `trace_id`, `timestamp` e estado (`HEALTHY`, `MISCONFIGURED`, `VIOLATION`). Nenhuma decisão do agente passa sem rastro auditável.

### 2. Qualidade de contexto
- **Handshake de inicialização** — o agente confirma que carregou o contexto correto antes de executar tarefas
- **Quiz interno de confiança** — mecanismo de auto-validação que reduz alucinação arquitetural
- **Detecção de drift** — o sistema compara o estado atual com o estado compilado e sinaliza divergências

### 3. Documentação otimizada para IA (4 camadas)

- **Camada I — Material comprimido:** conteúdo denso e estruturado para consumo de agente, não de humano
- **Camada II — Leitura sob demanda:** o agente acessa contexto pontualmente, em vez de carregar arquivos extensos no início de cada sessão. Reduz consumo de tokens diretamente.
- **Camada III — Índices reativos com path A/B/C/D:** o agente navega por caminhos de leitura otimizados conforme o tipo de tarefa
- **Camada IV — ADRs no contexto interno:** decisões arquiteturais já tomadas ficam disponíveis inline, evitando que o agente repita discussões resolvidas ou reverta escolhas consolidadas

### 4. CLI de abstração
A CLI automatiza configurações que exigiriam conhecimento técnico profundo da estrutura interna, tornando o SDD acessível sem acoplamento ao detalhe de implementação.

---

## No que o SDD é similar a ferramentas como CAVEMAN?

A similaridade está em um único ponto: **ambos abstraem conhecimento técnico de configuração de ambiente através de CLI**.

A diferença fundamental é o escopo:
- CAVEMAN e similares entregam o **setup inicial** — scaffolding, estrutura de projeto, boilerplate configurado
- O SDD entrega setup inicial **e** **conformidade contínua em runtime** — o ambiente valida sua própria arquitetura a cada operação

---

## Os mandates são configuráveis?

Os mandates têm três níveis:

- **OBRIGATÓRIO** — inegociável para o agente em runtime. O sistema detecta e registra qualquer desvio sem exceção. Não há bypass.
- **OPCIONAL** — ativável por configuração de workspace
- **CUSTOMIZÁVEL** — o comportamento base pode ser sobrescrito por variáveis do ambiente sem alterar a estrutura canônica

---

## O que acontece se eu rodar o wizard e importar o pacote completo?

Você recebe um ambiente funcional com governança pré-compilada e imediatamente validável — não apenas boilerplate. O pacote inclui:

- Mandates canônicos prontos (Clean Architecture, TDD, Context Awareness)
- Anti-patterns identificados e documentados para o agente evitar
- Guardrails configurados para detectar desvios automaticamente
- Trilha de telemetria ativa desde o primeiro comando
- Documentação indexada em quatro camadas para consumo eficiente por agentes

Padrões incluídos são **agnósticos de linguagem** — funcionam independentemente do stack.

---

## O que a telemetria entrega na prática?

Cada decisão relevante do agente gera um evento JSONL com `ts`, `event`, `command`, `state`, e `details`. Isso permite:

- **Auditoria completa** de cada sessão de agente
- **Detecção retroativa de drift** — você sabe quando e onde o desvio ocorreu
- **Gate de CI automatizado** — o pipeline pode falhar se a conformidade caiu abaixo do threshold
- **Rastreabilidade por `trace_id`** — cada operação é correlacionável de ponta a ponta
