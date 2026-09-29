import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: {
    // The invocation layer runs in node, spawns processes and imports nothing from
    // `electron`. That is the point: CI can run this without a display.
    environment: 'node',
    include: ['test/**/*.test.ts'],
    // Real processes are spawned, including one deliberate 1.5s timeout case.
    testTimeout: 30_000,
    hookTimeout: 30_000,
    reporters: ['default'],
  },
});
