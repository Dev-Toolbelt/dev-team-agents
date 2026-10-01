// @vitest-environment jsdom
/**
 * The Credentials tab. What it must never do: show or prefill a secret, send an op for a leaf
 * nobody touched, overwrite a file that changed on disk, or lose typed edits silently.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProjectCredentials } from '../../src/renderer/credentials/ProjectCredentials.js';
import { ProjectSettings } from '../../src/renderer/screens/ProjectSettings.js';
import { CREDENTIALS_ALREADY_EXISTS, CREDENTIALS_HASH_CONFLICT, CREDENTIALS_SAVED_UNREADABLE } from '../../src/shared/api.js';
import { credentialsView, deferred, environment, fail, fakeBridge, installBridge, ok, project } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

type Overrides = Parameters<typeof fakeBridge>[0];

function renderTab(overrides: Overrides = {}) {
  const bridge = fakeBridge(overrides);
  installBridge(bridge);
  const onDirtyChange = vi.fn();
  render(<ProjectCredentials project={project()} environment={environment()} onDirtyChange={onDirtyChange} onRunningChange={vi.fn()} />);
  return { bridge, user: userEvent.setup(), onDirtyChange };
}

/** The secret field whose input id is `id`, found through its label, since several share the name Password. */
function secretBox(id: string): HTMLElement {
  const label = document.getElementById(`${id}-label`);
  if (label?.parentElement == null) throw new Error(`no secret field ${id}`);
  return label.parentElement;
}

function setAppPassword(view: ReturnType<typeof credentialsView>): void {
  const app = view.data?.['app'] as { staging: { password: unknown } };
  app.staging.password = { secret: true, set: true };
}

const APP_PASSWORD = 'cred-app-staging-password';

describe('ProjectCredentials — load states', () => {
  it('shows a loading line while the file is read', async () => {
    const pending = deferred<ReturnType<typeof ok>>();
    renderTab({ credentialsLocalShow: vi.fn(() => pending.promise as never) });
    expect(screen.getByText(/Running cred local show/)).toBeInTheDocument();
    pending.resolve(ok(credentialsView()));
    expect(await screen.findByText('Work feedback')).toBeInTheDocument();
  });

  it('offers to create a missing file, showing its path', async () => {
    const missing = credentialsView({ exists: false, valid: false, hash: null, data: null });
    const { bridge, user } = renderTab({
      credentialsLocalShow: vi.fn(() => Promise.resolve(ok(missing))),
      credentialsLocalInit: vi.fn(() => Promise.resolve(ok(credentialsView()))),
    });

    expect(await screen.findByText('There is no credentials file yet.')).toBeInTheDocument();
    expect(screen.getAllByText(missing.path).length).toBeGreaterThan(0);
    expect(screen.queryByText('Work feedback')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Create file' }));
    expect(bridge.credentialsLocalInit).toHaveBeenCalledWith('proj-1');
    expect(await screen.findByText('Work feedback')).toBeInTheDocument();
    expect(screen.queryByText('There is no credentials file yet.')).not.toBeInTheDocument();
  });

  it('reloads when the file turns out to exist already', async () => {
    const missing = credentialsView({ exists: false, valid: false, hash: null, data: null });
    const show = vi.fn().mockResolvedValueOnce(ok(missing)).mockResolvedValue(ok(credentialsView()));
    const { bridge, user } = renderTab({
      credentialsLocalShow: show,
      credentialsLocalInit: vi.fn(() => Promise.resolve(fail('exists', { kind: 'conflict', exitCode: 4, reason: CREDENTIALS_ALREADY_EXISTS }))),
    });
    await user.click(await screen.findByRole('button', { name: 'Create file' }));
    expect(await screen.findByText('Work feedback')).toBeInTheDocument();
    expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(2);
  });

  it('explains an invalid file with its line and column, and offers no form or Save', async () => {
    renderTab({
      credentialsLocalShow: vi.fn(() =>
        Promise.resolve(ok(credentialsView({ valid: false, data: null, error: { message: 'Unexpected token }', line: 4, column: 9 } }))),
      ),
    });
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('not valid JSON');
    expect(alert).toHaveTextContent('Unexpected token }');
    expect(alert).toHaveTextContent('line 4, column 9');
    expect(screen.queryByText('Work feedback')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save/ })).not.toBeInTheDocument();
  });

  it('shows the CLI problem when the file cannot be read', async () => {
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(fail('cred local show exploded'))) });
    expect(await screen.findByText(/cred local show exploded/)).toBeInTheDocument();
  });

  it('renders the work feedback card, the categories and their environments', async () => {
    renderTab();
    expect(await screen.findByRole('switch', { name: 'Work feedback active' })).toBeChecked();
    expect(screen.getByLabelText('Check-in interval (minutes)')).toHaveValue('5');
    expect(screen.getByText('devops')).toBeInTheDocument();
    expect(screen.getByText('app')).toBeInTheDocument();
    for (const name of ['devops environments', 'app environments']) {
      const tabs = screen.getByRole('tablist', { name });
      expect(within(tabs).getByRole('tab', { name: 'staging' })).toBeInTheDocument();
      expect(within(tabs).getByRole('tab', { name: 'production' })).toBeInTheDocument();
    }
  });
});

