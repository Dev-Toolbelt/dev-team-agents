/**
 * The write-action handlers in `main/ipc.ts`, and `validateBindRequest` directly.
 *
 * `electron` is mocked with the same shape `test/settings.test.ts` already uses:
 * `ipcMain.handle` captures each handler into a map, so a test can call it directly
 * without a real IPC round trip, and `dialog.showOpenDialog` is a controllable stub.
 *
 * Every registerIpc-driven test in this file points `cliPath` at
 * `fixtures/fake-devteam-write.mjs`, a second fake CLI dedicated to this file — see its
 * own header comment for why `fake-devteam.mjs`'s env-selected scenarios cannot express
 * one `registerIpc` flow (resolve, then `list`, then a write command). That fixture
 * knows one project, `proj-1` at `/repo/project-1`.
 */

import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from 'vitest';

import type * as IpcModule from '../src/main/ipc.js';
import type * as ApiModule from '../src/shared/api.js';
import { readLauncherManifest, resolveFixtureBinary } from './fixtures/launcher-manifest.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam-write.mjs', import.meta.url));

/**
 * `registerAgainstFake` points the app's own settings file at `FAKE_BINARY` as
 * `cliPath`, which `main/ipc.ts` hands to `invokeDevteam` as `binary` — spawned with
 * `shell: false` (`invoke.ts`'s policy for the real CLI too). `FAKE` is a `.mjs`
 * script: POSIX runs it via its shebang, Windows has neither shebang support nor a
 * `.mjs` association, so the spawn cannot start it. There is no seam here (as there is
 * in `invoke.test.ts`'s `fakeCli()`) to insert `node` ahead of the subcommand, because
 * `main/ipc.ts` decides that argv from `cliPath` onward, not this test. On Windows,
 * `FAKE_BINARY` is instead the compiled launcher `launcher-global-setup.ts` built for
 * this fixture, when one built successfully — this fixture selects its behaviour from
 * argv, not an environment variable, so it needs no scenario file the way
 * `resolve.test.ts`'s `plant()` does. `launcherAvailable` gates every `it.skipIf` below
 * that needs the fixture to actually answer; the ones that only check the argv built
 * for a refusal, or that never call the CLI at all, are unaffected either way.
 */
const { binary: FAKE_BINARY, available: launcherAvailable } = resolveFixtureBinary(
  FAKE,
  readLauncherManifest()?.fakeDevteamWrite,
);

const skipOnWindows = process.platform === 'win32';
const skipOnWindowsWithoutLauncher = skipOnWindows && !launcherAvailable;

let dir: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'devteam-app-ipc-'));
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

type Handler = (...args: unknown[]) => unknown;

/** A fresh mocked `electron` module and a freshly imported `ipc.js` against it. */
async function loadIpc(): Promise<{
  readonly handlers: Map<string, Handler>;
  readonly showOpenDialog: ReturnType<typeof vi.fn>;
  readonly showMessageBox: ReturnType<typeof vi.fn>;
  readonly registerIpc: typeof IpcModule.registerIpc;
  readonly validateBindRequest: typeof IpcModule.validateBindRequest;
  readonly validateSkillInstallRequest: typeof IpcModule.validateSkillInstallRequest;
  readonly CHANNELS: typeof ApiModule.CHANNELS;
}> {
  vi.resetModules();
  const handlers = new Map<string, Handler>();
  const showOpenDialog = vi.fn(() => Promise.resolve({ canceled: true, filePaths: [] as string[] }));
  // Declines by default: a test that expects a consent key to be written has to say yes.
  const showMessageBox = vi.fn(() => Promise.resolve({ response: 1, checkboxChecked: false }));
  vi.doMock('electron', () => ({
    ipcMain: {
      handle: (channel: string, listener: Handler) => {
        handlers.set(channel, listener);
      },
    },
    dialog: { showOpenDialog, showMessageBox },
  }));
  const { registerIpc, validateBindRequest, validateSkillInstallRequest } = await import('../src/main/ipc.js');
  const { CHANNELS } = await import('../src/shared/api.js');
  onTestFinished(() => {
    vi.doUnmock('electron');
  });
  return { handlers, showOpenDialog, showMessageBox, registerIpc, validateBindRequest, validateSkillInstallRequest, CHANNELS };
}

async function registerAgainstFake(registerIpc: typeof IpcModule.registerIpc): Promise<void> {
  await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE_BINARY }), 'utf8');
  registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false });
}

