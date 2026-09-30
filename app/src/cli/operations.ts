/**
 * The named operations this app can perform, and nothing else.
 *
 * Read-only for most of this file — `list`, `catalog*`, `doctor`, `prefsList` — plus the
 * project lifecycle's write actions at the bottom: `bindProject`, `unbindProject`,
 * `syncProject`, `syncAllProjects`, `setPin`, `planUpgrade`, `applyUpgrade`, and the
 * project-layer preference writes `prefsSet` / `prefsUnset`. One function
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
import { explain, ranAndAnswered, type CliResult } from './contract.js';
import { textProblem } from '../shared/preferenceRules.js';
import type {
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
  OperationResult,
  PinReport,
  PreferencesImport,
  PreferenceValue,
  PreferenceWrite,
  ProjectList,
  ProjectPreferences,
  ProjectRecord,
  ProblemKind,
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
  Pick<InvokeOptions, 'env' | 'timeoutMs' | 'declarationFile'>;

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
  ['prefs', 'set'],
  ['prefs', 'unset'],
]);

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
  /** Positional operands the app may pass after the command words. `prefs set` is the one with two: key and value. */
  readonly operands: 0 | 1 | 2;
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
  // The preference commands resolve their project from `--path` alone, so — as with `pin`
  // — the path is always one `main/ipc.ts` resolved from a `project_id`. `--scope` is
  // always `project`: the settings screen edits one project's layer and never the global
  // one, which would silently change every other bound project too.
  'prefs list': { operands: 0, flags: { '--path': 'value' } },
  'prefs set': { operands: 2, flags: { '--scope': 'value', '--path': 'value' } },
  'prefs unset': { operands: 1, flags: { '--scope': 'value', '--path': 'value' } },
});

const MAX_COMMAND_WORDS = 2;

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
  return toOperationResult(await invokeDevteam({ ...context, args }), validate);
}

/** `--path <the app's own working directory>`, for the commands that accept it. */
function projectPathFlag(context: CliContext): readonly string[] {
  return ['--path', context.cwd];
}

// ── list ──────────────────────────────────────────────────────────────────────

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
