/**
 * The main process. Creates one window, hardens it, and registers the IPC handlers.
 *
 * CommonJS. The deciding constraint is the preload: a sandboxed preload script is loaded
 * as CommonJS, which is the price of `sandbox: true` and worth paying. Compiling main and
 * preload to the same module system keeps a `require()`-of-ESM boundary out of the app for
 * the sake of one shared constants module; the renderer is bundled by Vite either way.
 */

import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { BrowserWindow, Menu, Notification, Tray, app, clipboard, nativeImage, session } from 'electron';

import { DISPLAY_NAME, aboutCredits, type AboutFacts } from './about.js';
import { terminateInFlight } from '../cli/invoke.js';
import { GATED_COMMANDS, ackNotification, listTasks, watchNotifications, watchTasks } from '../cli/operations.js';
import { registerIpc } from './ipc.js';
import { hardenContents, hardenSession, resolveDevServer, windowWebPreferences, type RendererTarget } from './security.js';
import { createFileLog, describeError, type FileLog } from './logFile.js';
import { CODE_SIGNED } from './build-info.js';
import { NotificationCenter, type NativeNotice } from './notifications.js';
import { registerNotificationIpc } from './notificationIpc.js';
import { TaskBoard, saveBoardSettings } from './taskBoard.js';
import { registerTaskBoardIpc } from './taskBoardIpc.js';
import { loginItemOptions, loginItemState, shouldHideOnClose, trayTitle, trayTooltip } from './background.js';
import { readSettings, writeBoardSettings, writeOpenAtLogin } from './settings.js';
import { CHANNELS, type BackgroundSettings, type NotificationFeed, type ProjectId } from '../shared/api.js';

/**
 * Set by `npm run dev:app` to the Vite dev server's origin. Absent — and ignored even when
 * set — in a packaged build, which is what puts the app on the production CSP and the
 * bundle-only request filter. See `resolveDevServer`.
 */
const DEV_SERVER = resolveDevServer(process.env['DEVTEAM_APP_DEV_SERVER'], app.isPackaged);

/** `dist/node/main/index.js` → `dist/renderer`. */
const RENDERER_INDEX = join(__dirname, '..', '..', 'renderer', 'index.html');

/** The one place the renderer may be, for navigation, requests and IPC senders alike. */
const RENDERER_TARGET: RendererTarget = {
  indexUrl: pathToFileURL(RENDERER_INDEX).toString(),
  bundleDir: dirname(RENDERER_INDEX),
  devServerOrigin: DEV_SERVER,
};

// ── diagnostics ───────────────────────────────────────────────────────────────

let fileLog: FileLog | null = null;
/** Set once `app.setName` has run; `getPath('logs')` read before that names the wrong directory. */
let logDirectoryFinal = false;

/**
 * stderr, and the log file under `app.getPath('logs')`. The file is created on first use
 * rather than at module load because the `logs` directory is derived from the app name,
 * which is set further down. Never throws: it is called from crash handlers.
 */
function log(message: string): void {
  try {
    process.stderr.write(`dev-team-agents: ${message}\n`);
  } catch {
    // A closed stderr (a packaged GUI launch) is the normal case, not a failure.
  }
  try {
    if (!logDirectoryFinal) return;
    fileLog ??= createFileLog(app.getPath('logs'));
    fileLog.write(message);
  } catch {
    // `getPath` can throw before the app is ready on some platforms; the line is lost, not the app.
  }
}

// Registered at module scope so it also covers the window before `whenReady`. Not
// swallowed: each is written down. Electron's own default for an uncaught main-process
// exception is a dialog and a process that keeps running; a tray app that must outlive its
// window keeps that behaviour, so these handlers record and do not exit.
process.on('uncaughtException', (error) => log(`uncaught exception: ${describeError(error)}`));
process.on('unhandledRejection', (reason) => log(`unhandled rejection: ${describeError(reason)}`));
app.on('render-process-gone', (_event, _contents, details) => {
  log(`renderer process gone: ${details.reason} (exit ${details.exitCode})`);
});
app.on('child-process-gone', (_event, details) => {
  log(`${details.type} process gone: ${details.reason} (exit ${details.exitCode})`);
});
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
function developmentIconPath(): string | null {
  if (app.isPackaged) return null;
  const file = join(__dirname, '..', '..', '..', 'build', 'icon.png');
  return existsSync(file) ? file : null;
}

