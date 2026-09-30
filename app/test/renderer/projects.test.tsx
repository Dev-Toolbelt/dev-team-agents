// @vitest-environment jsdom
/**
 * `Projects` is the screen ADR-0015's fourth Risks row names: "a misrendered `list` leads
 * a user to a destructive action they take in the terminal, where no gate applies." Every
 * test below asserts a way that could happen — a wrong `path_exists` badge, a write button
 * enabled when the environment withheld it, an unbind that fires without its confirm step,
 * an upgrade offering Apply before a plan exists, a bind sending a path the app was never
 * given — and asserts the opposite is true.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Projects } from '../../src/renderer/screens/Projects.js';
import type { DevteamBridge, DirectoryChoice, OperationResult, ProjectFolders, ProjectFoldersAnswer, UpgradePlan } from '../../src/shared/api.js';
import {
  bindReport,
  deferred,
  environment,
  fail,
  fakeBridge,
  installBridge,
  migrationPlan,
  migrationReport,
  ok,
  project,
  unbindReport,
  upgradePlan,
  upgradeReport,
} from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Projects — path_exists is rendered faithfully', () => {
  it('shows a missing badge only for false, never for true or null', async () => {
    // Rows are found by display name (the path's basename) — the id is never rendered.
    const projects = [
      project({ project_id: 'exists', path: '/repo/dir-a', path_exists: true }),
      project({ project_id: 'gone', path: '/repo/dir-b', path_exists: false }),
      project({ project_id: 'unknown', path: '/repo/dir-c', path_exists: null }),
    ];
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects }))) }));

    render(<Projects environment={environment()} />);
    await screen.findByText('dir-a');

    const existsRow = screen.getByText('dir-a').closest('tr')!;
    const goneRow = screen.getByText('dir-b').closest('tr')!;
    const unknownRow = screen.getByText('dir-c').closest('tr')!;

    expect(within(existsRow).queryByText('missing')).not.toBeInTheDocument();
    expect(within(existsRow).queryByText('not checked')).not.toBeInTheDocument();

    // `false` is the only state ever labelled "missing" — the collapse this guards
    // against is `null` (silence) rendering the same destructive badge as `false`.
    expect(within(goneRow).getByText('missing')).toBeInTheDocument();

    // `null` gets its own, non-alarming label — never "missing" and never nothing.
    expect(within(unknownRow).getByText('not checked')).toBeInTheDocument();
    expect(within(unknownRow).queryByText('missing')).not.toBeInTheDocument();
  });
});

describe('Projects — write actions are withheld honestly', () => {
  it('disables the withheld action and states why on the wrapper and to assistive tech', async () => {
    const user = userEvent.setup();
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: null, projects: [] }))) }));
    const env = environment({ withheld: [{ command: 'bind', reason: 'the schema declaration could not be written' }] });

    render(<Projects environment={env} />);
    const bindButton = await screen.findByRole('button', { name: /withheld: the schema declaration/i });

    expect(bindButton).toBeDisabled();
    // The tooltip hangs on the wrapper — a disabled button gets no hover of its own.
    await user.hover(bindButton.closest('span')!);
    expect(await screen.findByRole('tooltip')).toHaveTextContent('the schema declaration could not be written');
  });

  it('fails closed while the environment has not answered yet, rather than enabling writes', async () => {
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))),
      }),
    );

    render(<Projects environment={null} />);
    await screen.findByText('project-1');

    // Not anchored: `environment === null` gives every `WriteButton` an
    // `aria-label` of `"<label> — withheld: …"`, not the bare label.
    for (const name of [/bind/i, /sync/i, /pin/i, /upgrade/i, /unbind/i]) {
      const button = screen.getAllByRole('button', { name }).find((candidate) => candidate.hasAttribute('disabled'));
      expect(button, `expected a disabled button matching ${String(name)}`).toBeDefined();
    }
  });
});

describe('Projects — a successful write surfaces its notice, and only when there is one', () => {
  // `syncAllProjects`, not the per-row `syncProject`: see the per-row finding in the test
  // report — a row-level write's `Notice` is unmounted mid-flight by the list reload its
  // own success triggers, so it can never be asserted as visible. `Sync all` lives on
  // `Projects` itself, which survives its own reload, and is the one write path where
  // this is provable.
  it('shows stderr from a successful command, and shows nothing when there was none', async () => {
    const user = userEvent.setup();
    const syncAllProjects = vi
      .fn()
      .mockResolvedValueOnce(ok({ synced: [], problems: [] }, { notice: 'bind artifacts were added to no ignore file' }));
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))),
        syncAllProjects,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');

    expect(screen.queryByText(/added to no ignore file/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^sync all$/i }));

    expect(await screen.findByText(/added to no ignore file/i)).toBeInTheDocument();
    expect(screen.getByText(/the command succeeded and reported this/i)).toBeInTheDocument();
  });

  it('shows no notice banner when the command reported none', async () => {
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))) }));
    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    expect(screen.queryByText(/the command succeeded and reported this/i)).not.toBeInTheDocument();
  });
});

describe('Projects — the destructive path needs the confirm step', () => {
  it('does not call unbind from the row button, only from the dialog confirm, and reports a count not the list', async () => {
    const user = userEvent.setup();
    const unbindProject = vi.fn(() =>
      Promise.resolve(ok(unbindReport({ quarantined: [{ to: '/store/quarantine/proj-1/2026-09-29' }] }))),
    );
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))),
        unbindProject,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');

    await user.click(screen.getByRole('button', { name: /unbind…/i }));
    // Opening the dialog must not itself have fired the write.
    expect(unbindProject).not.toHaveBeenCalled();

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /^unbind$/i }));

    expect(unbindProject).toHaveBeenCalledTimes(1);
    // 159 entries: the count is shown, the list is not.
    expect(await within(dialog).findByText('159 links removed.')).toBeInTheDocument();
    expect(within(dialog).queryByText('file-0')).not.toBeInTheDocument();
    // `quarantined` is the one the user must read.
    expect(within(dialog).getByText('/store/quarantine/proj-1/2026-09-29')).toBeInTheDocument();
  });
});

describe('Projects — the upgrade order is enforced structurally', () => {
  it('withholds Apply until the plan has resolved, and shows collisions, git_tracked and actions first', async () => {
    const user = userEvent.setup();
    const plan = upgradePlan({
      collisions: ['docs/project.md'],
      git_tracked: ['.dev-team-agents/user-data/session-summary.md'],
      actions: ['move session-summary.md into the store'],
    });
    let resolvePlan!: (value: OperationResult<UpgradePlan>) => void;
    const planUpgrade = vi.fn(
      () => new Promise<OperationResult<UpgradePlan>>((resolve) => (resolvePlan = resolve)),
    );
    const applyUpgrade = vi.fn(() => Promise.resolve(ok(upgradeReport())));
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))),
        planUpgrade,
        applyUpgrade,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /upgrade…/i }));

    const dialog = await screen.findByRole('dialog');
    // Before the plan resolves, Apply is not available to click.
    expect(within(dialog).getByRole('button', { name: /apply/i })).toBeDisabled();
    expect(applyUpgrade).not.toHaveBeenCalled();

    resolvePlan(ok(plan));

    expect(await within(dialog).findByText('docs/project.md')).toBeInTheDocument();
    expect(within(dialog).getByText('.dev-team-agents/user-data/session-summary.md')).toBeInTheDocument();
    expect(within(dialog).getByText('move session-summary.md into the store')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /apply/i })).toBeEnabled();

    await user.click(within(dialog).getByRole('button', { name: /apply/i }));
    expect(applyUpgrade).toHaveBeenCalledTimes(1);
  });
});

describe('Projects — bind sends no path the app was not given', () => {
  it('changes nothing on a dismissed picker, and shows merged_project_files on success', async () => {
    const user = userEvent.setup();
    const chooseProjectDirectory = vi.fn<() => Promise<DirectoryChoice>>(() => Promise.resolve({ chosen: false }));
    const bindProject = vi.fn(() => Promise.resolve(ok(bindReport({ merged_project_files: ['.gitignore', 'package.json'] }))));
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory,
        bindProject,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    // A dismissed picker: the confirm Bind button stays disabled, and nothing was sent.
    expect(await within(dialog).findByText(/no directory chosen yet/i)).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /^bind$/i })).toBeDisabled();
    expect(bindProject).not.toHaveBeenCalled();

    // Now the picker returns a path, and only then can Bind be confirmed.
    chooseProjectDirectory.mockResolvedValueOnce({ chosen: true, path: '/Users/dev/my-project' });
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await within(dialog).findByText('/Users/dev/my-project');
    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));

    expect(bindProject).toHaveBeenCalledTimes(1);
    expect(bindProject).toHaveBeenCalledWith(expect.objectContaining({ path: '/Users/dev/my-project' }));
    expect(await within(dialog).findByText('.gitignore')).toBeInTheDocument();
    expect(within(dialog).getByText('package.json')).toBeInTheDocument();
    expect(within(dialog).getByText(/commit them yourself/i)).toBeInTheDocument();
  });
});

describe('Projects — bind defaults to the recommended mode, but lets it be changed', () => {
  it('opens with link pre-selected and marked recommended, and sends it even though the user touched nothing in the fieldset', async () => {
    const user = userEvent.setup();
    const chooseProjectDirectory = vi.fn<() => Promise<DirectoryChoice>>(() =>
      Promise.resolve({ chosen: true, path: '/Users/dev/my-project' }),
    );
    const bindProject = vi.fn(() => Promise.resolve(ok(bindReport())));
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory,
        bindProject,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await within(dialog).findByText('/Users/dev/my-project');
    expect(within(dialog).getByRole('radio', { name: /link \(recommended\)/i })).toBeChecked();

    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));

    // Unlike `providers`, which stays omitted until the user checks one, `mode` is always
    // sent — the app has an opinion now, so the pre-selected recommendation goes out as-is.
    expect(bindProject).toHaveBeenCalledWith(expect.objectContaining({ mode: 'link' }));
  });

  it('sends whatever mode the user switches to instead', async () => {
    const user = userEvent.setup();
    const chooseProjectDirectory = vi.fn<() => Promise<DirectoryChoice>>(() =>
      Promise.resolve({ chosen: true, path: '/Users/dev/my-project' }),
    );
    const bindProject = vi.fn(() => Promise.resolve(ok(bindReport({ mode: 'copy' }))));
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory,
        bindProject,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await within(dialog).findByText('/Users/dev/my-project');
    await user.click(within(dialog).getByRole('radio', { name: /^copy$/i }));
    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));

    expect(bindProject).toHaveBeenCalledWith(expect.objectContaining({ mode: 'copy' }));
  });
});

describe('Projects — a successful write refreshes the list', () => {
  it('calls listProjects again after a write resolves', async () => {
    const user = userEvent.setup();
    const listProjects = vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] })));
    installBridge(fakeBridge({ listProjects, syncProject: vi.fn(() => Promise.resolve(ok(bindReport()))) }));

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    expect(listProjects).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /^sync$/i }));

    await vi.waitFor(() => expect(listProjects).toHaveBeenCalledTimes(2));
  });
});

describe('Projects — a row-level notice survives the reload its own write triggers', () => {
  /**
   * This was a real defect, found by this file and fixed in `useOperation`.
   *
   * `ProjectRow`'s per-row `sync`/`pin` call `onChanged()` on success, which calls the
   * parent's `reload()`. `useOperation` used to reset to `phase: 'loading'` on every re-run,
   * so `Projects` replaced its whole `<Table>` with `<Loading />` — unmounting every
   * `ProjectRow`, including the one whose `Notice` the success branch had just set. The
   * notice was unreadable *by construction*: the thing that produced it destroyed the
   * component that showed it. `Sync all` never had the problem, because its state lives in
   * `Projects` itself, above the early `Loading` return.
   *
   * The fix is that a **reload keeps the result already on screen** and only the first load
   * blanks it (`useOperation`'s `refreshing`). This test is the regression: it asserts the
   * notice is still readable after the write's own reload has settled.
   */
  it('keeps the row-level notice readable after the write reloads the list', async () => {
    const syncProject = vi
      .fn()
      .mockResolvedValueOnce(ok(bindReport(), { notice: 'bind artifacts were added to no ignore file' }));
    const listProjects = vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] })));
    installBridge(fakeBridge({ listProjects, syncProject }));

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await userEvent.setup().click(screen.getByRole('button', { name: /^sync$/i }));

    await vi.waitFor(() => expect(syncProject).toHaveBeenCalledTimes(1));
    // The reload happened — so this is not passing because nothing refreshed.
    await vi.waitFor(() => expect(listProjects).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/added to no ignore file/i)).toBeInTheDocument();
    // And the row was never unmounted, which is what made the notice unreadable before.
    expect(screen.getByText('project-1')).toBeInTheDocument();
  });

  it('shows nothing in place of the table while a reload is in flight, and says it is refreshing', async () => {
    // Initialised to a no-op rather than null: the assignment below happens inside a
    // closure the compiler cannot see, so a nullable type narrows to `null` here and the
    // call stops type-checking. The no-op keeps the type `() => void` throughout.
    let releaseSecondList: () => void = () => {};
    const listProjects = vi
      .fn()
      .mockResolvedValueOnce(ok({ current: '2.48.0', projects: [project()] }))
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            releaseSecondList = () => resolve(ok({ current: '2.48.0', projects: [project()] }));
          }),
      );
    installBridge(
      fakeBridge({
        listProjects,
        syncAllProjects: vi.fn(() => Promise.resolve(ok({ synced: [bindReport()], problems: [] }))),
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await userEvent.setup().click(screen.getByRole('button', { name: /sync all/i }));

    // Mid-reload: the table is still there and the refresh is announced.
    await screen.findByText(/refreshing the project list/i);
    expect(screen.getByText('project-1')).toBeInTheDocument();

    releaseSecondList();
    await vi.waitFor(() => expect(screen.queryByText(/refreshing the project list/i)).not.toBeInTheDocument());
  });
});