describe('ProjectCredentials — secrets', () => {
  it('never prefills a secret and says whether one is set', async () => {
    renderTab({
      credentialsLocalShow: vi.fn(() =>
        Promise.resolve(
          ok(
            credentialsView({
              data: {
                work_feedback_active: true,
                work_feedback_interval_minutes: 5,
                app: {
                  agents: [],
                  staging: { appUrl: '', username: '', password: { secret: true, set: true } },
                  production: { appUrl: '', username: '', password: { secret: true, set: false } },
                },
              },
            }),
          ),
        ),
      ),
    });
    await screen.findByText('Work feedback');
    expect(within(secretBox(APP_PASSWORD)).getByText('Set')).toBeInTheDocument();
    expect(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /Replace/ })).toBeInTheDocument();
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
  });

  it('shows Not set with a Set action for an empty secret', async () => {
    renderTab();
    await screen.findByText('Work feedback');
    expect(within(secretBox(APP_PASSWORD)).getByText('Not set')).toBeInTheDocument();
    expect(within(secretBox(APP_PASSWORD)).queryByRole('button', { name: /Remove/ })).not.toBeInTheDocument();
  });

  it('opens an empty write-only input on Replace, and sends the patch with the loaded hash', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('Work feedback');

    await user.click(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /^Set/ }));
    const input = document.getElementById(APP_PASSWORD) as HTMLInputElement;
    expect(input).toHaveValue('');
    expect(input).toHaveAttribute('type', 'password');
    await user.type(input, 'hunter2');

    expect(screen.getByRole('region', { name: 'Unsaved credential changes' })).toHaveTextContent('1 change not saved yet');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(bridge.credentialsLocalPatch).toHaveBeenCalledWith('proj-1', 'hash-1', [
      { op: 'set', pointer: '/app/staging/password', value: 'hunter2' },
    ]);
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Unsaved credential changes' })).not.toBeInTheDocument());
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
  });

  it('sends an empty string to remove a stored secret', async () => {
    const set = credentialsView();
    setAppPassword(set);
    const { bridge, user } = renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(set))) });
    await screen.findByText('Work feedback');
    await user.click(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /Remove/ }));
    expect(screen.getByText('Will be removed when you save')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(bridge.credentialsLocalPatch).toHaveBeenCalledWith('proj-1', 'hash-1', [{ op: 'set', pointer: '/app/staging/password', value: '' }]);
  });

  it('never renders a secret value from the view into the DOM', async () => {
    const view = credentialsView();
    // A misbehaving CLI that leaked a value into the view must still not reach the page as text.
    setAppPassword(view);
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(view))) });
    await screen.findByText('Work feedback');
    const inputs = Array.from(document.querySelectorAll('input')).map((input) => input.value);
    expect(inputs.every((value) => value !== 'true' && !value.includes('secret'))).toBe(true);
    expect(document.body.textContent).not.toMatch(/"secret"|\[object Object\]/);
  });
});