// ── validateBindRequest — pure, no electron, no CLI ────────────────────────────────

describe('validateBindRequest', () => {
  it('refuses a path the offered set does not contain', async () => {
    const { validateBindRequest } = await loadIpc();
    const result = validateBindRequest({ path: '/not/offered' }, new Set(['/offered']));
    expect(result).toContain('never offered');
  });

  it('accepts a path the offered set contains, with no other fields', async () => {
    const { validateBindRequest } = await loadIpc();
    const result = validateBindRequest({ path: '/offered' }, new Set(['/offered']));
    expect(result).toEqual({ path: '/offered' });
  });

  it('accepts real providers and a real mode, in the closed unions BindRequest promises', async () => {
    const { validateBindRequest } = await loadIpc();
    const result = validateBindRequest(
      { path: '/offered', providers: ['claude', 'codex'], mode: 'link', pin: '3.0.0' },
      new Set(['/offered']),
    );
    expect(result).toEqual({ path: '/offered', providers: ['claude', 'codex'], mode: 'link', pin: '3.0.0' });
  });

  it('refuses a provider outside BindProvider, even on an offered path', async () => {
    const { validateBindRequest } = await loadIpc();
    const result = validateBindRequest(
      { path: '/offered', providers: ['claude', 'not-a-real-provider'] },
      new Set(['/offered']),
    );
    expect(result).toContain('not a provider this app knows');
  });

  it('refuses a mode outside BindMode', async () => {
    const { validateBindRequest } = await loadIpc();
    const result = validateBindRequest({ path: '/offered', mode: 'symlink-farm' }, new Set(['/offered']));
    expect(result).toContain('not a bind mode this app knows');
  });

  it('accepts an explicit null pin, and refuses a non-string, non-null one', async () => {
    const { validateBindRequest } = await loadIpc();
    expect(validateBindRequest({ path: '/offered', pin: null }, new Set(['/offered']))).toEqual({
      path: '/offered',
      pin: null,
    });
    expect(validateBindRequest({ path: '/offered', pin: 42 }, new Set(['/offered']))).toContain(
      'must be a string or null',
    );
  });

  it('refuses a non-object request and one with no string path', async () => {
    const { validateBindRequest } = await loadIpc();
    expect(validateBindRequest(null, new Set())).toContain('must be an object');
    expect(validateBindRequest('a string', new Set())).toContain('must be an object');
    expect(validateBindRequest({}, new Set())).toContain('must name a string');
  });

  it('accepts a string name, and refuses a non-string one — never reaching the CLI argv either way', async () => {
    const { validateBindRequest } = await loadIpc();
    expect(validateBindRequest({ path: '/offered', name: 'My Project' }, new Set(['/offered']))).toEqual({
      path: '/offered',
      name: 'My Project',
    });
    expect(validateBindRequest({ path: '/offered', name: 42 }, new Set(['/offered']))).toContain(
      '`name` must be a string',
    );
  });
});

// ── chooseProjectDirectory and the offered set it feeds ─────────────────────────────

describe('chooseProjectDirectory and the offered-directory set', () => {
  it('records a chosen directory and returns it', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['/chosen/dir'] });
    await registerAgainstFake(registerIpc);

    const result = await handlers.get(CHANNELS.chooseProjectDirectory)?.();
    expect(result).toEqual({ chosen: true, path: '/chosen/dir' });
  });

  it('reports the dialog being dismissed as chosen: false, and offers nothing', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: true, filePaths: [] });
    await registerAgainstFake(registerIpc);

    const choice = await handlers.get(CHANNELS.chooseProjectDirectory)?.();
    expect(choice).toEqual({ chosen: false });

    // Nothing was offered, so bindProject must refuse any path at all — including one
    // that merely looks plausible.
    const bound = (await handlers
      .get(CHANNELS.bindProject)
      ?.({}, { path: '/looks/plausible' })) as { readonly ok: false; readonly kind: string; readonly message: string };
    expect(bound.ok).toBe(false);
    expect(bound.kind).toBe('refused');
    expect(bound.message).toContain('never offered');
  });

  it('bindProject refuses a path this session never offered, even a real-looking one, and spawns nothing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const result = (await handlers.get(CHANNELS.bindProject)?.({}, { path: '/repo/project-1' })) as {
      readonly ok: false;
      readonly kind: string;
      readonly command: string;
      readonly durationMs: number;
    };
    expect(result.ok).toBe(false);
    expect(result.kind).toBe('refused');
    // `durationMs: 0` and a `command` that never became a real argv are the proof no
    // process was spawned for this refusal — the same shape `run()`'s own refusal uses.
    expect(result.durationMs).toBe(0);
    expect(result.command).toBe('devteam bind');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('bindProject spawns bind for an offered path, with --provider repeated per entry', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['/chosen/dir'] });
    await registerAgainstFake(registerIpc);

    await handlers.get(CHANNELS.chooseProjectDirectory)?.();
    const result = (await handlers.get(CHANNELS.bindProject)?.(
      {},
      { path: '/chosen/dir', providers: ['claude', 'codex'], mode: 'link' },
    )) as { readonly command: string };

    expect(result.command).toContain('bind /chosen/dir --provider claude --provider codex --mode link --json');
  });
});

