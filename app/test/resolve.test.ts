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
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { knownBinDirs, knownLocationSource, resolveDevteam } from '../src/cli/resolve.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));

let root: string;

/** Put a copy of the fake CLI at `<root>/<dir>/devteam`, pinned to one scenario. */
async function plant(dir: string, scenario: string): Promise<string> {
  const target = join(root, dir);
  await mkdir(target, { recursive: true });
  const path = join(target, 'devteam');
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

describe('order', () => {
  it('prefers DEVTEAM_CLI_PATH over everything on PATH', async () => {
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

  it('prefers the settings-file path over PATH too, and names which seam won', async () => {
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

  it('falls back to PATH, honouring PATH order', async () => {
    const first = await plant('bin-a', 'version-with-compat');
    await plant('bin-b', 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: [join(root, 'bin-a'), join(root, 'bin-b')].join(':') },
      platform: 'darwin',
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.path).toBe(first);
    expect(resolution.cli.source).toBe('path');
  });

  it('falls back to HOMEBREW_PREFIX/bin when PATH has nothing — the Finder-launch case', async () => {
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

  it('reads the store version and compat block from the probe, so the UI needs no second call', async () => {
    const path = await plant('bin', 'version-with-compat');
    const resolution = await resolveDevteam({ env: { PATH: join(root, 'bin') }, platform: 'darwin' });
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

  it('finds a CLI in a Windows channel location, under every shim name', async () => {
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
    // `executableNames` tries the four shim names; `devteam` is the one planted here.
    expect(resolution.cli.path).toBe(join(links, 'devteam'));
  });
});

describe('a candidate must answer, not merely exist', () => {
  it('rejects a program called devteam that has no compat block', async () => {
    await plant('bin', 'version-no-compat');
    const good = await plant('bin2', 'version-with-compat');
    const resolution = await resolveDevteam({
      env: { PATH: [join(root, 'bin'), join(root, 'bin2')].join(':') },
      platform: 'darwin',
    });
    if (!resolution.found) throw new Error('expected a CLI');
    expect(resolution.cli.path).toBe(good);
    expect(resolution.rejected.map((entry) => entry.reason).join(' ')).toContain('not a devteam CLI');
  });

  it('records a file that exists but is not executable', async () => {
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
    expect(resolution.remedy.join(' ')).toContain('brew install');
    // The claim ADR-0011 rests on, asserted rather than only commented.
    expect(resolution.remedy.join(' ')).toContain('ships no copy of the CLI');
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
  });
});