function developmentIcon(): Electron.NativeImage | null {
  const file = developmentIconPath();
  if (file === null) return null;
  const image = nativeImage.createFromPath(file);
  return image.isEmpty() ? null : image;
}

/**
 * The application menu. macOS keeps Electron's default — its app menu already carries
 * "About Dev Team Agents", labelled from `app.setName`. Windows' default has no About at
 * all, so a Help menu is appended to the default roles rather than the menu rebuilt.
 */
function installMenu(): void {
  if (process.platform === 'darwin') return;
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      { role: 'fileMenu' },
      { role: 'editMenu' },
      { role: 'viewMenu' },
      { role: 'windowMenu' },
      { label: 'Help', submenu: [{ label: `About ${DISPLAY_NAME}`, click: () => app.showAboutPanel() }] },
    ]),
  );
}

// ── background mode (phase 2) ─────────────────────────────────────────────────

/** Set once a real quit starts; until then, closing the window only hides it. */
let quitting = false;
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let center: NotificationCenter | null = null;
let board: TaskBoard | null = null;
/** The window is created hidden on a login launch: the user did not open the app. */
let startHidden = false;
/** A project a notification asked to show, delivered once the renderer can hear it. */
let pendingProject: ProjectId | null = null;
/**
 * Whether the renderer has subscribed to `openProject`. `did-finish-load` can fire before
 * React's effect subscribes, and a push sent then is lost — so until the renderer says it
 * listens (by taking the pending project), the project waits here instead of being sent.
 */
let rendererListening = false;
/**
 * Live notifications. Electron drops a notification's click handler when the object is
 * garbage-collected, so a click on a banner still on screen would do nothing; each is
 * held until it is closed.
 */
const liveNotices = new Set<Notification>();

/** The tray icon: shipped via `extraResources` when packaged, read from build/ in development. */
function trayIconPath(): string | null {
  const file = app.isPackaged
    ? join(process.resourcesPath, 'tray', 'tray.png')
    : join(__dirname, '..', '..', '..', 'build', 'tray', 'tray.png');
  return existsSync(file) ? file : null;
}

function showWindow(projectId?: ProjectId): void {
  if (mainWindow === null || mainWindow.isDestroyed()) mainWindow = createWindow();
  if (process.platform === 'darwin') void app.dock?.show();
  startHidden = false;
  mainWindow.show();
  mainWindow.focus();
  if (projectId !== undefined) {
    pendingProject = projectId;
    deliverPendingProject();
  }
}

function deliverPendingProject(): void {
  if (pendingProject === null || mainWindow === null || !rendererListening) return;
  mainWindow.webContents.send(CHANNELS.openProject, pendingProject);
  pendingProject = null;
}

/** The renderer's half of the handshake: it listens now, and takes what was waiting. */
function takePendingProject(): ProjectId | null {
  rendererListening = true;
  const projectId = pendingProject;
  pendingProject = null;
  return projectId;
}

function quitForReal(): void {
  quitting = true;
  app.quit();
}

function refreshTray(feed: NotificationFeed): void {
  if (tray === null) return;
  tray.setToolTip(trayTooltip(DISPLAY_NAME, feed.unread, feed.paused));
  if (process.platform === 'darwin') tray.setTitle(trayTitle(feed.unread));
  const recent = feed.items.slice(0, 5);
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: `Open ${DISPLAY_NAME}`, click: () => showWindow() },
      { type: 'separator' },
      {
        label: 'Recent notifications',
        enabled: recent.length > 0,
        submenu:
          recent.length > 0
            ? recent.map((item) => ({
                label: `${item.projectName}: ${item.message}`.slice(0, 80),
                click: () => showWindow(item.projectId),
              }))
            : [{ label: 'None yet', enabled: false }],
      },
      {
        label: 'Pause notifications',
        type: 'checkbox',
        checked: feed.paused,
        click: (menuItem) => center?.setPaused(menuItem.checked),
      },
      { type: 'separator' },
      { label: `Quit ${DISPLAY_NAME}`, click: quitForReal },
    ]),
  );
}

