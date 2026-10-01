// @vitest-environment jsdom
/**
 * The Integrations screens. Generic like the Plugins tests: every assertion is about what an
 * `IntegrationView` makes the screen do. What must never happen: a token shown or kept after a
 * submit, a write without an explicit Save, a destructive action without a confirm, or a write
 * button live while the environment withholds its command.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { IntegrationField, IntegrationView } from '../../src/shared/api.js';
import { Integrations } from '../../src/renderer/screens/Integrations.js';
import { ProjectIntegrations } from '../../src/renderer/screens/ProjectIntegrations.js';
import { ProjectSettings } from '../../src/renderer/screens/ProjectSettings.js';
import { environment, fail, fakeBridge, installBridge, ok, project } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const FIELDS: IntegrationField[] = [
  { key: 'api_url', scope: 'account', type: 'string', label: 'API URL', help: null, required: true, default: 'https://api.github.com', placeholder: null, options: [], resource: null, visible_when: null, binds_token: true },
  { key: 'deployment', scope: 'account', type: 'enum', label: 'Deployment', help: null, required: false, default: 'cloud', placeholder: null, options: [{ value: 'cloud', label: 'Cloud' }, { value: 'data_center', label: 'Data Center' }], resource: null, visible_when: null, binds_token: false },
  { key: 'email', scope: 'account', type: 'string', label: 'Email', help: null, required: true, default: null, placeholder: null, options: [], resource: null, visible_when: { key: 'deployment', equals: 'cloud' }, binds_token: false },
  { key: 'repository', scope: 'project', type: 'string', label: 'Repository', help: null, required: false, default: null, placeholder: 'owner/name', options: [], resource: 'repos', visible_when: null, binds_token: false },
];

function view(overrides: Partial<IntegrationView> = {}): IntegrationView {
  return {
    name: 'github',
    title: 'GitHub',
    description: 'Issues and pull requests.',
    homepage: null,
    auth: { kind: 'token', label: 'Personal access token', help: null, has_token: true, stale: false, backend: 'keychain' },
    fields: FIELDS,
    account: { api_url: 'https://api.github.com', email: 'me@example.com' },
    project: { repository: 'acme/app' },
    project_problem: null,
    detected: {},
    connected: true,
    project_configured: true,
    status: { state: 'connected', checked_at: '2026-09-30T12:00:00Z', summary: 'Signed in as octocat', facts: [{ label: 'Account', value: 'octocat', tone: 'positive' }] },
    ...overrides,
  };
}

const listOf = (views: IntegrationView[], projectId: string | null = null) => ok({ project_id: projectId, integrations: views });
const testOf = (overrides: Partial<{ ok: boolean; summary: string }> = {}) => ({ ok: true, state: 'connected', summary: 'Signed in as octocat', facts: [], checked_at: '2026-09-30T12:05:00Z', ...overrides });

const card = () => screen.getByRole('region', { name: 'GitHub' });
async function expand() {
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Show GitHub details' }));
}

async function openAccount(overrides: Parameters<typeof fakeBridge>[0] = {}, env = environment()) {
  const bridge = fakeBridge({ integrationList: vi.fn(() => Promise.resolve(listOf([view()]))), ...overrides });
  installBridge(bridge);
  render(<Integrations environment={env} />);
  await screen.findByRole('heading', { name: 'GitHub' });
  await expand();
  return { bridge, user: userEvent.setup() };
}

async function openProject(overrides: Parameters<typeof fakeBridge>[0] = {}, v: IntegrationView = view(), env = environment(), onConnect = vi.fn()) {
  const bridge = fakeBridge({ integrationList: vi.fn(() => Promise.resolve(listOf([v], 'proj-1'))), ...overrides });
  installBridge(bridge);
  render(<ProjectIntegrations project={project()} environment={env} onDirtyChange={vi.fn()} onRunningChange={vi.fn()} onConnectAccount={onConnect} />);
  await screen.findByRole('heading', { name: 'GitHub' });
  await expand();
  return { bridge, user: userEvent.setup(), onConnect };
}

const withheldEnv = (...commands: string[]) => environment({ withheld: commands.map((command) => ({ command, reason: 'CLI too old' })) });

describe('the standing badge', () => {
  it.each<[string, Partial<IntegrationView>, string]>([
    ['not connected', { connected: false, auth: { kind: 'token', label: 'T', help: null, has_token: false, stale: false, backend: null }, status: { state: 'not_connected', checked_at: null, summary: '', facts: [] } }, 'Not connected'],
    ['connected', {}, 'Connected'],
    ['invalid token', { status: { state: 'invalid_token', checked_at: null, summary: 'Bad token', facts: [] } }, 'Invalid token'],
    ['rate limited', { status: { state: 'rate_limited', checked_at: null, summary: 'Slow down', facts: [] } }, 'Rate limited'],
    ['unreachable', { status: { state: 'unreachable', checked_at: null, summary: 'No route', facts: [] } }, 'Unreachable'],
    ['unknown but connected', { status: { state: 'unknown', checked_at: null, summary: '', facts: [] } }, 'Not tested'],
  ])('leads with the right badge for %s', async (_name, overrides, label) => {
    installBridge(fakeBridge({ integrationList: vi.fn(() => Promise.resolve(listOf([view(overrides)]))) }));
    render(<Integrations environment={environment()} />);
    await screen.findByRole('heading', { name: 'GitHub' });
    expect(within(card()).getByText(label, { selector: '[data-slot="badge"]' })).toBeInTheDocument();
  });
});

describe('account mode', () => {
  it('never pre-fills the token: a stored one is a fact with Replace and Remove', async () => {
    await openAccount();
    expect(screen.getByText('Stored in keychain')).toBeInTheDocument();
    expect(screen.queryByLabelText('Personal access token')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Replace/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Remove/ })).toBeInTheDocument();
  });

  it('offers an empty password input when nothing is stored', async () => {
    await openAccount({ integrationList: vi.fn(() => Promise.resolve(listOf([view({ connected: false, auth: { kind: 'token', label: 'Personal access token', help: null, has_token: false, stale: false, backend: null } })]))) });
    const input = screen.getByLabelText('Personal access token');
    expect(input).toHaveAttribute('type', 'password');
    expect(input).toHaveValue('');
  });

  it('connects with the typed token and clears it from the input right after', async () => {
    let release: (value: unknown) => void = () => undefined;
    const connect = vi.fn(() => new Promise((resolve) => { release = resolve; }));
    const { user } = await openAccount({
      integrationList: vi.fn(() => Promise.resolve(listOf([view({ connected: false, auth: { kind: 'token', label: 'Personal access token', help: null, has_token: false, stale: false, backend: null } })]))),
      integrationConnect: connect as never,
    });
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_secret');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(connect).toHaveBeenCalledWith('github', {}, 'ghp_secret', null);
    // Cleared while the call is still in flight, not after it lands.
    expect(document.body.innerHTML).not.toContain('ghp_secret');
    release(ok({ integration: view(), test: testOf(), warning: null }));
    expect(await screen.findByText('Signed in as octocat', { selector: '[role="status"]' })).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain('ghp_secret');
  });

  it('clears the token even when the connect fails', async () => {
    const connect = vi.fn(() => Promise.resolve(fail('bad thing')));
    const { user } = await openAccount({ integrationConnect: connect });
    await user.click(screen.getByRole('button', { name: /Replace/ }));
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_again');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('bad thing')).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain('ghp_again');
  });

  it('sends a null token and no fields when only the token store is untouched', async () => {
    const connect = vi.fn(() => Promise.resolve(ok({ integration: view({ connected: false, auth: { kind: 'token', label: 'T', help: null, has_token: false, stale: false, backend: null } }), test: testOf(), warning: null })));
    const { user } = await openAccount({ integrationConnect: connect, integrationList: vi.fn(() => Promise.resolve(listOf([view({ connected: false, auth: { kind: 'token', label: 'Personal access token', help: null, has_token: false, stale: false, backend: null } })]))) });
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_x');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(connect).toHaveBeenCalledWith('github', {}, 'ghp_x', null);
  });

  it('requires re-entering the token before the address can be changed', async () => {
    const connect = vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf(), warning: null })));
    const { user } = await openAccount({ integrationConnect: connect });
    const url = screen.getByLabelText(/API URL/);
    await user.clear(url);
    await user.type(url, 'https://ghe.example/api/v3');
    expect(screen.getAllByText('Changing the address requires re-entering the token').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /Replace/ }));
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_new');
    expect(screen.queryByText('Changing the address requires re-entering the token')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(connect).toHaveBeenCalledWith('github', { api_url: 'https://ghe.example/api/v3' }, 'ghp_new', null);
  });

  it('saves a field that does not bind the token without asking for it again', async () => {
    const connect = vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf(), warning: null })));
    const { user } = await openAccount({ integrationConnect: connect });
    const email = screen.getByLabelText(/Email/);
    await user.clear(email);
    await user.type(email, 'other@example.com');
    expect(screen.queryByText('Changing the address requires re-entering the token')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(connect).toHaveBeenCalledWith('github', { email: 'other@example.com' }, null, null);
  });

  it('shows the warning a connect returns when the token went to the unencrypted store', async () => {
    const fresh = view({ connected: false, auth: { kind: 'token', label: 'Personal access token', help: null, has_token: false, stale: false, backend: null } });
    const connect = vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf(), warning: 'the token is in a mode-600 file' })));
    const { user } = await openAccount({ integrationConnect: connect, integrationList: vi.fn(() => Promise.resolve(listOf([fresh]))) });
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_fresh');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('the token is in a mode-600 file');
  });

  it('shows a stale token as a standing badge, offers the token input and blocks Save until one is typed', async () => {
    const stale = view({ connected: false, auth: { kind: 'token', label: 'Personal access token', help: null, has_token: true, stale: true, backend: 'keychain' }, status: { state: 'not_connected', checked_at: null, summary: '', facts: [] } });
    const connect = vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf(), warning: null })));
    const { user } = await openAccount({ integrationConnect: connect, integrationList: vi.fn(() => Promise.resolve(listOf([stale]))) });
    expect(within(card()).getByText('Token needs reconnecting', { selector: '[data-slot="badge"]' })).toBeInTheDocument();
    expect(screen.getByLabelText('Personal access token')).toHaveAttribute('type', 'password');
    expect(screen.queryByRole('button', { name: /Keep the stored token/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save changes' })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_fresh');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(connect).toHaveBeenCalledWith('github', {}, 'ghp_fresh', null);
  });

  it('says "Settings saved." when the connect succeeded but the test failed', async () => {
    const connect = vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf({ ok: false, summary: 'Token rejected' }), warning: null })));
    const { user } = await openAccount({ integrationConnect: connect });
    await user.click(screen.getByRole('button', { name: /Replace/ }));
    await user.type(screen.getByLabelText('Personal access token'), 'ghp_bad');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect((await screen.findAllByText('Settings saved.')).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Connected settings saved/)).not.toBeInTheDocument();
    expect(screen.getByText('Token rejected')).toBeInTheDocument();
  });

  it('formats the last check in the reader\'s locale and keeps the ISO value in the element', async () => {
    await openAccount();
    const time = card().querySelector('time');
    expect(time).not.toBeNull();
    expect(time?.getAttribute('datetime')).toBe('2026-09-30T12:00:00Z');
    expect(time?.getAttribute('title')).toBe('2026-09-30T12:00:00Z');
    expect(time?.textContent).not.toContain('2026-09-30T12:00:00Z');
    expect(time?.textContent).toMatch(/2026/);
  });

  it('honours visible_when and blocks a blank required field', async () => {
    const { user } = await openAccount();
    expect(screen.getByLabelText(/Email/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Deployment'), 'data_center');
    expect(screen.queryByLabelText(/Email/)).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Deployment'), 'cloud');
    await user.clear(screen.getByLabelText(/Email/));
    expect(screen.getByText('This is required.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });

  it('tests the connection and shows the result', async () => {
    const test = vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf({ summary: 'Token works' }), warning: null })));
    const { user } = await openAccount({ integrationTest: test });
    await user.click(screen.getByRole('button', { name: 'Test connection' }));
    expect(test).toHaveBeenCalledWith('github', null);
    expect(await screen.findByText('Token works')).toBeInTheDocument();
  });

  it('asks before disconnecting, and Keep connected writes nothing', async () => {
    const disconnect = vi.fn(() => Promise.resolve(ok({ integration: view({ connected: false, auth: { kind: 'token', label: 'T', help: null, has_token: false, stale: false, backend: null }, status: { state: 'not_connected', checked_at: null, summary: '', facts: [] } }), changed: true })));
    const { user } = await openAccount({ integrationDisconnect: disconnect });
    await user.click(screen.getByRole('button', { name: 'Disconnect' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Keep connected' }));
    expect(disconnect).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Disconnect' }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Disconnect' }));
    expect(disconnect).toHaveBeenCalledWith('github', false);
    await waitFor(() => expect(within(card()).getByText('Not connected', { selector: '[data-slot="badge"]' })).toBeInTheDocument());
  });

  it('disables every write button the environment withholds', async () => {
    await openAccount({}, withheldEnv('integration connect', 'integration disconnect', 'integration test'));
    expect(screen.getByRole('button', { name: 'Test connection' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Disconnect' })).toBeDisabled();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/API URL/), 'x');
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });

  it('reports a failed list with a retry', async () => {
    installBridge(fakeBridge({ integrationList: vi.fn(() => Promise.resolve(fail('list exploded'))) }));
    render(<Integrations environment={environment()} />);
    expect(await screen.findByText('list exploded')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});

describe('project mode', () => {
  it('asks for the project list, shows only project fields and leaves the account read-only', async () => {
    const { bridge } = await openProject();
    expect(bridge.integrationList).toHaveBeenCalledWith('proj-1');
    expect(screen.getByLabelText('Repository')).toHaveValue('acme/app');
    expect(screen.queryByLabelText(/API URL/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Personal access token')).not.toBeInTheDocument();
    expect(screen.getByText('Signed in as octocat')).toBeInTheDocument();
  });

  it('saves a project field through config set, and unsets it when emptied', async () => {
    const set = vi.fn(() => Promise.resolve(ok({ integration: view({ project: { repository: 'acme/other' } }), key: 'repository' })));
    const unset = vi.fn(() => Promise.resolve(ok({ integration: view({ project: {} }), key: 'repository', removed: true })));
    const { user } = await openProject({ integrationConfigSet: set, integrationConfigUnset: unset });
    const field = screen.getByLabelText('Repository');
    await user.clear(field);
    await user.type(field, 'acme/other');
    expect(set).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(set).toHaveBeenCalledWith('github', 'repository', 'acme/other', 'proj-1');
    await waitFor(() => expect(screen.getByLabelText('Repository')).toHaveValue('acme/other'));

    await user.clear(screen.getByLabelText('Repository'));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(unset).toHaveBeenCalledWith('github', 'repository', 'proj-1');
  });

  it('says why the committed binding reads as empty when it cannot be parsed', async () => {
    await openProject({ integrationList: vi.fn(() => Promise.resolve(listOf([view({ project: {}, project_problem: 'bad JSON' })], 'proj-1'))) });
    expect(screen.getByText(/could not be read, so it is treated as empty: bad JSON/)).toBeInTheDocument();
  });

  it('keeps Load options disabled while the account token needs reconnecting', async () => {
    const stale = view({ connected: false, auth: { kind: 'token', label: 'Personal access token', help: null, has_token: true, stale: true, backend: 'keychain' } });
    await openProject({ integrationList: vi.fn(() => Promise.resolve(listOf([stale], 'proj-1'))) });
    expect(screen.getByRole('button', { name: 'Load options' })).toBeDisabled();
  });

  it('loads options for a resource field and fills the draft from the pick', async () => {
    const resources = vi.fn(() => Promise.resolve(ok({ items: [{ value: 'acme/api', label: 'acme/api' }, { value: 'acme/web', label: 'acme/web' }], truncated: true })));
    const { user } = await openProject({ integrationResources: resources });
    await user.click(screen.getByRole('button', { name: 'Load options' }));
    expect(resources).toHaveBeenCalledWith('github', 'repos', 'proj-1');
    expect(await screen.findByText(/Only the first options are listed/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Repository options'), 'acme/web');
    expect(screen.getByLabelText('Repository')).toHaveValue('acme/web');
    expect(within(card()).getAllByText('1 unsaved change').length).toBeGreaterThan(0);
  });

  it('shows a failed option load as a problem', async () => {
    const { user } = await openProject({ integrationResources: vi.fn(() => Promise.resolve(fail('no network'))) });
    await user.click(screen.getByRole('button', { name: 'Load options' }));
    expect(await screen.findByText('no network')).toBeInTheDocument();
  });

  it('offers a detected value as a one-click suggestion', async () => {
    const { user } = await openProject({}, view({ project: {}, detected: { repository: 'acme/detected' } }));
    await user.click(screen.getByRole('button', { name: 'Use detected: acme/detected' }));
    expect(screen.getByLabelText('Repository')).toHaveValue('acme/detected');
    expect(screen.queryByRole('button', { name: /Use detected/ })).not.toBeInTheDocument();
  });

  it('points at the Integrations tab when the account is not connected', async () => {
    const off = view({ connected: false, auth: { kind: 'token', label: 'T', help: null, has_token: false, stale: false, backend: null }, status: { state: 'not_connected', checked_at: null, summary: '', facts: [] } });
    const { user, onConnect } = await openProject({}, off);
    expect(screen.getByText(/is not connected/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open Integrations' }));
    expect(onConnect).toHaveBeenCalledTimes(1);
  });

  it('shows the connect hint for a stale token like a missing one', async () => {
    const stale = view({ connected: false, auth: { kind: 'token', label: 'T', help: null, has_token: true, stale: true, backend: 'keychain' }, status: { state: 'not_connected', checked_at: null, summary: '', facts: [] } });
    const { user, onConnect } = await openProject({}, stale);
    expect(screen.getByText(/is not connected/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open Integrations' }));
    expect(onConnect).toHaveBeenCalledTimes(1);
  });

  it('disables Save when config set and config unset are withheld', async () => {
    const { user } = await openProject({}, view(), withheldEnv('integration config set'));
    await user.type(screen.getByLabelText('Repository'), 'x');
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });
});

describe('the project screen', () => {
  it('loads integrations only when the tab is opened and warns about unsaved edits when leaving', async () => {
    const bridge = fakeBridge({ integrationList: vi.fn(() => Promise.resolve(listOf([view()], 'proj-1'))) });
    installBridge(bridge);
    const onBack = vi.fn();
    render(<ProjectSettings project={project()} name="project-1" environment={environment()} active onBack={onBack} onChanged={vi.fn()} onUnbound={vi.fn()} />);
    const user = userEvent.setup();
    await screen.findByRole('tab', { name: 'Preferences', selected: true });
    expect(bridge.integrationList).not.toHaveBeenCalled();

    await user.click(screen.getByRole('tab', { name: /Integrations/ }));
    await screen.findByRole('heading', { name: 'GitHub' });
    await expand();
    await user.type(screen.getByLabelText('Repository'), 'x');
    await user.click(screen.getByRole('button', { name: 'Projects' }));
    expect(within(await screen.findByRole('dialog')).getByText(/1 change to project-1 will be lost/)).toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
  });
});

describe('keeping the project list current', () => {
  const projectTab = (props: Partial<Parameters<typeof ProjectIntegrations>[0]> = {}) => (
    <ProjectIntegrations project={project()} environment={environment()} onDirtyChange={vi.fn()} onRunningChange={vi.fn()} {...props} />
  );

  it('reloads when the tab becomes active again and when the account nonce changes', async () => {
    const list = vi.fn(() => Promise.resolve(listOf([view()], 'proj-1')));
    installBridge(fakeBridge({ integrationList: list }));
    const { rerender } = render(projectTab({ active: true, refreshNonce: 0 }));
    await screen.findByRole('heading', { name: 'GitHub' });
    expect(list).toHaveBeenCalledTimes(1);

    rerender(projectTab({ active: false, refreshNonce: 0 }));
    expect(list).toHaveBeenCalledTimes(1);
    rerender(projectTab({ active: true, refreshNonce: 0 }));
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2));

    rerender(projectTab({ active: true, refreshNonce: 1 }));
    await waitFor(() => expect(list).toHaveBeenCalledTimes(3));

    // A bump while hidden waits for the return, and then costs one reload, not two.
    rerender(projectTab({ active: false, refreshNonce: 1 }));
    rerender(projectTab({ active: false, refreshNonce: 2 }));
    expect(list).toHaveBeenCalledTimes(3);
    rerender(projectTab({ active: true, refreshNonce: 2 }));
    await waitFor(() => expect(list).toHaveBeenCalledTimes(4));
  });

  it('shows the fresh account standing after a reload instead of the old one', async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(listOf([view()], 'proj-1'))
      .mockResolvedValue(listOf([view({ connected: false, auth: { kind: 'token', label: 'T', help: null, has_token: false, stale: false, backend: null }, status: { state: 'not_connected', checked_at: null, summary: '', facts: [] } })], 'proj-1'));
    installBridge(fakeBridge({ integrationList: list }));
    const { rerender } = render(projectTab({ active: true, refreshNonce: 0 }));
    await screen.findByRole('heading', { name: 'GitHub' });
    expect(within(card()).getByText('Connected', { selector: '[data-slot="badge"]' })).toBeInTheDocument();
    rerender(projectTab({ active: true, refreshNonce: 1 }));
    await waitFor(() => expect(within(card()).getByText('Not connected', { selector: '[data-slot="badge"]' })).toBeInTheDocument());
  });

  it('drops the previous project\'s list when the project changes', async () => {
    let release: (value: ReturnType<typeof listOf>) => void = () => undefined;
    const list = vi
      .fn()
      .mockResolvedValueOnce(listOf([view()], 'proj-1'))
      .mockReturnValueOnce(new Promise((resolve) => { release = resolve; }));
    installBridge(fakeBridge({ integrationList: list }));
    const { rerender } = render(projectTab());
    await screen.findByRole('heading', { name: 'GitHub' });
    rerender(projectTab({ project: project({ project_id: 'proj-2' }) }));
    expect(screen.queryByRole('heading', { name: 'GitHub' })).not.toBeInTheDocument();
    expect(list).toHaveBeenLastCalledWith('proj-2');
    release(listOf([view({ title: 'Second' })], 'proj-2'));
    expect(await screen.findByRole('heading', { name: 'Second' })).toBeInTheDocument();
  });

  it('tells the owner when an account write succeeds', async () => {
    const onAccountChanged = vi.fn();
    installBridge(fakeBridge({ integrationList: vi.fn(() => Promise.resolve(listOf([view()]))), integrationTest: vi.fn(() => Promise.resolve(ok({ integration: view(), test: testOf(), warning: null }))) }));
    render(<Integrations environment={environment()} onAccountChanged={onAccountChanged} />);
    await screen.findByRole('heading', { name: 'GitHub' });
    await expand();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Test connection' }));
    await waitFor(() => expect(onAccountChanged).toHaveBeenCalledTimes(1));
  });
});