describe('ProjectCredentials — editing and saving', () => {
  it('lists unknown paths read-only', async () => {
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(credentialsView({ unknown_paths: ['/legacy/token', '/extra'] })))) });
    const list = await screen.findByRole('list', { name: 'Keys only the file can change' });
    expect(within(list).getAllByRole('listitem').map((item) => item.textContent)).toEqual(['/legacy/token', '/extra']);
    expect(within(list).queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('sends only the leaf that changed, and a numeric interval', async () => {
    const { bridge, user } = renderTab();
    const interval = await screen.findByLabelText('Check-in interval (minutes)');
    await user.clear(interval);
    await user.type(interval, '15');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(bridge.credentialsLocalPatch).toHaveBeenCalledWith('proj-1', 'hash-1', [
      { op: 'set', pointer: '/work_feedback_interval_minutes', value: 15 },
    ]);
  });

  it('blocks Save and explains an invalid interval', async () => {
    const { bridge, user } = renderTab();
    const interval = await screen.findByLabelText('Check-in interval (minutes)');
    await user.clear(interval);
    expect(await screen.findByText('Enter a whole number of at least 1.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    expect(bridge.credentialsLocalPatch).not.toHaveBeenCalled();
  });

  it('Discard resets every edit and hides the save bar', async () => {
    const { user, onDirtyChange } = renderTab();
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).not.toBeChecked();
    expect(onDirtyChange).toHaveBeenLastCalledWith(1);

    await user.click(screen.getByRole('button', { name: 'Discard' }));
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).toBeChecked();
    expect(screen.queryByRole('region', { name: 'Unsaved credential changes' })).not.toBeInTheDocument();
    expect(onDirtyChange).toHaveBeenLastCalledWith(0);
  });

  it('shows a clear conflict message when the file changed on disk, and Reload re-fetches', async () => {
    const { bridge, user } = renderTab({
      credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('hash mismatch', { kind: 'conflict', exitCode: 4, reason: CREDENTIALS_HASH_CONFLICT }))),
    });
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(await screen.findByText('The file changed on disk')).toBeInTheDocument();
    expect(screen.getByText(/Reload to see the latest version/)).toBeInTheDocument();
    expect(screen.queryByText('hash mismatch')).not.toBeInTheDocument();

    const before = vi.mocked(bridge.credentialsLocalShow).mock.calls.length;
    const alert = screen.getByText('The file changed on disk').closest('[role="alert"]') as HTMLElement;
    await user.click(within(alert).getByRole('button', { name: 'Reload' }));
    // Unsaved edits exist, so Reload goes through the discard confirmation.
    await user.click(await screen.findByRole('button', { name: 'Discard and reload' }));
    await waitFor(() => expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(before + 1));
    await waitFor(() => expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument());
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).toBeChecked();
  });

  it('shows any other save failure as an inline problem and keeps the edit', async () => {
    const { user } = renderTab({ credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('disk is full'))) });
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText(/disk is full/)).toBeInTheDocument();
    expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).not.toBeChecked();
  });

  it('withholds Save when the app has not declared the patch command usable', async () => {
    const bridge = fakeBridge();
    installBridge(bridge);
    render(<ProjectCredentials project={project()} environment={null} onDirtyChange={vi.fn()} onRunningChange={vi.fn()} />);
    await userEvent.setup().click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });
});