describe('Projects — project names: stored, rendered, and falling back to the basename', () => {
  it('falls back to the directory’s own basename when no name is stored for a project', async () => {
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() =>
          Promise.resolve(ok({ current: '2.48.0', projects: [project({ project_id: 'abc-123', path: '/repo/my-app' })] })),
        ),
        // The default `fakeBridge` already answers `projectNames` with `{}` — spelled out
        // here so the point of the test is not hidden in the fixture default.
        projectNames: vi.fn(() => Promise.resolve({})),
      }),
    );

    render(<Projects environment={environment()} />);

    // The basename is the row's name, and the id is never rendered at all.
    expect(await screen.findByText('my-app')).toBeInTheDocument();
    expect(screen.queryByText('abc-123')).not.toBeInTheDocument();
  });

  it('renders the stored name instead of the basename when one is on record', async () => {
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() =>
          Promise.resolve(ok({ current: '2.48.0', projects: [project({ project_id: 'abc-123', path: '/repo/my-app' })] })),
        ),
        projectNames: vi.fn(() => Promise.resolve({ 'abc-123': 'Storefront' })),
      }),
    );

    render(<Projects environment={environment()} />);

    expect(await screen.findByText('Storefront')).toBeInTheDocument();
    expect(screen.queryByText('my-app')).not.toBeInTheDocument();
    expect(screen.queryByText('abc-123')).not.toBeInTheDocument();
  });

  it('pre-fills the bind dialog’s name field with the chosen directory’s basename, editable', async () => {
    const user = userEvent.setup();
    const chooseProjectDirectory = vi.fn<() => Promise<DirectoryChoice>>(() =>
      Promise.resolve({ chosen: true, path: '/Users/dev/storefront-app' }),
    );
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));

    const nameField = await within(dialog).findByLabelText(/project name/i);
    expect(nameField).toHaveValue('storefront-app');

    // It is a suggestion, not a fixed value — the user can still change it.
    await user.clear(nameField);
    await user.type(nameField, 'Storefront');
    expect(nameField).toHaveValue('Storefront');
  });

  it('stores the name the user typed, and the newly bound project renders it in the table after Done', async () => {
    const user = userEvent.setup();
    const chooseProjectDirectory = vi.fn<() => Promise<DirectoryChoice>>(() =>
      Promise.resolve({ chosen: true, path: '/Users/dev/storefront-app' }),
    );
    const bindProject = vi.fn(() =>
      Promise.resolve(ok(bindReport({ project_id: 'proj-new', path: '/Users/dev/storefront-app' }))),
    );
    const listProjects = vi
      .fn()
      .mockResolvedValueOnce(ok({ current: '2.48.0', projects: [] }))
      .mockResolvedValue(
        ok({
          current: '2.48.0',
          projects: [project({ project_id: 'proj-new', path: '/Users/dev/storefront-app' })],
        }),
      );
    const projectNames = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockResolvedValue({ 'proj-new': 'Storefront' });
    installBridge(fakeBridge({ listProjects, projectNames, chooseProjectDirectory, bindProject }));

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    const nameField = await within(dialog).findByLabelText(/project name/i);
    await user.clear(nameField);
    await user.type(nameField, 'Storefront');
    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));

    // The success step reads as a name, and never shows the id.
    expect(await within(dialog).findByText('Storefront')).toBeInTheDocument();
    expect(within(dialog).queryByText('proj-new')).not.toBeInTheDocument();
    expect(bindProject).toHaveBeenCalledWith(expect.objectContaining({ name: 'Storefront' }));

    await user.click(within(dialog).getByRole('button', { name: /^done$/i }));

    // The table reflects it after the reload Done triggers.
    expect(await screen.findByText('Storefront')).toBeInTheDocument();
    expect(screen.queryByText('proj-new')).not.toBeInTheDocument();
  });
});

