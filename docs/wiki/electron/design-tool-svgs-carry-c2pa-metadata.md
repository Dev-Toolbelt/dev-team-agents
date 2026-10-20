# Design-Tool SVGs Carry C2PA Metadata That Bloats Them

**Origin:** Official provider logos in the desktop app | 2026-10-19
**Tags:** svg, c2pa, content credentials, metadata, manifest, design export, provider logo, sed, dark:invert, svg sanitize

> Read this first: an SVG exported from a design or AI tool can be 10 times larger than its drawing because it embeds a C2PA content-credentials manifest. Strip it before committing and re-audit the file before any markup-level use.

---

## What it is
Logos for Claude, Codex, and opencode were exported from design and AI tools. Those exports embed a provenance manifest. The drawing is 1 to 7 KB; the file is 40 to 64 KB.

## How it works
1. The manifest sits in one block: `<metadata><c2pa:manifest>...base64...</c2pa:manifest></metadata>`. It is on one line.
2. Strip it before committing:
   ```bash
   sed -E 's#<metadata>.*</metadata>##' logo.svg > logo.clean.svg
   ```
3. Drop unused `xmlns:xlink` declarations.
4. Audit the cleaned file for active content:
   - `<script>`
   - `on*=` event handlers
   - `href` and `xlink:href`
   - `foreignObject`
   - `<use>`
   - `<style>`
   - external `url()` references
5. Render third-party SVGs only through `<img>`. Scripts inside an image never run.
6. Re-run the audit before inlining an SVG as markup or converting it to an SVGR component. Inlined SVG runs in the page's DOM.

## Gotchas
- Stripping the manifest does not make a file safe. The audit in step 4 is still required.
- A near-black mark, such as opencode `#211F1F`, disappears on the dark color scheme. Apply `dark:invert` on the `<img>` so it stays visible.

## References
- `app/src/renderer/providers/ProviderIcon.tsx`
- Commits c2f76b0, 6c8751f, 882095f on `main`
