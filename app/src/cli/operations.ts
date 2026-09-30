/**
 * The named operations this app can perform, and nothing else.
 *
 * Read-only for most of this file — `list`, `catalog*`, `doctor`, `prefsList` — plus the
 * project lifecycle's write actions at the bottom: `bindProject`, `unbindProject`,
 * `syncProject`, `syncAllProjects`, `setPin`, `planUpgrade`, `applyUpgrade`, and the
 * project-layer preference writes `prefsSet` / `prefsUnset`, and the global-skills
 * commands `skills list|show|install|remove`. One function
 * per screen's needs. Each builds its own argument vector — the renderer never supplies
 * one — and each validates the payload it got before handing it on.
 *
 * **Validation checks that required keys are present and of the right type. It does not
 * demand an exact key set.** ADR-0014 § 2 makes an *additive* payload change explicitly
 * non-breaking, so a client that rejected an unfamiliar key would break itself on a
 * change the contract permits. A *missing* key is the other direction: it is reported, and
 * where the key is a boolean claim about the world it is reported as **unknown** rather
 * than collapsed into `false` — see `ProjectRecord.path_exists`.
 *
 * **What this build may spawn is enforced, not merely listed.** `COMMAND_SHAPES` is
 * consulted by `run()` on every call, so an argv outside it is refused before a process
 * exists. The `compat` classification of those commands is asserted in
 * `test/operations.test.ts` against the same table the CLI classifies with.
 */

import { invokeDevteam, type InvokeOptions } from './invoke.js';
import { streamDevteam, type StreamEnd, type StreamHandle } from './stream.js';
import { explain, ranAndAnswered, type CliResult } from './contract.js';
import { textProblem } from '../shared/preferenceRules.js';
import { PLUGIN_ACTION_ID, PLUGIN_CONFIG_KEY, PLUGIN_NAME } from '../shared/pluginRules.js';
import type {
  BoardColumn,
  BoardCounts,
  BoardReview,
  BoardReviewState,
  BoardProject,
  BoardSession,
  BoardSessionStatus,
  BoardTask,
  BindMode,
  BindProvider,
  BindReport,
  CatalogDetail,
  CatalogEntry,
  CatalogKind,
  CatalogListing,
  CatalogSummary,
  DoctorFinding,
  DoctorReport,
  MigrationMove,
  MigrationPlan,
  MigrationReport,
  NotificationLevel,
  OperationResult,
  PinReport,
  PluginAction,
  PluginConfigField,
  PluginConfigWrite,
  InvalidPlugin,
  PluginList,
  PluginRequirement,
  PluginRunResult,
  PluginStatus,
  PluginToggleReport,
  PluginView,
  PreferencesImport,
  QueuedNotification,
  PreferenceValue,
  PreferenceWrite,
  ProjectList,
  ProjectPreferences,
  ProjectRecord,
  ProblemKind,
  SkillDetail,
  SkillInstallReport,
  SkillList,
  SkillProvider,
  SkillProviderFilter,
  SkillRecord,
  SkillRemoveReport,
  SyncAllReport,
  UnbindReport,
  UpgradePlan,
  UpgradeReport,
} from '../shared/api.js';

/**
 * Everything an operation needs, and `cwd` is **required**.
 *
 * `cwd` used to be optional, so nothing set it and the child inherited the main process's
 * directory — `app/` under `npm start`, `/` for a Finder launch. `catalog --json` then
 * answered with a real `project_id` from one directory and `null` from another, and
 * `doctor` changed its project finding the same way, which is the state `CLAUDE-md/cli.md`
 * § Catalog forbids: the app "must never report the harness in two different states
 * depending on where the user was standing when they asked". Making it required means a
 * context cannot be constructed without deciding, and the decision is made once, in
 * `main/ipc.ts`.
 *
 * The same directory is also passed as an explicit `--path` to every command that accepts
 * one (see `COMMAND_SHAPES`), so the project answer comes from an argument the app chose
 * rather than from an ambient default. `doctor` gets `--no-project` instead, which is the
 * CLI's own switch for "check the store only, ignoring the cwd".
 */
export type CliContext = Required<Pick<InvokeOptions, 'binary' | 'cwd'>> &
  Pick<InvokeOptions, 'env' | 'timeoutMs' | 'declarationFile' | 'cancelOnQuit'>;

/** Subcommands this build runs that the framework classifies in `compat.READ_ONLY`. */
export const READ_ONLY_COMMANDS: readonly (readonly string[])[] = Object.freeze([
  ['version'],
  ['compat'],
  ['list'],
  ['catalog'],
  ['catalog', 'agents'],
  ['catalog', 'skills'],
  ['catalog', 'commands'],
  ['catalog', 'show'],
  ['prefs', 'list'],
  ['plugin', 'list'],
  ['notifications', 'list'],
  ['notifications', 'watch'],
  ['skills', 'list'],
  ['skills', 'show'],
  ['tasks', 'list'],
  ['tasks', 'watch'],
]);

/**
 * Subcommands this build runs that the framework classifies in `compat.MUTATING`.
 *
 * **`doctor` alone was the whole list until this build.** It stayed alone because the
 * app had no project lifecycle: nothing else this app ran needed to change the store,
 * and admitting an entry here without needing one would have been a widening with no
 * corresponding capability to justify it.
 *
 * This build adds the five commands that *are* the project lifecycle — `bind`, `unbind`,
 * `sync`, `pin`, `upgrade` — because the UI now offers binding, unbinding, syncing,
 * pinning and upgrading a project, and every one of those five is listed in
 * `compat.MUTATING` with its own reason (`bind`: "writes project.json, the registry
 * entry, the manifest and every artifact"; `unbind`: "removes artifacts and rewrites the
 * registry entry"; `sync`: "rebuilds artifacts and rewrites the manifest"; `pin`: "writes
 * the pin into the registry entry"; `upgrade`: "relocates this project's memory into the
 * store"). None of the five can be reclassified as read-only to avoid this list; the
 * decision this app made instead is to run them, declare its schemas on every
 * invocation as it already did for `doctor`, and accept the framework's exit-4 refusal
 * as the real protection whenever the store is ahead of what this app understands.
 *
 * **Each addition here is deliberate, and the security posture that makes it safe lives
 * in `main/ipc.ts`, not in this file.** This table only says which command words may be
 * spawned; it is `ipc.ts` that resolves every write action's target against the
 * registry's own `list` answer before an argv is built (`resolveProject`), and that
 * treats `bind` — the one command with no existing project to resolve — as the
 * exception, refusing any path the main process did not itself hand back through
 * `chooseProjectDirectory`. Widening this list without that resolution in place would be
 * the defect the whole design exists to prevent.
 *
 * Adding a further entry is again a decision to widen what this app can change. Make it
 * explicitly; `test/operations.test.ts` fails on an unreviewed addition.
 */
export const GATED_COMMANDS: readonly (readonly string[])[] = Object.freeze([
  ['doctor'],
  ['bind'],
  ['unbind'],
  ['sync'],
  ['pin'],
  ['upgrade'],
  // A v2 install converted from the bind dialog. Its plan writes nothing, but the command is
  // classified mutating by the CLI (`compat.py`) and the gate is per command, not per flag.
  // `--untrack` is the one path by which this app causes a git operation (`git rm -r
  // --cached` on the plan's own paths); see ADR-0015's amendment.
  ['migrate'],
  ['prefs', 'set'],
  ['prefs', 'unset'],
  // ADR-0019. `plugin run` is listed here although only some actions write: the framework
  // cannot know which, and the app has no way to tell the gate a script is harmless.
  ['plugin', 'enable'],
  ['plugin', 'disable'],
  ['plugin', 'config', 'set'],
  ['plugin', 'config', 'unset'],
  ['plugin', 'run'],
  // Writes `notifications-seen.json` in one project's machine-local state directory —
  // the smallest write this app makes, and still a write, so it is declared and gated
  // like every other. The id is validated (`NOTIFICATION_ID`) before it reaches argv.
  ['notifications', 'ack'],
  ['skills', 'install'],
  ['skills', 'remove'],
]);

/**
 * Deadline for a gated command. `DEFAULT_TIMEOUT_MS` is sized for a read; a write killed at
 * 20 s is killed mid-mutation (a `sync` rebuilding artifacts, an `upgrade` relocating a
 * project's memory), which leaves the store's lock held until the CLI's own stale-lock
 * window passes and the store half-written. Still finite, so a wedged lock wait ends.
 */
export const GATED_TIMEOUT_MS = 5 * 60_000;

function isGatedArgv(args: readonly string[]): boolean {
  return GATED_COMMANDS.some((command) => command.every((word, index) => args[index] === word));
}

/** Every subcommand this build is allowed to run. */
export const ALLOWED_COMMANDS: readonly (readonly string[])[] = Object.freeze([
  ...READ_ONLY_COMMANDS,
  ...GATED_COMMANDS,
]);

export const CATALOG_KINDS: readonly CatalogKind[] = Object.freeze(['agents', 'skills', 'commands']);

// ── the argv boundary ─────────────────────────────────────────────────────────

/**
 * The full shape of every command this app may spawn: the words, how many positional
 * operands may follow, and which flags may be passed.
 *
 * **This table is enforced at runtime by `run()`, and that is the point of it.** The three
 * lists above had *no runtime consumer* — `GATED_COMMANDS` was read once to build a display
 * string, and `invokeDevteam` spawned whatever argv it was handed. A `credGet()` that ran
 * `['cred', 'get', key]` therefore typechecked, linted and passed every test, which made
 * the "never runs `cred get`" assertion a statement about a list nothing consulted.
 *
 * `--json` is deliberately **not** listed for any command: it is appended in `invoke.ts`,
 * so a caller that supplies one is a caller building an argv this layer did not intend.
 * That is also the second line of defence behind `validateEntryName` — an operand that
 * would read as a flag is refused here even if a call site stops validating it.
 */
export interface CommandShape {
  /** Positional operands the app may pass after the command words. `prefs set` takes two (key and value); `plugin config set` takes three. */
  readonly operands: 0 | 1 | 2 | 3;
  /**
   * Flags this command may be passed, and how each is used.
   *
   * `'repeatable'` is `'value'` in every way `argvProblem` checks it — a flag word
   * followed by a value token — named apart so the table states honestly that `bind`
   * means the flag to appear once per provider (`--provider claude --provider codex`)
   * rather than smuggling a joined list through a single occurrence (`--provider
   * "claude,codex"`, which the real CLI's `argparse` would read as one unknown choice).
   */
  readonly flags: Readonly<Record<string, 'value' | 'bare' | 'repeatable'>>;
}

