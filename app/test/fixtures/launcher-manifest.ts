/**
 * Where `launcher-global-setup.ts` records what it built, and how test files read it
 * back.
 *
 * A fixed path under the OS temp dir, not an env var: Vitest's worker pool does not
 * make it a promise that a `process.env` mutation made inside `globalSetup` reaches
 * the test files it then runs (the `threads` and `forks` pools differ, and neither is
 * documented behaviour this suite wants to depend on) — a file at a name every process
 * can independently compute has no handoff to get wrong.
 */

import { existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export const LAUNCHER_MANIFEST_PATH = join(tmpdir(), 'devteam-app-test-launcher-manifest.json');

export interface LauncherBuildOutcome {
  readonly path: string | null;
  readonly reason: string | null;
}

export interface LauncherManifest {
  readonly compiler: string | null;
  readonly fakeDevteam: LauncherBuildOutcome;
  readonly fakeDevteamWrite: LauncherBuildOutcome;
}

/** `null` off Windows, and whenever the manifest is missing or unreadable. */
export function readLauncherManifest(): LauncherManifest | null {
  if (process.platform !== 'win32') return null;
  if (!existsSync(LAUNCHER_MANIFEST_PATH)) return null;
  try {
    return JSON.parse(readFileSync(LAUNCHER_MANIFEST_PATH, 'utf8')) as LauncherManifest;
  } catch {
    return null;
  }
}

/**
 * The binary a test should spawn, and whether that binary can actually answer.
 *
 * Off Windows this is always `posixScript` itself (run via its shebang, as today). On
 * Windows it is the compiled launcher when `launcher-global-setup.ts` built one, and
 * `posixScript` otherwise — a value the caller must never spawn there, but still needs
 * to satisfy a non-nullable `binary: string` on the tests that `skipIf` skips anyway.
 */
export function resolveFixtureBinary(
  posixScript: string,
  outcome: LauncherBuildOutcome | undefined,
): { readonly binary: string; readonly available: boolean } {
  if (process.platform !== 'win32') return { binary: posixScript, available: true };
  const built = outcome?.path ?? null;
  return { binary: built ?? posixScript, available: built !== null };
}