describe('Projects — the Bind dialog resets fully every time it is reopened', () => {
  /**
   * This was a real defect: `onBound` (in `Projects`) closes the dialog by calling the
   * parent's `onOpenChange` directly, bypassing `BindDialog`'s own `close()`. Pressing
   * "Bind…" again therefore reopened the same still-mounted dialog with the previous
   * bind's `bind.state.phase === 'done'` intact, showing the last "… is bound" result
   * instead of a fresh form. The fix resets on every open, not only on close — this test
   * pins it.
   */
  it('shows a fresh form, not the previous result, the second time it is opened', async () => {
    const user = userEvent.setup();
    const chooseProjectDirectory = vi.fn<() => Promise<DirectoryChoice>>(() =>
      Promise.resolve({ chosen: true, path: '/Users/dev/first-project' }),
    );
    const bindProject = vi.fn(() => Promise.resolve(ok(bindReport())));
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory,
        bindProject,
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));

    let dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await within(dialog).findByText('/Users/dev/first-project');
    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));
    await within(dialog).findByText(/is bound/i);

    await user.click(within(dialog).getByRole('button', { name: /^done$/i }));

    // Reopen. This must be a blank form — not the previous success screen, not the
    // previous directory choice.
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    dialog = await screen.findByRole('dialog');

    expect(within(dialog).queryByText(/is bound/i)).not.toBeInTheDocument();
    expect(within(dialog).getByText(/no directory chosen yet/i)).toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/project name/i)).not.toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /^bind$/i })).toBeDisabled();
  });
});