// ── project names — the app's own record, stored only after a successful bind ──────────

describe('bindProject stores a name only after the bind succeeds, and never in the CLI argv', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('stores the name and projectNames() reflects it afterward', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['/chosen/dir'] });
    await registerAgainstFake(registerIpc);

    // Nothing stored before the bind.
    expect(await handlers.get(CHANNELS.projectNames)?.()).toEqual({});

    await handlers.get(CHANNELS.chooseProjectDirectory)?.();
    const bound = (await handlers.get(CHANNELS.bindProject)?.(
      {},
      { path: '/chosen/dir', name: 'My Project' },
    )) as { readonly command: string; readonly ok: boolean };
    expect(bound.ok).toBe(true);
    // `name` never became argv — every fixture-answered command is asserted on its own
    // `command` elsewhere in this file; here the proof is that this exact string appears
    // nowhere in the one that did run.
    expect(bound.command).not.toContain('My Project');

    expect(await handlers.get(CHANNELS.projectNames)?.()).toEqual({ 'proj-1': 'My Project' });
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('stores nothing when bindProject is called with no name', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['/chosen/dir'] });
    await registerAgainstFake(registerIpc);

    await handlers.get(CHANNELS.chooseProjectDirectory)?.();
    await handlers.get(CHANNELS.bindProject)?.({}, { path: '/chosen/dir' });

    expect(await handlers.get(CHANNELS.projectNames)?.()).toEqual({});
  });

  it('a refused bind (path never offered) never reaches name storage', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const bound = (await handlers.get(CHANNELS.bindProject)?.(
      {},
      { path: '/never/offered', name: 'Should Not Be Stored' },
    )) as { readonly ok: boolean };
    expect(bound.ok).toBe(false);

    expect(await handlers.get(CHANNELS.projectNames)?.()).toEqual({});
  });
});

// ── project_id resolution — the security property every non-bind write action rests on ──

