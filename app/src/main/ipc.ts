/**
 * The IPC handlers: one per named operation in `shared/api.ts`.
 *
 * Every `devteam` invocation in this app goes through here, in the main process. The
 * renderer supplies at most a catalog kind, an entry name, or — for the write actions —
 * a `project_id` and, for `bind` only, a path this same process already handed back
 * through `chooseProjectDirectory`. Never a command, and never a path for anything but
 * `bind`: every other write action resolves its target from `project_id` against this
 * session's own `list` answer (`resolveProject`), so an id the registry does not know is
 * refused before an argv is built at all.
 *
 * The resolution and the handshake are cached for the session: resolution spawns a
 * `version` probe per candidate and the handshake is a second spawn, and re-running both
 * on every screen change would make the app slower for no new information. `refresh()`
 * exists for the case that matters — the user installed the CLI, or upgraded the store,
 * while the app was open — and is what the retry button calls.
 */

import { join } from 'node:path';

import { dialog, ipcMain } from 'electron';

import { DECLARATION_FILE_NAME, performHandshakeCall, writeDeclarationFile } from '../cli/declaration.js';
import {
  applyUpgrade,
  bindProject,
  catalogEntry,
  catalogListing,
  catalogSummary,
  doctor,
  listProjects,
  planUpgrade,
  setPin,
  syncAllProjects,
  syncProject,
  unbindProject,
  GATED_COMMANDS,
  type CliContext,
} from '../cli/operations.js';
import { resolveDevteam, type Resolution } from '../cli/resolve.js';
import { readSettings, writeProjectName, type AppSettings } from './settings.js';
import { CODE_SIGNED, HAS_WRITE_ACTIONS } from './build-info.js';
import {
  CHANNELS,
  type BindMode,
  type BindProvider,
  type BindReport,
  type BuildInfo,
  type CatalogKind,
  type CliResolution,
  type DeclarationState,
  type DirectoryChoice,
  type EnvironmentReport,
  type HandshakeView,
  type OperationResult,
  type PinReport,
  type SyncAllReport,
  type UnbindReport,
  type UpgradePlan,
  type UpgradeReport,
} from '../shared/api.js';

/** The closed unions `BindRequest` promises. A type is a compile-time claim and this is
 *  a process boundary — the renderer is not trusted to have sent a member of either
 *  union just because the type says it did, the same argument `catalogListing`'s handler
 *  already makes for `CatalogKind`. */
const BIND_PROVIDERS: readonly BindProvider[] = ['claude', 'opencode', 'codex'];
const BIND_MODES: readonly BindMode[] = ['auto', 'link', 'copy', 'vendored'];

/** `validateBindRequest`'s accepted shape: `BindRequest` with `path` proven offered. */
interface ValidatedBindRequest {
  readonly path: string;
  readonly providers?: readonly BindProvider[];
  readonly mode?: BindMode;
  readonly pin?: string | null;
  readonly name?: string;
}

/**
 * Validate a `bindProject` argument against the offered-directory set and the closed
 * unions, or say why it was refused.
 *
 * Exported for direct testing: this is the one function standing between "the renderer
 * can ask for any argv" and the security property `chooseProjectDirectory`'s doc comment
 * promises. It does not know whether `path` is *also* a bound project already; only that
 * this session's main process handed it back once.
 */