describe('Projects — filters narrow the list, client-side, and distinguish no-match from nothing-bound', () => {
  it('filters by text, by mode, and by providers (any-of), and reports a distinct empty state', async () => {
    const user = userEvent.setup();
    const projects = [
      project({ project_id: 'alpha-id', path: '/repo/alpha', mode: 'link', providers: ['claude'] }),
      project({ project_id: 'beta-id', path: '/repo/beta', mode: 'copy', providers: ['codex'] }),
    ];
    installBridge(fakeBridge({ listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects }))) }));

    render(<Projects environment={environment()} />);
    await screen.findByText('alpha');
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.getByText(/showing 2 of 2 projects/i)).toBeInTheDocument();

    // Free-text narrows by name (basename, here — neither project has a stored name).
    await user.type(screen.getByLabelText(/filter by name or path/i), 'alpha');
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.queryByText('beta')).not.toBeInTheDocument();
    expect(screen.getByText(/showing 1 of 2 projects/i)).toBeInTheDocument();
    await user.clear(screen.getByLabelText(/filter by name or path/i));

    // The mode select narrows independently.
    await user.selectOptions(screen.getByLabelText(/^mode$/i), 'copy');
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.queryByText('alpha')).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(/^mode$/i), 'all');

    // Provider checkboxes are any-of: checking just Codex still surfaces the row with only
    // Codex, and excludes the Claude-only one.
    await user.click(screen.getByRole('checkbox', { name: /codex \(openai\)/i }));
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.queryByText('alpha')).not.toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /codex \(openai\)/i }));

    // A combination matching nothing is reported distinctly from "nothing is bound yet" —
    // there is plenty bound, these filters just do not match any of it.
    await user.type(screen.getByLabelText(/filter by name or path/i), 'no-such-project');
    expect(await screen.findByText(/no bound project matches these filters/i)).toBeInTheDocument();
    expect(screen.queryByText(/nothing is bound yet/i)).not.toBeInTheDocument();
  });
});

describe('Projects — the bind form waits for a directory', () => {
  it('shows only the picker until a directory is chosen', async () => {
    const user = userEvent.setup();
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory: vi.fn<() => Promise<DirectoryChoice>>(() =>
          Promise.resolve({ chosen: true, path: '/Users/dev/my-project' }),
        ),
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');

    expect(within(dialog).queryByLabelText(/project name/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('radio')).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('checkbox')).not.toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    expect(await within(dialog).findByLabelText(/project name/i)).toBeInTheDocument();
    expect(within(dialog).getAllByRole('radio').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByRole('checkbox').length).toBeGreaterThan(0);
  });
});

describe('Projects — a directory that is already bound cannot be bound again', () => {
  async function choose(chosen: string) {
    const user = userEvent.setup();
    const bridge = fakeBridge({
      listProjects: vi.fn(() =>
        Promise.resolve(ok({ current: '2.48.0', projects: [project({ path: '/repo/project-1' })] })),
      ),
      chooseProjectDirectory: vi.fn<() => Promise<DirectoryChoice>>(() => Promise.resolve({ chosen: true, path: chosen })),
    });
    installBridge(bridge);
    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    return { dialog, bridge };
  }

  it('says so, hides the form, keeps Bind disabled and asks the CLI nothing', async () => {
    const { dialog, bridge } = await choose('/repo/project-1/');
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/already bound as project-1/i);
    expect(within(dialog).queryByLabelText(/project name/i)).not.toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /^bind$/i })).toBeDisabled();
    expect(bridge.planMigration).not.toHaveBeenCalled();
    expect(bridge.bindProject).not.toHaveBeenCalled();
  });

  it('refuses a directory inside a bound project, which the CLI would resolve to that project', async () => {
    const { dialog } = await choose('/repo/project-1/src');
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/inside project-1, which is already bound/i);
    expect(within(dialog).getByRole('button', { name: /^bind$/i })).toBeDisabled();
  });

  it('does not mistake a sibling with the same prefix for the bound project', async () => {
    const { dialog } = await choose('/repo/project-10');
    expect(await within(dialog).findByLabelText(/project name/i)).toBeInTheDocument();
    expect(within(dialog).queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('Projects — a v2 install is migrated from the bind dialog', () => {
  async function openAndChoose(overrides: Parameters<typeof fakeBridge>[0]) {
    const user = userEvent.setup();
    const bridge = fakeBridge({
      listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
      chooseProjectDirectory: vi.fn<() => Promise<DirectoryChoice>>(() =>
        Promise.resolve({ chosen: true, path: '/chosen/dir' }),
      ),
      ...overrides,
    });
    installBridge(bridge);
    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    return { user, dialog, bridge };
  }

  it('offers a reviewed migration instead of Bind, and applies exactly what was reviewed', async () => {
    const { user, dialog, bridge } = await openAndChoose({
      planMigration: vi.fn(() => Promise.resolve(ok(migrationPlan()))),
    });
    expect(await within(dialog).findByText(/dev-team-agents v2 found/i)).toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: /^bind$/i })).not.toBeInTheDocument();
    // Detection asked with the path alone; nothing was applied.
    expect(bridge.planMigration).toHaveBeenCalledWith({ path: '/chosen/dir' });
    expect(bridge.applyMigration).not.toHaveBeenCalled();

    await user.click(within(dialog).getByLabelText(/Claude Code/));
    await user.click(within(dialog).getByRole('button', { name: /review migration/i }));
    expect(await within(dialog).findByText(/what the migration does/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/leaves git's index/i)).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: /^migrate$/i }));
    expect(await within(dialog).findByText(/is migrated and bound/i)).toBeInTheDocument();
    const reviewedWith = vi.mocked(bridge.planMigration).mock.calls[1]?.[0];
    const appliedWith = vi.mocked(bridge.applyMigration).mock.calls[0]?.[0];
    expect(appliedWith).toEqual(reviewedWith);
    expect(appliedWith).toMatchObject({ path: '/chosen/dir', providers: ['claude'], mode: 'link', name: 'dir' });
    expect(within(dialog).getByText(/left git's index/i)).toBeInTheDocument();
  });

  it('binds as before when the directory has no v2 install (exit 2)', async () => {
    const { user, dialog, bridge } = await openAndChoose({});
    const bindButton = await within(dialog).findByRole('button', { name: /^bind$/i });
    await vi.waitFor(() => expect(bindButton).toBeEnabled());
    await user.click(bindButton);
    await vi.waitFor(() => expect(bridge.bindProject).toHaveBeenCalled());
    expect(bridge.applyMigration).not.toHaveBeenCalled();
    expect(within(dialog).queryByText(/dev-team-agents v2 found/i)).not.toBeInTheDocument();
  });

  it('shows a detection problem other than "not v2", and keeps Bind disabled', async () => {
    const { dialog } = await openAndChoose({
      planMigration: vi.fn(() =>
        Promise.resolve(fail('two memory directories', { kind: 'conflict', exitCode: 4, hint: 'Merge them by hand.' })),
      ),
    });
    expect(await within(dialog).findByText(/two memory directories/)).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /^bind$/i })).toBeDisabled();
  });

  it('reports an untrack problem without calling the migration a failure', async () => {
    const { user, dialog } = await openAndChoose({
      planMigration: vi.fn(() => Promise.resolve(ok(migrationPlan()))),
      applyMigration: vi.fn(() =>
        Promise.resolve(ok(migrationReport({ untracked: [], untrack_problem: '/chosen/dir is not inside a git work tree' }))),
      ),
    });
    await user.click(await within(dialog).findByRole('button', { name: /review migration/i }));
    await user.click(await within(dialog).findByRole('button', { name: /^migrate$/i }));
    expect(await within(dialog).findByText(/is migrated and bound/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/nothing was untracked/i)).toBeInTheDocument();
  });
});

describe('Projects — the Version column says whether a project is current', () => {
  it('marks a project on the current store version up to date and any other one outdated', async () => {
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() =>
          Promise.resolve(
            ok({
              current: '2.48.0',
              projects: [
                project({ project_id: 'a', path: '/repo/fresh', resolves_to: '2.48.0' }),
                project({ project_id: 'b', path: '/repo/stale', resolves_to: '2.40.0' }),
              ],
            }),
          ),
        ),
      }),
    );

    render(<Projects environment={environment()} />);
    const freshRow = (await screen.findByText('fresh')).closest('tr')!;
    const staleRow = screen.getByText('stale').closest('tr')!;

    expect(within(freshRow).getByRole('img', { name: /up to date/i })).toBeInTheDocument();
    expect(within(staleRow).getByRole('img', { name: /outdated.*2\.48\.0/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Version' })).toBeInTheDocument();
  });

  it('claims neither when the store has no current version', async () => {
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() =>
          Promise.resolve(ok({ current: null, projects: [project({ path: '/repo/lonely', resolves_to: '2.48.0' })] })),
        ),
      }),
    );

    render(<Projects environment={environment()} />);
    const row = (await screen.findByText('lonely')).closest('tr')!;
    expect(within(row).queryByRole('img')).not.toBeInTheDocument();
  });
});