describe('ProjectCredentials — reload, races and failures', () => {
  it('asks before a header Reload discards unsaved edits', async () => {
    const { bridge, user } = renderTab();
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    const before = vi.mocked(bridge.credentialsLocalShow).mock.calls.length;

    await user.click(screen.getByRole('button', { name: 'Reload' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Discard unsaved changes and reload?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Keep editing' }));
    expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(before);
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).not.toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Reload' }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Discard and reload' }));
    await waitFor(() => expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(before + 1));
    await waitFor(() => expect(screen.getByRole('switch', { name: 'Work feedback active' })).toBeChecked());
  });

  it('reloads straight away when nothing is unsaved', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('Work feedback');
    await user.click(screen.getByRole('button', { name: 'Reload' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(2));
  });

  it('disables the form while a reload is in flight', async () => {
    const second = deferred<ReturnType<typeof ok>>();
    const show = vi.fn().mockResolvedValueOnce(ok(credentialsView())).mockReturnValueOnce(second.promise);
    const { user } = renderTab({ credentialsLocalShow: show as never });
    await screen.findByText('Work feedback');
    await user.click(screen.getByRole('button', { name: 'Reload' }));
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).toBeDisabled();
    second.resolve(ok(credentialsView()));
    await waitFor(() => expect(screen.getByRole('switch', { name: 'Work feedback active' })).toBeEnabled());
  });

  it('disables Save after a hash conflict until the file is reloaded', async () => {
    const { user } = renderTab({
      credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('moved', { kind: 'conflict', exitCode: 4, reason: CREDENTIALS_HASH_CONFLICT }))),
    });
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await screen.findByText('The file changed on disk');
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();

    const alert = screen.getByText('The file changed on disk').closest('[role="alert"]') as HTMLElement;
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).toBeDisabled();
    await user.click(within(alert).getByRole('button', { name: 'Reload' }));
    await user.click(await screen.findByRole('button', { name: 'Discard and reload' }));
    await waitFor(() => expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument());
    await user.click(screen.getByRole('switch', { name: 'Work feedback active' }));
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  });

  it('calls a conflict without hash details a busy file, not a changed one', async () => {
    const { user } = renderTab({
      credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('locked', { kind: 'conflict', exitCode: 4 }))),
    });
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('The credentials file is busy')).toBeInTheDocument();
    expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  });

  it('reloads when a save went through but its answer was unreadable', async () => {
    const show = vi.fn().mockResolvedValueOnce(ok(credentialsView())).mockResolvedValue(ok(credentialsView({ hash: 'hash-2' })));
    const { bridge, user } = renderTab({
      credentialsLocalShow: show,
      credentialsLocalPatch: vi.fn(() =>
        Promise.resolve(fail('unreadable', { kind: 'contract-breach', exitCode: 0, reason: CREDENTIALS_SAVED_UNREADABLE })),
      ),
    });
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Unsaved credential changes' })).not.toBeInTheDocument());
    expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument();
  });

  it('does not let a slow load overwrite the view a create produced', async () => {
    const missing = credentialsView({ exists: false, valid: false, hash: null, data: null });
    const slow = deferred<ReturnType<typeof ok>>();
    const show = vi.fn().mockResolvedValueOnce(ok(missing)).mockReturnValueOnce(slow.promise);
    const bridge = fakeBridge({
      credentialsLocalShow: show as never,
      credentialsLocalInit: vi.fn(() => Promise.resolve(ok(credentialsView({ hash: 'hash-created' })))),
    });
    installBridge(bridge);
    const props = { project: project(), environment: environment(), onDirtyChange: vi.fn(), onRunningChange: vi.fn() };
    const view = render(<ProjectCredentials {...props} active={false} />);
    const user = userEvent.setup();
    await screen.findByText('There is no credentials file yet.');
    // The tab is shown again: a re-read starts and is still pending when the file is created.
    view.rerender(<ProjectCredentials {...props} active />);
    await waitFor(() => expect(show).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole('button', { name: 'Create file' }));
    await screen.findByText('Work feedback');
    slow.resolve(ok(missing));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.getByText('Work feedback')).toBeInTheDocument();
    expect(screen.queryByText('There is no credentials file yet.')).not.toBeInTheDocument();
  });
});

