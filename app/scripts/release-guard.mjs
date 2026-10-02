/**
 * Refuse a publishable build from anything but a tagged, clean commit (ADR-0027 § 2).
 *
 * `dist:beta` runs this before `dist:all`. The tag must be exactly `app-v<version>` from
 * `package.json` — never `v<version>`, which `.github/workflows/release.yml` treats as a
 * framework release — and the working tree must have no changes, tracked or untracked,
 * so the digests in `SHA256SUMS.txt` describe a commit someone else can check out.
 * `dist:all` stays unguarded: a test build from a dirty tree is normal.
 */
import { spawnSync } from 'node:child_process';

import { readRelease, runScript } from './release-artifacts.mjs';

function git(...args) {
  const result = spawnSync('git', args, { encoding: 'utf8' });
  if (result.error) throw new Error(`could not run git: ${result.error.message}`);
  return { status: result.status, stdout: result.stdout.trim() };
}

await runScript('release-guard', () => {
  const { version } = readRelease();
  const expected = `app-v${version}`;

  const tags = git('tag', '--points-at', 'HEAD');
  if (tags.status !== 0) throw new Error('not inside a git repository');
  if (!tags.stdout.split('\n').includes(expected)) {
    throw new Error(`HEAD is not tagged ${expected} (package.json version ${version}); tag the commit first`);
  }

  const status = git('status', '--porcelain');
  if (status.stdout !== '') throw new Error('the working tree has changes; commit or stash them before a release build');

  process.stdout.write(`release-guard: building ${expected}\n`);
});
