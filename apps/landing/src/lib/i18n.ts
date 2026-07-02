/**
 * Bilingual copy for the landing page (Landing.tsx). Ported from
 * `Selector Landing v4.dc.html`. Text tokens `{{FP}}`, `{{MCOUNT}}`,
 * `{{GCOUNT}}` are resolved against real governance stats via
 * `withGovernanceStats` (see governance-data.ts) rather than shipping
 * illustrative fingerprints/counts as production content.
 */

export type Lang = 'pt' | 'en';

export interface Step {
  roman: string;
  t: string;
  d: string;
  cmd: string;
}

export interface Zone {
  zone: string;
  range: string;
  action: string;
  dot: string;
}

export interface CtxPoint {
  k: string;
  d: string;
}

export interface CacheField {
  key: string;
  desc: string;
}

export interface CompStat {
  value: string;
  label: string;
  color: string;
}

export interface LandingCopy {
  navOverview: string; navCapabilities: string; navDocs: string;
  heroEyebrow: string; heroTitle: string; heroSub: string;
  heroCtaPrimary: string; heroCtaSecondary: string;
  legendMandate: string; legendGuideline: string;
  capEyebrow: string; capTitle: string; capSub: string;
  auditTitle: string; auditBody: string; auditCaption: string;
  ctxTitle: string; ctxBody: string;
  crossTitle: string; crossBody: string;
  cellA: string; cellB: string; cellAgent: string; cellIsolated: string; handshake: string; federation: string;
  compTitle: string; compBody: string;
  howEyebrow: string; howTitle: string;
  previewEyebrow: string; previewTitle: string; previewSub: string;
  footerNote: string;
  zones: Zone[];
  ctxPoints: CtxPoint[];
  cacheFields: CacheField[];
  steps: Step[];
  compStats: CompStat[];
  tabAudit: string; tabContext: string; tabRuntime: string; tabCompile: string;
}