/** Keyed by the command words joined with a space. Pinned to `ALLOWED_COMMANDS` by a test. */
export const COMMAND_SHAPES: Readonly<Record<string, CommandShape>> = Object.freeze({
  version: { operands: 0, flags: {} },
  compat: { operands: 0, flags: {} },
  // `list` reads the registry; it resolves no project, so it takes no `--path`.
  list: { operands: 0, flags: {} },
  catalog: { operands: 0, flags: { '--path': 'value' } },
  'catalog agents': { operands: 0, flags: { '--path': 'value' } },
  'catalog skills': { operands: 0, flags: { '--path': 'value' } },
  'catalog commands': { operands: 0, flags: { '--path': 'value' } },
  'catalog show': { operands: 1, flags: { '--path': 'value' } },
  // `--no-project`: "check the store only, ignoring the cwd". Never `--reassign-identity`.
  doctor: { operands: 0, flags: { '--no-project': 'bare' } },
  // The one positional is the directory to bind — the path `chooseProjectDirectory`
  // offered, never one the renderer typed. See `main/ipc.ts` -> `resolveProject`.
  bind: { operands: 1, flags: { '--provider': 'repeatable', '--mode': 'value', '--pin': 'value' } },
  // The positional `path` this app never passes: every unbind names its target by
  // `--project-id`, resolved against `list` in `main/ipc.ts` first.
  unbind: { operands: 1, flags: { '--project-id': 'value', '--keep-artifacts': 'bare' } },
  sync: { operands: 1, flags: { '--all': 'bare', '--project-id': 'value' } },
  // `cmd_pin` resolves its target from `--path`/the positional path alone — there is no
  // `--project-id` on this command — so `main/ipc.ts` resolves the id to a path first.
  pin: { operands: 1, flags: { '--path': 'value', '--release': 'bare' } },
  // Same as `pin`: `upgrade.plan`/`upgrade.apply` take only a path, so the positional
  // here is always a path `main/ipc.ts` resolved from a `project_id`, never a renderer
  // string.
  upgrade: { operands: 1, flags: { '--apply': 'bare' } },
  migrate: {
    operands: 1,
    flags: { '--provider': 'repeatable', '--mode': 'value', '--apply': 'bare', '--untrack': 'bare' },
  },
  // The preference commands resolve their project from `--path` alone, so — as with `pin`
  // — the path is always one `main/ipc.ts` resolved from a `project_id`. `--scope` is
  // always `project`: the settings screen edits one project's layer and never the global
  // one, which would silently change every other bound project too.
  'prefs list': { operands: 0, flags: { '--path': 'value' } },
  'prefs set': { operands: 2, flags: { '--scope': 'value', '--path': 'value' } },
  'prefs unset': { operands: 1, flags: { '--scope': 'value', '--path': 'value' } },
  // ADR-0019 § 3. Every plugin command resolves its project from `--path` alone, so the path
  // is one `main/ipc.ts` resolved from a `project_id`. `--force` (enable anyway) is
  // deliberately absent: the UI has no way to say "I know a requirement is missing".
  'plugin list': { operands: 0, flags: { '--path': 'value' } },
  'plugin enable': { operands: 1, flags: { '--path': 'value' } },
  'plugin disable': { operands: 1, flags: { '--path': 'value' } },
  'plugin config set': { operands: 3, flags: { '--path': 'value' } },
  'plugin config unset': { operands: 2, flags: { '--path': 'value' } },
  'plugin run': { operands: 2, flags: { '--path': 'value' } },
  // One id per ack: the app acknowledges each notification as it shows it. Never `--all`
  // — an ack the user did not see happen is a notification they never got.
  'notifications list': { operands: 0, flags: { '--unseen': 'bare' } },
  'notifications ack': { operands: 1, flags: {} },
  // Streamed, not invoked: `stream.ts`, entered through `watchNotifications` below, which
  // consults this table exactly as `run()` does.
  'notifications watch': { operands: 0, flags: {} },
  // Global (user-level) skills. These take no `--path`: they act on the providers' own
  // directories, never on a project. `--source` is always a path the main process's own
  // picker returned (`main/ipc.ts` -> `installSkill`), and `--root` on `remove`/`show` is a
  // root id copied from a `skills list` record. `install` passes no `--root`: which roots a
  // skill lands in is the CLI's decision from the providers, not this app's.
  'skills list': { operands: 0, flags: { '--provider': 'value' } },
  'skills show': { operands: 1, flags: { '--root': 'value' } },
  'skills install': {
    operands: 0,
    flags: { '--source': 'value', '--provider': 'repeatable', '--replace': 'bare', '--link': 'bare' },
  },
  'skills remove': { operands: 1, flags: { '--root': 'value' } },
  // The task board (ADR-0018). Both are reads of machine-local records. `--stale-after` is
  // the app's own setting in seconds; the app filters periods itself, so `--since` is only
  // allowed on the one-shot `list`.
  'tasks list': { operands: 0, flags: { '--stale-after': 'value', '--since': 'value' } },
  'tasks watch': { operands: 0, flags: { '--stale-after': 'value' } },
});

const MAX_COMMAND_WORDS = 3;

/**
 * Why this argv may not be spawned, or `null` when it may.
 *
 * Exported for direct testing, but the assertion that matters is the call site: `run()` is
 * the only way an operation reaches `invokeDevteam`, and it consults this first.
 */
export function argvProblem(args: readonly string[]): string | null {
  if (args.length === 0) return 'an empty argument vector is not a command';

  let words = 0;
  let shape: CommandShape | undefined;
  for (let take = Math.min(args.length, MAX_COMMAND_WORDS); take >= 1; take -= 1) {
    const candidate = COMMAND_SHAPES[args.slice(0, take).join(' ')];
    if (candidate !== undefined) {
      words = take;
      shape = candidate;
      break;
    }
  }
  if (shape === undefined) {
    return `\`devteam ${args.join(' ')}\` is not a command this app is allowed to run`;
  }

  const name = args.slice(0, words).join(' ');
  let operands = 0;
  for (let index = words; index < args.length; index += 1) {
    const part = args[index] as string;
    if (part.startsWith('-')) {
      const takesValue = shape.flags[part];
      if (takesValue === undefined) {
        return `\`devteam ${name}\` may not be passed \`${part}\``;
      }
      if (takesValue === 'value' || takesValue === 'repeatable') {
        index += 1;
        const value = args[index];
        if (value === undefined) return `\`${part}\` was passed with no value`;
        if (value.startsWith('-')) return `\`${part}\` was passed \`${value}\`, which would read as another flag`;
      }
      continue;
    }
    operands += 1;
    if (operands > shape.operands) {
      return `\`devteam ${name}\` takes ${shape.operands} operand${shape.operands === 1 ? '' : 's'}, not ${operands}`;
    }
  }
  return null;
}

/**
 * The `kind` an error document gets, per exit code. Exhaustive over the four non-zero
 * outcomes, so adding one is a compile error rather than a silent fall-through.
 */
const PROBLEM_KIND_BY_OUTCOME: Readonly<Record<'findings' | 'usage' | 'environment' | 'conflict', ProblemKind>> =
  Object.freeze({
    findings: 'findings',
    usage: 'usage',
    environment: 'environment',
    conflict: 'conflict',
  });

/**
 * Translate a `CliResult` into a screen-facing result, applying `validate` to a payload.
 *
 * The two codes that carry data — 0 and 1 — go down the same path and differ only in the
 * `outcome` field the UI reads. Codes 2, 3 and 4 become problems the UI states, with the
 * CLI's own `error` and `hint` text rather than a message invented here: the CLI's hints
 * are actionable and a paraphrase would be neither.
 */
function toOperationResult<T>(result: CliResult, validate: (body: Record<string, unknown>) => T | string): OperationResult<T> {
  if (!ranAndAnswered(result)) {
    const kind: ProblemKind = result.outcome;
    return {
      ok: false,
      kind,
      message: explain(result),
      ...(result.outcome === 'unavailable'
        ? { hint: 'The app needs a `devteam` CLI on this host; it deliberately bundles none.' }
        : {}),
      exitCode: result.outcome === 'contract-breach' ? result.exitCode : null,
      command: result.command.display,
      durationMs: result.durationMs,
    };
  }

  if (result.document.kind === 'error') {
    if (result.outcome === 'success') {
      // Exit 0 carrying an error document contradicts the contract in both directions;
      // there is no honest `kind` for it, so it is reported rather than labelled.
      return {
        ok: false,
        kind: 'contract-breach',
        message: `${result.command.display} exited 0 but emitted an error document: ${result.document.error}`,
        exitCode: result.exitCode,
        command: result.command.display,
        durationMs: result.durationMs,
      };
    }
    return {
      ok: false,
      // One entry per outcome that can carry an error document, so a code cannot fall
      // through to a label that is wrong. `findings` fell through to `'environment'`,
      // which titled an exit-1 error document "The environment is not ready".
      kind: PROBLEM_KIND_BY_OUTCOME[result.outcome],
      message: result.document.error,
      ...(result.document.hint !== undefined ? { hint: result.document.hint } : {}),
      ...(typeof result.document.details?.['reason'] === 'string' ? { reason: result.document.details['reason'] } : {}),
      exitCode: result.exitCode,
      command: result.command.display,
      durationMs: result.durationMs,
    };
  }

  if (result.outcome !== 'success' && result.outcome !== 'findings') {
    // Exit 2/3/4 with a *payload* rather than an error document. Nothing in the CLI
    // does this today; if something starts to, the shape is not what those codes mean
    // and the app says so instead of rendering it as data.
    return {
      ok: false,
      kind: 'contract-breach',
      message: `${result.command.display} exited ${result.exitCode} but emitted a success payload rather than an error document`,
      exitCode: result.exitCode,
      command: result.command.display,
      durationMs: result.durationMs,
    };
  }

  const validated = validate(result.document.body);
  if (typeof validated === 'string') {
    return {
      ok: false,
      kind: 'contract-breach',
      message: `${result.command.display} returned a document this app cannot read: ${validated}`,
      exitCode: result.exitCode,
      command: result.command.display,
      durationMs: result.durationMs,
    };
  }

  // A succeeding command's stderr is carried, not discarded: see `OperationResult.notice`
  // in `shared/api.ts` for the case that forced it (`bind` outside a git repository warns
  // that nothing was added to an ignore file, and the payload cannot say so). Spread
  // conditionally so the key is absent rather than `''` when there was nothing to say.
  const notice = (result.stderr ?? '').trim();
  return {
    ok: true,
    outcome: result.outcome,
    data: validated,
    command: result.command.display,
    durationMs: result.durationMs,
    ...(notice === '' ? {} : { notice }),
  };
}

/**
 * The one door to `invokeDevteam`, and the one place the allow-list is enforced.
 *
 * Exported so a test can hand it an argv no operation builds and assert that nothing is
 * spawned. Every operation below goes through it; a new one that does not would be
 * bypassing the boundary, which is the defect this function exists to make impossible.
 */
export async function run<T>(
  context: CliContext,
  args: readonly string[],
  validate: (body: Record<string, unknown>) => T | string,
): Promise<OperationResult<T>> {
  const problem = argvProblem(args);
  if (problem !== null) {
    return {
      ok: false,
      kind: 'refused',
      message: `this app refused to run it: ${problem}`,
      hint: 'Add the command to `COMMAND_SHAPES` deliberately, or fix the caller.',
      exitCode: null,
      command: `devteam ${args.join(' ')}`,
      durationMs: 0,
    };
  }
  // The caller's own `timeoutMs` wins; otherwise a write gets the long deadline and a read
  // keeps `invokeDevteam`'s default.
  const timeoutMs = context.timeoutMs ?? (isGatedArgv(args) ? GATED_TIMEOUT_MS : undefined);
  return toOperationResult(
    await invokeDevteam({ ...context, args, ...(timeoutMs !== undefined ? { timeoutMs } : {}) }),
    validate,
  );
}

/**
 * The shape of a version a project may be pinned to: the same one the CLI's `update.REF_RE`
 * accepts. The CLI joins a pin onto its versions directory, so an unchecked string such as
 * `../x` or `/abs` would point a project's hooks at arbitrary content. A version is
 * `vX.Y.Z` with an optional pre-release or build suffix and nothing else — no separators,
 * no leading dash, no whitespace.
 */
const PIN_RE = /^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;

