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
import { cliResolutionFound, fakeBridge, installBridge } from './support.js';

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
