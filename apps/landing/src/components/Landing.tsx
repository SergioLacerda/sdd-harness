import React, { useState } from 'react';
import { Terminal } from './ds/Terminal';
import { GovernanceFooter } from './ds/GovernanceFooter';
import { LANDING_CONTENT, TERM_AUDIT, TERM_COMPILE, type Lang } from '../lib/i18n';
import {
  withGovernanceStats,
  PLACEHOLDER_GOVERNANCE_STATS,
  type GovernanceStats,
} from '../lib/governance-stats';

type Page = 'overview' | 'capabilities';
type CapTab = 'audit' | 'context' | 'runtime' | 'compile';

const BASE_URL = import.meta.env.BASE_URL;

interface LandingProps {
  stats?: GovernanceStats;
}

/**
 * The SDD Harness Selector landing page — "custody / guardian" direction.
 * Ported from `Selector Landing v4.dc.html`. Two top-level tabs (Overview /
 * Capabilities); Selector is a link out to the real, compiled Selector at
 * /selector/ rather than a third tab, per ADR
 * selector-landing-mkdocs-refinement-20260702 (no embedded Selector preview).
 * A subtle breathing halo + rotating ring + drifting motes around the header
 * mark; an external "Docs" link out to the MkDocs site (deployed alongside
 * this app at /docs/).
 */
