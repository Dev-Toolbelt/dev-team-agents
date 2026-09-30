// @vitest-environment jsdom
/**
 * `Doctor` renders what the CLI answered, not what a screen assumed about it.
 *
 * Two things a misrendering could get silently wrong: treating `outcome: 'findings'`
 * (exit 1, a complete report) as an error and showing nothing on the one screen whose
 * whole purpose is the report, and dropping `hint` from a genuine failure.
 *
 * The app-health section above it is a different subject (see `selfCheck.test.ts` for its
 * own branch coverage) — these tests only check that it renders, that a `fail` is visible
 * as text and not only as colour, and that it never masks or is masked by the store section.
 */
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Doctor } from '../../src/renderer/screens/Doctor.js';
import { cliResolutionNotFound, doctorReport, fail, fakeBridge, installBridge, ok } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Doctor', () => {
  it('renders a findings result as the report it is, not as a failure', async () => {
    const report = doctorReport({
      status: 'warn',
      findings: [
        { level: 'warn', category: 'symlinks', message: 'a skill reference is broken', hint: 'run the symlink repair' },
      ],
      actions: ['repaired 2 broken symlinks'],
    });
    installBridge(fakeBridge({ doctor: vi.fn(() => Promise.resolve(ok(report, { outcome: 'findings' }))) }));

    render(<Doctor />);

    expect(await screen.findByText('a skill reference is broken')).toBeInTheDocument();
    expect(screen.getByText('run the symlink repair')).toBeInTheDocument();
    // The findings-is-not-an-error distinction, stated in the copy the screen itself uses.
    expect(screen.getByText(/that is a result, not a failure/i)).toBeInTheDocument();
    // `doctor` is the one mutating command this app runs; what it repaired is a write and
    // is labelled as one.
    expect(screen.getByText('repaired 2 broken symlinks')).toBeInTheDocument();
    expect(screen.getByText(/these were writes/i)).toBeInTheDocument();
  });

  it('renders an ok: false result as a failure, message and hint both reachable', async () => {
    installBridge(
      fakeBridge({
        doctor: vi.fn(() => Promise.resolve(fail('the store could not be reached', { hint: 'run `devteam doctor --no-project`', kind: 'unavailable' }))),
      }),
    );

    render(<Doctor />);

    expect(await screen.findByText('the store could not be reached')).toBeInTheDocument();
    expect(screen.getByText('run `devteam doctor --no-project`')).toBeInTheDocument();
    // A genuine failure renders the shared `Problem` alert instead of a report table.
    // Scoped to that alert, since the app-health section above it renders a table of its
    // own and a bare `queryByRole('table')` would now find that one instead.
    expect(within(screen.getByRole('alert')).queryByRole('table')).not.toBeInTheDocument();
  });

  it('renders nothing to report when the run found nothing', async () => {
    installBridge(fakeBridge({ doctor: vi.fn(() => Promise.resolve(ok(doctorReport({ status: 'ok' })))) }));

    render(<Doctor />);

    expect(await screen.findByText(/nothing to report/i)).toBeInTheDocument();
    expect(screen.getByText('No findings.')).toBeInTheDocument();
  });

  it('renders the app-health section above the store section, independently of it', async () => {
    installBridge(fakeBridge({ doctor: vi.fn(() => Promise.resolve(ok(doctorReport({ status: 'ok' })))) }));

    render(<Doctor />);

    expect(await screen.findByRole('heading', { name: 'This app' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'The store' })).toBeInTheDocument();
  });

  it('shows a failing app precondition as visible text, not only by colour, without hiding the store section', async () => {
    installBridge(fakeBridge({ resolveCli: vi.fn(() => Promise.resolve(cliResolutionNotFound())) }));

    render(<Doctor />);

    const appSection = (await screen.findByRole('heading', { name: 'This app' })).closest('section');
    expect(appSection).not.toBeNull();
    // "fail" appears twice inside the section — the status line and the finding's own
    // badge — so it is asserted as text present at least once, not by a single unique node.
    expect(within(appSection as HTMLElement).getAllByText('fail').length).toBeGreaterThan(0);
    expect(within(appSection as HTMLElement).getByText(/no devteam cli could be found/i)).toBeInTheDocument();
    // A failing app precondition does not prevent the store section from rendering.
    expect(screen.getByRole('heading', { name: 'The store' })).toBeInTheDocument();
  });

  it('says so, instead of loading forever, when the app cannot read its own state', async () => {
    installBridge(fakeBridge({ environment: vi.fn(() => Promise.reject(new Error('ipc gone'))) }));

    render(<Doctor />);

    expect(await screen.findByText(/could not read its own state/i)).toBeInTheDocument();
    expect(screen.getByText(/ipc gone/)).toBeInTheDocument();
    expect(screen.queryByText(/running this app's own preconditions/i)).not.toBeInTheDocument();
  });
});
