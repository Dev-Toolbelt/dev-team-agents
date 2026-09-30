// @vitest-environment jsdom
/**
 * The Plugins tab. It is generic: every assertion here is about what a `PluginView` makes
 * the screen do, never about a particular plugin. What it must never do: write config
 * without an explicit Save, save a value that failed validation, run an action that is
 * disabled, or lose typed edits on a tab switch or on the way out.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { addListItem } from '../../src/renderer/plugins/ListEditor.js';
import { Projects } from '../../src/renderer/screens/Projects.js';
import { ProjectSettings } from '../../src/renderer/screens/ProjectSettings.js';
import type { PluginConfigChange } from '../../src/shared/api.js';
import { environment, fail, fakeBridge, installBridge, ok, pluginField, pluginList, pluginView, project, runResult } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function openPlugins(overrides: Parameters<typeof fakeBridge>[0] = {}, env = environment()) {
  const bridge = fakeBridge(overrides);
  installBridge(bridge);
  const onBack = vi.fn();
  render(<ProjectSettings project={project()} name="project-1" environment={env} active onBack={onBack} />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('tab', { name: /Plugins/ }));
  return { bridge, user, onBack };
}

const card = (title = 'Graphify') => screen.getByRole('region', { name: title });

describe('the project screen’s tabs', () => {
  it('shows Preferences first and loads plugins only when the tab is opened', async () => {
    const bridge = fakeBridge();
    installBridge(bridge);
    render(<ProjectSettings project={project()} name="project-1" environment={environment()} active onBack={vi.fn()} />);
    const user = userEvent.setup();

    expect(await screen.findByRole('tab', { name: 'Preferences', selected: true })).toBeInTheDocument();
    expect(bridge.projectPlugins).not.toHaveBeenCalled();

    await user.click(screen.getByRole('tab', { name: /Plugins/ }));
    expect(await screen.findByRole('heading', { name: 'Graphify' })).toBeInTheDocument();
    expect(bridge.projectPlugins).toHaveBeenCalledWith('proj-1');
  });

  it('shows only the active panel: the other is hidden by its inactive state', async () => {
    const { user } = await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    const panels = () => Array.from(document.querySelectorAll<HTMLElement>('[role="tabpanel"]'));
    const inactive = () => panels().filter((panel) => panel.getAttribute('data-state') === 'inactive');
    expect(panels()).toHaveLength(2);
    expect(inactive()).toHaveLength(1);
    expect(inactive()[0]).toHaveClass('data-[state=inactive]:hidden');
    expect(panels().find((panel) => panel.getAttribute('data-state') === 'active')).toContainElement(screen.getByRole('heading', { name: 'Graphify' }));
    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    expect(inactive()[0]).toContainElement(screen.getByRole('heading', { name: 'Graphify', hidden: true }));
  });

  it('keeps a preferences problem inside its tab, so plugins stay reachable', async () => {
    const { bridge } = await openPlugins({ projectPreferences: vi.fn(() => Promise.resolve(fail('prefs unavailable'))) });
    expect(await screen.findByRole('heading', { name: 'Graphify' })).toBeInTheDocument();
    expect(bridge.projectPreferences).toHaveBeenCalled();
  });

  it('lists plugins the CLI skipped for an invalid manifest', async () => {
    await openPlugins({
      projectPlugins: vi.fn(() =>
        Promise.resolve(ok(pluginList([pluginView()], [{ name_or_dir: 'broken-plugin', problem: 'manifest.json: missing name' }]))),
      ),
    });
    expect(await screen.findByText(/manifest is invalid and it was skipped/)).toBeInTheDocument();
    expect(screen.getByText('broken-plugin')).toBeInTheDocument();
    expect(screen.getByText(/missing name/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Graphify' })).toBeInTheDocument();
  });

  it('shows no skipped-plugin notice when nothing was skipped', async () => {
    await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(screen.queryByText(/was skipped/)).not.toBeInTheDocument();
  });

  it('names the version and says how to update when it ships no plugins', async () => {
    await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([])))) });
    expect(await screen.findByText(/ships no plugins/)).toHaveTextContent('dev-team-agents 2.48.0, which ships no plugins');
    expect(screen.getByText('devteam update')).toBeInTheDocument();
    expect(screen.queryByText('devteam pin --release')).not.toBeInTheDocument();
  });

  it('points a pinned project at releasing its pin instead of updating', async () => {
    installBridge(fakeBridge({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([])))) }));
    render(<ProjectSettings project={project({ pin: '2.47.0', resolves_to: '2.47.0' })} name="p" environment={environment()} active onBack={vi.fn()} />);
    await userEvent.setup().click(await screen.findByRole('tab', { name: /Plugins/ }));
    expect(await screen.findByText(/It is pinned to 2\.47\.0/)).toBeInTheDocument();
    expect(screen.getByText('devteam pin --release')).toBeInTheDocument();
    expect(screen.queryByText('devteam update')).not.toBeInTheDocument();
  });

  it('says the version could not be resolved rather than naming none', async () => {
    installBridge(fakeBridge({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([])))) }));
    render(<ProjectSettings project={project({ resolves_to: null })} name="p" environment={environment()} active onBack={vi.fn()} />);
    await userEvent.setup().click(await screen.findByRole('tab', { name: /Plugins/ }));
    expect(await screen.findByText(/could not be resolved/)).toBeInTheDocument();
  });

  it('reports a failed list as a problem with a retry', async () => {
    await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(fail('plugin list exploded'))) });
    expect(await screen.findByText('plugin list exploded')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});

describe('a plugin card', () => {
  it.each([
    ['Missing requirements', { ready: false, requirements: [{ binary: 'graphify', found: false, install_hint: '/devteam:install graphify' }] }],
    ['Disabled', { enabled: false }],
    ['Needs setup', { enabled: true, configured: false }],
    ['Enabled', { enabled: true, configured: true }],
  ])('leads with the %s standing', async (label, overrides) => {
    await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([pluginView(overrides)])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByText(label, { selector: '[data-slot="badge"]' })).toBeInTheDocument();
  });

  it('lists a missing binary with its install hint as code, and will not enable past it', async () => {
    await openPlugins({
      projectPlugins: vi.fn(() =>
        Promise.resolve(ok(pluginList([pluginView({ ready: false, requirements: [{ binary: 'jq', found: false, install_hint: '/devteam:install jq' }] })]))),
      ),
    });
    await screen.findByRole('heading', { name: 'Graphify' });
    const alert = within(card()).getByRole('alert');
    expect(within(alert).getByText('jq')).toBeInTheDocument();
    expect(within(alert).getByText('/devteam:install jq').tagName).toBe('CODE');
    expect(within(card()).getByRole('switch', { name: /Enable/ })).toBeDisabled();
  });

  it('says the switch is committed to the repository and names the settings file', async () => {
    await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByText(/committed to the repository and applies to everyone on the project/)).toBeInTheDocument();
    expect(within(card()).getByText('.dev-team-agents/plugin-settings/graphify.json')).toBeInTheDocument();
  });

  it('notes a legacy config', async () => {
    await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([pluginView({ source: 'legacy', enabled: true })])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByText('legacy config')).toBeInTheDocument();
    expect(within(card()).getByText(/still reads a legacy config file/)).toBeInTheDocument();
  });

  it('shows the status summary and facts as a definition list', async () => {
    await openPlugins({
      projectPlugins: vi.fn(() =>
        Promise.resolve(ok(pluginList([pluginView({ enabled: true, status: { summary: 'Graph is current', facts: [{ label: 'Nodes', value: '128' }] } })]))),
      ),
    });
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByText('Graph is current')).toBeInTheDocument();
    expect(within(card()).getByText('Nodes').tagName).toBe('DT');
    expect(within(card()).getByText('128').tagName).toBe('DD');
  });

  it('enables through the bridge and says what happened', async () => {
    const { bridge, user } = await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('switch', { name: /Enable/ }));
    expect(bridge.setPluginEnabled).toHaveBeenCalledWith('proj-1', 'graphify', true);
    expect(await within(card()).findByRole('status')).toHaveTextContent(/is on for this project/);
    await waitFor(() => expect(bridge.projectPlugins).toHaveBeenCalledTimes(2));
  });

  it('withholds the switch, Save and actions when the store is ahead of the app', async () => {
    const withheld = environment({
      withheld: ['plugin enable', 'plugin disable', 'plugin config set', 'plugin config unset', 'plugin run'].map((command) => ({
        command,
        reason: 'the store is ahead of this app',
      })),
    });
    await openPlugins({}, withheld);
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByRole('switch', { name: /Enable/ })).toBeDisabled();
    expect(within(card()).getByRole('button', { name: 'Detect paths' })).toBeDisabled();
    expect(within(card()).getAllByText(/Withheld: the store is ahead of this app/)).toHaveLength(2);
    expect(within(card()).getByText(/Changing this plugin is unavailable right now: the store is ahead of this app/)).toBeInTheDocument();
  });
});

describe('the config form', () => {
  const rich = pluginView({
    enabled: true,
    config_fields: [
      pluginField(),
      pluginField({ key: 'depth', type: 'integer', label: 'Depth', min: 1, max: 9, required: false, default: 3, placeholder: null }),
      pluginField({ key: 'mode', type: 'enum', label: 'Mode', required: false, default: 'a', options: [{ value: 'a', label: 'Alpha' }, { value: 'b', label: 'Beta' }], placeholder: null }),
      pluginField({ key: 'label', type: 'string', label: 'Label', required: false, default: '', placeholder: 'name' }),
      pluginField({ key: 'auto_refresh', type: 'boolean', label: 'Refresh at session end', required: false, default: false, placeholder: null, help: null }),
    ],
    config: { targetPaths: ['src'], depth: 3, mode: 'a', label: '', auto_refresh: false },
    configured: true,
  });

  it('renders a control per type from the field alone', async () => {
    await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([rich])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    expect(scope.getByRole('list', { name: 'Source paths' })).toBeInTheDocument();
    expect(scope.getByRole('textbox', { name: /Depth/ })).toHaveValue('3');
    expect(scope.getByRole('combobox', { name: /Mode/ })).toHaveValue('a');
    expect(scope.getByRole('textbox', { name: /Label/ })).toHaveValue('');
    expect(scope.getByRole('switch', { name: /Refresh at session end/ })).not.toBeChecked();
  });

  it('stages edits, saves them in one batch, and does nothing until then', async () => {
    const { bridge, user } = await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([rich])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());

    await user.type(scope.getByRole('textbox', { name: 'Source paths' }), 'lib{Enter}');
    await user.clear(scope.getByRole('textbox', { name: /Depth/ }));
    await user.type(scope.getByRole('textbox', { name: /Depth/ }), '7');
    await user.selectOptions(scope.getByRole('combobox', { name: /Mode/ }), 'b');
    await user.click(scope.getByRole('switch', { name: /Refresh at session end/ }));
    expect(bridge.updatePluginConfig).not.toHaveBeenCalled();
    expect(scope.getByText('4 unsaved changes', { selector: 'p:not(.sr-only)' })).toBeInTheDocument();

    await user.click(scope.getByRole('button', { name: /Save changes/ }));
    const sent = (bridge.updatePluginConfig as ReturnType<typeof vi.fn>).mock.calls[0] as [string, string, PluginConfigChange[]];
    expect(sent[0]).toBe('proj-1');
    expect(sent[1]).toBe('graphify');
    expect(sent[2]).toEqual([
      { key: 'targetPaths', action: 'set', value: ['src', 'lib'] },
      { key: 'depth', action: 'set', value: 7 },
      { key: 'mode', action: 'set', value: 'b' },
      { key: 'auto_refresh', action: 'set', value: true },
    ]);
    expect(await scope.findByText(/Saved 4 changes/)).toBeInTheDocument();
  });

  it('keeps the saved values on screen when the reload after a save fails', async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(ok(pluginList([rich])))
      .mockResolvedValueOnce(fail('reload exploded'));
    const { user } = await openPlugins({ projectPlugins: list });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    await user.click(scope.getByRole('switch', { name: /Refresh at session end/ }));
    await user.click(scope.getByRole('button', { name: /Save changes/ }));
    expect(await screen.findByText('reload exploded')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(scope.getByRole('switch', { name: /Refresh at session end/ })).toBeChecked();
    expect(await scope.findByText(/could not be read back/)).toBeInTheDocument();
  });

  it('blocks Save while a value is invalid, and says which', async () => {
    const { bridge, user } = await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([rich])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    const depth = scope.getByRole('textbox', { name: /Depth/ });
    await user.clear(depth);
    await user.type(depth, '99');
    expect(scope.getByText('Must be at most 9.')).toBeInTheDocument();
    expect(depth).toHaveAttribute('aria-invalid', 'true');
    expect(scope.getByRole('button', { name: /Save changes/ })).toBeDisabled();
    expect(bridge.updatePluginConfig).not.toHaveBeenCalled();
  });

  it('discards staged edits', async () => {
    const { user } = await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([rich])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    await user.click(scope.getByRole('switch', { name: /Refresh at session end/ }));
    expect(scope.getByRole('switch', { name: /Refresh at session end/ })).toBeChecked();
    await user.click(scope.getByRole('button', { name: 'Discard' }));
    expect(scope.getByRole('switch', { name: /Refresh at session end/ })).not.toBeChecked();
  });

  it('states a partial save and keeps what did not land', async () => {
    const updatePluginConfig = vi.fn((_id: string, _name: string, changes: readonly PluginConfigChange[]) =>
      Promise.resolve(ok({ applied: changes.slice(0, 1), failed: { change: changes[1] as PluginConfigChange, problem: fail('depth is reserved') } })),
    );
    const { user } = await openPlugins({ projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([rich])))), updatePluginConfig });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    await user.click(scope.getByRole('switch', { name: /Refresh at session end/ }));
    await user.selectOptions(scope.getByRole('combobox', { name: /Mode/ }), 'b');
    await user.click(scope.getByRole('button', { name: /Save changes/ }));
    expect(await scope.findByText(/1 change was saved before one failed/)).toBeInTheDocument();
    expect(scope.getByText('depth is reserved')).toBeInTheDocument();
  });
});

describe('the string list editor', () => {
  it('adds on Enter and on the button, trims, and removes by name', async () => {
    const { user } = await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    const input = scope.getByRole('textbox', { name: 'Source paths' });

    await user.type(input, '  src  {Enter}');
    await user.type(input, 'lib');
    await user.click(scope.getByRole('button', { name: /^Add/ }));
    const list = scope.getByRole('list', { name: 'Source paths' });
    expect(within(list).getAllByRole('listitem').map((item) => item.textContent)).toEqual(['src', 'lib']);

    await user.click(scope.getByRole('button', { name: 'Remove src from Source paths' }));
    expect(within(scope.getByRole('list', { name: 'Source paths' })).getAllByRole('listitem')).toHaveLength(1);
  });

  it('rejects a duplicate and an empty entry with a message', async () => {
    const { user } = await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    const input = scope.getByRole('textbox', { name: 'Source paths' });

    await user.type(input, 'src{Enter}');
    await user.type(input, 'src{Enter}');
    expect(await scope.findByRole('alert')).toHaveTextContent('"src" is already in the list.');
    expect(within(scope.getByRole('list', { name: 'Source paths' })).getAllByRole('listitem')).toHaveLength(1);

    await user.clear(input);
    await user.type(input, '   {Enter}');
    expect(scope.getByRole('alert')).toHaveTextContent('Enter a value first.');
  });

  it('applies the same rules as a plain function', () => {
    expect(addListItem(['a'], ' b ')).toEqual({ ok: true, list: ['a', 'b'] });
    expect(addListItem(['a'], 'a')).toEqual({ ok: false, error: '"a" is already in the list.' });
    expect(addListItem([], '')).toMatchObject({ ok: false });
    expect(addListItem([], 'x\u0007')).toMatchObject({ ok: false });
  });
});

describe('actions', () => {
  it('disables an enabled-only action while the plugin is off, and says why', async () => {
    await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByRole('button', { name: 'Rebuild graph' })).toBeDisabled();
    expect(within(card()).getByText('Enable this plugin to run this action.')).toBeInTheDocument();
    expect(within(card()).getByRole('button', { name: 'Detect paths' })).toBeEnabled();
  });

  it('disables every action while a requirement is missing', async () => {
    await openPlugins({
      projectPlugins: vi.fn(() =>
        Promise.resolve(ok(pluginList([pluginView({ ready: false, enabled: true, requirements: [{ binary: 'x', found: false, install_hint: null }] })]))),
      ),
    });
    await screen.findByRole('heading', { name: 'Graphify' });
    expect(within(card()).getByRole('button', { name: 'Detect paths' })).toBeDisabled();
    expect(within(card()).getByRole('button', { name: 'Rebuild graph' })).toBeDisabled();
  });

  it('fills the draft from a config action without saving, then saves on request', async () => {
    const runPluginAction = vi.fn(() => Promise.resolve(ok(runResult({ output: { targetPaths: ['src', 'app'], auto_refresh: true, rogue: 1 } }))));
    const { bridge, user } = await openPlugins({ runPluginAction });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());

    await user.click(scope.getByRole('button', { name: 'Detect paths' }));
    expect(runPluginAction).toHaveBeenCalledWith('proj-1', 'graphify', 'detect');
    expect(await scope.findByText(/Proposed values filled in — review and save/)).toBeInTheDocument();
    expect(scope.getByText(/Ignored 1 value/)).toBeInTheDocument();
    expect(within(scope.getByRole('list', { name: 'Source paths' })).getAllByRole('listitem').map((item) => item.textContent)).toEqual(['src', 'app']);
    expect(scope.getByRole('switch', { name: /Refresh at session end/ })).toBeChecked();
    expect(bridge.updatePluginConfig).not.toHaveBeenCalled();

    await user.click(scope.getByRole('button', { name: /Save changes/ }));
    const changes = (bridge.updatePluginConfig as ReturnType<typeof vi.fn>).mock.calls[0]?.[2] as PluginConfigChange[];
    expect(changes).toEqual([
      { key: 'targetPaths', action: 'set', value: ['src', 'app'] },
      { key: 'auto_refresh', action: 'set', value: true },
    ]);
  });

  it('says so when a proposal changes nothing, and when the script fails', async () => {
    const runPluginAction = vi
      .fn()
      .mockResolvedValueOnce(ok(runResult({ output: { auto_refresh: false } })))
      .mockResolvedValueOnce(ok(runResult({ ok: false, exit_code: 3, log_tail: 'no manifest found' })));
    const { user } = await openPlugins({ runPluginAction });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    await user.click(scope.getByRole('button', { name: 'Detect paths' }));
    expect(await scope.findByText(/matches the current settings/)).toBeInTheDocument();
    await user.click(scope.getByRole('button', { name: 'Detect paths' }));
    expect(await scope.findByText('Failed (exit 3)')).toBeInTheDocument();
    expect(scope.getByText('no manifest found')).toBeInTheDocument();
  });

  it('says a detect that found nothing found nothing, not that it matches', async () => {
    const runPluginAction = vi.fn(() => Promise.resolve(ok(runResult({ output: { targetPaths: [] } }))));
    const { user } = await openPlugins({ runPluginAction });
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('button', { name: 'Detect paths' }));
    expect(await within(card()).findByText(/found nothing to propose/)).toBeInTheDocument();
    expect(within(card()).queryByText(/matches the current settings/)).not.toBeInTheDocument();
  });

  it('warns before leaving while an action is still running', async () => {
    let finish: (value: unknown) => void = () => {};
    const runPluginAction = vi.fn(() => new Promise((resolve) => (finish = resolve)));
    const { user, onBack } = await openPlugins({ runPluginAction: runPluginAction as never });
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('button', { name: 'Detect paths' }));
    await user.click(screen.getByRole('button', { name: 'Projects' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/still running/)).toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Leave' }));
    expect(onBack).toHaveBeenCalled();
    finish(ok(runResult()));
  });

  // Leaving by any route must pass the same guard. Switching the app's top-level tab keeps
  // this screen mounted (`forceMount` in App.tsx), so a running action and its result
  // survive it; closing the window hides it (background mode). The one other route is a
  // notification asking for a different project, which `Projects` defers until Back.
  it('does not let a notification for another project bypass the running-action warning', async () => {
    let finish: (value: unknown) => void = () => {};
    const runPluginAction = vi.fn(() => new Promise((resolve) => (finish = resolve)));
    installBridge(
      fakeBridge({
        runPluginAction: runPluginAction as never,
        listProjects: vi.fn(() =>
          Promise.resolve(ok({ current: '2.48.0', projects: [project(), project({ project_id: 'proj-2', path: '/work/project-2' })] })),
        ),
      }),
    );
    const user = userEvent.setup();
    const env = environment();
    const view = render(<Projects environment={env} openRequest={null} />);
    await user.click(await screen.findByRole('button', { name: 'project-1 — open settings' }));
    await user.click(await screen.findByRole('tab', { name: /Plugins/ }));
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('button', { name: 'Detect paths' }));

    view.rerender(<Projects environment={env} openRequest={{ projectId: 'proj-2', nonce: 1 }} />);
    expect(await screen.findByText(/A notification asked to open/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /project-1 · Settings/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Projects' }));
    expect(within(await screen.findByRole('dialog')).getByText(/still running/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /project-1 · Settings/, hidden: true })).toBeInTheDocument();
    finish(ok(runResult()));
  });

  it('shows a log action’s outcome with its duration and a collapsible tail, then re-reads the card', async () => {
    const runPluginAction = vi.fn(() => Promise.resolve(ok(runResult({ action: 'rebuild', duration_ms: 2500, log_tail: 'built 12 nodes' }))));
    const { bridge, user } = await openPlugins({
      runPluginAction,
      projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([pluginView({ enabled: true, configured: true })])))),
    });
    await screen.findByRole('heading', { name: 'Graphify' });
    const scope = within(card());
    await user.click(scope.getByRole('button', { name: 'Rebuild graph' }));
    expect(await scope.findByText('Succeeded')).toBeInTheDocument();
    expect(scope.getByText('2.5 s')).toBeInTheDocument();
    expect(scope.getByText('built 12 nodes').tagName).toBe('PRE');
    expect(scope.getByText('Output').tagName).toBe('SUMMARY');
    await waitFor(() => expect(bridge.projectPlugins).toHaveBeenCalledTimes(2));
  });

  it('shows a json action’s answer as text', async () => {
    const view = pluginView({
      enabled: true,
      actions: [{ id: 'probe', label: 'Probe', help: null, output: 'json', requires_enabled: false, writes: false, timeout_seconds: null }],
    });
    const runPluginAction = vi.fn(() => Promise.resolve(ok(runResult({ action: 'probe', output: { nodes: 3 } }))));
    const { user } = await openPlugins({ runPluginAction, projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList([view])))) });
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('button', { name: 'Probe' }));
    expect(await within(card()).findByText(/"nodes": 3/)).toBeInTheDocument();
  });

  it('reports a refusal from the main process as a problem', async () => {
    const runPluginAction = vi.fn(() => Promise.resolve(fail('graphify declares no action detect', { kind: 'refused' })));
    const { user } = await openPlugins({ runPluginAction });
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('button', { name: 'Detect paths' }));
    expect(await within(card()).findByText('graphify declares no action detect')).toBeInTheDocument();
  });
});

describe('leaving with unsaved plugin edits', () => {
  it('asks first, counts the plugin edits, and keeps them across a tab switch', async () => {
    const { user, onBack } = await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(within(card()).getByRole('switch', { name: /Refresh at session end/ }));

    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    await user.click(screen.getByRole('tab', { name: /Plugins/ }));
    expect(within(card()).getByRole('switch', { name: /Refresh at session end/ })).toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Projects' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/1 change to project-1 will be lost/)).toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Discard and leave' }));
    expect(onBack).toHaveBeenCalled();
  });

  it('leaves at once when nothing is staged', async () => {
    const { user, onBack } = await openPlugins();
    await screen.findByRole('heading', { name: 'Graphify' });
    await user.click(screen.getByRole('button', { name: 'Projects' }));
    expect(onBack).toHaveBeenCalled();
  });
});
