/**
 * The first-run channels in `main/ipc.ts` and the preload bridge in front of them (ADR-0030):
 * what crosses the bridge, and what main refuses before spawning anything. Same harness as
 * `ipc.test.ts` — a mocked `electron`, and `fixtures/fake-devteam-write.mjs` as the CLI.
 */
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from 'vitest';

import type * as IpcModule from '../src/main/ipc.js';
import { CHANNELS, type DevteamBridge } from '../src/shared/api.js';
import { readLauncherManifest, resolveFixtureBinary } from './fixtures/launcher-manifest.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam-write.mjs', import.meta.url));
const { binary: FAKE_BINARY, available: launcherAvailable } = resolveFixtureBinary(FAKE, readLauncherManifest()?.fakeDevteamWrite);
const skip = process.platform === 'win32' && !launcherAvailable;

const TRUSTED_RENDERER = { indexUrl: 'file:///app/dist/renderer/index.html', devServerOrigin: null } as const;
const TRUSTED = { senderFrame: { url: TRUSTED_RENDERER.indexUrl, parent: null } };

type Handler = (...args: unknown[]) => unknown;

/** The slice of an answer these tests read; `toMatchObject` checks the rest. */
interface Answer {
  readonly command: string;
  readonly data: { readonly findings: readonly { readonly auto_fixable: boolean }[] };
}

let dir: string;
beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'devteam-app-onboarding-'));
});
afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

async function load(chosenPath: string | null = '/work/my app') {
  vi.resetModules();
  const handlers = new Map<string, Handler>();
  const showOpenDialog = vi.fn(() =>
    Promise.resolve(chosenPath === null ? { canceled: true, filePaths: [] as string[] } : { canceled: false, filePaths: [chosenPath] }),
  );
  vi.doMock('electron', () => ({
    ipcMain: { handle: (channel: string, listener: Handler) => handlers.set(channel, listener) },
    dialog: { showOpenDialog, showMessageBox: vi.fn() },
  }));
  onTestFinished(() => {
    vi.doUnmock('electron');
  });
  const { registerIpc } = await import('../src/main/ipc.js');
  const runFix = vi.fn<NonNullable<IpcModule.IpcDependencies['runFix']>>(() => Promise.resolve({ ran: true, succeeded: true, message: 'Done.' }));
  const launchTerminal = vi.fn<NonNullable<IpcModule.IpcDependencies['launchTerminal']>>(() => Promise.resolve({ launched: true }));
  await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE_BINARY }), 'utf8');
  registerIpc({
    userDataDir: dir,
    appVersion: '0.0.0-test',
    electronVersion: '39.8.10',
    packaged: false,
    trustedRenderer: TRUSTED_RENDERER,
    runFix,
    launchTerminal,
  });
  const call = (channel: string, ...args: unknown[]) => handlers.get(channel)!(TRUSTED, ...args) as Promise<Answer>;
  const offer = () => call(CHANNELS.chooseProjectDirectory);
  return { call, offer, runFix, launchTerminal };
}

describe.skipIf(skip)('detectProject and startProject', () => {
  it('refuse a folder this session never offered, and spawn nothing', async () => {
    const { call } = await load();
    for (const channel of [CHANNELS.detectProject, CHANNELS.startProject]) {
      const result = await call(channel, channel === CHANNELS.startProject ? { path: '/work/my app' } : '/work/my app');
      expect(result).toMatchObject({ ok: false, kind: 'refused', message: expect.stringContaining('never offered') });
    }
    expect(await call(CHANNELS.detectProject, 5)).toMatchObject({ ok: false, kind: 'refused' });
    expect(await call(CHANNELS.startProject, 'nope')).toMatchObject({ ok: false, kind: 'refused' });
  });

  it('detect reads what the CLI reports for an offered folder', async () => {
    const { call, offer } = await load();
    await offer();
    const result = await call(CHANNELS.detectProject, '/work/my app');
    expect(result).toMatchObject({
      ok: true,
      data: { path: '/work/my app', stack: { primary: 'node' }, first_task: { kind: 'audit', launch: { argv: expect.any(Array) } } },
    });
  });

  it('start passes the chosen provider and type, and refuses values outside the closed sets', async () => {
    const { call, offer } = await load();
    await offer();
    const started = await call(CHANNELS.startProject, { path: '/work/my app', provider: 'codex', type: 'new' });
    expect(started).toMatchObject({
      ok: true,
      data: { bound: true, featured_commands: ['plan', 'fix', 'review', 'commit', 'pr'], detect: { project_type: { suggested: 'new' } } },
    });
    expect(started.command).toContain('--provider codex');
    expect(started.command).toContain('--type new');

    expect(await call(CHANNELS.startProject, { path: '/work/my app', provider: 'rm -rf /' })).toMatchObject({ ok: false, kind: 'refused' });
    expect(await call(CHANNELS.startProject, { path: '/work/my app', type: 'sideways' })).toMatchObject({ ok: false, kind: 'refused' });
  });
});

