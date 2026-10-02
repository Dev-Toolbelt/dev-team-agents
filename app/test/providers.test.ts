/**
 * The app's provider list must equal the CLI's. `ALL_PROVIDERS` in
 * `scripts/lib/devteam/providers.py` is the source of truth; every list in the app derives
 * from `src/shared/providers.ts`, and this test is what notices when the two diverge —
 * and when a screen goes back to hardcoding its own.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { PROVIDERS } from '../src/shared/providers.js';

const APP = fileURLToPath(new URL('..', import.meta.url));
const PROVIDERS_PY = join(APP, '..', 'scripts', 'lib', 'devteam', 'providers.py');

function cliProviders(): string[] {
  const text = readFileSync(PROVIDERS_PY, 'utf8');
  const match = /^ALL_PROVIDERS\s*(?::[^=]+)?=\s*\(([^)]*)\)/m.exec(text);
  if (match === null) throw new Error('ALL_PROVIDERS not found in providers.py');
  return [...(match[1] as string).matchAll(/["']([a-z0-9_-]+)["']/g)].map((m) => m[1] as string);
}

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return sources(full);
    return /\.(ts|tsx)$/.test(name) ? [full] : [];
  });
}

describe('providers', () => {
  it('the app list equals ALL_PROVIDERS, in order', () => {
    expect([...PROVIDERS]).toEqual(cliProviders());
  });

  it('no other source file hardcodes the provider list', () => {
    const offenders = sources(join(APP, 'src')).filter((file) => {
      if (file.endsWith(join('shared', 'providers.ts'))) return false;
      const text = readFileSync(file, 'utf8');
      // Three of the provider names inside one array literal or union is a copy of the list.
      return /\[\s*['"](?:claude|opencode|codex)['"]\s*,\s*['"](?:claude|opencode|codex)['"]\s*,\s*['"](?:claude|opencode|codex)['"]/.test(text)
        || /['"](?:claude|opencode|codex)['"]\s*\|\s*['"](?:claude|opencode|codex)['"]\s*\|\s*['"](?:claude|opencode|codex)['"]/.test(text);
    });
    expect(offenders).toEqual([]);
  });
});
