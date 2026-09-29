/**
 * Finding the one `devteam` on this host.
 *
 * **Nothing is bundled.** ADR-0011 names the failure a bundled CLI causes — "an older
 * CLI can end up writing a newer store, which is the exact case `devteam compat`
 * exists to detect and the one nothing was preventing" — and a copy shipped inside the
 * `.app` is that older CLI by construction, because the app and the framework update on
 * different cadences. So there is no fallback binary here, and a host with no `devteam`
 * is a state the UI reports rather than one this module papers over.
 *
 * Resolution order, first hit wins:
 *
 *   1. **an explicit path the user configured** — `DEVTEAM_CLI_PATH` in the
 *      environment, or `cliPath` in the app's own settings file. The user overriding
 *      the search must beat the search, or the override is not one. This is also the
 *      seam a contributor uses to point the app at `scripts/cli/devteam` in a checkout.
 *   2. **`PATH`** — where the Homebrew formula's symlink, a pipx shim, or a
 *      hand-installed CLI all appear. Preferring `PATH` over a hardcoded Homebrew
 *      location means the app agrees with what the user's own terminal runs, which is
 *      the only way "which CLI did it use?" has one answer.
 *   3. **Known per-platform channel locations** — Homebrew's `bin` on macOS and Linux
 *      (`$HOMEBREW_PREFIX/bin`, then `/opt/homebrew/bin` for Apple silicon and
 *      `/usr/local/bin` for Intel), winget's shim directory on Windows. Reached when the
 *      app was launched from Finder or the Start menu, neither of which inherits a login
 *      shell's `PATH`: the cask `depends_on formula: "devteam"`, so on a cask install the
 *      formula's binary is there even when `PATH` cannot see it.
 *
 *      **This step is not macOS-only.** It was guarded by `platform !== 'win32'`, so
 *      winget's shim directory was never searched — and ADR-0015's Risks table says the
 *      resolution order "is the *only* thing standing between the app and no CLI" on
 *      Windows. `executableNames` already handled `.exe`/`.cmd`/`.bat`; the gap was a
 *      directory list, and it is `knownBinDirs` below.
 *
 * A candidate is not accepted for existing. It is **run** — `devteam version --json` —
 * and accepted only if it answers with a conforming document carrying a `compat` block.
 * A file called `devteam` that is some other program would otherwise be resolved and
 * then fail, confusingly, on every screen.
 *
 * **On the environment variable's name.** ADR-0015 § 5 names step 2 `DEVTEAM_CLI` and puts
 * it below the settings-file path; this module reads `DEVTEAM_CLI_PATH` and tries it first.
 * The ADR's own amendment records both divergences and keeps them: the value is a
 * filesystem path, which `DEVTEAM_CLI` does not say and `DEVTEAM_HOME` sets the precedent
 * for; and within tier 1 an environment variable is the narrower, more deliberate act than
 * a settings key, so it wins. The remedy text, the settings docs and this seam all use the
 * one name — do not add a second alias.
 */

import { constants } from 'node:fs';
import { access, stat } from 'node:fs/promises';
import { delimiter, join } from 'node:path';

import { invokeDevteam } from './invoke.js';
import { ranAndAnswered } from './contract.js';

/** Probe budget. A `version` call touches no locks; slow means wrong, not busy. */
const PROBE_TIMEOUT_MS = 10_000;

export type ResolutionSource = 'configured' | 'path' | 'homebrew' | 'winget';

export interface ResolvedCli {
  readonly path: string;
  readonly source: ResolutionSource;
  /** How the source is described to the user, e.g. `DEVTEAM_CLI_PATH`. */
  readonly sourceDetail: string;
  /** `current` from `devteam version --json`; null when no version is installed. */
  readonly storeVersion: string | null;
  /** The `compat` block the probe returned, so the UI can show it without a second call. */
  readonly compat: {
    readonly jsonContract: number | null;
    readonly minAppVersion: string | null;
    readonly storeSchemas: Readonly<Record<string, number>>;
  };
}

export interface RejectedCandidate {
  readonly path: string;
  readonly source: ResolutionSource;
  readonly reason: string;
}