describe('ProjectCredentials — form details', () => {
  it('shows only the names of docker keys, never their values', async () => {
    const view = credentialsView();
    const production = (view.data?.['devops'] as { production: { docker: unknown } }).production;
    production.docker = { host: 'tcp://x', registryPassword: 'hunter2-leak' };
    const { user } = renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(view))) });
    await screen.findByText('Work feedback');
    const tabs = screen.getByRole('tablist', { name: 'devops environments' });
    await user.click(within(tabs).getByRole('tab', { name: 'production' }));
    const list = await screen.findByRole('list', { name: 'Docker keys in production' });
    expect(within(list).getAllByRole('listitem').map((item) => item.textContent)).toEqual(['host', 'registryPassword']);
    expect(document.body.textContent).not.toContain('hunter2-leak');
    expect(document.body.textContent).not.toContain('tcp://x');
  });

  it('does not render a top-level object that is not a category as a card', async () => {
    const view = credentialsView();
    (view.data as Record<string, unknown>)['jira'] = { baseUrl: 'https://x.test', token: { secret: true, set: true } };
    (view.data as Record<string, unknown>)['qa'] = { agents: [], staging: { appUrl: '' } };
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(view))) });
    await screen.findByText('Work feedback');
    expect(screen.getByRole('tablist', { name: 'qa environments' })).toBeInTheDocument();
    expect(screen.queryByRole('tablist', { name: 'jira environments' })).not.toBeInTheDocument();
  });

  it('keeps ids unique for custom keys that differ only by punctuation', async () => {
    const view = credentialsView();
    (view.data as Record<string, unknown>)['qa'] = { agents: [], 'a-b': { appUrl: '' }, 'a/b': { appUrl: '' } };
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(view))) });
    await screen.findByText('Work feedback');
    const ids = Array.from(document.querySelectorAll('[id]')).map((el) => el.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('puts the legend first in a database group and keeps Remove outside it', async () => {
    const { user } = renderTab();
    await screen.findByText('Work feedback');
    const group = screen.getByRole('group', { name: /Database 1/ });
    expect(group.firstElementChild?.tagName).toBe('LEGEND');
    expect(within(group.querySelector('legend') as HTMLElement).queryByRole('button')).not.toBeInTheDocument();
    await user.click(within(group).getByRole('button', { name: /Remove/ }));
    expect(screen.queryByRole('group', { name: /Database 1/ })).not.toBeInTheDocument();
  });

  it('refuses to add a database when the file keeps a non-list there', async () => {
    const view = credentialsView();
    ((view.data?.['devops'] as { staging: Record<string, unknown> }).staging)['database'] = 'managed elsewhere';
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(view))) });
    await screen.findByText('Work feedback');
    expect(screen.getByRole('button', { name: /Add database/ })).toBeDisabled();
    expect(screen.getByText(/not a list of databases/)).toBeInTheDocument();
  });

  it('marks password inputs new-password and moves focus with Replace, Cancel', async () => {
    const { user } = renderTab();
    await screen.findByText('Work feedback');
    await user.click(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /^Set/ }));
    const input = document.getElementById(APP_PASSWORD) as HTMLInputElement;
    expect(input).toHaveAttribute('autocomplete', 'new-password');
    expect(input).toHaveFocus();
    await user.click(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /^Cancel/ }));
    expect(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /^Set/ })).toHaveFocus();
  });

  it('focuses Undo after Remove and the action button after Undo', async () => {
    const set = credentialsView();
    setAppPassword(set);
    const { user } = renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(set))) });
    await screen.findByText('Work feedback');
    await user.click(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /Remove/ }));
    expect(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /^Undo/ })).toHaveFocus();
    await user.click(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /^Undo/ }));
    expect(within(secretBox(APP_PASSWORD)).getByRole('button', { name: /Replace/ })).toHaveFocus();
  });
});

describe('Credentials tab inside the project screen', () => {
  function renderSettings() {
    const bridge = fakeBridge();
    installBridge(bridge);
    const onBack = vi.fn();
    render(<ProjectSettings project={project()} name="project-1" environment={environment()} active onBack={onBack} onChanged={vi.fn()} onUnbound={vi.fn()} />);
    return { bridge, onBack, user: userEvent.setup() };
  }

  it('reads the file only once the tab is opened', async () => {
    const { bridge, user } = renderSettings();
    await screen.findByRole('tab', { name: 'Preferences', selected: true });
    expect(bridge.credentialsLocalShow).not.toHaveBeenCalled();
    await user.click(screen.getByRole('tab', { name: /Credentials/ }));
    expect(await screen.findByText('Work feedback')).toBeInTheDocument();
    expect(bridge.credentialsLocalShow).toHaveBeenCalledWith('proj-1');
  });

  it('counts unsaved edits on the tab and keeps them across a tab switch', async () => {
    const { user } = renderSettings();
    await user.click(await screen.findByRole('tab', { name: /Credentials/ }));
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    expect(screen.getByRole('tab', { name: /Credentials/ })).toHaveTextContent('1');

    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    await user.click(screen.getByRole('tab', { name: /Credentials/ }));
    expect(screen.getByRole('switch', { name: 'Work feedback active' })).not.toBeChecked();
    expect(screen.getByRole('tab', { name: /Credentials/ })).toHaveTextContent('1');
  });

  it('asks before leaving with unsaved credential edits', async () => {
    const { user, onBack } = renderSettings();
    await user.click(await screen.findByRole('tab', { name: /Credentials/ }));
    await user.click(await screen.findByRole('switch', { name: 'Work feedback active' }));
    await user.click(screen.getByRole('button', { name: 'Back to Projects' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Discard unsaved changes?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Keep editing' }));
    expect(onBack).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Back to Projects' }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Discard and leave' }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});
