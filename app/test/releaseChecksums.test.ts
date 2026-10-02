/**
 * The direct-download beta's release scripts (ADR-0027), run as processes against a fake
 * app directory, the way `dist:beta` and `dist:all` run them.
 *
 * `checksums.mjs` is what a user verifies an unsigned installer against, so its output
 * has to be exactly what `shasum -a 256 -c` reads. `release-guard.mjs` is what keeps a
 * publishable build tied to a tagged, clean commit.
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

const scriptPath = (name: string) => fileURLToPath(new URL(`../scripts/${name}`, import.meta.url));
const installers = ['demo-1.2.3.dmg', 'demo-Setup-1.2.3.exe', 'demo-Setup-1.2.3-x64.exe', 'demo-Setup-1.2.3-arm64.exe'];

let dir: string;

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'checksums-'));
  writeFileSync(join(dir, 'package.json'), JSON.stringify({ productName: 'demo', version: '1.2.3' }));
  mkdirSync(join(dir, 'release'));
});

afterEach(() => rmSync(dir, { recursive: true, force: true }));

const run = (name: string) => spawnSync(process.execPath, [scriptPath(name)], { cwd: dir, encoding: 'utf8' });
const git = (...args: string[]) =>
  spawnSync('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false', ...args], {
    cwd: dir,
    encoding: 'utf8',
  });

describe('checksums.mjs', () => {
  it('writes one sha256sum-format line per installer, in installer order', () => {
    for (const name of installers) writeFileSync(join(dir, 'release', name), `payload of ${name}`);

    const result = run('checksums.mjs');

    expect(result.status).toBe(0);
    const expected = installers
      .map((name) => `${createHash('sha256').update(`payload of ${name}`).digest('hex')}  ${name}\n`)
      .join('');
    expect(readFileSync(join(dir, 'release', 'SHA256SUMS.txt'), 'utf8')).toBe(expected);
  });

  it('refuses a partial set and names what is missing', () => {
    writeFileSync(join(dir, 'release', installers[0]!), 'only the dmg');

    const result = run('checksums.mjs');

    expect(result.status).toBe(1);
    expect(result.stderr).toContain('demo-Setup-1.2.3-arm64.exe');
    expect(() => readFileSync(join(dir, 'release', 'SHA256SUMS.txt'))).toThrow();
  });
});

describe('release-guard.mjs', () => {
  beforeEach(() => {
    git('init', '-q');
    git('add', 'package.json');
    git('commit', '-q', '-m', 'release');
  });

  it('passes on a clean commit tagged app-v<version>', () => {
    git('tag', 'app-v1.2.3');

    const result = run('release-guard.mjs');

    expect(result.status).toBe(0);
    expect(result.stdout).toContain('app-v1.2.3');
  });

  it('refuses a commit tagged v<version>, the framework release tag', () => {
    git('tag', 'v1.2.3');

    const result = run('release-guard.mjs');

    expect(result.status).toBe(1);
    expect(result.stderr).toContain('not tagged app-v1.2.3');
  });

  it('refuses a tagged commit with untracked changes', () => {
    git('tag', 'app-v1.2.3');
    writeFileSync(join(dir, 'stray.txt'), 'edit');

    const result = run('release-guard.mjs');

    expect(result.status).toBe(1);
    expect(result.stderr).toContain('working tree has changes');
  });
});
