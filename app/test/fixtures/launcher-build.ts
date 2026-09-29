/**
 * Compiles `launcher.c` from source. Used only by `launcher-global-setup.ts` — a test
 * file never calls this directly, it only reads the result back through
 * `launcher-manifest.ts`.
 *
 * Nothing here runs off Windows: `launcher.c` includes `<windows.h>` unconditionally,
 * so there is nothing to probe or compile elsewhere, and the one caller checks
 * `process.platform` before touching this module regardless.
 */

import { spawnSync } from 'node:child_process';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export interface Compiler {
  readonly command: string;
  readonly kind: 'gcc-like' | 'msvc';
}

/**
 * `cc`, `gcc`, `clang`, then MSVC's `cl.exe` — in that order, because `windows-latest`
 * carries Visual Studio, so `cl` is the most certain hit, but reaching it usually means
 * having already run `vcvarsall.bat` for the INCLUDE/LIB environment it needs, which a
 * plain `shell: bash` CI step has not done. `cc`/`gcc`/`clang` from a MinGW or LLVM
 * toolchain already on PATH need no such setup, so they are tried first. Which one (if
 * any) actually wins on the runner cannot be verified from macOS — see
 * `launcher-global-setup.ts`'s report.
 */
const CANDIDATES: readonly Compiler[] = [
  { command: 'cc', kind: 'gcc-like' },
  { command: 'gcc', kind: 'gcc-like' },
  { command: 'clang', kind: 'gcc-like' },
  { command: 'cl', kind: 'msvc' },
];

function probeOne(compiler: Compiler): boolean {
  // gcc-like: `--version` exits 0 for a real compiler. `cl` has no such flag — invoked
  // bare it prints its banner to stderr and exits non-zero, which still proves the
  // binary exists and ran; only `spawnSync`'s own `error` (e.g. ENOENT) means "not
  // found" for either kind.
  const probe = spawnSync(compiler.command, compiler.kind === 'gcc-like' ? ['--version'] : [], {
    stdio: 'ignore',
    shell: false,
    windowsHide: true,
  });
  return probe.error === undefined;
}

/** First working compiler on PATH, in the documented order, or null. */
export function probeCompiler(): Compiler | null {
  for (const candidate of CANDIDATES) {
    if (probeOne(candidate)) return candidate;
  }
  return null;
}

function cDefine(name: string, value: string): string {
  const escaped = value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  return `-D${name}="${escaped}"`;
}

/**
 * Compiles `sourcePath` to `outExe`, baking `nodePath` and `scriptPath` in as the two
 * defines `launcher.c` requires. Returns `null` on success, or the compiler's own
 * output (trimmed) on failure. Never throws — a broken toolchain is data for the
 * caller to degrade on, not a reason to crash the test run.
 */
export function compileLauncher(
  compiler: Compiler,
  sourcePath: string,
  outExe: string,
  nodePath: string,
  scriptPath: string,
): string | null {
  const defines = [cDefine('NODE_PATH', nodePath), cDefine('SCRIPT_PATH', scriptPath)];
  const args =
    compiler.kind === 'msvc'
      ? ['/nologo', '/O2', ...defines, sourcePath, `/Fe:${outExe}`]
      : ['-O2', ...defines, '-o', outExe, sourcePath];
  const result = spawnSync(compiler.command, args, { encoding: 'utf8', shell: false, windowsHide: true });
  if (result.error) return String(result.error);
  if (result.status !== 0) return (result.stderr || result.stdout || `exit code ${String(result.status)}`).trim();
  return null;
}

export async function makeBuildDir(): Promise<string> {
  return mkdtemp(join(tmpdir(), 'devteam-app-launcher-'));
}
