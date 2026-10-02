/**
 * Resolution order, and the rule that a candidate must answer rather than merely exist.
 *
 * **These tests depend on nothing outside `root`.** Step 3's directories are absolute
 * machine paths, so the three `found === false` assertions below used to pass only because
 * neither `/opt/homebrew/bin/devteam` nor `/usr/local/bin/devteam` happened to exist on the
 * machine running them — on a contributor's laptop with a Homebrew-installed CLI they went
 * red with a message that named neither cause. Every test that asserts a negative now
 * passes `knownLocations` explicitly; what `knownBinDirs` derives is asserted separately, as
 * a pure function, where the real paths are the subject rather than an accident.
 */

import { chmod, copyFile, mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { delimiter, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { installerBinDirs, knownBinDirs, knownLocationSource, resolveDevteam } from '../src/cli/resolve.js';
import { readLauncherManifest, resolveFixtureBinary } from './fixtures/launcher-manifest.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));

/**
 * `plant()` below stands in for a real installed CLI: `resolveDevteam` decides the
 * candidate path itself and spawns it directly with `shell: false` (`invoke.ts`'s
 * policy), so — unlike `invoke.test.ts`'s `fakeCli()` — there is no seam here to route
 * through `node` instead. On POSIX the wrapper `plant()` writes is a `#!/bin/sh`
 * script; on Windows it copies the compiled launcher `launcher-global-setup.ts` built
 * (see `launcherAvailable` below), a real PE, because Windows honours no `#!` line and
 * Node's own `spawn` refuses to launch a `.bat`/`.cmd` without `shell: true` besides
 * (CVE-2024-27980), which `invoke.ts` deliberately never sets. When the launcher could
 * not be built (no compiler, or the compile failed), every test that needs a planted
 * candidate to actually answer stays skipped on Windows; the ones that only assert on
 * `knownBinDirs` or on a rejection reached before a spawn is attempted are unaffected
 * either way.
 */
const skipOnWindows = process.platform === 'win32';
const launcherManifest = readLauncherManifest();
const { available: launcherAvailable } = resolveFixtureBinary(FAKE, launcherManifest?.fakeDevteam);
/** Guards every `plant()`-dependent test that has no POSIX-mode-bit reason to skip. */
const skipOnWindowsWithoutLauncher = skipOnWindows && !launcherAvailable;

let root: string;

/**
 * `platform: 'darwin'` below is deliberate — see the comment on the Homebrew-fallback
 * test — but `executableNames(platform)` is what it actually decides, and that is the
 * filename `resolveDevteam` searches for, not merely a label. `plant()` always writes
 * `devteam.exe` on a real Windows host (`CreateProcess` refuses to run an extensionless
 * PE — see `plant()`'s own comment), regardless of which platform a test asks
 * `resolveDevteam` to simulate. So a test that both plants a real Windows binary *and*
 * simulates `'darwin'` is searching for a name that can never match what is actually on
 * disk there — not a Windows incompatibility in the behaviour under test, just this
 * file asking for a filename the real host cannot produce. `crossPlatform` is `'win32'`
 * only on a real Windows host and `'darwin'` everywhere else, which is a no-op for
 * macOS/Linux CI: every branch `resolveDevteam` takes off `platform` besides
 * `executableNames` treats "not `'win32'`" as one case. Tests whose assertions are
 * themselves Homebrew- or POSIX-mode-specific keep the hardcoded `'darwin'` and are
 * skipped on Windows instead — the two are not the same fix.
 */
const crossPlatform: NodeJS.Platform = process.platform === 'win32' ? 'win32' : 'darwin';

/** Put a copy of the fake CLI at `<root>/<dir>/devteam`, pinned to one scenario. */
async function plant(dir: string, scenario: string): Promise<string> {
  const target = join(root, dir);
  await mkdir(target, { recursive: true });
  // `.exe` on Windows, and it is not cosmetic: `CreateProcess` states that
  // `lpApplicationName` "must include the file name extension; no default extension is
  // assumed", so an extensionless file is not executed there even when it is a valid PE.
  // `executableNames('win32')` lists `devteam.exe` first, so this is also the name the
  // resolver looks for first.
  const path = join(target, process.platform === 'win32' ? 'devteam.exe' : 'devteam');
  if (process.platform === 'win32') {
    // `skipOnWindowsWithoutLauncher` gates every caller, so `launcherManifest`'s path
    // is present whenever this branch actually runs.
    const launcherPath = launcherManifest?.fakeDevteam.path;
    if (launcherPath === null || launcherPath === undefined) {
      throw new Error('plant() called on Windows without a built launcher — a missing skipIf guard');
    }
    await copyFile(launcherPath, path);
    // `resolveDevteam`'s probe never passes `invokeDevteam` a custom `env` (see
    // `resolve.ts`'s `probe()`), so — same reason as the POSIX wrapper below — the
    // scenario cannot travel through the environment. `launcher.c` reads this sibling
    // file at startup instead.
    await writeFile(`${path}.scenario`, scenario, 'utf8');
    return path;
  }
  await copyFile(FAKE, path);
  // The fake reads its scenario from the environment, which `resolveDevteam` does not
  // forward — so it is baked into a shell wrapper instead. A wrapper is also a fair
  // stand-in for the Homebrew formula's `bin.install_symlink`.
  await writeFile(path, `#!/bin/sh\nFAKE_DEVTEAM_SCENARIO=${scenario} exec ${process.execPath} ${FAKE} "$@"\n`);
  await chmod(path, 0o755);
  return path;
}

beforeEach(async () => {
  root = await mkdtemp(join(tmpdir(), 'devteam-app-resolve-'));
});

// One `mkdtemp` per test and nothing removed them: a full run left a few hundred
// directories under the system temp dir, which survive until the OS sweeps them.
afterEach(async () => {
  await rm(root, { recursive: true, force: true });
});

describe('PATH walk', () => {
  it('skips relative entries', async () => {
    const resolution = await resolveDevteam({
      env: { PATH: ['.', 'bin', join(root, 'abs')].join(delimiter) },
      platform: crossPlatform,
      knownLocations: [],
    });
    if (resolution.found) throw new Error('unreachable');
    expect(resolution.searched.every((path) => path.startsWith(root))).toBe(true);
    expect(resolution.searched.length).toBeGreaterThan(0);
  });
});

describe('order', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('prefers DEVTEAM_CLI_PATH over everything on PATH', async () => {
    const configured = await plant('configured', 'version-with-compat');
    const onPath = await plant('bin', 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { DEVTEAM_CLI_PATH: configured, PATH: join(root, 'bin') },
      platform: 'darwin',
    });
    expect(resolution.found).toBe(true);
    if (!resolution.found) throw new Error('unreachable');
    expect(resolution.cli.path).toBe(configured);
    expect(resolution.cli.source).toBe('configured');
    expect(resolution.cli.path).not.toBe(onPath);
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('prefers the settings-file path over PATH too, and names which seam won', async () => {
    const configured = await plant('configured', 'version-with-compat');
    await plant('bin', 'version-with-compat');
    const resolution = await resolveDevteam({
      configuredPath: configured,
      env: { PATH: join(root, 'bin') },
      platform: 'darwin',
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.source).toBe('configured');
    expect(resolution.cli.sourceDetail).toContain('settings file');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('falls back to PATH, honouring PATH order', async () => {
    const first = await plant('bin-a', 'version-with-compat');
    await plant('bin-b', 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: [join(root, 'bin-a'), join(root, 'bin-b')].join(delimiter) },
      platform: crossPlatform,
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.path).toBe(first);
    expect(resolution.cli.source).toBe('path');
  });

  // Homebrew itself is not a Windows concept, and `platform: 'darwin'` below is what
  // `resolveDevteam` actually branches on for the fallback being tested — that part
  // was always the point. What does not survive a real Windows host is `crossPlatform`
  // above: `knownBinDirs('win32', …)` ignores `HOMEBREW_PREFIX` entirely, so mapping
  // this test's `platform` the way the PATH-order tests do would just fail the
  // assertion for a different reason. A genuinely Windows-skipped behaviour, not a
  // launcher-gated one — `skipOnWindowsWithoutLauncher` used to gate it on the (wrong)
  // assumption that spawning the planted binary was the only thing standing in the
  // way; `plant()`'s `.exe` requirement (see its own comment) means `executableNames`
  // searching for extensionless `devteam` can never find it there regardless.
  it.skipIf(skipOnWindows)('falls back to HOMEBREW_PREFIX/bin when PATH has nothing — the Finder-launch case', async () => {
    // Deliberately *not* injecting `knownLocations`: this is the one test whose subject is
    // the derivation, and it stays machine-independent because `knownBinDirs` puts
    // `$HOMEBREW_PREFIX/bin` ahead of the two conventional prefixes, so a real
    // `/opt/homebrew/bin/devteam` could never win over the one planted here.
    const brewPrefix = join(root, 'brew');
    await plant('brew/bin', 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'empty'), HOMEBREW_PREFIX: brewPrefix },
      platform: 'darwin',
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.source).toBe('homebrew');
    expect(resolution.cli.path).toBe(join(brewPrefix, 'bin', 'devteam'));
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('reads the store version and compat block from the probe, so the UI needs no second call', async () => {
    const path = await plant('bin', 'version-with-compat');
    const resolution = await resolveDevteam({ env: { PATH: join(root, 'bin') }, platform: crossPlatform });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.path).toBe(path);
    expect(resolution.cli.storeVersion).toBe('3.0.0');
    expect(resolution.cli.compat.jsonContract).toBe(1);
    expect(resolution.cli.compat.minAppVersion).toBeNull();
    expect(resolution.cli.compat.storeSchemas['project_layout']).toBe(2);
  });
});

describe('step 3 — the channel location a GUI launch cannot see', () => {
  it('derives Homebrew’s two conventional prefixes on macOS, and honours HOMEBREW_PREFIX first', () => {
    // The real absolute paths, asserted where they are the subject. The `found === false`
    // tests below no longer touch them.
    expect(knownBinDirs('darwin', {})).toEqual(['/opt/homebrew/bin', '/usr/local/bin']);
    expect(knownBinDirs('darwin', { HOMEBREW_PREFIX: '/opt/brew' })).toEqual([
      '/opt/brew/bin',
      '/opt/homebrew/bin',
      '/usr/local/bin',
    ]);
    // An empty or non-string prefix is ignored rather than joined into `/bin`.
    expect(knownBinDirs('linux', { HOMEBREW_PREFIX: '' })).toEqual(['/opt/homebrew/bin', '/usr/local/bin']);
    expect(knownLocationSource('darwin')).toBe('homebrew');
  });

  it('searches winget’s shim directories on Windows — the gap that was guarded away', () => {
    // ADR-0015 § 5 row 4 names "winget's shim directory on Windows", and its Risks table
    // says the resolution order is the only thing standing between a Windows app and no
    // CLI. The step used to be skipped entirely on win32.
    expect(knownBinDirs('win32', { LOCALAPPDATA: 'C:\\Users\\k\\AppData\\Local' })).toEqual([
      join('C:\\Users\\k\\AppData\\Local', 'Microsoft', 'WinGet', 'Links'),
      join('C:\\Users\\k\\AppData\\Local', 'Microsoft', 'WindowsApps'),
    ]);
    // No path is invented when the variable that anchors them is absent.
    expect(knownBinDirs('win32', {})).toEqual([]);
    expect(knownLocationSource('win32')).toBe('winget');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('finds a CLI in a Windows channel location, under every shim name', async () => {
    const localAppData = join(root, 'AppData');
    const links = join(localAppData, 'Microsoft', 'WinGet', 'Links');
    await plant(join('AppData', 'Microsoft', 'WinGet', 'Links'), 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'nowhere'), LOCALAPPDATA: localAppData },
      platform: 'win32',
      knownLocations: [links],
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.source).toBe('winget');
    expect(resolution.cli.sourceDetail).toContain('winget shim directory');
    // `executableNames` tries the four shim names; `plant()` decides which one actually
    // exists to be found, and it decides that from the *real* host, not this test's
    // simulated `platform: 'win32'` — `devteam.exe` on an actual Windows runner (the
    // first name tried, so it wins outright), `devteam` everywhere else. A hardcoded
    // `'devteam'` here happened to match on every CI leg except the one this test is
    // named after, because only a real Windows host ever writes the `.exe`.
    expect(resolution.cli.path).toBe(join(links, process.platform === 'win32' ? 'devteam.exe' : 'devteam'));
  });
});

describe('step 4 — the devteam installers’ own directory (ADR-0028)', () => {
  it('derives the NSIS installer’s bin on Windows and ~/.local/bin elsewhere', () => {
    expect(installerBinDirs('win32', { LOCALAPPDATA: 'C:\\Users\\k\\AppData\\Local' })).toEqual([
      join('C:\\Users\\k\\AppData\\Local', 'Programs', 'devteam', 'bin'),
    ]);
    expect(installerBinDirs('darwin', { HOME: '/Users/k' })).toEqual(['/Users/k/.local/bin']);
    // No path is invented when the variable that anchors it is absent.
    expect(installerBinDirs('win32', {})).toEqual([]);
    expect(installerBinDirs('darwin', {})).toEqual([]);
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('finds a CLI the Windows installer placed, with no PATH entry for it', async () => {
    // The case the app's own "Install the CLI" action creates: the installer appended its
    // bin to the user PATH, but this process started before that and still has the old one.
    // LOCALAPPDATA is the temp root, so step 3's winget directories are empty too and the
    // test depends only on what it planted.
    const localAppData = join(root, 'AppData');
    await plant(join('AppData', 'Programs', 'devteam', 'bin'), 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'nowhere'), LOCALAPPDATA: localAppData },
      platform: 'win32',
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.source).toBe('installer');
    expect(resolution.cli.sourceDetail).toContain('devteam installer');
  });
});

describe('a candidate must answer, not merely exist', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('rejects a program called devteam that has no compat block', async () => {
    await plant('bin', 'version-no-compat');
    const good = await plant('bin2', 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: [join(root, 'bin'), join(root, 'bin2')].join(delimiter) },
      platform: crossPlatform,
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.path).toBe(good);
    expect(resolution.rejected.map((entry) => entry.reason).join(' ')).toContain('not a devteam CLI');
  });

  // Windows has no POSIX execute bit: `chmod(path, 0o600)` does not make a file
  // non-executable there (see `invoke.test.ts`'s equivalent test and `resolve.ts`'s own
  // `worldWritableDirProblem` comment on the same limit of `fs`'s emulated `mode`).
  it.skipIf(skipOnWindows)('records a file that exists but is not executable', async () => {
    const dir = join(root, 'bin');
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'devteam'), '#!/bin/sh\n');
    await chmod(join(dir, 'devteam'), 0o600);
    // `knownLocations: []` — see this file's header. Without it a Homebrew-installed
    // `devteam` on the machine running the test would satisfy the search and this would go
    // red for a reason that has nothing to do with the file mode being asserted.
    const resolution = await resolveDevteam({ env: { PATH: dir }, platform: 'darwin', knownLocations: [] });
    expect(resolution.found).toBe(false);
    if (resolution.found) throw new Error('unreachable');
    expect(resolution.rejected[0]?.reason).toContain('not executable');
  });

  // Not skipped on Windows: the rejection is decided from the candidate's name, so it is
  // the same answer on every host — which is the point. A shim the resolver can see and
  // the spawner can never run has to say so, or the failure surfaces later as an `EINVAL`
  // from `invoke.ts` naming no cause at all.
  it('rejects a .cmd or .bat shim it could never spawn, and says why', async () => {
    const dir = join(root, 'bin');
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'devteam.cmd'), '@echo off\n');
    const resolution = await resolveDevteam({
      env: { PATH: dir },
      platform: 'win32',
      knownLocations: [],
    });
    expect(resolution.found).toBe(false);
    if (resolution.found) throw new Error('unreachable');
    const reasons = resolution.rejected.map((entry) => entry.reason).join(' ');
    expect(reasons).toContain('without a shell');
  });

  it('does not report a directory as a CLI', async () => {
    await mkdir(join(root, 'bin', 'devteam'), { recursive: true });
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'bin') },
      platform: 'darwin',
      knownLocations: [],
    });
    expect(resolution.found).toBe(false);
    if (resolution.found) throw new Error('unreachable');
    expect(resolution.rejected[0]?.reason).toContain('not a regular file');
  });

  // Windows has no POSIX world-writable bit for `chmod(dir, 0o777)` to set — the same
  // limit the two skips below this one are for — and `worldWritableDirProblem` is
  // itself `platform === 'win32'`-gated to skip the check outright in production, so
  // exercising it needs `platform: 'darwin'` simulated. That reintroduces the
  // extensionless-name mismatch `crossPlatform` exists to avoid (see its own comment
  // above): mapping this test to `crossPlatform` would find the `.exe` `plant()`
  // wrote and pass it straight to `probe()`, which would answer and make `found` true,
  // asserting the opposite of what this test is for. A behaviour the production code
  // itself disables on Windows has nothing here to prove either way.
  it.skipIf(skipOnWindows)('refuses to run a candidate out of a world-writable directory', async () => {
    const cli = await plant('bin', 'version-with-compat');
    await chmod(join(root, 'bin'), 0o777);
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'bin') },
      platform: 'darwin',
      knownLocations: [],
    });
    expect(resolution.found).toBe(false);
    if (resolution.found) throw new Error('unreachable');
    expect(resolution.rejected[0]?.path).toBe(cli);
    expect(resolution.rejected[0]?.reason).toContain('world-writable');
  });

  // Stays POSIX-only even with the Windows launcher available: the point being
  // asserted is `chmod(dir, 0o777)`, and NTFS has no world-writable bit for it to set.
  it.skipIf(skipOnWindows)('trusts a configured path even out of a world-writable directory — the user overrode the search', async () => {
    const cli = await plant('configured', 'version-with-compat');
    await chmod(join(root, 'configured'), 0o777);
    const resolution = await resolveDevteam({
      env: { DEVTEAM_CLI_PATH: cli },
      platform: 'darwin',
      knownLocations: [],
    });
    expect(resolution.found).toBe(true);
    if (!resolution.found) throw new Error('unreachable');
    expect(resolution.cli.path).toBe(cli);
  });
});

