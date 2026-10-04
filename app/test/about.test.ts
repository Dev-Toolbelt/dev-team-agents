/**
 * The native About panel's text. It replaced an in-app tab as the answer to "which
 * `devteam` is this?" (ADR-0011), so each state of the resolution must say something true.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { APP_ID, DISPLAY_NAME, aboutCredits, type AboutFacts } from '../src/main/about.js';

const facts: AboutFacts = {
  appVersion: '0.0.0',
  electronVersion: '44.5.1',
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
    expect(text).toContain('Electron 44.5.1 · development · unsigned build');
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

describe('APP_ID', () => {
  it('is the appId electron-builder stamps on the packaged build', () => {
    const config = readFileSync(fileURLToPath(new URL('../electron-builder.yml', import.meta.url)), 'utf8');
    expect(config).toMatch(new RegExp(`^appId: ${APP_ID.replace(/\./g, '\\.')}$`, 'm'));
  });
});
