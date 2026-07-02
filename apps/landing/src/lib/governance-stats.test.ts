import { describe, expect, it } from 'vitest';
import {
  PLACEHOLDER_GOVERNANCE_STATS,
  withGovernanceStats,
  type GovernanceStats,
} from './governance-stats';

const STATS: GovernanceStats = {
  mandatesCount: 16,
  guidelinesCount: 23,
  fingerprintShort: 'f95a…b222',
  available: true,
};

describe('withGovernanceStats', () => {
  it('replaces {{FP}} with the fingerprint', () => {
    expect(withGovernanceStats(STATS, 'fingerprint {{FP}}')).toBe(
      'fingerprint f95a…b222',
    );
  });

  it('replaces {{MCOUNT}} zero-padded to 3 digits', () => {
    expect(withGovernanceStats(STATS, 'M001–M{{MCOUNT}}')).toBe('M001–M016');
  });

  it('replaces {{GCOUNT}} zero-padded to 2 digits', () => {
    expect(withGovernanceStats(STATS, 'G01–G{{GCOUNT}}')).toBe('G01–G23');
  });

  it('pads a single-digit count instead of truncating', () => {
    const smallStats: GovernanceStats = { ...STATS, guidelinesCount: 5 };
    expect(withGovernanceStats(smallStats, 'G01–G{{GCOUNT}}')).toBe('G01–G05');
  });

  it('replaces multiple occurrences of the same token', () => {
    expect(withGovernanceStats(STATS, '{{FP}} ... {{FP}}')).toBe(
      'f95a…b222 ... f95a…b222',
    );
  });

  it('leaves text with no tokens unchanged', () => {
    expect(withGovernanceStats(STATS, 'no tokens here')).toBe(
      'no tokens here',
    );
  });
});

describe('PLACEHOLDER_GOVERNANCE_STATS', () => {
  it('is marked unavailable with a placeholder fingerprint', () => {
    expect(PLACEHOLDER_GOVERNANCE_STATS.available).toBe(false);
    expect(PLACEHOLDER_GOVERNANCE_STATS.fingerprintShort).toBe('—');
  });
});
