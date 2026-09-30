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

/** Where the renderer lives; the sender check trusts a main frame at exactly this URL. */
const TRUSTED_RENDERER = { indexUrl: 'file:///app/dist/renderer/index.html', devServerOrigin: null } as const;
/** The event a handler receives from the renderer's own main frame. */
const TRUSTED = { senderFrame: { url: TRUSTED_RENDERER.indexUrl, parent: null } };

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
  readonly classifySkillPick: typeof IpcModule.classifySkillPick;
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
  const { registerIpc, validateBindRequest, validateSkillInstallRequest, classifySkillPick } = await import('../src/main/ipc.js');
  const { CHANNELS } = await import('../src/shared/api.js');
  onTestFinished(() => {
    vi.doUnmock('electron');
  });
  return { handlers, showOpenDialog, showMessageBox, registerIpc, validateBindRequest, validateSkillInstallRequest, classifySkillPick, CHANNELS };
}

async function registerAgainstFake(registerIpc: typeof IpcModule.registerIpc): Promise<void> {
  await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE_BINARY }), 'utf8');
  registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false, trustedRenderer: TRUSTED_RENDERER });
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

    const result = await handlers.get(CHANNELS.chooseProjectDirectory)?.(TRUSTED);
    expect(result).toEqual({ chosen: true, path: '/chosen/dir' });
  });

  it('reports the dialog being dismissed as chosen: false, and offers nothing', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: true, filePaths: [] });
    await registerAgainstFake(registerIpc);

    const choice = await handlers.get(CHANNELS.chooseProjectDirectory)?.(TRUSTED);
    expect(choice).toEqual({ chosen: false });

    // Nothing was offered, so bindProject must refuse any path at all — including one
    // that merely looks plausible.
    const bound = (await handlers
      .get(CHANNELS.bindProject)
      ?.(TRUSTED, { path: '/looks/plausible' })) as { readonly ok: false; readonly kind: string; readonly message: string };
    expect(bound.ok).toBe(false);
    expect(bound.kind).toBe('refused');
    expect(bound.message).toContain('never offered');
  });

  it('bindProject refuses a path this session never offered, even a real-looking one, and spawns nothing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const result = (await handlers.get(CHANNELS.bindProject)?.(TRUSTED, { path: '/repo/project-1' })) as {
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

    await handlers.get(CHANNELS.chooseProjectDirectory)?.(TRUSTED);
    const result = (await handlers.get(CHANNELS.bindProject)?.(
      TRUSTED,
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
    expect(await handlers.get(CHANNELS.projectNames)?.(TRUSTED)).toEqual({});

    await handlers.get(CHANNELS.chooseProjectDirectory)?.(TRUSTED);
    const bound = (await handlers.get(CHANNELS.bindProject)?.(
      TRUSTED,
      { path: '/chosen/dir', name: 'My Project' },
    )) as { readonly command: string; readonly ok: boolean };
    expect(bound.ok).toBe(true);
    // `name` never became argv — every fixture-answered command is asserted on its own
    // `command` elsewhere in this file; here the proof is that this exact string appears
    // nowhere in the one that did run.
    expect(bound.command).not.toContain('My Project');

    expect(await handlers.get(CHANNELS.projectNames)?.(TRUSTED)).toEqual({ 'proj-1': 'My Project' });
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('stores nothing when bindProject is called with no name', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['/chosen/dir'] });
    await registerAgainstFake(registerIpc);

    await handlers.get(CHANNELS.chooseProjectDirectory)?.(TRUSTED);
    await handlers.get(CHANNELS.bindProject)?.(TRUSTED, { path: '/chosen/dir' });

    expect(await handlers.get(CHANNELS.projectNames)?.(TRUSTED)).toEqual({});
  });

  it('a refused bind (path never offered) never reaches name storage', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const bound = (await handlers.get(CHANNELS.bindProject)?.(
      TRUSTED,
      { path: '/never/offered', name: 'Should Not Be Stored' },
    )) as { readonly ok: boolean };
    expect(bound.ok).toBe(false);

    expect(await handlers.get(CHANNELS.projectNames)?.(TRUSTED)).toEqual({});
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
      const result = (await handler(TRUSTED, ...args)) as {
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

    const unbind = (await handlers.get(CHANNELS.unbindProject)?.(TRUSTED, 'proj-1')) as { readonly command: string };
    expect(unbind.command).toContain('unbind --project-id proj-1 --json');

    const sync = (await handlers.get(CHANNELS.syncProject)?.(TRUSTED, 'proj-1')) as { readonly command: string };
    expect(sync.command).toContain('sync --project-id proj-1 --json');

    const syncAll = (await handlers.get(CHANNELS.syncAllProjects)?.(TRUSTED)) as { readonly command: string };
    expect(syncAll.command).toContain('sync --all --json');

    const plan = (await handlers.get(CHANNELS.planUpgrade)?.(TRUSTED, 'proj-1')) as { readonly command: string };
    // `upgrade` takes a path, resolved from the id — never the id itself, and never a
    // path the renderer could have supplied.
    expect(plan.command).toContain('upgrade /repo/project-1 --json');

    const apply = (await handlers.get(CHANNELS.applyUpgrade)?.(TRUSTED, 'proj-1')) as { readonly command: string };
    expect(apply.command).toContain('upgrade /repo/project-1 --apply --json');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('setPin(id, null) resolves to --release, never an empty-string version', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const released = (await handlers.get(CHANNELS.setPin)?.(TRUSTED, 'proj-1', null)) as { readonly command: string };
    expect(released.command).toContain('pin --path /repo/project-1 --release --json');
    expect(released.command).not.toContain("pin ''");
    expect(released.command).not.toContain('pin ""');

    const versioned = (await handlers.get(CHANNELS.setPin)?.(TRUSTED, 'proj-1', '3.1.0')) as { readonly command: string };
    expect(versioned.command).toContain('pin 3.1.0 --path /repo/project-1 --json');
  });

  it('refuses a non-string projectId or a version that is neither a string nor null, before any lookup', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const badId = (await handlers.get(CHANNELS.unbindProject)?.(TRUSTED, 42)) as {
      readonly ok: false;
      readonly kind: string;
      readonly durationMs: number;
    };
    expect(badId.ok).toBe(false);
    expect(badId.kind).toBe('refused');
    expect(badId.durationMs).toBe(0);

    const badVersion = (await handlers.get(CHANNELS.setPin)?.(TRUSTED, 'proj-1', 42)) as {
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

    const result = (await handlers.get(CHANNELS.projectPreferences)?.(TRUSTED, 'proj-1')) as ApiModule.OperationResult<ApiModule.ProjectPreferencesView>;
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
    const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', changes)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
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
    const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', changes)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
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
      const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', [
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
      const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', [change])) as {
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

    const declined = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', batch)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    expect(showMessageBox).toHaveBeenCalledOnce();
    expect(declined.ok).toBe(false);
    if (declined.ok) throw new Error('unreachable');
    expect(declined.kind).toBe('refused');
    expect(declined.message).toContain('not confirmed');

    showMessageBox.mockResolvedValueOnce({ response: 0, checkboxChecked: false });
    const accepted = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', batch)) as ApiModule.OperationResult<ApiModule.PreferenceUpdateReport>;
    if (!accepted.ok) throw new Error(accepted.message);
    expect(accepted.data.applied.map((change) => change.key)).toEqual(['language', 'telemetry']);

    // Turning one off needs no confirmation.
    showMessageBox.mockClear();
    const off = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', [
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
      const result = (await handlers.get(CHANNELS.updateProjectPreferences)?.(TRUSTED, 'proj-1', batch)) as {
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

    const info = (await handlers.get(CHANNELS.buildInfo)?.(TRUSTED)) as {
      readonly hasWriteActions: boolean;
      readonly mutatingCommandsRun: readonly string[];
    };
    expect(info.hasWriteActions).toBe(true);
    // Exact set and exact spelling: subcommand words, space-joined, one leaf per entry
    // — `sync` covers both the per-row sync and Sync All, because the framework
    // classifies one `("sync",)` leaf in `compat.MUTATING`, not two.
    expect([...info.mutatingCommandsRun].sort()).toEqual(
      [
        'bind',
        'doctor',
        'migrate',
        'notifications ack',
        'pin',
        'plugin config set',
        'plugin config unset',
        'plugin disable',
        'plugin enable',
        'plugin run',
        'prefs set',
        'prefs unset',
        'skills install',
        'skills remove',
        'sync',
        'unbind',
        'upgrade',
      ].sort(),
    );
  });
});