describe('write actions resolve project_id against list, never trust a path from the renderer', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('refuses an id list does not know, for unbind/sync/setPin/planUpgrade/applyUpgrade alike, and spawns nothing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const channels: readonly [string, readonly unknown[]][] = [
      [CHANNELS.unbindProject, ['unknown-id']],
      [CHANNELS.syncProject, ['unknown-id']],
      [CHANNELS.setPin, ['unknown-id', '1.0.0']],
      [CHANNELS.planUpgrade, ['unknown-id']],
      [CHANNELS.applyUpgrade, ['unknown-id']],
    ];
    for (const [channel, args] of channels) {
      const handler = handlers.get(channel);
      if (handler === undefined) throw new Error(`no handler registered for ${channel}`);
      const result = (await handler({}, ...args)) as {
        readonly ok: false;
        readonly kind: string;
        readonly message: string;
        readonly command: string;
      };
      expect(result.ok, channel).toBe(false);
      expect(result.kind, channel).toBe('refused');
      expect(result.message, channel).toContain('unknown-id');
      // The command this refusal names is `list` — the lookup that failed — never the
      // write command itself, which proves no write argv was ever built.
      expect(result.command, channel).toBe('devteam list');
    }
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('resolves a known id and spawns the real write command, never the renderer’s own path', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const unbind = (await handlers.get(CHANNELS.unbindProject)?.({}, 'proj-1')) as { readonly command: string };
    expect(unbind.command).toContain('unbind --project-id proj-1 --json');

    const sync = (await handlers.get(CHANNELS.syncProject)?.({}, 'proj-1')) as { readonly command: string };
    expect(sync.command).toContain('sync --project-id proj-1 --json');

    const syncAll = (await handlers.get(CHANNELS.syncAllProjects)?.({})) as { readonly command: string };
    expect(syncAll.command).toContain('sync --all --json');

    const plan = (await handlers.get(CHANNELS.planUpgrade)?.({}, 'proj-1')) as { readonly command: string };
    // `upgrade` takes a path, resolved from the id — never the id itself, and never a
    // path the renderer could have supplied.
    expect(plan.command).toContain('upgrade /repo/project-1 --json');

    const apply = (await handlers.get(CHANNELS.applyUpgrade)?.({}, 'proj-1')) as { readonly command: string };
    expect(apply.command).toContain('upgrade /repo/project-1 --apply --json');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('setPin(id, null) resolves to --release, never an empty-string version', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const released = (await handlers.get(CHANNELS.setPin)?.({}, 'proj-1', null)) as { readonly command: string };
    expect(released.command).toContain('pin --path /repo/project-1 --release --json');
    expect(released.command).not.toContain("pin ''");
    expect(released.command).not.toContain('pin ""');

    const versioned = (await handlers.get(CHANNELS.setPin)?.({}, 'proj-1', '3.1.0')) as { readonly command: string };
    expect(versioned.command).toContain('pin 3.1.0 --path /repo/project-1 --json');
  });

  it('refuses a non-string projectId or a version that is neither a string nor null, before any lookup', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const badId = (await handlers.get(CHANNELS.unbindProject)?.({}, 42)) as {
      readonly ok: false;
      readonly kind: string;
      readonly durationMs: number;
    };
    expect(badId.ok).toBe(false);
    expect(badId.kind).toBe('refused');
    expect(badId.durationMs).toBe(0);

    const badVersion = (await handlers.get(CHANNELS.setPin)?.({}, 'proj-1', 42)) as {
      readonly ok: false;
      readonly kind: string;
      readonly durationMs: number;
    };
    expect(badVersion.ok).toBe(false);
    expect(badVersion.kind).toBe('refused');
    expect(badVersion.durationMs).toBe(0);
  });
});

// ── project preferences — project layer only, keys checked against `prefs list` ──

