/**
 * The security posture, in one file so it can be reviewed as a whole.
 *
 * The app shells out to a CLI. That is only safe if the renderer cannot reach the shell,
 * the filesystem, or the network — so each of the following is a load-bearing decision
 * rather than a default worth reconsidering casually:
 *
 *   - `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` on the one
 *     window. The renderer gets the named operations in `shared/api.ts` and nothing else.
 *   - **no remote content, ever.** The packaged app loads `file://` only. Every request
 *     to any other scheme is cancelled at the session level, so a dependency that tries
 *     to fetch a font or report telemetry fails rather than succeeding quietly.
 *   - a **restrictive CSP** applied as a response header, not only as a `<meta>` tag: a
 *     header cannot be removed by injected markup, and it covers responses a `<meta>`
 *     tag in `index.html` never sees.
 *   - window-open, navigation and webview attachment are all denied. Window-open is denied
 *     **without** an `openExternal` escape: the app renders no links, so a handler that
 *     opened one would be an outbound capability with no caller.
 *   - every permission request (notifications, media, geolocation…) is denied. This app
 *     needs none, so the handler is a flat `false` rather than a list to maintain.
 */

import type { Session, WebContents } from 'electron';

/**
 * The renderer options every window in this app is created with.
 *
 * It lives here, beside the reasoning, rather than inline in `index.ts` for one concrete
 * reason: `index.ts` runs `app.enableSandbox()` and an `app.whenReady()` chain at module
 * scope, so a test cannot import it outside a real Electron process, and the only way to
 * assert these three flags there was to match the file's own source text. A source-text
 * assertion on the app's most security-critical object breaks on reformatting and can be
 * evaded by building the object a different way, so the object is exported instead and
 * `test/security.test.ts` asserts the real value.
 *
 * `preload` is deliberately absent: it is a path `index.ts` derives from `__dirname`.
 */
export const WINDOW_WEB_PREFERENCES = Object.freeze({
  // The three non-negotiables.
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
  // No `<webview>`, and no second window inheriting anything.
  webviewTag: false,
  spellcheck: false,
});

/**
 * Production CSP. `default-src 'none'` and then only what the bundle needs.
 *
 * No `'unsafe-inline'` for scripts or styles: Vite emits a real `.js` and a real `.css`
 * file for the build, so nothing needs it. `connect-src 'none'` is what makes "no
 * network" a rule the renderer cannot talk its way out of.
 */
export const PRODUCTION_CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "worker-src 'none'",
].join('; ');

/**
 * Development CSP, used **only** when a dev server URL is supplied.
 *
 * It is looser in exactly two ways and both are Vite's, not ours: the dev server injects
 * `<style>` tags rather than emitting a stylesheet, and HMR needs a websocket. It is a
 * separate constant rather than a relaxation of the production one so a loosening cannot
 * leak into a packaged build by editing one string.
 */
export function developmentCsp(devServerOrigin: string): string {
  const ws = devServerOrigin.replace(/^http/, 'ws');
  return [
    "default-src 'none'",
    `script-src 'self' ${devServerOrigin}`,
    `style-src 'self' 'unsafe-inline' ${devServerOrigin}`,
    `img-src 'self' data: ${devServerOrigin}`,
    `font-src 'self' ${devServerOrigin}`,
    `connect-src ${devServerOrigin} ${ws}`,
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
    "object-src 'none'",
  ].join('; ');
}

/**
 * Schemes the renderer may load from — the local bundle, and Electron's own inspector.
 *
 * **Narrowed to match the rule the file header states.** It also held `data:`, `blob:` and
 * `chrome-extension:`, which made `loadURL('data:text/html,…')` succeed: a `data:` URL is a
 * *navigation* the request filter does see, and it can carry arbitrary markup into this
 * renderer. Nothing in the bundle needs any of the three — `assetsInlineLimit: 0` means
 * Vite emits files rather than URIs, and `worker-src` is `'none'`.
 *
 * The production CSP still carries `img-src 'self' data:`. That is not a contradiction and
 * is not dead: a `data:` image is satisfied inside the renderer and never reaches this
 * filter, so the CSP is the only layer that governs it. This set governs what may be
 * *navigated to or fetched*, and there `file:` is the whole of it.
 */
const ALWAYS_ALLOWED_SCHEMES = new Set(['file:', 'devtools:']);

export function isRequestAllowed(url: string, devServerOrigin: string | null): boolean {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (ALWAYS_ALLOWED_SCHEMES.has(parsed.protocol)) return true;
  if (devServerOrigin !== null && url.startsWith(devServerOrigin)) return true;
  return false;
}

export function hardenSession(session: Session, devServerOrigin: string | null): void {
  const csp = devServerOrigin === null ? PRODUCTION_CSP : developmentCsp(devServerOrigin);

  session.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [csp],
        'X-Content-Type-Options': ['nosniff'],
      },
    });
  });

  // The hard stop. Anything that is not the local bundle (or, in development, the dev
  // server) never leaves the process.
  session.webRequest.onBeforeRequest((details, callback) => {
    callback({ cancel: !isRequestAllowed(details.url, devServerOrigin) });
  });

  session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  session.setPermissionCheckHandler(() => false);
}

/**
 * Applied to every `WebContents`, not only to the window this app creates on purpose.
 * Taking `WebContents` rather than `BrowserWindow` is what lets the same rules be
 * attached from `app.on('web-contents-created')`, which is the hook that catches one
 * this file did not create.
 */
export function hardenContents(contents: WebContents, devServerOrigin: string | null): void {
  // Denied outright. Nothing in this app opens a window or a link, so the handler has
  // nothing to allow — and the version that called `shell.openExternal` for any `https://`
  // URL was a standing outbound primitive inside a renderer whose CSP sets
  // `connect-src 'none'` precisely so that none exists. Unreachable today is not a reason
  // to keep it: the next screen that renders CLI text as markup makes it reachable, and
  // then the capability is already there.
  //
  // If a link ever needs to open, allow-list the exact hosts here and say which; do not
  // widen this back to a scheme test.
  contents.setWindowOpenHandler(() => ({ action: 'deny' }));

  contents.on('will-navigate', (event, url) => {
    if (!isRequestAllowed(url, devServerOrigin)) event.preventDefault();
  });

  contents.on('will-attach-webview', (event) => event.preventDefault());
}