describe('environment withholds every gated command when the declaration could not be written', () => {
  it('lists every gated command in withheld, spelled as exact subcommand words', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE }), 'utf8');
    registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false, trustedRenderer: TRUSTED_RENDERER });

    // No write permission on the directory itself: `writeDeclarationFile` creates a new
    // temp file there, which fails closed rather than silently succeeding. Restored in
    // `finally`, synchronously before the test resolves — not `onTestFinished`, which
    // does not run early enough to beat the outer `afterEach`'s `rm(dir, ...)`.
    await chmod(dir, 0o500);
    try {
      const report = (await handlers.get(CHANNELS.environment)?.(TRUSTED)) as {
        readonly declaration: { readonly state: string };
        readonly withheld: readonly { readonly command: string; readonly reason: string }[];
      };
      if (report.declaration.state !== 'failed') {
        // Root, or a filesystem that does not enforce the mode, ran this test — the same
        // defensive skip `test/settings.test.ts` uses for the equivalent case.
        return;
      }
      expect([...report.withheld.map((w) => w.command)].sort()).toEqual(
        [
          'bind',
          'doctor',
          'migrate',
          'notifications ack',
          'pin',
          'plugin config set',
          'plugin config unset',
          'plugin disable',
          'plugin enable',
          'plugin run',
          'prefs set',
          'prefs unset',
          'skills install',
          'skills remove',
          'sync',
          'unbind',
          'upgrade',
        ].sort(),
      );
      for (const entry of report.withheld) {
        expect(entry.reason).toContain('schema declaration');
      }

      const unbind = (await handlers.get(CHANNELS.unbindProject)?.(TRUSTED, 'proj-1')) as {
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

// ── plugins (ADR-0019) — names checked against this project's own `plugin list` ──

describe('plugins are read, toggled, configured and run only as the project’s own list declares them', () => {
  type Failure = { readonly ok: false; readonly kind: string; readonly message: string; readonly durationMs: number };

  it.skipIf(skipOnWindowsWithoutLauncher)('lists against the resolved path, never a renderer path', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const result = (await handlers.get(CHANNELS.projectPlugins)?.(TRUSTED, 'proj-1')) as ApiModule.OperationResult<ApiModule.PluginList>;
    expect(result.command).toContain('plugin list --path /repo/project-1 --json');
    if (!result.ok) throw new Error(result.message);
    expect(result.data.plugins.map((plugin) => plugin.name)).toEqual(['demo']);

    const unknown = (await handlers.get(CHANNELS.projectPlugins)?.(TRUSTED, 'nope')) as Failure;
    expect(unknown.ok).toBe(false);
    expect(unknown.kind).toBe('refused');
    const bad = (await handlers.get(CHANNELS.projectPlugins)?.(TRUSTED, 7)) as Failure;
    expect(bad.durationMs).toBe(0);
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('enables and disables by exact command, never with --force', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const on = (await handlers.get(CHANNELS.setPluginEnabled)?.(TRUSTED, 'proj-1', 'demo', true)) as ApiModule.OperationResult<ApiModule.PluginToggleReport>;
    expect(on.command).toContain('plugin enable demo --path /repo/project-1 --json');
    expect(on.command).not.toContain('--force');
    if (!on.ok) throw new Error(on.message);
    expect(on.data.plugin.enabled).toBe(true);

    const off = (await handlers.get(CHANNELS.setPluginEnabled)?.(TRUSTED, 'proj-1', 'demo', false)) as ApiModule.OperationResult<ApiModule.PluginToggleReport>;
    expect(off.command).toContain('plugin disable demo --path /repo/project-1 --json');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('refuses a plugin the project’s list does not return, and a malformed name, before writing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const stranger = (await handlers.get(CHANNELS.setPluginEnabled)?.(TRUSTED, 'proj-1', 'ghost', true)) as Failure;
    expect(stranger.kind).toBe('refused');
    expect(stranger.message).toContain('ghost');
    const flag = (await handlers.get(CHANNELS.setPluginEnabled)?.(TRUSTED, 'proj-1', '--force', true)) as Failure;
    expect(flag.durationMs).toBe(0);
    const notBoolean = (await handlers.get(CHANNELS.setPluginEnabled)?.(TRUSTED, 'proj-1', 'demo', 'yes')) as Failure;
    expect(notBoolean.durationMs).toBe(0);
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('applies config in order with each value serialized for the CLI', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const changes = [
      { key: 'paths', action: 'set', value: ['src', 'lib'] },
      { key: 'auto', action: 'set', value: true },
      { key: 'depth', action: 'set', value: 5 },
      { key: 'mode', action: 'set', value: 'b' },
      { key: 'name', action: 'unset' },
    ];
    const result = (await handlers.get(CHANNELS.updatePluginConfig)?.(TRUSTED, 'proj-1', 'demo', changes)) as ApiModule.OperationResult<ApiModule.PluginConfigUpdateReport>;
    if (!result.ok) throw new Error(result.message);
    expect(result.data.failed).toBeNull();
    expect(result.data.applied.map((change) => change.key)).toEqual(['paths', 'auto', 'depth', 'mode', 'name']);
    expect(result.command).toBe('devteam plugin config set');

    // The exact argv of one write shows in the failure report of a batch that stops there.
    const partial = (await handlers.get(CHANNELS.updatePluginConfig)?.(TRUSTED, 'proj-1', 'demo', [
      { key: 'paths', action: 'set', value: ['src'] },
      { key: 'depth', action: 'set', value: 7 },
      { key: 'auto', action: 'set', value: true },
    ])) as ApiModule.OperationResult<ApiModule.PluginConfigUpdateReport>;
    if (!partial.ok) throw new Error(partial.message);
    expect(partial.data.applied.map((change) => change.key)).toEqual(['paths']);
    expect(partial.data.failed?.change.key).toBe('depth');
    expect(partial.data.failed?.problem.message).toContain('reserved');
    expect(partial.data.failed?.problem.command).toContain('plugin config set demo depth 7 --path /repo/project-1');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('sends a list as a JSON array string and a boolean as true/false', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    // The fixture refuses exactly these two spellings, which puts the argv of the failing
    // write — value included — in the report.
    const write = (changes: unknown) =>
      handlers.get(CHANNELS.updatePluginConfig)?.(TRUSTED, 'proj-1', 'demo', changes) as Promise<ApiModule.OperationResult<ApiModule.PluginConfigUpdateReport>>;

    const list = await write([{ key: 'paths', action: 'set', value: ['fail'] }]);
    if (!list.ok) throw new Error(list.message);
    expect(list.data.failed?.problem.command).toContain('plugin config set demo paths "[\\"fail\\"]" --path /repo/project-1');

    const flag = await write([{ key: 'auto', action: 'set', value: false }]);
    if (!flag.ok) throw new Error(flag.message);
    expect(flag.data.failed?.problem.command).toContain('plugin config set demo auto false --path /repo/project-1');

    const number = await write([{ key: 'depth', action: 'set', value: 7 }]);
    if (!number.ok) throw new Error(number.message);
    expect(number.data.failed?.problem.command).toContain('plugin config set demo depth 7 --path /repo/project-1');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('refuses an unknown key, a value that does not fit its field, and a malformed batch, before writing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const send = (name: string, changes: unknown) =>
      handlers.get(CHANNELS.updatePluginConfig)?.(TRUSTED, 'proj-1', name, changes) as Promise<Failure>;

    const unknownKey = await send('demo', [{ key: 'ghost', action: 'set', value: 'x' }]);
    expect(unknownKey.kind).toBe('refused');
    expect(unknownKey.message).toContain('ghost');
    for (const bad of [
      { key: 'depth', action: 'set', value: 99 },
      { key: 'depth', action: 'set', value: '5' },
      { key: 'paths', action: 'set', value: 'src' },
      { key: 'paths', action: 'set', value: ['a', 'a'] },
      { key: 'mode', action: 'set', value: 'z' },
      { key: 'auto', action: 'set', value: 'true' },
      { key: 'name', action: 'set', value: '--flag' },
    ]) {
      const refused = await send('demo', [bad]);
      expect(refused.kind, JSON.stringify(bad)).toBe('refused');
    }
    expect((await send('ghost', [{ key: 'paths', action: 'unset' }])).kind).toBe('refused');
    for (const malformed of ['x', [], [{ key: 'paths' }], [{ key: 'paths', action: 'set' }, { key: 'paths', action: 'unset' }], [{ key: 'bad key', action: 'unset' }]]) {
      expect((await send('demo', malformed)).durationMs, JSON.stringify(malformed)).toBe(0);
    }
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('runs only a declared action, by name, and refuses everything else', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);

    const detect = (await handlers.get(CHANNELS.runPluginAction)?.(TRUSTED, 'proj-1', 'demo', 'detect')) as ApiModule.OperationResult<ApiModule.PluginRunResult>;
    expect(detect.command).toContain('plugin run demo detect --path /repo/project-1 --json');
    if (!detect.ok) throw new Error(detect.message);
    expect(detect.data.output).toEqual({ paths: ['src'] });

    const undeclared = (await handlers.get(CHANNELS.runPluginAction)?.(TRUSTED, 'proj-1', 'demo', 'format-disk')) as Failure;
    expect(undeclared.kind).toBe('refused');
    expect(undeclared.message).toContain('format-disk');
    const stranger = (await handlers.get(CHANNELS.runPluginAction)?.(TRUSTED, 'proj-1', 'ghost', 'detect')) as Failure;
    expect(stranger.kind).toBe('refused');
    for (const args of [['proj-1', 'demo', '--x'], ['proj-1', '../demo', 'detect'], ['proj-1', 'demo', 5], [3, 'demo', 'detect']]) {
      const refused = (await handlers.get(CHANNELS.runPluginAction)?.(TRUSTED, ...args)) as Failure;
      expect(refused.durationMs, JSON.stringify(args)).toBe(0);
    }
  });
});

describe('plugin writes are withheld with the rest when the declaration could not be written', () => {
  it('refuses enable, config and run without spawning, rather than running them ungated', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE }), 'utf8');
    registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false, trustedRenderer: TRUSTED_RENDERER });

    await chmod(dir, 0o500);
    try {
      const env = (await handlers.get(CHANNELS.environment)?.(TRUSTED)) as { readonly declaration: { readonly state: string } };
      if (env.declaration.state !== 'failed') return;
      const enable = (await handlers.get(CHANNELS.setPluginEnabled)?.(TRUSTED, 'proj-1', 'demo', true)) as { readonly ok: boolean; readonly kind: string; readonly message: string };
      expect(enable.ok).toBe(false);
      expect(enable.kind).toBe('refused');
      expect(enable.message).toContain('plugin enable');
      const run = (await handlers.get(CHANNELS.runPluginAction)?.(TRUSTED, 'proj-1', 'demo', 'detect')) as { readonly ok: boolean; readonly kind: string };
      expect(run.kind).toBe('refused');
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
    const ipc = registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false, trustedRenderer: TRUSTED_RENDERER });

    const names = await Promise.all(Array.from({ length: 5 }, () => ipc.projectName('proj-1')));
    expect(names).toEqual(Array.from({ length: 5 }, () => 'project-1'));
    expect((await readFile(log, 'utf8')).trim().split('\n')).toEqual(['list']);
  });
});

