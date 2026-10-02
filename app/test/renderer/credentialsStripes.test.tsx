// @vitest-environment jsdom
/** The credentials editor alternates its rows (odd/even), per list and over what a search shows. */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CredentialsEditor } from '../../src/renderer/credentials/CredentialsEditor.js';

afterEach(cleanup);

const DOC = {
  app: { url: 'https://app.test', region: 'us' },
  gcp: { project: 'p' },
  manager: { user: 'm' },
  websites: { production: ['a', 'b'], staging: ['c'] },
};

function stripes(list: HTMLElement): (string | null)[] {
  return Array.from(list.children).map((li) => li.getAttribute('data-stripe'));
}

function renderEditor() {
  render(<CredentialsEditor doc={DOC} disabled={false} onEdit={vi.fn()} onProblem={vi.fn()} />);
  return userEvent.setup();
}

describe('CredentialsEditor — odd/even rows', () => {
  it('alternates the top-level groups, tinting only the odd ones', () => {
    renderEditor();
    const top = screen.getByRole('region', { name: 'app' }).closest('ul')!;
    expect(stripes(top)).toEqual(['even', 'odd', 'even', 'odd']);
    expect(screen.getByRole('region', { name: 'gcp' })).toHaveClass('bg-muted/40');
    expect(screen.getByRole('region', { name: 'app' })).not.toHaveClass('bg-muted/40');
  });

  it('starts over inside each group, for nested groups and fields alike', () => {
    renderEditor();
    const nested = screen.getByRole('region', { name: 'production' }).closest('ul')!;
    expect(stripes(nested)).toEqual(['even', 'odd']);
    const fields = screen.getByText('region').closest('ul')!;
    expect(stripes(fields)).toEqual(['even', 'odd']);
    expect(screen.getByText('region').closest('li')!.firstElementChild).toHaveClass('bg-muted/40');
  });

  it('counts only the rows a search leaves visible', async () => {
    const user = renderEditor();
    await user.type(screen.getByRole('searchbox', { name: 'Search credentials' }), 'm');
    const top = screen.getByRole('region', { name: 'manager' }).closest('ul')!;
    const shown = stripes(top);
    expect(shown[0]).toBe('even');
    expect(shown.every((s, i) => s === (i % 2 === 1 ? 'odd' : 'even'))).toBe(true);
  });
});