describe.skipIf(skip)('launchFirstTask', () => {
  it('refuses a folder that was never offered', async () => {
    const { call, launchTerminal } = await load();
    expect(await call(CHANNELS.launchFirstTask, '/work/my app')).toMatchObject({ launched: false });
    expect(launchTerminal).not.toHaveBeenCalled();
  });

  it('refuses before the CLI has reported a first task for the folder', async () => {
    const { call, offer, launchTerminal } = await load();
    await offer();
    expect(await call(CHANNELS.launchFirstTask, '/work/my app')).toMatchObject({ launched: false });
    expect(launchTerminal).not.toHaveBeenCalled();
  });

  it('opens the terminal with the argv the CLI reported, never one the renderer sent', async () => {
    const { call, offer, launchTerminal } = await load();
    await offer();
    await call(CHANNELS.startProject, { path: '/work/my app', provider: 'codex' });

    // Extra arguments a hostile renderer might add are ignored: the channel takes a folder only.
    expect(await call(CHANNELS.launchFirstTask, '/work/my app', ['sh', '-c', 'evil'])).toEqual({ launched: true });
    expect(launchTerminal).toHaveBeenCalledWith('/work/my app', ['claude', '--permission-mode', 'plan', '$devteam-audit src --report-only']);
  });
});

describe.skipIf(skip)('machine fixes', () => {
  it('run only the fix of an auto-fixable finding of the last check, by index', async () => {
    const { call, runFix } = await load();

    // Nothing offered yet.
    expect(await call(CHANNELS.runMachineFix, 0)).toMatchObject({ ran: false });

    const report = await call(CHANNELS.doctorMachine);
    expect(report).toMatchObject({ ok: true, outcome: 'findings' });
    expect(report.data.findings.map((f) => f.auto_fixable)).toEqual([true, false, false]);

    expect(await call(CHANNELS.runMachineFix, 0)).toEqual({ ran: true, succeeded: true, message: 'Done.' });
    expect(runFix).toHaveBeenCalledTimes(1);
    expect(runFix.mock.calls[0]![0]).toBe('brew install git');

    // A finding that is not auto-fixable, one with no fix, an index out of range and a non-integer.
    for (const index of [1, 2, 9, -1, 0.5, '0', null]) {
      expect(await call(CHANNELS.runMachineFix, index), String(index)).toMatchObject({ ran: false });
    }
    expect(runFix).toHaveBeenCalledTimes(1);
  });
});

describe.skipIf(skip)('the first-run flag', () => {
  it('starts not done, and completing it is written to the app’s own settings and read back', async () => {
    const { call } = await load();
    expect(await call(CHANNELS.onboardingState)).toEqual({ completed: false });
    expect(await call(CHANNELS.completeOnboarding)).toEqual({ completed: true });
    expect(await call(CHANNELS.onboardingState)).toEqual({ completed: true });
    const stored = JSON.parse(await readFile(join(dir, 'settings.json'), 'utf8')) as Record<string, unknown>;
    expect(stored['onboardingCompleted']).toBe(true);
    // The CLI path set by hand survives the write.
    expect(stored['cliPath']).toBe(FAKE_BINARY);
  });
});

describe('the preload bridge', () => {
  const invoke = vi.fn(() => Promise.resolve(undefined));
  let exposed: DevteamBridge;

  beforeEach(async () => {
    invoke.mockClear();
    vi.resetModules();
    vi.doMock('electron', () => ({
      ipcRenderer: { invoke: (...args: unknown[]) => (invoke as (...a: unknown[]) => unknown)(...args), on: vi.fn(), removeListener: vi.fn() },
      contextBridge: { exposeInMainWorld: (_name: string, api: unknown) => (exposed = api as DevteamBridge) },
    }));
    await import('../src/preload/index.js');
  });
  afterEach(() => {
    vi.doUnmock('electron');
  });

  it('declares each first-run operation on its own channel', async () => {
    await exposed.doctorMachine();
    await exposed.runMachineFix(2);
    await exposed.detectProject('/work/app');
    await exposed.launchFirstTask('/work/app');
    await exposed.onboardingState();
    await exposed.completeOnboarding();
    expect(invoke.mock.calls).toEqual([
      [CHANNELS.doctorMachine],
      [CHANNELS.runMachineFix, 2],
      [CHANNELS.detectProject, '/work/app'],
      [CHANNELS.launchFirstTask, '/work/app'],
      [CHANNELS.onboardingState],
      [CHANNELS.completeOnboarding],
    ]);
  });

  it('rebuilds a start request into plain values, dropping anything extra', async () => {
    await exposed.startProject({ path: '/work/app', provider: 'claude', type: 'new', extra: 'x' } as never);
    await exposed.startProject({ path: '/work/app' });
    expect(invoke.mock.calls).toEqual([
      [CHANNELS.startProject, { path: '/work/app', provider: 'claude', type: 'new' }],
      [CHANNELS.startProject, { path: '/work/app' }],
    ]);
  });

  it('has a distinct channel for each new operation', () => {
    const names = ['doctorMachine', 'runMachineFix', 'detectProject', 'startProject', 'launchFirstTask', 'onboardingState', 'completeOnboarding'] as const;
    const values = names.map((name) => CHANNELS[name]);
    expect(new Set(values).size).toBe(names.length);
    expect(Object.values(CHANNELS).length).toBe(new Set(Object.values(CHANNELS)).size);
  });
});