describe('when nothing is found', () => {
  it('names the places it looked and what to do — no bundled fallback', async () => {
    const brewish = join(root, 'not-brew', 'bin');
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'nowhere') },
      platform: 'darwin',
      knownLocations: [brewish],
    });
    expect(resolution.found).toBe(false);
    if (resolution.found) throw new Error('unreachable');
    expect(resolution.searched.length).toBeGreaterThan(0);
    // Both steps are in the report, in order: PATH, then the channel location.
    expect(resolution.searched).toContain(join(root, 'nowhere', 'devteam'));
    expect(resolution.searched).toContain(join(brewish, 'devteam'));
    expect(resolution.remedy.join(' ')).toContain('DEVTEAM_CLI_PATH');
    // No formula is published (ADR-0027 § 6), so the remedy must not send anyone to one.
    expect(resolution.remedy.join(' ')).not.toContain('brew install');
    // The CLI's own installer (ADR-0028), into a directory step 4 searches.
    expect(resolution.remedy.join(' ')).toContain('install-cli.sh');
    expect(resolution.remedy.join(' ')).toContain('~/.local/bin');
    // The claim ADR-0011 rests on, asserted rather than only commented.
    expect(resolution.remedy.join(' ')).toContain('ships no copy of the CLI');
    // "which locations it tried" (ADR-0015 § 5), grouped by step rather than one count.
    const path = resolution.searchedBySource.find((entry) => entry.source === 'path');
    const homebrew = resolution.searchedBySource.find((entry) => entry.source === 'homebrew');
    expect(path?.count).toBe(1);
    expect(homebrew?.count).toBe(1);
  });

  it('still searches a channel location on Windows, under each shim name', async () => {
    const links = join(root, 'AppData', 'Microsoft', 'WinGet', 'Links');
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'nowhere') },
      platform: 'win32',
      knownLocations: [links],
    });
    if (resolution.found) throw new Error('unreachable');
    expect(resolution.searched.some((path) => path.includes('homebrew'))).toBe(false);
    expect(resolution.searched.some((path) => path.endsWith('devteam.exe'))).toBe(true);
    for (const name of ['devteam.exe', 'devteam.cmd', 'devteam.bat', 'devteam']) {
      expect(resolution.searched, name).toContain(join(links, name));
    }
    // Four shim names under the one winget directory: one location, four candidates.
    const winget = resolution.searchedBySource.find((entry) => entry.source === 'winget');
    expect(winget?.count).toBe(4);
  });

  it('gives Windows a remedy that is actually true, not a macOS or invented-package one', async () => {
    const resolution = await resolveDevteam({
      env: { PATH: join(root, 'nowhere') },
      platform: 'win32',
      knownLocations: [],
    });
    if (resolution.found) throw new Error('unreachable');
    const remedy = resolution.remedy.join(' ');
    // The defect this covers: the remedy used to open with `brew install`, unconditionally,
    // on every platform — including this one, where Homebrew does not apply.
    expect(remedy).not.toContain('brew install');
    // No packaged Windows CLI exists; a `winget install <pkg>` line would claim a package
    // that does not exist.
    expect(remedy).not.toContain('winget install');
    // The installer the screen's "Install the CLI" action fetches (ADR-0028).
    expect(remedy).toContain('Install the CLI');
    expect(remedy).toContain('devteam-setup-');
    expect(remedy).toContain('DEVTEAM_CLI_PATH');
    // The app's own installer shape is decided (NSIS); the remedy used to call it undecided.
    expect(remedy).not.toContain('undecided');
  });
});
