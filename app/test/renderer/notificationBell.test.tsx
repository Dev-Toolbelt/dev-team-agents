// @vitest-environment jsdom
/**
 * The header's bell. It mirrors a feed the main process owns — these tests pin what it
 * shows, what opening it tells the main process, and that it names projects rather than
 * printing their ids.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { NotificationBell } from '../../src/renderer/NotificationBell.js';
import type { NotificationFeed } from '../../src/shared/api.js';
import { appNotification, backgroundSettings, fakeBridge, installBridge, notificationFeed } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderBell(feed: NotificationFeed, overrides: Parameters<typeof fakeBridge>[0] = {}) {
  const bridge = fakeBridge({
    notificationFeed: vi.fn(() => Promise.resolve(feed)),
    markNotificationsRead: vi.fn(() => Promise.resolve({ ...feed, unread: 0 })),
    ...overrides,
  });
  installBridge(bridge);
  const onOpenProject = vi.fn();
  render(<NotificationBell onOpenProject={onOpenProject} />);
  return { bridge, onOpenProject };
}

describe('NotificationBell', () => {
  it('announces the unread count in its accessible name', async () => {
    renderBell(notificationFeed({ items: [appNotification()], unread: 1 }));
    expect(await screen.findByRole('button', { name: 'Notifications, 1 new' })).toBeInTheDocument();
  });

  it('opening it marks the list read and shows each item by project name, never by id', async () => {
    const user = userEvent.setup();
    const { bridge } = renderBell(
      notificationFeed({ items: [appNotification({ projectId: 'c0ffee-uuid', projectName: 'Storefront' })], unread: 1 }),
    );
    await user.click(await screen.findByRole('button', { name: /notifications, 1 new/i }));
    const panel = await screen.findByRole('dialog', { name: 'Notifications' });
    expect(within(panel).getByText('Storefront')).toBeInTheDocument();
    expect(within(panel).queryByText(/c0ffee-uuid/)).not.toBeInTheDocument();
    expect(bridge.markNotificationsRead).toHaveBeenCalled();
  });

  it('says the level in words, not only by icon colour', async () => {
    const user = userEvent.setup();
    renderBell(notificationFeed({ items: [appNotification({ level: 'critical' })] }));
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    expect(await screen.findByText(/Critical:/)).toBeInTheDocument();
  });

  it('presents an available update as news of its own, not as a plain info', async () => {
    const user = userEvent.setup();
    renderBell(notificationFeed({ items: [appNotification({ level: 'info', code: 'update.available' })] }));
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    expect(await screen.findByText(/Update available:/)).toBeInTheDocument();
    expect(screen.queryByText(/Info:/)).not.toBeInTheDocument();
  });

  it('clicking an item opens its project', async () => {
    const user = userEvent.setup();
    const { onOpenProject } = renderBell(notificationFeed({ items: [appNotification({ projectId: 'proj-7' })] }));
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    await user.click(await screen.findByRole('button', { name: /Storefront/ }));
    expect(onOpenProject).toHaveBeenCalledWith('proj-7');
  });

  it('shows the login item as the OS reports it, including a registration macOS refused', async () => {
    const user = userEvent.setup();
    renderBell(notificationFeed(), {
      backgroundSettings: vi.fn(() =>
        Promise.resolve(
          backgroundSettings({
            openAtLogin: true,
            loginItemStatus: 'not-registered',
            detail: 'macOS did not register it. This build is not signed.',
          }),
        ),
      ),
    });
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    expect(await screen.findByRole('switch', { name: /start at login/i })).toBeChecked();
    expect(screen.getByText(/did not register it/)).toBeInTheDocument();
  });

  it('disables the login switch on a development build, and says why', async () => {
    const user = userEvent.setup();
    renderBell(notificationFeed(), {
      backgroundSettings: vi.fn(() =>
        Promise.resolve(backgroundSettings({ loginItemStatus: 'unsupported', detail: 'A development build runs the stock Electron binary.' })),
      ),
    });
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    expect(await screen.findByRole('switch', { name: /start at login/i })).toBeDisabled();
  });

  it('pausing goes to the main process', async () => {
    const user = userEvent.setup();
    const { bridge } = renderBell(notificationFeed());
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    await user.click(await screen.findByRole('switch', { name: /pause system notifications/i }));
    expect(bridge.setNotificationsPaused).toHaveBeenCalledWith(true);
  });

  it('shows a refused login-item change, keeps the previous state, and leaves no unhandled rejection', async () => {
    const user = userEvent.setup();
    const unhandled = vi.fn();
    process.on('unhandledRejection', unhandled);
    const { bridge } = renderBell(notificationFeed(), {
      backgroundSettings: vi.fn(() => Promise.resolve(backgroundSettings({ openAtLogin: false }))),
      setOpenAtLogin: vi.fn(() => Promise.reject(new Error('settings.json is corrupt'))),
    });
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    await user.click(await screen.findByRole('switch', { name: /start at login/i }));
    expect(await screen.findByText(/settings\.json is corrupt/)).toBeInTheDocument();
    expect(bridge.setOpenAtLogin).toHaveBeenCalledWith(true);
    expect(screen.getByRole('switch', { name: /start at login/i })).not.toBeChecked();
    await new Promise((resolve) => setTimeout(resolve, 0));
    process.off('unhandledRejection', unhandled);
    expect(unhandled).not.toHaveBeenCalled();
  });

  it('says so when the login setting cannot be read, and survives failing reads', async () => {
    const user = userEvent.setup();
    const { bridge } = renderBell(notificationFeed(), {
      notificationFeed: vi.fn(() => Promise.reject(new Error('untrusted sender'))),
      markNotificationsRead: vi.fn(() => Promise.reject(new Error('untrusted sender'))),
      backgroundSettings: vi.fn(() => Promise.reject(new Error('untrusted sender'))),
    });
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    expect(await screen.findByText(/could not read the start-at-login setting/i)).toBeInTheDocument();
    expect(bridge.markNotificationsRead).toHaveBeenCalled();
    expect(screen.getByRole('switch', { name: /pause system notifications/i })).not.toBeChecked();
  });

  it('keeps the pause switch where it was when the change is refused', async () => {
    const user = userEvent.setup();
    renderBell(notificationFeed(), {
      setNotificationsPaused: vi.fn(() => Promise.reject(new Error('refused'))),
    });
    await user.click(await screen.findByRole('button', { name: 'Notifications' }));
    const toggle = await screen.findByRole('switch', { name: /pause system notifications/i });
    await user.click(toggle);
    expect(toggle).not.toBeChecked();
  });
});
