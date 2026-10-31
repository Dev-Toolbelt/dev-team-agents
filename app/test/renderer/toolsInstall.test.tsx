// @vitest-environment jsdom
/** The tools step that follows a bind (ADR-0060): reported on its own, never able to fail the bind. */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../../src/components/ui/sonner.js';
import { runToolsInstall } from '../../src/renderer/toolsInstall.js';
import { Projects } from '../../src/renderer/screens/Projects.js';
import type { ToolsReport } from '../../src/shared/api.js';
import { bindReport, environment, fail, fakeBridge, installBridge, ok } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const toolsReport = (tools: ToolsReport['tools']): ToolsReport => ({ bin_dir: '/b', platform: 'linux', skipped_all: null, on_path: true, tools });
const record = (name: string, status: ToolsReport['tools'][number]['status'], reason: string | null = null) => ({
  name,
  version: null,
  purpose: '',
  status,
  method: null,
  path: null,
  reason,
});

describe('runToolsInstall', () => {
  it('toasts the installed tools', async () => {
    installBridge(fakeBridge({ installTools: vi.fn(() => Promise.resolve(ok(toolsReport([record('jq', 'installed')])))) }));
    render(<Toaster />);
    await runToolsInstall();
    expect(await screen.findByText(/Installed helper tools: jq/)).toBeInTheDocument();
  });

  it('keeps a failed tool on screen with its reason', async () => {
    installBridge(fakeBridge({ installTools: vi.fn(() => Promise.resolve(ok(toolsReport([record('semgrep', 'failed', 'offline')])))) }));
    render(<Toaster />);
    await runToolsInstall();
    expect(await screen.findByText(/1 helper tool could not be installed/)).toBeInTheDocument();
    expect(screen.getByText(/semgrep \(failed\): offline/)).toBeInTheDocument();
  });

  it('turns a refused or timed-out install, and a rejected call, into a toast and never throws', async () => {
    const installTools = vi.fn().mockResolvedValueOnce(fail('timeout')).mockRejectedValueOnce(new Error('ipc down'));
    installBridge(fakeBridge({ installTools }));
    render(<Toaster />);
    await expect(runToolsInstall()).resolves.toBeUndefined();
    await expect(runToolsInstall()).resolves.toBeUndefined();
    expect(installTools).toHaveBeenCalledTimes(2);
  });
});

describe('Projects — the tools step after a bind', () => {
  async function bindOnce(bridgeOverrides: Parameters<typeof fakeBridge>[0]) {
    const user = userEvent.setup();
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory: vi.fn(() => Promise.resolve({ chosen: true as const, path: '/Users/dev/p' })),
        ...bridgeOverrides,
      }),
    );
    render(
      <>
        <Projects environment={environment()} />
        <Toaster />
      </>,
    );
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^new project$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await within(dialog).findByText('/Users/dev/p');
    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));
    return dialog;
  }

  it('runs the install after a successful bind, and a failed install leaves the bind done', async () => {
    const bindProject = vi.fn(() => Promise.resolve(ok(bindReport({ merged_project_files: ['.gitignore'] }))));
    const installTools = vi.fn(() => Promise.resolve(fail('timeout')));
    const dialog = await bindOnce({ bindProject, installTools });
    await waitFor(() => expect(installTools).toHaveBeenCalledTimes(1));
    // The bind's own result is still on screen; the failure is a toast beside it.
    expect(await within(dialog).findByText('.gitignore')).toBeInTheDocument();
    expect(within(dialog).queryByRole('alert')).not.toBeInTheDocument();
  });

  it('does not run the install when the bind failed', async () => {
    const bindProject = vi.fn(() => Promise.resolve(fail('exit')));
    const installTools = vi.fn(() => Promise.resolve(ok(toolsReport([]))));
    await bindOnce({ bindProject, installTools });
    await waitFor(() => expect(bindProject).toHaveBeenCalled());
    expect(installTools).not.toHaveBeenCalled();
  });
});
