/**
 * The main process. Creates one window, hardens it, and registers the IPC handlers.
 *
 * CommonJS. The deciding constraint is the preload: a sandboxed preload script is loaded
 * as CommonJS, which is the price of `sandbox: true` and worth paying. Compiling main and
 * preload to the same module system keeps a `require()`-of-ESM boundary out of the app for
 * the sake of one shared constants module; the renderer is bundled by Vite either way.
 */

import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { BrowserWindow, app, nativeImage, session } from 'electron';

import { registerIpc } from './ipc.js';
import { WINDOW_WEB_PREFERENCES, hardenContents, hardenSession } from './security.js';
import { CODE_SIGNED } from './build-info.js';

/**
 * Set by `npm run dev:app` to the Vite dev server's origin. Absent in a packaged build,
 * which is what puts the app on the production CSP and the `file://`-only request filter.
 */
const DEV_SERVER = process.env['DEVTEAM_APP_DEV_SERVER'] ?? null;

/** `dist/node/main/index.js` → `dist/renderer`. */
const RENDERER_INDEX = join(__dirname, '..', '..', 'renderer', 'index.html');
// `dist/node/main` -> `dist/preload/index.js`. Bundled, not tsc-compiled: see
// `vite.preload.config.mts` for why a sandboxed preload has to be one self-contained file.
const PRELOAD = join(__dirname, '..', '..', 'preload', 'index.js');

/**
 * The brand icon, for development only.
 *
 * A packaged build takes its icon from the bundle electron-builder assembles, so this is
 * `null` there and nothing below runs. Unpackaged, `electron .` launches the stock
 * Electron binary, which carries Electron's own icon — so the app showed the default
 * atom in the dock and in the task switcher for every contributor who ran it, while the
 * header two centimetres below showed the brand. Set here rather than left alone,
 * because "how the app looks when you run it" is the thing this build exists to try.
 *
 * `dist/node/main` → `app/build/icon.png`, which only resolves in a checkout. That is the
 * same condition as `!app.isPackaged`, but the `existsSync` is kept anyway: a missing
 * icon must never be the reason a window fails to open.
 */
function developmentIcon(): Electron.NativeImage | null {
  if (app.isPackaged) return null;
  const file = join(__dirname, '..', '..', '..', 'build', 'icon.png');
  if (!existsSync(file)) return null;
  const image = nativeImage.createFromPath(file);
  return image.isEmpty() ? null : image;
}

function createWindow(): BrowserWindow {
  const icon = developmentIcon();
  const window = new BrowserWindow({
    width: 1080,
    height: 760,
    minWidth: 720,
    minHeight: 520,
    // macOS convention: the traffic lights sit over the app's own header row.
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    backgroundColor: '#1c1c1e',
    // Windows and Linux read the window's own icon; macOS ignores it entirely and takes
    // the dock's, which is set once in the ready handler instead.
    ...(icon !== null && process.platform !== 'darwin' ? { icon } : {}),
    show: false,
    // The flags themselves live in `main/security.ts` as `WINDOW_WEB_PREFERENCES`, so a
    // test can assert the real object instead of this file's source text.
    webPreferences: { preload: PRELOAD, ...WINDOW_WEB_PREFERENCES },
  });

  hardenContents(window.webContents, DEV_SERVER);
  window.once('ready-to-show', () => window.show());

  if (DEV_SERVER !== null) void window.loadURL(DEV_SERVER);
  else void window.loadURL(pathToFileURL(RENDERER_INDEX).toString());

  return window;
}

// Electron's own hardening switch: process-level sandbox for every renderer, not only
// the ones whose `webPreferences` say so.
app.enableSandbox();

/**
 * The app's own directory, which must not be the CLI's store.
 *
 * Electron derives `userData` from the app's name, and this app's `productName` is
 * `dev-team-agents` — the same string as `paths.py`'s `APP_NAME`. So the default
 * `userData` resolves to exactly the store root: `~/Library/Application
 * Support/dev-team-agents` on macOS, holding the CLI's own `core/` and `data/`, and the
 * equivalent collision under `%APPDATA%` on Windows. Left alone, this app would write its
 * `settings.json` and its schema declaration *inside the user's store* — a second writer in
 * a tree ADR-0011 makes the single source of truth, and, since the same directory is now
 * every invocation's `cwd` and `--path`, one the CLI would also be asked about.
 *
 * Set before `whenReady`, because every later `getPath('userData')` reads the value cached
 * here. The suffix is the app's name plus `-app`, which is the same distinction
 * `packaging/` already draws between the formula and the cask.
 */
app.setPath('userData', join(app.getPath('appData'), `${app.getName()}-app`));

void app.whenReady().then(() => {
  if (!CODE_SIGNED && app.isPackaged) {
    // Visible in the console of a packaged build as well as in the UI banner. A packaged
    // app that says nothing about being unsigned is the thing this repository must not
    // produce.
    process.stderr.write(
      'dev-team-agents: this is an UNSIGNED, UNNOTARISED build. Do not distribute it.\n',
    );
  }

  // macOS only, and only unpackaged: the dock icon belongs to the running binary, not to
  // the window, so it cannot be set in `createWindow` with the others.
  if (process.platform === 'darwin') {
    const icon = developmentIcon();
    if (icon !== null) app.dock?.setIcon(icon);
  }

  hardenSession(session.defaultSession, DEV_SERVER);
  registerIpc({
    userDataDir: app.getPath('userData'),
    appVersion: app.getVersion(),
    electronVersion: process.versions.electron,
    packaged: app.isPackaged,
  });

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// Belt and braces for the "no remote content" rule: if any code path ever tries to
// create a window this file did not, it still cannot get node integration.
app.on('web-contents-created', (_event, contents) => {
  hardenContents(contents, DEV_SERVER);
});
