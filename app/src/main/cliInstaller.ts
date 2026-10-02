/**
 * "Install the CLI" on Windows: fetch the newest CLI installer, check it, run it (ADR-0028).
 *
 * The app still ships no CLI (ADR-0011): it installs the newest *published* one, which then
 * updates itself through `devteam update`. So the bundled-older-CLI failure ADR-0011 forbids
 * cannot arise from this — the CLI it installs is never older than the newest release.
 *
 * Every network call is to GitHub and nowhere else: the release listing on
 * `api.github.com`, the assets on `github.com`, which redirects to GitHub's asset hosts.
 * A response that ends anywhere else is refused, and so is an installer whose SHA-256 is
 * not the one the same release's `SHA256SUMS.txt` lists. That proves integrity, not
 * authorship — the same limit ADR-0027 records for the app's own installers.
 *
 * The installer runs with no shell (`spawn`, `shell: false`), interactively: its wizard is
 * where the user sees what is installed and is offered Git for Windows.
 */
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import type { CliInstallResult } from '../shared/api.js';

export const RELEASES_URL = 'https://api.github.com/repos/Dev-Toolbelt/dev-team-agents/releases?per_page=50';
export const RELEASES_PAGE = 'https://github.com/Dev-Toolbelt/dev-team-agents/releases';

/** Hosts a request may start at or be redirected to. Exact names; no suffix matching. */
const ALLOWED_HOSTS = new Set([
  'api.github.com',
  'github.com',
  'objects.githubusercontent.com',
  'release-assets.githubusercontent.com',
]);

/** NSIS exit codes: 1 is the user cancelling; the CLI installer uses 2 for a failed setup step. */
const NSIS_CANCELLED = 1;

export interface ReleaseAsset {
  readonly name: string;
  readonly browser_download_url: string;
}

export interface Release {
  readonly tag_name: string;
  readonly draft?: boolean;
  readonly prerelease?: boolean;
  readonly assets: readonly ReleaseAsset[];
}

export interface InstallerChoice {
  readonly version: string;
  readonly installer: ReleaseAsset;
  readonly sums: ReleaseAsset;
}

export type InstallerArch = 'x64' | 'arm64';

export function installerArch(arch: string): InstallerArch | null {
  return arch === 'x64' || arch === 'arm64' ? arch : null;
}

export function isAllowedUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && ALLOWED_HOSTS.has(parsed.hostname);
  } catch {
    return false;
  }
}

function semverKey(tag: string): readonly number[] | null {
  const match = /^v(\d+)\.(\d+)\.(\d+)$/.exec(tag);
  return match === null ? null : [Number(match[1]), Number(match[2]), Number(match[3])];
}

function compareKeys(left: readonly number[], right: readonly number[]): number {
  for (let index = 0; index < left.length; index += 1) {
    const difference = left[index]! - right[index]!;
    if (difference !== 0) return difference;
  }
  return 0;
}

/**
 * The newest `vX.Y.Z` release that carries this architecture's installer and its sums.
 *
 * Not `releases/latest`: the app's own `app-v*` releases live in the same repository
 * (ADR-0027) and are not the CLI. Drafts and pre-releases are skipped.
 */
export function pickRelease(releases: readonly Release[], arch: InstallerArch): InstallerChoice | null {
  let best: { key: readonly number[]; choice: InstallerChoice } | null = null;
  for (const release of releases) {
    if (release.draft === true || release.prerelease === true) continue;
    const key = semverKey(release.tag_name);
    if (key === null) continue;
    const version = release.tag_name.slice(1);
    const installer = release.assets.find((asset) => asset.name === `devteam-setup-${version}-${arch}.exe`);
    const sums = release.assets.find((asset) => asset.name === 'SHA256SUMS.txt');
    if (installer === undefined || sums === undefined) continue;
    if (best === null || compareKeys(key, best.key) > 0) best = { key, choice: { version, installer, sums } };
  }
  return best?.choice ?? null;
}

