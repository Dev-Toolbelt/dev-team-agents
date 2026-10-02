/**
 * Write `release/SHA256SUMS.txt` for the installers `dist:all` produced.
 *
 * The direct-download beta (ADR-0027) ships unsigned installers, so a published digest
 * is the only thing a user can check a download against. It proves integrity, not
 * authorship: whoever can replace the installer on the release can replace this file
 * too.
 *
 * The format is GNU `sha256sum`'s — `<hex digest>␠␠<file name>`, one per line — so the
 * file verifies as-is with `shasum -a 256 -c SHA256SUMS.txt` on macOS and
 * `sha256sum -c SHA256SUMS.txt` elsewhere. Hashing uses `node:crypto` rather than either
 * tool, so the output does not depend on which one the build host has, and streams each
 * installer so a several-hundred-MB file is never held in memory whole.
 */
import { createHash } from 'node:crypto';
import { createReadStream, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pipeline } from 'node:stream/promises';

import { readRelease, releaseDir, requireInstallers, runScript } from './release-artifacts.mjs';

async function sha256(path) {
  const hash = createHash('sha256');
  await pipeline(createReadStream(path), hash);
  return hash.digest('hex');
}

await runScript('checksums', async () => {
  const { installers } = readRelease();
  requireInstallers(installers);

  let lines = '';
  for (const name of installers) lines += `${await sha256(join(releaseDir, name))}  ${name}\n`;

  const output = join(releaseDir, 'SHA256SUMS.txt');
  writeFileSync(output, lines);
  process.stdout.write(`checksums: ${output}\n`);
});
