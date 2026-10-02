/**
 * How a resolved `devteam` is actually started.
 *
 * On POSIX the CLI is an executable python script with a shebang, and `spawn` runs it as
 * is. Windows has no shebang: an extensionless `scripts/cli/devteam` cannot be spawned by
 * name at all, so it is launched **through a python interpreter** instead. A real `.exe`
 * (a packaged shim) is spawned directly.
 *
 * Security posture, kept from `resolve.ts` and `invoke.ts`:
 *   - `shell: false` stays; the interpreter is the program, the script is its first argument.
 *   - the interpreter is found only in **absolute** `PATH` entries. A relative entry (`.`)
 *     resolves against the app's working directory, which would let a `python.exe` dropped
 *     next to wherever the app was started be run instead of the user's.
 *   - only `py.exe` (with `-3`) and `python.exe` are considered, never `.cmd`/`.bat`: Node
 *     refuses those without a shell (CVE-2024-27980), and turning the shell on would hand
 *     it the CLI's argv, which is the vulnerability.
 *
 * Imports nothing from `electron`.
 */

import { statSync } from 'node:fs';
import { posix, win32 } from 'node:path';

export interface Launch {
  readonly command: string;
  readonly args: readonly string[];
}

type Env = Readonly<Record<string, string | undefined>>;

/**
 * `process.env` is case-insensitive on Windows (`Path`, `PATH`); a plain object is not.
 * Looks a key up the way the platform does.
 */
export function lookupEnv(env: Env, key: string, platform: NodeJS.Platform = process.platform): string | undefined {
  const exact = env[key];
  if (exact !== undefined || platform !== 'win32') return exact;
  const wanted = key.toLowerCase();
  for (const [name, value] of Object.entries(env)) {
    if (name.toLowerCase() === wanted) return value;
  }
  return undefined;
}

/**
 * Absolute in the strict sense. On Windows that is a drive letter or a UNC prefix:
 * `\\tools` and `/tools` are rooted but resolve against the *current drive*, which is as
 * dependent on where the app was started as a relative entry is.
 */
export function isAbsoluteEntry(dir: string, platform: NodeJS.Platform = process.platform): boolean {
  if (platform === 'win32') return /^(?:[A-Za-z]:[\\/]|\\\\[^\\/]|\/\/[^\\/])/.test(dir);
  return posix.isAbsolute(dir);
}

function isFile(path: string): boolean {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

/**
 * The python interpreter to run a script with, from absolute `PATH` entries only.
 * `py.exe` first, because it honours the user's installed-version choice (`-3`); then
 * `python.exe`. `null` when there is none.
 */
export function findWindowsPython(
  env: Env,
  platform: NodeJS.Platform = process.platform,
  exists: (path: string) => boolean = isFile,
): Launch | null {
  const path = platform === 'win32' ? win32 : posix;
  const pathValue = lookupEnv(env, 'PATH', platform) ?? '';
  const dirs = pathValue
    .split(platform === 'win32' ? ';' : ':')
    .map((dir) => dir.trim().replace(/^"(.*)"$/, '$1'))
    .filter((dir) => isAbsoluteEntry(dir, platform));
  for (const [name, args] of [
    ['py.exe', ['-3']],
    ['python.exe', []],
  ] as const) {
    for (const dir of dirs) {
      const candidate = path.join(dir, name);
      if (exists(candidate)) return { command: candidate, args };
    }
  }
  return null;
}

/**
 * What to hand to `spawn` for `binary` and `args`. Unchanged everywhere except a Windows
 * non-`.exe` target with a python interpreter available, which becomes
 * `<interpreter> [-3] <binary> <args…>`. With no interpreter the binary is returned as is,
 * so the spawn fails with its own, honest error rather than one invented here.
 */
export function launchCommand(
  binary: string,
  args: readonly string[],
  env: Env = process.env,
  platform: NodeJS.Platform = process.platform,
  exists?: (path: string) => boolean,
): Launch {
  if (platform !== 'win32' || binary.toLowerCase().endsWith('.exe')) return { command: binary, args };
  const python = findWindowsPython(env, platform, exists);
  if (python === null) return { command: binary, args };
  return { command: python.command, args: [...python.args, binary, ...args] };
}