// ── the IPC sender check ──────────────────────────────────────────────────────

describe('every channel refuses a sender that is not the renderer\'s main frame', () => {
  it('rejects a foreign page, a subframe and a missing frame on every registered channel', async () => {
    const { handlers, registerIpc } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const { registerNotificationIpc } = await import('../src/main/notificationIpc.js');
    registerNotificationIpc({
      trustedRenderer: TRUSTED_RENDERER,
      feed: () => ({ status: 'live', detail: null, items: [], unread: 0, paused: false }),
      markRead: () => ({ status: 'live', detail: null, items: [], unread: 0, paused: false }),
      setPaused: () => ({ status: 'live', detail: null, items: [], unread: 0, paused: false }),
      backgroundSettings: () => Promise.reject(new Error('must not run')),
      setOpenAtLogin: () => Promise.reject(new Error('must not run')),
      takePendingProject: () => null,
    });
    expect(handlers.size).toBeGreaterThan(20);

    const strangers = [
      { senderFrame: { url: 'file:///tmp/evil.html', parent: null } },
      { senderFrame: { url: TRUSTED_RENDERER.indexUrl, parent: {} } },
      { senderFrame: null },
      {},
    ];
    for (const [channel, handler] of handlers) {
      for (const stranger of strangers) {
        // Sync throw or rejection are both a refusal; what must not happen is an answer.
        await expect(Promise.resolve().then(() => handler(stranger)), channel).rejects.toThrow(/refused/);
      }
    }
  });

  it('lets the renderer\'s main frame through, with or without a hash', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const withHash = { senderFrame: { url: `${TRUSTED_RENDERER.indexUrl}#/projects`, parent: null } };
    expect(await handlers.get(CHANNELS.projectNames)?.(withHash)).toEqual({});
  });
});