export type Resolution =
  | { readonly found: true; readonly cli: ResolvedCli; readonly rejected: readonly RejectedCandidate[] }
  | {
      readonly found: false;
      readonly rejected: readonly RejectedCandidate[];
      /** Where the search looked, in order, for a message that names them. */
      readonly searched: readonly string[];
      readonly remedy: readonly string[];
    };

export interface ResolveOptions {
  /** `cliPath` from the app's settings file, when the user set one. */
  readonly configuredPath?: string | undefined;
  readonly env?: Readonly<Record<string, string | undefined>>;
  readonly platform?: NodeJS.Platform;
  /**
   * Step 3's directories, replacing the platform-derived ones.
   *
   * A seam for tests, and a real one. `knownBinDirs` returns absolute machine paths
   * (`/opt/homebrew/bin`, `%LOCALAPPDATA%\…`), so a test that asserted `found === false`
   * was asserting something about the machine it ran on: green here, red on a
   * contributor's laptop with a Homebrew-installed `devteam`, with a message that names
   * neither cause. Passing `[]` — or a temp directory — makes such a test depend only on
   * what it created.
   */
  readonly knownLocations?: readonly string[];
}

/** Candidate executable names. The CLI is a python script behind a symlink on unix. */
function executableNames(platform: NodeJS.Platform): string[] {
  // On Windows the packaging shape is still undecided (ADR-0011's winget row is a
  // placeholder), so every plausible shim name is tried rather than one being assumed.
  return platform === 'win32' ? ['devteam.exe', 'devteam.cmd', 'devteam.bat', 'devteam'] : ['devteam'];
}

/** Which channel step 3's directories belong to, for the badge that names it. */
export function knownLocationSource(platform: NodeJS.Platform): ResolutionSource {
  return platform === 'win32' ? 'winget' : 'homebrew';
}

/**
 * Step 3's directories for this platform: the channel locations a GUI launch cannot see.
 *
 * Windows gets winget's two shim directories. `Microsoft\WinGet\Links` is where winget
 * puts the shim for a portable package; `Microsoft\WindowsApps` is the execution-alias
 * directory an MSIX install uses. Both live under `%LOCALAPPDATA%`, so both are skipped
 * when that variable is absent rather than guessed at from a drive letter. No directory is
 * invented for an `InstallerType: exe` install: ADR-0011 records that shape as "a
 * placeholder, not a decision", and a guessed path would read as one that was decided.
 */
export function knownBinDirs(
  platform: NodeJS.Platform,
  env: Readonly<Record<string, string | undefined>>,
): string[] {
  const dirs: string[] = [];
  const push = (dir: string): void => {
    if (!dirs.includes(dir)) dirs.push(dir);
  };

  if (platform === 'win32') {
    const localAppData = env['LOCALAPPDATA'];
    if (typeof localAppData === 'string' && localAppData !== '') {
      push(join(localAppData, 'Microsoft', 'WinGet', 'Links'));
      push(join(localAppData, 'Microsoft', 'WindowsApps'));
    }
    return dirs;
  }

  const prefix = env['HOMEBREW_PREFIX'];
  if (typeof prefix === 'string' && prefix !== '') push(join(prefix, 'bin'));
  push('/opt/homebrew/bin');
  push('/usr/local/bin');
  return dirs;
}

async function isExecutableFile(candidate: string): Promise<string | null> {
  try {
    const info = await stat(candidate); // follows symlinks, which is what we want
    if (!info.isFile()) return `not a regular file`;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === 'ENOENT' ? 'does not exist' : `unreadable: ${String(error)}`;
  }
  try {
    await access(candidate, constants.X_OK);
  } catch {
    return 'exists but is not executable';
  }
  return null;
}

/**
 * Does this binary answer as our CLI? Returns the accepted record, or why not.
 *
 * `version` is the probe rather than `compat` because `version` is the call ADR-0011
 * has a client make first and it carries the same `compat` block, so one probe both
 * identifies the binary and fills the header the UI shows.
 */
