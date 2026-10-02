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

import { realpath } from 'node:fs/promises';
import { basename, isAbsolute, join, relative, sep } from 'node:path';

import { dialog, ipcMain, type NativeImage } from 'electron';

import { DECLARATION_FILE_NAME, performHandshakeCall, writeDeclarationFile } from '../cli/declaration.js';
import {
  applyUpgrade,
  applyMigration,
  planMigration,
  type MigrateOptions,
  bindProject,
  catalogEntry,
  catalogListing,
  catalogSummary,
  doctor,
  installSkill,
  credentialsLocalInit,
  credentialsLocalPatch,
  credentialsLocalShow,
  credentialsOpsProblem,
  isCredentialsOps,
  CREDENTIALS_HASH,
  integrationConfigSet,
  integrationConfigUnset,
  integrationConnect,
  integrationDisconnect,
  integrationFieldsProblem,
  integrationList,
  integrationResources,
  integrationTest,
  integrationTokenProblem,
  listProjects,
  listSkills,
  pinProblem,
  planUpgrade,
  pluginConfigSet,
  pluginConfigUnset,
  pluginDisable,
  pluginEnable,
  pluginList,
  pluginRun,
  preferenceArgumentProblem,
  prefsList,
  prefsSet,
  prefsUnset,
  removeSkill,
  setPin,
  showSkill,
  skillTargetProblem,
  syncAllProjects,
  syncProject,
  unbindProject,
  GATED_COMMANDS,
  type CliContext,
} from '../cli/operations.js';
import { resolveDevteam, type Resolution } from '../cli/resolve.js';
import {
  PLUGIN_ACTION_ID,
  PLUGIN_CONFIG_KEY,
  PLUGIN_NAME,
  isEditable,
  pluginValueProblem,
  serializePluginValue,
} from '../shared/pluginRules.js';
import { CONSENT_KEYS, PREFERENCE_RULES, valueProblem } from '../shared/preferenceRules.js';
import { trustedHandler, type RendererTarget } from './security.js';
import { readSettings, writeProjectFolders, writeProjectName, type AppSettings } from './settings.js';
import { projectFoldersProblem, sanitizeProjectFolders, type ProjectFolders, type ProjectFoldersAnswer } from '../shared/projectFolders.js';
import { PROVIDERS } from '../shared/providers.js';
import { CODE_SIGNED, HAS_WRITE_ACTIONS } from './build-info.js';
import {
  type CliInstallResult,
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
  type IntegrationConfigWrite,
  type IntegrationConnectReport,
  type IntegrationDisconnectReport,
  type CredentialsLocalView,
  type IntegrationList,
  type IntegrationResources,
  type IntegrationTestReport,
  type PluginConfigChange,
  type PluginConfigField,
  type PluginConfigUpdateReport,
  type PluginConfigValue,
  type PluginList,
  type PluginRunResult,
  type PluginToggleReport,
  type PluginView,
  type PreferenceChange,
  type PreferenceUpdateReport,
  type PreferenceValue,
  type ProjectPathPick,
  type ProjectPreferencesView,
  type SkillDetail,
  type SkillInstallAnswer,
  type SkillList,
  type SkillProvider,
  type SkillProviderFilter,
  type SkillRemoveReport,
  type SyncAllReport,
  type UnbindReport,
  type MigrationPlan,
  type MigrationReport,
  type UpgradePlan,
  type UpgradeReport,
} from '../shared/api.js';

/** The closed unions `BindRequest` promises. A type is a compile-time claim and this is
 *  a process boundary — the renderer is not trusted to have sent a member of either
 *  union just because the type says it did, the same argument `catalogListing`'s handler
 *  already makes for `CatalogKind`. */
const BIND_PROVIDERS: readonly BindProvider[] = PROVIDERS;
const BIND_MODES: readonly BindMode[] = ['auto', 'link', 'copy', 'vendored'];

const SKILL_PROVIDERS: readonly SkillProvider[] = PROVIDERS;
const SKILL_FILTERS: readonly SkillProviderFilter[] = ['all', ...SKILL_PROVIDERS];

/** The extensions `skills install` accepts as an archive. */
const SKILL_ARCHIVE_EXTENSIONS = ['zip', 'skill'];

/**
 * One native picker for every kind of source. macOS lets a single dialog select a file or
 * a folder. Windows and Linux cannot: Electron shows a folder picker when both are asked
 * for, which would hide archives. There the picker selects files only, and the skill's own
 * `SKILL.md` stands for its folder.
 */
function skillPickerOptions(platform: NodeJS.Platform): Electron.OpenDialogOptions {
  return {
    title: 'Select a skill folder, its SKILL.md, or a .zip/.skill archive',
    properties: platform === 'darwin' ? ['openFile', 'openDirectory'] : ['openFile'],
    filters: [{ name: 'Skill (folder, SKILL.md, .zip, .skill)', extensions: [...SKILL_ARCHIVE_EXTENSIONS, 'md'] }],
  };
}

/**
 * What a picked path is, from its name alone. An archive by extension; a `.md` file goes
 * to the CLI **as the file**, because only the CLI can tell a skill's own folder (the
 * `SKILL.md`'s folder carries the skill's name) from a `SKILL.md` lying loose in, say,
 * Downloads — which must install that one file, never the whole folder around it.
 * Anything else was a folder. Exported for direct testing.
 */
export function classifySkillPick(path: string): { readonly path: string; readonly kind: 'folder' | 'archive' | 'file' } {
  const lower = path.toLowerCase();
  if (SKILL_ARCHIVE_EXTENSIONS.some((ext) => lower.endsWith(`.${ext}`))) return { path, kind: 'archive' };
  if (lower.endsWith('.md')) return { path, kind: 'file' };
  return { path, kind: 'folder' };
}

