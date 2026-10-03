// @vitest-environment jsdom
/**
 * The first-run wizard mounted in the real shell (ADR-0030): the order, the three clicks, the
 * words, the keyboard and focus, and who skips it.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, configure, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from '../../src/renderer/App.js';
import {
  authState,
  cliResolutionFound,
  cliResolutionNotFound,
  detectReport,
  doctorReport,
  fakeBridge,
  installBridge,
  ok,
  project,
  signedOutState,
  startReport,
} from './support.js';

// The whole shell mounts here (CLI, account, machine check, then the step): give a loaded
// machine more than the default second to get there.
configure({ asyncUtilTimeout: 5000 });

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const FORBIDDEN = /\b(bind\w*|bound|layouts?|stores?|stored|preference layers?)\b/i;

/** The wizard's own area: the page header carries the app's name and version, not first-run copy. */
const wizard = () => within(screen.getByRole('main'));

function freshBridge(overrides: Parameters<typeof fakeBridge>[0] = {}) {
  return fakeBridge({
    onboardingState: vi.fn(() => Promise.resolve({ completed: false })),
    chooseProjectDirectory: vi.fn(() => Promise.resolve({ chosen: true as const, path: '/work/my-app' })),
    ...overrides,
  });
}

describe('the first-run wizard', () => {
  it('takes three clicks after sign-in, and the app only opens its tabs once it is finished', async () => {
    const user = userEvent.setup();
    const bridge = freshBridge();
    installBridge(bridge);
    render(<App />);

    // Signed in, machine fine: the folder step is the first thing there is to do.
    expect(await screen.findByRole('heading', { name: 'Choose your project folder' })).toHaveFocus();
    expect(screen.queryByRole('tab', { name: 'Projects' })).not.toBeInTheDocument();
    expect(wizard().getByRole('listitem', { current: 'step' })).toHaveTextContent('Folder');
    expect(wizard().getByText('Get started')).toBeInTheDocument();

    // Click 1: choose the folder. Nothing is set up yet.
    await user.click(screen.getByRole('button', { name: 'Choose a folder' }));
    expect(bridge.detectProject).toHaveBeenCalledWith('/work/my-app');
    expect(await screen.findByRole('heading', { name: 'Does this look right?' })).toHaveFocus();
    expect(bridge.startProject).not.toHaveBeenCalled();
    expect(screen.getByLabelText('AI coding tool')).toHaveValue('claude');
    expect(screen.getByLabelText('This project is')).toHaveValue('maintenance');

    // Click 2: confirm what was found.
    await user.click(screen.getByRole('button', { name: 'Looks right' }));
    expect(await screen.findByRole('heading', { name: 'Start your first task' })).toBeInTheDocument();
    expect(screen.getByText('Audit this module')).toBeInTheDocument();
    expect(bridge.startProject).not.toHaveBeenCalled();

    // Click 3: start. The project is set up with what was detected, then the terminal opens.
    await user.click(screen.getByRole('button', { name: 'Start first task' }));
    expect(await screen.findByRole('heading', { name: 'You are all set' })).toBeInTheDocument();
    expect(bridge.startProject).toHaveBeenCalledWith({ path: '/work/my-app', provider: 'claude', type: 'maintenance' });
    expect(bridge.launchFirstTask).toHaveBeenCalledWith('/work/my-app');
    expect(screen.getByText('Your first task is open in a terminal window.')).toBeInTheDocument();

    // The five featured commands, typed the way the chosen provider types them.
    for (const name of ['plan', 'fix', 'review', 'commit', 'pr']) {
      expect(screen.getByText(`/devteam:${name}`)).toBeInTheDocument();
    }
    expect(screen.queryByRole('tab', { name: 'Projects' })).not.toBeInTheDocument();

    // Finishing records it and reveals the full app (Advanced settings).
    await user.click(screen.getByRole('button', { name: 'Finish' }));
    expect(await screen.findByRole('tab', { name: 'Projects' })).toBeInTheDocument();
    expect(bridge.completeOnboarding).toHaveBeenCalledTimes(1);
  });

  it('never uses the framework’s own vocabulary on any step', async () => {
    const user = userEvent.setup();
    installBridge(freshBridge());
    render(<App />);

    const check = () => expect(screen.getByRole('main').textContent).not.toMatch(FORBIDDEN);

    await screen.findByRole('heading', { name: 'Choose your project folder' });
    check();
    expect(document.querySelector('header')!.textContent).not.toMatch(FORBIDDEN);
    await user.click(screen.getByRole('button', { name: 'Choose a folder' }));
    await screen.findByRole('heading', { name: 'Does this look right?' });
    check();
    await user.click(screen.getByRole('button', { name: 'Looks right' }));
    await screen.findByRole('heading', { name: 'Start your first task' });
    check();
    await user.click(screen.getByRole('button', { name: 'Start first task' }));
    await screen.findByRole('heading', { name: 'You are all set' });
    check();
  });

  it('lets each detected value be changed with one select, and sends the changed values', async () => {
    const user = userEvent.setup();
    const bridge = freshBridge();
    installBridge(bridge);
    render(<App />);

    await user.click(await screen.findByRole('button', { name: 'Choose a folder' }));
    await user.selectOptions(await screen.findByLabelText('AI coding tool'), 'codex');
    await user.selectOptions(screen.getByLabelText('This project is'), 'new');
    await user.click(screen.getByRole('button', { name: 'Looks right' }));
    await user.click(await screen.findByRole('button', { name: 'Start first task' }));

    await waitFor(() => expect(bridge.startProject).toHaveBeenCalledWith({ path: '/work/my-app', provider: 'codex', type: 'new' }));
  });

  it('shows the command to copy, and does not claim the terminal opened, when a provider has no launch', async () => {
    const user = userEvent.setup();
    const detect = detectReport({
      first_task: { kind: 'audit', target: 'src', label: 'Audit this module', read_only: true, launch: null },
    });
    const bridge = freshBridge({
      detectProject: vi.fn(() => Promise.resolve(ok(detect))),
      startProject: vi.fn(() => Promise.resolve(ok(startReport({ detect })))),
    });
    installBridge(bridge);
    render(<App />);

    await user.click(await screen.findByRole('button', { name: 'Choose a folder' }));
    await user.click(await screen.findByRole('button', { name: 'Looks right' }));
    await user.click(await screen.findByRole('button', { name: 'Start first task' }));

    expect(await screen.findByText(/did not open on its own/)).toBeInTheDocument();
    expect(bridge.launchFirstTask).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Command')).toHaveTextContent('/devteam:audit src');
    expect(screen.getByRole('button', { name: 'Copy command' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Open it again' })).not.toBeInTheDocument();
  });

  it('offers Copy command beside the opened terminal, and copies the shell-quoted command', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    installBridge(freshBridge());
    render(<App />);

    await user.click(await screen.findByRole('button', { name: 'Choose a folder' }));
    await user.click(await screen.findByRole('button', { name: 'Looks right' }));
    await user.click(await screen.findByRole('button', { name: 'Start first task' }));
    await user.click(await screen.findByRole('button', { name: 'Copy command' }));

    expect(writeText).toHaveBeenCalledWith("cd /work/my-app && claude --permission-mode plan '/devteam:audit src --report-only'");
    expect(await screen.findByText('Copied')).toBeInTheDocument();
  });

  it('shows a problem with the folder and stays on that step', async () => {
    const user = userEvent.setup();
    const bridge = freshBridge({
      detectProject: vi.fn(() => Promise.resolve({ ok: false as const, kind: 'environment' as const, message: 'that folder cannot be read', exitCode: 3, command: 'devteam detect', durationMs: 1 })),
    });
    installBridge(bridge);
    render(<App />);

    await user.click(await screen.findByRole('button', { name: 'Choose a folder' }));
    expect(await screen.findByText('that folder cannot be read')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Choose your project folder' })).toBeInTheDocument();
  });

  it('does nothing when the folder picker is dismissed', async () => {
    const user = userEvent.setup();
    const bridge = freshBridge({ chooseProjectDirectory: vi.fn(() => Promise.resolve({ chosen: false as const })) });
    installBridge(bridge);
    render(<App />);

    await user.click(await screen.findByRole('button', { name: 'Choose a folder' }));
    expect(bridge.detectProject).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: 'Choose your project folder' })).toBeInTheDocument();
  });
});

