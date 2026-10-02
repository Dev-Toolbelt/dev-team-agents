/**
 * The installers `dist:all` publishes, named the way `electron-builder.yml` names them.
 *
 * One list for every script that consumes the release: `zip-release.mjs` bundles these
 * files and `checksums.mjs` hashes them. Two copies would drift the first time an
 * architecture is added, and the zip and the checksum file would then disagree about
 * what a release contains.
 *
 * Paths are relative to the working directory, which is `app/` when run from npm.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

export const releaseDir = 'release';

export function readRelease() {
  const { productName, version } = JSON.parse(readFileSync('package.json', 'utf8'));
  const installers = [
    `${productName}-${version}.dmg`,
    `${productName}-Setup-${version}.exe`,
    `${productName}-Setup-${version}-x64.exe`,
    `${productName}-Setup-${version}-arm64.exe`,
  ];
  return { productName, version, installers };
}

/** Throws naming every missing installer, so no script works from a partial set that looks complete. */
export function requireInstallers(installers) {
  const missing = installers.filter((name) => !existsSync(join(releaseDir, name)));
  if (missing.length > 0) throw new Error(`missing in ${releaseDir}/: ${missing.join(', ')}`);
}

/** Runs a script body, turning a thrown error into `<script>: <message>` and exit 1. */
export async function runScript(scriptName, body) {
  try {
    await body();
  } catch (error) {
    process.stderr.write(`${scriptName}: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  }
}
