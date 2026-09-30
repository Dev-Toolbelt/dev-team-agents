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
 *   - navigation is an allow-list of one: the renderer's own index (or, unpackaged, the dev
 *     server's origin). A `file:` URL is not "local, therefore safe" — dropping an `.html`
 *     file on the window would otherwise navigate to it, and the preload would hand that
 *     page the whole `window.devteam` API. The IPC handlers close the same door from the
 *     other side by refusing any sender that is not the renderer's own main frame.
 *   - window-open and webview attachment are denied. Window-open is denied
 *     **without** an `openExternal` escape: the app renders no links, so a handler that
 *     opened one would be an outbound capability with no caller.
 *   - every permission request (notifications, media, geolocation…) is denied. This app
 *     needs none, so the handler is a flat `false` rather than a list to maintain.
 */

import { isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

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
 * `WINDOW_WEB_PREFERENCES` plus the one flag that depends on how the app was built.
 *
 * DevTools are a console into a renderer that holds the whole IPC surface, so a packaged
 * build ships without them; unpackaged, contributors need them. A function of `packaged`
 * rather than a read of `app.isPackaged` here, because this file must stay importable
 * without the `electron` runtime (see the header of `test/security.test.ts`).
 */
export function windowWebPreferences(packaged: boolean): Readonly<typeof WINDOW_WEB_PREFERENCES & { devTools: boolean }> {
  return Object.freeze({ ...WINDOW_WEB_PREFERENCES, devTools: !packaged });
}

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
const ALWAYS_ALLOWED_SCHEMES = new Set(['devtools:']);

/**
 * Where the renderer lives, for the three checks that must agree on it: what a window may
 * navigate to, what a request may fetch, and which IPC sender is trusted.
 */
export interface RendererTarget {
  /** `file:` URL of the bundle's `index.html`. */
  readonly indexUrl: string;
  /** Directory of the bundle; `file:` subresources are honoured only beneath it. */
  readonly bundleDir: string;
  /** Vite's origin, set only for an unpackaged `dev:app` run. */
  readonly devServerOrigin: string | null;
}

/**
 * The dev server origin to honour, or `null`.
 *
 * `DEVTEAM_APP_DEV_SERVER` loosens the CSP and lets a remote origin into the request
 * filter, so it must be unable to do that in a shipped build — an environment variable is
 * something a launcher, a login item or another process can set. Only an `http(s)` URL is
 * accepted, and it is reduced to its origin so every later comparison is exact.
 */
export function resolveDevServer(value: string | undefined, packaged: boolean): string | null {
  if (packaged || value === undefined || value === '') return null;
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
    return parsed.origin;
  } catch {
    return null;
  }
}

function withoutFragmentAndQuery(url: URL): string {
  const copy = new URL(url.href);
  copy.hash = '';
  copy.search = '';
  return copy.href;
}

function isUnderDirectory(fileUrl: URL, directory: string): boolean {
  let path: string;
  try {
    path = fileURLToPath(fileUrl);
  } catch {
    return false;
  }
  const rel = relative(resolve(directory), resolve(path));
  return rel !== '' && rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel);
}

export function isRequestAllowed(url: string, target: Pick<RendererTarget, 'bundleDir' | 'devServerOrigin'>): boolean {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (ALWAYS_ALLOWED_SCHEMES.has(parsed.protocol)) return true;
  // Under the bundle only: the `file:` scheme as a whole would let a navigation that got
  // through some other way read any local file the user can.
  if (parsed.protocol === 'file:') return isUnderDirectory(parsed, target.bundleDir);
  // Parsed origin, not `startsWith`: `http://localhost:5173.evil.tld/` starts with the dev
  // origin's text and is a different host.
  if (target.devServerOrigin !== null && parsed.origin === target.devServerOrigin) return true;
  return false;
}

/**
 * Whether a top-level or frame navigation to `url` is the renderer itself: the exact index
 * URL with any hash or query ignored (the router uses them), or — dev only — any path on
 * the dev server's origin. Every other page, `file:` included, is refused.
 */
export function isRendererUrl(url: string, target: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>): boolean {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (target.devServerOrigin !== null) return parsed.origin === target.devServerOrigin;
  if (parsed.protocol !== 'file:') return false;
  return withoutFragmentAndQuery(parsed) === withoutFragmentAndQuery(new URL(target.indexUrl));
}

/** The slice of an IPC event the sender check reads; `IpcMainInvokeEvent` satisfies it. */
export interface IpcSenderEvent {
  readonly senderFrame?: { readonly url: string; readonly parent: unknown } | null;
}

/**
 * Whether an IPC call came from the renderer's own main frame.
 *
 * Navigation is locked down above, but that is one layer; this is the one that holds when
 * it is not — a subframe, a page that slipped in some other way, a frame whose `senderFrame`
 * is already gone (`null`). The handlers run `devteam`, so "who is asking" is checked on
 * every call rather than assumed from "the preload only exposes it to our page".
 */
export function isTrustedSender(event: IpcSenderEvent | undefined, target: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>): boolean {
  const frame = event?.senderFrame;
  if (frame === undefined || frame === null) return false;
  if (frame.parent !== null) return false;
  return isRendererUrl(frame.url, target);
}

/**
 * Wrap an `ipcMain.handle` listener so it runs only for a trusted sender. A refused call
 * rejects the renderer's `invoke` and never reaches the handler body.
 */
export function trustedHandler<Args extends unknown[], R>(
  target: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>,
  listener: (event: never, ...args: Args) => R,
): (event: IpcSenderEvent, ...args: Args) => R {
  return (event, ...args) => {
    if (!isTrustedSender(event, target)) {
      throw new Error('IPC call refused: the sender is not this app\'s renderer.');
    }
    return listener(event as never, ...args);
  };
}

export function hardenSession(session: Session, target: Pick<RendererTarget, 'bundleDir' | 'devServerOrigin'>): void {
  const { devServerOrigin } = target;
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
    callback({ cancel: !isRequestAllowed(details.url, target) });
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
export function hardenContents(contents: WebContents, target: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>): void {
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
    if (!isRendererUrl(url, target)) event.preventDefault();
  });
  // `will-navigate` covers the main frame only; this one fires for subframes too, so an
  // iframe cannot be pointed at a page that would then be a sender of its own.
  contents.on('will-frame-navigate', (event) => {
    if (!isRendererUrl(event.url, target)) event.preventDefault();
  });

  contents.on('will-attach-webview', (event) => event.preventDefault());
}