describe('project preferences are written to the project layer only, for keys the project declares', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('reads prefs list against the resolved path, never a renderer path', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const result = (await handlers.get(CHANNELS.projectPreferences)?.({}, 'proj-1')) as ApiModule.OperationResult<ApiModule.ProjectPreferencesView>;
    expect(result.command).toContain('prefs list --path /repo/project-1 --json');
    if (!result.ok) throw new Error(result.message);
    expect(result.data.origin['model_max_tokens']).toBe('global');
    expect(result.data.unknown).toEqual(['mystery_key']);
    // The cascade without the project layer, read from the app's own non-project directory.
    expect(result.data.inherited?.['language']).toBe('pt-BR');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('applies a batch in order with --scope project, and never --scope global', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const changes = [
      { key: 'language', action: 'set', value: 'pt-BR' },
      { key: 'worktree_active', action: 'set', value: false },
      { key: 'model_max_tokens', action: 'unset' },
    ];
    const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', changes)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    if (!result.ok) throw new Error(result.message);
    expect(result.data.failed).toBeNull();
    expect(result.data.applied.map((change) => change.key)).toEqual(['language', 'worktree_active', 'model_max_tokens']);
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('stops at the first failing key and reports what was written before it', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const changes = [
      { key: 'language', action: 'set', value: 'es' },
      { key: 'model_max_tokens', action: 'set', value: 5000 },
      { key: 'worktree_active', action: 'set', value: false },
    ];
    const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', changes)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    if (!result.ok) throw new Error(result.message);
    expect(result.data.applied.map((change) => change.key)).toEqual(['language']);
    expect(result.data.failed?.change.key).toBe('model_max_tokens');
    expect(result.data.failed?.problem.message).toContain('too small');
    expect(result.data.failed?.problem.command).toContain('prefs set model_max_tokens 5000 --scope project --path /repo/project-1');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('refuses a key the project does not declare, and an unknown carried key, before writing anything', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    for (const key of ['not_a_pref', 'mystery_key']) {
      const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', [
        { key: 'language', action: 'set', value: 'es' },
        { key, action: 'set', value: 2 },
      ])) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
      expect(result.ok, key).toBe(false);
      if (result.ok) throw new Error('unreachable');
      expect(result.kind, key).toBe('refused');
      expect(result.message, key).toContain(key);
    }
  });

  it('refuses a value of the wrong type or out of range, and read-only keys, before spawning anything', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    for (const change of [
      // `_coerce` reads true/false/null before the default's type, so these would be stored.
      { key: 'model_max_tokens', action: 'set', value: true },
      { key: 'model_max_tokens', action: 'set', value: null },
      { key: 'model_max_tokens', action: 'set', value: 99_999_999 },
      { key: 'model_max_tokens', action: 'set', value: 1.5 },
      { key: 'worktree_active', action: 'set', value: 'yes' },
      { key: 'worktree_commit_action', action: 'set', value: 'push' },
      { key: 'language', action: 'set', value: null },
      { key: 'worktree_path', action: 'set', value: '../outside' },
      { key: 'transcript_multiplier', action: 'set', value: 2 },
      { key: 'transcript_multiplier', action: 'unset' },
    ]) {
      const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', [change])) as {
        readonly ok: boolean;
        readonly kind: string;
        readonly durationMs: number;
      };
      expect(result.ok, JSON.stringify(change)).toBe(false);
      expect(result.kind, JSON.stringify(change)).toBe('refused');
      expect(result.durationMs, JSON.stringify(change)).toBe(0);
    }
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('asks natively before turning a consent key on, and writes nothing on cancel', async () => {
    const { handlers, registerIpc, showMessageBox, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const batch = [
      { key: 'language', action: 'set', value: 'es' },
      { key: 'telemetry', action: 'set', value: true },
    ];

    const declined = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', batch)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    expect(showMessageBox).toHaveBeenCalledOnce();
    expect(declined.ok).toBe(false);
    if (declined.ok) throw new Error('unreachable');
    expect(declined.kind).toBe('refused');
    expect(declined.message).toContain('not confirmed');

    showMessageBox.mockResolvedValueOnce({ response: 0, checkboxChecked: false });
    const accepted = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', batch)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    if (!accepted.ok) throw new Error(accepted.message);
    expect(accepted.data.applied.map((change) => change.key)).toEqual(['language', 'telemetry']);

    // Turning one off needs no confirmation.
    showMessageBox.mockClear();
    const off = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', [
      { key: 'telemetry', action: 'set', value: false },
    ])) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    expect(off.ok).toBe(true);
    expect(showMessageBox).not.toHaveBeenCalled();
  });

  it('refuses a malformed batch before resolving the project', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    for (const batch of [
      'language=en',
      [],
      [{ key: 'language', action: 'delete' }],
      [{ key: '--scope', action: 'set', value: 'global' }],
      [{ key: 'language', action: 'set', value: '--path' }],
      [{ key: 'language', action: 'set', value: { nested: true } }],
      [
        { key: 'language', action: 'set', value: 'en' },
        { key: 'language', action: 'unset' },
      ],
    ]) {
      const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.({}, 'proj-1', batch)) as {
        readonly ok: boolean;
        readonly kind: string;
        readonly durationMs: number;
      };
      expect(result.ok, JSON.stringify(batch)).toBe(false);
      expect(result.kind, JSON.stringify(batch)).toBe('refused');
      expect(result.durationMs, JSON.stringify(batch)).toBe(0);
    }
  });
});

// ── buildInfo and environment — the surfaces the UI reads the write-action state from ──

describe('buildInfo reports write actions honestly', () => {
  it('reports hasWriteActions: true and enumerates GATED_COMMANDS, not a hardcoded list', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const info = (await handlers.get(CHANNELS.buildInfo)?.()) as {
      readonly hasWriteActions: boolean;
      readonly mutatingCommandsRun: readonly string[];
    };
    expect(info.hasWriteActions).toBe(true);
    // Exact set and exact spelling: subcommand words, space-joined, one leaf per entry
    // — `sync` covers both the per-row sync and Sync All, because the framework
    // classifies one `("sync",)` leaf in `compat.MUTATING`, not two.
    expect([...info.mutatingCommandsRun].sort()).toEqual(
      ['bind', 'doctor', 'notifications ack', 'pin', 'prefs set', 'prefs unset', 'skills install', 'skills remove', 'sync', 'unbind', 'upgrade'].sort(),
    );
  });
});

