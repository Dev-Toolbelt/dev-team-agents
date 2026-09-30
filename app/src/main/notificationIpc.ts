/**
 * The IPC channels for notifications and background mode.
 *
 * Kept apart from `ipc.ts`, whose channels each run a CLI command: none of these do. The
 * feed is the notification center's in-memory state, and the login-item channels talk
 * to the OS. Every argument from the renderer is re-checked here — a `boolean` in the
 * type is a compile-time claim, and this is a process boundary.
 */

import { ipcMain } from 'electron';

import { CHANNELS, type BackgroundSettings, type NotificationFeed } from '../shared/api.js';

export interface NotificationIpcDeps {
  readonly feed: () => NotificationFeed;
  readonly markRead: () => NotificationFeed;
  readonly setPaused: (paused: boolean) => NotificationFeed;
  readonly backgroundSettings: () => Promise<BackgroundSettings>;
  readonly setOpenAtLogin: (enabled: boolean) => Promise<BackgroundSettings>;
}

export function registerNotificationIpc(deps: NotificationIpcDeps): void {
  ipcMain.handle(CHANNELS.notificationFeed, () => deps.feed());
  ipcMain.handle(CHANNELS.markNotificationsRead, () => deps.markRead());
  ipcMain.handle(CHANNELS.setNotificationsPaused, (_event, paused: unknown) => {
    // Anything but a real boolean changes nothing and returns the current feed.
    if (typeof paused !== 'boolean') return deps.feed();
    return deps.setPaused(paused);
  });
  ipcMain.handle(CHANNELS.backgroundSettings, () => deps.backgroundSettings());
  ipcMain.handle(CHANNELS.setOpenAtLogin, async (_event, enabled: unknown) => {
    if (typeof enabled !== 'boolean') return deps.backgroundSettings();
    return deps.setOpenAtLogin(enabled);
  });
}