/** Why `version` is not a pinnable version, or `null` when it is. */
export function pinProblem(version: string): string | null {
  return PIN_RE.test(version) ? null : `\`${version}\` is not a version (expected vX.Y.Z)`;
}

/** `--path <the app's own working directory>`, for the commands that accept it. */
function projectPathFlag(context: CliContext): readonly string[] {
  return ['--path', context.cwd];
}

// ── list ──────────────────────────────────────────────────────────────────────

/** Each key keeps only a value of the type the table can honestly render; anything else is `null`. */
function parseListPreferences(raw: Record<string, unknown>): NonNullable<ProjectRecord['preferences']> {
  const flag = (value: unknown): boolean | null => (typeof value === 'boolean' ? value : null);
  const muted = raw['suppress_notifications'];
  return {
    auto_update: flag(raw['auto_update']),
    worktree_active: flag(raw['worktree_active']),
    suppress_notifications: Array.isArray(muted)
      ? muted.filter((item): item is string => typeof item === 'string')
      : flag(muted),
  };
}

export function listProjects(context: CliContext): Promise<OperationResult<ProjectList>> {
  return run(context, ['list'], (body) => {
    if (!Array.isArray(body['projects'])) return 'no `projects` array';
    const projects: ProjectRecord[] = [];
    for (const raw of body['projects']) {
      if (!isRecord(raw)) return 'a project entry is not an object';
      if (typeof raw['project_id'] !== 'string' || typeof raw['path'] !== 'string') {
        return 'a project entry has no string `project_id` and `path`';
      }
      projects.push({
        project_id: raw['project_id'],
        path: raw['path'],
        providers: asStringArray(raw['providers']),
        mode: asNullableString(raw['mode']),
        pin: asNullableString(raw['pin']),
        resolves_to: asNullableString(raw['resolves_to']),
        // `=== true` turned an absent or non-boolean key into an affirmative `false`, and
        // the UI rendered that as a red `missing` badge beside a path that exists. Silence
        // is reported as silence; see `ProjectRecord.path_exists`.
        path_exists: typeof raw['path_exists'] === 'boolean' ? raw['path_exists'] : null,
        ...(isRecord(raw['preferences']) ? { preferences: parseListPreferences(raw['preferences']) } : {}),
      });
    }
    return { current: asNullableString(body['current']), projects };
  });
}

// ── catalog ───────────────────────────────────────────────────────────────────

export function catalogSummary(context: CliContext): Promise<OperationResult<CatalogSummary>> {
  return run(context, ['catalog', ...projectPathFlag(context)], (body) => {
    const counts = asCounts(body['counts']);
    if (typeof counts === 'string') return `\`counts\`: ${counts}`;
    const malformed = asCounts(body['malformed']);
    if (typeof malformed === 'string') return `\`malformed\`: ${malformed}`;
    return {
      version: asNullableString(body['version']),
      project_id: asNullableString(body['project_id']),
      counts,
      malformed,
    };
  });
}

export function catalogListing(context: CliContext, kind: CatalogKind): Promise<OperationResult<CatalogListing>> {
  if (!CATALOG_KINDS.includes(kind)) {
    // Not reachable from a well-behaved renderer; kept because "the renderer cannot ask
    // for an arbitrary command" has to hold even when the renderer is misbehaving.
    return Promise.resolve<OperationResult<CatalogListing>>({
      ok: false,
      kind: 'refused',
      message: `unknown catalog kind: ${String(kind)}`,
      exitCode: null,
      command: 'devteam catalog',
      durationMs: 0,
    });
  }
  return run(context, ['catalog', kind, ...projectPathFlag(context)], (body) => {
    const rows = body[kind];
    if (!Array.isArray(rows)) return `no \`${kind}\` array`;
    const entries: CatalogEntry[] = [];
    for (const raw of rows) {
      if (!isRecord(raw)) return `a ${kind} entry is not an object`;
      if (typeof raw['name'] !== 'string') return `a ${kind} entry has no string \`name\``;
      entries.push(asEntry(raw, raw['name']));
    }
    return {
      kind,
      version: asNullableString(body['version']),
      project_id: asNullableString(body['project_id']),
      count: typeof body['count'] === 'number' ? body['count'] : entries.length,
      entries,
    };
  });
}

/**
 * One catalog entry by name.
 *
 * A name beginning with `-` is refused rather than passed on. No shell is involved, so
 * there is no injection here — but `argparse` would read `--json` or `--path` as a flag,
 * and a renderer that could choose a flag could choose one this app never meant to send.
 * Refusing the shape is cheaper than reasoning about which flags are harmless.
 */
export function catalogEntry(context: CliContext, name: string): Promise<OperationResult<CatalogDetail>> {
  const problem = validateEntryName(name);
  if (problem !== null) {
    return Promise.resolve<OperationResult<CatalogDetail>>({
      ok: false,
      kind: 'refused',
      message: problem,
      exitCode: null,
      command: 'devteam catalog show',
      durationMs: 0,
    });
  }
  // The trimmed name, not the raw one: `validateEntryName` judged `name.trim()`, so a
  // name with trailing whitespace was validated in one form and spawned in another.
  return run(context, ['catalog', 'show', name.trim(), ...projectPathFlag(context)], (body) => {
    if (typeof body['name'] !== 'string') return 'no string `name`';
    if (typeof body['kind'] !== 'string') return 'no string `kind`';
    return {
      ...asEntry(body, body['name']),
      kind: body['kind'],
      body: typeof body['body'] === 'string' ? body['body'] : '',
      project_id: asNullableString(body['project_id']),
    };
  });
}

export function validateEntryName(name: unknown): string | null {
  if (typeof name !== 'string') return 'a catalog entry name must be a string';
  const trimmed = name.trim();
  if (trimmed === '') return 'a catalog entry name cannot be empty';
  if (trimmed.startsWith('-')) return 'a catalog entry name cannot begin with "-"; it would be read as a flag';
  if (trimmed.length > 200) return 'a catalog entry name cannot be longer than 200 characters';
  return null;
}

// ── doctor ────────────────────────────────────────────────────────────────────

export function doctor(context: CliContext): Promise<OperationResult<DoctorReport>> {
  // `--no-project`: the CLI's own switch for "check the store only, ignoring the cwd".
  // Without it the project findings changed with the directory the app happened to be
  // launched from — `ok` from inside a bound project, `warn` with "/ is not a bound
  // project" from a Finder launch. This build has no project picker, so "no project" is
  // the true answer and the Diagnosis screen states it.
  return run(context, ['doctor', '--no-project'], (body) => {
    if (typeof body['status'] !== 'string') return 'no string `status`';
    if (!Array.isArray(body['findings'])) return 'no `findings` array';
    if (!Array.isArray(body['actions'])) return 'no `actions` array';
    const findings: DoctorFinding[] = [];
    for (const raw of body['findings']) {
      if (!isRecord(raw)) return 'a finding is not an object';
      findings.push({
        level: typeof raw['level'] === 'string' ? raw['level'] : 'unknown',
        category: typeof raw['category'] === 'string' ? raw['category'] : 'unknown',
        message: typeof raw['message'] === 'string' ? raw['message'] : '',
        ...(typeof raw['hint'] === 'string' ? { hint: raw['hint'] } : {}),
      });
    }
    return {
      status: body['status'],
      findings,
      // `actions` is a list of things doctor *did*. Rendered as text; shape is not pinned
      // per-item by the contract test, so anything non-string is stringified rather than
      // dropped — a repair the app silently hid would be worse than an ugly line.
      actions: body['actions'].map((entry) => (typeof entry === 'string' ? entry : JSON.stringify(entry))),
    };
  });
}

// ── write actions ────────────────────────────────────────────────────────────
//
// Every function below takes an already-resolved target — a `path` `main/ipc.ts`
// offered or resolved from a `project_id` against `list`, never a bare renderer
// string. That resolution, and the closed-union validation of `BindRequest`, are the
// main process's job; this file only builds the argv and reads the answer back.

/** What `bindProject` accepts beyond the target path, mirroring `BindRequest` minus `path`. */
export interface BindOptions {
  readonly providers?: readonly BindProvider[];
  readonly mode?: BindMode;
  readonly pin?: string | null;
}

export function bindProject(
  context: CliContext,
  path: string,
  options: BindOptions = {},
): Promise<OperationResult<BindReport>> {
  const args: string[] = ['bind', path];
  for (const provider of options.providers ?? []) {
    args.push('--provider', provider);
  }
  if (options.mode !== undefined) args.push('--mode', options.mode);
  // `null` and `undefined` both mean "no pin at bind time" — `bind` has no `--release`
  // of its own the way `pin` does, so there is nothing an explicit `null` could mean
  // beyond omitting the flag.
  if (typeof options.pin === 'string') args.push('--pin', options.pin);
  return run(context, args, asBindReport);
}

/**
 * `projectId` goes straight to `--project-id`: `bind_module.unbind` resolves that flag
 * itself, so unlike `pin`/`upgrade` this needs no path resolved first. `main/ipc.ts`
 * still confirms the id against `list` before calling this, so nothing is spawned for
 * an id the registry does not know.
 */
export function unbindProject(context: CliContext, projectId: string): Promise<OperationResult<UnbindReport>> {
  return run(context, ['unbind', '--project-id', projectId], asUnbindReport);
}

/** Same reasoning as `unbindProject`: `sync --project-id` needs no path. */
export function syncProject(context: CliContext, projectId: string): Promise<OperationResult<BindReport>> {
  return run(context, ['sync', '--project-id', projectId], asBindReport);
}

export function syncAllProjects(context: CliContext): Promise<OperationResult<SyncAllReport>> {
  return run(context, ['sync', '--all'], asSyncAllReport);
}

/**
 * `path` is the project's resolved location, not its id — `cmd_pin` has no
 * `--project-id`. `version === null` is `pin --release`; it must never become `pin ''`,
 * which `cmd_pin` would read as "no version and no --release" and refuse.
 */
export function setPin(context: CliContext, path: string, version: string | null): Promise<OperationResult<PinReport>> {
  if (version !== null) {
    const problem = pinProblem(version);
    if (problem !== null) {
      return Promise.resolve({
        ok: false,
        kind: 'refused',
        message: `this app refused to run it: ${problem}`,
        exitCode: null,
        command: 'devteam pin',
        durationMs: 0,
      });
    }
  }
  const args = version === null ? ['pin', '--path', path, '--release'] : ['pin', version, '--path', path];
  return run(context, args, asPinReport);
}

/** `path` is resolved the same way as `setPin`'s — `upgrade` takes only a path. */
export function planUpgrade(context: CliContext, path: string): Promise<OperationResult<UpgradePlan>> {
  return run(context, ['upgrade', path], asUpgradePlan);
}

export function applyUpgrade(context: CliContext, path: string): Promise<OperationResult<UpgradeReport>> {
  return run(context, ['upgrade', path, '--apply'], asUpgradeReport);
}

/**
 * `devteam migrate`, for a directory the picker offered (as `bindProject`). The plan and
 * the apply take the same options, so what the user reviewed is what runs. The apply
 * always passes `--untrack`: the app's migration ends with the old paths out of git's
 * index, ready for the user's own commit — see `MigrationReport`.
 */
function migrateArgs(path: string, options: MigrateOptions): string[] {
  const args: string[] = ['migrate', path];
  for (const provider of options.providers ?? []) args.push('--provider', provider);
  if (options.mode !== undefined) args.push('--mode', options.mode);
  return args;
}