export const LANDING_CONTENT: Record<Lang, LandingCopy> = {
  pt: {
    navOverview: 'Visão geral', navCapabilities: 'Capacidades', navDocs: 'Docs',
    heroEyebrow: 'CUSTÓDIA DE GOVERNANÇA',
    heroTitle: 'A guardiã silenciosa do contrato: vigilância contínua, do commit ao runtime.',
    heroSub: 'O harness mantém a custódia do que foi selecionado — aplica, audita e testemunha cada execução, sem substituir o julgamento do agente.',
    heroCtaPrimary: 'Abrir Selector', heroCtaSecondary: 'Ver capacidades',
    legendMandate: 'mandate · imutável', legendGuideline: 'guideline · flexível',
    capEyebrow: 'Capacidades', capTitle: 'Governança que roda junto com o agente',
    capSub: 'Além da seleção, o harness opera em runtime: audita continuamente, mantém contexto isolado por projeto, coordena agentes e compila contratos otimizados.',
    auditTitle: 'Auditoria: drift & economia de tokens',
    auditBody: 'sdd governance drift compara runtime × especificação; sdd economy report reporta a zona de budget. Eventos de telemetria armam em RED e disparam em BREACH.',
    auditCaption: 'circuit breaker: retries ≤ 3 · reflections ≤ 2 · entropy score por decisão',
    ctxTitle: 'Context-aware: cache isolado por projeto',
    ctxBody: 'Cada projeto mantém .sdd/task-context.json. O agente sincroniza (pre-flight) antes de agir e faz checkpoint ao fim de cada sub-tarefa — um loop de aprendizado que converge o estado e barra anti-padrões e memória obsoleta.',
    crossTitle: 'Cross-learning em runtime: células isoladas + handshake',
    crossBody: 'Cada repositório ou thread é uma célula context-aware separada (M003). Agentes trocam estado por handshake bidirecional (M015), sem um agente quebrar as premissas do outro. A federação de governança (M019) compartilha regras entre projetos sem contaminação cruzada.',
    cellA: 'célula · repo-a', cellB: 'célula · repo-b', cellAgent: 'agente governado',
    cellIsolated: 'Contexto project-scoped. Não referencia estado de outra célula.',
    handshake: 'handshake bidirecional',
    federation: 'M019 — federação de governança: regras compartilhadas entre projetos, cada célula preserva seu contexto.',
    compTitle: 'Compilação: otimizada, assinada, com fingerprint',
    compBody: 'Após a escolha, sdd governance compile transforma a seleção em contratos de runtime compactados para economia de token, assinados com Ed25519 e com fingerprint interno para detecção de drift.',
    howEyebrow: 'Como funciona', howTitle: 'Da seleção ao contrato de runtime',
    previewEyebrow: 'Preview interativo', previewTitle: 'Experimente o Selector',
    previewSub: 'Marque mandates e guidelines. Veja as dependências resolverem e a seleção se consolidar em selector-selection.json.',
    footerNote: 'Governança é mandatória e autoritativa a partir de .sdd.',
    zones: [
      { zone: 'GREEN', range: '< 70%', action: 'Prossegue normalmente.', dot: 'var(--green-500)' },
      { zone: 'YELLOW', range: '70–90%', action: 'Aplica compressão antes de carregar mais contexto.', dot: 'var(--amber-500)' },
      { zone: 'RED', range: '> 90%', action: 'Emite economy.budget.warn. Compressão obrigatória.', dot: 'var(--red-500)' },
      { zone: 'BREACH', range: '≥ 100%', action: 'Emite economy.budget.breach. Bloqueia carga de contexto.', dot: 'var(--red-700)' },
    ],
    ctxPoints: [
      { k: 'Pre-flight sync', d: 'Lê o cache antes de qualquer tarefa e sobrescreve memória obsoleta.' },
      { k: 'Checkpoint por sub-tarefa', d: 'Grava o estado ao fim de cada bloco lógico, junto do commit.' },
      { k: 'Isolamento por projeto', d: 'Cada repositório é uma célula; nunca mistura regras entre projetos.' },
    ],
    cacheFields: [
      { key: 'current_objective', desc: 'Objetivo de alto nível em curso.' },
      { key: 'active_subtask', desc: 'O que está sendo feito agora.' },
      { key: 'completed_milestones', desc: 'O que está 100% verificado.' },
      { key: 'shared_state', desc: 'Valores que múltiplos agentes precisam.' },
      { key: 'pending_risks', desc: 'Bloqueios e gotchas descobertos.' },
    ],
    steps: [
      { roman: 'I', t: 'Navegue o catálogo', d: 'Mandates imutáveis (M001–M{{MCOUNT}}) e guidelines (G01–G{{GCOUNT}}) com categoria e risco.', cmd: 'sdd governance list' },
      { roman: 'II', t: 'Selecione o que se aplica', d: 'Marque itens no Selector; dependências implícitas são resolvidas automaticamente.', cmd: 'selector-selection.json' },
      { roman: 'III', t: 'Compile os contratos', d: 'A seleção vira contratos fail-closed, compactados e assinados com fingerprint.', cmd: 'sdd governance compile' },
      { roman: 'IV', t: 'Audite o drift', d: 'O harness compara runtime × especificação e registra evidência de compliance.', cmd: 'sdd governance drift' },
    ],
    compStats: [
      { value: '−63%', label: 'tokens após compactação', color: 'var(--green-600)' },
      { value: 'Ed25519', label: 'assinatura por contrato', color: 'var(--indigo-600)' },
      { value: '{{FP}}', label: 'fingerprint de drift', color: 'var(--blue-600)' },
    ],
    tabAudit: 'Auditoria', tabContext: 'Context-aware', tabRuntime: 'Cross-learning', tabCompile: 'Compilação',
  },
  en: {
    navOverview: 'Overview', navCapabilities: 'Capabilities', navDocs: 'Docs',
    heroEyebrow: 'GOVERNANCE CUSTODY',
    heroTitle: 'The contract’s quiet custodian: continuous vigilance, from commit to runtime.',
    heroSub: 'The harness holds custody of what was selected — enforcing, auditing, and witnessing every execution, without overriding the agent’s judgment.',
    heroCtaPrimary: 'Open Selector', heroCtaSecondary: 'See capabilities',
    legendMandate: 'mandate · immutable', legendGuideline: 'guideline · flexible',
    capEyebrow: 'Capabilities', capTitle: 'Governance that runs alongside the agent',
    capSub: 'Beyond selection, the harness operates at runtime: it audits continuously, keeps project-isolated context, coordinates agents, and compiles optimized contracts.',
    auditTitle: 'Audit: drift & token economy',
    auditBody: 'sdd governance drift compares runtime against the spec; sdd economy report reports the budget zone. Telemetry events arm at RED and fire at BREACH.',
    auditCaption: 'circuit breaker: retries ≤ 3 · reflections ≤ 2 · entropy score per decision',
    ctxTitle: 'Context-aware: project-isolated cache',
    ctxBody: 'Each project keeps .sdd/task-context.json. The agent syncs (pre-flight) before acting and checkpoints at the end of every sub-task — a learning loop that converges state and blocks anti-patterns and stale memory.',
    crossTitle: 'Runtime cross-learning: isolated cells + handshake',
    crossBody: 'Each repository or thread is a separate context-aware cell (M003). Agents exchange state via a bidirectional handshake (M015), without one agent breaking another’s assumptions. Governance federation (M019) shares rules across projects with no cross-contamination.',
    cellA: 'cell · repo-a', cellB: 'cell · repo-b', cellAgent: 'governed agent',
    cellIsolated: 'Project-scoped context. Never references another cell’s state.',
    handshake: 'bidirectional handshake',
    federation: 'M019 — governance federation: rules shared across projects, each cell preserves its own context.',
    compTitle: 'Compile: optimized, signed, fingerprinted',
    compBody: 'After selection, sdd governance compile turns the selection into runtime contracts compacted for token economy, signed with Ed25519 and carrying an internal fingerprint for drift detection.',
    howEyebrow: 'How it works', howTitle: 'From selection to runtime contract',
    previewEyebrow: 'Interactive preview', previewTitle: 'Try the Selector',
    previewSub: 'Check mandates and guidelines. Watch dependencies resolve and the selection consolidate into selector-selection.json.',
    footerNote: 'Governance is mandatory and authoritative from .sdd.',
    zones: [
      { zone: 'GREEN', range: '< 70%', action: 'Proceed normally.', dot: 'var(--green-500)' },
      { zone: 'YELLOW', range: '70–90%', action: 'Compress before loading more context.', dot: 'var(--amber-500)' },
      { zone: 'RED', range: '> 90%', action: 'Emit economy.budget.warn. Compression required.', dot: 'var(--red-500)' },
      { zone: 'BREACH', range: '≥ 100%', action: 'Emit economy.budget.breach. Block context loading.', dot: 'var(--red-700)' },
    ],
    ctxPoints: [
      { k: 'Pre-flight sync', d: 'Reads the cache before any task and overrides stale memory.' },
      { k: 'Per-subtask checkpoint', d: 'Writes state at the end of each logical block, next to the commit.' },
      { k: 'Project isolation', d: 'Each repo is a cell; rules never mix across projects.' },
    ],
    cacheFields: [
      { key: 'current_objective', desc: 'High-level goal being pursued.' },
      { key: 'active_subtask', desc: 'What is being worked on right now.' },
      { key: 'completed_milestones', desc: 'What is 100% verified.' },
      { key: 'shared_state', desc: 'Values multiple agents need to know.' },
      { key: 'pending_risks', desc: 'Blockers and gotchas discovered.' },
    ],
    steps: [
      { roman: 'I', t: 'Browse the catalog', d: 'Immutable mandates (M001–M{{MCOUNT}}) and guidelines (G01–G{{GCOUNT}}) with category and risk.', cmd: 'sdd governance list' },
      { roman: 'II', t: 'Select what applies', d: 'Check items in the Selector; implicit dependencies are resolved automatically.', cmd: 'selector-selection.json' },
      { roman: 'III', t: 'Compile the contracts', d: 'The selection becomes fail-closed, compacted contracts signed with a fingerprint.', cmd: 'sdd governance compile' },
      { roman: 'IV', t: 'Audit drift', d: 'The harness compares runtime against the spec and records compliance evidence.', cmd: 'sdd governance drift' },
    ],
    compStats: [
      { value: '−63%', label: 'tokens after compaction', color: 'var(--green-600)' },
      { value: 'Ed25519', label: 'signature per contract', color: 'var(--indigo-600)' },
      { value: '{{FP}}', label: 'drift fingerprint', color: 'var(--blue-600)' },
    ],
    tabAudit: 'Audit', tabContext: 'Context-aware', tabRuntime: 'Cross-learning', tabCompile: 'Compile',
  },
};

export const TERM_AUDIT = [
  { prompt: '$', text: 'sdd governance drift --profile client', tone: 'text' as const },
  { text: '✓ drift=clean · 0 violations', tone: 'green' as const },
  { text: '  fingerprint {{FP}}', tone: 'dim' as const },
  { text: '', tone: 'dim' as const },
  { prompt: '$', text: 'sdd economy report', tone: 'text' as const },
  { text: 'zone=YELLOW  budget=82%  retries=1/3', tone: 'amber' as const },
  { text: '! economy.budget.warn arms at >90%', tone: 'amber' as const },
  { text: '✓ governance=active', tone: 'green' as const },
];

export const TERM_COMPILE = [
  { prompt: '$', text: 'sdd governance compile --optimize', tone: 'text' as const },
  { text: '✓ 12 contracts compiled', tone: 'green' as const },
  { text: '✓ compacted −63% tokens', tone: 'green' as const },
  { text: '✓ signed (Ed25519)', tone: 'green' as const },
  { text: '  fingerprint {{FP}}', tone: 'dim' as const },
  { text: '→ .sdd/compiled/  (runtime-ready)', tone: 'dim' as const },
];