export function validateBindRequest(
  request: unknown,
  offered: ReadonlySet<string>,
): ValidatedBindRequest | string {
  if (request === null || typeof request !== 'object') return 'a bind request must be an object';
  const raw = request as Record<string, unknown>;
  if (typeof raw['path'] !== 'string') return 'a bind request must name a string `path`';
  const path = raw['path'];
  if (!offered.has(path)) {
    return 'this app never offered that directory; call chooseProjectDirectory first';
  }

  let providers: BindProvider[] | undefined;
  if (raw['providers'] !== undefined) {
    if (!Array.isArray(raw['providers'])) return '`providers` must be an array';
    providers = [];
    for (const entry of raw['providers']) {
      if (!BIND_PROVIDERS.includes(entry as BindProvider)) {
        return `\`${String(entry)}\` is not a provider this app knows`;
      }
      providers.push(entry as BindProvider);
    }
  }

  let mode: BindMode | undefined;
  const rawMode = raw['mode'];
  if (rawMode !== undefined) {
    if (!BIND_MODES.includes(rawMode as BindMode)) {
      return `\`${JSON.stringify(rawMode)}\` is not a bind mode this app knows`;
    }
    mode = rawMode as BindMode;
  }

  let pin: string | null | undefined;
  const rawPin = raw['pin'];
  if (rawPin !== undefined) {
    if (rawPin !== null && typeof rawPin !== 'string') return '`pin` must be a string or null';
    pin = rawPin;
  }

  // `name` never reaches the CLI's argv — see `BindRequest.name`'s doc comment in
  // `shared/api.ts`. It is validated here like every other field this boundary is not
  // trusted to have sent honestly, and stored by the caller only after `bindProject`
  // itself has succeeded.
  let name: string | undefined;
  const rawName = raw['name'];
  if (rawName !== undefined) {
    if (typeof rawName !== 'string') return '`name` must be a string';
    name = rawName;
  }

  return {
    path,
    ...(providers !== undefined ? { providers } : {}),
    ...(mode !== undefined ? { mode } : {}),
    ...(pin !== undefined ? { pin } : {}),
    ...(name !== undefined ? { name } : {}),
  };
}

export interface IpcDependencies {
  readonly userDataDir: string;
  readonly appVersion: string;
  readonly electronVersion: string;
  readonly packaged: boolean;
}

const NO_CLI: OperationResult<never> = {
  ok: false,
  kind: 'unavailable',
  message: 'No `devteam` CLI was found on this host.',
  hint: 'Install it with Homebrew, or point the app at one with DEVTEAM_CLI_PATH.',
  exitCode: null,
  command: 'devteam',
  durationMs: 0,
};

/**
 * The problem returned instead of running a mutating command the app cannot declare for.
 *
 * ADR-0014's gate binds a client that declares itself, so with no declaration file every
 * call runs **ungated** — and any of this build's `compat.MUTATING` commands (`doctor`,
 * and now `bind`/`unbind`/`sync`/`pin`/`upgrade`) would run against a store the framework
 * never checked this build against. The app refuses instead. The refusal is the explicit
 * state; the silent downgrade was the defect.
 */
function undeclaredRefusal(command: string, detail: string): OperationResult<never> {
  return {
    ok: false,
    kind: 'refused',
    message: `\`devteam ${command}\` can change the store, and this app could not write the schema declaration that lets the framework refuse it. It was not run.`,
    hint: `The declaration file could not be written: ${detail}. Fix that — a read-only or full user-data directory is the usual cause — then retry.`,
    exitCode: null,
    command: `devteam ${command}`,
    durationMs: 0,
  };
}