describe('environment withholds every gated command when the declaration could not be written', () => {
  it('lists every gated command in withheld, spelled as exact subcommand words', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE }), 'utf8');
    registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false });

    // No write permission on the directory itself: `writeDeclarationFile` creates a new
    // temp file there, which fails closed rather than silently succeeding. Restored in
    // `finally`, synchronously before the test resolves — not `onTestFinished`, which
    // does not run early enough to beat the outer `afterEach`'s `rm(dir, ...)`.
    await chmod(dir, 0o500);
    try {
      const report = (await handlers.get(CHANNELS.environment)?.()) as {
        readonly declaration: { readonly state: string };
        readonly withheld: readonly { readonly command: string; readonly reason: string }[];
      };
      if (report.declaration.state !== 'failed') {
        // Root, or a filesystem that does not enforce the mode, ran this test — the same
        // defensive skip `test/settings.test.ts` uses for the equivalent case.
        return;
      }
      expect([...report.withheld.map((w) => w.command)].sort()).toEqual(
        ['bind', 'doctor', 'notifications ack', 'pin', 'prefs set', 'prefs unset', 'skills install', 'skills remove', 'sync', 'unbind', 'upgrade'].sort(),
      );
      for (const entry of report.withheld) {
        expect(entry.reason).toContain('schema declaration');
      }

      const unbind = (await handlers.get(CHANNELS.unbindProject)?.({}, 'proj-1')) as {
        readonly ok: false;
        readonly kind: string;
        readonly message: string;
      };
      expect(unbind.ok).toBe(false);
      expect(unbind.kind).toBe('refused');
      expect(unbind.message).toContain('schema declaration');
    } finally {
      await chmod(dir, 0o700);
    }
  });
});

describe('projectName names a burst of notifications with one `devteam list`', () => {
  it.skipIf(skipOnWindows)('shares one listing across concurrent calls', async () => {
    const { registerIpc } = await loadIpc();
    // A wrapper that records each `list` before handing over to the fixture.
    const log = join(dir, 'calls.log');
    const wrapper = join(dir, 'devteam');
    await writeFile(
      wrapper,
      `#!/bin/sh\ncase " $* " in *" list "*) echo list >> '${log}' ;; esac\nexec '${FAKE_BINARY}' "$@"\n`,
      'utf8',
    );
    await chmod(wrapper, 0o755);
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: wrapper }), 'utf8');
    const ipc = registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false });

    const names = await Promise.all(Array.from({ length: 5 }, () => ipc.projectName('proj-1')));
    expect(names).toEqual(Array.from({ length: 5 }, () => 'project-1'));
    expect((await readFile(log, 'utf8')).trim().split('\n')).toEqual(['list']);
  });
});

// ── global skills ─────────────────────────────────────────────────────────────

describe('validateSkillInstallRequest', () => {
  it('accepts a kind of source and closed providers, and drops a repeated provider', async () => {
    const { validateSkillInstallRequest } = await loadIpc();
    expect(
      validateSkillInstallRequest({ source: 'folder', providers: ['claude', 'claude', 'codex'], replace: false, link: true }),
    ).toEqual({ source: 'folder', providers: ['claude', 'codex'], replace: false, link: true });
  });

  it('refuses a path as the source, an unknown provider, no provider, and non-boolean toggles', async () => {
    const { validateSkillInstallRequest } = await loadIpc();
    const base = { source: 'folder', providers: ['claude'], replace: false, link: false };
    expect(validateSkillInstallRequest({ ...base, source: '/etc' })).toContain('`source`');
    expect(validateSkillInstallRequest({ ...base, providers: ['vim'] })).toContain('not a provider');
    expect(validateSkillInstallRequest({ ...base, providers: [] })).toContain('at least one provider');
    expect(validateSkillInstallRequest({ ...base, replace: 'yes' })).toContain('booleans');
    expect(validateSkillInstallRequest(null)).toContain('object');
  });
});

