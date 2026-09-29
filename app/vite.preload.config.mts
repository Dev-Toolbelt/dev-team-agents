/**
 * The preload is **bundled**, and this file is why.
 *
 * A sandboxed preload script (`sandbox: true`) is not loaded by node's module loader. It
 * runs in Electron's sandbox bundle, whose `require` resolves `electron` and a handful of
 * builtins and nothing else — so `require('../shared/api.js')` fails at runtime with
 * `module not found`, and the bridge is simply absent in the renderer. That was not caught
 * by typecheck, lint or the unit tests; it was caught by launching the app, which is the
 * note worth keeping here.
 *
 * So the preload is rolled into one self-contained CommonJS file with `electron` left
 * external. That keeps `CHANNELS` a single shared constant — the alternative was to inline
 * the channel strings into the preload and let them drift from `shared/api.ts`.
 */
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: fileURLToPath(new URL('./dist/preload', import.meta.url)),
    emptyOutDir: true,
    sourcemap: true,
    minify: false,
    lib: {
      entry: fileURLToPath(new URL('./src/preload/index.ts', import.meta.url)),
      formats: ['cjs'],
      fileName: () => 'index.js',
    },
    rollupOptions: {
      // Provided by the sandbox bundle, never bundled in.
      external: ['electron'],
    },
  },
});