describe('Projects — a bind that adopted a v2 preferences file says so', () => {
  async function bindWith(report: ReturnType<typeof bindReport>) {
    const user = userEvent.setup();
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
        chooseProjectDirectory: vi.fn<() => Promise<DirectoryChoice>>(() =>
          Promise.resolve({ chosen: true, path: '/Users/dev/legacy' }),
        ),
        bindProject: vi.fn(() => Promise.resolve(ok(report))),
      }),
    );
    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await within(dialog).findByText('/Users/dev/legacy');
    await user.click(within(dialog).getByRole('button', { name: /^bind$/i }));
    await within(dialog).findByText(/is bound/i);
    return dialog;
  }

  const imported = {
    source: '.dev-team-agents/user-data/preferences.json',
    imported: ['language', 'worktree_active'],
    unchanged: [],
    conflicts: ['qa_browser'],
    ignored: [{ key: 'old_key', reason: 'unknown' }],
    quarantined: '/store/data/quarantine/2026-09-29/proj-1/imported-preferences/preferences.json',
    problem: null,
  };

  it('counts what was imported, and names conflicts and ignored keys', async () => {
    const dialog = await bindWith(bindReport({ preferences_import: imported }));
    expect(within(dialog).getByText(/2 preferences were imported from the old preferences file/)).toBeInTheDocument();
    expect(within(dialog).getByText('qa_browser')).toBeInTheDocument();
    expect(within(dialog).getByText('old_key (unknown)')).toBeInTheDocument();
  });

  it('says the file was left in place, and why, when the import did not happen', async () => {
    const dialog = await bindWith(
      bindReport({ preferences_import: { ...imported, imported: [], quarantined: null, problem: 'not a JSON object; left in place' } }),
    );
    expect(within(dialog).getByText(/were not imported: not a JSON object; left in place/)).toBeInTheDocument();
  });

  it('says nothing when there was no old file', async () => {
    const dialog = await bindWith(bindReport({ preferences_import: null }));
    expect(within(dialog).queryByText(/old preferences file/)).not.toBeInTheDocument();
  });
});