export function registerIpc(deps: IpcDependencies): void {
  let resolution: Resolution | null = null;
  let declaration: DeclarationState | null = null;
  let settings: AppSettings | null = null;
  let handshake: OperationResult<HandshakeView> | null = null;

  /**
   * The directory every child is given, as `cwd` and as `--path`.
   *
   * The app's own user-data directory, chosen because it is the one directory the app owns,
   * it always exists, and it is not a bound project — so the project answer is the same on
   * every launch. Nothing used to set `cwd` at all, so the child inherited the main
   * process's: `app/` under `npm start`, `/` for a Finder launch, and a different
   * `project_id` from each.
   */
  const workingDirectory = deps.userDataDir;

  async function ensureSettings(): Promise<AppSettings> {
    if (settings !== null) return settings;
    settings = await readSettings(deps.userDataDir);
    return settings;
  }

  async function ensureResolution(): Promise<Resolution> {
    if (resolution !== null) return resolution;
    const current = await ensureSettings();
    resolution = await resolveDevteam({ configuredPath: current.cliPath });
    return resolution;
  }

  /** Write the declaration once, and remember whether it worked either way. */
  async function ensureDeclaration(): Promise<DeclarationState> {
    if (declaration !== null) return declaration;
    try {
      declaration = { state: 'written', path: await writeDeclarationFile(deps.userDataDir) };
    } catch (error) {
      // Not silent, and not merely "reported on the compat screen": the state is a field
      // the `environment` channel returns, the header renders it, and the gated command
      // is withheld while it holds. Leaving `declarationFile` null and calling that
      // visibility was the defect — no field of any view model carried it.
      declaration = {
        state: 'failed',
        path: join(deps.userDataDir, DECLARATION_FILE_NAME),
        detail: String(error),
      };
    }
    return declaration;
  }

  async function context(): Promise<CliContext | null> {
    const resolved = await ensureResolution();
    if (!resolved.found) return null;
    const declared = await ensureDeclaration();
    return {
      binary: resolved.cli.path,
      cwd: workingDirectory,
      ...(declared.state === 'written' ? { declarationFile: declared.path } : {}),
    };
  }

  /**
   * Directories `chooseProjectDirectory` has handed back this session. `bindProject`
   * refuses any path that is not in it — see that channel's doc comment in
   * `shared/api.ts`. Session-lifetime and in memory only: there is nothing to persist,
   * and persisting it would only widen the window in which a stale offer is honoured.
   */
  const offeredDirectories = new Set<string>();

  /**
   * A context for a `compat.MUTATING` command, or the problem to return instead.
   *
   * Every gated command needs the same two checks context() does not make on its own —
   * a resolvable CLI, and a declaration that was actually written — so this is the one
   * place both are made, rather than each handler repeating the `doctor` handler's
   * pre-write-action shape by hand.
   */
  async function gatedContext(
    command: string,
  ): Promise<{ readonly ready: true; readonly ctx: CliContext } | { readonly ready: false; readonly problem: OperationResult<never> }> {
    const ctx = await context();
    if (ctx === null) return { ready: false, problem: NO_CLI };
    if (ctx.declarationFile === undefined) {
      const declared = await ensureDeclaration();
      return {
        ready: false,
        problem: undeclaredRefusal(command, declared.state === 'failed' ? declared.detail : 'no declaration was written'),
      };
    }
    return { ready: true, ctx };
  }

  /**
   * Resolve a `project_id` the renderer named into the path this session's own `list`
   * answer says it lives at — never the renderer's own claim. An id `list` does not
   * return is refused here, before any write-action argv is built; see `GATED_COMMANDS`'s
   * doc comment for why this is the security property the whole write surface rests on.
   * `bind` is the one write action with no existing project to resolve, and is handled
   * the other way round, through `offeredDirectories` above.
   */
  async function resolveProject(projectId: string): Promise<{ readonly path: string } | OperationResult<never>> {
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    const listing = await listProjects(ctx);
    if (!listing.ok) return listing;
    const found = listing.data.projects.find((project) => project.project_id === projectId);
    if (found === undefined) {
      return {
        ok: false,
        kind: 'refused',
        message: `\`${projectId}\` is not a project this app's registry knows about.`,
        exitCode: null,
        command: 'devteam list',
        durationMs: 0,
      };
    }
    return { path: found.path };
  }

  /** A write channel was called with an argument that does not even typecheck as sent. */
  function refusedBadArgument(command: string): OperationResult<never> {
    return {
      ok: false,
      kind: 'refused',
      message: `\`devteam ${command}\` was not given an argument this app recognises.`,
      exitCode: null,
      command: `devteam ${command}`,
      durationMs: 0,
    };
  }

  function toCliResolution(resolved: Resolution): CliResolution {
    if (resolved.found) {
      return {
        found: true,
        cli: {
          path: resolved.cli.path,
          source: resolved.cli.source,
          sourceDetail: resolved.cli.sourceDetail,
          storeVersion: resolved.cli.storeVersion,
          jsonContract: resolved.cli.compat.jsonContract,
          minAppVersion: resolved.cli.compat.minAppVersion,
          storeSchemas: resolved.cli.compat.storeSchemas,
        },
        rejected: resolved.rejected,
      };
    }
    return {
      found: false,
      rejected: resolved.rejected,
      searchedCount: resolved.searched.length,
      searchedBySource: resolved.searchedBySource,
      remedy: resolved.remedy,
    };
  }

  ipcMain.handle(CHANNELS.buildInfo, (): BuildInfo => ({
    appVersion: deps.appVersion,
    electronVersion: deps.electronVersion,
    packaged: deps.packaged,
    codeSigned: CODE_SIGNED,
    hasWriteActions: HAS_WRITE_ACTIONS,
    // Derived from the same table `run()` enforces, not restated — a command added to
    // `GATED_COMMANDS` without a corresponding handler below would still show up here
    // honestly; one added to a hardcoded list here could silently claim a capability
    // the app does not actually have a handler for.
    mutatingCommandsRun: GATED_COMMANDS.map((command) => command.join(' ')),
  }));

  ipcMain.handle(CHANNELS.environment, async (): Promise<EnvironmentReport> => {
    const declared = await ensureDeclaration();
    const current = await ensureSettings();
    return {
      declaration: declared,
      settings: {
        path: current.path,
        problem: current.problem ?? null,
        cliPathConfigured: current.cliPath !== undefined,
      },
      workingDirectory,
      withheld:
        declared.state === 'failed'
          ? GATED_COMMANDS.map((command) => ({
              command: command.join(' '),
              reason: 'it can change the store and no schema declaration could be written',
            }))
          : [],
    };
  });

  ipcMain.handle(CHANNELS.resolveCli, async (): Promise<CliResolution> => {
    // A call to this channel is the user asking again, so it re-resolves. Everything
    // downstream is invalidated with it — a different CLI is a different verdict. The
    // settings file and the declaration are re-read too: a user who is retrying has
    // usually just edited one of them, and reusing a cached failure would hide the fix.
    resolution = null;
    handshake = null;
    settings = null;
    declaration = null;
    return toCliResolution(await ensureResolution());
  });

  ipcMain.handle(CHANNELS.handshake, async (): Promise<OperationResult<HandshakeView>> => {
    if (handshake !== null) return handshake;
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    // The real argument vector and the real duration. They were fabricated as
    // `'devteam compat --json'` and `0`, which the UI then rendered as fact.
    const call = await performHandshakeCall({ binary: ctx.binary, cwd: ctx.cwd });
    handshake = {
      ok: true,
      outcome: 'success',
      data: call.view,
      command: call.command,
      durationMs: call.durationMs,
    };
    return handshake;
  });

  ipcMain.handle(CHANNELS.listProjects, async () => {
    const ctx = await context();
    return ctx === null ? NO_CLI : listProjects(ctx);
  });

  // Spawns nothing — reads this app's own settings file. See `BindRequest.name`'s
  // comment above for why this channel is not in `CHANNELS`.
  ipcMain.handle(CHANNELS.projectNames, async (): Promise<Readonly<Record<string, string>>> => {
    const current = await ensureSettings();
    return current.projectNames;
  });

  ipcMain.handle(CHANNELS.catalogSummary, async () => {
    const ctx = await context();
    return ctx === null ? NO_CLI : catalogSummary(ctx);
  });

  ipcMain.handle(CHANNELS.catalogListing, async (_event, kind: unknown) => {
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    // The renderer names a kind, not a command. An unrecognised one is refused here
    // rather than forwarded, so nothing the renderer sends can become an argv entry
    // that was not on this list.
    if (kind !== 'agents' && kind !== 'skills' && kind !== 'commands') {
      return {
        ok: false,
        kind: 'refused',
        message: `unknown catalog kind: ${String(kind)}`,
        exitCode: null,
        command: 'devteam catalog',
        durationMs: 0,
      };
    }
    return catalogListing(ctx, kind satisfies CatalogKind);
  });

  ipcMain.handle(CHANNELS.catalogEntry, async (_event, name: unknown) => {
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    return catalogEntry(ctx, typeof name === 'string' ? name : '');
  });

  ipcMain.handle(CHANNELS.doctor, async () => {
    // With no declaration the framework's write gate has nothing to bind, so this would
    // run ungated; the app refuses and says why rather than running it anyway.
    const gated = await gatedContext('doctor');
    if (!gated.ready) return gated.problem;
    return doctor(gated.ctx);
  });

  // ── write actions ────────────────────────────────────────────────────────────

  ipcMain.handle(CHANNELS.chooseProjectDirectory, async (): Promise<DirectoryChoice> => {
    const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
    const path = result.filePaths[0];
    if (result.canceled || path === undefined) return { chosen: false };
    offeredDirectories.add(path);
    return { chosen: true, path };
  });

  ipcMain.handle(CHANNELS.bindProject, async (_event, request: unknown): Promise<OperationResult<BindReport>> => {
    const validated = validateBindRequest(request, offeredDirectories);
    if (typeof validated === 'string') {
      return {
        ok: false,
        kind: 'refused',
        message: validated,
        exitCode: null,
        command: 'devteam bind',
        durationMs: 0,
      };
    }
    const gated = await gatedContext('bind');
    if (!gated.ready) return gated.problem;
    const result = await bindProject(gated.ctx, validated.path, {
      ...(validated.providers !== undefined ? { providers: validated.providers } : {}),
      ...(validated.mode !== undefined ? { mode: validated.mode } : {}),
      ...(validated.pin !== undefined ? { pin: validated.pin } : {}),
    });
    if (result.ok && validated.name !== undefined) {
      try {
        await writeProjectName(deps.userDataDir, result.data.project_id, validated.name);
        // The cached copy `ensureSettings()` holds is now stale; drop it so the next
        // `projectNames()` call sees the name that was just written rather than the
        // snapshot read before this bind ran.
        settings = null;
      } catch {
        // Best-effort: this app's own local convenience record, not the framework's
        // write. A bind that succeeded must be reported as succeeded even when naming it
        // afterward failed — see `BindRequest.name`'s doc comment in `shared/api.ts`.
      }
    }
    return result;
  });

  ipcMain.handle(CHANNELS.unbindProject, async (_event, projectId: unknown): Promise<OperationResult<UnbindReport>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('unbind');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('unbind');
    if (!gated.ready) return gated.problem;
    return unbindProject(gated.ctx, projectId);
  });

  ipcMain.handle(CHANNELS.syncProject, async (_event, projectId: unknown): Promise<OperationResult<BindReport>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('sync');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('sync');
    if (!gated.ready) return gated.problem;
    return syncProject(gated.ctx, projectId);
  });

  ipcMain.handle(CHANNELS.syncAllProjects, async (): Promise<OperationResult<SyncAllReport>> => {
    const gated = await gatedContext('sync');
    if (!gated.ready) return gated.problem;
    return syncAllProjects(gated.ctx);
  });

  ipcMain.handle(
    CHANNELS.setPin,
    async (_event, projectId: unknown, version: unknown): Promise<OperationResult<PinReport>> => {
      if (typeof projectId !== 'string') return refusedBadArgument('pin');
      // `null` is a release; anything else must be a non-empty string — never the empty
      // string `setPin(id, null)` must not become. See `setPin`'s own doc comment.
      if (version !== null && typeof version !== 'string') return refusedBadArgument('pin');
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('pin');
      if (!gated.ready) return gated.problem;
      return setPin(gated.ctx, resolved.path, version);
    },
  );

  ipcMain.handle(CHANNELS.planUpgrade, async (_event, projectId: unknown): Promise<OperationResult<UpgradePlan>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('upgrade');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('upgrade');
    if (!gated.ready) return gated.problem;
    return planUpgrade(gated.ctx, resolved.path);
  });

  ipcMain.handle(CHANNELS.applyUpgrade, async (_event, projectId: unknown): Promise<OperationResult<UpgradeReport>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('upgrade');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('upgrade');
    if (!gated.ready) return gated.problem;
    return applyUpgrade(gated.ctx, resolved.path);
  });
}
