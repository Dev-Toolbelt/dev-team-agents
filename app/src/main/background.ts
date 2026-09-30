/**
 * Running in the background (phase 2): what the app does when its window is closed, and
 * whether it starts at login.
 *
 * The notification stream lives in the main process (`notifications.ts`). That only
 * helps if the main process outlives the window: macOS keeps an app alive with no
 * window by convention, Windows does not — closing the last window quits. So:
 *
 *   - **closing the window hides it**, on both platforms, and a tray / menu-bar icon is
 *     how to bring it back or quit. Quitting for real is the tray's Quit, ⌘Q on macOS, or
 *     the OS shutting down;
 *   - **one instance only** — two would run two `watch` children and show every
 *     notification twice;
 *   - **start at login is opt-in**, off by default: changing what the OS launches is a
 *     change to the user's machine, not to this app.
 *
 * The functions here are pure so they can be tested without Electron; `index.ts` owns
 * the native objects.
 */

import type { BackgroundSettings, LoginItemStatus } from '../shared/api.js';

/**
 * What `app.getLoginItemSettings()` returns, reduced to the fields this reads. `status`
 * is macOS 13+ only (SMAppService); elsewhere only `openAtLogin` exists.
 */
export interface OsLoginItem {
  readonly openAtLogin: boolean;
  readonly status?: string;
}

/**
 * The login-item state the UI shows: the OS's answer, never the user's choice alone.
 *
 * On an unsigned macOS build, registration can be refused or left pending approval; a
 * toggle that said "on" while the OS said otherwise would be the app lying about the
 * user's machine.
 */
export function loginItemState(
  chosen: boolean,
  os: OsLoginItem,
  platform: NodeJS.Platform,
  packaged: boolean,
): BackgroundSettings {
  if (!packaged) {
    return {
      openAtLogin: chosen,
      loginItemStatus: 'unsupported',
      detail:
        'A development build runs the stock Electron binary, which is not this app: there is nothing to register. It works in a packaged build.',
    };
  }
  if (platform === 'darwin' && os.status !== undefined) {
    const status = macStatus(os.status);
    return { openAtLogin: chosen, loginItemStatus: status, detail: MAC_DETAIL[status] };
  }
  return {
    openAtLogin: chosen,
    loginItemStatus: os.openAtLogin ? 'enabled' : 'disabled',
    detail: chosen && !os.openAtLogin ? 'The system did not record the login item.' : null,
  };
}

function macStatus(status: string): LoginItemStatus {
  switch (status) {
    case 'enabled':
      return 'enabled';
    case 'requires-approval':
      return 'requires-approval';
    case 'not-registered':
    case 'not-found':
      return 'not-registered';
    default:
      return 'disabled';
  }
}

const MAC_DETAIL: Readonly<Record<LoginItemStatus, string | null>> = {
  enabled: null,
  disabled: null,
  'requires-approval':
    'macOS registered it but needs your approval: System Settings → General → Login Items.',
  'not-registered':
    'macOS did not register it. This build is not signed, and macOS may refuse login items from unsigned apps.',
  unsupported: null,
};

/** The tray tooltip: the app, and how much is waiting. */
export function trayTooltip(appName: string, unread: number, paused: boolean): string {
  const parts = [appName];
  if (unread > 0) parts.push(`${unread} new notification${unread === 1 ? '' : 's'}`);
  if (paused) parts.push('notifications paused');
  return parts.join(' — ');
}

/**
 * The macOS menu-bar title beside the icon: the unread count, or nothing. Windows has no
 * title slot beside a tray icon; the tooltip carries the count there.
 */
export function trayTitle(unread: number): string {
  if (unread <= 0) return '';
  return unread > 99 ? '99+' : String(unread);
}

/**
 * Whether a window `close` should hide instead of closing. Only a real quit — the tray's
 * Quit, ⌘Q, the OS logging out — lets it close; everything else is "hide".
 */
export function shouldHideOnClose(quitting: boolean): boolean {
  return !quitting;
}