describe('who skips the wizard', () => {
  it('a returning user with a project goes straight to the app', async () => {
    installBridge(
      freshBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))) }),
    );
    render(<App />);
    expect(await screen.findByRole('tab', { name: 'Projects' })).toBeInTheDocument();
    expect(screen.queryByText('Get started')).not.toBeInTheDocument();
  });

  it('a user who finished it goes straight to the app, even with no project', async () => {
    installBridge(fakeBridge());
    render(<App />);
    expect(await screen.findByRole('tab', { name: 'Projects' })).toBeInTheDocument();
    expect(screen.queryByText('Get started')).not.toBeInTheDocument();
  });

  it('a failed read of the flag never blocks the app behind a wizard', async () => {
    installBridge(freshBridge({ onboardingState: vi.fn(() => Promise.reject(new Error('gone'))) }));
    render(<App />);
    expect(await screen.findByRole('tab', { name: 'Projects' })).toBeInTheDocument();
  });
});

describe('the steps before the project', () => {
  it('starts with the install when there is no CLI, offering it on macOS too', async () => {
    vi.spyOn(window.navigator, 'platform', 'get').mockReturnValue('MacIntel');
    const user = userEvent.setup();
    const installCli = vi.fn(() =>
      Promise.resolve({
        outcome: 'manual' as const,
        message: 'Homebrew was not found. Open Terminal, paste this command and press Return; then come back and choose Look again.',
        command: 'curl -fsSL https://example.test/install-cli.sh | bash',
      }),
    );
    installBridge(freshBridge({ resolveCli: vi.fn(() => Promise.resolve(cliResolutionNotFound())), installCli }));
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Install the devteam tool' })).toHaveFocus();
    expect(wizard().getByRole('listitem', { current: 'step' })).toHaveTextContent('Install');
    await user.click(screen.getByRole('button', { name: 'Install the CLI' }));

    expect(await screen.findByText(/Homebrew was not found/)).toBeInTheDocument();
    expect(screen.getByLabelText('Command')).toHaveTextContent('curl -fsSL https://example.test/install-cli.sh | bash');
    expect(screen.getByRole('button', { name: 'Copy command' })).toBeInTheDocument();
  });

  it('asks for sign-in through the existing sign-in screen, and nothing about the project yet', async () => {
    installBridge(
      freshBridge({ authCheck: vi.fn(() => Promise.resolve(ok(signedOutState({ gate_mode: 'enforce' }), { outcome: 'findings' }))) }),
    );
    render(<App />);

    expect(await screen.findByText('Sign in to dev-team-agents')).toBeInTheDocument();
    expect(wizard().getByRole('listitem', { current: 'step' })).toHaveTextContent('Sign in');
    expect(screen.queryByRole('button', { name: 'Choose a folder' })).not.toBeInTheDocument();
  });

  it('shows a Fix button only for an auto-fixable finding, runs it on the click, and only copies the rest', async () => {
    const user = userEvent.setup();
    const report = doctorReport({
      status: 'warn',
      findings: [
        { level: 'warn', category: 'git', message: 'git is not installed', fix: 'brew install git', auto_fixable: true },
        { level: 'warn', category: 'provider', message: 'No AI coding tool found', fix: 'npm install -g some-tool', auto_fixable: false },
        { level: 'ok', category: 'python', message: 'Python 3.12', fix: null, auto_fixable: false },
      ],
    });
    const doctorMachine = vi.fn().mockResolvedValueOnce(ok(report, { outcome: 'findings' })).mockResolvedValue(ok(doctorReport()));
    const runMachineFix = vi.fn(() => Promise.resolve({ ran: true as const, succeeded: true, message: 'Done.' }));
    installBridge(freshBridge({ doctorMachine, runMachineFix }));
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Checking this computer' })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /^Fix/ })).toHaveLength(1);
    // The command of a finding that is not auto-fixable is shown to copy, never run.
    expect(screen.getByLabelText('Command')).toHaveTextContent('npm install -g some-tool');
    expect(runMachineFix).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Fix: git is not installed' }));
    expect(runMachineFix).toHaveBeenCalledWith(0);
    expect(doctorMachine).toHaveBeenCalledTimes(2);
    // The second check is clean, so the step passes by itself.
    expect(await screen.findByRole('heading', { name: 'Choose your project folder' })).toBeInTheDocument();
  });

  it('lets the person continue past a prerequisite they will handle themselves', async () => {
    const user = userEvent.setup();
    const report = doctorReport({
      status: 'warn',
      findings: [{ level: 'warn', category: 'provider', message: 'No AI coding tool found', fix: null, auto_fixable: false }],
    });
    installBridge(freshBridge({ doctorMachine: vi.fn(() => Promise.resolve(ok(report, { outcome: 'findings' }))) }));
    render(<App />);

    await user.click(await screen.findByRole('button', { name: 'Continue anyway' }));
    expect(await screen.findByRole('heading', { name: 'Choose your project folder' })).toBeInTheDocument();
  });

  it('passes the machine step by itself when the account is signed in and nothing is missing', async () => {
    const doctorMachine = vi.fn(() => Promise.resolve(ok(doctorReport())));
    installBridge(freshBridge({ doctorMachine, authCheck: vi.fn(() => Promise.resolve(ok(authState()))) }));
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Choose your project folder' })).toBeInTheDocument();
    expect(doctorMachine).toHaveBeenCalledTimes(1);
    expect(cliResolutionFound().found).toBe(true);
  });
});