describe('the skills handlers', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('lists with a closed provider filter and refuses anything else without spawning', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const listed = (await handlers.get(CHANNELS.listSkills)?.({}, 'codex')) as { readonly command: string; readonly ok: boolean };
    expect(listed.ok).toBe(true);
    expect(listed.command).toContain('skills list --provider codex --json');

    const refused = (await handlers.get(CHANNELS.listSkills)?.({}, '--all')) as { readonly ok: boolean; readonly kind: string };
    expect(refused.ok).toBe(false);
    expect(refused.kind).toBe('refused');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('opens the picker in the main process and sends the chosen path, never a renderer one', async () => {
    const { handlers, registerIpc, CHANNELS, showOpenDialog } = await loadIpc();
    await registerAgainstFake(registerIpc);
    showOpenDialog.mockResolvedValueOnce({ canceled: false, filePaths: ['/picked/my-skill'] });

    const answer = (await handlers.get(CHANNELS.installSkill)?.(
      {},
      { source: 'folder', providers: ['claude', 'opencode'], replace: false, link: true },
    )) as { readonly picked: true; readonly source: string; readonly result: { readonly ok: boolean; readonly command: string } };

    expect(showOpenDialog).toHaveBeenCalledTimes(1);
    expect(showOpenDialog.mock.calls[0]?.[0]).toMatchObject({ properties: ['openDirectory'] });
    expect(answer.picked).toBe(true);
    expect(answer.source).toBe('/picked/my-skill');
    expect(answer.result.ok).toBe(true);
    expect(answer.result.command).toContain(
      'skills install --source /picked/my-skill --provider claude --provider opencode --link --json',
    );
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('an archive uses a file picker limited to .zip and .skill, and refuses --link', async () => {
    const { handlers, registerIpc, CHANNELS, showOpenDialog } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const linked = (await handlers.get(CHANNELS.installSkill)?.(
      {},
      { source: 'archive', providers: ['claude'], replace: false, link: true },
    )) as { readonly result: { readonly ok: boolean; readonly kind: string } };
    expect(linked.result.ok).toBe(false);
    expect(linked.result.kind).toBe('refused');
    expect(showOpenDialog).not.toHaveBeenCalled();

    showOpenDialog.mockResolvedValueOnce({ canceled: false, filePaths: ['/picked/pack.skill'] });
    await handlers.get(CHANNELS.installSkill)?.({}, { source: 'archive', providers: ['claude'], replace: false, link: false });
    expect(showOpenDialog.mock.calls[0]?.[0]).toMatchObject({
      properties: ['openFile'],
      filters: [{ extensions: ['zip', 'skill'] }],
    });
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('a dismissed picker runs nothing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const answer = await handlers.get(CHANNELS.installSkill)?.({}, { source: 'folder', providers: ['claude'], replace: false, link: false });
    expect(answer).toEqual({ picked: false });
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('a conflict is retried against the previous source held in main, with --replace', async () => {
    const { handlers, registerIpc, CHANNELS, showOpenDialog } = await loadIpc();
    await registerAgainstFake(registerIpc);
    showOpenDialog.mockResolvedValueOnce({ canceled: false, filePaths: ['/picked/clash'] });
    const request = { providers: ['claude'], replace: false, link: false };

    const first = (await handlers.get(CHANNELS.installSkill)?.({}, { ...request, source: 'folder' })) as {
      readonly result: { readonly ok: boolean; readonly kind?: string; readonly exitCode?: number };
    };
    expect(first.result.ok).toBe(false);
    expect(first.result.kind).toBe('conflict');

    const retry = (await handlers.get(CHANNELS.installSkill)?.({}, { ...request, source: 'previous', replace: true })) as {
      readonly source: string;
      readonly result: { readonly ok: boolean; readonly command: string };
    };
    expect(showOpenDialog).toHaveBeenCalledTimes(1);
    expect(retry.source).toBe('/picked/clash');
    expect(retry.result.ok).toBe(true);
    expect(retry.result.command).toContain('--source /picked/clash --provider claude --replace --json');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('remove resolves the target against skills list, and refuses an unlisted or managed skill', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const remove = handlers.get(CHANNELS.removeSkill);
    if (remove === undefined) throw new Error('no removeSkill handler');

    const unknown = (await remove({}, { name: 'ghost', root: 'claude' })) as { readonly ok: boolean; readonly command: string };
    expect(unknown.ok).toBe(false);
    expect(unknown.command).toBe('devteam skills list');

    const managed = (await remove({}, { name: 'framework-owned', root: 'claude' })) as { readonly ok: boolean; readonly message: string };
    expect(managed.ok).toBe(false);
    expect(managed.message).toContain('managed');

    const flagLike = (await remove({}, { name: '--root', root: 'claude' })) as { readonly ok: boolean; readonly kind: string };
    expect(flagLike.kind).toBe('refused');

    const removed = (await remove({}, { name: 'alpha', root: 'claude' })) as { readonly ok: boolean; readonly command: string };
    expect(removed.ok).toBe(true);
    expect(removed.command).toContain('skills remove alpha --root claude --json');
  });
});
