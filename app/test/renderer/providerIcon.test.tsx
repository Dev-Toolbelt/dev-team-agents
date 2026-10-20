// @vitest-environment jsdom
/** The provider mark shared by every screen: each known provider has its own logo, and the name is never lost. */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { ProviderIcon, providerChoiceLabel, providerLabel } from '../../src/renderer/providers/ProviderIcon.js';
import { PROVIDERS } from '../../src/shared/providers.js';

afterEach(cleanup);

describe('ProviderIcon', () => {
  it('draws a logo of its own for every provider, named by its label', () => {
    render(
      <>
        {PROVIDERS.map((provider) => (
          <ProviderIcon key={provider} provider={provider} />
        ))}
      </>,
    );
    const sources = PROVIDERS.map((provider) => {
      const mark = screen.getByRole('img', { name: providerLabel(provider) });
      expect(mark.tagName).toBe('IMG');
      return mark.getAttribute('src');
    });
    expect(sources.every((src) => src !== null && src !== '')).toBe(true);
    expect(new Set(sources).size).toBe(PROVIDERS.length);
  });

  it('inverts only the near-black opencode mark in the dark scheme', () => {
    render(
      <>
        <ProviderIcon provider="opencode" />
        <ProviderIcon provider="claude" />
      </>,
    );
    expect(screen.getByRole('img', { name: 'opencode' })).toHaveClass('dark:invert');
    expect(screen.getByRole('img', { name: 'Claude Code' })).not.toHaveClass('dark:invert');
  });

  it('prints the name beside the mark and hides the mark from assistive tech', () => {
    const { container } = render(<ProviderIcon provider="codex" withLabel />);
    expect(screen.getByText('Codex')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(container.querySelector('img')).toHaveAttribute('alt', '');
    expect(container.querySelector('[title]')).toBeNull();
  });

  it('leaves the name to the caller when decorative: empty alt and no tooltip', () => {
    const { container } = render(<ProviderIcon provider="claude" decorative />);
    expect(container.querySelector('img')).toHaveAttribute('alt', '');
    expect(container.querySelector('[title]')).toBeNull();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('hides the fallback glyph too when decorative', () => {
    const { container } = render(<ProviderIcon provider="newtool" decorative />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('draws the larger size on request', () => {
    render(
      <>
        <ProviderIcon provider="claude" />
        <ProviderIcon provider="codex" size="md" />
      </>,
    );
    expect(screen.getByRole('img', { name: 'Claude Code' })).toHaveClass('size-3.5');
    expect(screen.getByRole('img', { name: 'Codex' })).toHaveClass('size-4');
  });

  it('never resolves a provider id through Object.prototype', () => {
    render(<ProviderIcon provider="constructor" />);
    expect(screen.getByRole('img', { name: 'constructor' }).tagName.toLowerCase()).toBe('svg');
    expect(providerLabel('__proto__')).toBe('__proto__');
    expect(providerChoiceLabel('toString')).toBe('toString');
  });

  it.each(PROVIDERS)('spells the %s choice label as a long form of its short name', (provider) => {
    expect(providerChoiceLabel(provider).startsWith(providerLabel(provider))).toBe(true);
  });

  it('falls back to a glyph, named by the raw id, for a provider this build does not know', () => {
    render(<ProviderIcon provider="newtool" />);
    const mark = screen.getByRole('img', { name: 'newtool' });
    expect(mark.tagName.toLowerCase()).toBe('svg');
  });
});
