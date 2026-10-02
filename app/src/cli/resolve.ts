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
import { delimiter, dirname, join, posix as posixPath } from 'node:path';

import { invokeDevteam } from './invoke.js';
import { isAbsoluteEntry, lookupEnv } from './launch.js';
import { ranAndAnswered } from './contract.js';
import type { CliSource, RejectedCli } from '../shared/api.js';

/** Probe budget. A `version` call touches no locks; slow means wrong, not busy. */
const PROBE_TIMEOUT_MS = 10_000;

// `CliSource` and `RejectedCli` are declared once, in `shared/api.ts`, and re-exported
// here under this module's own names so callers of `resolve.ts` need not change. See
// `declaration.ts`'s `Handshake`/`UnsupportedShape` re-export for the same reasoning.
export type ResolutionSource = CliSource;
export type RejectedCandidate = RejectedCli;

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

/**
 * How many candidates were tried under one resolution step. `label` matches the
 * numbered steps in this file's own header comment, so the screen that renders this
 * can name the same three steps the header documents rather than inventing new prose.
 */
export interface SearchedLocation {
  readonly source: ResolutionSource;
  readonly label: string;
  readonly count: number;
}

export type Resolution =
  | { readonly found: true; readonly cli: ResolvedCli; readonly rejected: readonly RejectedCandidate[] }
  | {
      readonly found: false;
      readonly rejected: readonly RejectedCandidate[];
      /** Where the search looked, in order, for a message that names them. */
      readonly searched: readonly string[];
      /**
       * `searched`, grouped by resolution step. ADR-0015 § 5 says the app "shows which
       * locations it tried" — a bare count of `searched.length` does not, because most
       * of that count is `PATH` entries with nothing there, which is the ordinary case
       * and not itself informative. A per-step breakdown (configured path, PATH, this
       * platform's channel location) names the locations without listing every one of
       * dozens of `PATH` directories individually.
       */
      readonly searchedBySource: readonly SearchedLocation[];
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
  // `posixPath.join`, not the platform-bound `join`: this branch's paths are always
  // POSIX (Homebrew never runs on Windows), but the host running this code is not
  // necessarily the platform being asked about — `resolveDevteam`'s own tests probe
  // `knownBinDirs('darwin', …)` from whichever CI runner they happen to execute on.
  // Production never hits this mismatch (it always calls with the true platform, so a
  // real POSIX host already gets POSIX behaviour from the plain `join`), but the plain
  // `join` import resolves to `path.win32.join` on an actual Windows host, which would
  // turn a simulated-macOS prefix like `/opt/brew` into `\opt\brew\bin`.
  if (typeof prefix === 'string' && prefix !== '') push(posixPath.join(prefix, 'bin'));
  push('/opt/homebrew/bin');
  push('/usr/local/bin');
  return dirs;
}

/**
 * Refuse a candidate whose containing directory anyone can write to.
 *
 * Whoever can write a `PATH` directory can already plant an executable there and run it
 * as this user by other means, so this is a defense in depth rather than one that closes
 * a real gap — the finding that prompted it says as much. It is cheap (one `stat`, and
 * only once the file itself has already passed `isExecutableFile`, so it is never paid
 * for the ordinary "not there" candidate) and it means the main process — this app's
 * most privileged context — does not spawn a binary out of a directory any local user
 * could have altered, without at least saying so first.
 *
 * Posix-only: Node's emulated `mode` on Windows does not reflect the real ACL, so a
 * check built on it there would be either a false sense of security or false positives.
 * `configured` is exempt — the user pointed the app here explicitly, which is the one
 * source this module trusts by design (see the file header on step 1).
 */
async function worldWritableDirProblem(directory: string, platform: NodeJS.Platform): Promise<string | null> {
  if (platform === 'win32') return null;
  try {
    const info = await stat(directory);
    return (info.mode & 0o002) !== 0 ? `${directory} is world-writable` : null;
  } catch {
    // Can't stat the directory — let the candidate's own check (which just ran) be the
    // one that explains why, rather than failing twice for the same underlying cause.
    return null;
  }
}

/**
 * Extensions this app can find but can **never** invoke, so finding one is a dead end.
 *
 * `invoke.ts` spawns with `shell: false`, which is a security property and not a
 * preference. Node refuses outright to spawn a `.cmd` or `.bat` without a shell — the
 * hardening that closed CVE-2024-27980, where the Windows command interpreter re-parsed
 * an argument list that had already been quoted. So a candidate with one of these
 * extensions would resolve, then fail on first use with an `EINVAL` naming no cause.
 *
 * `executableNames('win32')` still lists them, deliberately: a shim shaped this way is a
 * real thing to *find*, and the honest outcome is a rejection that names the constraint,
 * not silence about a file that is sitting right there. The alternative — turning the
 * shell on for this one case — would hand a shell the argv the CLI is invoked with, which
 * is exactly what the CVE was.
 */
const UNSPAWNABLE_EXTENSIONS = ['.cmd', '.bat'];

