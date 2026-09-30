// @vitest-environment jsdom
/**
 * The project settings screen. What it must never do: write to a layer other than the
 * project's, send a value that failed validation, save while `prefs set` is withheld,
 * lose edits silently on the way out, or hide that a batch was only partly written.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Projects } from '../../src/renderer/screens/Projects.js';
import { ProjectSettings } from '../../src/renderer/screens/ProjectSettings.js';
import type { OperationResult, PreferenceChange, PreferenceUpdateReport } from '../../src/shared/api.js';
import { deferred, environment, fakeBridge, installBridge, ok, project, projectPreferences } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderSettings(overrides: Parameters<typeof fakeBridge>[0] = {}, env = environment(), active = true) {
  const bridge = fakeBridge(overrides);
  installBridge(bridge);
  const onBack = vi.fn();
  const view = render(
    <ProjectSettings project={project()} name="project-1" environment={env} active={active} onBack={onBack} onChanged={vi.fn()} onUnbound={vi.fn()} />,
  );
  const setActive = (next: boolean) =>
    view.rerender(<ProjectSettings project={project()} name="project-1" environment={env} active={next} onBack={onBack} onChanged={vi.fn()} onUnbound={vi.fn()} />);
  return { bridge, onBack, setActive };
}

/** The fixture's preferences with some values and origins replaced. */
function prefsWith(values: Record<string, unknown>, origin: Record<string, string> = {}, inherited: Record<string, unknown> = {}) {
  const base = projectPreferences();
  return vi.fn(() =>
    Promise.resolve(
      ok({
        ...base,
        values: { ...base.values, ...values },
        origin: { ...base.origin, ...origin },
        inherited: { ...base.inherited, ...inherited },
      }),
    ),
  );
}

describe('ProjectSettings — header', () => {
  it('no longer carries the inheritance notice', async () => {
    installBridge(fakeBridge());
    render(<ProjectSettings project={project()} name="project-1" environment={environment()} active onBack={vi.fn()} onChanged={vi.fn()} onUnbound={vi.fn()} />);
    await screen.findByRole('heading', { name: /project-1 · Settings/ });
    expect(screen.queryByText(/Changes are saved to this project only/)).not.toBeInTheDocument();
  });
});

describe('ProjectSettings — a notification asking for another project', () => {
  it('never replaces an open settings screen, says so, and opens the project on leaving', async () => {
    const projects = [project(), project({ project_id: 'proj-2', path: '/repo/project-2' })];
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects }))) }));
    const user = userEvent.setup();
    const env = environment();
    const view = render(<Projects environment={env} openRequest={null} />);

    await user.click(await screen.findByRole('button', { name: 'project-1 — open settings' }));
    await screen.findByRole('heading', { name: /project-1 · Settings/ });

    view.rerender(<Projects environment={env} openRequest={{ projectId: 'proj-2', nonce: 1 }} />);
    expect(await screen.findByText(/A notification asked to open project-2/)).toBeInTheDocument();
    // Still on project-1: its unsaved-changes guard was not bypassed.
    expect(screen.getByRole('heading', { name: /project-1 · Settings/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Projects' }));
    expect(await screen.findByRole('heading', { name: /project-2 · Settings/ })).toBeInTheDocument();
    expect(screen.queryByText(/A notification asked to open/)).not.toBeInTheDocument();
  });
});

describe('ProjectSettings — opening another project does not carry the previous one over', () => {
  it('shows nothing of project 1 while project 2 loads, then project 2’s own values, nothing unsaved', async () => {
    const projects = [project(), project({ project_id: 'proj-2', path: '/repo/project-2' })];
    const second = deferred<OperationResult<ReturnType<typeof projectPreferences>>>();
    const projectPreferencesFn = vi.fn((projectId: string) =>
      projectId === 'proj-2' ? second.promise : Promise.resolve(ok(projectPreferences())),
    );
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects }))),
        projectPreferences: projectPreferencesFn,
      }),
    );
    const user = userEvent.setup();
    const env = environment();
    const view = render(<Projects environment={env} openRequest={null} />);

    await user.click(await screen.findByRole('button', { name: 'project-1 — open settings' }));
    expect(await screen.findByLabelText('Conversation language')).toHaveValue('en');

    view.rerender(<Projects environment={env} openRequest={{ projectId: 'proj-2', nonce: 1 }} />);
    await user.click(await screen.findByRole('button', { name: 'Projects' }));
    await screen.findByRole('heading', { name: /project-2 · Settings/ });

    // Project 1's form is gone the moment project 2 is asked for.
    expect(screen.queryByLabelText('Conversation language')).not.toBeInTheDocument();

    second.resolve(ok(projectPreferences({ project_id: 'proj-2', values: { ...projectPreferences().values, language: 'es' } })));
    expect(await screen.findByLabelText('Conversation language')).toHaveValue('es');
    // Nothing is dirty, so there is nothing to save.
    expect(screen.queryByRole('region', { name: 'Unsaved changes' })).not.toBeInTheDocument();
  });
});