function createTray(): void {
  const path = trayIconPath();
  // No icon means no tray rather than an invisible one: an empty tray image is a click
  // target the user cannot see. Then macOS still hides on close (the Dock brings it
  // back), and elsewhere closing the window quits — see `shouldHideOnClose`.
  if (path === null) return;
  tray = new Tray(nativeImage.createFromPath(path));
  tray.on('click', () => {
    // macOS opens the menu on click by convention; Windows shows the app.
    if (process.platform !== 'darwin') showWindow();
  });
  refreshTray(center?.snapshot() ?? { status: 'starting', detail: null, items: [], unread: 0, paused: false });
}

function showNative(notice: NativeNotice): void {
  const notification = new Notification({
    title: notice.title,
    body: notice.body,
    // Windows/Linux: a critical notice stays until dismissed. macOS decides persistence
    // per app in System Settings (Banners vs Alerts); there is no per-notification switch.
    ...(notice.persistent ? { timeoutType: 'never' as const } : {}),
  });
  liveNotices.add(notification);
  notification.on('click', () => {
    liveNotices.delete(notification);
    notice.onClick();
  });
  notification.on('close', () => liveNotices.delete(notification));
  notification.show();
}

async function currentBackgroundSettings(): Promise<BackgroundSettings> {
  const chosen = (await readSettings(app.getPath('userData'))).openAtLogin;
  const os = app.getLoginItemSettings(loginItemOptions(process.platform));
  return loginItemState(chosen, os, process.platform, app.isPackaged);
}

async function setOpenAtLogin(enabled: boolean): Promise<BackgroundSettings> {
  await writeOpenAtLogin(app.getPath('userData'), enabled);
  if (app.isPackaged) {
    // The same options `currentBackgroundSettings` reads with — see `loginItemOptions`.
    app.setLoginItemSettings({ openAtLogin: enabled, ...loginItemOptions(process.platform) });
  }
  return currentBackgroundSettings();
}

function launchedAtLogin(): boolean {
  if (process.argv.includes('--hidden')) return true;
  if (process.platform === 'darwin' && app.isPackaged) {
    return app.getLoginItemSettings().wasOpenedAtLogin === true;
  }
  return false;
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
    title: DISPLAY_NAME,
    backgroundColor: '#1c1c1e',
    // Windows and Linux read the window's own icon; macOS ignores it entirely and takes
    // the dock's, which is set once in the ready handler instead.
    ...(icon !== null && process.platform !== 'darwin' ? { icon } : {}),
    show: false,
    // The flags themselves live in `main/security.ts` as `WINDOW_WEB_PREFERENCES` (via `windowWebPreferences`), so a
    // test can assert the real object instead of this file's source text.
    webPreferences: { preload: PRELOAD, ...windowWebPreferences(app.isPackaged) },
  });

  hardenContents(window.webContents, RENDERER_TARGET);
  window.once('ready-to-show', () => {
    if (!startHidden) window.show();
  });
  // A (re)load drops the renderer's listeners; it says it listens again once React has
  // subscribed, by taking the pending project.
  window.webContents.on('did-start-loading', () => {
    rendererListening = false;
  });
  window.webContents.on('did-finish-load', () => {
    if (center !== null) window.webContents.send(CHANNELS.notificationFeedChanged, center.snapshot());
    if (board !== null) window.webContents.send(CHANNELS.taskBoardChanged, board.snapshot());
  });
  // Windows logoff and shutdown do not always emit `before-quit`; without this the
  // `preventDefault` below would hold the session open for a hidden window.
  window.on('session-end', () => {
    quitting = true;
  });
  // Closing hides: the notification stream lives in this process and must outlive the
  // window. Only a real quit (tray Quit, ⌘Q, logout) lets the window close — or having
  // no tray to come back through (see `shouldHideOnClose`).
  window.on('close', (event) => {
    if (!shouldHideOnClose(quitting, tray !== null, process.platform)) return;
    event.preventDefault();
    window.hide();
    // No window, no Dock icon: the menu bar is where the app lives while hidden.
    if (process.platform === 'darwin' && tray !== null) app.dock?.hide();
  });

  if (DEV_SERVER !== null) void window.loadURL(DEV_SERVER);
  else void window.loadURL(RENDERER_TARGET.indexUrl);

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
 * here. A literal, not derived from `app.getName()`: the display name is now `Dev Team
 * Agents`, and a derived path would have moved with it. `-app` is the same distinction
 * `packaging/` already draws between the formula and the cask.
 */
