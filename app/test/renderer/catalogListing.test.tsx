// @vitest-environment jsdom
/**
 * `Listing` orders what the CLI returned: every kind by name, and skills grouped under
 * sorted category headings with a category filter that composes with the text filter.
 */
import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Listing } from '../../src/renderer/screens/CatalogListing.js';
import type { CatalogEntry, CatalogKind } from '../../src/shared/api.js';
import { fakeBridge, installBridge, ok } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function serve(kind: CatalogKind, entries: CatalogEntry[]) {
  installBridge(fakeBridge({ catalogListing: vi.fn(() => Promise.resolve(ok({ kind, version: '1.0.0', project_id: null, count: entries.length, entries }))) }));
}

const entry = (name: string, category?: string | null): CatalogEntry => ({
  name,
  description: `${name} description`,
  path: `${name}.md`,
  version: '1.0.0',
  ...(category !== undefined ? { category } : {}),
});

const names = (scope: HTMLElement) =>
  within(scope)
    .getAllByText(/^[a-z-]+$/, { selector: 'span.font-mono' })
    .map((each) => each.textContent);

describe('Catalog listing', () => {
  it('sorts agents by name', async () => {
    serve('agents', [entry('qa-specialist'), entry('backend-developer'), entry('frontend-developer')]);

    render(<Listing kind="agents" />);

    await screen.findByText('backend-developer');
    expect(names(document.body)).toEqual(['backend-developer', 'frontend-developer', 'qa-specialist']);
  });

  it('sorts commands by name', async () => {
    serve('commands', [entry('version'), entry('adr'), entry('plan')]);

    render(<Listing kind="commands" />);

    await screen.findByText('adr');
    expect(names(document.body)).toEqual(['adr', 'plan', 'version']);
  });

  it('groups skills by sorted category, sorts within each, and puts uncategorized last', async () => {
    serve('skills', [
      entry('worktree', 'shared'),
      entry('orphan', null),
      entry('aws', 'devops'),
      entry('adr', 'shared'),
      entry('docker-dev', 'devops'),
    ]);

    render(<Listing kind="skills" />);

    const headings = await screen.findAllByRole('heading', { level: 3 });
    expect(headings.map((each) => each.textContent)).toEqual(['devops (2)', 'shared (2)', 'uncategorized (1)']);
    const shared = headings[1]?.closest('section') as HTMLElement;
    expect(names(shared)).toEqual(['adr', 'worktree']);
  });

  it('filters skills by category, combined with the text filter', async () => {
    serve('skills', [entry('aws', 'devops'), entry('docker-dev', 'devops'), entry('adr', 'shared')]);

    render(<Listing kind="skills" />);

    const select = await screen.findByLabelText('Filter skills by category');
    expect(within(select).getAllByRole('option').map((each) => each.textContent)).toEqual([
      'All categories',
      'devops',
      'shared',
    ]);

    fireEvent.change(select, { target: { value: 'devops' } });
    expect(names(document.body)).toEqual(['aws', 'docker-dev']);

    fireEvent.change(screen.getByLabelText('Filter skills'), { target: { value: 'docker' } });
    expect(names(document.body)).toEqual(['docker-dev']);

    fireEvent.change(screen.getByLabelText('Filter skills'), { target: { value: 'adr' } });
    expect(screen.getByText('No skills match the filters.')).toBeInTheDocument();
  });

  it('files an empty category under uncategorized, not as a second "All categories"', async () => {
    serve('skills', [entry('aws', 'devops'), entry('blank', '')]);

    render(<Listing kind="skills" />);

    const select = await screen.findByLabelText('Filter skills by category');
    expect(within(select).getAllByRole('option').map((each) => each.textContent)).toEqual([
      'All categories',
      'devops',
      'uncategorized',
    ]);
    const headings = screen.getAllByRole('heading', { level: 3 });
    expect(headings.map((each) => each.textContent)).toEqual(['devops (1)', 'uncategorized (1)']);
    // Each group is labelled by its own heading, whatever characters the category holds.
    expect(new Set(headings.map((each) => each.id)).size).toBe(2);
    expect(screen.getByRole('region', { name: 'uncategorized (1)' })).toBeInTheDocument();
  });

  it('says the bound version has none when the listing is empty', async () => {
    serve('commands', []);

    render(<Listing kind="commands" />);

    expect(await screen.findByText('No commands in the bound version.')).toBeInTheDocument();
  });

  it('offers no category filter outside skills', async () => {
    serve('agents', [entry('backend-developer')]);

    render(<Listing kind="agents" />);

    await screen.findByText('backend-developer');
    expect(screen.queryByLabelText('Filter agents by category')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Filter skills by category')).not.toBeInTheDocument();
  });
});

describe('Catalog listing — featured commands (ADR-0030)', () => {
  const featuredEntry = (name: string): CatalogEntry => ({ ...entry(name), featured: true });
  const five = ['plan', 'fix', 'review', 'commit', 'pr'].map(featuredEntry);

  it('shows only the featured commands by default, with a toggle naming the full count', async () => {
    serve('commands', [entry('adr'), ...five, entry('version')]);
    render(<Listing kind="commands" />);

    await screen.findByText('plan');
    expect(names(document.body)).toEqual(['commit', 'fix', 'plan', 'pr', 'review']);
    expect(screen.getByRole('button', { name: 'Show all commands (7)' })).toBeInTheDocument();
  });

  it('shows every command after the toggle, and goes back', async () => {
    serve('commands', [entry('adr'), ...five, entry('version')]);
    render(<Listing kind="commands" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Show all commands (7)' }));
    expect(names(document.body)).toHaveLength(7);
    fireEvent.click(screen.getByRole('button', { name: 'Show featured commands (5)' }));
    expect(names(document.body)).toHaveLength(5);
  });

  it('falls back to every command, with no toggle, when none is marked featured', async () => {
    serve('commands', [entry('version'), entry('adr'), entry('plan')]);
    render(<Listing kind="commands" />);

    await screen.findByText('adr');
    expect(names(document.body)).toEqual(['adr', 'plan', 'version']);
    expect(screen.queryByRole('button', { name: /Show (all|featured) commands/ })).not.toBeInTheDocument();
  });

  it('does not narrow agents', async () => {
    serve('agents', [{ ...entry('qa-specialist'), featured: true }, entry('backend-developer')]);
    render(<Listing kind="agents" />);

    await screen.findByText('qa-specialist');
    expect(names(document.body)).toEqual(['backend-developer', 'qa-specialist']);
  });
});