describe('Projects — a successful write refreshes the list however the dialog is left', () => {
  function listing() {
    return vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] })));
  }

  it('reloads on Esc after an unbind, and reopens Unbind as a fresh confirm step', async () => {
    const user = userEvent.setup();
    const listProjects = listing();
    installBridge(fakeBridge({ listProjects }));

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /unbind…/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /^unbind$/i }));
    await within(dialog).findByText('159 links removed.');
    // Held until the dialog closes: the reload removes the row, and the report with it.
    expect(listProjects).toHaveBeenCalledTimes(1);

    await user.keyboard('{Escape}');
    await vi.waitFor(() => expect(listProjects).toHaveBeenCalledTimes(2));

    await user.click(screen.getByRole('button', { name: /unbind…/i }));
    const reopened = await screen.findByRole('dialog');
    expect(within(reopened).queryByText('159 links removed.')).not.toBeInTheDocument();
    expect(within(reopened).getByRole('button', { name: /^unbind$/i })).toBeEnabled();
  });

  it('does not close an Unbind dialog while the write is pending', async () => {
    const user = userEvent.setup();
    const pending = deferred<OperationResult<ReturnType<typeof unbindReport>>>();
    installBridge(fakeBridge({ listProjects: listing(), unbindProject: vi.fn(() => pending.promise) }));

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /unbind…/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /^unbind/i }));

    await user.keyboard('{Escape}');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /cancel/i })).toBeDisabled();

    pending.resolve(ok(unbindReport()));
    expect(await within(dialog).findByText('159 links removed.')).toBeInTheDocument();
  });

  it('reloads as soon as an upgrade applies, and blocks Esc while it is applying', async () => {
    const user = userEvent.setup();
    const listProjects = listing();
    const applying = deferred<OperationResult<ReturnType<typeof upgradeReport>>>();
    installBridge(fakeBridge({ listProjects, applyUpgrade: vi.fn(() => applying.promise) }));

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /upgrade…/i }));
    const dialog = await screen.findByRole('dialog');
    await vi.waitFor(() => expect(within(dialog).getByRole('button', { name: /apply/i })).toBeEnabled());
    await user.click(within(dialog).getByRole('button', { name: /apply/i }));

    await user.keyboard('{Escape}');
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    applying.resolve(ok(upgradeReport()));
    // Before "Done" is pressed.
    await vi.waitFor(() => expect(listProjects).toHaveBeenCalledTimes(2));
    await user.click(await within(dialog).findByRole('button', { name: /^done$/i }));
    // Done only closes; it does not reload a second time.
    expect(listProjects).toHaveBeenCalledTimes(2);
  });

  it('reloads as soon as a bind lands, and Done only closes', async () => {
    const user = userEvent.setup();
    const listProjects = listing();
    installBridge(
      fakeBridge({
        listProjects,
        chooseProjectDirectory: vi.fn(() => Promise.resolve({ chosen: true, path: '/Users/dev/new-app' } as const)),
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await user.click(await within(dialog).findByRole('button', { name: /^bind$/i }));

    await vi.waitFor(() => expect(listProjects).toHaveBeenCalledTimes(2));
    await user.click(await within(dialog).findByRole('button', { name: /^done$/i }));
    expect(listProjects).toHaveBeenCalledTimes(2);
  });

  it('does not close the Bind dialog while the bind is pending', async () => {
    const user = userEvent.setup();
    const pending = deferred<OperationResult<ReturnType<typeof bindReport>>>();
    installBridge(
      fakeBridge({
        listProjects: listing(),
        chooseProjectDirectory: vi.fn(() => Promise.resolve({ chosen: true, path: '/Users/dev/new-app' } as const)),
        bindProject: vi.fn(() => pending.promise),
      }),
    );

    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));
    await user.click(await within(dialog).findByRole('button', { name: /^bind$/i }));

    await user.keyboard('{Escape}');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    pending.resolve(ok(bindReport()));
    await within(dialog).findByRole('button', { name: /^done$/i });
  });
});

describe('Projects — a failed list can be retried', () => {
  it('offers Try again next to the problem and reloads the list', async () => {
    const user = userEvent.setup();
    const listProjects = vi
      .fn()
      .mockResolvedValueOnce(fail('the store is locked', { kind: 'unavailable' }))
      .mockResolvedValue(ok({ current: '2.48.0', projects: [project()] }));
    installBridge(fakeBridge({ listProjects }));

    render(<Projects environment={environment()} />);
    expect(await screen.findByText('the store is locked')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /try again/i }));

    expect(await screen.findByText('project-1')).toBeInTheDocument();
    expect(listProjects).toHaveBeenCalledTimes(2);
  });
});

describe('Projects — bridge failures do not strand the screen', () => {
  it('falls back to basenames when the stored names cannot be read', async () => {
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))),
        projectNames: vi.fn(() => Promise.reject(new Error('ipc gone'))),
      }),
    );
    render(<Projects environment={environment()} />);
    expect(await screen.findByText('project-1')).toBeInTheDocument();
  });

  it('turns a rejected row action into a shown problem and frees the button', async () => {
    const user = userEvent.setup();
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [project()] }))),
        syncProject: vi.fn(() => Promise.reject(new Error('handler gone'))),
      }),
    );
    render(<Projects environment={environment()} />);
    await screen.findByText('project-1');

    await user.click(screen.getByRole('button', { name: /^sync$/i }));

    expect(await screen.findByText(/could not reach its own main process/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^sync$/i })).toBeEnabled();
  });

  it('treats a picker that rejects as a dismissed one', async () => {
    const user = userEvent.setup();
    installBridge(
      fakeBridge({
        chooseProjectDirectory: vi.fn(() => Promise.reject(new Error('no picker'))),
      }),
    );
    render(<Projects environment={environment()} />);
    await screen.findByText(/nothing is bound yet/i);
    await user.click(screen.getByRole('button', { name: /^bind…$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /choose directory/i }));

    expect(await within(dialog).findByRole('button', { name: /choose directory/i })).toBeEnabled();
  });
});

