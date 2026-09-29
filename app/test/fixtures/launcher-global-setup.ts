/**
 * Vitest `globalSetup`: on Windows only, compiles `launcher.c` once per test run into
 * a temp directory, so `resolve.test.ts`, `handshake.test.ts`, `operations.test.ts`
 * and `ipc.test.ts` can spawn a real PE in place of a POSIX shebang fixture. The
 * result is written to `launcher-manifest.ts`'s fixed path; every test file reads it
 * back independently rather than depending on an env var surviving into the worker
 * pool (see that module's header).
 *
 * This step must never fail the run. A missing compiler or a failed compile is
 * recorded in the manifest and printed once; the affected tests then `skipIf`
 * themselves with that same reason. A fixture toolchain problem must never look like
 * a product failure — see this task's own instructions on that point.
 */

import { rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { compileLauncher, makeBuildDir, probeCompiler } from './launcher-build.js';
import { LAUNCHER_MANIFEST_PATH, type LauncherManifest } from './launcher-manifest.js';

const LAUNCHER_SRC = fileURLToPath(new URL('./launcher.c', import.meta.url));
const FAKE_DEVTEAM = fileURLToPath(new URL('./fake-devteam.mjs', import.meta.url));
const FAKE_DEVTEAM_WRITE = fileURLToPath(new URL('./fake-devteam-write.mjs', import.meta.url));

export default async function setup(): Promise<() => Promise<void>> {
  if (process.platform !== 'win32') return async () => {};

  const buildDir = await makeBuildDir();
  const compiler = probeCompiler();

  function build(script: string, outName: string): { path: string | null; reason: string | null } {
    if (compiler === null) return { path: null, reason: 'no C compiler found on PATH (tried cc, gcc, clang, cl)' };
    const out = join(buildDir, outName);
    const failure = compileLauncher(compiler, LAUNCHER_SRC, out, process.execPath, script);
    return failure === null ? { path: out, reason: null } : { path: null, reason: failure };
  }

  const fakeDevteam = build(FAKE_DEVTEAM, 'fake-devteam.exe');
  const fakeDevteamWrite = build(FAKE_DEVTEAM_WRITE, 'fake-devteam-write.exe');

  const manifest: LauncherManifest = { compiler: compiler?.command ?? null, fakeDevteam, fakeDevteamWrite };
  await writeFile(LAUNCHER_MANIFEST_PATH, JSON.stringify(manifest, null, 2), 'utf8');

  if (compiler === null) {
    console.warn(
      '[windows launcher] no C compiler found on PATH (tried cc, gcc, clang, cl) — ' +
        'the spawn-dependent Windows tests stay skipped, not failed.',
    );
  } else if (fakeDevteam.path === null || fakeDevteamWrite.path === null) {
    console.warn(
      `[windows launcher] found ${compiler.command} but compilation failed — ` +
        `the spawn-dependent Windows tests stay skipped, not failed. ` +
        `${fakeDevteam.reason ?? fakeDevteamWrite.reason ?? ''}`,
    );
  } else {
    console.log(`[windows launcher] built with ${compiler.command} — the spawn-dependent Windows tests will run.`);
  }

  return async () => {
    await rm(buildDir, { recursive: true, force: true });
  };
}