export type MigrateOptions = Pick<BindOptions, 'providers' | 'mode'>;

export function planMigration(
  context: CliContext,
  path: string,
  options: MigrateOptions = {},
): Promise<OperationResult<MigrationPlan>> {
  return run(context, migrateArgs(path, options), asMigrationPlan);
}

export function applyMigration(
  context: CliContext,
  path: string,
  options: MigrateOptions = {},
): Promise<OperationResult<MigrationReport>> {
  return run(context, [...migrateArgs(path, options), '--apply', '--untrack'], asMigrationReport);
}

// ── preferences ─────────────────────────────────────────────────────────────────
//
// `path` is resolved by `main/ipc.ts` from a `project_id`, as for `setPin`. Writes are
// always `--scope project`; see the `COMMAND_SHAPES` comment for why never `global`.

export function prefsList(context: CliContext, path: string): Promise<OperationResult<ProjectPreferences>> {
  return run(context, ['prefs', 'list', '--path', path], asProjectPreferences);
}

export function prefsSet(
  context: CliContext,
  path: string,
  key: string,
  value: PreferenceValue,
): Promise<OperationResult<PreferenceWrite>> {
  const problem = preferenceArgumentProblem(key, value);
  if (problem !== null) return Promise.resolve(refusedPreference('set', problem));
  return run(
    context,
    ['prefs', 'set', key, serializePreference(value), '--scope', 'project', '--path', path],
    asPreferenceWrite,
  );
}

export function prefsUnset(context: CliContext, path: string, key: string): Promise<OperationResult<PreferenceWrite>> {
  const problem = preferenceArgumentProblem(key, null);
  if (problem !== null) return Promise.resolve(refusedPreference('unset', problem));
  return run(context, ['prefs', 'unset', key, '--scope', 'project', '--path', path], asPreferenceWrite);
}

/**
 * The string `prefs set` parses back into `value`. `_coerce` in `prefs.py` reads `null`
 * (and the empty string) as `None` and `true`/`false` as booleans before it looks at the
 * default's type, so those spellings are the contract rather than a convenience.
 */
