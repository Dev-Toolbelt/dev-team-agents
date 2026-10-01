/**
 * Renderer build. The main process and the preload are compiled by `tsc` instead
 * (`tsconfig.node.json`), because a sandboxed preload must be CommonJS and a bundler
 * buys nothing for two node-side files.
 *
 * `base: './'` matters: the packaged renderer is loaded over `file://`, and absolute
 * asset URLs would resolve against the filesystem root and 404.
 */
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  root: fileURLToPath(new URL('./src/renderer', import.meta.url)),
  base: './',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: fileURLToPath(new URL('./dist/renderer', import.meta.url)),
    emptyOutDir: true,
    // No inline assets: the production CSP has no `'unsafe-inline'` and a data: URI
    // large enough to be inlined is better as a file the CSP's `img-src 'self'` covers.
    assetsInlineLimit: 0,
    sourcemap: true,
    rollupOptions: {
      output: {
        // Vendor code changes on a dependency bump, app code on every commit: separate
        // chunks keep each one under the 500 kB warning limit instead of raising it.
        manualChunks(id) {
          if (!id.includes('/node_modules/')) return undefined;
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'vendor-react';
          if (/\/node_modules\/(radix-ui|@radix-ui|@floating-ui)\//.test(id)) return 'vendor-radix';
          if (id.includes('/node_modules/lucide-react/')) return 'vendor-icons';
          return 'vendor';
        },
      },
    },
  },
  // Nothing in this app talks to the network; `server` exists only for `npm run dev:app`.
  server: { port: 5173, strictPort: true },
});