describe('ProjectSettings — the section being read is highlighted', () => {
  it('marks exactly one section current: the one the user jumps to', async () => {
    // jsdom has no layout, so which section scrolling selects is checked by hand in the
    // app; the click and the single-current rule are checked here.
    renderSettings();
    const nav = await screen.findByRole('navigation', { name: 'Settings sections' });
    await userEvent.setup().click(within(nav).getByRole('link', { name: /Context & session/ }));
    const current = within(nav)
      .getAllByRole('link')
      .filter((link) => link.getAttribute('aria-current') === 'location');
    expect(current.map((link) => link.textContent)).toEqual(['Context & session']);
  });
});

describe('ProjectSettings — the scroll spy only runs while Preferences is on show', () => {
  it('does not measure sections while the Plugins tab is open, and measures again on return', async () => {
    renderSettings();
    const user = userEvent.setup();
    await screen.findByRole('navigation', { name: 'Settings sections' });
    const measure = vi.spyOn(Element.prototype, 'getBoundingClientRect');

    await user.click(screen.getByRole('tab', { name: /Plugins/ }));
    measure.mockClear();
    document.dispatchEvent(new Event('scroll'));
    expect(measure).not.toHaveBeenCalled();

    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    expect(measure).toHaveBeenCalled();
  });

  it('does not measure while the whole screen is on a background tab', async () => {
    const { setActive } = renderSettings();
    await screen.findByRole('navigation', { name: 'Settings sections' });
    setActive(false);
    const measure = vi.spyOn(Element.prototype, 'getBoundingClientRect');
    document.dispatchEvent(new Event('scroll'));
    expect(measure).not.toHaveBeenCalled();
    setActive(true);
    expect(measure).toHaveBeenCalled();
  });
});

describe('ProjectSettings — navigation', () => {
  it('opens from the project name in the list, and returns with Projects', async () => {
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))) }));
    const user = userEvent.setup();
    render(<Projects environment={environment()} />);

    await user.click(await screen.findByRole('button', { name: 'project-1 — open settings' }));
    expect(await screen.findByRole('heading', { name: /project-1 · Settings/ })).toBeInTheDocument();
    expect(window.devteam.projectPreferences).toHaveBeenCalledWith('proj-1');

    await user.click(screen.getByRole('button', { name: 'Projects' }));
    expect(await screen.findByRole('heading', { name: 'Bound projects' })).toBeInTheDocument();
  });

  it('moves focus to the settings heading on open, and back to the project name on return', async () => {
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))) }));
    const user = userEvent.setup();
    render(<Projects environment={environment()} />);

    await user.click(await screen.findByRole('button', { name: 'project-1 — open settings' }));
    const heading = await screen.findByRole('heading', { name: /project-1 · Settings/ });
    expect(heading).toHaveFocus();

    await user.click(screen.getByRole('button', { name: 'Projects' }));
    expect(await screen.findByRole('button', { name: 'project-1 — open settings' })).toHaveFocus();
    // Returning refetches the list, so a change made elsewhere is not hidden behind a stale table.
    expect(window.devteam.listProjects).toHaveBeenCalledTimes(2);
  });

  it('refetches the project list when its tab becomes visible again', async () => {
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))) }));
    const view = render(<Projects environment={environment()} active />);
    await screen.findByText('project-1');
    view.rerender(<Projects environment={environment()} active={false} />);
    view.rerender(<Projects environment={environment()} active />);
    await vi.waitFor(() => expect(window.devteam.listProjects).toHaveBeenCalledTimes(2));
  });

  it('asks before leaving with unsaved changes', async () => {
    const { onBack } = renderSettings();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('switch', { name: 'Learn before every commit' }));
    await user.click(screen.getByRole('button', { name: 'Projects' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Discard unsaved changes?')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Keep editing' }));
    expect(onBack).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Projects' }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Discard and leave' }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});

