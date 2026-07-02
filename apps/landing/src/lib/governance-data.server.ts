/**
 * Server-only: reads real governance stats from `.sdd/metadata.json` at
 * build time. Import this only from `.astro` frontmatter (never from a
 * client-hydrated component) — it uses Node built-ins that don't exist in
 * the browser bundle.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  PLACEHOLDER_GOVERNANCE_STATS,
  type GovernanceStats,
} from './governance-stats';

const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../..',
);
const METADATA_PATH = path.join(REPO_ROOT, '.sdd', 'metadata.json');

function shortenFingerprint(fingerprint: string): string {
  if (fingerprint.length <= 12) return fingerprint;
  return `${fingerprint.slice(0, 4)}…${fingerprint.slice(-4)}`;
}

/**
 * Loads real governance stats. Falls back to placeholder stats (with a
 * build warning) if `.sdd/metadata.json` isn't present — mirrors the
 * fallback behavior of `selector_compiler.py`, which never ships fake data
 * as if it were real.
 */
export function loadGovernanceStats(): GovernanceStats {
  try {
    const raw = readFileSync(METADATA_PATH, 'utf-8');
    const metadata = JSON.parse(raw) as {
      mandates_count?: number;
      guidelines_count?: number;
      fingerprints?: { combined?: string };
    };
    const fingerprint = metadata.fingerprints?.combined;
    if (
      typeof metadata.mandates_count !== 'number' ||
      typeof metadata.guidelines_count !== 'number' ||
      !fingerprint
    ) {
      throw new Error('metadata.json is missing required governance fields');
    }
    return {
      mandatesCount: metadata.mandates_count,
      guidelinesCount: metadata.guidelines_count,
      fingerprintShort: shortenFingerprint(fingerprint),
      available: true,
    };
  } catch (err) {
    console.warn(
      `[governance-data] .sdd/metadata.json not readable at ${METADATA_PATH} ` +
        `(${(err as Error).message}). Run 'sdd governance generate' before building ` +
        'for production. Falling back to placeholder stats.',
    );
    return PLACEHOLDER_GOVERNANCE_STATS;
  }
}