// ── pin validation ────────────────────────────────────────────────────────────

describe('a pin must look like a version', () => {
  const HOSTILE = ['../x', '../../etc', '/abs/path', 'a/b', '-x', '--release', '', ' ', '1.2.3 ', ' 1.2.3', '1.2', '1.2.3/..', '1.2.3\n', 'latest', 'v1.2.3;rm'];
  const VALID = ['3.1.0', 'v3.1.0', '3.1.0-rc.1', '3.1.0+build.5', '10.20.30'];

  it('validateBindRequest refuses a hostile pin and accepts a version or null', async () => {
    const { validateBindRequest } = await loadIpc();
    const offered = new Set(['/p']);
    for (const pin of HOSTILE) {
      expect(typeof validateBindRequest({ path: '/p', pin }, offered), JSON.stringify(pin)).toBe('string');
    }
    for (const pin of VALID) {
      expect(validateBindRequest({ path: '/p', pin }, offered), pin).toMatchObject({ pin });
    }
    expect(validateBindRequest({ path: '/p', pin: null }, offered)).toMatchObject({ pin: null });
  });

  it('the setPin channel refuses a hostile version before any command is built', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    for (const version of HOSTILE) {
      const result = (await handlers.get(CHANNELS.setPin)?.(TRUSTED, 'proj-1', version)) as {
        readonly ok: boolean;
        readonly kind: string;
        readonly durationMs: number;
      };
      expect(result.ok, JSON.stringify(version)).toBe(false);
      expect(result.kind).toBe('refused');
      expect(result.durationMs).toBe(0);
    }
  });

  it('setPin in operations refuses on its own, for a caller that skipped the handler', async () => {
    const { setPin } = await import('../src/cli/operations.js');
    const result = await setPin({ binary: '/no/such/binary', cwd: dir }, '/repo/p', '../x');
    expect(result).toMatchObject({ ok: false, kind: 'refused', durationMs: 0 });
  });
});

