/**
 * Bundle the installers `dist:all` produced into one zip, for handing a test build to
 * another machine as a single file. Never published: ADR-0027 publishes the installers
 * themselves, next to `SHA256SUMS.txt`, which does not cover this zip.
 *
 * Only the four installers go in — the `.blockmap` files and the `*-unpacked` /
 * `mac-universal*` directories are build by-products nobody installs from. A missing
 * installer fails the script instead of zipping a partial set that looks complete.
 *
 * Uses the system `zip`, which `dist:all` can rely on: it already needs a macOS host to
 * build the `.dmg`.
 */
import { spawnSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import { join } from 'node:path';

import { readRelease, releaseDir, requireInstallers, runScript } from './release-artifacts.mjs';

await runScript('zip-release', () => {
  const { productName, version, installers } = readRelease();
  requireInstallers(installers);

  const archive = `${productName}-${version}-unsigned.zip`;
  rmSync(join(releaseDir, archive), { force: true });

  const result = spawnSync('zip', ['-q', archive, ...installers], { cwd: releaseDir, stdio: 'inherit' });
  if (result.error) throw new Error(`could not run zip: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`zip exited with ${result.status ?? 'a signal'}`);

  process.stdout.write(`zip-release: ${join(releaseDir, archive)}\n`);
});