describe('ProjectSettings — grouping and origin', () => {
  it('renders every group and says where each value comes from', async () => {
    renderSettings();
    for (const title of ['General', 'Context & session', 'Memory & docs', 'Worktrees', 'Notifications', 'QA & CI']) {
      expect(await screen.findByRole('heading', { name: title, level: 3 })).toBeInTheDocument();
    }
    expect(screen.getAllByText('Not opted in').length).toBe(2);
    expect(screen.getAllByLabelText(/^This project:/)).toHaveLength(2);
    // The deprecated key is shown but cannot be edited.
    expect(screen.getByText('Deprecated — no longer applied')).toBeInTheDocument();
  });

  it('masks the context window with digit grouping and draws both thresholds in tokens', async () => {
    renderSettings();
    expect(await screen.findByLabelText('Model context window')).toHaveValue('200,000');
    expect(screen.getByText(/110,000 tokens/)).toBeInTheDocument();
    expect(screen.getByText(/120,000 tokens/)).toBeInTheDocument();
  });

  it('shows keys the table does not know as read-only under Other', async () => {
    renderSettings({
      projectPreferences: vi.fn(() => {
        const base = projectPreferences();
        return Promise.resolve(
          ok({
            ...base,
            values: { ...base.values, future_key: 3 },
            origin: { ...base.origin, future_key: 'project' },
            unknown: ['future_key'],
          }),
        );
      }),
    });
    expect(await screen.findByRole('heading', { name: 'Other' })).toBeInTheDocument();
    expect(screen.getByText('future_key')).toBeInTheDocument();
    expect(screen.getByText('unknown key')).toBeInTheDocument();
  });
});

