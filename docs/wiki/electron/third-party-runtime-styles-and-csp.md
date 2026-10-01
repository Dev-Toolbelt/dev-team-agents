# Third-Party Libraries Injecting Styles at Runtime vs. CSP

**Origin:** Electron desktop app, Sonner toast library | 2026-10-01
**Tags:** sonner, CSP, content-security-policy, third-party, runtime styles, development vs production, __insertCSS, unsafe-inline

> Libraries that inject `<style>` elements at module load render completely unstyled in the packaged build when CSP forbids `'unsafe-inline'`, but look fine in development where Vite injects inline styles freely.

---

## What it is

Third-party libraries like sonner bundle a CSS file and inject it into the DOM at runtime using a helper like `__insertCSS`. This works in development (where Vite's dev server injects styles inline with `'unsafe-inline'` allowed) but fails silently in production if the CSP restricts `style-src`.

`app/src/main/security.ts` defines two CSP headers:

- **Development**: `style-src 'self' 'unsafe-inline'` — allows injected styles
- **Production**: `style-src 'self'` — blocks any runtime injection

The packaged app loads with the production CSP, so the library's runtime `<style>` injection is refused by the browser (one CSP violation in the console, easy to miss). The component renders but has no styles, appearing broken.

## How it works

1. Sonner (or similar) loads as an ES module
2. Its bundler helper emits a small `<style>` tag with the CSS
3. Browser checks the tag against CSP: `style-src 'self'` forbids it
4. CSS is rejected silently; component renders unstyled
5. One CSP violation appears in the console per launch (harmless; we accept it)

**The fix:** Import the library's published stylesheet into your CSS bundle instead of relying on runtime injection.

```css
/* app/src/renderer/index.css */
@import 'tailwindcss';
@import 'sonner/dist/styles.css';
```

The runtime injection still occurs and is still blocked, but the CSS was already in the page via the preload stylesheet. Sonner (and any library using this pattern) will work correctly.

**Verification:** After building, grep the output:

```bash
grep data-sonner-toaster dist/renderer/assets/*.css
```

If the selector appears, the stylesheet was bundled.

## Gotchas

- **Never relax the CSP to allow `'unsafe-inline'`** in production — that defeats the security boundary. The fix is to import the stylesheet, not to weaken the policy.
- The library's runtime `<style>` tag will still appear in the DOM and still violate CSP (one message in the console). This is harmless and expected; the CSS is already in the page from the import.
- React inline `style={{}}` props are unaffected — they set styles through the CSSOM, which `style-src` without `unsafe-inline` permits.
- Check after every build, especially when upgrading the library.

## References

- `app/src/main/security.ts` — CSP header definitions (development vs production)
- `app/src/renderer/index.css` — CSS bundling entry point
- Sonner documentation: CSS import instructions