/** `sha256sum` format: `<hex>  <name>` (a `*` before the name marks binary mode). */
export function parseSums(text: string): Map<string, string> {
  const sums = new Map<string, string>();
  for (const line of text.split(/\r?\n/)) {
    const match = /^([0-9a-fA-F]{64}) [ *](.+)$/.exec(line.trim());
    if (match !== null) sums.set(match[2]!, match[1]!.toLowerCase());
  }
  return sums;
}

export interface InstallerDeps {
  readonly platform: NodeJS.Platform;
  readonly arch: string;
  readonly tempDir: string;
  readonly fetch: typeof fetch;
  /** Runs the installer and resolves with its exit code. */
  readonly runInstaller: (path: string) => Promise<number | null>;
}

async function get(deps: InstallerDeps, url: string): Promise<Response> {
  if (!isAllowedUrl(url)) throw new Error(`refused to download from ${url}`);
  const response = await deps.fetch(url, {
    redirect: 'follow',
    headers: { 'User-Agent': 'dev-team-agents-app', Accept: 'application/octet-stream, application/json' },
  });
  // Where the redirects ended, not only where they began.
  if (response.url !== '' && !isAllowedUrl(response.url)) throw new Error(`refused a redirect to ${response.url}`);
  if (!response.ok) throw new Error(`${url} answered HTTP ${response.status}`);
  return response;
}

export async function installCli(deps: InstallerDeps): Promise<CliInstallResult> {
  const arch = installerArch(deps.arch);
  if (deps.platform !== 'win32' || arch === null) {
    return { outcome: 'unsupported', message: 'The app installs the CLI on Windows (x64, arm64) only.' };
  }

  let choice: InstallerChoice | null;
  try {
    const releases = (await (await get(deps, RELEASES_URL)).json()) as Release[];
    choice = pickRelease(Array.isArray(releases) ? releases : [], arch);
  } catch (error) {
    return { outcome: 'failed', message: `Could not read the releases from GitHub: ${String(error)}` };
  }
  if (choice === null) {
    return {
      outcome: 'no-release',
      message: `No published release carries a Windows ${arch} CLI installer yet. See ${RELEASES_PAGE}.`,
    };
  }

  const dir = await mkdtemp(join(deps.tempDir, 'devteam-cli-'));
  try {
    const [installerBytes, sumsText] = await Promise.all([
      get(deps, choice.installer.browser_download_url).then(async (r) => Buffer.from(await r.arrayBuffer())),
      get(deps, choice.sums.browser_download_url).then((r) => r.text()),
    ]);
    const expected = parseSums(sumsText).get(choice.installer.name);
    const actual = createHash('sha256').update(installerBytes).digest('hex');
    if (expected === undefined || expected !== actual) {
      return {
        outcome: 'checksum-mismatch',
        version: choice.version,
        message: `${choice.installer.name} does not match the SHA-256 its release lists, so it was not run.`,
      };
    }
    const path = join(dir, choice.installer.name);
    await writeFile(path, installerBytes);
    const code = await deps.runInstaller(path);
    if (code === 0) return { outcome: 'installed', version: choice.version, message: `devteam ${choice.version} is installed.` };
    if (code === NSIS_CANCELLED) return { outcome: 'cancelled', version: choice.version, message: 'The installer was cancelled.' };
    return { outcome: 'failed', version: choice.version, message: `The installer exited with ${String(code)}.` };
  } catch (error) {
    return { outcome: 'failed', version: choice.version, message: String(error) };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

/** The real installer run: no shell, the wizard visible, resolved on exit. */
export function runInstallerProcess(path: string): Promise<number | null> {
  return new Promise((resolve) => {
    const child = spawn(path, [], { shell: false, stdio: 'ignore', windowsHide: false });
    child.once('error', () => resolve(null));
    child.once('exit', (code) => resolve(code));
  });
}
