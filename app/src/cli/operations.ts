/**
 * The named read-only operations this app can perform, and nothing else.
 *
 * One function per screen's needs. Each builds its own argument vector — the renderer
 * never supplies one — and each validates the payload it got before handing it on.
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
import type {
  CatalogDetail,
  CatalogEntry,
  CatalogKind,
  CatalogListing,
  CatalogSummary,
  DoctorFinding,
  DoctorReport,
  OperationResult,
  ProjectList,
  ProjectRecord,
  ProblemKind,
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
]);

/**
 * Subcommands this build runs that the framework classifies in `compat.MUTATING`.
 *
 * **Exactly one, and it is `doctor`.** This slice was specified as read-only and the
 * diagnosis screen was specified as `devteam doctor`; those two are in tension, because
 * `compat.MUTATING` lists `doctor` with the reason written out — it "repairs what it
 * finds… it rewrites the directory pointers, relocates a moved registry entry, and
 * reassigns identity with --reassign-identity. Read the actions it returns, not the word
 * 'diagnose', before reclassifying this one." So the app cannot both show a diagnosis
 * screen and claim it never runs a mutating command.
 *
 * It is listed here rather than hidden in the read-only list, and the consequences are
 * carried rather than papered over: the app declares its schemas on every invocation, so
 * the framework's gate refuses this call with exit 4 whenever the store is ahead of the
 * app — that refusal is the protection, and the Diagnosis screen states that any repairs
 * it reports were writes. `--reassign-identity` is never passed.
 *
 * Adding a second entry here is a decision to widen what this app can change. Make it
 * explicitly; `test/operations.test.ts` fails on an unreviewed addition.
 */
export const GATED_COMMANDS: readonly (readonly string[])[] = Object.freeze([['doctor']]);

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
  /** Positional operands the app may pass after the command words. */
  readonly operands: 0 | 1;
  /** Flags this command may be passed, and whether each takes a value. */
  readonly flags: Readonly<Record<string, 'value' | 'bare'>>;
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
      if (takesValue === 'value') {
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

  return {
    ok: true,
    outcome: result.outcome,
    data: validated,
    command: result.command.display,
    durationMs: result.durationMs,
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