export function Landing({ stats = PLACEHOLDER_GOVERNANCE_STATS }: LandingProps) {
  const [lang, setLang] = useState<Lang>('pt');
  const [page, setPage] = useState<Page>('overview');
  const [tab, setTab] = useState<CapTab>('audit');
  const c = LANDING_CONTENT[lang];
  const termAuditLive = TERM_AUDIT.map((l) => ({ ...l, text: withGovernanceStats(stats, l.text) }));
  const termCompileLive = TERM_COMPILE.map((l) => ({ ...l, text: withGovernanceStats(stats, l.text) }));

  const navBtnStyle = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer', padding: '0 0 4px',
    fontFamily: 'inherit', fontSize: 13, letterSpacing: '.03em', textTransform: 'uppercase',
    color: active ? 'var(--ink-900)' : 'var(--ink-500)',
    borderBottom: `1px solid ${active ? 'var(--indigo-600)' : 'transparent'}`,
  });

  const articleTabStyle = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer', padding: '0 0 14px',
    fontFamily: 'var(--font-mono)', fontSize: 13, letterSpacing: '.03em', marginBottom: -1,
    color: active ? 'var(--ink-900)' : 'var(--ink-400)',
    borderBottom: `2px solid ${active ? 'var(--indigo-600)' : 'transparent'}`,
  });

  return (
    <div style={{ margin: '0 auto' }}>
      {/* NAV */}
      <div
        style={{
          position: 'sticky', top: 0, zIndex: 40, display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: 32, padding: '20px 32px', background: 'rgba(255,255,255,.94)', backdropFilter: 'blur(6px)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, position: 'absolute', left: 32 }}>
          <span style={{ position: 'relative', width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
            <span style={{ position: 'absolute', width: 44, height: 44, borderRadius: 999, background: 'radial-gradient(circle, rgba(68,83,189,.22) 0%, rgba(68,83,189,0) 70%)', animation: 'guardianHalo 6s ease-in-out infinite', pointerEvents: 'none' }} />
            <svg width={44} height={44} viewBox="0 0 44 44" style={{ position: 'absolute', animation: 'guardianRing 70s linear infinite', pointerEvents: 'none' }} aria-hidden="true">
              <circle cx={22} cy={22} r={21} fill="none" stroke="var(--indigo-200)" strokeWidth={1} strokeDasharray="1 5" />
            </svg>
            <span style={{ position: 'absolute', left: -3, top: 6, width: 3, height: 3, borderRadius: 999, background: 'var(--blue-500)', animation: 'guardianMote 8s ease-in-out infinite', animationDelay: '0s', pointerEvents: 'none' }} />
            <span style={{ position: 'absolute', right: -4, bottom: 8, width: 2.5, height: 2.5, borderRadius: 999, background: 'var(--green-500)', animation: 'guardianMote 9.5s ease-in-out infinite', animationDelay: '-3.5s', pointerEvents: 'none' }} />
            <span style={{ position: 'absolute', left: 6, top: -4, width: 3, height: 3, borderRadius: 999, background: 'var(--indigo-400)', animation: 'guardianMote 6.5s ease-in-out infinite', animationDelay: '-1.5s', pointerEvents: 'none' }} />
            <span style={{ position: 'absolute', right: 8, bottom: -3, width: 3, height: 3, borderRadius: 999, background: 'var(--blue-500)', animation: 'guardianMote 9s ease-in-out infinite', animationDelay: '-5s', pointerEvents: 'none' }} />
            <span style={{ position: 'absolute', left: '50%', top: -4, marginLeft: -1.25, width: 2.5, height: 2.5, borderRadius: 999, background: 'var(--green-500)', animation: 'guardianMote 7.8s ease-in-out infinite', animationDelay: '-2.4s', pointerEvents: 'none' }} />
            <span style={{ position: 'absolute', right: 2, top: -2, width: 2.5, height: 2.5, borderRadius: 999, background: 'var(--indigo-300)', animation: 'guardianMote 8s ease-in-out infinite', animationDelay: '-6.2s', pointerEvents: 'none' }} />
            <img src={`${BASE_URL}assets/sdd-mark.svg`} width={28} height={28} alt="" style={{ position: 'relative', zIndex: 1 }} />
          </span>
          <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--ink-900)' }}>
            SDD<span style={{ fontWeight: 400, color: 'var(--ink-500)' }}>Harness</span>
          </span>
        </span>

        <nav style={{ display: 'flex', gap: 30, fontSize: 13, letterSpacing: '.03em', textTransform: 'uppercase', alignItems: 'center' }}>
          <button type="button" onClick={() => setPage('overview')} style={navBtnStyle(page === 'overview')}>{c.navOverview}</button>
          <button type="button" onClick={() => setPage('capabilities')} style={navBtnStyle(page === 'capabilities')}>{c.navCapabilities}</button>
          <a href={`${BASE_URL}selector/`} style={navBtnStyle(false)}>Selector</a>
          <span style={{ width: 1, height: 14, background: 'var(--border-strong)' }} />
          {/* MkDocs documentation is deployed alongside this app (see the CI/CD workflow) at /docs/ */}
          <a href={`${BASE_URL}docs/`} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: 'var(--ink-500)', textDecoration: 'none', fontSize: 13, letterSpacing: '.03em', textTransform: 'uppercase' }}>
            {c.navDocs}<span style={{ fontSize: 11 }}>↗</span>
          </a>
        </nav>

        <div style={{ position: 'absolute', right: 32, display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ display: 'inline-flex', gap: 2, fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.04em' }}>
            <button type="button" onClick={() => setLang('pt')} style={{ padding: '4px 9px', cursor: 'pointer', border: 'none', background: 'transparent', color: lang === 'pt' ? 'var(--ink-900)' : 'var(--ink-400)', borderBottom: `1px solid ${lang === 'pt' ? 'var(--indigo-600)' : 'transparent'}` }}>PT-BR</button>
            <button type="button" onClick={() => setLang('en')} style={{ padding: '4px 9px', cursor: 'pointer', border: 'none', background: 'transparent', color: lang === 'en' ? 'var(--ink-900)' : 'var(--ink-400)', borderBottom: `1px solid ${lang === 'en' ? 'var(--indigo-600)' : 'transparent'}` }}>EN</button>
          </span>
        </div>
      </div>

      {/* OVERVIEW — hero + how it works */}
      {page === 'overview' && (
        <>
          <div style={{ background: 'var(--indigo-900)', padding: '96px 32px 80px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 14, marginBottom: 26 }}>
              <span style={{ width: 30, height: 1, background: 'rgba(255,255,255,.3)' }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, letterSpacing: '.22em', color: 'var(--indigo-200)', textTransform: 'uppercase' }}>{c.heroEyebrow}</span>
              <span style={{ width: 30, height: 1, background: 'rgba(255,255,255,.3)' }} />
            </div>
            <h1 style={{ margin: 0, maxWidth: 780, fontSize: 44, lineHeight: 1.18, letterSpacing: '-0.015em', fontWeight: 600, color: '#fff' }}>{c.heroTitle}</h1>
            <p style={{ margin: '24px 0 0', fontSize: 17, lineHeight: 1.65, color: 'var(--indigo-100)', maxWidth: 560 }}>{c.heroSub}</p>
            <div style={{ display: 'flex', gap: 14, marginTop: 34 }}>
              <a href={`${BASE_URL}selector/`} style={{ display: 'inline-flex', alignItems: 'center', height: 46, padding: '0 26px', borderRadius: 3, background: '#fff', color: 'var(--indigo-800)', fontSize: 14, fontWeight: 600, letterSpacing: '.02em', textDecoration: 'none', whiteSpace: 'nowrap' }}>{c.heroCtaPrimary}</a>
              <button type="button" onClick={() => setPage('capabilities')} style={{ display: 'inline-flex', alignItems: 'center', height: 46, padding: '0 26px', borderRadius: 3, background: 'transparent', border: '1px solid rgba(255,255,255,.35)', color: '#fff', fontSize: 14, fontWeight: 600, letterSpacing: '.02em', cursor: 'pointer', whiteSpace: 'nowrap' }}>{c.heroCtaSecondary}</button>
            </div>

            {/* custody seal */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 26, marginTop: 68 }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#cdd6ff' }}>{withGovernanceStats(stats, 'M001–M{{MCOUNT}}')}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.08em', color: 'var(--indigo-300)', textTransform: 'uppercase', marginTop: 2 }}>{c.legendMandate}</div>
              </div>
              <svg width={132} height={132} viewBox="0 0 200 200" aria-hidden="true">
                <circle cx={100} cy={100} r={94} fill="none" stroke="rgba(255,255,255,.14)" strokeWidth={1} />
                <circle cx={100} cy={100} r={76} fill="none" stroke="rgba(255,255,255,.22)" strokeWidth={1} />
                <path d="M100 176 A76 76 0 0 1 100 24" fill="none" stroke="var(--blue-500)" strokeWidth={1.8} />
                <path d="M100 24 A76 76 0 0 1 100 176" fill="none" stroke="var(--green-500)" strokeWidth={1.8} />
                <line x1={100} y1={24} x2={100} y2={176} stroke="rgba(255,255,255,.25)" strokeWidth={1} />
                <line x1={24} y1={100} x2={176} y2={100} stroke="rgba(255,255,255,.16)" strokeWidth={1} />
                <line x1={100} y1={14} x2={100} y2={24} stroke="rgba(255,255,255,.4)" strokeWidth={1.4} />
                <line x1={100} y1={176} x2={100} y2={186} stroke="rgba(255,255,255,.4)" strokeWidth={1.4} />
                <line x1={14} y1={100} x2={24} y2={100} stroke="rgba(255,255,255,.4)" strokeWidth={1.4} />
                <line x1={176} y1={100} x2={186} y2={100} stroke="rgba(255,255,255,.4)" strokeWidth={1.4} />
                <circle cx={100} cy={100} r={3} fill="#fff" />
              </svg>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#cdd6ff' }}>{withGovernanceStats(stats, 'G01–G{{GCOUNT}}')}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.08em', color: 'var(--indigo-300)', textTransform: 'uppercase', marginTop: 2 }}>{c.legendGuideline}</div>
              </div>
            </div>

            <div style={{ marginTop: 40 }}>
              <GovernanceFooter drift="clean" governance="active" profile="client" surface="dark" />
            </div>
          </div>

          {/* HOW IT WORKS */}
          <div style={{ maxWidth: 780, margin: '0 auto', padding: '80px 32px 80px' }}>
            <div style={{ textAlign: 'center', marginBottom: 40 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.18em', textTransform: 'uppercase', color: 'var(--ink-400)', marginBottom: 12 }}>{c.howEyebrow}</div>
              <h2 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: '-0.015em', color: 'var(--ink-900)' }}>{c.howTitle}</h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {c.steps.map((s) => (
                <div key={s.roman} style={{ display: 'grid', gridTemplateColumns: '52px 1fr', gap: 22, padding: '22px 0', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ width: 40, height: 40, borderRadius: 999, border: '1px solid var(--indigo-300)', color: 'var(--indigo-700)', fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{s.roman}</div>
                  <div>
                    <h3 style={{ margin: '0 0 5px', fontSize: 16, fontWeight: 600, color: 'var(--ink-900)' }}>{s.t}</h3>
                    <p style={{ margin: '0 0 10px', fontSize: 14, lineHeight: 1.55, color: 'var(--text-muted)', maxWidth: 560 }}>{withGovernanceStats(stats, s.d)}</p>
                    <code style={{ display: 'inline-block', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--indigo-700)', background: 'var(--surface-sunken)', borderRadius: 4, padding: '6px 10px' }}>{s.cmd}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* CAPABILITIES — charter articles */}
      {page === 'capabilities' && (
        <div style={{ maxWidth: 940, margin: '0 auto', padding: '88px 32px 72px' }}>
          <div style={{ textAlign: 'center', marginBottom: 46 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.18em', textTransform: 'uppercase', color: 'var(--ink-400)', marginBottom: 12 }}>{c.capEyebrow}</div>
            <h2 style={{ margin: '0 0 14px', fontSize: 30, fontWeight: 600, letterSpacing: '-0.015em', color: 'var(--ink-900)' }}>{c.capTitle}</h2>
            <p style={{ margin: '0 auto', fontSize: 16, lineHeight: 1.6, color: 'var(--ink-600)', maxWidth: 560 }}>{c.capSub}</p>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: 36, borderBottom: '1px solid var(--border)', marginBottom: 40 }}>
            <button type="button" onClick={() => setTab('audit')} style={articleTabStyle(tab === 'audit')}>I. {c.tabAudit}</button>
            <button type="button" onClick={() => setTab('context')} style={articleTabStyle(tab === 'context')}>II. {c.tabContext}</button>
            <button type="button" onClick={() => setTab('runtime')} style={articleTabStyle(tab === 'runtime')}>III. {c.tabRuntime}</button>
            <button type="button" onClick={() => setTab('compile')} style={articleTabStyle(tab === 'compile')}>IV. {c.tabCompile}</button>
          </div>

          {tab === 'audit' && (
            <div>
              <h3 style={{ margin: '0 0 10px', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink-900)', textAlign: 'center' }}>{c.auditTitle}</h3>
              <p style={{ margin: '0 auto 28px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-600)', maxWidth: 640, textAlign: 'center' }}>{c.auditBody}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 36, alignItems: 'start' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {c.zones.map((z) => (
                    <div key={z.zone} style={{ display: 'grid', gridTemplateColumns: '90px 76px 1fr', gap: 14, alignItems: 'center', padding: '13px 0', borderTop: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-800)', display: 'flex', alignItems: 'center', gap: 7 }}>
                        <span style={{ width: 6, height: 6, borderRadius: 999, background: z.dot }} />{z.zone}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>{z.range}</span>
                      <span style={{ fontSize: 13, color: 'var(--ink-600)', lineHeight: 1.4 }}>{z.action}</span>
                    </div>
                  ))}
                  <p style={{ margin: '16px 0 0', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-faint)' }}>{c.auditCaption}</p>
                </div>
                <Terminal title="sdd — audit" chrome lines={termAuditLive} />
              </div>
            </div>
          )}

          {tab === 'context' && (
            <div>
              <h3 style={{ margin: '0 0 10px', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink-900)', textAlign: 'center' }}>{c.ctxTitle}</h3>
              <p style={{ margin: '0 auto 28px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-600)', maxWidth: 640, textAlign: 'center' }}>{c.ctxBody}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 36, alignItems: 'start' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {c.ctxPoints.map((p) => (
                    <div key={p.k} style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 14 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 4 }}>{p.k}</div>
                      <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--text-muted)' }}>{p.d}</div>
                    </div>
                  ))}
                </div>
                <div style={{ background: 'var(--term-bg)', borderRadius: 4, border: '1px solid var(--term-border)', padding: '18px 20px' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--term-dim)', marginBottom: 12 }}>.sdd/task-context.json</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {c.cacheFields.map((f) => (
                      <div key={f.key}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--term-blue)' }}>{f.key}</span>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--term-dim)', lineHeight: 1.5 }}>{f.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === 'runtime' && (
            <div>
              <h3 style={{ margin: '0 0 10px', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink-900)', textAlign: 'center' }}>{c.crossTitle}</h3>
              <p style={{ margin: '0 auto 30px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-600)', maxWidth: 640, textAlign: 'center' }}>{c.crossBody}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 24, alignItems: 'center' }}>
                <div style={{ border: '1px solid var(--border)', borderRadius: 4, padding: 20 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--blue-700)', marginBottom: 10 }}>{c.cellA}</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 4 }}>{c.cellAgent}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>.sdd/task-context.json</div>
                  <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{c.cellIsolated}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minWidth: 110 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-400)' }}>M015</span>
                  <span style={{ width: 1, height: 34, background: 'var(--border-strong)' }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-faint)', textAlign: 'center' }}>{c.handshake}</span>
                </div>
                <div style={{ border: '1px solid var(--border)', borderRadius: 4, padding: 20 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--green-700)', marginBottom: 10 }}>{c.cellB}</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 4 }}>{c.cellAgent}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>.sdd/task-context.json</div>
                  <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{c.cellIsolated}</div>
                </div>
              </div>
              <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '16px 20px', borderTop: '1px solid var(--border-subtle)' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--ink-500)' }}>M019</span>
                <span style={{ fontSize: 14, color: 'var(--ink-700)', lineHeight: 1.5, textAlign: 'center' }}>{c.federation}</span>
              </div>
            </div>
          )}

          {tab === 'compile' && (
            <div>
              <h3 style={{ margin: '0 0 10px', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink-900)', textAlign: 'center' }}>{c.compTitle}</h3>
              <p style={{ margin: '0 auto 28px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-600)', maxWidth: 640, textAlign: 'center' }}>{c.compBody}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 36, alignItems: 'start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 22 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-700)', border: '1px solid var(--border)', padding: '8px 12px', borderRadius: 3 }}>selector-selection.json</span>
                    <span style={{ color: 'var(--text-faint)' }}>→</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-700)', border: '1px solid var(--border)', padding: '8px 12px', borderRadius: 3 }}>compile --optimize</span>
                    <span style={{ color: 'var(--text-faint)' }}>→</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-700)', border: '1px solid var(--border)', padding: '8px 12px', borderRadius: 3 }}>.sdd/compiled/</span>
                  </div>
                  <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
                    {c.compStats.map((s) => (
                      <div key={s.label}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 21, fontWeight: 600, color: s.color }}>{withGovernanceStats(stats, s.value)}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <Terminal title="sdd — compile" chrome lines={termCompileLive} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* SELECTOR CTA — links out to the real, compiled Selector at /selector/.
          Deliberately not an embedded preview: the Selector is owned and
          generated by sdd_wizard, and this landing page must not become a
          second, drifting implementation of it. */}
      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '48px 32px 80px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.18em', textTransform: 'uppercase', color: 'var(--ink-400)', marginBottom: 12 }}>{c.previewEyebrow}</div>
        <h2 style={{ margin: '0 0 10px', fontSize: 28, fontWeight: 600, letterSpacing: '-0.015em', color: 'var(--ink-900)' }}>{c.previewTitle}</h2>
        <p style={{ margin: '0 auto 24px', fontSize: 15, lineHeight: 1.6, color: 'var(--ink-600)', maxWidth: 560 }}>{c.previewSub}</p>
        <a href={`${BASE_URL}selector/`} style={{ display: 'inline-flex', alignItems: 'center', height: 46, padding: '0 26px', borderRadius: 3, background: 'var(--indigo-700)', color: '#fff', fontSize: 14, fontWeight: 600, letterSpacing: '.02em', textDecoration: 'none', whiteSpace: 'nowrap' }}>{c.heroCtaPrimary}</a>
      </div>

      {/* FOOTER — mirrors hero, always visible */}
      <div style={{ background: 'var(--indigo-900)', padding: '40px 32px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, textAlign: 'center' }}>
        <img src={`${BASE_URL}assets/sdd-mark.svg`} width={26} height={26} alt="" />
        <span style={{ fontSize: 13, color: 'var(--indigo-100)', fontFamily: 'var(--font-mono)' }}>{c.footerNote}</span>
        <GovernanceFooter drift="clean" governance="active" profile="client" surface="dark" />
      </div>
    </div>
  );
}
