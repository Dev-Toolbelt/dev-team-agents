/**
 * The native About panel's text. It replaced an in-app tab as the answer to "which
 * `devteam` is this?" (ADR-0011), so each state of the resolution must say something true.
 */
import { describe, expect, it } from 'vitest';

import { DISPLAY_NAME, aboutCredits, type AboutFacts } from '../src/main/about.js';

const facts: AboutFacts = {
  appVersion: '0.0.0',
  electronVersion: '39.8.10',
  packaged: false,
  codeSigned: false,
  mutatingCommandsRun: ['doctor', 'bind'],
};

describe('aboutCredits', () => {
  it('names the CLI, its source, the store, the contract, the write actions and the build', () => {
    const text = aboutCredits(facts, {
      found: true,
      cli: { path: '/usr/local/bin/devteam', source: 'homebrew', storeVersion: '2.48.0', jsonContract: 1 },
    } as never);
    expect(text).toContain('devteam CLI: /usr/local/bin/devteam (via Homebrew)');
    expect(text).toContain('Store version: 2.48.0');
    expect(text).toContain('JSON contract: 1');
    expect(text).toContain('Write actions: doctor, bind');
    expect(text).toContain('Electron 39.8.10 · development · unsigned build');
  });

  it('says the CLI was not found rather than showing an empty line', () => {
    expect(aboutCredits(facts, { found: false } as never)).toContain('devteam CLI: not found on this host');
  });

  it('says the CLI has not been resolved yet before the first answer', () => {
    expect(aboutCredits(facts, null)).toContain('not resolved yet');
  });

  it('uses the product name users read, not the package name', () => {
    expect(DISPLAY_NAME).toBe('Dev Team Agents');
  });
});
