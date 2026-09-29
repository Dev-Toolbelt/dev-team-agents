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

import { chmod, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from 'vitest';

import type * as IpcModule from '../src/main/ipc.js';
import type * as ApiModule from '../src/shared/api.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam-write.mjs', import.meta.url));

/**
 * `registerAgainstFake` points the app's own settings file at `FAKE` as `cliPath`,
 * which `main/ipc.ts` hands to `invokeDevteam` as `binary` — spawned with `shell: false`
 * (`invoke.ts`'s policy for the real CLI too). `FAKE` is a `.mjs` script: POSIX runs it
 * via its shebang, Windows has neither shebang support nor a `.mjs` association, so the
 * spawn cannot start it. There is no seam here (as there is in `invoke.test.ts`'s
 * `fakeCli()`) to insert `node` ahead of the subcommand, because `main/ipc.ts` decides
 * that argv from `cliPath` onward, not this test. Only the tests below that need the
 * fixture to actually answer are skipped on Windows; the ones that only check the argv
 * built for a refusal, or that never call the CLI at all, are unaffected.
 */
const skipOnWindows = process.platform === 'win32';

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
  readonly registerIpc: typeof IpcModule.registerIpc;
  readonly validateBindRequest: typeof IpcModule.validateBindRequest;
  readonly CHANNELS: typeof ApiModule.CHANNELS;
}> {
  vi.resetModules();
  const handlers = new Map<string, Handler>();
  const showOpenDialog = vi.fn(() => Promise.resolve({ canceled: true, filePaths: [] as string[] }));
  vi.doMock('electron', () => ({
    ipcMain: {
      handle: (channel: string, listener: Handler) => {
        handlers.set(channel, listener);
      },
    },
    dialog: { showOpenDialog },
  }));
  const { registerIpc, validateBindRequest } = await import('../src/main/ipc.js');
  const { CHANNELS } = await import('../src/shared/api.js');
  onTestFinished(() => {
    vi.doUnmock('electron');
  });
  return { handlers, showOpenDialog, registerIpc, validateBindRequest, CHANNELS };
}

async function registerAgainstFake(registerIpc: typeof IpcModule.registerIpc): Promise<void> {
  await writeFile(join(dir, 'settings.json'), JSON.stringify({ cliPath: FAKE }), 'utf8');
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

  it.skipIf(skipOnWindows)('bindProject spawns bind for an offered path, with --provider repeated per entry', async () => {
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

// ── project_id resolution — the security property every non-bind write action rests on ──

describe('write actions resolve project_id against list, never trust a path from the renderer', () => {
  it.skipIf(skipOnWindows)('refuses an id list does not know, for unbind/sync/setPin/planUpgrade/applyUpgrade alike, and spawns nothing', async () => {
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

  it.skipIf(skipOnWindows)('resolves a known id and spawns the real write command, never the renderer’s own path', async () => {
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

  it.skipIf(skipOnWindows)('setPin(id, null) resolves to --release, never an empty-string version', async () => {
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
      ['bind', 'doctor', 'pin', 'sync', 'unbind', 'upgrade'].sort(),
    );
  });
});

describe('environment withholds every gated command when the declaration could not be written', () => {
  it('lists all six gated commands in withheld, spelled as exact subcommand words', async () => {
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
        ['bind', 'doctor', 'pin', 'sync', 'unbind', 'upgrade'].sort(),
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