export function serializePreference(value: PreferenceValue): string {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/**
 * Why this key/value may not reach an argv, or `null`. A value is refused when `_coerce`
 * would read it as something else (`''` becomes `None`, `"true"` becomes a boolean) or
 * when `argparse` would read it as a flag.
 */
export function preferenceArgumentProblem(key: unknown, value: unknown): string | null {
  if (typeof key !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(key)) {
    return 'a preference key must be lowercase letters, digits and underscores';
  }
  if (value === null || typeof value === 'boolean') return null;
  if (typeof value === 'number') {
    return Number.isFinite(value) && value >= 0 ? null : 'a numeric preference must be a finite, non-negative number';
  }
  if (typeof value !== 'string') return 'a preference value must be a string, number, boolean or null';
  return textProblem(value);
}

function refusedPreference(verb: 'set' | 'unset', message: string): OperationResult<never> {
  return { ok: false, kind: 'refused', message, exitCode: null, command: `devteam prefs ${verb}`, durationMs: 0 };
}

/** `prefs list --json`. */
export function asProjectPreferences(body: Record<string, unknown>): ProjectPreferences | string {
  if (!isRecord(body['values'])) return 'no `values` object';
  if (!isRecord(body['origin'])) return 'no `origin` object';
  if (typeof body['version'] !== 'string') return 'no string `version`';
  const origin: Record<string, string> = {};
  for (const [key, layer] of Object.entries(body['origin'])) {
    if (typeof layer === 'string') origin[key] = layer;
  }
  return {
    project_id: asNullableString(body['project_id']),
    version: body['version'],
    values: { ...body['values'] },
    origin,
    unknown: asStringArray(body['unknown']),
  };
}

/** `prefs set --json` and `prefs unset --json`, which share `key`, `scope` and `file`. */
export function asPreferenceWrite(body: Record<string, unknown>): PreferenceWrite | string {
  if (typeof body['key'] !== 'string') return 'no string `key`';
  if (typeof body['scope'] !== 'string') return 'no string `scope`';
  return {
    key: body['key'],
    scope: body['scope'],
    ...(typeof body['removed'] === 'boolean' ? { removed: body['removed'] } : {}),
  };
}

// ── plugins (ADR-0019) ───────────────────────────────────────────────────────────────
//
// `path` is resolved by `main/ipc.ts` from a `project_id`, as for `prefsList`. `name`,
// `key` and `actionId` are checked there against the project's own `plugin list` answer;
// the shape checks here are the second line, so an operand that would read as a flag or
// that no manifest could declare never reaches an argv.

/**
 * `plugin list` runs the status script of every enabled plugin in turn, each allowed up to
 * 30 s by the CLI. A fixed 60 s gave up under three slow plugins; the plugin count is
 * not known before the list answers, so this is a flat ceiling: 15 s of overhead plus six
 * slow status scripts, past any realistic install.
 */
export const PLUGIN_LIST_TIMEOUT_MS = 180_000;
/** `plugin enable` may run a `config` action to seed the settings (`seeded: true`). */
export const PLUGIN_ENABLE_TIMEOUT_MS = 120_000;
/** The longest a manifest may declare (the CLI's own cap), and what an action with no declared timeout gets. */
export const PLUGIN_RUN_MAX_SECONDS = 3600;
/** Added to the action's own timeout so the CLI's deadline trips, and reports, before ours. */
export const PLUGIN_RUN_MARGIN_SECONDS = 30;

function refusedPlugin(command: string, message: string): OperationResult<never> {
  return { ok: false, kind: 'refused', message, exitCode: null, command: `devteam ${command}`, durationMs: 0 };
}

export function pluginNameProblem(name: unknown): string | null {
  return typeof name === 'string' && PLUGIN_NAME.test(name) ? null : 'a plugin name is lowercase letters, digits and dashes';
}

export function pluginListArgs(path: string): readonly string[] {
  return ['plugin', 'list', '--path', path];
}

export function pluginList(context: CliContext, path: string): Promise<OperationResult<PluginList>> {
  return run({ ...context, timeoutMs: PLUGIN_LIST_TIMEOUT_MS }, pluginListArgs(path), asPluginList);
}

export function pluginEnable(context: CliContext, path: string, name: string): Promise<OperationResult<PluginToggleReport>> {
  const problem = pluginNameProblem(name);
  if (problem !== null) return Promise.resolve(refusedPlugin('plugin enable', problem));
  return run({ ...context, timeoutMs: PLUGIN_ENABLE_TIMEOUT_MS }, ['plugin', 'enable', name, '--path', path], asPluginToggle);
}

export function pluginDisable(context: CliContext, path: string, name: string): Promise<OperationResult<PluginToggleReport>> {
  const problem = pluginNameProblem(name);
  if (problem !== null) return Promise.resolve(refusedPlugin('plugin disable', problem));
  return run(context, ['plugin', 'disable', name, '--path', path], asPluginToggle);
}

/** `value` is already the CLI's spelling — see `serializePluginValue`. */
export function pluginConfigSet(
  context: CliContext,
  path: string,
  name: string,
  key: string,
  value: string,
): Promise<OperationResult<PluginConfigWrite>> {
  const problem = pluginNameProblem(name) ?? pluginKeyProblem(key) ?? pluginArgumentProblem(value);
  if (problem !== null) return Promise.resolve(refusedPlugin('plugin config set', problem));
  return run(context, ['plugin', 'config', 'set', name, key, value, '--path', path], asPluginConfigWrite);
}

export function pluginConfigUnset(
  context: CliContext,
  path: string,
  name: string,
  key: string,
): Promise<OperationResult<PluginConfigWrite>> {
  const problem = pluginNameProblem(name) ?? pluginKeyProblem(key);
  if (problem !== null) return Promise.resolve(refusedPlugin('plugin config unset', problem));
  return run(context, ['plugin', 'config', 'unset', name, key, '--path', path], asPluginConfigWrite);
}

/**
 * `timeoutSeconds` is the action's own `timeout_seconds` from the last `plugin list`, or
 * `null` when the CLI did not send one. Either way the deadline is capped, so a hostile
 * or malformed number cannot hold a process open for longer than the manifest maximum.
 */
export function pluginRun(
  context: CliContext,
  path: string,
  name: string,
  actionId: string,
  timeoutSeconds: number | null,
): Promise<OperationResult<PluginRunResult>> {
  const problem =
    pluginNameProblem(name) ?? (PLUGIN_ACTION_ID.test(actionId) ? null : 'an action id is lowercase letters, digits, dashes and underscores');
  if (problem !== null) return Promise.resolve(refusedPlugin('plugin run', problem));
  return run(
    { ...context, timeoutMs: pluginRunTimeoutMs(timeoutSeconds), cancelOnQuit: true },
    ['plugin', 'run', name, actionId, '--path', path],
    asPluginRunResult,
  );
}

export function pluginRunTimeoutMs(timeoutSeconds: number | null): number {
  const declared =
    timeoutSeconds !== null && Number.isFinite(timeoutSeconds) && timeoutSeconds > 0
      ? Math.min(timeoutSeconds, PLUGIN_RUN_MAX_SECONDS)
      : PLUGIN_RUN_MAX_SECONDS;
  return (declared + PLUGIN_RUN_MARGIN_SECONDS) * 1000;
}

function pluginKeyProblem(key: unknown): string | null {
  return typeof key === 'string' && PLUGIN_CONFIG_KEY.test(key) ? null : 'a config key is letters, digits and underscores';
}

/** `argparse` would read a value beginning with `-` as a flag, and `''` is not a value. */
function pluginArgumentProblem(value: unknown): string | null {
  if (typeof value !== 'string' || value === '') return 'a config value must be a non-empty string';
  if (value.startsWith('-')) return 'a config value cannot begin with "-"; it would be read as a flag';
  return null;
}

// ── plugin payload validation ───────────────────────────────────────────────────────

const PLUGIN_ACTION_OUTPUTS = ['config', 'json', 'log'];

function asPluginConfigField(raw: unknown): PluginConfigField | string {
  if (!isRecord(raw)) return 'a `config_fields` entry is not an object';
  if (typeof raw['key'] !== 'string') return 'a `config_fields` entry has no string `key`';
  if (typeof raw['type'] !== 'string') return `\`config_fields.${raw['key']}\` has no string \`type\``;
  const options: { value: string; label: string }[] = [];
  if (Array.isArray(raw['options'])) {
    for (const option of raw['options']) {
      if (isRecord(option) && typeof option['value'] === 'string') {
        options.push({ value: option['value'], label: typeof option['label'] === 'string' ? option['label'] : option['value'] });
      }
    }
  }
  return {
    key: raw['key'],
    type: raw['type'],
    label: typeof raw['label'] === 'string' ? raw['label'] : raw['key'],
    help: asNullableString(raw['help']),
    required: raw['required'] === true,
    default: raw['default'] ?? null,
    placeholder: asNullableString(raw['placeholder']),
    options,
    min: typeof raw['min'] === 'number' ? raw['min'] : null,
    max: typeof raw['max'] === 'number' ? raw['max'] : null,
  };
}

function asPluginAction(raw: unknown): PluginAction | string {
  if (!isRecord(raw)) return 'an `actions` entry is not an object';
  if (typeof raw['id'] !== 'string') return 'an `actions` entry has no string `id`';
  const output = typeof raw['output'] === 'string' ? raw['output'] : 'log';
  return {
    id: raw['id'],
    label: typeof raw['label'] === 'string' ? raw['label'] : raw['id'],
    help: asNullableString(raw['help']),
    // An output kind a newer CLI adds is kept, and shown as a log: that is the only way to
    // render an unfamiliar answer without inventing a meaning for it.
    output: PLUGIN_ACTION_OUTPUTS.includes(output) ? output : 'log',
    requires_enabled: raw['requires_enabled'] === true,
    writes: raw['writes'] === true,
    timeout_seconds: typeof raw['timeout_seconds'] === 'number' ? raw['timeout_seconds'] : null,
  };
}

/** A fact is display text; a number or boolean the script printed is still shown, an object is not guessed at. */
function asFactValue(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function asPluginStatus(raw: unknown): PluginStatus | null {
  if (!isRecord(raw) || typeof raw['summary'] !== 'string') return null;
  const facts: { label: string; value: string }[] = [];
  if (Array.isArray(raw['facts'])) {
    for (const fact of raw['facts']) {
      if (isRecord(fact) && typeof fact['label'] === 'string') {
        facts.push({ label: fact['label'], value: asFactValue(fact['value']) });
      }
    }
  }
  return { summary: raw['summary'], facts };
}

/** One `PluginView`: `plugin show`, and each entry of `plugin list`'s `plugins`. */
export function asPluginView(raw: unknown): PluginView | string {
  if (!isRecord(raw)) return 'a plugin entry is not an object';
  const name = raw['name'];
  if (typeof name !== 'string' || !PLUGIN_NAME.test(name)) return 'a plugin entry has no valid string `name`';
  for (const key of ['enabled', 'ready', 'configured'] as const) {
    if (typeof raw[key] !== 'boolean') return `plugin \`${name}\` has no boolean \`${key}\``;
  }
  if (!Array.isArray(raw['config_fields'])) return `plugin \`${name}\` has no \`config_fields\` array`;
  if (!Array.isArray(raw['actions'])) return `plugin \`${name}\` has no \`actions\` array`;
  if (raw['config'] !== undefined && !isRecord(raw['config'])) return `plugin \`${name}\` has a \`config\` that is not an object`;

  const config_fields: PluginConfigField[] = [];
  for (const entry of raw['config_fields']) {
    const field = asPluginConfigField(entry);
    if (typeof field === 'string') return `plugin \`${name}\`: ${field}`;
    config_fields.push(field);
  }
  const actions: PluginAction[] = [];
  for (const entry of raw['actions']) {
    const action = asPluginAction(entry);
    if (typeof action === 'string') return `plugin \`${name}\`: ${action}`;
    actions.push(action);
  }
  const requirements: PluginRequirement[] = [];
  if (Array.isArray(raw['requirements'])) {
    for (const entry of raw['requirements']) {
      if (!isRecord(entry) || typeof entry['binary'] !== 'string') return `plugin \`${name}\`: a requirement has no string \`binary\``;
      requirements.push({
        binary: entry['binary'],
        // A requirement the CLI did not say was found is treated as missing: the safe
        // direction, since it only ever withholds a switch.
        found: entry['found'] === true,
        install_hint: asNullableString(entry['install_hint']),
      });
    }
  }
  return {
    name,
    title: typeof raw['title'] === 'string' ? raw['title'] : name,
    description: typeof raw['description'] === 'string' ? raw['description'] : '',
    homepage: asNullableString(raw['homepage']),
    enabled: raw['enabled'] as boolean,
    source: typeof raw['source'] === 'string' ? raw['source'] : 'none',
    settings_file: typeof raw['settings_file'] === 'string' ? raw['settings_file'] : `.dev-team-agents/plugin-settings/${name}.json`,
    requirements,
    ready: raw['ready'] as boolean,
    configured: raw['configured'] as boolean,
    config_fields,
    config: isRecord(raw['config']) ? { ...raw['config'] } : {},
    unknown_config: asStringArray(raw['unknown_config']),
    actions,
    hooks: asStringArray(raw['hooks']),
    status: asPluginStatus(raw['status']),
  };
}

/** `plugin list --json`. */
export function asPluginList(body: Record<string, unknown>): PluginList | string {
  if (!Array.isArray(body['plugins'])) return 'no `plugins` array';
  const plugins: PluginView[] = [];
  for (const raw of body['plugins']) {
    const view = asPluginView(raw);
    if (typeof view === 'string') return view;
    plugins.push(view);
  }
  return { project_id: asNullableString(body['project_id']), plugins, invalid: asInvalidPlugins(body['invalid']) };
}

/** Additive field: absent, or an entry of the wrong shape, is dropped rather than failing the list. */
function asInvalidPlugins(value: unknown): InvalidPlugin[] {
  if (!Array.isArray(value)) return [];
  const invalid: InvalidPlugin[] = [];
  for (const raw of value) {
    if (!isRecord(raw) || typeof raw['name_or_dir'] !== 'string') continue;
    invalid.push({
      name_or_dir: raw['name_or_dir'],
      problem: typeof raw['problem'] === 'string' ? raw['problem'] : 'unknown problem',
    });
  }
  return invalid;
}

/** `plugin enable --json` and `plugin disable --json`. */
export function asPluginToggle(body: Record<string, unknown>): PluginToggleReport | string {
  const plugin = asPluginView(body['plugin']);
  if (typeof plugin === 'string') return `\`plugin\`: ${plugin}`;
  if (typeof body['changed'] !== 'boolean') return 'no boolean `changed`';
  return { plugin, changed: body['changed'], seeded: body['seeded'] === true };
}

/** `plugin config set --json` and `plugin config unset --json`. */
export function asPluginConfigWrite(body: Record<string, unknown>): PluginConfigWrite | string {
  const plugin = asPluginView(body['plugin']);
  if (typeof plugin === 'string') return `\`plugin\`: ${plugin}`;
  if (typeof body['key'] !== 'string') return 'no string `key`';
  return { plugin, key: body['key'], ...(typeof body['removed'] === 'boolean' ? { removed: body['removed'] } : {}) };
}

/** `plugin run --json`. */
export function asPluginRunResult(body: Record<string, unknown>): PluginRunResult | string {
  if (typeof body['plugin'] !== 'string') return 'no string `plugin`';
  if (typeof body['action'] !== 'string') return 'no string `action`';
  if (typeof body['ok'] !== 'boolean') return 'no boolean `ok`';
  if (typeof body['exit_code'] !== 'number') return 'no numeric `exit_code`';
  if (typeof body['duration_ms'] !== 'number') return 'no numeric `duration_ms`';
  const output = body['output'];
  if (output !== null && output !== undefined && !isRecord(output)) return '`output` is neither an object nor null';
  return {
    plugin: body['plugin'],
    action: body['action'],
    ok: body['ok'],
    exit_code: body['exit_code'],
    duration_ms: body['duration_ms'],
    output: isRecord(output) ? { ...output } : null,
    log_tail: typeof body['log_tail'] === 'string' ? body['log_tail'] : '',
  };
}

// ── write-action payload validation ─────────────────────────────────────────────
//
// Exported, unlike `asCounts`/`asEntry` above: `test/operations.test.ts` exercises each
// of these against the real payload shapes captured from the CLI, independent of
// spawning anything, the way `validateEntryName` is already tested directly.

/**
 * `bind --json` and single-project `sync --json`. Shared because the two commands
 * answer with the same document — `sync` adds `worktrees`, which is why it is read as
 * optional here rather than the two call sites keeping separate near-identical readers.
 */
export function asBindReport(body: Record<string, unknown>): BindReport | string {
  if (typeof body['path'] !== 'string') return 'no string `path`';
  if (typeof body['project_id'] !== 'string') return 'no string `project_id`';
  if (typeof body['version'] !== 'string') return 'no string `version`';
  if (typeof body['mode'] !== 'string') return 'no string `mode`';
  if (!Array.isArray(body['providers'])) return 'no `providers` array';
  if (typeof body['artifacts'] !== 'number') return 'no numeric `artifacts`';
  if (typeof body['identity_created'] !== 'boolean') return 'no boolean `identity_created`';
  if (typeof body['gitignore'] !== 'string') return 'no string `gitignore`';
  if (typeof body['git_exclude'] !== 'string') return 'no string `git_exclude`';
  if (!Array.isArray(body['retired'])) return 'no `retired` array';
  if (!Array.isArray(body['merged_project_files'])) return 'no `merged_project_files` array';

  let pruned: BindReport['pruned'];
  const prunedRaw = body['pruned'];
  if (prunedRaw !== undefined) {
    if (!isRecord(prunedRaw) || !Array.isArray(prunedRaw['unlinked']) || !Array.isArray(prunedRaw['quarantined'])) {
      return '`pruned` is present but not `{unlinked: [], quarantined: []}`';
    }
    pruned = { unlinked: asStringArray(prunedRaw['unlinked']), quarantined: prunedRaw['quarantined'] };
  }

  let preferencesImport: BindReport['preferences_import'];
  const importRaw = body['preferences_import'];
  if (importRaw !== undefined) {
    const parsed = importRaw === null ? null : asPreferencesImport(importRaw);
    if (typeof parsed === 'string') return `\`preferences_import\`: ${parsed}`;
    preferencesImport = parsed;
  }

  let worktrees: BindReport['worktrees'];
  const worktreesRaw = body['worktrees'];
  if (worktreesRaw !== undefined) {
    if (!Array.isArray(worktreesRaw)) return '`worktrees` is present but not an array';
    worktrees = worktreesRaw;
  }

  return {
    path: body['path'],
    project_id: body['project_id'],
    version: body['version'],
    mode: body['mode'],
    providers: asStringArray(body['providers']),
    artifacts: body['artifacts'],
    identity_created: body['identity_created'],
    gitignore: body['gitignore'],
    git_exclude: body['git_exclude'],
    pin: asNullableString(body['pin']),
    fallback_reason: asNullableString(body['fallback_reason']),
    retired: body['retired'],
    merged_project_files: asStringArray(body['merged_project_files']),
    ...(pruned !== undefined ? { pruned } : {}),
    ...(worktrees !== undefined ? { worktrees } : {}),
    ...(preferencesImport !== undefined ? { preferences_import: preferencesImport } : {}),
  };
}

/** `preferences_import` inside a bind or sync report. */
export function asPreferencesImport(raw: unknown): PreferencesImport | string {
  if (!isRecord(raw)) return 'not an object';
  if (typeof raw['source'] !== 'string') return 'no string `source`';
  for (const key of ['imported', 'unchanged', 'conflicts', 'ignored'] as const) {
    if (!Array.isArray(raw[key])) return `no \`${key}\` array`;
  }
  const ignored = (raw['ignored'] as unknown[]).flatMap((entry) =>
    isRecord(entry) && typeof entry['key'] === 'string'
      ? [{ key: entry['key'], reason: typeof entry['reason'] === 'string' ? entry['reason'] : 'unknown' }]
      : [],
  );
  return {
    source: raw['source'],
    imported: asStringArray(raw['imported']),
    unchanged: asStringArray(raw['unchanged']),
    conflicts: asStringArray(raw['conflicts']),
    ignored,
    quarantined: asNullableString(raw['quarantined']),
    problem: asNullableString(raw['problem']),
  };
}

/** `sync --all --json`. */
export function asSyncAllReport(body: Record<string, unknown>): SyncAllReport | string {
  const syncedRaw = body['synced'];
  if (!Array.isArray(syncedRaw)) return 'no `synced` array';
  const synced: BindReport[] = [];
  for (const raw of syncedRaw) {
    if (!isRecord(raw)) return 'a `synced` entry is not an object';
    const report = asBindReport(raw);
    if (typeof report === 'string') return `a \`synced\` entry: ${report}`;
    synced.push(report);
  }
  if (!Array.isArray(body['problems'])) return 'no `problems` array';
  return { synced, problems: body['problems'] };
}

/** `unbind --json`. */
export function asUnbindReport(body: Record<string, unknown>): UnbindReport | string {
  if (typeof body['path'] !== 'string') return 'no string `path`';
  if (typeof body['project_id'] !== 'string') return 'no string `project_id`';
  if (!Array.isArray(body['unlinked'])) return 'no `unlinked` array';
  if (!Array.isArray(body['quarantined'])) return 'no `quarantined` array';
  if (!Array.isArray(body['kept'])) return 'no `kept` array';
  if (!Array.isArray(body['problems'])) return 'no `problems` array';
  const quarantined = body['quarantined'].map((entry) =>
    isRecord(entry) && typeof entry['to'] === 'string' ? { to: entry['to'] } : {},
  );
  return {
    path: body['path'],
    project_id: body['project_id'],
    unlinked: asStringArray(body['unlinked']),
    quarantined,
    kept: asStringArray(body['kept']),
    problems: body['problems'],
  };
}

/** `pin <version> --json` and `pin --release --json`. */
export function asPinReport(body: Record<string, unknown>): PinReport | string {
  if (typeof body['project_id'] !== 'string') return 'no string `project_id`';
  if (typeof body['path'] !== 'string') return 'no string `path`';
  return { project_id: body['project_id'], path: body['path'], pin: asNullableString(body['pin']) };
}

/** `upgrade --json` without `--apply` — a preview; nothing was written. */
function asMoves(raw: unknown): MigrationMove[] | null {
  if (!Array.isArray(raw)) return null;
  const moves: MigrationMove[] = [];
  for (const item of raw) {
    if (typeof item !== 'object' || item === null) return null;
    const record = item as Record<string, unknown>;
    if (typeof record['from'] !== 'string' || typeof record['to'] !== 'string') return null;
    moves.push({ from: record['from'], to: record['to'] });
  }
  return moves;
}

export function asMigrationPlan(body: Record<string, unknown>): MigrationPlan | string {
  if (typeof body['path'] !== 'string') return 'no string `path`';
  if (typeof body['layout'] !== 'string') return 'no string `layout`';
  if (typeof body['install_dir'] !== 'string') return 'no string `install_dir`';
  if (typeof body['mode'] !== 'string') return 'no string `mode`';
  if (typeof body['adopts_identity'] !== 'boolean') return 'no boolean `adopts_identity`';
  for (const key of ['providers', 'actions', 'context_paths_added', 'git_tracked', 'git_tracked_artifacts', 'preserved']) {
    if (!Array.isArray(body[key])) return `no \`${key}\` array`;
  }
  const moves = asMoves(body['memory_moves']);
  if (moves === null) return 'no well-formed `memory_moves` array';
  return {
    path: body['path'],
    layout: body['layout'],
    install_dir: body['install_dir'],
    providers: asStringArray(body['providers']),
    mode: body['mode'],
    actions: asStringArray(body['actions']),
    adopts_identity: body['adopts_identity'],
    memory_moves: moves,
    context_paths_added: asStringArray(body['context_paths_added']),
    git_tracked: asStringArray(body['git_tracked']),
    git_tracked_artifacts: asStringArray(body['git_tracked_artifacts']),
    preserved: asStringArray(body['preserved']),
  };
}

export function asMigrationReport(body: Record<string, unknown>): MigrationReport | string {
  for (const key of ['path', 'layout', 'project_id', 'version', 'mode']) {
    if (typeof body[key] !== 'string') return `no string \`${key}\``;
  }
  if (typeof body['adopted_identity'] !== 'boolean') return 'no boolean `adopted_identity`';
  for (const key of ['providers', 'context_paths_added', 'retired_links', 'git_tracked', 'git_tracked_artifacts', 'untracked', 'unrecognised']) {
    if (!Array.isArray(body[key])) return `no \`${key}\` array`;
  }
  const memory = asMoves(body['memory_moved']);
  if (memory === null) return 'no well-formed `memory_moved` array';
  const quarantined = asMoves(body['quarantined']);
  if (quarantined === null) return 'no well-formed `quarantined` array';
  const quarantineDir = body['quarantine_dir'];
  if (quarantineDir !== null && typeof quarantineDir !== 'string') return '`quarantine_dir` is neither a string nor null';
  const problem = body['untrack_problem'];
  if (problem !== null && typeof problem !== 'string') return '`untrack_problem` is neither a string nor null';
  return {
    path: body['path'] as string,
    layout: body['layout'] as string,
    project_id: body['project_id'] as string,
    version: body['version'] as string,
    mode: body['mode'] as string,
    providers: asStringArray(body['providers']),
    adopted_identity: body['adopted_identity'],
    memory_moved: memory,
    context_paths_added: asStringArray(body['context_paths_added']),
    quarantined,
    quarantine_dir: quarantineDir,
    retired_links: asStringArray(body['retired_links']),
    git_tracked: asStringArray(body['git_tracked']),
    git_tracked_artifacts: asStringArray(body['git_tracked_artifacts']),
    untracked: asStringArray(body['untracked']),
    untrack_problem: problem,
    unrecognised: asStringArray(body['unrecognised']),
  };
}

export function asUpgradePlan(body: Record<string, unknown>): UpgradePlan | string {
  if (typeof body['path'] !== 'string') return 'no string `path`';
  if (typeof body['project_id'] !== 'string') return 'no string `project_id`';
  if (typeof body['from_layout'] !== 'number') return 'no numeric `from_layout`';
  if (typeof body['to_layout'] !== 'number') return 'no numeric `to_layout`';
  if (typeof body['files'] !== 'number') return 'no numeric `files`';
  if (typeof body['source'] !== 'string') return 'no string `source`';
  if (typeof body['destination'] !== 'string') return 'no string `destination`';
  if (typeof body['state_destination'] !== 'string') return 'no string `state_destination`';
  if (!Array.isArray(body['machine_local'])) return 'no `machine_local` array';
  if (!Array.isArray(body['retained'])) return 'no `retained` array';
  if (!Array.isArray(body['collisions'])) return 'no `collisions` array';
  if (!Array.isArray(body['git_tracked'])) return 'no `git_tracked` array';
  if (!Array.isArray(body['actions'])) return 'no `actions` array';
  return {
    path: body['path'],
    project_id: body['project_id'],
    from_layout: body['from_layout'],
    to_layout: body['to_layout'],
    files: body['files'],
    source: body['source'],
    destination: body['destination'],
    state_destination: body['state_destination'],
    machine_local: asStringArray(body['machine_local']),
    retained: asStringArray(body['retained']),
    collisions: asStringArray(body['collisions']),
    git_tracked: asStringArray(body['git_tracked']),
    actions: asStringArray(body['actions']),
  };
}

/** `upgrade --apply --json`. */
export function asUpgradeReport(body: Record<string, unknown>): UpgradeReport | string {
  if (typeof body['path'] !== 'string') return 'no string `path`';
  if (typeof body['project_id'] !== 'string') return 'no string `project_id`';
  if (typeof body['from_layout'] !== 'number') return 'no numeric `from_layout`';
  if (typeof body['to_layout'] !== 'number') return 'no numeric `to_layout`';
  if (typeof body['copied'] !== 'number') return 'no numeric `copied`';
  if (!Array.isArray(body['retained'])) return 'no `retained` array';
  if (typeof body['destination'] !== 'string') return 'no string `destination`';
  if (typeof body['state_destination'] !== 'string') return 'no string `state_destination`';
  if (typeof body['state_pointer'] !== 'string') return 'no string `state_pointer`';
  if (typeof body['memory_pointer'] !== 'string') return 'no string `memory_pointer`';
  if (!Array.isArray(body['git_tracked'])) return 'no `git_tracked` array';
  return {
    path: body['path'],
    project_id: body['project_id'],
    from_layout: body['from_layout'],
    to_layout: body['to_layout'],
    copied: body['copied'],
    retained: asStringArray(body['retained']),
    destination: body['destination'],
    state_destination: body['state_destination'],
    quarantined: asNullableString(body['quarantined']),
    state_pointer: body['state_pointer'],
    memory_pointer: body['memory_pointer'],
    git_tracked: asStringArray(body['git_tracked']),
  };
}

// ── global skills ─────────────────────────────────────────────────────────────
//
// The user-level skill directories of Claude Code, Codex and opencode, through
// `devteam skills`. `list` and `show` only read; `install` and `remove` are in
// `GATED_COMMANDS`. The main process (`main/ipc.ts`) chooses the install source through
// its own picker and resolves a removal against `skills list` before any of this runs.

export function listSkills(context: CliContext, provider: SkillProviderFilter): Promise<OperationResult<SkillList>> {
  return run(context, ['skills', 'list', '--provider', provider], asSkillList);
}

/** `root` is always passed: without it the CLI answers exit 2 for a name in several roots. */
export function showSkill(context: CliContext, name: string, root: string): Promise<OperationResult<SkillDetail>> {
  const problem = skillTargetProblem(name, root);
  if (problem !== null) return Promise.resolve(refusedSkill('show', problem));
  return run(context, ['skills', 'show', name.trim(), '--root', root], asSkillDetail);
}

export interface SkillInstallOptions {
  readonly providers: readonly SkillProvider[];
  readonly replace: boolean;
  readonly link: boolean;
}

export function installSkill(
  context: CliContext,
  source: string,
  options: SkillInstallOptions,
): Promise<OperationResult<SkillInstallReport>> {
  const args: string[] = ['skills', 'install', '--source', source];
  for (const provider of options.providers) args.push('--provider', provider);
  if (options.replace) args.push('--replace');
  if (options.link) args.push('--link');
  return run(context, args, asSkillInstallReport);
}

export function removeSkill(context: CliContext, name: string, root: string): Promise<OperationResult<SkillRemoveReport>> {
  const problem = skillTargetProblem(name, root);
  if (problem !== null) return Promise.resolve(refusedSkill('remove', problem));
  return run(context, ['skills', 'remove', name.trim(), '--root', root], asSkillRemoveReport);
}

/** Why this name/root pair may not reach an argv. `argparse` would read a leading `-` as a flag. */
export function skillTargetProblem(name: unknown, root: unknown): string | null {
  const nameProblem = validateEntryName(name);
  if (nameProblem !== null) return nameProblem.replace('catalog entry', 'skill');
  // A bare directory name, never something a path join could resolve outside the root.
  // The CLI refuses these too; this keeps `showSkill`/`removeSkill` safe on their own.
  const trimmed = (name as string).trim();
  if (trimmed.startsWith('.') || /[/\\\0]/.test(trimmed) || /^[A-Za-z]:/.test(trimmed)) {
    return 'a skill name must be a bare directory name: no ".", "..", path separators or drive letters';
  }
  if (typeof root !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/.test(root)) {
    return 'a skill root id must be letters, digits, dots, dashes and underscores';
  }
  return null;
}

function refusedSkill(verb: 'show' | 'remove', message: string): OperationResult<never> {
  return { ok: false, kind: 'refused', message, exitCode: null, command: `devteam skills ${verb}`, durationMs: 0 };
}

function asSkillRecord(raw: Record<string, unknown>): SkillRecord | string {
  if (typeof raw['name'] !== 'string') return 'a skill has no string `name`';
  if (typeof raw['root'] !== 'string') return 'a skill has no string `root`';
  if (typeof raw['path'] !== 'string') return 'a skill has no string `path`';
  if (typeof raw['managed'] !== 'boolean') return 'a skill has no boolean `managed`';
  if (raw['status'] !== 'ok' && raw['status'] !== 'malformed') return 'a skill has no `status` of ok or malformed';
  return {
    name: raw['name'],
    description: asNullableString(raw['description']),
    root: raw['root'],
    root_path: asNullableString(raw['root_path']),
    path: raw['path'],
    providers: asStringArray(raw['providers']),
    is_symlink: raw['is_symlink'] === true,
    link_target: asNullableString(raw['link_target']),
    managed: raw['managed'],
    status: raw['status'],
    error: asNullableString(raw['error']),
  };
}

/** `skills list --json`. */
export function asSkillList(body: Record<string, unknown>): SkillList | string {
  if (!Array.isArray(body['roots'])) return 'no `roots` array';
  if (!Array.isArray(body['skills'])) return 'no `skills` array';
  const roots: SkillList['roots'][number][] = [];
  for (const raw of body['roots']) {
    if (!isRecord(raw)) return 'a root is not an object';
    if (typeof raw['id'] !== 'string' || typeof raw['path'] !== 'string') return 'a root has no string `id` and `path`';
    roots.push({
      id: raw['id'],
      path: raw['path'],
      // Not `=== true`: an absent flag is not the claim that the directory is absent.
      exists: raw['exists'] !== false,
      providers: asStringArray(raw['providers']),
      install_target_for: asStringArray(raw['install_target_for']),
    });
  }
  const skills: SkillRecord[] = [];
  for (const raw of body['skills']) {
    if (!isRecord(raw)) return 'a skill entry is not an object';
    const record = asSkillRecord(raw);
    if (typeof record === 'string') return record;
    skills.push(record);
  }
  return { provider: typeof body['provider'] === 'string' ? body['provider'] : 'all', roots, skills };
}

/** `skills show --json`. */
export function asSkillDetail(body: Record<string, unknown>): SkillDetail | string {
  const record = asSkillRecord(body);
  if (typeof record === 'string') return record;
  return {
    ...record,
    body: typeof body['body'] === 'string' ? body['body'] : null,
    files: asStringArray(body['files']),
    files_truncated: body['files_truncated'] === true,
  };
}

/** `skills install --json`. */
export function asSkillInstallReport(body: Record<string, unknown>): SkillInstallReport | string {
  if (typeof body['name'] !== 'string') return 'no string `name`';
  if (!Array.isArray(body['installed'])) return 'no `installed` array';
  const installed: SkillInstallReport['installed'][number][] = [];
  for (const raw of body['installed']) {
    if (!isRecord(raw)) return 'an `installed` entry is not an object';
    if (typeof raw['root'] !== 'string' || typeof raw['path'] !== 'string') {
      return 'an `installed` entry has no string `root` and `path`';
    }
    installed.push({
      root: raw['root'],
      path: raw['path'],
      providers: asStringArray(raw['providers']),
      replaced: raw['replaced'] === true,
      quarantined_to: asNullableString(raw['quarantined_to']),
    });
  }
  return {
    name: body['name'],
    description: asNullableString(body['description']),
    source: asNullableString(body['source']),
    linked: body['linked'] === true,
    source_kind: body['source_kind'] === 'archive' || body['source_kind'] === 'file' ? body['source_kind'] : 'folder',
    installed,
    also_present: Array.isArray(body['also_present'])
      ? body['also_present'].flatMap((raw) =>
          isRecord(raw) && typeof raw['root'] === 'string' && typeof raw['path'] === 'string'
            ? [{ root: raw['root'], path: raw['path'] }]
            : [],
        )
      : [],
  };
}

/** `skills remove --json`. */
export function asSkillRemoveReport(body: Record<string, unknown>): SkillRemoveReport | string {
  if (typeof body['name'] !== 'string') return 'no string `name`';
  if (typeof body['root'] !== 'string') return 'no string `root`';
  if (typeof body['path'] !== 'string') return 'no string `path`';
  if (body['action'] !== 'unlinked' && body['action'] !== 'quarantined') return 'no `action` of unlinked or quarantined';
  return {
    name: body['name'],
    root: body['root'],
    path: body['path'],
    providers: asStringArray(body['providers']),
    action: body['action'],
    quarantined_to: asNullableString(body['quarantined_to']),
    link_target: asNullableString(body['link_target']),
  };
}

// ── helpers ───────────────────────────────────────────────────────────────────

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function asNullableString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
}

function asCounts(value: unknown): CatalogSummary['counts'] | string {
  if (!isRecord(value)) return 'not an object';
  for (const key of ['agents', 'skills', 'commands'] as const) {
    if (typeof value[key] !== 'number') return `no numeric \`${key}\``;
  }
  return {
    agents: value['agents'] as number,
    skills: value['skills'] as number,
    commands: value['commands'] as number,
  };
}

function asEntry(raw: Record<string, unknown>, name: string): CatalogEntry {
  return {
    name,
    description: asNullableString(raw['description']),
    path: asNullableString(raw['path']),
    version: asNullableString(raw['version']),
    ...('tier' in raw ? { tier: asNullableString(raw['tier']) } : {}),
    ...('model' in raw ? { model: asNullableString(raw['model']) } : {}),
    ...('category' in raw ? { category: asNullableString(raw['category']) } : {}),
    // `catalog.py` → `_malformed()` sets both. Carried so the row can say *which* entry
    // the summary's `malformed` count is counting.
    ...(raw['malformed'] === true ? { malformed: true } : {}),
    ...('error' in raw ? { error: asNullableString(raw['error']) } : {}),
  };
}

// ── notifications ─────────────────────────────────────────────────────────────

/**
 * The shape `notify.sh` writes the id in: `<epoch>-<pid>-<random>`. Checked before an
 * id reaches argv — it came off a stream a hook wrote, and a hook is not the app.
 */
export const NOTIFICATION_ID = /^[0-9]{1,12}-[0-9]{1,10}-[0-9]{1,20}$/;

export const NOTIFICATION_LEVELS: readonly NotificationLevel[] = Object.freeze(['info', 'warning', 'critical']);

export function asNotification(raw: unknown): QueuedNotification | string {
  if (!isRecord(raw)) return 'a notification that is not an object';
  const id = raw['id'];
  if (typeof id !== 'string' || !NOTIFICATION_ID.test(id)) return 'a notification with no well-formed `id`';
  const level = raw['level'];
  if (typeof level !== 'string' || !(NOTIFICATION_LEVELS as readonly string[]).includes(level)) {
    return `notification ${id} has an unknown \`level\``;
  }
  const message = raw['message'];
  if (typeof message !== 'string' || message.trim() === '') return `notification ${id} has no \`message\``;
  const ts = raw['ts'];
  if (typeof ts !== 'number') return `notification ${id} has no numeric \`ts\``;
  return {
    id,
    level: level as NotificationLevel,
    code: typeof raw['code'] === 'string' ? raw['code'] : '',
    message,
    ts,
    projectId: typeof raw['project_id'] === 'string' ? raw['project_id'] : '',
    sessionId: typeof raw['session_id'] === 'string' ? raw['session_id'] : '',
    expiresAt: typeof raw['expires_at'] === 'number' ? raw['expires_at'] : 0,
    seen: raw['seen'] === true,
  };
}

export function listNotifications(context: CliContext): Promise<OperationResult<readonly QueuedNotification[]>> {
  return run(context, ['notifications', 'list'], (body) => {
    if (!Array.isArray(body['notifications'])) return 'no `notifications` array';
    const items: QueuedNotification[] = [];
    for (const raw of body['notifications']) {
      const parsed = asNotification(raw);
      // One malformed record is dropped, not fatal: the CLI already skips malformed
      // queue lines, so this is a second net rather than a reason to show nothing.
      if (typeof parsed !== 'string') items.push(parsed);
    }
    return items;
  });
}

export function ackNotification(context: CliContext, id: string): Promise<OperationResult<{ readonly acknowledged: readonly string[] }>> {
  if (!NOTIFICATION_ID.test(id)) {
    return Promise.resolve({
      ok: false,
      kind: 'refused',
      message: `this app refused to acknowledge \`${id.slice(0, 40)}\`: not a notification id`,
      hint: 'Notification ids come from `devteam notifications watch`; this one did not.',
      exitCode: null,
      command: 'devteam notifications ack',
      durationMs: 0,
    });
  }
  return run(context, ['notifications', 'ack', id], (body) => ({ acknowledged: asStringArray(body['acknowledged']) }));
}

export type WatchEvent =
  | { readonly event: 'notification'; readonly notification: QueuedNotification }
  | { readonly event: 'ready'; readonly projects: number }
  | { readonly event: 'heartbeat' }
  | { readonly event: 'end'; readonly reason: string }
  /**
   * The stream failed: the CLI's error document, as one line. The exit code follows as
   * the process ends; this carries the words that explain it.
   */
  | { readonly event: 'error'; readonly message: string; readonly hint: string | null; readonly exitCode: number | null };

/** A line the stream sent, as a typed event — or why it is not one. */
export function asWatchEvent(raw: Record<string, unknown>): WatchEvent | string {
  switch (raw['event']) {
    case 'notification': {
      const parsed = asNotification(raw['notification']);
      return typeof parsed === 'string' ? parsed : { event: 'notification', notification: parsed };
    }
    case 'ready':
      return { event: 'ready', projects: typeof raw['projects'] === 'number' ? raw['projects'] : 0 };
    case 'heartbeat':
      return { event: 'heartbeat' };
    case 'end':
      return { event: 'end', reason: typeof raw['reason'] === 'string' ? raw['reason'] : 'unknown' };
    case 'error':
      return {
        event: 'error',
        message: typeof raw['error'] === 'string' ? raw['error'] : 'the notification stream failed',
        hint: typeof raw['hint'] === 'string' ? raw['hint'] : null,
        exitCode: typeof raw['exit_code'] === 'number' ? raw['exit_code'] : null,
      };
    default:
      return `an event the app does not know: ${JSON.stringify(raw['event'])}`;
  }
}

/**
 * Start `devteam notifications watch`, through the same allow-list `run()` enforces.
 *
 * Returns `null` when the argv is refused — which only a mis-edit of `COMMAND_SHAPES`
 * could cause, and which the caller reports rather than retries.
 */
export function watchNotifications(
  context: CliContext,
  handlers: {
    readonly onEvent: (event: WatchEvent) => void;
    readonly onInvalid: (detail: string) => void;
    readonly onEnd: (end: StreamEnd) => void;
  },
  spawnStream: typeof streamDevteam = streamDevteam,
): StreamHandle | null {
  const args = ['notifications', 'watch'];
  if (argvProblem(args) !== null) return null;
  return spawnStream({
    binary: context.binary,
    cwd: context.cwd,
    ...(context.env !== undefined ? { env: context.env } : {}),
    ...(context.declarationFile !== undefined ? { declarationFile: context.declarationFile } : {}),
    args,
    onEvent: (raw) => {
      const event = asWatchEvent(raw);
      if (typeof event === 'string') handlers.onInvalid(event);
      else handlers.onEvent(event);
    },
    onEnd: handlers.onEnd,
  });
}

// ── the task board ────────────────────────────────────────────────────────────

const BOARD_COLUMNS: readonly BoardColumn[] = ['todo', 'in_progress', 'in_review', 'done'];
const REVIEW_STATES: readonly BoardReviewState[] = ['pending', 'findings', 'unread'];
const SESSION_STATUSES: readonly BoardSessionStatus[] = ['active', 'idle', 'ended'];
const MAX_TASK_TEXT = 2_000;
const MAX_ID = 512;
const MAX_TASKS_PER_SESSION = 2_000;
/**
 * One shell operand exactly as python's `shlex.quote` (the CLI's own quoting) writes it: a
 * bare run of `[\w@%+=:,./-]`, or single-quoted segments, where an embedded quote is the
 * escape `'"'"'`. Control characters are refused everywhere. Anything else — an unquoted
 * `;`, `&`, `$`, a space, a backtick — is not one token and fails the whole command, so a
 * hostile id or path can only ever reach the clipboard inside quotes.
 */
const SHELL_TOKEN = String.raw`(?:[\w@%+=:,./-]+|(?:'[^'\u0000-\u001f\u007f]*'|"'")+)`;
/** A resume command is one line the user pastes into a terminal; anything else is not shown. */
export const RESUME_COMMAND = new RegExp(
  String.raw`^cd ${SHELL_TOKEN} && (?:claude --resume|codex resume|opencode --session) ${SHELL_TOKEN}$`,
);

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function nonNegative(value: unknown): number | null {
  const n = finiteNumber(value);
  return n !== null && n >= 0 ? n : null;
}

function boundedString(value: unknown, max: number): string | null {
  return typeof value === 'string' && value.length > 0 && value.length <= max ? value : null;
}

function asBoardCounts(value: unknown): BoardCounts | string {
  if (!isRecord(value)) return 'no `counts` object';
  const todo = nonNegative(value['todo']);
  const inProgress = nonNegative(value['in_progress']);
  const done = nonNegative(value['done']);
  const rawReview = value['in_review'];
  const inReview = rawReview === undefined || rawReview === null ? 0 : nonNegative(rawReview);
  const total = nonNegative(value['total']);
  if (todo === null || inProgress === null || inReview === null || done === null || total === null) {
    return '`counts` needs non-negative numeric todo, in_progress, done and total (in_review optional)';
  }
  return { todo, in_progress: inProgress, in_review: inReview, done, total };
}

/** A review window, or null when absent or malformed: a bad one costs the badge, not the card. */
function asBoardReview(value: unknown): BoardReview | null {
  if (!isRecord(value)) return null;
  const state = value['state'];
  if (typeof state !== 'string' || !(REVIEW_STATES as readonly string[]).includes(state)) return null;
  const since = nonNegative(value['since']);
  if (since === null) return null;
  const raw = value['findings'];
  let findings: number | null = null;
  if (raw !== undefined && raw !== null) {
    if (typeof raw !== 'number' || !Number.isInteger(raw) || raw < 0) return null;
    findings = raw;
  }
  return { state: state as BoardReviewState, findings, since };
}

/** `null` for a task this app cannot draw honestly; the caller drops it. */
export function asBoardTask(raw: unknown): BoardTask | null {
  if (!isRecord(raw)) return null;
  const key = boundedString(raw['key'], MAX_ID);
  const column = raw['column'];
  const createdAt = nonNegative(raw['created_at']);
  const statusSince = nonNegative(raw['status_since']);
  if (key === null || createdAt === null || statusSince === null) return null;
  if (typeof column !== 'string' || !(BOARD_COLUMNS as readonly string[]).includes(column)) return null;
  const content = typeof raw['content'] === 'string' ? raw['content'].slice(0, MAX_TASK_TEXT) : '';
  const durations: Record<string, number> = {};
  if (isRecord(raw['durations'])) {
    for (const [status, seconds] of Object.entries(raw['durations'])) {
      const n = nonNegative(seconds);
      if (n !== null) durations[status] = n;
    }
  }
  return {
    key,
    content,
    owner: typeof raw['owner'] === 'string' ? raw['owner'].slice(0, MAX_ID) : 'main',
    agent_type: asNullableString(raw['agent_type']),
    status: typeof raw['status'] === 'string' ? raw['status'] : column,
    column: column as BoardColumn,
    created_at: createdAt,
    status_since: statusSince,
    completed_at: nonNegative(raw['completed_at']),
    durations,
    stale: raw['stale'] === true,
    abandoned: raw['abandoned'] === true,
    review: asBoardReview(raw['review']),
  };
}

function asBoardSession(raw: unknown): BoardSession | null {
  if (!isRecord(raw)) return null;
  const sessionId = boundedString(raw['session_id'], MAX_ID);
  const provider = boundedString(raw['provider'], 64);
  const status = raw['status'];
  const counts = asBoardCounts(raw['counts']);
  if (sessionId === null || provider === null || typeof counts === 'string') return null;
  if (typeof status !== 'string' || !(SESSION_STATUSES as readonly string[]).includes(status)) return null;
  const resume = raw['resume_command'];
  const tasks: BoardTask[] = [];
  if (Array.isArray(raw['tasks'])) {
    for (const entry of raw['tasks'].slice(0, MAX_TASKS_PER_SESSION)) {
      const task = asBoardTask(entry);
      if (task !== null) tasks.push(task);
    }
  }
  return {
    session_id: sessionId,
    provider,
    branch: asNullableString(raw['branch']),
    cwd: typeof raw['cwd'] === 'string' ? raw['cwd'] : '',
    status: status as BoardSessionStatus,
    created_at: nonNegative(raw['created_at']) ?? 0,
    last_activity_at: nonNegative(raw['last_activity_at']) ?? 0,
    ended_at: nonNegative(raw['ended_at']),
    resume_command: typeof resume === 'string' && resume.length <= 4_096 && RESUME_COMMAND.test(resume) ? resume : null,
    counts,
    tasks,
  };
}

/** A project document from `tasks list` or a `snapshot` event, or why it is unusable. */
export function asBoardProject(raw: unknown): BoardProject | string {
  if (!isRecord(raw)) return 'a project that is not an object';
  const projectId = boundedString(raw['project_id'], MAX_ID);
  if (projectId === null) return 'a project with no `project_id`';
  const root = typeof raw['root'] === 'string' ? raw['root'] : '';
  const counts = asBoardCounts(raw['counts']);
  if (typeof counts === 'string') return `project ${projectId}: ${counts}`;
  const sessionsTotal = nonNegative(raw['sessions_total']);
  const sessionsActive = nonNegative(raw['sessions_active']);
  if (sessionsTotal === null || sessionsActive === null) return `project ${projectId} has no numeric sessions_total / sessions_active`;
  if (!Array.isArray(raw['sessions'])) return `project ${projectId} has no sessions array`;
  const sessions: BoardSession[] = [];
  for (const entry of raw['sessions']) {
    const session = asBoardSession(entry);
    if (session !== null) sessions.push(session);
  }
  return {
    project_id: projectId,
    root,
    providers: asStringArray(raw['providers']),
    sessions_total: sessionsTotal,
    sessions_active: sessionsActive,
    counts,
    stale: nonNegative(raw['stale']) ?? 0,
    abandoned: nonNegative(raw['abandoned']) ?? 0,
    with_findings: nonNegative(raw['with_findings']) ?? 0,
    last_activity_at: nonNegative(raw['last_activity_at']) ?? 0,
    sessions,
  };
}

/** `tasks list --json`: every project that has at least one task. A bad project is dropped. */
export function asBoardList(body: Record<string, unknown>): { readonly projects: readonly BoardProject[] } | string {
  if (!Array.isArray(body['projects'])) return 'no `projects` array';
  const projects: BoardProject[] = [];
  for (const raw of body['projects']) {
    const parsed = asBoardProject(raw);
    if (typeof parsed !== 'string') projects.push(parsed);
  }
  return { projects };
}

/** Seconds a stale threshold may take on the argv: a positive integer, bounded. */
function secondsArgument(seconds: number): string | null {
  return Number.isInteger(seconds) && seconds >= 1 && seconds <= 7 * 24 * 3600 ? String(seconds) : null;
}

export function listTasks(
  context: CliContext,
  options: { readonly staleAfterSeconds: number },
): Promise<OperationResult<{ readonly projects: readonly BoardProject[] }>> {
  const stale = secondsArgument(options.staleAfterSeconds);
  return run(context, ['tasks', 'list', ...(stale === null ? [] : ['--stale-after', stale])], asBoardList);
}

export type TaskWatchEvent =
  | { readonly event: 'snapshot'; readonly project: BoardProject }
  | { readonly event: 'removed'; readonly projectId: string }
  | { readonly event: 'ready' }
  | { readonly event: 'heartbeat' }
  | { readonly event: 'end'; readonly reason: string }
  | { readonly event: 'error'; readonly message: string; readonly hint: string | null; readonly exitCode: number | null };

export function asTaskWatchEvent(raw: Record<string, unknown>): TaskWatchEvent | string {
  switch (raw['event']) {
    case 'snapshot': {
      const project = raw['project'];
      if (isRecord(project) && project['removed'] === true) {
        const id = boundedString(project['project_id'], MAX_ID);
        return id === null ? 'a removal with no `project_id`' : { event: 'removed', projectId: id };
      }
      const parsed = asBoardProject(project);
      return typeof parsed === 'string' ? parsed : { event: 'snapshot', project: parsed };
    }
    case 'ready':
      return { event: 'ready' };
    case 'heartbeat':
      return { event: 'heartbeat' };
    case 'end':
      return { event: 'end', reason: typeof raw['reason'] === 'string' ? raw['reason'] : 'unknown' };
    case 'error':
      return {
        event: 'error',
        message: typeof raw['error'] === 'string' ? raw['error'] : 'the task stream failed',
        hint: typeof raw['hint'] === 'string' ? raw['hint'] : null,
        exitCode: typeof raw['exit_code'] === 'number' ? raw['exit_code'] : null,
      };
    default:
      return `an event the app does not know: ${JSON.stringify(raw['event'])}`;
  }
}

/** `watchTasks` refused its own argv: a bug in the app, distinct from "no CLI was found". */
export class TaskStreamRefused extends Error {
  constructor(readonly problem: string) {
    super(`the task stream was refused by the argument allow-list: ${problem}`);
    this.name = 'TaskStreamRefused';
  }
}

/** Start `devteam tasks watch`, through the same allow-list `run()` enforces. Throws `TaskStreamRefused` on a bad argv. */
export function watchTasks(
  context: CliContext,
  options: { readonly staleAfterSeconds: number },
  handlers: {
    readonly onEvent: (event: TaskWatchEvent) => void;
    readonly onInvalid: (detail: string) => void;
    readonly onEnd: (end: StreamEnd) => void;
  },
  spawnStream: typeof streamDevteam = streamDevteam,
): StreamHandle {
  const stale = secondsArgument(options.staleAfterSeconds);
  const args = ['tasks', 'watch', ...(stale === null ? [] : ['--stale-after', stale])];
  const problem = argvProblem(args);
  if (problem !== null) throw new TaskStreamRefused(problem);
  return spawnStream({
    binary: context.binary,
    cwd: context.cwd,
    ...(context.env !== undefined ? { env: context.env } : {}),
    ...(context.declarationFile !== undefined ? { declarationFile: context.declarationFile } : {}),
    args,
    onEvent: (raw) => {
      const event = asTaskWatchEvent(raw);
      if (typeof event === 'string') handlers.onInvalid(event);
      else handlers.onEvent(event);
    },
    onEnd: handlers.onEnd,
  });
}
