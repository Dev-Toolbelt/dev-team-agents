import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: {
    // The invocation layer runs in node, spawns processes and imports nothing from
    // `electron`. That is the point: CI can run this without a display.
    environment: 'node',
    // `test/renderer/**/*.test.tsx` opts into `jsdom` per file via a `// @vitest-environment
    // jsdom` directive (see those files) — the default here stays `node` for every other
    // suite, which spawns real processes and has no business touching a DOM.
    include: ['test/**/*.test.ts', 'test/**/*.test.tsx'],
    // Real processes are spawned, including one deliberate 1.5s timeout case.
    testTimeout: 30_000,
    hookTimeout: 30_000,
    reporters: ['default'],
  },
});