// ── resolution caching ────────────────────────────────────────────────────────

describe('the CLI resolution', () => {
  it.skipIf(skipOnWindows)('is probed once for callers that arrive while it is in flight', async () => {
    const { registerIpc } = await loadIpc();
    const log = join(dir, 'probes.log');
    const wrapper = join(dir, 'devteam');
    await writeFile(
      wrapper,
      `#!/bin/sh\ncase " $* " in *" version "*) echo v >> '${log}'; sleep 0.3 ;; esac\nexec '${FAKE_BINARY}' "$@"\n`,
      'utf8',
    );
    await chmod(wrapper, 0o755);
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: wrapper }), 'utf8');
    const ipc = registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false, trustedRenderer: TRUSTED_RENDERER });

    const contexts = await Promise.all(Array.from({ length: 5 }, () => ipc.context()));
    expect(new Set(contexts.map((ctx) => ctx?.binary)).size).toBe(1);
    // Mutation: caching only the finished result starts one probe per caller.
    expect((await readFile(log, 'utf8')).trim().split('\n')).toHaveLength(1);
  });

  it.skipIf(skipOnWindows)('does not let a probe that started before a reset fill the cache', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    const slow = join(dir, 'slow-devteam');
    const fast = join(dir, 'fast-devteam');
    await writeFile(slow, `#!/bin/sh\ncase " $* " in *" version "*) sleep 0.8 ;; esac\nexec '${FAKE_BINARY}' "$@"\n`, 'utf8');
    await writeFile(fast, `#!/bin/sh\nexec '${FAKE_BINARY}' "$@"\n`, 'utf8');
    await chmod(slow, 0o755);
    await chmod(fast, 0o755);
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: slow }), 'utf8');
    const ipc = registerIpc({ userDataDir: dir, appVersion: '0.0.0-test', electronVersion: '39.8.10', packaged: false, trustedRenderer: TRUSTED_RENDERER });

    const stale = ipc.context();
    await new Promise((resolve) => setTimeout(resolve, 150));
    await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: fast }), 'utf8');
    await handlers.get(CHANNELS.resolveCli)?.(TRUSTED);
    await stale;
    // The reset picked `fast`; the stale probe finishing afterwards must not put `slow` back.
    expect((await ipc.context())?.binary).toBe(fast);
  });
});