describe('ProjectSettings — validation', () => {
  it('shows an out-of-range number inline and keeps Save disabled', async () => {
    renderSettings();
    const user = userEvent.setup();
    const input = await screen.findByLabelText('Remind to commit after');
    await user.clear(input);
    await user.type(input, '0');

    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Between 1 and 200 turns.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save changes/ })).toBeDisabled();
    expect(within(screen.getByRole('region', { name: 'Unsaved changes' })).getByText('1 value needs fixing before you can save')).toBeInTheDocument();
  });

  it('refuses a warning at or above the critical level', async () => {
    renderSettings();
    const user = userEvent.setup();
    const warning = await screen.findByLabelText('Warn at');
    await user.clear(warning);
    await user.type(warning, '70');

    expect(screen.getByText('The warning has to come before the critical level.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save changes/ })).toBeDisabled();
  });

  it('shows a pasted non-integer as an error instead of rewriting it into another number', async () => {
    renderSettings();
    const user = userEvent.setup();
    const input = await screen.findByLabelText('Keep session summaries for');
    await user.clear(input);
    await user.click(input);
    await user.paste('1e6');
    expect(input).toHaveValue('1e6');
    expect(screen.getByText('Whole numbers only.')).toBeInTheDocument();
  });

  it('refuses a reserved word in a free-text field before it reaches the CLI', async () => {
    renderSettings();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('QA browser'), '__other__');
    await user.type(screen.getByLabelText('QA browser, custom value'), 'none');
    expect(screen.getByText('"none" is a reserved word here.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save changes/ })).toBeDisabled();
  });

  it('checks a reset against the inherited value it will bring back', async () => {
    // Warning is 55 in the project layer and 70 inherited; limit becomes 65. Resetting the
    // warning would store 70 ≥ 65, which the pair rule has to catch before the save.
    renderSettings({
      projectPreferences: prefsWith(
        { context_window_percent_warning: 55 },
        { context_window_percent_warning: 'project' },
        { context_window_percent_warning: 70 },
      ),
    });
    const user = userEvent.setup();
    const limit = await screen.findByLabelText('Critical at');
    await user.clear(limit);
    await user.type(limit, '65');
    expect(screen.queryByText('The critical level has to be above the warning.')).not.toBeInTheDocument();

    const warningRow = screen.getByLabelText('Warn at').closest('[class*="grid"]')!.parentElement!;
    await user.click(within(warningRow).getByRole('button', { name: /Reset to inherited/ }));
    expect(screen.getByText('reverts to 70 on save')).toBeInTheDocument();
    expect(screen.getByText('The critical level has to be above the warning.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save changes/ })).toBeDisabled();
  });

  it('does not let a pair that was already invalid in the store block an unrelated edit', async () => {
    const { bridge } = renderSettings({
      projectPreferences: prefsWith({ context_window_percent_warning: 80, context_window_percent_limit: 60 }),
    });
    const user = userEvent.setup();
    expect(await screen.findByText('The warning has to come before the critical level.')).toBeInTheDocument();

    await user.click(screen.getByRole('switch', { name: 'Mute notifications' }));
    await user.click(screen.getByRole('button', { name: /Save changes/ }));
    expect(bridge.updateProjectPreferences).toHaveBeenCalledWith('proj-1', [
      { key: 'suppress_notifications', action: 'set', value: true },
    ]);
  });
});

describe('ProjectSettings — saving', () => {
  it('sends only the changed keys, then reloads', async () => {
    const { bridge } = renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('switch', { name: 'Use a worktree per task' }));
    await user.selectOptions(screen.getByLabelText('Conversation language'), 'pt-BR');
    await user.click(screen.getByRole('button', { name: '1M' }));
    await user.click(screen.getByRole('radio', { name: /Finalize/ }));
    await user.selectOptions(screen.getByLabelText('GitHub Actions'), 'false');

    expect(within(screen.getByRole('region', { name: 'Unsaved changes' })).getByText('5 unsaved changes')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Save changes/ }));

    const expected: PreferenceChange[] = [
      { key: 'language', action: 'set', value: 'pt-BR' },
      { key: 'model_max_tokens', action: 'set', value: 1000000 },
      { key: 'worktree_active', action: 'set', value: false },
      { key: 'worktree_commit_action', action: 'set', value: 'finalize' },
      { key: 'ci_cd_detected', action: 'set', value: false },
    ];
    expect(bridge.updateProjectPreferences).toHaveBeenCalledWith('proj-1', expected);
    expect(await screen.findByText(/Saved 5 changes to this project/)).toBeInTheDocument();
    expect(bridge.projectPreferences).toHaveBeenCalledTimes(2);
  });

  it('treats an edit changed back to the original value as no change', async () => {
    renderSettings();
    const user = userEvent.setup();
    const toggle = await screen.findByRole('switch', { name: 'Mute notifications' });
    await user.click(toggle);
    expect(within(screen.getByRole('region', { name: 'Unsaved changes' })).getByText('1 unsaved change')).toBeInTheDocument();
    await user.click(toggle);
    expect(screen.queryByRole('region', { name: 'Unsaved changes' })).not.toBeInTheDocument();
  });

  it('turns Reset to inherited into an unset of the project layer', async () => {
    const { bridge } = renderSettings();
    const user = userEvent.setup();
    // `language` is the one fixture key set in the project layer.
    const resets = await screen.findAllByRole('button', { name: /Reset to inherited/ });
    await user.click(resets[0]!);
    // The badge names the value the reset brings back, and the control already shows it.
    expect(screen.getByText('reverts to “pt-BR” on save')).toBeInTheDocument();
    expect(screen.getByLabelText('Conversation language')).toHaveValue('pt-BR');

    await user.click(screen.getByRole('button', { name: /Save changes/ }));
    expect(bridge.updateProjectPreferences).toHaveBeenCalledWith('proj-1', [{ key: 'language', action: 'unset' }]);
  });

  it('can choose the null option of a select whose current value is set', async () => {
    const { bridge } = renderSettings({
      projectPreferences: prefsWith({ qa_browser: 'chrome', ci_cd_detected: true }, { qa_browser: 'global', ci_cd_detected: 'project' }),
    });
    const user = userEvent.setup();
    const browser = await screen.findByLabelText('QA browser');
    expect(browser).toHaveValue('chrome');
    await user.selectOptions(browser, '__null__');
    await user.selectOptions(screen.getByLabelText('GitHub Actions'), '__null__');

    // The control shows what will be saved — it used to snap back to the old value.
    expect(browser).toHaveValue('__null__');
    expect(screen.getByLabelText('GitHub Actions')).toHaveValue('__null__');
    await user.click(screen.getByRole('button', { name: /Save changes/ }));
    expect(bridge.updateProjectPreferences).toHaveBeenCalledWith('proj-1', [
      { key: 'qa_browser', action: 'set', value: null },
      { key: 'ci_cd_detected', action: 'set', value: null },
    ]);
  });

  it('saves on ⌘S only while its tab is visible', async () => {
    const { bridge, setActive } = renderSettings();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('switch', { name: 'Mute notifications' }));

    setActive(false);
    await user.keyboard('{Meta>}s{/Meta}');
    expect(bridge.updateProjectPreferences).not.toHaveBeenCalled();

    setActive(true);
    await user.keyboard('{Meta>}s{/Meta}');
    expect(bridge.updateProjectPreferences).toHaveBeenCalledOnce();
  });

  it('disables the form while saving, and keeps the saved values on screen until the reload lands', async () => {
    let finish: (value: OperationResult<PreferenceUpdateReport>) => void = () => {};
    const { bridge } = renderSettings({
      updateProjectPreferences: vi.fn(
        () => new Promise<OperationResult<PreferenceUpdateReport>>((resolve) => (finish = resolve)),
      ),
    });
    const user = userEvent.setup();
    const toggle = await screen.findByRole('switch', { name: 'Mute notifications' });
    await user.click(toggle);
    await user.click(screen.getByRole('button', { name: /Save changes/ }));

    expect(toggle).toBeDisabled();
    expect(screen.getByLabelText('Conversation language')).toBeDisabled();

    // The reload answers with the saved value; until then the draft keeps it on screen.
    const afterSave = prefsWith({ suppress_notifications: true }, { suppress_notifications: 'project' });
    vi.mocked(bridge.projectPreferences).mockImplementation(() => afterSave());
    finish(ok({ applied: [{ key: 'suppress_notifications', action: 'set', value: true }], failed: null }));
    expect(toggle).toBeChecked();
    await vi.waitFor(() => expect(toggle).toBeEnabled());
    expect(toggle).toBeChecked();
    expect(screen.queryByRole('region', { name: 'Unsaved changes' })).not.toBeInTheDocument();
  });

  it('keeps Save disabled while prefs set is withheld, and says why', async () => {
    renderSettings({}, environment({ withheld: [{ command: 'prefs set', reason: 'the store is newer than this app' }] }));
    const user = userEvent.setup();
    await user.click(await screen.findByRole('switch', { name: 'Isolated Docker stack per worktree' }));

    expect(screen.getByText('Saving is unavailable right now')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save changes/ })).toBeDisabled();
  });

  it('says which keys were written when a batch fails part-way, and keeps the rest', async () => {
    const partial: OperationResult<PreferenceUpdateReport> = ok({
      applied: [{ key: 'language', action: 'set', value: 'es' }],
      failed: {
        change: { key: 'worktree_active', action: 'set', value: false },
        problem: {
          ok: false,
          kind: 'usage',
          message: 'worktree_active expects true or false',
          exitCode: 2,
          command: 'devteam prefs set worktree_active false',
          durationMs: 5,
        },
      },
    });
    renderSettings({ updateProjectPreferences: vi.fn(() => Promise.resolve(partial)) });
    const user = userEvent.setup();

    await user.selectOptions(await screen.findByLabelText('Conversation language'), 'es');
    await user.click(screen.getByRole('switch', { name: 'Use a worktree per task' }));
    await user.click(screen.getByRole('button', { name: /Save changes/ }));

    expect(await screen.findByText(/1 change was saved \(Conversation language\) before one failed/)).toBeInTheDocument();
    expect(screen.getByText('worktree_active expects true or false')).toBeInTheDocument();
    // The failed key is still a pending edit once the reload has landed.
    expect(
      await within(screen.getByRole('region', { name: 'Unsaved changes' })).findByText('1 unsaved change'),
    ).toBeInTheDocument();
  });
});