describe('Projects — folders (ADR-0021)', () => {
  const PROJECTS = [
    project({ project_id: 'p1', path: '/repo/acme-site' }),
    project({ project_id: 'p2', path: '/repo/shop-front' }),
    project({ project_id: 'p3', path: '/repo/mobile-app' }),
  ];
  const SITES = { id: 'sites', name: 'Sites', parentId: null, collapsed: false };
  const APPS = { id: 'apps', name: 'Apps', parentId: null, collapsed: false };

  function withFolders(folders: ProjectFolders, overrides: Partial<DevteamBridge> = {}) {
    const bridge = fakeBridge({
      listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: PROJECTS }))),
      projectFolders: vi.fn(() => Promise.resolve(folders)),
      ...overrides,
    });
    installBridge(bridge);
    return bridge;
  }

  /** The `<tbody>` a folder's header row sits in: the group, and the drop target. */
  function group(name: RegExp | string): HTMLElement {
    const header = screen.getAllByRole('row').find((row) => row.hasAttribute('data-folder-header') && within(row).queryByText(name) !== null);
    return header!.closest('tbody')!;
  }

  function lastSaved(bridge: DevteamBridge): ProjectFolders {
    const calls = vi.mocked(bridge.saveProjectFolders).mock.calls;
    return calls[calls.length - 1]![0];
  }

  it('shows no group headers until a folder exists, then creates one from the header button', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [], membership: {} });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    expect(screen.queryByText('No folder')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /new folder/i }));
    await user.type(screen.getByLabelText('Name'), 'Sites');
    await user.click(screen.getByRole('button', { name: 'Create folder' }));

    expect(await screen.findByRole('button', { name: /^Sites/ })).toHaveAttribute('aria-expanded', 'true');
    expect(within(group('No folder')).getByText('acme-site')).toBeInTheDocument();
    expect(lastSaved(bridge).folders).toMatchObject([{ name: 'Sites', parentId: null }]);
  });

  it('refuses a duplicate name in the dialog, case-insensitively, without saving', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [SITES], membership: {} });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await user.click(screen.getByRole('button', { name: /new folder/i }));
    await user.type(screen.getByLabelText('Name'), 'sites');
    expect(screen.getByText(/already exists/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create folder' })).toBeDisabled();
    expect(bridge.saveProjectFolders).not.toHaveBeenCalled();
  });

  it('groups rows by folder and moves one through the row menu — the keyboard path', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [SITES, APPS], membership: { p1: 'sites' } });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    expect(within(group('Sites')).getByText('acme-site')).toBeInTheDocument();
    expect(within(group('No folder')).getByText('mobile-app')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Move mobile-app to a folder' }));
    await user.click(await screen.findByRole('menuitem', { name: /Apps/ }));

    expect(within(group('Apps')).getByText('mobile-app')).toBeInTheDocument();
    expect(lastSaved(bridge).membership).toEqual({ p1: 'sites', p3: 'apps' });
    expect(screen.getByText(/Moved mobile-app to “Apps”/)).toBeInTheDocument();
  });

  it('moves the selection in bulk, then clears it', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [SITES], membership: {} });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');

    await user.click(screen.getByRole('checkbox', { name: 'Select acme-site' }));
    await user.click(screen.getByRole('checkbox', { name: 'Select shop-front' }));
    const toolbar = screen.getByRole('region', { name: /selected projects/i });
    expect(toolbar).toHaveTextContent('2 selected');

    await user.click(within(toolbar).getByRole('button', { name: /move to/i }));
    await user.click(await screen.findByRole('menuitem', { name: /Sites/ }));

    expect(lastSaved(bridge).membership).toEqual({ p1: 'sites', p2: 'sites' });
    expect(screen.queryByRole('region', { name: /selected projects/i })).not.toBeInTheDocument();
  });

  it('drags a selected row and carries the whole selection onto the drop target', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [SITES], membership: {} });
    const { container } = render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await user.click(screen.getByRole('checkbox', { name: 'Select acme-site' }));
    await user.click(screen.getByRole('checkbox', { name: 'Select mobile-app' }));

    const handle = container.querySelector('[data-drag-handle="p1"]')!;
    fireEvent.dragStart(handle);
    expect(container.querySelectorAll('tr.opacity-50')).toHaveLength(2);
    fireEvent.dragOver(group('Sites'));
    fireEvent.drop(group('Sites'));

    // The save is queued behind any earlier one, so it lands a microtask later.
    await vi.waitFor(() => expect(bridge.saveProjectFolders).toHaveBeenCalled());
    expect(lastSaved(bridge).membership).toEqual({ p1: 'sites', p3: 'sites' });
    expect(within(group('Sites')).getByText('mobile-app')).toBeInTheDocument();
  });

  it('ignores a drop with no drag in progress', async () => {
    const bridge = withFolders({ folders: [SITES], membership: {} });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    fireEvent.drop(group('Sites'));
    await Promise.resolve();
    expect(bridge.saveProjectFolders).not.toHaveBeenCalled();
  });

  it('deletes a folder after a confirm step, filing its projects under no folder and unbinding nothing', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [SITES], membership: { p1: 'sites', p2: 'sites' } });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');

    await user.click(screen.getByRole('button', { name: 'Folder actions for Sites' }));
    await user.click(await screen.findByRole('menuitem', { name: /delete folder/i }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('Its 2 projects will move to “No folder”');
    await user.click(within(dialog).getByRole('button', { name: 'Delete folder' }));

    expect(lastSaved(bridge)).toEqual({ folders: [], membership: {} });
    expect(bridge.unbindProject).not.toHaveBeenCalled();
    expect(screen.getByText('acme-site')).toBeInTheDocument();
  });

  it('undoes the change and says why when the main process refuses to save', async () => {
    const user = userEvent.setup();
    withFolders(
      { folders: [SITES], membership: {} },
      { saveProjectFolders: vi.fn(() => Promise.resolve({ ok: false as const, message: 'The folders could not be saved: disk full' })) },
    );
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await user.click(screen.getByRole('button', { name: 'Move acme-site to a folder' }));
    await user.click(await screen.findByRole('menuitem', { name: /Sites/ }));

    expect(await screen.findByText('The folder change was undone')).toBeInTheDocument();
    expect(screen.getByText(/disk full/)).toBeInTheDocument();
    expect(within(group('No folder')).getByText('acme-site')).toBeInTheDocument();
  });

  it('collapses a folder and saves the choice, and a text filter opens it again', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [SITES], membership: { p1: 'sites' } });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');

    await user.click(screen.getByRole('button', { name: /^Sites/, expanded: true }));
    expect(screen.queryByText('acme-site')).not.toBeInTheDocument();
    expect(lastSaved(bridge).folders[0]?.collapsed).toBe(true);

    await user.type(screen.getByLabelText(/filter by name or path/i), 'acme');
    expect(screen.getByText('acme-site')).toBeInTheDocument();
  });

  it('hides a folder with no match while filtering', async () => {
    const user = userEvent.setup();
    withFolders({ folders: [SITES, APPS], membership: { p1: 'sites', p3: 'apps' } });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await user.type(screen.getByLabelText(/filter by name or path/i), 'mobile');
    expect(screen.queryByRole('button', { name: /^Sites/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Apps/ })).toBeInTheDocument();
  });

  it('syncs the selection one project at a time and names each failure', async () => {
    const user = userEvent.setup();
    const syncProject = vi
      .fn()
      .mockResolvedValueOnce(ok(bindReport()))
      .mockResolvedValueOnce(fail('the store is locked'));
    withFolders({ folders: [], membership: {} }, { syncProject });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await user.click(screen.getByRole('checkbox', { name: 'Select acme-site' }));
    await user.click(screen.getByRole('checkbox', { name: 'Select mobile-app' }));
    await user.click(screen.getByRole('button', { name: 'Sync selected' }));

    expect(await screen.findByText('Synced 1 of 2 projects.')).toBeInTheDocument();
    expect(syncProject.mock.calls).toEqual([['p1'], ['p3']]);
    expect(screen.getByText(/the store is locked/)).toBeInTheDocument();
  });

  it('drops membership of a project that is no longer bound', async () => {
    const bridge = withFolders({ folders: [SITES], membership: { p1: 'sites', gone: 'sites' } });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await vi.waitFor(() => expect(bridge.saveProjectFolders).toHaveBeenCalled());
    expect(lastSaved(bridge).membership).toEqual({ p1: 'sites' });
  });

  it('blocks every folder change while the stored folders could not be read, and retries', async () => {
    const user = userEvent.setup();
    const projectFolders = vi
      .fn<DevteamBridge['projectFolders']>()
      .mockRejectedValueOnce(new Error('EACCES'))
      .mockResolvedValueOnce({ folders: [SITES], membership: {} });
    const bridge = withFolders({ folders: [], membership: {} }, { projectFolders });
    render(<Projects environment={environment()} />);
    await screen.findByText('The folders could not be read');

    // The first action after a failed read must not be able to save an empty grouping.
    expect(screen.getByRole('button', { name: /new folder/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Move acme-site to a folder' })).toBeDisabled();
    expect(bridge.saveProjectFolders).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('button', { name: /^Sites/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new folder/i })).toBeEnabled();
  });

  it('never selects rows a collapsed folder hides, and checking a collapsed folder opens it', async () => {
    const user = userEvent.setup();
    const bridge = withFolders({ folders: [{ ...SITES, collapsed: true }], membership: { p1: 'sites', p2: 'sites' } });
    render(<Projects environment={environment()} />);
    await screen.findByText('mobile-app');

    await user.click(screen.getByRole('checkbox', { name: 'Select every project shown' }));
    expect(screen.getByRole('region', { name: /selected projects/i })).toHaveTextContent('1 selected');

    await user.click(screen.getByRole('checkbox', { name: 'Select every project in Sites' }));
    expect(screen.getByText('acme-site')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /selected projects/i })).toHaveTextContent('3 selected');
    expect(lastSaved(bridge).folders[0]?.collapsed).toBe(false);
  });

  it('holds every other sync while a bulk sync runs, and stops between projects when asked', async () => {
    const user = userEvent.setup();
    const first = deferred<OperationResult<ReturnType<typeof bindReport>>>();
    const syncProject = vi.fn().mockReturnValueOnce(first.promise).mockResolvedValue(ok(bindReport()));
    withFolders({ folders: [], membership: {} }, { syncProject });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');
    await user.click(screen.getByRole('checkbox', { name: 'Select acme-site' }));
    await user.click(screen.getByRole('checkbox', { name: 'Select mobile-app' }));
    await user.click(screen.getByRole('button', { name: 'Sync selected' }));

    expect(screen.getByRole('button', { name: /^sync all/i })).toBeDisabled();
    const shopRow = screen.getByText('shop-front').closest('tr')!;
    expect(within(shopRow).getByRole('button', { name: /^sync/i })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Stop after this one' }));
    first.resolve(ok(bindReport()));
    expect(await screen.findByText(/Synced 1 of 2 projects\. Stopped before the other 1\./)).toBeInTheDocument();
    expect(syncProject).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /^sync all/i })).toBeEnabled();
  });

  it('says how many queued changes a failed save took with it', async () => {
    const user = userEvent.setup();
    const firstSave = deferred<ProjectFoldersAnswer>();
    const saveProjectFolders = vi.fn<DevteamBridge['saveProjectFolders']>().mockReturnValueOnce(firstSave.promise);
    withFolders({ folders: [SITES, APPS], membership: {} }, { saveProjectFolders });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');

    await user.click(screen.getByRole('button', { name: 'Move acme-site to a folder' }));
    await user.click(await screen.findByRole('menuitem', { name: /Sites/ }));
    await user.click(screen.getByRole('button', { name: 'Move mobile-app to a folder' }));
    await user.click(await screen.findByRole('menuitem', { name: /Apps/ }));
    firstSave.resolve({ ok: false, message: 'The folders could not be saved: disk full.' });

    expect(await screen.findByText(/disk full\. 1 later change was undone with it\./)).toBeInTheDocument();
    expect(saveProjectFolders).toHaveBeenCalledTimes(1);
    expect(within(group('No folder')).getByText('mobile-app')).toBeInTheDocument();
  });

  it('keeps a shown error when housekeeping prunes an unbound project in the background', async () => {
    const user = userEvent.setup();
    const listProjects = vi
      .fn()
      .mockResolvedValueOnce(ok({ current: '2.48.0', projects: PROJECTS }))
      .mockResolvedValue(ok({ current: '2.48.0', projects: PROJECTS.slice(0, 2) }));
    const saveProjectFolders = vi
      .fn<DevteamBridge['saveProjectFolders']>()
      .mockResolvedValueOnce({ ok: false, message: 'The folders could not be saved: disk full' })
      .mockImplementation((folders) => Promise.resolve({ ok: true, folders }));
    withFolders({ folders: [SITES], membership: { p3: 'sites' } }, { listProjects, saveProjectFolders });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');

    await user.click(screen.getByRole('button', { name: 'Move acme-site to a folder' }));
    await user.click(await screen.findByRole('menuitem', { name: /Sites/ }));
    expect(await screen.findByText('The folder change was undone')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Refresh' }));
    await vi.waitFor(() => expect(saveProjectFolders).toHaveBeenCalledTimes(2));
    expect(saveProjectFolders.mock.calls[1]![0].membership).toEqual({});
    expect(screen.getByText('The folder change was undone')).toBeInTheDocument();
  });

  it('keeps a row sync in flight, and its result, when the row moves to another folder', async () => {
    const user = userEvent.setup();
    const pending = deferred<OperationResult<ReturnType<typeof bindReport>>>();
    withFolders({ folders: [SITES], membership: {} }, { syncProject: vi.fn(() => pending.promise) });
    render(<Projects environment={environment()} />);
    await screen.findByText('acme-site');

    const row = () => screen.getByText('acme-site').closest('tr')!;
    await user.click(within(row()).getByRole('button', { name: /^sync/i }));
    await user.click(screen.getByRole('button', { name: 'Move acme-site to a folder' }));
    await user.click(await screen.findByRole('menuitem', { name: /Sites/ }));

    expect(within(group('Sites')).getByText('acme-site')).toBeInTheDocument();
    expect(within(row()).getByRole('button', { name: /syncing/i })).toBeDisabled();
    pending.resolve(fail('the store is locked'));
    expect(await within(row()).findByText(/the store is locked/)).toBeInTheDocument();
  });
});
