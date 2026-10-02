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

describe('ProjectCredentials — load states', () => {
  it('shows a loading line while the file is read', async () => {
    const pending = deferred<ReturnType<typeof ok>>();
    renderTab({ credentialsLocalShow: vi.fn(() => pending.promise as never) });
    expect(screen.getByText(/Running cred local show/)).toBeInTheDocument();
    pending.resolve(ok(credentialsView()));
    expect(await screen.findByText('work_feedback_active')).toBeInTheDocument();
  });

  it('offers to create a missing file, showing its path', async () => {
    const missing = credentialsView({ exists: false, valid: false, hash: null, data: null });
    const { bridge, user } = renderTab({
      credentialsLocalShow: vi.fn(() => Promise.resolve(ok(missing))),
      credentialsLocalInit: vi.fn(() => Promise.resolve(ok(credentialsView()))),
    });

    expect(await screen.findByText('There is no credentials file yet.')).toBeInTheDocument();
    expect(screen.getAllByText(missing.path).length).toBeGreaterThan(0);
    expect(screen.queryByText('work_feedback_active')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Create file' }));
    expect(bridge.credentialsLocalInit).toHaveBeenCalledWith('proj-1');
    expect(await screen.findByText('work_feedback_active')).toBeInTheDocument();
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
    expect(await screen.findByText('work_feedback_active')).toBeInTheDocument();
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
    expect(screen.queryByText('work_feedback_active')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save/ })).not.toBeInTheDocument();
  });

  it('shows the CLI problem when the file cannot be read', async () => {
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(fail('cred local show exploded'))) });
    expect(await screen.findByText(/cred local show exploded/)).toBeInTheDocument();
  });
});

describe('ProjectCredentials — editing and saving', () => {
  it('Discard resets every edit and hides the save bar', async () => {
    const { user, onDirtyChange } = renderTab();
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).not.toBeChecked();
    expect(onDirtyChange).toHaveBeenLastCalledWith(1);

    await user.click(screen.getByRole('button', { name: 'Discard' }));
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).toBeChecked();
    expect(screen.queryByRole('region', { name: 'Unsaved credential changes' })).not.toBeInTheDocument();
    expect(onDirtyChange).toHaveBeenLastCalledWith(0);
  });

  it('shows a clear conflict message when the file changed on disk, and Reload re-fetches', async () => {
    const { bridge, user } = renderTab({
      credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('hash mismatch', { kind: 'conflict', exitCode: 4, reason: CREDENTIALS_HASH_CONFLICT }))),
    });
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
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
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).toBeChecked();
  });

  it('shows any other save failure as an inline problem and keeps the edit', async () => {
    const { user } = renderTab({ credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('disk is full'))) });
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText(/disk is full/)).toBeInTheDocument();
    expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).not.toBeChecked();
  });

  it('withholds Save when the app has not declared the patch command usable', async () => {
    const bridge = fakeBridge();
    installBridge(bridge);
    render(<ProjectCredentials project={project()} environment={null} onDirtyChange={vi.fn()} onRunningChange={vi.fn()} />);
    await userEvent.setup().click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });
});