async function probe(path: string, source: ResolutionSource, sourceDetail: string): Promise<ResolvedCli | string> {
  const result = await invokeDevteam({ binary: path, args: ['version'], timeoutMs: PROBE_TIMEOUT_MS });
  if (!ranAndAnswered(result)) {
    return result.outcome === 'timeout'
      ? `did not answer \`version --json\` within ${result.timeoutMs} ms`
      : result.outcome === 'unavailable'
        ? result.detail
        : `answered \`version --json\` with something other than one JSON document (${result.reason})`;
  }
  if (result.document.kind === 'error') {
    return `\`version --json\` failed: ${result.document.error}`;
  }
  const body = result.document.body;
  const compat = body['compat'];
  if (compat === null || typeof compat !== 'object' || Array.isArray(compat)) {
    // The discriminator. `compat` in `version --json` is what makes this a devteam
    // rather than an unrelated program that happens to print JSON.
    return 'answered `version --json` without a `compat` block, so it is not a devteam CLI';
  }
  const block = compat as Record<string, unknown>;
  const schemas = block['store_schemas'];
  return {
    path,
    source,
    sourceDetail,
    storeVersion: typeof body['current'] === 'string' ? body['current'] : null,
    compat: {
      jsonContract: typeof block['json_contract'] === 'number' ? block['json_contract'] : null,
      minAppVersion: typeof block['min_app_version'] === 'string' ? block['min_app_version'] : null,
      storeSchemas: isNumberMap(schemas) ? schemas : {},
    },
  };
}

function isNumberMap(value: unknown): value is Record<string, number> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  return Object.values(value as Record<string, unknown>).every((v) => typeof v === 'number');
}

export async function resolveDevteam(options: ResolveOptions = {}): Promise<Resolution> {
  const env = options.env ?? process.env;
  const platform = options.platform ?? process.platform;
  const names = executableNames(platform);

  const candidates: { path: string; source: ResolutionSource; detail: string }[] = [];

  // 1 — explicit configuration wins over everything.
  const fromEnv = env['DEVTEAM_CLI_PATH'];
  if (typeof fromEnv === 'string' && fromEnv.trim() !== '') {
    candidates.push({ path: fromEnv.trim(), source: 'configured', detail: 'DEVTEAM_CLI_PATH' });
  }
  if (options.configuredPath !== undefined && options.configuredPath.trim() !== '') {
    candidates.push({
      path: options.configuredPath.trim(),
      source: 'configured',
      detail: 'cliPath in the app settings file',
    });
  }

  // 2 — PATH, in the order the shell would search it.
  const pathValue = env['PATH'] ?? '';
  for (const dir of pathValue.split(delimiter)) {
    if (dir === '') continue;
    for (const name of names) {
      candidates.push({ path: join(dir, name), source: 'path', detail: `PATH entry ${dir}` });
    }
  }

  // 3 — the channel's own location, for a Finder or Start-menu launch whose PATH cannot
  // see it. Every platform, not only the ones with brew.
  const knownSource = knownLocationSource(platform);
  const knownLabel = knownSource === 'winget' ? 'winget shim directory' : 'Homebrew bin';
  for (const dir of options.knownLocations ?? knownBinDirs(platform, env)) {
    for (const name of names) {
      candidates.push({ path: join(dir, name), source: knownSource, detail: `${knownLabel} ${dir}` });
    }
  }

  const rejected: RejectedCandidate[] = [];
  const searched: string[] = [];
  const seen = new Set<string>();

  for (const candidate of candidates) {
    if (seen.has(candidate.path)) continue;
    seen.add(candidate.path);
    searched.push(candidate.path);

    const fileProblem = await isExecutableFile(candidate.path);
    if (fileProblem !== null) {
      // "does not exist" for every PATH entry is the normal case and would drown the
      // report, so only a file that is there and unusable is worth recording.
      if (fileProblem !== 'does not exist') {
        rejected.push({ path: candidate.path, source: candidate.source, reason: fileProblem });
      }
      continue;
    }
    const outcome = await probe(candidate.path, candidate.source, candidate.detail);
    if (typeof outcome === 'string') {
      rejected.push({ path: candidate.path, source: candidate.source, reason: outcome });
      continue;
    }
    return { found: true, cli: outcome, rejected };
  }

  return {
    found: false,
    rejected,
    searched,
    remedy: [
      'Install the CLI: `brew install dev-toolbelt/devteam/devteam` (macOS).',
      'Or set DEVTEAM_CLI_PATH to the `devteam` executable, e.g. a checkout\'s scripts/cli/devteam.',
      'Or set `cliPath` in the app settings file to the same path.',
      'The app deliberately ships no copy of the CLI: a bundled, older CLI writing a newer store is the failure ADR-0011 forbids.',
    ],
  };
}
