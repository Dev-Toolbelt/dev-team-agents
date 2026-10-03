/**
 * "Install the CLI" (ADR-0028): which release it picks, what it refuses, and how it reads
 * the installer's exit — with a fake `fetch` and a fake installer run, so nothing here
 * touches the network or starts a process.
 */
import { createHash } from 'node:crypto';
import { mkdtempSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  BREW_CANDIDATES,
  BREW_FORMULA,
  INSTALL_SCRIPT_COMMAND,
  MAX_INSTALLER_BYTES,
  RELEASE_AUTHOR,
  RELEASES_URL,
  installCli,
  isAllowedUrl,
  parseSums,
  pickRelease,
  type InstallerDeps,
  type Release,
} from '../src/main/cliInstaller.js';

const asset = (name: string) => ({
  name,
  browser_download_url: `https://github.com/Dev-Toolbelt/dev-team-agents/releases/download/x/${name}`,
});

const release = (tag: string, names: string[], extra: Partial<Release> = {}): Release => ({
  tag_name: tag,
  author: { login: RELEASE_AUTHOR },
  assets: names.map(asset),
  ...extra,
});

const cliRelease = (version: string) =>
  release(`v${version}`, [`devteam-setup-${version}-x64.exe`, `devteam-setup-${version}-arm64.exe`, 'SHA256SUMS.txt']);

describe('pickRelease', () => {
  it('takes the newest vX.Y.Z by version, not by listing order', () => {
    const picked = pickRelease([cliRelease('2.9.0'), cliRelease('2.10.0'), cliRelease('2.8.1')], 'x64');
    expect(picked?.version).toBe('2.10.0');
    expect(picked?.installer.name).toBe('devteam-setup-2.10.0-x64.exe');
  });

  it('skips the app’s own releases, drafts, pre-releases and releases without this architecture', () => {
    const picked = pickRelease(
      [
        release('app-v0.2.0', ['Dev Team Agents-Setup.exe', 'SHA256SUMS.txt']),
        { ...cliRelease('3.0.0'), draft: true },
        { ...cliRelease('2.99.0'), prerelease: true },
        release('v2.60.0', ['devteam-setup-2.60.0-x64.exe', 'SHA256SUMS.txt']),
        cliRelease('2.50.0'),
      ],
      'arm64',
    );
    expect(picked?.version).toBe('2.50.0');
  });

  it('skips a release the release workflow did not create', () => {
    const picked = pickRelease([{ ...cliRelease('9.0.0'), author: { login: 'someone' } }, cliRelease('2.50.0')], 'x64');
    expect(picked?.version).toBe('2.50.0');
    expect(pickRelease([{ ...cliRelease('2.50.0'), author: null }], 'x64')).toBeNull();
  });

  it('answers null when no release carries an installer and its sums', () => {
    expect(pickRelease([release('v2.48.0', ['source.tar.gz'])], 'x64')).toBeNull();
    expect(pickRelease([release('v2.48.0', ['devteam-setup-2.48.0-x64.exe'])], 'x64')).toBeNull();
  });
});

describe('parseSums', () => {
  it('reads sha256sum lines, text and binary mode, and ignores anything else', () => {
    const hex = 'a'.repeat(64);
    const sums = parseSums(`${hex}  one.exe\r\n${'B'.repeat(64)} *two.exe\nnot a line\n`);
    expect(sums.get('one.exe')).toBe(hex);
    expect(sums.get('two.exe')).toBe('b'.repeat(64));
    expect(sums.size).toBe(2);
  });
});

describe('isAllowedUrl', () => {
  it('admits GitHub’s API, site and asset hosts over https only', () => {
    expect(isAllowedUrl(RELEASES_URL)).toBe(true);
    expect(isAllowedUrl('https://objects.githubusercontent.com/x')).toBe(true);
    expect(isAllowedUrl('https://release-assets.githubusercontent.com/x')).toBe(true);
    expect(isAllowedUrl('http://github.com/x')).toBe(false);
    expect(isAllowedUrl('https://github.com.evil.example/x')).toBe(false);
    expect(isAllowedUrl('https://evilgithub.com/x')).toBe(false);
    expect(isAllowedUrl('not a url')).toBe(false);
  });
});

