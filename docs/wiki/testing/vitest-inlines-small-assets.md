# Vitest Inlines Small Imported Assets, Production Does Not

**Origin:** Provider logo on the desktop app board | 2026-10-19
**Tags:** vitest, assetsInlineLimit, data URI, svg import, inline limit, img src, renderer tests, filename assertion, providerIcon, vite

> Read this first: never assert on an imported asset's filename in `app/` renderer tests. Under Vitest a small SVG becomes a `data:` URL and a large one becomes a file path, so the filename disappears for some assets and not others.

---

## What it is
The Electron app in `app/` builds with Vite and imports images and SVGs as modules. The production and test configs disagree on when an asset is inlined, so the `src` a component receives depends on the runner.

## How it works
1. `app/vite.config.mts` sets `build.assetsInlineLimit: 0`. Production emits every imported image as a same-origin file. The renderer CSP is `img-src 'self' data:`, so this is the only shape that loads.
2. `app/vitest.config.mts` does not inherit that setting. Vite's default inline limit of 4 KB applies.
3. Under Vitest, an imported SVG below 4 KB resolves to `data:image/svg+xml,...`. A larger one resolves to a file path such as `/codex.svg`.
4. A test that asserted `src` contains `codex.svg` passed for `claude.svg` (7 KB) and failed for `codex.svg` and `opencode.svg` (under 4 KB).

## Gotchas
- The failure depends on file size, not on the component. Adding a logo smaller than 4 KB flips it.
- Assert the behavior instead: `src` is non-empty and distinct for each provider. See `app/test/renderer/providerIcon.test.tsx`.
- Do not copy the production `assetsInlineLimit: 0` into Vitest to make the filenames match. The test then diverges from the code path the user actually sees in a different way.

## References
- `app/vite.config.mts` (`build.assetsInlineLimit`), `app/vitest.config.mts`
- `app/src/renderer/providers/ProviderIcon.tsx`
- `app/test/renderer/providerIcon.test.tsx`