/**
 * An `installSkill` request, rebuilt from `unknown`, or why it was refused. Exported for
 * direct testing. The renderer names a *kind* of source, never a path: the picker runs in
 * this process and the path it returns never crosses back as an input.
 */
export function validateSkillInstallRequest(request: unknown):
  | { readonly source: 'pick' | 'previous'; readonly providers: readonly SkillProvider[]; readonly replace: boolean; readonly link: boolean }
  | string {
  if (request === null || typeof request !== 'object') return 'an install request must be an object';
  const raw = request as Record<string, unknown>;
  const source = raw['source'];
  if (source !== 'pick' && source !== 'previous') {
    return '`source` must be pick or previous';
  }
  if (!Array.isArray(raw['providers']) || raw['providers'].length === 0) return 'choose at least one provider';
  const providers: SkillProvider[] = [];
  for (const entry of raw['providers']) {
    if (!SKILL_PROVIDERS.includes(entry as SkillProvider)) return `\`${String(entry)}\` is not a provider this app knows`;
    if (!providers.includes(entry as SkillProvider)) providers.push(entry as SkillProvider);
  }
  if (typeof raw['replace'] !== 'boolean' || typeof raw['link'] !== 'boolean') {
    return '`replace` and `link` must be booleans';
  }
  return { source, providers, replace: raw['replace'], link: raw['link'] };
}

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
    if (rawPin !== null) {
      const problem = pinProblem(rawPin);
      if (problem !== null) return problem;
    }
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
  /** Who may call any channel below; see `trustedHandler` in `security.ts`. */
  readonly trustedRenderer: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>;
  /** Told every time the renderer re-resolves the CLI — the About panel shows the answer. */
  readonly onResolved?: (resolution: CliResolution) => void;
  /** The icon native dialogs show; `null` (or absent) leaves the platform's default. */
  readonly dialogIcon?: NativeImage | null;
  /** "Install the CLI" (ADR-0028, `cliInstaller.ts`); absent means the action is unsupported. */
  readonly installCli?: () => Promise<CliInstallResult>;
}