describe('ProjectCredentials — reload, races and failures', () => {
  it('asks before a header Reload discards unsaved edits', async () => {
    const { bridge, user } = renderTab();
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    const before = vi.mocked(bridge.credentialsLocalShow).mock.calls.length;

    await user.click(screen.getByRole('button', { name: 'Reload' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Discard unsaved changes and reload?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Keep editing' }));
    expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(before);
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).not.toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Reload' }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Discard and reload' }));
    await waitFor(() => expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(before + 1));
    await waitFor(() => expect(screen.getByRole('switch', { name: 'work_feedback_active' })).toBeChecked());
  });

  it('reloads straight away when nothing is unsaved', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('work_feedback_active');
    await user.click(screen.getByRole('button', { name: 'Reload' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => expect(bridge.credentialsLocalShow).toHaveBeenCalledTimes(2));
  });

  it('disables the form while a reload is in flight', async () => {
    const second = deferred<ReturnType<typeof ok>>();
    const show = vi.fn().mockResolvedValueOnce(ok(credentialsView())).mockReturnValueOnce(second.promise);
    const { user } = renderTab({ credentialsLocalShow: show as never });
    await screen.findByText('work_feedback_active');
    await user.click(screen.getByRole('button', { name: 'Reload' }));
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).toBeDisabled();
    second.resolve(ok(credentialsView()));
    await waitFor(() => expect(screen.getByRole('switch', { name: 'work_feedback_active' })).toBeEnabled());
  });

  it('disables Save after a hash conflict until the file is reloaded', async () => {
    const { user } = renderTab({
      credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('moved', { kind: 'conflict', exitCode: 4, reason: CREDENTIALS_HASH_CONFLICT }))),
    });
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await screen.findByText('The file changed on disk');
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();

    const alert = screen.getByText('The file changed on disk').closest('[role="alert"]') as HTMLElement;
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).toBeDisabled();
    await user.click(within(alert).getByRole('button', { name: 'Reload' }));
    await user.click(await screen.findByRole('button', { name: 'Discard and reload' }));
    await waitFor(() => expect(screen.queryByText('The file changed on disk')).not.toBeInTheDocument());
    await user.click(screen.getByRole('switch', { name: 'work_feedback_active' }));
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  });

  it('calls a conflict without hash details a busy file, not a changed one', async () => {
    const { user } = renderTab({
      credentialsLocalPatch: vi.fn(() => Promise.resolve(fail('locked', { kind: 'conflict', exitCode: 4 }))),
    });
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
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
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
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
    await screen.findByText('work_feedback_active');
    slow.resolve(ok(missing));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.getByText('work_feedback_active')).toBeInTheDocument();
    expect(screen.queryByText('There is no credentials file yet.')).not.toBeInTheDocument();
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
    expect(await screen.findByText('work_feedback_active')).toBeInTheDocument();
    expect(bridge.credentialsLocalShow).toHaveBeenCalledWith('proj-1');
  });

  it('counts unsaved edits on the tab and keeps them across a tab switch', async () => {
    const { user } = renderSettings();
    await user.click(await screen.findByRole('tab', { name: /Credentials/ }));
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    expect(screen.getByRole('tab', { name: /Credentials/ })).toHaveTextContent('1');

    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    await user.click(screen.getByRole('tab', { name: /Credentials/ }));
    expect(screen.getByRole('switch', { name: 'work_feedback_active' })).not.toBeChecked();
    expect(screen.getByRole('tab', { name: /Credentials/ })).toHaveTextContent('1');
  });

  it('asks before leaving with unsaved credential edits', async () => {
    const { user, onBack } = renderSettings();
    await user.click(await screen.findByRole('tab', { name: /Credentials/ }));
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
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

/** The ops the last save sent. */
function sentOps(bridge: ReturnType<typeof fakeBridge>): unknown[] {
  const calls = vi.mocked(bridge.credentialsLocalPatch).mock.calls;
  return calls[calls.length - 1]?.[2] as unknown[];
}

async function save(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
}

describe('ProjectCredentials — free-form editor', () => {
  it('draws whatever groups and fields the file has, with production own and inherited', async () => {
    const { user } = renderTab();
    expect(await screen.findByText('example')).toBeInTheDocument();
    expect(screen.getByText('staging')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'example › production is production' })).toBeChecked();
    expect(screen.getByRole('switch', { name: 'example › staging is production' })).not.toBeChecked();
    expect(screen.getAllByText('Production', { selector: '[data-slot="badge"]' })).toHaveLength(1);
    expect(screen.getByText('Production (inherited)')).toBeInTheDocument();
    // Groups deeper than two levels start collapsed.
    expect(screen.queryByDisplayValue('db.prod.test')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Expand example › production › db' }));
    expect(screen.getByDisplayValue('db.prod.test')).toBeInTheDocument();
    // The reserved keys are controls, never fields.
    expect(screen.queryByText('$secrets')).not.toBeInTheDocument();
    expect(screen.queryByText('$production')).not.toBeInTheDocument();
  });

  it('never renders a secret value and says whether one is set', async () => {
    const view = credentialsView();
    renderTab({ credentialsLocalShow: vi.fn(() => Promise.resolve(ok(view))) });
    await screen.findByText('example');
    expect(screen.getAllByText('Set', { selector: 'span' })).toHaveLength(2);
    expect(screen.getByText('Not set')).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain('"secret"');
    expect(screen.getByRole('button', { name: /Mark secret.*token/ })).toBeInTheDocument();
  });

  it('sends a replaced secret as one set op with the loaded hash', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Replace example › production › password' }));
    const input = document.querySelector('input[type="password"]') as HTMLInputElement;
    expect(input).toHaveValue('');
    expect(input).toHaveAttribute('autocomplete', 'new-password');
    await user.type(input, 's3cret');
    await save(user);
    expect(bridge.credentialsLocalPatch).toHaveBeenCalledWith('proj-1', 'hash-1', [
      { op: 'set', pointer: '/example/production/password', value: 's3cret' },
    ]);
  });

  it('renames a secret with a move, keeping $secrets in step', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Rename example › staging › password' }));
    const dialog = await screen.findByRole('dialog');
    const name = within(dialog).getByLabelText('New name');
    await user.clear(name);
    await user.type(name, 'pass');
    await user.click(within(dialog).getByRole('button', { name: 'Rename' }));
    await save(user);
    expect(sentOps(bridge)).toEqual([
      { op: 'move', from: '/example/staging/password', pointer: '/example/staging/pass' },
      { op: 'set', pointer: '/example/staging/$secrets', value: ['pass'] },
    ]);
  });

  it('refuses a rename onto a name that already exists, or a reserved one', async () => {
    const { user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Rename example › staging › password' }));
    const dialog = await screen.findByRole('dialog');
    const name = within(dialog).getByLabelText('New name');
    await user.clear(name);
    await user.type(name, 'url');
    expect(within(dialog).getByRole('alert')).toHaveTextContent('"url" already exists here');
    expect(within(dialog).getByRole('button', { name: 'Rename' })).toBeDisabled();
    await user.clear(name);
    await user.type(name, '$x');
    expect(within(dialog).getByRole('alert')).toHaveTextContent('reserved');
  });

  it('adds a field, a secret field and a nested group anywhere', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Add group to the file' }));
    await user.type(screen.getByLabelText('Group name'), 'jira');
    await user.click(screen.getByRole('button', { name: 'Add' }));
    await user.click(await screen.findByRole('button', { name: 'Add field to jira' }));
    await user.type(screen.getByLabelText('Field name'), 'apiToken');
    await user.type(screen.getByLabelText('Value'), 'tok-1');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Add' }));
    await save(user);
    expect(sentOps(bridge)).toEqual([
      { op: 'set', pointer: '/jira', value: {} },
      { op: 'set', pointer: '/jira/apiToken', value: 'tok-1' },
      { op: 'set', pointer: '/jira/$secrets', value: ['apiToken'] },
    ]);
  });

  it('removes a marked field and drops it from $secrets', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Remove example › staging › password' }));
    expect(screen.queryByRole('button', { name: 'Remove example › staging › password' })).not.toBeInTheDocument();
    await save(user);
    expect(sentOps(bridge)).toEqual([
      { op: 'unset', pointer: '/example/staging/password' },
      { op: 'unset', pointer: '/example/staging/$secrets' },
    ]);
  });

  it('marks a group as production and a field as secret', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('switch', { name: 'example › staging is production' }));
    await user.click(screen.getByRole('button', { name: /Not secret.*example › staging › username/ }));
    await save(user);
    expect(sentOps(bridge)).toEqual([
      { op: 'set', pointer: '/example/staging/$production', value: true },
      { op: 'set', pointer: '/example/staging/$secrets', value: ['password', 'username'] },
    ]);
  });

  it('asks before unmarking a secret, since its value shows after saving', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: /unmark example › production › password/ }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Keep it secret' }));
    expect(screen.queryByRole('region', { name: 'Unsaved credential changes' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /unmark example › production › password/ }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Show the value' }));
    await save(user);
    expect(sentOps(bridge)).toEqual([{ op: 'unset', pointer: '/example/production/$secrets' }]);
  });

  it('searches keys and visible values, never secret values', async () => {
    const { user } = renderTab();
    await screen.findByText('example');
    const search = screen.getByRole('searchbox', { name: 'Search credentials' });
    await user.type(search, 'prod.test');
    expect(screen.getByDisplayValue('db.prod.test')).toBeInTheDocument();
    expect(screen.getByDisplayValue('https://prod.test')).toBeInTheDocument();
    expect(screen.queryByText('staging')).not.toBeInTheDocument();
    expect(screen.queryByText('work_feedback_active')).not.toBeInTheDocument();

    await user.clear(search);
    await user.type(search, 'usern');
    expect(screen.getByText('username')).toBeInTheDocument();
    expect(screen.queryByText('production')).not.toBeInTheDocument();

    await user.clear(search);
    await user.type(search, 'zzz-nothing');
    expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
  });

  it('keeps a number a number, and blocks Save on text that is not one', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    const interval = screen.getByLabelText('work_feedback_interval_minutes');
    await user.clear(interval);
    await user.type(interval, '10x');
    expect(screen.getByText('Must be a number')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();

    await user.type(interval, '{Backspace}');
    expect(screen.queryByText('Must be a number')).not.toBeInTheDocument();
    await save(user);
    expect(sentOps(bridge)).toEqual([{ op: 'set', pointer: '/work_feedback_interval_minutes', value: 10 }]);
  });

  it('moves a secret into another group, carrying its mark', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Move example › staging › password' }));
    const dialog = await screen.findByRole('dialog');
    const into = within(dialog).getByLabelText('Move into');
    expect(within(into).queryByRole('option', { name: 'example › staging' })).not.toBeInTheDocument();
    expect(within(into).queryByRole('option', { name: 'example › production' })).not.toBeInTheDocument();
    await user.selectOptions(into, 'example › production › db');
    await user.click(within(dialog).getByRole('button', { name: 'Move' }));
    expect(screen.queryByRole('button', { name: 'Move example › staging › password' })).not.toBeInTheDocument();
    await save(user);
    expect(sentOps(bridge)).toEqual([
      { op: 'move', from: '/example/staging/password', pointer: '/example/production/db/password' },
      { op: 'unset', pointer: '/example/staging/$secrets' },
      { op: 'set', pointer: '/example/production/db/$secrets', value: ['password'] },
    ]);
  });

  it('moves a whole group to the top of the file', async () => {
    const { bridge, user } = renderTab();
    await screen.findByText('example');
    await user.click(screen.getByRole('button', { name: 'Move example › staging' }));
    const dialog = await screen.findByRole('dialog');
    await user.selectOptions(within(dialog).getByLabelText('Move into'), 'The top of the file');
    await user.click(within(dialog).getByRole('button', { name: 'Move' }));
    await save(user);
    expect(sentOps(bridge)).toEqual([{ op: 'move', from: '/example/staging', pointer: '/staging' }]);
  });

  it('gives every icon button a tooltip and paints Remove red', async () => {
    const { user } = renderTab();
    await screen.findByText('example');
    await user.hover(screen.getByRole('button', { name: 'Rename example › staging › url' }));
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Rename');
    await user.unhover(screen.getByRole('button', { name: 'Rename example › staging › url' }));

    await user.hover(screen.getByRole('button', { name: 'Move example › staging › url' }));
    await waitFor(() => expect(screen.getByRole('tooltip')).toHaveTextContent('Move to another group'));
    await user.unhover(screen.getByRole('button', { name: 'Move example › staging › url' }));

    const remove = screen.getByRole('button', { name: 'Remove example › staging › url' });
    expect(remove).toHaveClass('text-destructive');
    expect(screen.getByRole('button', { name: 'Rename example › staging › url' })).not.toHaveClass('text-destructive');
    await user.hover(remove);
    await waitFor(() => expect(screen.getByRole('tooltip')).toHaveTextContent('Remove'));
  });

  it('pins the save bar to the window edge and leaves room for it at the end of the form', async () => {
    const { user } = renderTab();
    await user.click(await screen.findByRole('switch', { name: 'work_feedback_active' }));
    expect(screen.getByRole('region', { name: 'Unsaved credential changes' })).toHaveClass('fixed', 'bottom-0');
    expect(screen.getByTestId('save-bar-spacer')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Discard' }));
    expect(screen.queryByTestId('save-bar-spacer')).not.toBeInTheDocument();
  });

  it('keeps ids unique for keys that differ only by punctuation', async () => {
    renderTab({
      credentialsLocalShow: vi.fn(() => Promise.resolve(ok(credentialsView({ data: { 'a-b': 'one', 'a/b': 'two', 'a.b': 'three' } })))),
    });
    await screen.findByText('a-b');
    const ids = [...document.querySelectorAll('[id]')].map((node) => node.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
