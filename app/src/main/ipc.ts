/**
 * The IPC handlers: one per named operation in `shared/api.ts`.
 *
 * Every `devteam` invocation in this app goes through here, in the main process. The
 * renderer supplies at most a catalog kind or an entry name, both validated before they
 * reach an argument vector, and never a command.
 *
 * The resolution and the handshake are cached for the session: resolution spawns a
 * `version` probe per candidate and the handshake is a second spawn, and re-running both
 * on every screen change would make the app slower for no new information. `refresh()`
 * exists for the case that matters — the user installed the CLI, or upgraded the store,
 * while the app was open — and is what the retry button calls.
 */

import { join } from 'node:path';

import { ipcMain } from 'electron';

import { DECLARATION_FILE_NAME, performHandshakeCall, writeDeclarationFile } from '../cli/declaration.js';
import {
  catalogEntry,
  catalogListing,
  catalogSummary,
  doctor,
  listProjects,
  GATED_COMMANDS,
  type CliContext,
} from '../cli/operations.js';
import { resolveDevteam, type Resolution } from '../cli/resolve.js';
import { readSettings, type AppSettings } from './settings.js';
import { CODE_SIGNED, NO_WRITE_ACTIONS } from './build-info.js';
import {
  CHANNELS,
  type BuildInfo,
  type CatalogKind,
  type CliResolution,
  type DeclarationState,
  type EnvironmentReport,
  type HandshakeView,
  type OperationResult,
} from '../shared/api.js';

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
 * call runs **ungated** — and `doctor`, the app's one `compat.MUTATING` command, would run
 * a repair against a store the framework never checked this build against. The app refuses
 * instead. The refusal is the explicit state; the silent downgrade was the defect.
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
      remedy: resolved.remedy,
    };
  }

  ipcMain.handle(CHANNELS.buildInfo, (): BuildInfo => ({
    appVersion: deps.appVersion,
    electronVersion: deps.electronVersion,
    packaged: deps.packaged,
    codeSigned: CODE_SIGNED,
    noWriteActions: NO_WRITE_ACTIONS,
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
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    // The one mutating command, and the one place the declaration is load-bearing. With no
    // declaration the framework's write gate has nothing to bind, so this would run
    // ungated; the app refuses and says why rather than running it anyway.
    if (ctx.declarationFile === undefined) {
      const declared = await ensureDeclaration();
      return undeclaredRefusal('doctor', declared.state === 'failed' ? declared.detail : 'no declaration was written');
    }
    return doctor(ctx);
  });
}