const NO_CLI: OperationResult<never> = {
  ok: false,
  kind: 'unavailable',
  message: 'No `devteam` CLI was found on this host.',
  hint: 'Install it with the devteam installer, or point the app at one with DEVTEAM_CLI_PATH.',
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

/**
 * What the rest of the main process needs from the IPC layer, so nothing resolves the CLI
 * or writes the declaration a second time: the notification center runs `watch` and
 * `notifications ack` with exactly the binary, working directory and declaration every
 * channel below uses.
 */
export interface IpcHandle {
  readonly context: () => Promise<CliContext | null>;
  /** `context()` for a command in `compat.MUTATING`, or `null` when it must not run ungated. */
  readonly gatedContext: (command: string) => Promise<CliContext | null>;
  /** The app's name for a project, else its directory's basename — never the UUID. */
  readonly projectName: (projectId: string) => Promise<string>;
}

/** Folders a plugin path setting must never point into: version control and the harness's own state. */
const FORBIDDEN_PROJECT_DIRS = ['.git', '.dev-team-agents'];

/**
 * Turn the picker's absolute answer into a project-relative POSIX path, or say why not.
 * Both sides go through `realpath`, so a symlink inside the project that leads out of it
 * is judged by where it lands, and only the relative path ever leaves the main process.
 */
export async function projectRelativeChoice(realRoot: string, chosen: string): Promise<ProjectPathPick> {
  const real = await realpath(chosen).catch(() => null);
  if (real === null) return { picked: false, refused: 'That location could not be read.' };
  const rel = relative(realRoot, real);
  if (rel === '') return { picked: false, refused: 'Choose something inside the project, not the project folder itself.' };
  if (rel === '..' || rel.startsWith(`..${sep}`) || isAbsolute(rel)) {
    return { picked: false, refused: 'That location is outside the project. Choose something inside it.' };
  }
  const parts = rel.split(sep);
  if (parts.some((part) => FORBIDDEN_PROJECT_DIRS.includes(part))) {
    return { picked: false, refused: 'That location is inside .git or .dev-team-agents, which a setting cannot point to.' };
  }
  return { picked: true, path: parts.join('/') };
}

export function registerIpc(deps: IpcDependencies): IpcHandle {
  // The one door to `ipcMain.handle`: every channel in this file goes through it, so a new
  // handler cannot forget the sender check by being written the plain way.
  const handle = (channel: string, listener: Parameters<typeof trustedHandler>[1]): void =>
    ipcMain.handle(channel, trustedHandler(deps.trustedRenderer, listener));

  let resolution: Resolution | null = null;
  let declaration: DeclarationState | null = null;
  let settings: AppSettings | null = null;
  /**
   * The resolution in flight, shared by every caller that arrives while it runs. Caching
   * only the finished result let the renderer's first burst of channels (environment,
   * handshake, list…) each start their own probe of every candidate CLI.
   */
  let resolving: Promise<Resolution> | null = null;
  /**
   * Bumped by every reset. A read or probe that started before a reset finishes against
   * the old settings and the old CLI, so it may answer its own callers but must not fill
   * the cache the reset just emptied.
   */
  let generation = 0;
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
    const started = generation;
    const read = await readSettings(deps.userDataDir);
    if (started === generation) settings = read;
    return read;
  }

  async function ensureResolution(): Promise<Resolution> {
    if (resolution !== null) return resolution;
    if (resolving !== null) return resolving;
    const started = generation;
    const attempt = (async (): Promise<Resolution> => {
      try {
        const current = await ensureSettings();
        const resolved = await resolveDevteam({ configuredPath: current.cliPath });
        if (started === generation) resolution = resolved;
        return resolved;
      } finally {
        if (started === generation) resolving = null;
      }
    })();
    resolving = attempt;
    return attempt;
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
  /** A request refused before anything was spawned, carrying the validator's own reason. */
  function refusedRequest(command: string, message: string): OperationResult<never> {
    return { ok: false, kind: 'refused', message, exitCode: null, command: `devteam ${command}`, durationMs: 0 };
  }

  function migrateOptions(validated: ValidatedBindRequest): MigrateOptions {
    return {
      ...(validated.providers !== undefined ? { providers: validated.providers } : {}),
      ...(validated.mode !== undefined ? { mode: validated.mode } : {}),
    };
  }

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

  handle(CHANNELS.buildInfo, (): BuildInfo => ({
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

  handle(CHANNELS.environment, async (): Promise<EnvironmentReport> => {
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

  handle(CHANNELS.resolveCli, async (): Promise<CliResolution> => {
    // A call to this channel is the user asking again, so it re-resolves. Everything
    // downstream is invalidated with it — a different CLI is a different verdict. The
    // settings file and the declaration are re-read too: a user who is retrying has
    // usually just edited one of them, and reusing a cached failure would hide the fix.
    generation += 1;
    resolution = null;
    resolving = null;
    handshake = null;
    settings = null;
    declaration = null;
    const resolved = toCliResolution(await ensureResolution());
    deps.onResolved?.(resolved);
    return resolved;
  });

  // The renderer calls `resolveCli` afterwards, which is the reset: a CLI that did not
  // exist a moment ago invalidates everything the empty resolution cached.
  handle(CHANNELS.installCli, async (): Promise<CliInstallResult> =>
    deps.installCli === undefined
      ? { outcome: 'unsupported', message: 'This build cannot install the CLI on this platform.' }
      : deps.installCli(),
  );

  handle(CHANNELS.handshake, async (): Promise<OperationResult<HandshakeView>> => {
    if (handshake !== null) return handshake;
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    // The real argument vector and the real duration. They were fabricated as
    // `'devteam compat --json'` and `0`, which the UI then rendered as fact.
    const started = generation;
    const call = await performHandshakeCall({ binary: ctx.binary, cwd: ctx.cwd });
    const verdict: OperationResult<HandshakeView> = {
      ok: true,
      outcome: 'success',
      data: call.view,
      command: call.command,
      durationMs: call.durationMs,
    };
    // A `resolveCli` reset while this call ran means it answered for the previous CLI:
    // return it to its caller, but do not let it stand as the new CLI's verdict.
    if (started === generation) handshake = verdict;
    return verdict;
  });

  handle(CHANNELS.listProjects, async () => {
    const ctx = await context();
    return ctx === null ? NO_CLI : listProjects(ctx);
  });

  // Spawns nothing — reads this app's own settings file. See `BindRequest.name`'s
  // comment above for why this channel is not in `CHANNELS`.
  handle(CHANNELS.projectNames, async (): Promise<Readonly<Record<string, string>>> => {
    const current = await ensureSettings();
    return current.projectNames;
  });

  // Spawns nothing — the folders are this app's own record (ADR-0021).
  handle(CHANNELS.projectFolders, async (): Promise<ProjectFolders> => {
    const current = await ensureSettings();
    return current.projectFolders;
  });

  handle(CHANNELS.saveProjectFolders, async (_event, raw: unknown): Promise<ProjectFoldersAnswer> => {
    const problem = projectFoldersProblem(raw);
    if (problem !== null) return { ok: false, message: `The folders were not saved: ${problem}.` };
    // Written from a rebuilt copy, never from the renderer's own object: the check above
    // proves the shape, and this makes sure the shape is all that gets stored.
    const folders = sanitizeProjectFolders(raw as ProjectFolders);
    try {
      await writeProjectFolders(deps.userDataDir, folders);
    } catch (error) {
      return { ok: false, message: `The folders could not be saved: ${error instanceof Error ? error.message : String(error)}` };
    } finally {
      // Stale either way: a failed write may still have been preceded by a successful read.
      settings = null;
    }
    return { ok: true, folders };
  });

  handle(CHANNELS.catalogSummary, async () => {
    const ctx = await context();
    return ctx === null ? NO_CLI : catalogSummary(ctx);
  });

  handle(CHANNELS.catalogListing, async (_event, kind: unknown) => {
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

  handle(CHANNELS.catalogEntry, async (_event, name: unknown) => {
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    return catalogEntry(ctx, typeof name === 'string' ? name : '');
  });

  handle(CHANNELS.doctor, async () => {
    // With no declaration the framework's write gate has nothing to bind, so this would
    // run ungated; the app refuses and says why rather than running it anyway.
    const gated = await gatedContext('doctor');
    if (!gated.ready) return gated.problem;
    return doctor(gated.ctx);
  });

  // ── write actions ────────────────────────────────────────────────────────────

  handle(CHANNELS.chooseProjectDirectory, async (): Promise<DirectoryChoice> => {
    const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
    const path = result.filePaths[0];
    if (result.canceled || path === undefined) return { chosen: false };
    offeredDirectories.add(path);
    return { chosen: true, path };
  });

  handle(CHANNELS.bindProject, async (_event, request: unknown): Promise<OperationResult<BindReport>> => {
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

  // `migrate` has `bind`'s provenance rule, and the same validator: its target is a
  // directory with no registry entry yet, so there is no `project_id` to resolve — the
  // path must be one this process handed back through the picker. `pin` is refused by the
  // validator's caller below rather than silently dropped: migrate takes no `--pin`.
  const validateMigrateRequest = (request: unknown): ValidatedBindRequest | string => {
    if (typeof request === 'object' && request !== null && 'pin' in request) return '`pin` is not a migrate option';
    return validateBindRequest(request, offeredDirectories);
  };

  handle(CHANNELS.planMigration, async (_event, request: unknown): Promise<OperationResult<MigrationPlan>> => {
    const validated = validateMigrateRequest(request);
    if (typeof validated === 'string') return refusedRequest('migrate', validated);
    const gated = await gatedContext('migrate');
    if (!gated.ready) return gated.problem;
    return planMigration(gated.ctx, validated.path, migrateOptions(validated));
  });

  handle(CHANNELS.applyMigration, async (_event, request: unknown): Promise<OperationResult<MigrationReport>> => {
    const validated = validateMigrateRequest(request);
    if (typeof validated === 'string') return refusedRequest('migrate', validated);
    const gated = await gatedContext('migrate');
    if (!gated.ready) return gated.problem;
    const result = await applyMigration(gated.ctx, validated.path, migrateOptions(validated));
    if (result.ok && validated.name !== undefined) {
      try {
        await writeProjectName(deps.userDataDir, result.data.project_id, validated.name);
        settings = null; // see the same line in the bindProject handler
      } catch {
        // Best-effort, exactly as for a bind: the migration succeeded either way.
      }
    }
    return result;
  });

  handle(CHANNELS.unbindProject, async (_event, projectId: unknown): Promise<OperationResult<UnbindReport>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('unbind');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('unbind');
    if (!gated.ready) return gated.problem;
    return unbindProject(gated.ctx, projectId);
  });

  handle(CHANNELS.syncProject, async (_event, projectId: unknown): Promise<OperationResult<BindReport>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('sync');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('sync');
    if (!gated.ready) return gated.problem;
    return syncProject(gated.ctx, projectId);
  });

  handle(CHANNELS.syncAllProjects, async (): Promise<OperationResult<SyncAllReport>> => {
    const gated = await gatedContext('sync');
    if (!gated.ready) return gated.problem;
    return syncAllProjects(gated.ctx);
  });

  handle(
    CHANNELS.setPin,
    async (_event, projectId: unknown, version: unknown): Promise<OperationResult<PinReport>> => {
      if (typeof projectId !== 'string') return refusedBadArgument('pin');
      // `null` is a release; anything else must be a non-empty string — never the empty
      // string `setPin(id, null)` must not become. See `setPin`'s own doc comment.
      if (version !== null && typeof version !== 'string') return refusedBadArgument('pin');
      if (version !== null && pinProblem(version) !== null) return refusedBadArgument('pin');
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('pin');
      if (!gated.ready) return gated.problem;
      return setPin(gated.ctx, resolved.path, version);
    },
  );

  handle(CHANNELS.planUpgrade, async (_event, projectId: unknown): Promise<OperationResult<UpgradePlan>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('upgrade');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('upgrade');
    if (!gated.ready) return gated.problem;
    return planUpgrade(gated.ctx, resolved.path);
  });

  handle(CHANNELS.applyUpgrade, async (_event, projectId: unknown): Promise<OperationResult<UpgradeReport>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('upgrade');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('upgrade');
    if (!gated.ready) return gated.problem;
    return applyUpgrade(gated.ctx, resolved.path);
  });

  handle(
    CHANNELS.projectPreferences,
    async (_event, projectId: unknown): Promise<OperationResult<ProjectPreferencesView>> => {
      if (typeof projectId !== 'string') return refusedBadArgument('prefs list');
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const ctx = await context();
      if (ctx === null) return NO_CLI;
      const current = await prefsList(ctx, resolved.path);
      if (!current.ok) return current;
      // The app's own working directory is its `userData`, never a project, so `prefs list`
      // there is the cascade minus any project layer — what a reset falls back to. Trusted
      // only when the CLI confirms it resolved no project; otherwise it is reported unknown.
      const base = await prefsList(ctx, workingDirectory);
      const inherited = base.ok && base.data.project_id === null ? base.data.values : null;
      return { ...current, data: { ...current.data, inherited } };
    },
  );

  // ── global skills ──────────────────────────────────────────────────────────

  handle(CHANNELS.listSkills, async (_event, provider: unknown): Promise<OperationResult<SkillList>> => {
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    if (!SKILL_FILTERS.includes(provider as SkillProviderFilter)) return refusedBadArgument('skills list');
    return listSkills(ctx, provider as SkillProviderFilter);
  });

  handle(
    CHANNELS.showSkill,
    async (_event, name: unknown, root: unknown): Promise<OperationResult<SkillDetail>> => {
      const ctx = await context();
      if (ctx === null) return NO_CLI;
      if (typeof name !== 'string' || typeof root !== 'string') return refusedBadArgument('skills show');
      return showSkill(ctx, name, root);
    },
  );

  /**
   * The last source the picker returned this session, held here and never handed to the
   * renderer as something it can send back — a retry names `previous`, and this process
   * supplies the path. That is how "retry with replace" works without the renderer ever
   * holding a path it could substitute.
   */
  let lastSkillSource: { readonly path: string; readonly kind: 'folder' | 'archive' | 'file' } | null = null;

  handle(CHANNELS.installSkill, async (_event, request: unknown): Promise<SkillInstallAnswer> => {
    const refused = (message: string): SkillInstallAnswer => ({
      picked: true,
      source: '',
      result: {
        ok: false,
        kind: 'refused',
        message,
        exitCode: null,
        command: 'devteam skills install',
        durationMs: 0,
      },
    });
    const validated = validateSkillInstallRequest(request);
    if (typeof validated === 'string') return refused(`\`devteam skills install\` was refused: ${validated}`);
    // Gate before the picker: a withheld action must not open a dialog and then fail.
    const gated = await gatedContext('skills install');
    if (!gated.ready) return { picked: true, source: '', result: gated.problem };

    let chosen: { readonly path: string; readonly kind: 'folder' | 'archive' | 'file' };
    if (validated.source === 'previous') {
      if (lastSkillSource === null) return refused('There is no previous source to retry; choose one again.');
      chosen = lastSkillSource;
    } else {
      const picked = await dialog.showOpenDialog(skillPickerOptions(process.platform));
      const path = picked.filePaths[0];
      if (picked.canceled || path === undefined) return { picked: false };
      chosen = classifySkillPick(path);
      lastSkillSource = chosen;
    }
    if (chosen.kind === 'archive' && validated.link) {
      return refused('`devteam skills install` was refused: --link works only with a folder, not an archive.');
    }
    const result = await installSkill(gated.ctx, chosen.path, {
      providers: validated.providers,
      replace: validated.replace,
      link: validated.link,
    });
    return { picked: true, source: chosen.path, result };
  });

  handle(
    CHANNELS.removeSkill,
    async (_event, request: unknown): Promise<OperationResult<SkillRemoveReport>> => {
      if (request === null || typeof request !== 'object') return refusedBadArgument('skills remove');
      const { name, root } = request as { name?: unknown; root?: unknown };
      const problem = skillTargetProblem(name, root);
      if (problem !== null || typeof name !== 'string' || typeof root !== 'string') {
        return refusedBadArgument('skills remove');
      }
      const ctx = await context();
      if (ctx === null) return NO_CLI;
      // The target must be a skill this session's own `skills list` returns, and not a
      // managed one — the CLI refuses that at exit 4, but a refusal before the argv is built
      // is the same posture `resolveProject` takes for the project lifecycle.
      const listing = await listSkills(ctx, 'all');
      if (!listing.ok) return listing;
      const found = listing.data.skills.find((skill) => skill.name === name.trim() && skill.root === root);
      if (found === undefined) {
        return {
          ok: false,
          kind: 'refused',
          message: `\`${name}\` is not a skill in the \`${root}\` root.`,
          exitCode: null,
          command: 'devteam skills list',
          durationMs: 0,
        };
      }
      if (found.managed) {
        return {
          ok: false,
          kind: 'refused',
          message: `\`${name}\` is managed by dev-team-agents and is not removed from here.`,
          exitCode: null,
          command: 'devteam skills remove',
          durationMs: 0,
        };
      }
      const gated = await gatedContext('skills remove');
      if (!gated.ready) return gated.problem;
      return removeSkill(gated.ctx, name, root);
    },
  );

  /**
   * A batch of project-layer writes, applied in order and stopped at the first failure.
   *
   * Each key is checked against **this project's own `prefs list` answer** before anything
   * is written, so the renderer cannot aim `prefs set` at a key the framework does not
   * declare — an unknown key would otherwise be written and carried forever as `unknown`.
   * The scope is fixed to `project` in `cli/operations.ts`; there is no way to reach the
   * global layer through this channel.
   */
  handle(
    CHANNELS.updateProjectPreferences,
    async (_event, projectId: unknown, changes: unknown): Promise<OperationResult<PreferenceUpdateReport>> => {
      if (typeof projectId !== 'string') return refusedBadArgument('prefs set');
      const parsed = parsePreferenceChanges(changes);
      if (typeof parsed === 'string') {
        return refusedPreferences(`\`devteam prefs set\` was refused: ${parsed}`);
      }
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('prefs set');
      if (!gated.ready) return gated.problem;

      const listing = await prefsList(gated.ctx, resolved.path);
      if (!listing.ok) return listing;
      const known = new Set(Object.keys(listing.data.values).filter((key) => !listing.data.unknown.includes(key)));
      const stranger = parsed.find((change) => !known.has(change.key));
      if (stranger !== undefined) {
        return refusedPreferences(
          `\`${stranger.key}\` is not a preference store version ${listing.data.version} declares.`,
        );
      }

      const consenting = parsed.filter(
        (change) => change.action === 'set' && CONSENT_KEYS.has(change.key) && change.value === true,
      );
      if (consenting.length > 0 && !(await confirmConsent(consenting.map((change) => change.key), deps.dialogIcon ?? null))) {
        return refusedPreferences('Turning on a consent setting was not confirmed, so nothing was saved.');
      }

      const started = Date.now();
      const applied: PreferenceChange[] = [];
      for (const change of parsed) {
        const result =
          change.action === 'unset'
            ? await prefsUnset(gated.ctx, resolved.path, change.key)
            : await prefsSet(gated.ctx, resolved.path, change.key, change.value);
        if (!result.ok) {
          return {
            ok: true,
            outcome: 'success',
            data: { applied, failed: { change, problem: result } },
            command: result.command,
            durationMs: Date.now() - started,
          };
        }
        applied.push(change);
      }
      return {
        ok: true,
        outcome: 'success',
        data: { applied, failed: null },
        command: 'devteam prefs set --scope project',
        durationMs: Date.now() - started,
      };
    },
  );

  // ── plugins (ADR-0019) ─────────────────────────────────────────────────────────────
  //
  // Every plugin write first re-reads **this project's own `plugin list`** and checks the
  // plugin, the action and each config key against it: the renderer names things, this
  // process decides whether they exist. The set of runnable things changes only with a
  // core release, and `plugin run` never receives anything but two identifiers.

  /** The plugin `name` in this project's own list, or the problem to return instead. */
  async function findPlugin(
    ctx: CliContext,
    path: string,
    name: string,
    command: string,
  ): Promise<{ readonly plugin: PluginView } | OperationResult<never>> {
    const listing = await pluginList(ctx, path);
    if (!listing.ok) return listing;
    const plugin = listing.data.plugins.find((entry) => entry.name === name);
    if (plugin === undefined) return refusedPlugin(command, `\`${name}\` is not a plugin this project's \`plugin list\` returned.`);
    return { plugin };
  }

  handle(CHANNELS.projectPlugins, async (_event, projectId: unknown): Promise<OperationResult<PluginList>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('plugin list');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    return pluginList(ctx, resolved.path);
  });

  handle(
    CHANNELS.setPluginEnabled,
    async (_event, projectId: unknown, name: unknown, enabled: unknown): Promise<OperationResult<PluginToggleReport>> => {
      const command = enabled === false ? 'plugin disable' : 'plugin enable';
      if (typeof projectId !== 'string' || typeof name !== 'string' || typeof enabled !== 'boolean') {
        return refusedBadArgument(command);
      }
      if (!PLUGIN_NAME.test(name)) return refusedPlugin(command, 'a plugin name is lowercase letters, digits and dashes');
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext(command);
      if (!gated.ready) return gated.problem;
      const found = await findPlugin(gated.ctx, resolved.path, name, command);
      if (!('plugin' in found)) return found;
      return enabled ? pluginEnable(gated.ctx, resolved.path, name) : pluginDisable(gated.ctx, resolved.path, name);
    },
  );

  handle(
    CHANNELS.updatePluginConfig,
    async (
      _event,
      projectId: unknown,
      name: unknown,
      changes: unknown,
    ): Promise<OperationResult<PluginConfigUpdateReport>> => {
      if (typeof projectId !== 'string' || typeof name !== 'string') return refusedBadArgument('plugin config set');
      const parsed = parsePluginConfigChanges(changes);
      if (typeof parsed === 'string') return refusedPlugin('plugin config set', `\`devteam plugin config set\` was refused: ${parsed}`);
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('plugin config set');
      if (!gated.ready) return gated.problem;
      const found = await findPlugin(gated.ctx, resolved.path, name, 'plugin config set');
      if (!('plugin' in found)) return found;

      const fields = new Map<string, PluginConfigField>(found.plugin.config_fields.map((field) => [field.key, field]));
      for (const change of parsed) {
        const field = fields.get(change.key);
        if (field === undefined) {
          return refusedPlugin('plugin config set', `\`${change.key}\` is not a setting \`${name}\` declares.`);
        }
        if (!isEditable(field)) {
          return refusedPlugin('plugin config set', `\`${change.key}\` is a ${field.type} setting this app cannot edit.`);
        }
        if (change.action === 'set') {
          const problem = pluginValueProblem(field, change.value);
          if (problem !== null) return refusedPlugin('plugin config set', `\`${change.key}\`: ${problem}`);
        }
      }

      const started = Date.now();
      const applied: PluginConfigChange[] = [];
      for (const change of parsed) {
        const field = fields.get(change.key) as PluginConfigField;
        const result =
          change.action === 'unset'
            ? await pluginConfigUnset(gated.ctx, resolved.path, name, change.key)
            : await pluginConfigSet(gated.ctx, resolved.path, name, change.key, serializePluginValue(field, change.value));
        if (!result.ok) {
          return {
            ok: true,
            outcome: 'success',
            data: { applied, failed: { change, problem: result } },
            command: result.command,
            durationMs: Date.now() - started,
          };
        }
        applied.push(change);
      }
      return {
        ok: true,
        outcome: 'success',
        data: { applied, failed: null },
        command: 'devteam plugin config set',
        durationMs: Date.now() - started,
      };
    },
  );

  // ── integrations (ADR-0023) ────────────────────────────────────────────────────────
  //
  // Account-level connections to an external API. The renderer names an integration and a
  // key; the CLI owns the descriptors and rejects anything it does not declare. `projectId`
  // is optional: `null` means no project, a string is resolved against the registry exactly
  // as the plugin handlers do. The token is forwarded over stdin to one invocation and is
  // never logged, returned, or kept in this process.

  /** `null` for "no project", a registered project's path for an id, or the refusal to return. */
  async function integrationProject(projectId: unknown): Promise<{ readonly path: string | null } | OperationResult<never>> {
    if (projectId === null) return { path: null };
    if (typeof projectId !== 'string') return refusedBadArgument('integration');
    return resolveProject(projectId);
  }

  handle(CHANNELS.integrationList, async (_event, projectId: unknown): Promise<OperationResult<IntegrationList>> => {
    const resolved = await integrationProject(projectId);
    if (!('path' in resolved)) return resolved;
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    return integrationList(ctx, resolved.path);
  });

  handle(
    CHANNELS.integrationConnect,
    async (
      _event,
      name: unknown,
      fields: unknown,
      token: unknown,
      projectId: unknown,
    ): Promise<OperationResult<IntegrationConnectReport>> => {
      if (typeof name !== 'string') return refusedBadArgument('integration connect');
      const problem = integrationFieldsProblem(fields) ?? integrationTokenProblem(token);
      if (problem !== null) return refusedRequest('integration connect', `\`devteam integration connect\` was refused: ${problem}`);
      const resolved = await integrationProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('integration connect');
      if (!gated.ready) return gated.problem;
      return integrationConnect(
        gated.ctx,
        resolved.path,
        name,
        fields as Readonly<Record<string, string>>,
        typeof token === 'string' ? token : null,
      );
    },
  );

  handle(
    CHANNELS.integrationTest,
    async (_event, name: unknown, projectId: unknown): Promise<OperationResult<IntegrationTestReport>> => {
      if (typeof name !== 'string') return refusedBadArgument('integration test');
      const resolved = await integrationProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('integration test');
      if (!gated.ready) return gated.problem;
      return integrationTest(gated.ctx, resolved.path, name);
    },
  );

  handle(
    CHANNELS.integrationDisconnect,
    async (_event, name: unknown, keepToken: unknown): Promise<OperationResult<IntegrationDisconnectReport>> => {
      if (typeof name !== 'string' || typeof keepToken !== 'boolean') return refusedBadArgument('integration disconnect');
      const gated = await gatedContext('integration disconnect');
      if (!gated.ready) return gated.problem;
      return integrationDisconnect(gated.ctx, name, keepToken);
    },
  );

  handle(
    CHANNELS.integrationConfigSet,
    async (
      _event,
      name: unknown,
      key: unknown,
      value: unknown,
      projectId: unknown,
    ): Promise<OperationResult<IntegrationConfigWrite>> => {
      if (typeof name !== 'string' || typeof key !== 'string' || typeof value !== 'string') {
        return refusedBadArgument('integration config set');
      }
      const resolved = await integrationProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('integration config set');
      if (!gated.ready) return gated.problem;
      return integrationConfigSet(gated.ctx, resolved.path, name, key, value);
    },
  );

  handle(
    CHANNELS.integrationConfigUnset,
    async (_event, name: unknown, key: unknown, projectId: unknown): Promise<OperationResult<IntegrationConfigWrite>> => {
      if (typeof name !== 'string' || typeof key !== 'string') return refusedBadArgument('integration config unset');
      const resolved = await integrationProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('integration config unset');
      if (!gated.ready) return gated.problem;
      return integrationConfigUnset(gated.ctx, resolved.path, name, key);
    },
  );

  handle(
    CHANNELS.integrationResources,
    async (_event, name: unknown, kind: unknown, projectId: unknown): Promise<OperationResult<IntegrationResources>> => {
      if (typeof name !== 'string' || typeof kind !== 'string') return refusedBadArgument('integration resources');
      const resolved = await integrationProject(projectId);
      if (!('path' in resolved)) return resolved;
      const ctx = await context();
      if (ctx === null) return NO_CLI;
      return integrationResources(ctx, resolved.path, name, kind);
    },
  );

  // ── local credentials file (ADR-0024) ──────────────────────────────────────────────
  //
  // The project is named by id and resolved against the registry; the renderer never supplies
  // a path. Edits travel to the CLI over stdin and the response carries no secret value.

  handle(CHANNELS.credentialsLocalShow, async (_event, projectId: unknown): Promise<OperationResult<CredentialsLocalView>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('cred local show');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const ctx = await context();
    if (ctx === null) return NO_CLI;
    return credentialsLocalShow(ctx, resolved.path);
  });

  handle(CHANNELS.credentialsLocalInit, async (_event, projectId: unknown): Promise<OperationResult<CredentialsLocalView>> => {
    if (typeof projectId !== 'string') return refusedBadArgument('cred local init');
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) return resolved;
    const gated = await gatedContext('cred local init');
    if (!gated.ready) return gated.problem;
    return credentialsLocalInit(gated.ctx, resolved.path);
  });

  handle(
    CHANNELS.credentialsLocalPatch,
    async (_event, projectId: unknown, expectHash: unknown, ops: unknown): Promise<OperationResult<CredentialsLocalView>> => {
      if (typeof projectId !== 'string') return refusedBadArgument('cred local patch');
      if (typeof expectHash !== 'string' || !CREDENTIALS_HASH.test(expectHash)) {
        return refusedRequest('cred local patch', '`devteam cred local patch` was refused: the expected hash is 64 hex characters');
      }
      if (!isCredentialsOps(ops)) {
        return refusedRequest('cred local patch', `\`devteam cred local patch\` was refused: ${credentialsOpsProblem(ops) ?? 'invalid edits'}`);
      }
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('cred local patch');
      if (!gated.ready) return gated.problem;
      return credentialsLocalPatch(gated.ctx, resolved.path, expectHash, ops);
    },
  );

  handle(CHANNELS.pickProjectPath, async (_event, projectId: unknown, picker: unknown): Promise<ProjectPathPick> => {
    if (typeof projectId !== 'string' || (picker !== 'directory' && picker !== 'file')) {
      return { picked: false, refused: 'That request was not a project and a picker kind this app knows.' };
    }
    const resolved = await resolveProject(projectId);
    if (!('path' in resolved)) {
      return { picked: false, refused: resolved.ok ? 'That project could not be resolved.' : resolved.message };
    }
    const root = await realpath(resolved.path).catch(() => null);
    if (root === null) return { picked: false, refused: 'The project folder could not be found on disk.' };
    const dir = picker === 'directory';
    const chosen = await dialog.showOpenDialog({
      title: dir ? 'Choose a source directory' : 'Choose a file',
      defaultPath: root,
      properties: dir ? ['openDirectory', 'dontAddToRecent'] : ['openFile', 'dontAddToRecent'],
    });
    const path = chosen.filePaths[0];
    if (chosen.canceled || path === undefined) return { picked: false };
    return projectRelativeChoice(root, path);
  });

  handle(
    CHANNELS.runPluginAction,
    async (_event, projectId: unknown, name: unknown, actionId: unknown): Promise<OperationResult<PluginRunResult>> => {
      if (typeof projectId !== 'string' || typeof name !== 'string' || typeof actionId !== 'string') {
        return refusedBadArgument('plugin run');
      }
      if (!PLUGIN_NAME.test(name) || !PLUGIN_ACTION_ID.test(actionId)) {
        return refusedPlugin('plugin run', 'a plugin name or action id has a shape no manifest can declare');
      }
      const resolved = await resolveProject(projectId);
      if (!('path' in resolved)) return resolved;
      const gated = await gatedContext('plugin run');
      if (!gated.ready) return gated.problem;
      const found = await findPlugin(gated.ctx, resolved.path, name, 'plugin run');
      if (!('plugin' in found)) return found;
      const action = found.plugin.actions.find((entry) => entry.id === actionId);
      if (action === undefined) return refusedPlugin('plugin run', `\`${name}\` declares no action \`${actionId}\`.`);
      return pluginRun(gated.ctx, resolved.path, name, actionId, action.timeout_seconds);
    },
  );
  // Paths from `list`, kept for a minute: a burst of notifications must not start one
  // `devteam list` each just to name the project in a banner title.
  //
  // The **promise** is cached, set before the first await: caching the result after it
  // arrived let every call in a burst miss together and each start its own `list`. Only
  // a successful listing is kept — a failed one would have named every project "a bound
  // project" for the whole minute.
  let pathsCache: { at: number; paths: Promise<Map<string, string>> } | null = null;
  async function listPaths(): Promise<Map<string, string> | null> {
    try {
      const ctx = await context();
      const listed = ctx === null ? null : await listProjects(ctx);
      if (listed === null || !listed.ok) return null;
      return new Map(listed.data.projects.map((project) => [project.project_id, project.path] as const));
    } catch {
      return null; // Same as a failed listing: the caller falls back.
    }
  }
  function projectPaths(): Promise<Map<string, string>> {
    if (pathsCache !== null && Date.now() - pathsCache.at < 60_000) return pathsCache.paths;
    const entry: { at: number; paths: Promise<Map<string, string>> } = { at: Date.now(), paths: Promise.resolve(new Map<string, string>()) };
    entry.paths = listPaths().then((paths) => {
      if (paths !== null) return paths;
      if (pathsCache === entry) pathsCache = null;
      return new Map<string, string>();
    });
    pathsCache = entry;
    return entry.paths;
  }

  return {
    context,
    gatedContext: async (command) => {
      const gated = await gatedContext(command);
      return gated.ready ? gated.ctx : null;
    },
    projectName: async (projectId) => {
      const names = (await readSettings(deps.userDataDir)).projectNames;
      const named = names[projectId];
      if (named !== undefined) return named;
      const path = (await projectPaths()).get(projectId);
      return path !== undefined ? basename(path) : 'a bound project';
    },
  };
}

const CONSENT_LABELS: Readonly<Record<string, string>> = {
  telemetry: 'anonymous usage telemetry',
  auto_update: 'automatic updates',
};

/**
 * The user's own yes, asked in a native dialog the renderer cannot draw or answer. Consent
 * keys default to off until someone opts in; without this, anything able to call the bridge
 * could opt in silently — `auto_update` decides whether new framework code is applied.
 */
async function confirmConsent(keys: readonly string[], icon: NativeImage | null): Promise<boolean> {
  const names = keys.map((key) => CONSENT_LABELS[key] ?? key).join(' and ');
  const { response } = await dialog.showMessageBox({
    ...(icon !== null ? { icon } : {}),
    type: 'question',
    buttons: ['Turn on', 'Cancel'],
    defaultId: 1,
    cancelId: 1,
    message: `Turn on ${names} for this project?`,
    detail: 'This is an opt-in setting. You can turn it off again from the project settings at any time.',
  });
  return response === 0;
}

function refusedPreferences(message: string): OperationResult<never> {
  return { ok: false, kind: 'refused', message, exitCode: null, command: 'devteam prefs set', durationMs: 0 };
}

/** The renderer's batch, rebuilt from `unknown`. At most one change per key, 64 in total. */
export function parsePreferenceChanges(raw: unknown): PreferenceChange[] | string {
  if (!Array.isArray(raw)) return 'the changes are not a list';
  if (raw.length === 0) return 'there is nothing to change';
  if (raw.length > 64) return 'too many changes in one batch';
  const seen = new Set<string>();
  const changes: PreferenceChange[] = [];
  for (const entry of raw) {
    if (entry === null || typeof entry !== 'object') return 'a change is not an object';
    const { key, action, value } = entry as { key?: unknown; action?: unknown; value?: unknown };
    if (action !== 'set' && action !== 'unset') return 'a change has no `set` or `unset` action';
    const problem = preferenceArgumentProblem(key, action === 'set' ? value : null);
    if (problem !== null) return problem;
    const name = key as string;
    const rule = PREFERENCE_RULES[name];
    if (rule === undefined || rule.kind === 'readonly') return `\`${name}\` is not a preference this app edits`;
    if (action === 'set') {
      const invalid = valueProblem(name, value as PreferenceValue);
      if (invalid !== null) return invalid;
    }
    if (seen.has(name)) return `\`${name}\` appears twice in one batch`;
    seen.add(name);
    changes.push(
      action === 'unset' ? { key: name, action } : { key: name, action, value: value as PreferenceValue },
    );
  }
  return changes;
}

function refusedPlugin(command: string, message: string): OperationResult<never> {
  return { ok: false, kind: 'refused', message, exitCode: null, command: `devteam ${command}`, durationMs: 0 };
}

/**
 * The renderer's batch of plugin config edits, rebuilt from `unknown`. At most one change
 * per key, 64 in total. The values are only shape-checked here — whether a value suits its
 * field is decided against the field, after the plugin's own list has been read.
 */
export function parsePluginConfigChanges(raw: unknown): PluginConfigChange[] | string {
  if (!Array.isArray(raw)) return 'the changes are not a list';
  if (raw.length === 0) return 'there is nothing to change';
  if (raw.length > 64) return 'too many changes in one batch';
  const seen = new Set<string>();
  const changes: PluginConfigChange[] = [];
  for (const entry of raw as unknown[]) {
    if (entry === null || typeof entry !== 'object') return 'a change is not an object';
    const { key, action, value } = entry as { key?: unknown; action?: unknown; value?: unknown };
    if (action !== 'set' && action !== 'unset') return 'a change has no `set` or `unset` action';
    if (typeof key !== 'string' || !PLUGIN_CONFIG_KEY.test(key)) return 'a config key is letters, digits and underscores';
    if (seen.has(key)) return `\`${key}\` appears twice in one batch`;
    seen.add(key);
    changes.push(action === 'unset' ? { key, action } : { key, action, value: value as PluginConfigValue });
  }
  return changes;
}