async function isExecutableFile(candidate: string): Promise<string | null> {
  try {
    const info = await stat(candidate); // follows symlinks, which is what we want
    if (!info.isFile()) return `not a regular file`;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === 'ENOENT' ? 'does not exist' : `unreadable: ${String(error)}`;
  }
  // Checked **after** the file is known to exist, not before. Ahead of the `stat` this
  // answered "cannot be spawned" for a `.cmd` candidate that was never there, turning
  // every absent shim name into a rejection with a confident and wrong reason — the
  // search report is read by a user trying to find out why no CLI was found, and a
  // location that holds nothing must say so.
  const lowered = candidate.toLowerCase();
  if (UNSPAWNABLE_EXTENSIONS.some((extension) => lowered.endsWith(extension))) {
    return 'a .cmd or .bat shim cannot be spawned without a shell, and this app never uses one';
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
  // Absolute entries only: a relative one (`.`, `bin`) resolves against the app's working
  // directory, so a `devteam` planted there would be run in place of the user's.
  const pathValue = lookupEnv(env, 'PATH', platform) ?? '';
  // Split and judged by the *host's* rules, not the simulated `platform`: these are real
  // directories on this machine, and the only thing `platform` changes below is which
  // file names are tried.
  for (const dir of pathValue.split(delimiter)) {
    if (dir === '' || !isAbsoluteEntry(dir, process.platform)) continue;
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

  // One label per step, matching this file's own numbered header comment — the
  // screen that reports "which locations it tried" names these three steps rather
  // than a bare count or every individual `PATH` directory.
  const stepLabel: Record<ResolutionSource, string> = {
    configured: 'a configured path (DEVTEAM_CLI_PATH or the settings file)',
    path: 'a PATH entry',
    homebrew: 'Homebrew bin',
    winget: 'a winget shim directory',
  };

  const rejected: RejectedCandidate[] = [];
  const searched: string[] = [];
  const bySource = new Map<ResolutionSource, { label: string; count: number }>();
  const seen = new Set<string>();

  for (const candidate of candidates) {
    if (seen.has(candidate.path)) continue;
    seen.add(candidate.path);
    searched.push(candidate.path);
    const bucket = bySource.get(candidate.source);
    if (bucket) bucket.count += 1;
    else bySource.set(candidate.source, { label: stepLabel[candidate.source], count: 1 });

    const fileProblem = await isExecutableFile(candidate.path);
    if (fileProblem !== null) {
      // "does not exist" for every PATH entry is the normal case and would drown the
      // report, so only a file that is there and unusable is worth recording.
      if (fileProblem !== 'does not exist') {
        rejected.push({ path: candidate.path, source: candidate.source, reason: fileProblem });
      }
      continue;
    }
    if (candidate.source !== 'configured') {
      const dirProblem = await worldWritableDirProblem(dirname(candidate.path), platform);
      if (dirProblem !== null) {
        rejected.push({ path: candidate.path, source: candidate.source, reason: dirProblem });
        continue;
      }
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
    searchedBySource: [...bySource.entries()].map(([source, { label, count }]) => ({ source, label, count })),
    remedy: remedyFor(platform),
  };
}

/**
 * The remedy is the one thing on the no-CLI screen that used to be true on exactly one
 * platform: it opened with a `brew install` line and no branch, while `knownBinDirs`
 * above was fixed specifically so Windows resolution works. ADR-0011 records the
 * Windows installer shape as still undecided — "a placeholder, not a decision" — so the
 * Windows branch does not invent a `winget install <package>` line that would imply
 * one; it says what is actually true today, which is that a Windows user reaches this
 * CLI only by pointing the app at one directly. The macOS/Linux branch holds itself to
 * the same rule: no Homebrew formula is published yet (ADR-0027 § 6), so it gives the
 * from-a-clone install, which lands in `/usr/local/bin` — a directory `knownBinDirs`
 * searches — instead of a `brew install` line that cannot succeed today.
 */
function remedyFor(platform: NodeJS.Platform): readonly string[] {
  const forbidden =
    'The app deliberately ships no copy of the CLI: a bundled, older CLI writing a newer store is the failure ADR-0011 forbids.';
  if (platform === 'win32') {
    return [
      'No packaged Windows install exists yet — ADR-0011 records the Windows installer shape as still undecided.',
      'Set DEVTEAM_CLI_PATH to a `devteam.exe`, or to a checkout\'s scripts/cli/devteam (the extensionless python script).',
      'A script is run through `py.exe -3` or `python.exe` found in an absolute PATH entry, so Python 3 must be installed and on PATH. A `.cmd` or `.bat` shim cannot be used: the app never starts a shell.',
      'Or set `cliPath` in the app settings file to the same path.',
      forbidden,
    ];
  }
  return [
    'No Homebrew formula is published yet — ADR-0027 records the app as a direct-download beta until it is.',
    'Install the CLI from a clone: run `python3 scripts/cli/devteam store install --from .` in it, then `ln -s "$PWD/scripts/cli/devteam" /usr/local/bin/devteam`. Python 3.9+ is required.',
    'Or set DEVTEAM_CLI_PATH to the `devteam` executable, e.g. a checkout\'s scripts/cli/devteam.',
    'Or set `cliPath` in the app settings file to the same path.',
    forbidden,
  ];
}