// ── global skills ─────────────────────────────────────────────────────────────

describe('classifySkillPick', () => {
  it('reads an archive by extension, a SKILL.md as its folder, and anything else as a folder', async () => {
    const { classifySkillPick } = await loadIpc();
    expect(classifySkillPick('/x/pack.ZIP')).toEqual({ path: '/x/pack.ZIP', kind: 'archive' });
    expect(classifySkillPick('/x/pack.skill')).toEqual({ path: '/x/pack.skill', kind: 'archive' });
    expect(classifySkillPick('/x/my-skill/SKILL.md')).toEqual({ path: '/x/my-skill', kind: 'folder' });
    expect(classifySkillPick('/x/my-skill')).toEqual({ path: '/x/my-skill', kind: 'folder' });
  });
});

describe('validateSkillInstallRequest', () => {
  it('accepts a kind of source and closed providers, and drops a repeated provider', async () => {
    const { validateSkillInstallRequest } = await loadIpc();
    expect(
      validateSkillInstallRequest({ source: 'pick', providers: ['claude', 'claude', 'codex'], replace: false, link: true }),
    ).toEqual({ source: 'pick', providers: ['claude', 'codex'], replace: false, link: true });
  });

  it('refuses a path as the source, an unknown provider, no provider, and non-boolean toggles', async () => {
    const { validateSkillInstallRequest } = await loadIpc();
    const base = { source: 'pick', providers: ['claude'], replace: false, link: false };
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

    const listed = (await handlers.get(CHANNELS.listSkills)?.(TRUSTED, 'codex')) as { readonly command: string; readonly ok: boolean };
    expect(listed.ok).toBe(true);
    expect(listed.command).toContain('skills list --provider codex --json');

    const refused = (await handlers.get(CHANNELS.listSkills)?.(TRUSTED, '--all')) as { readonly ok: boolean; readonly kind: string };
    expect(refused.ok).toBe(false);
    expect(refused.kind).toBe('refused');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('opens the picker in the main process and sends the chosen path, never a renderer one', async () => {
    const { handlers, registerIpc, CHANNELS, showOpenDialog } = await loadIpc();
    await registerAgainstFake(registerIpc);
    showOpenDialog.mockResolvedValueOnce({ canceled: false, filePaths: ['/picked/my-skill'] });

    const answer = (await handlers.get(CHANNELS.installSkill)?.(
      TRUSTED,
      { source: 'pick', providers: ['claude', 'opencode'], replace: false, link: true },
    )) as { readonly picked: true; readonly source: string; readonly result: { readonly ok: boolean; readonly command: string } };

    expect(showOpenDialog).toHaveBeenCalledTimes(1);
    // One picker for every kind of source; on macOS it selects a file or a folder.
    const expected = process.platform === 'darwin' ? ['openFile', 'openDirectory'] : ['openFile'];
    expect(showOpenDialog.mock.calls[0]?.[0]).toMatchObject({
      properties: expected,
      filters: [{ extensions: ['zip', 'skill', 'md'] }],
    });
    expect(answer.picked).toBe(true);
    expect(answer.source).toBe('/picked/my-skill');
    expect(answer.result.ok).toBe(true);
    expect(answer.result.command).toContain(
      'skills install --source /picked/my-skill --provider claude --provider opencode --link --json',
    );
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('a picked archive is refused with --link after the picker, and never spawns', async () => {
    const { handlers, registerIpc, CHANNELS, showOpenDialog } = await loadIpc();
    await registerAgainstFake(registerIpc);
    showOpenDialog.mockResolvedValueOnce({ canceled: false, filePaths: ['/picked/pack.skill'] });

    const linked = (await handlers.get(CHANNELS.installSkill)?.(
      TRUSTED,
      { source: 'pick', providers: ['claude'], replace: false, link: true },
    )) as { readonly result: { readonly ok: boolean; readonly kind: string; readonly command: string } };
    expect(linked.result.ok).toBe(false);
    expect(linked.result.kind).toBe('refused');
    expect(linked.result.command).toBe('devteam skills install');
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('a dismissed picker runs nothing', async () => {
    const { handlers, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    const answer = await handlers.get(CHANNELS.installSkill)?.(TRUSTED, { source: 'pick', providers: ['claude'], replace: false, link: false });
    expect(answer).toEqual({ picked: false });
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('a conflict is retried against the previous source held in main, with --replace', async () => {
    const { handlers, registerIpc, CHANNELS, showOpenDialog } = await loadIpc();
    await registerAgainstFake(registerIpc);
    showOpenDialog.mockResolvedValueOnce({ canceled: false, filePaths: ['/picked/clash'] });
    const request = { providers: ['claude'], replace: false, link: false };

    const first = (await handlers.get(CHANNELS.installSkill)?.(TRUSTED, { ...request, source: 'pick' })) as {
      readonly result: { readonly ok: boolean; readonly kind?: string; readonly exitCode?: number };
    };
    expect(first.result.ok).toBe(false);
    expect(first.result.kind).toBe('conflict');

    const retry = (await handlers.get(CHANNELS.installSkill)?.(TRUSTED, { ...request, source: 'previous', replace: true })) as {
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

    const unknown = (await remove(TRUSTED, { name: 'ghost', root: 'claude' })) as { readonly ok: boolean; readonly command: string };
    expect(unknown.ok).toBe(false);
    expect(unknown.command).toBe('devteam skills list');

    const managed = (await remove(TRUSTED, { name: 'framework-owned', root: 'claude' })) as { readonly ok: boolean; readonly message: string };
    expect(managed.ok).toBe(false);
    expect(managed.message).toContain('managed');

    const flagLike = (await remove(TRUSTED, { name: '--root', root: 'claude' })) as { readonly ok: boolean; readonly kind: string };
    expect(flagLike.kind).toBe('refused');

    const removed = (await remove(TRUSTED, { name: 'alpha', root: 'claude' })) as { readonly ok: boolean; readonly command: string };
    expect(removed.ok).toBe(true);
    expect(removed.command).toContain('skills remove alpha --root claude --json');
  });
});

describe('migrate holds the bind provenance rule', () => {
  it('refuses a path the picker never offered, and a pin, before anything spawns', async () => {
    const { handlers, showOpenDialog, registerIpc, CHANNELS } = await loadIpc();
    await registerAgainstFake(registerIpc);
    for (const channel of [CHANNELS.planMigration, CHANNELS.applyMigration]) {
      const refused = (await handlers.get(channel)?.(TRUSTED, { path: '/never/offered' })) as {
        readonly ok: boolean;
        readonly kind: string;
        readonly message: string;
      };
      expect(refused.ok).toBe(false);
      expect(refused.kind).toBe('refused');
      expect(refused.message).toContain('never offered');
    }
    showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['/chosen/dir'] });
    await handlers.get(CHANNELS.chooseProjectDirectory)?.(TRUSTED);
    const pinned = (await handlers.get(CHANNELS.applyMigration)?.(TRUSTED, { path: '/chosen/dir', pin: '3.0.0' })) as {
      readonly kind: string;
      readonly message: string;
    };
    expect(pinned.kind).toBe('refused');
    expect(pinned.message).toContain('pin');
  });
});
