/**
 * Bundle the installers `dist:all` produced into one zip, for handing a test build to
 * another machine as a single file.
 *
 * Only the four installers go in — the `.blockmap` files and the `*-unpacked` /
 * `mac-universal*` directories are build by-products nobody installs from. A missing
 * installer fails the script instead of zipping a partial set that looks complete.
 *
 * Uses the system `zip`, which `dist:all` can rely on: it already needs a macOS host to
 * build the `.dmg`.
 */
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const { productName, version } = JSON.parse(readFileSync('package.json', 'utf8'));
const releaseDir = 'release';

const installers = [
  `${productName}-${version}.dmg`,
  `${productName}-Setup-${version}.exe`,
  `${productName}-Setup-${version}-x64.exe`,
  `${productName}-Setup-${version}-arm64.exe`,
];

const missing = installers.filter((name) => !existsSync(join(releaseDir, name)));
if (missing.length > 0) {
  process.stderr.write(`zip-release: missing in ${releaseDir}/: ${missing.join(', ')}\n`);
  process.exit(1);
}

const archive = `${productName}-${version}-unsigned.zip`;
rmSync(join(releaseDir, archive), { force: true });

const result = spawnSync('zip', ['-q', archive, ...installers], { cwd: releaseDir, stdio: 'inherit' });
if (result.error) {
  process.stderr.write(`zip-release: could not run zip: ${result.error.message}\n`);
  process.exit(1);
}
if (result.status !== 0) process.exit(result.status ?? 1);

process.stdout.write(`zip-release: ${join(releaseDir, archive)}\n`);