describe('installCli', () => {
  const installer = Buffer.from('MZ fake installer');
  const digest = createHash('sha256').update(installer).digest('hex');
  let temp: string;

  beforeEach(() => {
    temp = mkdtempSync(join(tmpdir(), 'cli-installer-'));
  });
  afterEach(() => rmSync(temp, { recursive: true, force: true }));

  function deps(overrides: Partial<InstallerDeps> & { sums?: string; redirectTo?: string } = {}): InstallerDeps {
    const sums = overrides.sums ?? `${digest}  devteam-setup-2.49.0-x64.exe\n`;
    const fetchFake = vi.fn((input: string) => {
      const url = input;
      const respond = (body: BodyInit) => {
        const response = new Response(body, { status: 200 });
        Object.defineProperty(response, 'url', { value: overrides.redirectTo ?? url });
        return Promise.resolve(response);
      };
      if (url === RELEASES_URL) return respond(JSON.stringify([cliRelease('2.49.0')]));
      if (url.endsWith('.exe')) return respond(installer);
      if (url.endsWith('SHA256SUMS.txt')) return respond(sums);
      return Promise.resolve(new Response('', { status: 404 }));
    });
    return {
      platform: 'win32',
      arch: 'x64',
      tempDir: temp,
      fetch: fetchFake as typeof fetch,
      runInstaller: vi.fn(() => Promise.resolve(0)),
      ...overrides,
    };
  }

  it('runs a verified installer and reports the version it came from', async () => {
    const d = deps();
    const result = await installCli(d);
    expect(result).toMatchObject({ outcome: 'installed', version: '2.49.0' });
    expect(d.runInstaller).toHaveBeenCalledWith(expect.stringMatching(/devteam-setup-2\.49\.0-x64\.exe$/));
  });

  it('never runs an installer whose digest is not the one its release lists', async () => {
    const d = deps({ sums: `${'0'.repeat(64)}  devteam-setup-2.49.0-x64.exe\n` });
    const result = await installCli(d);
    expect(result.outcome).toBe('checksum-mismatch');
    expect(d.runInstaller).not.toHaveBeenCalled();
  });

  it('never runs an installer the sums file does not name', async () => {
    const d = deps({ sums: `${digest}  something-else.exe\n` });
    expect((await installCli(d)).outcome).toBe('checksum-mismatch');
    expect(d.runInstaller).not.toHaveBeenCalled();
  });

  it('refuses a download that was redirected off GitHub', async () => {
    const d = deps({ redirectTo: 'https://downloads.example.com/x.exe' });
    const result = await installCli(d);
    expect(result.outcome).toBe('failed');
    expect(d.runInstaller).not.toHaveBeenCalled();
  });

  it('reads the installer’s exit: 1 is a cancel, anything else non-zero a failure', async () => {
    expect((await installCli(deps({ runInstaller: () => Promise.resolve(1) }))).outcome).toBe('cancelled');
    expect((await installCli(deps({ runInstaller: () => Promise.resolve(2) }))).outcome).toBe('failed');
    expect((await installCli(deps({ runInstaller: () => Promise.resolve(null) }))).outcome).toBe('failed');
  });

  it('leaves nothing behind in the temp directory', async () => {
    await installCli(deps());
    expect(readdirSync(temp)).toEqual([]);
  });

  it('does nothing off Windows and macOS or on an architecture with no installer', async () => {
    const linux = deps({ platform: 'linux' });
    expect((await installCli(linux)).outcome).toBe('unsupported');
    expect(linux.fetch).not.toHaveBeenCalled();
    expect((await installCli(deps({ arch: 'ia32' }))).outcome).toBe('unsupported');
  });

  describe('on macOS (ADR-0030)', () => {
    const macDeps = (overrides: Partial<InstallerDeps> = {}) =>
      deps({ platform: 'darwin', arch: 'arm64', ...overrides });

    it('runs `brew install` of the tap formula, by absolute path and with no download, when Homebrew is present', async () => {
      const runBrew = vi.fn(() => Promise.resolve({ code: 0, output: '' }));
      const isExecutable = vi.fn((path: string) => Promise.resolve(path === '/opt/homebrew/bin/brew'));
      const mac = macDeps({ runBrew, isExecutable });

      const result = await installCli(mac);

      expect(result.outcome).toBe('installed');
      expect(runBrew).toHaveBeenCalledWith('/opt/homebrew/bin/brew', ['install', BREW_FORMULA]);
      expect(BREW_FORMULA).toBe('dev-toolbelt/devteam/devteam');
      expect(mac.fetch).not.toHaveBeenCalled();
    });

    it('finds Homebrew at the Intel location too, trying the Apple-silicon one first', async () => {
      const runBrew = vi.fn(() => Promise.resolve({ code: 0, output: '' }));
      const isExecutable = vi.fn((path: string) => Promise.resolve(path === '/usr/local/bin/brew'));

      await installCli(macDeps({ runBrew, isExecutable }));

      expect(isExecutable.mock.calls.map((call) => call[0])).toEqual([...BREW_CANDIDATES]);
      expect(runBrew).toHaveBeenCalledWith('/usr/local/bin/brew', ['install', BREW_FORMULA]);
    });

    it('shows the exact script command, and downloads nothing, when Homebrew is absent', async () => {
      const runBrew = vi.fn();
      const mac = macDeps({ runBrew, isExecutable: () => Promise.resolve(false) });

      const result = await installCli(mac);

      expect(result.outcome).toBe('manual');
      expect(result.command).toBe(INSTALL_SCRIPT_COMMAND);
      expect(runBrew).not.toHaveBeenCalled();
      expect(mac.fetch).not.toHaveBeenCalled();
    });

    it('reports Homebrew’s failure with its output and offers the script command instead', async () => {
      const runBrew = vi.fn(() => Promise.resolve({ code: 1, output: 'Error: No available formula' }));
      const result = await installCli(macDeps({ runBrew, isExecutable: () => Promise.resolve(true) }));

      expect(result.outcome).toBe('failed');
      expect(result.message).toContain('No available formula');
      expect(result.command).toBe(INSTALL_SCRIPT_COMMAND);
    });
  });

  it('reports a failure, and runs nothing, when GitHub answers an error or garbage', async () => {
    const answering = (body: string, status: number) =>
      vi.fn(() => {
        const response = new Response(body, { status });
        Object.defineProperty(response, 'url', { value: RELEASES_URL });
        return Promise.resolve(response);
      }) as unknown as typeof fetch;
    for (const fetchFake of [answering('rate limited', 403), answering('<html>not json</html>', 200)]) {
      const d = deps({ fetch: fetchFake });
      expect((await installCli(d)).outcome).toBe('failed');
      expect(d.runInstaller).not.toHaveBeenCalled();
    }
  });

  it('refuses an installer larger than the cap without running it', async () => {
    const d = deps();
    const original = d.fetch;
    const oversized = vi.fn(async (input: string) => {
      const response = await original(input);
      if (!input.endsWith('.exe')) return response;
      const big = new Response('x', { status: 200, headers: { 'content-length': String(MAX_INSTALLER_BYTES + 1) } });
      Object.defineProperty(big, 'url', { value: input });
      return big;
    });
    const result = await installCli({ ...d, fetch: oversized as typeof fetch });
    expect(result.outcome).toBe('failed');
    expect(d.runInstaller).not.toHaveBeenCalled();
  });

  it('says so when no release carries an installer yet', async () => {
    const d = deps({
      fetch: vi.fn(() => {
        const response = new Response(JSON.stringify([release('v2.48.0', [])]), { status: 200 });
        Object.defineProperty(response, 'url', { value: RELEASES_URL });
        return Promise.resolve(response);
      }) as unknown as typeof fetch,
    });
    expect((await installCli(d)).outcome).toBe('no-release');
  });
});
