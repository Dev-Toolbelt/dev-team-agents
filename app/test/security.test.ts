/**
 * The security posture, pinned against real probes — not against a description of it.
 *
 * Every assertion here has a companion mutation recorded in the session summary /
 * report: the point of this file is that flipping the posture back to the broken state
 * the review reproduced (contextIsolation off, sandbox off, a permissive CSP, a working
 * `shell.openExternal`, an allowed remote scheme) must fail at least one test here.
 *
 * `security.ts` only *type*-imports from `electron` (`import type { Session,
 * WebContents }`), so this file never needs to mock the `electron` package to test it —
 * plain objects that shape-match the handful of methods actually called are enough, and
 * keeping those fakes minimal is deliberate: a fat fake would let the test assert its
 * own stub instead of the module under test.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it, vi } from 'vitest';

import type { Session, WebContents } from 'electron';

import {
  PRODUCTION_CSP,
  WINDOW_WEB_PREFERENCES,
  developmentCsp,
  hardenContents,
  hardenSession,
  isRendererUrl,
  isRequestAllowed,
  isTrustedSender,
  resolveDevServer,
  trustedHandler,
  windowWebPreferences,
  type RendererTarget,
} from '../src/main/security.js';

const SECURITY_SOURCE = readFileSync(
  fileURLToPath(new URL('../src/main/security.ts', import.meta.url)),
  'utf8',
);
const INDEX_SOURCE = readFileSync(
  fileURLToPath(new URL('../src/main/index.ts', import.meta.url)),
  'utf8',
);

// A file URL only maps to a path with a drive letter on Windows (`fileURLToPath` throws
// otherwise), so the fixture tree sits on `C:` there and at `/` everywhere else.
const WINDOWS = process.platform === 'win32';
const FILE_ROOT = WINDOWS ? 'file:///C:' : 'file://';
const BUNDLE = WINDOWS ? 'C:\\app\\dist\\renderer' : '/app/dist/renderer';
const INDEX = `${FILE_ROOT}/app/dist/renderer/index.html`;
const PROD: RendererTarget = { indexUrl: INDEX, bundleDir: BUNDLE, devServerOrigin: null };
const devTarget = (origin: string): RendererTarget => ({ ...PROD, devServerOrigin: origin });

describe('isRequestAllowed — scheme allowlist', () => {
  it('allows the bundle and devtools:, and nothing else, with no dev server configured', () => {
    expect(isRequestAllowed(`${FILE_ROOT}/app/dist/renderer/assets/index.js`, PROD)).toBe(true);
    expect(isRequestAllowed('devtools://devtools/bundled/inspector.html', PROD)).toBe(true);
    // Mutation: putting `data:`, `blob:` or `chrome-extension:` back into
    // ALWAYS_ALLOWED_SCHEMES flips these to `true` — that is exactly the regression the
    // header comment in security.ts describes (`loadURL('data:text/html,…')` succeeding).
    expect(isRequestAllowed('data:text/html,<h1>hi</h1>', PROD)).toBe(false);
    expect(isRequestAllowed('blob:https://example.com/uuid', PROD)).toBe(false);
    expect(isRequestAllowed('chrome-extension://abc/page.html', PROD)).toBe(false);
    expect(isRequestAllowed('https://example.com', PROD)).toBe(false);
    expect(isRequestAllowed('http://example.com', PROD)).toBe(false);
    expect(isRequestAllowed('ws://example.com', PROD)).toBe(false);
    expect(isRequestAllowed('about:blank', PROD)).toBe(false);
  });

  it('refuses a file: URL outside the renderer bundle', () => {
    // Mutation: a bare `file:` scheme test (the previous filter) lets all of these through,
    // which is what made a dropped `.html` file a first-class page of this app.
    expect(isRequestAllowed(`${FILE_ROOT}/tmp/evil.html`, PROD)).toBe(false);
    expect(isRequestAllowed(`${FILE_ROOT}/app/dist/renderer/../secret.html`, PROD)).toBe(false);
    expect(isRequestAllowed(`${FILE_ROOT}/app/dist/renderer-evil/index.html`, PROD)).toBe(false);
    expect(isRequestAllowed(`${FILE_ROOT}/app/dist/renderer`, PROD)).toBe(false);
  });

  it('rejects a malformed URL instead of throwing', () => {
    expect(isRequestAllowed('not a url at all', PROD)).toBe(false);
  });

  it('allows a configured dev server origin only on an exact parsed-origin match', () => {
    const origin = 'http://localhost:5173';
    expect(isRequestAllowed(`${origin}/main.js`, devTarget(origin))).toBe(true);
    // The regression this guards: `includes` instead of `startsWith` would let an
    // attacker-controlled URL that merely *contains* the dev origin later in the string
    // sail through — e.g. a redirect or query string smuggling the trusted origin in.
    expect(isRequestAllowed(`https://evil.example/?next=${origin}`, devTarget(origin))).toBe(false);
    expect(isRequestAllowed('https://evilhttp://localhost:5173.example', devTarget(origin))).toBe(false);
    // Mutation: the previous `url.startsWith(origin)` passes both of these.
    expect(isRequestAllowed('http://localhost:5173.evil.tld/main.js', devTarget(origin))).toBe(false);
    expect(isRequestAllowed('http://localhost:51730/main.js', devTarget(origin))).toBe(false);
    expect(isRequestAllowed('http://localhost:5173@evil.tld/main.js', devTarget(origin))).toBe(false);
  });

  it('never allows the dev server origin when none was supplied', () => {
    expect(isRequestAllowed('http://localhost:5173/main.js', PROD)).toBe(false);
  });
});

describe('PRODUCTION_CSP / developmentCsp', () => {
  it('locks the production CSP to default-deny with no inline anything', () => {
    expect(PRODUCTION_CSP).toContain("default-src 'none'");
    expect(PRODUCTION_CSP).toContain("connect-src 'none'");
    // Mutation: adding `'unsafe-inline'` to script-src or style-src is exactly what the
    // sabotage run did to smuggle inline scripts past the CSP.
    expect(PRODUCTION_CSP).not.toContain('unsafe-inline');
  });

  it('never returns the production CSP once a dev server origin is supplied', () => {
    const dev = developmentCsp('http://localhost:5173');
    expect(dev).not.toBe(PRODUCTION_CSP);
    // The two documented differences only: style-src carries 'unsafe-inline' (Vite's
    // injected <style> tags) and connect-src allows the origin + its ws: form (HMR).
    expect(dev).toContain("style-src 'self' 'unsafe-inline' http://localhost:5173");
    expect(dev).toContain('connect-src http://localhost:5173 ws://localhost:5173');
    // Nothing else may loosen: default-src, base-uri, form-action, frame-ancestors and
    // object-src stay locked even in development.
    expect(dev).toContain("default-src 'none'");
    expect(dev).toContain("base-uri 'none'");
    expect(dev).toContain("form-action 'none'");
    expect(dev).toContain("frame-ancestors 'none'");
    expect(dev).toContain("object-src 'none'");
  });

  it('deliberately disagrees with isRequestAllowed on data: images', () => {
    // img-src permits `data:` because a data-URI image never reaches onBeforeRequest —
    // it is resolved inside the renderer. A test asserting the CSP and the request
    // filter "agree" would be asserting the wrong invariant.
    expect(PRODUCTION_CSP).toContain("img-src 'self' data:");
    expect(isRequestAllowed('data:image/png;base64,abc', PROD)).toBe(false);
  });
});

type HeadersHandler = (details: { responseHeaders?: Record<string, string[]> }, cb: (r: unknown) => void) => void;
type BeforeRequestHandler = (details: { url: string }, cb: (r: unknown) => void) => void;

function fakeSession() {
  const handlers: {
    headers: HeadersHandler | null;
    beforeRequest: BeforeRequestHandler | null;
  } = { headers: null, beforeRequest: null };
  let permissionRequestCallback: ((granted: boolean) => void) | null = null;
  let permissionCheckResult: unknown;
  const session = {
    webRequest: {
      onHeadersReceived: vi.fn((cb: HeadersHandler) => {
        handlers.headers = cb;
      }),
      onBeforeRequest: vi.fn((cb: BeforeRequestHandler) => {
        handlers.beforeRequest = cb;
      }),
    },
    setPermissionRequestHandler: vi.fn(
      (cb: (contents: unknown, permission: unknown, callback: (granted: boolean) => void) => void) => {
        cb(null, 'notifications', (granted) => {
          permissionRequestCallback = () => granted;
        });
      },
    ),
    setPermissionCheckHandler: vi.fn((cb: () => unknown) => {
      permissionCheckResult = cb();
    }),
  };
  return {
    session,
    handlers,
    getPermissionRequestResult: () => permissionRequestCallback?.(true),
    getPermissionCheckResult: () => permissionCheckResult,
  };
}

describe('hardenSession — the response header and the request filter', () => {
  it('sends the production CSP as a real response header when no dev server is configured', () => {
    const { session, handlers } = fakeSession();
    hardenSession(session as unknown as Session, PROD);
    let sent: Record<string, string[]> | undefined;
    handlers.headers?.({ responseHeaders: {} }, (result) => {
      sent = (result as { responseHeaders: Record<string, string[]> }).responseHeaders;
    });
    expect(sent?.['Content-Security-Policy']).toEqual([PRODUCTION_CSP]);
    expect(sent?.['X-Content-Type-Options']).toEqual(['nosniff']);
  });

  it('cancels every request that isRequestAllowed would reject, and only those', () => {
    const { session, handlers } = fakeSession();
    hardenSession(session as unknown as Session, PROD);
    let outcome: { cancel: boolean } | undefined;
    handlers.beforeRequest?.({ url: 'https://example.com' }, (result) => {
      outcome = result as { cancel: boolean };
    });
    // Mutation: onBeforeRequest calling back with `{ cancel: false }` unconditionally,
    // or not registering the handler at all, is exactly the "remote content blocked"
    // guarantee the review verified by hand and found nothing pinning.
    expect(outcome?.cancel).toBe(true);
    handlers.beforeRequest?.({ url: `${FILE_ROOT}/app/dist/renderer/index.html` }, (result) => {
      outcome = result as { cancel: boolean };
    });
    expect(outcome?.cancel).toBe(false);
  });

  it('denies every permission request and every permission check unconditionally', () => {
    const { session, getPermissionRequestResult, getPermissionCheckResult } = fakeSession();
    hardenSession(session as unknown as Session, PROD);
    // Mutation: `callback(true)` here is the exact sabotage the review performed —
    // flipping the permission handler to grant everything, silently.
    expect(getPermissionRequestResult()).toBe(false);
    expect(getPermissionCheckResult()).toBe(false);
  });
});

function fakeWebContents() {
  let windowOpenHandler: ((details: { url: string }) => { action: string }) | null = null;
  const listeners = new Map<string, (event: { preventDefault: () => void }, ...rest: unknown[]) => void>();
  const contents = {
    setWindowOpenHandler: vi.fn((handler: typeof windowOpenHandler) => {
      windowOpenHandler = handler;
    }),
    on: vi.fn((event: string, listener: (event: { preventDefault: () => void }, ...rest: unknown[]) => void) => {
      listeners.set(event, listener);
    }),
  };
  return {
    contents,
    invokeWindowOpen: (url: string) => windowOpenHandler?.({ url }),
    fireWillNavigate: (url: string) => {
      const event = { preventDefault: vi.fn() };
      listeners.get('will-navigate')?.(event, url);
      return event;
    },
    fireWillFrameNavigate: (url: string) => {
      const event = { preventDefault: vi.fn(), url };
      listeners.get('will-frame-navigate')?.(event);
      return event;
    },
    fireWillAttachWebview: () => {
      const event = { preventDefault: vi.fn() };
      listeners.get('will-attach-webview')?.(event);
      return event;
    },
  };
}

describe('hardenContents — window-open, navigation, webview', () => {
  it('denies every window-open request and never touches an openExternal-style escape', () => {
    const { contents, invokeWindowOpen } = fakeWebContents();
    hardenContents(contents as unknown as WebContents, PROD);
    const result = invokeWindowOpen('https://example.com');
    // Mutation: this is the review's exact sabotage — a handler that calls
    // `shell.openExternal(url)` for an https: URL and returns `{ action: 'deny' }` (or
    // `'allow'`) would still pass a test that only checked the return value, so the
    // source-level assertion below is not decoration.
    expect(result).toEqual({ action: 'deny' });
  });

  it('imports no shell module at all — the regression is reintroducing the import', () => {
    // Source-text assertion, used because "shell.openExternal was never called" only
    // proves this specific handler; it does not prove the capability was removed from
    // the file rather than just left uncalled on this path. Grepping for the import is
    // a weak instrument in general, but here it is checking for the presence of a
    // specific, named symbol re-introduced by a specific historical regression, not
    // standing in for behavioural coverage that could exist instead.
    expect(SECURITY_SOURCE).not.toMatch(/import\s*\{[^}]*\bshell\b[^}]*\}\s*from\s*['"]electron['"]/);
  });

  it('prevents default on will-navigate to anything but the renderer index', () => {
    const { contents, fireWillNavigate } = fakeWebContents();
    hardenContents(contents as unknown as WebContents, PROD);
    expect(fireWillNavigate('https://example.com').preventDefault).toHaveBeenCalled();
    // Mutation: the previous filter allowed every `file:` URL, so a dropped `.html` file
    // navigated the window to a page that inherits the preload's `window.devteam`.
    expect(fireWillNavigate(`${FILE_ROOT}/tmp/evil.html`).preventDefault).toHaveBeenCalled();
    expect(fireWillNavigate(`${FILE_ROOT}/app/dist/renderer/other.html`).preventDefault).toHaveBeenCalled();
    expect(fireWillNavigate(INDEX).preventDefault).not.toHaveBeenCalled();
    // The router's hash and query are not a different page.
    expect(fireWillNavigate(`${INDEX}#/projects?tab=1`).preventDefault).not.toHaveBeenCalled();
  });

  it('applies the same allow-list to frame navigations', () => {
    const { contents, fireWillFrameNavigate } = fakeWebContents();
    hardenContents(contents as unknown as WebContents, PROD);
    expect(fireWillFrameNavigate(`${FILE_ROOT}/tmp/evil.html`).preventDefault).toHaveBeenCalled();
    expect(fireWillFrameNavigate('https://example.com/frame').preventDefault).toHaveBeenCalled();
    expect(fireWillFrameNavigate(INDEX).preventDefault).not.toHaveBeenCalled();
  });

  it('allows only the dev server origin in development, not the file index', () => {
    const { contents, fireWillNavigate } = fakeWebContents();
    hardenContents(contents as unknown as WebContents, devTarget('http://localhost:5173'));
    expect(fireWillNavigate('http://localhost:5173/#/x').preventDefault).not.toHaveBeenCalled();
    expect(fireWillNavigate('http://localhost:5173.evil.tld/').preventDefault).toHaveBeenCalled();
    expect(fireWillNavigate(`${FILE_ROOT}/tmp/evil.html`).preventDefault).toHaveBeenCalled();
  });

  it('prevents default on every webview attachment attempt', () => {
    const { contents, fireWillAttachWebview } = fakeWebContents();
    hardenContents(contents as unknown as WebContents, PROD);
    expect(fireWillAttachWebview().preventDefault).toHaveBeenCalled();
  });
});

describe('resolveDevServer', () => {
  it('ignores the variable in a packaged build', () => {
    expect(resolveDevServer('http://localhost:5173', true)).toBeNull();
  });

  it('reduces a valid http(s) URL to its origin when unpackaged', () => {
    expect(resolveDevServer('http://localhost:5173/some/path?x=1', false)).toBe('http://localhost:5173');
  });

  it('refuses an unset, empty, unparseable or non-http value', () => {
    expect(resolveDevServer(undefined, false)).toBeNull();
    expect(resolveDevServer('', false)).toBeNull();
    expect(resolveDevServer('not a url', false)).toBeNull();
    expect(resolveDevServer(`${FILE_ROOT}/tmp/x`, false)).toBeNull();
    expect(resolveDevServer('javascript:alert(1)', false)).toBeNull();
  });
});

describe('isRendererUrl', () => {
  it('matches the index exactly, ignoring hash and query', () => {
    expect(isRendererUrl(INDEX, PROD)).toBe(true);
    expect(isRendererUrl(`${INDEX}?a=1#b`, PROD)).toBe(true);
    expect(isRendererUrl(`${FILE_ROOT}/app/dist/renderer/index.html/../x.html`, PROD)).toBe(false);
    expect(isRendererUrl('not a url', PROD)).toBe(false);
  });
});

describe('IPC sender check', () => {
  const mainFrame = (url: string) => ({ senderFrame: { url, parent: null } });

  it('trusts only the renderer\'s own main frame', () => {
    expect(isTrustedSender(mainFrame(INDEX), PROD)).toBe(true);
    expect(isTrustedSender(mainFrame(`${INDEX}#/x`), PROD)).toBe(true);
    expect(isTrustedSender(mainFrame(`${FILE_ROOT}/tmp/evil.html`), PROD)).toBe(false);
    expect(isTrustedSender(mainFrame('https://example.com/'), PROD)).toBe(false);
  });

  it('refuses a subframe even at the renderer URL, and a missing frame or event', () => {
    expect(isTrustedSender({ senderFrame: { url: INDEX, parent: {} } }, PROD)).toBe(false);
    expect(isTrustedSender({ senderFrame: null }, PROD)).toBe(false);
    expect(isTrustedSender({}, PROD)).toBe(false);
    expect(isTrustedSender(undefined, PROD)).toBe(false);
  });

  it('trusts the dev origin in development and not a lookalike', () => {
    const dev = devTarget('http://localhost:5173');
    expect(isTrustedSender(mainFrame('http://localhost:5173/'), dev)).toBe(true);
    expect(isTrustedSender(mainFrame('http://localhost:5173.evil.tld/'), dev)).toBe(false);
  });

  it('runs the handler for a trusted sender and rejects before it for any other', () => {
    let calls = 0;
    const wrapped = trustedHandler(PROD, (_event: never, value: number): number => {
      calls += 1;
      return value + 1;
    });
    expect(wrapped(mainFrame(INDEX), 1)).toBe(2);
    expect(() => wrapped(mainFrame(`${FILE_ROOT}/tmp/evil.html`), 1)).toThrow(/refused/);
    expect(() => wrapped({}, 1)).toThrow(/refused/);
    expect(calls).toBe(1);
  });
});

describe('createWindow webPreferences and app.enableSandbox() — source-text fallback', () => {
  // `createWindow` in src/main/index.ts is not exported and the module has top-level
  // side effects (`app.enableSandbox()`, `app.whenReady().then(...)`, `app.on(...)`)
  // that run at import time against the real `electron` package — which, outside an
  // actual Electron process, is a string (the binary path), not the API object. Making
  // this a real behavioural assertion would mean either exporting `createWindow`/the
  // `WINDOW_WEB_PREFERENCES` is exported from src/main/security.ts precisely so this is a
  // real assertion on the real object rather than a match against index.ts's source text.
  // A source-text check on the app's most security-critical object breaks on reformatting
  // and can be evaded by constructing the object another way.
  it('pins the three non-negotiable webPreferences flags every window is created with', () => {
    expect(WINDOW_WEB_PREFERENCES.contextIsolation).toBe(true);
    expect(WINDOW_WEB_PREFERENCES.nodeIntegration).toBe(false);
    expect(WINDOW_WEB_PREFERENCES.sandbox).toBe(true);
    expect(WINDOW_WEB_PREFERENCES.webSecurity).toBe(true);
    expect(WINDOW_WEB_PREFERENCES.allowRunningInsecureContent).toBe(false);
    expect(WINDOW_WEB_PREFERENCES.webviewTag).toBe(false);
  });

  it('is frozen, so nothing can relax a flag at runtime', () => {
    expect(Object.isFrozen(WINDOW_WEB_PREFERENCES)).toBe(true);
    expect(Object.isFrozen(windowWebPreferences(true))).toBe(true);
  });

  it('turns DevTools off in a packaged build and keeps every base flag', () => {
    expect(windowWebPreferences(true).devTools).toBe(false);
    expect(windowWebPreferences(false).devTools).toBe(true);
    expect(windowWebPreferences(true)).toMatchObject(WINDOW_WEB_PREFERENCES);
  });

  it('is the object the window is actually created with', () => {
    // The remaining source-text assertion in this file, and the narrowest one possible:
    // it proves index.ts spreads the exported object rather than re-declaring the flags
    // inline, which is what would make the assertions above decorative.
    expect(INDEX_SOURCE).toMatch(/webPreferences:\s*\{[^}]*\.\.\.windowWebPreferences\(app\.isPackaged\)/);
    expect(INDEX_SOURCE).not.toMatch(/contextIsolation:/);
  });

  it('calls app.enableSandbox() at module scope', () => {
    expect(INDEX_SOURCE).toMatch(/^app\.enableSandbox\(\);/m);
  });
});

describe('the renderer document CSP (account screens make no network call)', () => {
  it("keeps connect-src 'none' in index.html so account secrets cannot leave the renderer", () => {
    const html = readFileSync(fileURLToPath(new URL('../src/renderer/index.html', import.meta.url)), 'utf8');
    expect(html).toContain("connect-src 'none'");
    expect(html).toContain("default-src 'none'");
    expect(html).not.toMatch(/connect-src[^;"]*(https?:|wss?:|\*)/);
  });
});
