// @vitest-environment jsdom
/**
 * The shell. What it must never do: sit on "Looking for a devteam CLI…" after a startup
 * call rejected, or let one screen's render error take the header, tabs and bell with it.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from '../../src/renderer/App.js';
import { isPrerelease } from '../../src/shared/appVersion.js';
import { buildInfo, cliResolutionFound, fakeBridge, installBridge } from './support.js';

const state = vi.hoisted(() => ({ doctorThrows: true }));

vi.mock('../../src/renderer/screens/Doctor.js', () => ({
  Doctor: () => {
    if (state.doctorThrows) throw new Error('doctor exploded');
    return <p>doctor is fine</p>;
  },
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  state.doctorThrows = true;
});

describe('App — start-up', () => {
  it('shows the failure and a retry when a start-up call rejects, and recovers on retry', async () => {
    const user = userEvent.setup();
    const resolveCli = vi
      .fn()
      .mockRejectedValueOnce(new Error('main process gone'))
      .mockResolvedValue(cliResolutionFound());
    installBridge(fakeBridge({ resolveCli }));

    render(<App />);

    expect(await screen.findByText(/could not finish its start-up checks/i)).toBeInTheDocument();
    expect(screen.getByText(/main process gone/)).toBeInTheDocument();
    expect(screen.queryByText(/running the first-run checks/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /try again/i }));

    expect(await screen.findByRole('tab', { name: 'Projects' })).toBeInTheDocument();
    expect(screen.queryByText(/could not finish its start-up checks/i)).not.toBeInTheDocument();
  });
});

describe('App — the header names this app’s version', () => {
  it('shows the app version before the store’s, with a beta badge while it is a pre-release', async () => {
    installBridge(fakeBridge({ buildInfo: vi.fn(() => Promise.resolve(buildInfo({ appVersion: '0.0.0' }))) }));
    render(<App />);
    const version = await screen.findByText('app 0.0.0');
    expect(version).toHaveTextContent('beta');
    const store = screen.getByText(/^store /);
    expect(version.compareDocumentPosition(store) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('drops the badge at a stable version', async () => {
    installBridge(fakeBridge({ buildInfo: vi.fn(() => Promise.resolve(buildInfo({ appVersion: '1.2.0' }))) }));
    render(<App />);
    expect(await screen.findByText('app 1.2.0')).not.toHaveTextContent('beta');
  });

  it('calls 0.x, suffixed and unparseable versions pre-releases, and plain ≥1 versions stable', () => {
    for (const version of ['0.0.0', '0.9.3', '1.0.0-beta.1', 'v2.0.0-rc.1', 'dev', '']) {
      expect(isPrerelease(version), version).toBe(true);
    }
    for (const version of ['1.0.0', 'v1.4.2', '2.0.0+build.7']) {
      expect(isPrerelease(version), version).toBe(false);
    }
  });
});

describe('App — pending project handshake', () => {
  it('still renders when takePendingProject rejects', async () => {
    installBridge(fakeBridge({ takePendingProject: vi.fn(() => Promise.reject(new Error('untrusted sender'))) }));
    render(<App />);
    expect(await screen.findByRole('tab', { name: 'Projects' })).toBeInTheDocument();
  });
});

describe('App — a failing screen', () => {
  it('keeps the shell, names the screen, and recovers on Try again', async () => {
    const user = userEvent.setup();
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    installBridge(fakeBridge());

    render(<App />);
    await user.click(await screen.findByRole('tab', { name: 'Diagnosis' }));

    expect(await screen.findByText(/The Diagnosis screen hit an unexpected error/)).toBeInTheDocument();
    expect(screen.getByText('doctor exploded')).toBeInTheDocument();
    // The shell is still there: the other tabs work.
    expect(screen.getByRole('tab', { name: 'Global Skills' })).toBeInTheDocument();

    state.doctorThrows = false;
    await user.click(screen.getByRole('button', { name: /try again/i }));

    expect(await screen.findByText('doctor is fine')).toBeInTheDocument();
  });

  it('moves focus to the fallback when a screen throws', async () => {
    const user = userEvent.setup();
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    installBridge(fakeBridge());

    render(<App />);
    await user.click(await screen.findByRole('tab', { name: 'Diagnosis' }));

    const fallback = await screen.findByRole('alert');
    await waitFor(() => expect(fallback).toHaveFocus());
  });
});

describe('App — the Integrations tab', () => {
  it('keeps a typed token while another tab is shown', async () => {
    state.doctorThrows = false;
    const user = userEvent.setup();
    const notConnected = {
      name: 'github', title: 'GitHub', description: '', homepage: null,
      auth: { kind: 'token', label: 'Personal access token', help: null, has_token: false, stale: false, backend: null },
      fields: [], account: {}, project: null, detected: {}, connected: false, project_configured: false,
      status: { state: 'not_connected', checked_at: null, summary: '', facts: [] },
    };
    const integrationList = vi.fn(() => Promise.resolve({ ok: true as const, data: { project_id: null, integrations: [notConnected] }, command: 'devteam integration list', durationMs: 0 }));
    installBridge(fakeBridge({ integrationList } as never));
    render(<App />);
    await user.click(await screen.findByRole('tab', { name: 'Integrations' }));
    await user.click(await screen.findByRole('button', { name: 'Show GitHub details' }));
    await user.type(await screen.findByLabelText('Personal access token'), 'ghp_draft');
    await user.click(screen.getByRole('tab', { name: 'Diagnosis' }));
    await user.click(screen.getByRole('tab', { name: 'Integrations' }));
    expect(screen.getByLabelText('Personal access token')).toHaveValue('ghp_draft');
  });
});