app.setPath('userData', join(app.getPath('appData'), 'dev-team-agents-app'));

// After `userData` is pinned, never before: the path above used to be derived from
// `app.getName()`, and renaming the app first would have moved every saved setting —
// the project names among them — to a directory nothing reads. The literal keeps the
// directory where it has always been; the name below is display only.
app.setName(DISPLAY_NAME);
logDirectoryFinal = true;

// One instance: a second would run a second `watch` and show every notification twice.
// Launching again while it runs — from the Dock, the Start menu, a shortcut — shows the
// running one instead.
//
// `app.quit()` is asynchronous: the losing instance would otherwise still reach
// `whenReady` below, create a window and a tray, and start a second `watch` — so the
// ready handler is only ever registered by the instance that holds the lock.
const primaryInstance = app.requestSingleInstanceLock();
if (!primaryInstance) {
  app.quit();
} else {
  // Before `ready` there is nothing to show yet, and constructing a `BrowserWindow` then
  // throws; `onReady` creates the window itself and shows it.
  app.on('second-instance', () => {
    if (app.isReady()) showWindow();
  });
  app.on('before-quit', () => {
    quitting = true;
    center?.dispose();
    board?.dispose();
    terminateInFlight();
  });
  void app.whenReady().then(onReady);
}

function onReady(): void {
  if (!CODE_SIGNED && app.isPackaged) {
    // Visible in the console of a packaged build as well as in the UI banner. A packaged
    // app that says nothing about being unsigned is the thing this repository must not
    // produce.
    log('this is an UNSIGNED, UNNOTARISED build. Do not distribute it.');
  }

  // macOS only, and only unpackaged: the dock icon belongs to the running binary, not to
  // the window, so it cannot be set in `createWindow` with the others.
  if (process.platform === 'darwin') {
    const icon = developmentIcon();
    if (icon !== null) app.dock?.setIcon(icon);
  }

  hardenSession(session.defaultSession, RENDERER_TARGET);
  const facts: AboutFacts = {
    appVersion: app.getVersion(),
    electronVersion: process.versions.electron,
    packaged: app.isPackaged,
    codeSigned: CODE_SIGNED,
    mutatingCommandsRun: GATED_COMMANDS.map((command) => command.join(' ')),
  };
  const setAbout = (resolution: Parameters<typeof aboutCredits>[1]) => {
    const iconPath = developmentIconPath();
    app.setAboutPanelOptions({
      applicationName: DISPLAY_NAME,
      applicationVersion: facts.appVersion,
      credits: aboutCredits(facts, resolution),
      copyright: 'dev-team-agents contributors',
      // Windows and Linux only; macOS shows the application icon, which the dock icon
      // set above already is.
      ...(iconPath !== null ? { iconPath } : {}),
    });
  };
  setAbout(null);
  installMenu();
  const ipc = registerIpc({
    userDataDir: app.getPath('userData'),
    appVersion: facts.appVersion,
    electronVersion: facts.electronVersion,
    packaged: facts.packaged,
    trustedRenderer: RENDERER_TARGET,
    onResolved: (resolution) => {
      setAbout(resolution);
      // A different CLI may mean a different store: start the stream again against it.
      void center?.restart();
      void board?.restart();
    },
  });

  center = new NotificationCenter({
    startStream: async (handlers) => {
      const ctx = await ipc.context();
      return ctx === null ? null : watchNotifications(ctx, handlers);
    },
    ack: async (id) => {
      // `notifications ack` is a write: without a declaration it would run ungated, so it
      // does not run. The record then stays unseen and is shown again next launch —
      // the lesser failure than an ungated write.
      const ctx = await ipc.gatedContext('notifications ack');
      if (ctx === null) throw new Error('withheld: no schema declaration');
      const result = await ackNotification(ctx, id);
      if (!result.ok) throw new Error(result.message);
    },
    projectName: (projectId) => ipc.projectName(projectId),
    nativeSupported: () => Notification.isSupported(),
    showNative,
    openProject: (projectId) => showWindow(projectId),
    onFeedChange: (feed) => {
      for (const window of BrowserWindow.getAllWindows()) {
        if (!window.isDestroyed()) window.webContents.send(CHANNELS.notificationFeedChanged, feed);
      }
      refreshTray(feed);
    },
    log,
  });

  const userDataDir = app.getPath('userData');
  const staleAfterSeconds = async (): Promise<number> =>
    (await readSettings(userDataDir)).board.staleAfterMinutes * 60;

  board = new TaskBoard({
    startStream: async (handlers) => {
      const ctx = await ipc.context();
      return ctx === null ? null : watchTasks(ctx, { staleAfterSeconds: await staleAfterSeconds() }, handlers);
    },
    list: async () => {
      const ctx = await ipc.context();
      if (ctx === null) {
        return {
          ok: false,
          kind: 'unavailable',
          message: 'No devteam CLI was found.',
          exitCode: null,
          command: 'devteam tasks list',
          durationMs: 0,
        };
      }
      return listTasks(ctx, { staleAfterSeconds: await staleAfterSeconds() });
    },
    onChange: (feed) => {
      for (const window of BrowserWindow.getAllWindows()) {
        if (!window.isDestroyed()) window.webContents.send(CHANNELS.taskBoardChanged, feed);
      }
    },
    log: (message) => process.stderr.write(`dev-team-agents: ${message}\n`),
  });

  registerTaskBoardIpc({
    trustedRenderer: RENDERER_TARGET,
    feed: () => board!.snapshot(),
    refresh: () => board!.refresh(),
    resumeCommand: (projectId, sessionId) => board!.resumeCommand(projectId, sessionId),
    copyText: (text) => clipboard.writeText(text),
    boardSettings: async () => (await readSettings(userDataDir)).board,
    saveBoardSettings: (next) =>
      saveBoardSettings(
        {
          read: async () => (await readSettings(userDataDir)).board,
          write: (settings) => writeBoardSettings(userDataDir, settings),
          restartStream: () => void board?.restart(),
        },
        next,
      ),
  });

  registerNotificationIpc({
    trustedRenderer: RENDERER_TARGET,
    feed: () => center!.snapshot(),
    markRead: () => center!.markRead(),
    setPaused: (paused) => center!.setPaused(paused),
    backgroundSettings: currentBackgroundSettings,
    setOpenAtLogin,
    takePendingProject,
  });

  // Tray first: whether a login launch may start hidden, and whether closing may hide,
  // both depend on there being one to come back through.
  createTray();
  startHidden = launchedAtLogin() && (tray !== null || process.platform === 'darwin');
  mainWindow = createWindow();
  if (startHidden && process.platform === 'darwin' && tray !== null) app.dock?.hide();
  void center.start();
  void board.start();

  app.on('activate', () => showWindow());
}

// Closing the last window normally hides it (see `createWindow`) and the process stays
// alive for the notification stream, so Electron's default — quit on the last window
// closing, outside macOS — must not apply. The exception is a window that really closed
// because there is no tray to reopen it from: then nothing could reach the app any more.
app.on('window-all-closed', () => {
  if (tray === null && process.platform !== 'darwin') quitForReal();
});

// Belt and braces for the "no remote content" rule: if any code path ever tries to
// create a window this file did not, it still cannot get node integration.
app.on('web-contents-created', (_event, contents) => {
  hardenContents(contents, RENDERER_TARGET);
});
