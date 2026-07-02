import { defineConfig } from 'vitest/config';

// Standalone config (not astro/config's getViteConfig()) — scope is
// logic-only tests in src/lib/ that don't render Astro/React, so the full
// Astro Vite pipeline isn't needed. See
// .analysis/refined/vitest-landing-testing-20260702/design.md.
export default defineConfig({
  test: {
    include: ['src/lib/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      // Scoped to the modules actually covered by this mission's test plan
      // (see .analysis/refined/vitest-landing-testing-20260702/design.md) —
      // not all of src/lib/**, since src/lib/i18n.ts is static copy/content
      // data, not logic, and was never in scope for testing.
      include: [
        'src/lib/governance-stats.ts',
        'src/lib/governance-data.server.ts',
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
    },
  },
});
