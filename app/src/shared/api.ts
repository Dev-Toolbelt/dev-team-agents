/**
 * The IPC surface, and the view models that cross it.
 *
 * Type-only, so it is safe to import from the main process, the preload script and the
 * renderer alike. Nothing here imports `electron` or `node:*`.
 *
 * The surface is a fixed list of **named operations**. There is deliberately no
 * `run(command)` channel: the app's security posture is that the renderer cannot ask
 * for an arbitrary process, and a generic escape hatch would hand back exactly the
 * capability `sandbox: true` and `contextIsolation: true` were set to remove. Adding a
 * command means adding a named operation here and a handler in `main/ipc.ts`.
 */

import type { ProjectFolders, ProjectFoldersAnswer } from './projectFolders.js';
import type { Provider } from './providers.js';

export type { ProjectFolders, ProjectFoldersAnswer };

export type ProblemKind =
  | 'usage'
  | 'environment'
  | 'conflict'
  /**
   * The command ran and reported a finding as an **error document** (exit 1 with
   * `error` rather than a payload). It has its own kind because the alternative was a
   * ternary that fell through to `'environment'`, which titled a finding "The
   * environment is not ready" — data preserved, label wrong.
   */
  | 'findings'
  /** The app refused to run something: an argv outside its allow-list, or a gated
   *  command it cannot declare for. Never a verdict about the CLI. */
  | 'refused'
  | 'contract-breach'
  | 'unavailable'
  | 'timeout';

/**
 * One operation's result. `findings` is a **success** carrying data: `devteam doctor`
 * exits 1 with a complete report, and a UI that treated that as an error would show
 * nothing on the screen whose entire purpose is to show it.
 */
export type OperationResult<T> =
  | {
      readonly ok: true;
      readonly outcome: 'success' | 'findings';
      readonly data: T;
      readonly command: string;
      readonly durationMs: number;
      /**
       * What the command wrote to **stderr while succeeding**, when it wrote anything.
       *
       * Not diagnostics for a log: the CLI uses stderr to tell the user something the
       * payload does not carry. `devteam bind` in a directory that is not a git repository
       * exits 0 with a complete document and says on stderr that the bind artifacts were
       * added to no ignore file — which means they can be committed by accident, and the
       * JSON has no field for it. Without this the app would render a clean success and
       * drop the one sentence the user needed.
       *
       * Absent when stderr was empty, so a UI can test for it rather than for `''`.
       */
      readonly notice?: string;
    }
  | {
      readonly ok: false;
      readonly kind: ProblemKind;
      readonly message: string;
      readonly hint?: string;
      /**
       * `details.reason` from the CLI's error document, when it gave one — a machine-readable
       * cause that tells two refusals with the same exit code apart. `skills install` answers
       * exit 4 both for "a skill of that name exists" (`exists`, which `--replace` resolves)
       * and for "that skill is managed by dev-team-agents" (`managed`, which nothing does).
       */
      readonly reason?: string;
      readonly exitCode: number | null;
      readonly command: string;
      readonly durationMs: number;
    };

// ── resolution ────────────────────────────────────────────────────────────────

/**
 * Which step of the resolution order produced a candidate. `homebrew` and `winget` are
 * the same step — "a known per-platform channel location" — kept apart because the badge
 * that names it should say which channel rather than "a known location".
 */
export type CliSource = 'configured' | 'path' | 'homebrew' | 'winget';

export interface CliIdentity {
  readonly path: string;
  readonly source: CliSource;
  readonly sourceDetail: string;
  readonly storeVersion: string | null;
  readonly jsonContract: number | null;
  readonly minAppVersion: string | null;
  readonly storeSchemas: Readonly<Record<string, number>>;
}

export interface RejectedCli {
  readonly path: string;
  readonly source: CliSource;
  readonly reason: string;
}

/** One resolution step's tally — see `resolve.ts`'s `SearchedLocation`. */
export interface SearchedLocation {
  readonly source: CliSource;
  readonly label: string;
  readonly count: number;
}

export type CliResolution =
  | { readonly found: true; readonly cli: CliIdentity; readonly rejected: readonly RejectedCli[] }
  | {
      readonly found: false;
      readonly rejected: readonly RejectedCli[];
      readonly searchedCount: number;
      /**
       * `searched`, grouped by resolution step (configured path, PATH, this platform's
       * channel location). ADR-0015 § 5 says the screen "shows which locations it
       * tried"; a bare count does not name them, and dozens of individual `PATH`
       * entries with nothing there would drown a report that listed every one.
       */
      readonly searchedBySource: readonly SearchedLocation[];
      readonly remedy: readonly string[];
    };

// ── the compat handshake ──────────────────────────────────────────────────────

export interface UnsupportedShape {
  readonly store: number;
  readonly client: number | null;
}

export type HandshakeView =
  | {
      readonly state: 'answered';
      readonly mayWrite: boolean;
      readonly jsonContract: number | null;
      readonly minAppVersion: string | null;
      readonly storeSchemas: Readonly<Record<string, number>>;
      readonly clientSchemas: Readonly<Record<string, number>>;
      readonly unsupported: Readonly<Record<string, UnsupportedShape>>;
      readonly summary: string;
    }
  | { readonly state: 'unknown'; readonly summary: string; readonly detail: string };

// ── screen payloads ──────────────────────────────────────────────────────────

/** `list --json` → `projects[]`. Keys pinned by `AppFacingKeySetContractTest`. */
export interface ProjectRecord {
  readonly project_id: string;
  readonly path: string;
  readonly providers: readonly string[];
  readonly mode: string | null;
  readonly pin: string | null;
  readonly resolves_to: string | null;
  /**
   * Whether the project's directory is still there — **`null` when the CLI did not say**.
   *
   * Three states, not two. `=== true` collapsed an absent or non-boolean key into
   * `false`, which the UI then rendered as a red `missing` badge beside a path that
   * exists: a missing key became an affirmative false claim. ADR-0015's own unmitigated
   * risk is "a bound project shown unbound leads the user to a destructive action in the
   * terminal", and this is that shape. Silence is reported as silence.
   */
  readonly path_exists: boolean | null;
  /**
   * The resolved values the Projects table shows as badges, from `list --json`. Absent
   * entirely on a CLI that predates the field, and each key is `null` when the CLI could
   * not resolve it — either way the UI renders a neutral dash, never "Off". Silence is
   * silence, as with `path_exists`.
   *
   * `suppress_notifications` is `true`/`false` or the list of muted notification types;
   * suppressing is the *negative* reading, so `true` is "Off" and `false` or `[]` is "On".
   */
  readonly preferences?: {
    readonly auto_update: boolean | null;
    readonly worktree_active: boolean | null;
    readonly suppress_notifications: boolean | readonly string[] | null;
  };
}

export interface ProjectList {
  readonly current: string | null;
  readonly projects: readonly ProjectRecord[];
}

export interface CatalogCounts {
  readonly agents: number;
  readonly skills: number;
  readonly commands: number;
}

export interface CatalogSummary {
  readonly version: string | null;
  readonly project_id: string | null;
  readonly counts: CatalogCounts;
  readonly malformed: CatalogCounts;
}

export type CatalogKind = 'agents' | 'skills' | 'commands';

/** The union of the three record shapes; `tier`/`model`/`category` are kind-specific. */
export interface CatalogEntry {
  readonly name: string;
  readonly description: string | null;
  readonly path: string | null;
  readonly version: string | null;
  readonly tier?: string | null;
  readonly model?: string | null;
  readonly category?: string | null;
  /**
   * `catalog.py` → `_malformed()`: the file was found and could not be read as its kind.
   * Its `name` is a best-effort fallback from the path, and `error` says why. Carried
   * because the summary's `malformed` counts say *how many* and only the per-kind rows
   * can say *which* — a count with no row is a number the user cannot act on.
   */
  readonly malformed?: boolean;
  readonly error?: string | null;
}

export interface CatalogListing {
  readonly kind: CatalogKind;
  readonly version: string | null;
  readonly project_id: string | null;
  readonly count: number;
  readonly entries: readonly CatalogEntry[];
}

export interface CatalogDetail extends CatalogEntry {
  readonly kind: string;
  readonly body: string;
  readonly project_id: string | null;
}

export interface DoctorFinding {
  readonly level: string;
  readonly category: string;
  readonly message: string;
  readonly hint?: string;
}

export interface DoctorReport {
  readonly status: string;
  readonly findings: readonly DoctorFinding[];
  readonly actions: readonly string[];
}

// ── write actions ────────────────────────────────────────────────────────────

/**
 * Where a mutating command's target came from.
 *
 * **Every write action names its target by `project_id`, never by path**, and the main
 * process resolves that id against the registry's own `list` answer before it builds an
 * argv. That is the whole security argument for this surface: an id the registry does not
 * know is refused in the main process, so the renderer cannot aim `unbind` at a directory
 * of its choosing. A path-taking parameter would have handed it exactly that.
 *
 * `bind` is the one command with no existing project to name, and it is handled the other
 * way round — see `DirectoryChoice`.
 */
export type ProjectId = string;

/**
 * The result of asking the OS for a directory.
 *
 * The renderer cannot type a path into `bind`. It calls `chooseProjectDirectory()`, the
 * **main process** opens the native picker, and the path the user picked is recorded in a
 * set of directories this session has offered. `bindProject` then refuses any path that is
 * not in that set.
 *
 * Two steps rather than one — a `bind()` that opened its own dialog would be safe too —
 * because the UI has to show what was chosen and let the user pick providers and a mode
 * before anything is written. The offered-set is what keeps the two-step safe: the
 * renderer is handed a path it may echo back and nothing else.
 */
export type DirectoryChoice =
  | { readonly chosen: true; readonly path: string }
  /** The user dismissed the picker. Not an error, and the UI says nothing about it. */
  | { readonly chosen: false };

export type BindProvider = Provider;
export type BindMode = 'auto' | 'link' | 'copy' | 'vendored';

/**
 * What `bind` is asked to do. `path` must be one the main process offered through
 * `chooseProjectDirectory`; every other field is optional and omitted rather than
 * defaulted here, so the CLI's own defaults stay the single source of truth.
 */
export interface BindRequest {
  readonly path: string;
  readonly providers?: readonly BindProvider[];
  readonly mode?: BindMode;
  readonly pin?: string | null;
  /**
   * A human name for this project — **the app's own record, never the CLI's.**
   *
   * `devteam bind` has no `--name`, and `project.json` has no `name` field: the
   * framework identifies a project by `project_id`, a UUID chosen so identity survives a
   * re-clone, a move and a machine change. This never reaches the CLI's argv; the main
   * process stores it after a successful bind and it is read back through
   * `projectNames()`.
   *
   * The consequence is worth stating rather than discovering: a name set here lives in
   * this app's `settings.json` on this machine only. It does not travel with the
   * project, another client does not see it, and clearing the app's data loses it.
   * Making it portable means adding a field to the committed `project.json` and a flag
   * to `bind` — a change to the framework's public surface, which a UI affordance is not
   * on its own a reason to make.
   */
  readonly name?: string;
}

/**
 * `bind --json` and single-project `sync --json`, which answer with the same document —
 * `sync` adds `worktrees`, which is why it is optional here rather than two near-identical
 * interfaces. Keys observed against the real CLI at store version 2.48.0 and pinned by
 * `app/test/real-cli.test.ts`.
 */
export interface BindReport {
  readonly path: string;
  readonly project_id: string;
  readonly version: string;
  readonly mode: string;
  readonly providers: readonly string[];
  readonly artifacts: number;
  readonly identity_created: boolean;
  readonly gitignore: string;
  readonly git_exclude: string;
  readonly pin: string | null;
  readonly fallback_reason: string | null;
  readonly retired: readonly unknown[];
  /**
   * Files the CLI merged into the project's own committed config. It prints "commit these
   * yourself", and the UI has to repeat that: a bind that silently leaves a dirty working
   * tree is a bind the user discovers from `git status` days later.
   */
  readonly merged_project_files: readonly string[];
  readonly pruned?: { readonly unlinked: readonly string[]; readonly quarantined: readonly unknown[] };
  readonly worktrees?: readonly unknown[];
  /**
   * What `bind`/`sync` adopted from a v2 `user-data/preferences.json`. Absent from a CLI that
   * predates the import, `null` when there was no such file.
   */
  readonly preferences_import?: PreferencesImport | null;
}

/**
 * `prefs.import_legacy` in the CLI: the v2 file's keys, sorted by what happened to them. The
 * file is moved to the store's quarantine only once every imported key has been read back.
 */
export interface PreferencesImport {
  readonly source: string;
  readonly imported: readonly string[];
  readonly unchanged: readonly string[];
  /** The project layer already held a different value, and kept it. */
  readonly conflicts: readonly string[];
  readonly ignored: readonly { readonly key: string; readonly reason: string }[];
  readonly quarantined: string | null;
  /** Why the file was left in place, when it was. */
  readonly problem: string | null;
}

/** `sync --all --json`. One entry per project, plus the ones that failed. */
export interface SyncAllReport {
  readonly synced: readonly BindReport[];
  readonly problems: readonly unknown[];
}

/**
 * `unbind --json`. `unlinked` is long — 159 entries on a claude-only bind — and the UI
 * shows its length rather than the list; `quarantined` is the one the user must read,
 * because it names where their files went.
 */
export interface UnbindReport {
  readonly path: string;
  readonly project_id: string;
  readonly unlinked: readonly string[];
  readonly quarantined: readonly { readonly to?: string }[];
  readonly kept: readonly string[];
  readonly problems: readonly unknown[];
}

/** `pin <version> --json` and `pin --release --json`. */
export interface PinReport {
  readonly project_id: string;
  readonly path: string;
  readonly pin: string | null;
}

/**
 * `upgrade --json` without `--apply`: reads only, and says so in its own first line.
 *
 * The preview is not a courtesy. `upgrade` moves a project's memory into the store and
 * quarantines what it moved; the plan is the only place the user can see `collisions` and
 * `git_tracked` before any of it happens, and the UI refuses to offer `--apply` until the
 * plan has been fetched.
 */
export interface UpgradePlan {
  readonly path: string;
  readonly project_id: string;
  readonly from_layout: number;
  readonly to_layout: number;
  readonly files: number;
  readonly source: string;
  readonly destination: string;
  readonly state_destination: string;
  readonly machine_local: readonly string[];
  readonly retained: readonly string[];
  readonly collisions: readonly string[];
  readonly git_tracked: readonly string[];
  readonly actions: readonly string[];
}

/** `upgrade --apply --json`. */
export interface UpgradeReport {
  readonly path: string;
  readonly project_id: string;
  readonly from_layout: number;
  readonly to_layout: number;
  readonly copied: number;
  readonly retained: readonly string[];
  readonly destination: string;
  readonly state_destination: string;
  readonly quarantined: string | null;
  readonly state_pointer: string;
  readonly memory_pointer: string;
  readonly git_tracked: readonly string[];
}

/**
 * A v2 install converted to a bind, from the bind dialog (`devteam migrate`).
 *
 * The same provenance as `BindRequest` — the path must be one the main process handed
 * back through the directory picker — and the same options, minus `pin`. `name` is the
 * app's own record, stored after a successful apply exactly as for a bind.
 */
export type MigrateRequest = Omit<BindRequest, 'pin'>;

/** A move the migration makes inside the project: memory, kept rather than quarantined. */
export interface MigrationMove {
  readonly from: string;
  readonly to: string;
}

/**
 * `migrate --json` without `--apply`: what converting the v2 install would do.
 *
 * `layout` names the v2 shape — `root` (vendored at `.dev-team-agents/`) or `pre-root`
 * (at `.claude/dev-team-agents/`, before v2.1.0). The bind dialog fetches this as soon as
 * a directory is chosen: a plan means "this is a v2 install"; exit 2 means it is not, and
 * the ordinary bind applies.
 */
export interface MigrationPlan {
  readonly path: string;
  readonly layout: string;
  readonly install_dir: string;
  readonly providers: readonly string[];
  readonly mode: string;
  readonly actions: readonly string[];
  readonly adopts_identity: boolean;
  readonly memory_moves: readonly MigrationMove[];
  readonly context_paths_added: readonly string[];
  readonly git_tracked: readonly string[];
  readonly git_tracked_artifacts: readonly string[];
  readonly preserved: readonly string[];
}

/**
 * `migrate --apply --untrack --json`. `untracked` is what left git's index (the files stay
 * on disk, nothing is committed); `untrack_problem` says why nothing did, when that is
 * the case — the migration itself still succeeded.
 */
export interface MigrationReport {
  readonly path: string;
  readonly layout: string;
  readonly project_id: string;
  readonly version: string;
  readonly mode: string;
  readonly providers: readonly string[];
  readonly adopted_identity: boolean;
  readonly memory_moved: readonly MigrationMove[];
  readonly context_paths_added: readonly string[];
  readonly quarantined: readonly MigrationMove[];
  readonly quarantine_dir: string | null;
  readonly retired_links: readonly string[];
  readonly git_tracked: readonly string[];
  readonly git_tracked_artifacts: readonly string[];
  readonly untracked: readonly string[];
  readonly untrack_problem: string | null;
  readonly unrecognised: readonly string[];
}

// ── preferences ─────────────────────────────────────────────────────────────

/** A value `prefs set` can store. Lists exist in the schema but cannot be written by the CLI. */
export type PreferenceValue = string | number | boolean | null;

/**
 * Which layer of the cascade a value came from (ADR-0008). `consent-withheld` is the CLI's
 * word for a consent key nobody opted into: the value is `false` whatever the default says.
 * Kept as `string` rather than a closed union so a layer a newer CLI adds is shown, not
 * rejected.
 */
export type PreferenceOrigin = 'defaults' | 'global' | 'project' | 'consent-withheld' | (string & {});

/** `prefs list --path <project> --json`. */
export interface ProjectPreferences {
  readonly project_id: string | null;
  readonly version: string;
  readonly values: Readonly<Record<string, unknown>>;
  readonly origin: Readonly<Record<string, PreferenceOrigin>>;
  /** Keys set in a layer that the version's defaults do not declare — shown, never edited. */
  readonly unknown: readonly string[];
}

/**
 * What the settings screen reads: the project's cascade, plus the cascade **without** the
 * project layer — the value each key would fall back to if its project value were removed.
 * `inherited` is `null` when it could not be read; the screen then cannot say what a reset
 * leads to and says so.
 */
export interface ProjectPreferencesView extends ProjectPreferences {
  readonly inherited: Readonly<Record<string, unknown>> | null;
}

/** `prefs set --json` / `prefs unset --json`. */
export interface PreferenceWrite {
  readonly key: string;
  readonly scope: string;
  readonly removed?: boolean;
}

/** One pending edit. `unset` drops the key from the project layer so the one below applies. */
export type PreferenceChange =
  | { readonly key: string; readonly action: 'set'; readonly value: PreferenceValue }
  | { readonly key: string; readonly action: 'unset' };

/**
 * The outcome of applying a batch of changes, **in order, stopping at the first failure**.
 * `applied` is what was actually written, so a partial save is stated rather than hidden.
 */
export interface PreferenceUpdateReport {
  readonly applied: readonly PreferenceChange[];
  readonly failed: {
    readonly change: PreferenceChange;
    readonly problem: Extract<OperationResult<never>, { ok: false }>;
  } | null;
}

// ── plugins ──────────────────────────────────────────────────────────────────

/**
 * What a plugin's config field holds. `string_list` is the only structured one; the CLI takes
 * it as a JSON array string, which `shared/pluginRules.ts` builds.
 */
export type PluginConfigValue = string | number | boolean | readonly string[];

/** The field types ADR-0019 § 1 defines. A type a newer CLI adds is carried as a plain string. */
export type PluginConfigType = 'boolean' | 'string' | 'integer' | 'string_list' | 'enum' | (string & {});

/** One entry of a manifest's `config`, as `plugin list` returns it. */
export interface PluginConfigField {
  readonly key: string;
  readonly type: PluginConfigType;
  readonly label: string;
  readonly help: string | null;
  readonly required: boolean;
  readonly default: unknown;
  readonly placeholder: string | null;
  /** `enum` only. */
  readonly options: readonly { readonly value: string; readonly label: string }[];
  /** `integer` only; `null` when the manifest sets no bound. */
  readonly min: number | null;
  readonly max: number | null;
  /**
   * `string` / `string_list` only. When set the value is chosen with the OS picker rather
   * than typed; `null` when the manifest declares none (or a CLI that predates the key).
   */
  readonly picker: PluginFieldPicker | null;
}

/** What a picker chooses. Anything else a newer CLI sends is dropped, the field stays free text. */
export type PluginFieldPicker = 'directory' | 'file';

export interface PluginRequirement {
  readonly binary: string;
  readonly found: boolean;
  readonly install_hint: string | null;
}

export type PluginActionOutput = 'config' | 'json' | 'log' | (string & {});

export interface PluginAction {
  readonly id: string;
  readonly label: string;
  readonly help: string | null;
  readonly output: PluginActionOutput;
  readonly requires_enabled: boolean;
  readonly writes: boolean;
  /** Not in ADR-0019's `PluginView` shape; read when the CLI sends it, so a long action gets its full budget. */
  readonly timeout_seconds: number | null;
}

/** How a status fact's value should read; absent (`null`) on a CLI that predates it. */
export type PluginFactTone = 'positive' | 'warning' | 'neutral';

export interface PluginStatusFact {
  readonly label: string;
  readonly value: string;
  readonly tone: PluginFactTone | null;
}

export interface PluginStatus {
  readonly summary: string;
  readonly facts: readonly PluginStatusFact[];
}

/** `plugin list` → `plugins[]`, and `plugin show`. */
export interface PluginView {
  readonly name: string;
  readonly title: string;
  readonly description: string;
  readonly homepage: string | null;
  readonly enabled: boolean;
  readonly source: 'settings' | 'legacy' | 'none' | (string & {});
  readonly settings_file: string;
  readonly requirements: readonly PluginRequirement[];
  readonly ready: boolean;
  readonly configured: boolean;
  readonly config_fields: readonly PluginConfigField[];
  readonly config: Readonly<Record<string, unknown>>;
  readonly unknown_config: readonly string[];
  readonly actions: readonly PluginAction[];
  readonly hooks: readonly string[];
  readonly status: PluginStatus | null;
}

/** `pickProjectPath`: dismissed, chosen (relative POSIX path), or refused with a reason. */
export type ProjectPathPick =
  | { readonly picked: true; readonly path: string }
  | { readonly picked: false; readonly refused?: undefined }
  | { readonly picked: false; readonly refused: string };

/** `plugin list --json`. */
export interface PluginList {
  readonly project_id: string | null;
  readonly plugins: readonly PluginView[];
  /** Plugin directories whose manifest the CLI rejected and skipped. Absent from the payload → empty. */
  readonly invalid: readonly InvalidPlugin[];
}

export interface InvalidPlugin {
  readonly name_or_dir: string;
  readonly problem: string;
}

/** `plugin enable --json` and `plugin disable --json`; `seeded` is always `false` for a disable. */
export interface PluginToggleReport {
  readonly plugin: PluginView;
  readonly changed: boolean;
  readonly seeded: boolean;
}

/** `plugin config set --json` and `plugin config unset --json`. */
export interface PluginConfigWrite {
  readonly plugin: PluginView;
  readonly key: string;
  readonly removed?: boolean;
}

/** `plugin run --json`. A script that exits non-zero is `ok: false` here, not a CLI error. */
export interface PluginRunResult {
  readonly plugin: string;
  readonly action: string;
  readonly ok: boolean;
  readonly exit_code: number;
  readonly duration_ms: number;
  readonly output: Readonly<Record<string, unknown>> | null;
  readonly log_tail: string;
}

/** One pending edit of a plugin's config. `unset` drops the key so the manifest default applies. */
export type PluginConfigChange =
  | { readonly key: string; readonly action: 'set'; readonly value: PluginConfigValue }
  | { readonly key: string; readonly action: 'unset' };

/** Like `PreferenceUpdateReport`: applied in order, stopped at the first failure. */
export interface PluginConfigUpdateReport {
  readonly applied: readonly PluginConfigChange[];
  readonly failed: {
    readonly change: PluginConfigChange;
    readonly problem: Extract<OperationResult<never>, { ok: false }>;
  } | null;
}

// ── integrations ─────────────────────────────────────────────────────────────

export type IntegrationFieldScope = 'account' | 'project';
export type IntegrationFieldType = 'string' | 'enum' | (string & {});
export type IntegrationStatusState =
  | 'not_connected'
  | 'connected'
  | 'invalid_token'
  | 'rate_limited'
  | 'unreachable'
  | 'unknown'
  | (string & {});
export type IntegrationFactTone = 'positive' | 'warning' | 'neutral';

/** One field an integration declares; `scope` decides where a write lands (account store or project binding). */
export interface IntegrationField {
  readonly key: string;
  readonly scope: IntegrationFieldScope;
  readonly type: IntegrationFieldType;
  readonly label: string;
  readonly help: string | null;
  readonly required: boolean;
  readonly default: string | null;
  readonly placeholder: string | null;
  /** Present for `type: "enum"`; empty otherwise. */
  readonly options: readonly { readonly value: string; readonly label: string }[];
  /** Name of a `resources` kind that can fill this field (a picker), or `null`. */
  readonly resource: string | null;
  readonly visible_when: { readonly key: string; readonly equals: string } | null;
  /**
   * The stored token is bound to this field's origin: changing it leaves the token stale, so
   * a save that changes it must carry a new token. `false` from a CLI that predates the key.
   */
  readonly binds_token: boolean;
}

export interface IntegrationFact {
  readonly label: string;
  readonly value: string;
  readonly tone: IntegrationFactTone | null;
}

/** The last test result of one integration; `checked_at` is `null` while it was never tested. */
export interface IntegrationStatus {
  readonly state: IntegrationStatusState;
  readonly checked_at: string | null;
  readonly summary: string;
  readonly facts: readonly IntegrationFact[];
}

/** Alias kept for callers that name the state rather than the record. */
export type IntegrationState = IntegrationStatusState;

/** `integration list`'s `integrations[]`, and `integration show`. The token value is never part of it. */
export interface IntegrationView {
  readonly name: string;
  readonly title: string;
  readonly description: string;
  readonly homepage: string | null;
  readonly auth: {
    readonly kind: string;
    readonly label: string;
    readonly help: string | null;
    readonly has_token: boolean;
    /** A token is stored but the account's base URL origin changed since; it must be re-entered. */
    readonly stale: boolean;
    readonly backend: string | null;
  };
  readonly fields: readonly IntegrationField[];
  readonly account: Readonly<Record<string, string>>;
  /** `null` when no bound project was resolved. */
  readonly project: Readonly<Record<string, string>> | null;
  /** Why the committed project binding could not be read (it then reads as unset), or `null`. */
  readonly project_problem: string | null;
  /** Values inferred without the user (e.g. a repository from `git remote`). Empty when none. */
  readonly detected: Readonly<Record<string, string>>;
  readonly connected: boolean;
  readonly project_configured: boolean;
  readonly status: IntegrationStatus;
}

/** `test` inside a connect/test report. */
export interface IntegrationTestResult {
  readonly ok: boolean;
  readonly state: IntegrationStatusState;
  readonly summary: string;
  readonly facts: readonly IntegrationFact[];
  readonly checked_at: string | null;
}

/** `integration list --json`. */
export interface IntegrationList {
  readonly project_id: string | null;
  readonly integrations: readonly IntegrationView[];
}

/** `integration connect --json`. */
export interface IntegrationConnectReport {
  readonly integration: IntegrationView;
  readonly test: IntegrationTestResult;
  /** Set when the new token went to the unencrypted fallback store; `null` otherwise. */
  readonly warning: string | null;
}

/** `integration test --json`. A failed test is `test.ok: false`, not an error. */
export interface IntegrationTestReport {
  readonly integration: IntegrationView;
  readonly test: IntegrationTestResult;
  /** Only `connect` sets it; always `null` for `test`. */
  readonly warning: string | null;
}

/** `integration disconnect --json`. */
export interface IntegrationDisconnectReport {
  readonly integration: IntegrationView;
  readonly changed: boolean;
}

/** `integration config set --json` and `integration config unset --json`. */
export interface IntegrationConfigWrite {
  readonly integration: IntegrationView;
  readonly key: string;
  readonly removed?: boolean;
}

/** `integration resources --json`. */
export interface IntegrationResources {
  readonly items: readonly { readonly value: string; readonly label: string }[];
  readonly truncated: boolean;
}

// ── local credentials file (ADR-0024) ────────────────────────────────────────

/** A secret leaf in `CredentialsLocalView.data`: the value is never sent, only whether one is stored. */
export interface CredentialsSecretLeaf {
  readonly secret: true;
  readonly set: boolean;
}

/** Where a parse failure sits in the file on disk (1-based, as the CLI reports it). */
export interface CredentialsLocalParseError {
  readonly message: string;
  readonly line: number | null;
  readonly column: number | null;
}

/** `cred local show`, `cred local init` and `cred local patch`: one view of the file. */
export interface CredentialsLocalView {
  readonly path: string;
  readonly exists: boolean;
  readonly valid: boolean;
  readonly error: CredentialsLocalParseError | null;
  /** A machine-keyed token of the raw bytes, `null` when the file does not exist. Pass it back as `expectHash`. */
  readonly hash: string | null;
  /**
   * The parsed file, free-form. A value listed in its object's `$secrets`, or one whose name or
   * content looks secret, is replaced by a `CredentialsSecretLeaf`; `null` unless `valid`.
   */
  readonly data: Readonly<Record<string, unknown>> | null;
}

/** What `cred local show` puts in place of a hidden value. `marked`: listed in `$secrets`, not just secret-looking. */
export interface CredentialsSecretLeaf {
  readonly secret: true;
  readonly set: boolean;
  readonly marked: boolean;
}

/** The reserved keys of the local credentials file (ADR-0024); every other key is the user's own. */
export const CREDENTIALS_SECRETS_KEY = '$secrets';
export const CREDENTIALS_PRODUCTION_KEY = '$production';

/**
 * One edit for `cred local patch`; pointers are RFC 6901. `set` needs `value`; `move` needs `from`
 * and refuses an existing destination, so a hidden value can be renamed without the app holding it.
 */
export type CredentialsPatchOp =
  | { readonly op: 'set'; readonly pointer: string; readonly value: unknown }
  | { readonly op: 'unset'; readonly pointer: string }
  | { readonly op: 'move'; readonly from: string; readonly pointer: string };

/** `reason` on a refused `credentialsLocalPatch` when the file changed since it was read (exit 4). */
export const CREDENTIALS_HASH_CONFLICT = 'hash-conflict';
/** `reason` on a refused `credentialsLocalInit` when the file already exists (exit 4). */
export const CREDENTIALS_ALREADY_EXISTS = 'exists';
/** `reason` on a failed `credentialsLocalPatch` when the CLI exited 0 but its answer was unreadable: the save happened. */
export const CREDENTIALS_SAVED_UNREADABLE = 'saved-unreadable';

// ── the bridge ───────────────────────────────────────────────────────────────

/** Static facts about the build, so the UI can be honest about what it is. */
export interface BuildInfo {
  readonly appVersion: string;
  readonly electronVersion: string;
  readonly packaged: boolean;
  /**
   * False in every build this repository can currently produce. No Apple Developer ID
   * exists (ADR-0011's amendment: the app is "blocked on signing credentials the
   * repository owner holds"), so the UI states the unsigned state rather than letting a
   * `.dmg` look shippable.
   */
  readonly codeSigned: boolean;
  /**
   * Whether this build exposes any write action at all.
   *
   * It used to be the literal type `true`, and the field was named for the claim rather
   * than the question — so the type system itself would have had to be edited to admit a
   * write action, which is exactly what happened. It is now a boolean, and it is `false`
   * in this build: the project lifecycle (bind, unbind, sync, pin, upgrade) is reachable
   * from the UI. Kept rather than deleted, because a build that offers nothing but reads
   * is a state the UI should still be able to state plainly.
   */
  readonly hasWriteActions: boolean;
  /**
   * Commands the app runs that the framework classifies as **mutating**. Surfaced so
   * "read-only" is not a claim the UI makes that the classification tables contradict —
   * and now, with write actions wired, so the About surface can enumerate exactly what
   * this build can change without anyone reading `operations.ts` to find out.
   */
  readonly mutatingCommandsRun: readonly string[];
}

// ── the app's own preconditions ───────────────────────────────────────────────

/**
 * Whether the schema declaration `--client-schemas` needs could be written.
 *
 * ADR-0014's gate binds a client that declares; a client that declares nothing runs
 * **ungated**. So a failed write is not a cosmetic problem — it silently removes the
 * protection the app opted into, and it is reachable from a read-only `userData` volume
 * rather than only from a refactor. It therefore has a state the UI reads, and the app
 * withholds its one mutating command while that state is `failed`.
 */
export type DeclarationState =
  | { readonly state: 'written'; readonly path: string }
  | { readonly state: 'failed'; readonly path: string; readonly detail: string };

/** The app's own preconditions, each one visible rather than silently degraded. */
export interface EnvironmentReport {
  readonly declaration: DeclarationState;
  readonly settings: {
    readonly path: string;
    /** Set when the file exists and could not be used; the CLI search then ran without it. */
    readonly problem: string | null;
    readonly cliPathConfigured: boolean;
  };
  /**
   * The directory every invocation is given, as `cwd` and — where the command takes one —
   * as an explicit `--path`. Never inherited: the child's cwd used to be the main
   * process's, so `catalog` answered with a different `project_id` depending on where the
   * app was launched from.
   */
  readonly workingDirectory: string;
  /**
   * Commands the app is refusing right now, and why. Empty in the ordinary case.
   *
   * **`command` is the CLI's own subcommand words, space-joined** — `bind`, `unbind`,
   * `sync`, `pin`, `upgrade`, `doctor`, and `store gc` for a two-word leaf. Not a channel
   * name, not a UI label, not a prefixed identifier. Pinned here because it is the one
   * field both sides of this contract have to agree on without a type to enforce it: the
   * renderer decides whether an action is available by matching this string against the
   * command that action would run, and a mismatch silently re-enables a withheld button.
   * `BuildInfo.mutatingCommandsRun` uses the same spelling for the same reason.
   */
  readonly withheld: readonly { readonly command: string; readonly reason: string }[];
}

// ── the app's own health ──────────────────────────────────────────────────────

/**
 * A finding about **this app**, in `DoctorFinding`'s shape so one table renders both.
 *
 * `devteam doctor` diagnoses the store, the machine, the registry and a project. It says
 * nothing about the app, and it must not: ADR-0015 makes the app a pure client of the CLI,
 * so teaching the CLI to check its callers would invert that dependency. The app's own
 * preconditions were therefore observable — `EnvironmentReport`, `CliResolution` and the
 * `compat` handshake each carry the raw facts — but nothing *evaluated* them, so the one
 * question a user actually asks ("is this app healthy, and is it too old?") had no answer
 * anywhere in the UI.
 *
 * `level` and `category` are narrower here than in `DoctorFinding`, whose strings come from
 * the CLI and are widened on purpose because the app must render a category it has never
 * heard of. These are the app's own, so they are exhaustive and the compiler checks them.
 */
export interface AppFinding {
  readonly level: 'ok' | 'warn' | 'fail';
  readonly category: 'cli' | 'version' | 'declaration' | 'settings' | 'schemas' | 'actions';
  readonly message: string;
  readonly hint?: string;
}

/**
 * The evaluated verdict on this app, derived — never fetched.
 *
 * Computed by a pure function from values the bridge already returns, so this adds **no
 * IPC channel, no preload surface and no new spawn**. A self-check that needed its own
 * channel would have widened the attack surface of the contract to answer a question the
 * renderer could already answer from what it holds.
 *
 * `status` is the worst `level` present, so an all-`ok` report is `ok` and a single `fail`
 * makes the whole report `fail`.
 */
export interface AppHealth {
  readonly status: 'ok' | 'warn' | 'fail';
  readonly findings: readonly AppFinding[];
}

// ── global skills ─────────────────────────────────────────────────────────────

/** The providers whose user-level skill directories `devteam skills` manages. */
export type SkillProvider = Provider;
export type SkillProviderFilter = SkillProvider | 'all';

/**
 * One global skill directory. `id` is data, not an enum: the CLI decides which roots exist
 * (today `claude`, `agents`, `codex`, `opencode`) and this app only echoes it back to name
 * a skill's location. `path` is display text; it is never sent back to the main process.
 */
export interface SkillRoot {
  readonly id: string;
  readonly path: string;
  readonly exists: boolean;
  readonly providers: readonly string[];
  readonly install_target_for: readonly string[];
}

/** One skill found in one root. The same name in two roots is two records. */
export interface SkillRecord {
  readonly name: string;
  readonly description: string | null;
  readonly root: string;
  readonly root_path: string | null;
  readonly path: string;
  readonly providers: readonly string[];
  readonly is_symlink: boolean;
  readonly link_target: string | null;
  /** Owned by dev-team-agents itself: the CLI refuses to remove or replace it (exit 4). */
  readonly managed: boolean;
  readonly status: 'ok' | 'malformed';
  readonly error: string | null;
}

export interface SkillList {
  readonly provider: string;
  readonly roots: readonly SkillRoot[];
  readonly skills: readonly SkillRecord[];
}

/** `skills show`: the record plus what the directory holds. `body` is text, never markup. */
export interface SkillDetail extends SkillRecord {
  readonly body: string | null;
  readonly files: readonly string[];
  readonly files_truncated: boolean;
}

/**
 * Where an install's source comes from. Never a path: `pick` opens the main process's one
 * native picker (folder, `SKILL.md` or archive), and `previous` reuses what it last returned.
 */
export type SkillSourceChoice = 'pick' | 'previous';

export interface SkillInstallRequest {
  readonly source: SkillSourceChoice;
  readonly providers: readonly SkillProvider[];
  readonly replace: boolean;
  /** Symlink instead of copy. Only meaningful for a folder; refused for an archive. */
  readonly link: boolean;
}

export interface SkillInstalledTo {
  readonly root: string;
  readonly path: string;
  readonly providers: readonly string[];
  readonly replaced: boolean;
  readonly quarantined_to: string | null;
}

export interface SkillInstallReport {
  readonly name: string;
  readonly description: string | null;
  readonly source: string | null;
  readonly linked: boolean;
  /** `file`: a loose `.md` became the skill's `SKILL.md`, and nothing beside it was copied. */
  readonly source_kind: 'folder' | 'archive' | 'file';
  readonly installed: readonly SkillInstalledTo[];
  /** Other roots a target's providers also read that already hold a skill of this name. */
  readonly also_present: readonly { readonly root: string; readonly path: string }[];
}

/**
 * The answer to an install: either the user dismissed the picker (nothing ran), or the CLI
 * ran and `result` says how it went. `source` is display text for what the user picked; a
 * retry names `'previous'` rather than sending it back.
 */
export type SkillInstallAnswer =
  | { readonly picked: false }
  | { readonly picked: true; readonly source: string; readonly result: OperationResult<SkillInstallReport> };

/** A skill is named by name and root id, both of which the main process checks against `skills list`. */
export interface SkillRemoveRequest {
  readonly name: string;
  readonly root: string;
}

export interface SkillRemoveReport {
  readonly name: string;
  readonly root: string;
  readonly path: string;
  readonly providers: readonly string[];
  readonly action: 'unlinked' | 'quarantined';
  readonly quarantined_to: string | null;
  /** Where an unlinked symlink pointed — the only record of it, since a link is not quarantined. */
  readonly link_target: string | null;
}

export interface DevteamBridge {
  readonly buildInfo: () => Promise<BuildInfo>;
  readonly environment: () => Promise<EnvironmentReport>;
  readonly resolveCli: () => Promise<CliResolution>;
  readonly handshake: () => Promise<OperationResult<HandshakeView>>;
  readonly listProjects: () => Promise<OperationResult<ProjectList>>;
  readonly catalogSummary: () => Promise<OperationResult<CatalogSummary>>;
  readonly catalogListing: (kind: CatalogKind) => Promise<OperationResult<CatalogListing>>;
  readonly catalogEntry: (name: string) => Promise<OperationResult<CatalogDetail>>;
  readonly doctor: () => Promise<OperationResult<DoctorReport>>;
  /**
   * The app's own names for bound projects, keyed by `project_id`. Spawns nothing.
   *
   * Read-only and app-local (see `BindRequest.name`). A project with no stored name is
   * absent from this map rather than present with a placeholder, so the caller decides
   * the fallback — which is the directory's own basename, so **no row ever renders a
   * bare UUID**, including for a project bound from the terminal and never named here.
   */
  readonly projectNames: () => Promise<Readonly<Record<string, string>>>;
  /**
   * The Projects screen's folders (ADR-0021). Spawns nothing; app-local, like
   * `projectNames`. See `shared/projectFolders.ts` for the model.
   */
  readonly projectFolders: () => Promise<ProjectFolders>;
  /**
   * Replace the whole folder state. The main process validates it with
   * `projectFoldersProblem` and writes nothing when it is refused. Spawns nothing — this is
   * the app's own file, so it is not gated by the CLI's write gate.
   */
  readonly saveProjectFolders: (folders: ProjectFolders) => Promise<ProjectFoldersAnswer>;

  // Write actions. Each one spawns a command in `compat.MUTATING`, so each one is
  // refused at exit 4 by the framework's own gate whenever the store is ahead of this
  // app's declaration — the app does not decide that, it declares and is told.
  /** Opens the native directory picker in the main process. Spawns nothing. */
  readonly chooseProjectDirectory: () => Promise<DirectoryChoice>;
  readonly bindProject: (request: BindRequest) => Promise<OperationResult<BindReport>>;
  readonly unbindProject: (projectId: ProjectId) => Promise<OperationResult<UnbindReport>>;
  readonly syncProject: (projectId: ProjectId) => Promise<OperationResult<BindReport>>;
  readonly syncAllProjects: () => Promise<OperationResult<SyncAllReport>>;
  /** `version: null` releases the pin, which is `pin --release`, not `pin ""`. */
  readonly setPin: (
    projectId: ProjectId,
    version: string | null,
  ) => Promise<OperationResult<PinReport>>;
  readonly planUpgrade: (projectId: ProjectId) => Promise<OperationResult<UpgradePlan>>;
  readonly applyUpgrade: (projectId: ProjectId) => Promise<OperationResult<UpgradeReport>>;
  /** `migrate <path>` — the plan for a v2 install in a directory the picker offered. Writes nothing. */
  readonly planMigration: (request: MigrateRequest) => Promise<OperationResult<MigrationPlan>>;
  /** `migrate <path> --apply --untrack`. Quarantines the v2 tree, binds, and untracks what the plan listed. */
  readonly applyMigration: (request: MigrateRequest) => Promise<OperationResult<MigrationReport>>;
  /** `prefs list` for one project. Read-only. */
  readonly projectPreferences: (projectId: ProjectId) => Promise<OperationResult<ProjectPreferencesView>>;
  /**
   * Writes a batch into the **project** layer only — `prefs set/unset --scope project`.
   * Every key must be one `prefs list` returned for that project, and every value must pass
   * `valueProblem` in `shared/preferenceRules.ts`; the main process checks both. Turning a
   * consent key on asks the user in a native dialog the renderer cannot answer for them.
   */
  readonly updateProjectPreferences: (
    projectId: ProjectId,
    changes: readonly PreferenceChange[],
  ) => Promise<OperationResult<PreferenceUpdateReport>>;

  /** `plugin list` for one project. Read-only; runs the status script of each enabled plugin. */
  readonly projectPlugins: (projectId: ProjectId) => Promise<OperationResult<PluginList>>;
  /**
   * `plugin enable` / `plugin disable`. Changes a **committed** file in the project. The
   * plugin `name` must be one this project's own `plugin list` answer returned.
   */
  readonly setPluginEnabled: (
    projectId: ProjectId,
    name: string,
    enabled: boolean,
  ) => Promise<OperationResult<PluginToggleReport>>;
  /**
   * `plugin config set/unset`, applied in order and stopped at the first failure. Every key
   * must be a `config_fields` entry of that plugin in the project's own `plugin list`
   * answer, and every value must pass `pluginValueProblem` for that field's type.
   */
  readonly updatePluginConfig: (
    projectId: ProjectId,
    name: string,
    changes: readonly PluginConfigChange[],
  ) => Promise<OperationResult<PluginConfigUpdateReport>>;
  /**
   * `plugin run`. `name` and `actionId` are checked against the project's own `plugin list`
   * answer before anything is spawned; an `output: "config"` action proposes values and
   * writes nothing.
   */
  readonly runPluginAction: (
    projectId: ProjectId,
    name: string,
    actionId: string,
  ) => Promise<OperationResult<PluginRunResult>>;
  /**
   * Opens the OS picker at the project's root for a field that declares a `picker` and
   * answers with a **project-relative** path only. The renderer never holds an absolute
   * path; main refuses a choice outside the project (symlinks resolved), the root itself,
   * and anything under `.git` / `.dev-team-agents`. Spawns nothing.
   */
  readonly pickProjectPath: (projectId: ProjectId, picker: PluginFieldPicker) => Promise<ProjectPathPick>;
  /**
   * Integrations (ADR-0023). Every operation is a named CLI command; `projectId` is resolved to a
   * registered project path in the main process, `null` meaning no project. The token travels
   * to the CLI over stdin only and is never returned, logged or stored by this app.
   */
  readonly integrationList: (projectId: ProjectId | null) => Promise<OperationResult<IntegrationList>>;
  /** `token: null` (or empty) keeps an existing token; `fields` are account-scope values only. */
  readonly integrationConnect: (
    name: string,
    fields: Readonly<Record<string, string>>,
    token: string | null,
    projectId: ProjectId | null,
  ) => Promise<OperationResult<IntegrationConnectReport>>;
  readonly integrationTest: (name: string, projectId: ProjectId | null) => Promise<OperationResult<IntegrationTestReport>>;
  readonly integrationDisconnect: (name: string, keepToken: boolean) => Promise<OperationResult<IntegrationDisconnectReport>>;
  readonly integrationConfigSet: (
    name: string,
    key: string,
    value: string,
    projectId: ProjectId | null,
  ) => Promise<OperationResult<IntegrationConfigWrite>>;
  readonly integrationConfigUnset: (
    name: string,
    key: string,
    projectId: ProjectId | null,
  ) => Promise<OperationResult<IntegrationConfigWrite>>;
  readonly integrationResources: (
    name: string,
    kind: string,
    projectId: ProjectId | null,
  ) => Promise<OperationResult<IntegrationResources>>;
  /**
   * The project's local credentials file (ADR-0024). Secret values never come back: a secret
   * leaf is `{secret: true, set}`. `credentialsLocalPatch` sends `ops` over stdin and is
   * refused with `reason: 'hash-conflict'` (kind `conflict`) when the file changed on disk
   * since `expectHash` was read; `credentialsLocalInit` is refused with `reason: 'exists'`.
   */
  readonly credentialsLocalShow: (projectId: ProjectId) => Promise<OperationResult<CredentialsLocalView>>;
  readonly credentialsLocalInit: (projectId: ProjectId) => Promise<OperationResult<CredentialsLocalView>>;
  readonly credentialsLocalPatch: (
    projectId: ProjectId,
    expectHash: string,
    ops: readonly CredentialsPatchOp[],
  ) => Promise<OperationResult<CredentialsLocalView>>;
  // Notifications. The main process owns the stream (`devteam notifications watch`) and
  // shows each one natively, so they arrive with the window closed; the renderer only
  // reads the feed for the bell. Spawns nothing from the renderer's side.
  readonly notificationFeed: () => Promise<NotificationFeed>;
  /** The bell was opened: the unread count returns to zero. App-local; spawns nothing. */
  readonly markNotificationsRead: () => Promise<NotificationFeed>;
  /** Stop showing native notifications for this app session; the bell still fills. */
  readonly setNotificationsPaused: (paused: boolean) => Promise<NotificationFeed>;
  /** Called with the feed whenever it changes. Returns the unsubscribe. */
  readonly onNotificationFeed: (listener: (feed: NotificationFeed) => void) => () => void;
  /** A notification (or the tray) asked to show a project. Returns the unsubscribe. */
  readonly onOpenProject: (listener: (projectId: ProjectId) => void) => () => void;
  /**
   * Call once `onOpenProject` is subscribed: returns the project a click asked for before
   * the renderer was listening (a fresh window loads after the click), and from then on
   * the main process pushes instead of holding.
   */
  readonly takePendingProject: () => Promise<ProjectId | null>;

  // Running in the background (phase 2). App-level, not a project preference.
  readonly backgroundSettings: () => Promise<BackgroundSettings>;
  /** Opt in or out of starting at login. Reports what the OS actually recorded. */
  readonly setOpenAtLogin: (enabled: boolean) => Promise<BackgroundSettings>;

  /** `skills list` for a provider filter. Read-only. */
  readonly listSkills: (provider: SkillProviderFilter) => Promise<OperationResult<SkillList>>;
  /** `skills show`. Read-only; `root` comes from a listed record. */
  readonly showSkill: (name: string, root: string) => Promise<OperationResult<SkillDetail>>;
  /**
   * `skills install`. The native picker opens in the main process **inside this call**, and
   * the chosen path goes to the CLI from there; the renderer receives the result only.
   */
  readonly installSkill: (request: SkillInstallRequest) => Promise<SkillInstallAnswer>;
  /** `skills remove`. A directory is moved to quarantine, a symlink is unlinked; nothing is deleted. */
  readonly removeSkill: (request: SkillRemoveRequest) => Promise<OperationResult<SkillRemoveReport>>;
  // The task board. The main process owns `devteam tasks watch` and keeps the latest
  // snapshot per project; the renderer reads it and hears every change.
  readonly taskBoard: () => Promise<BoardFeed>;
  /** One `tasks list`, replacing the snapshots — for a manual refresh. */
  readonly refreshTaskBoard: () => Promise<BoardFeed>;
  /** Called with the feed whenever it changes. Returns the unsubscribe. */
  readonly onTaskBoard: (listener: (feed: BoardFeed) => void) => () => void;
  readonly boardSettings: () => Promise<BoardSettings>;
  readonly setBoardSettings: (settings: BoardSettings) => Promise<BoardSettingsAnswer>;
  /** Open one validated PR/MR or issue link in the OS browser; the renderer sends ids, never a URL. */
  readonly openTaskLink: (request: OpenTaskLinkRequest) => Promise<OpenTaskLinkAnswer>;
}

export type NotificationLevel = 'info' | 'warning' | 'critical';

/** A record from `devteam notifications list|watch`, camel-cased at the boundary. */
export interface QueuedNotification {
  readonly id: string;
  readonly level: NotificationLevel;
  /** Stable identifier the hook chose, e.g. `context.critical`. */
  readonly code: string;
  /** Already in the user's language — the hook rendered it. */
  readonly message: string;
  /** Epoch seconds. */
  readonly ts: number;
  readonly projectId: ProjectId;
  readonly sessionId: string;
  /** Epoch seconds; 0 = never expires. */
  readonly expiresAt: number;
  readonly seen: boolean;
}

export interface AppNotification extends QueuedNotification {
  /** The app's name for the project, or its directory's basename — never the UUID. */
  readonly projectName: string;
}

export type NotificationStreamStatus =
  /** No CLI resolved yet, or the stream is being started. */
  | 'starting'
  /** `ready` arrived; every new notification is shown as it lands. */
  | 'live'
  /** The stream ended unexpectedly; it restarts after a backoff. */
  | 'retrying'
  /** It cannot run at all — no CLI, or the store needs a migration first. */
  | 'unavailable';

export interface NotificationFeed {
  readonly status: NotificationStreamStatus;
  /** Why the status is not `live`, in plain language; null when it is. */
  readonly detail: string | null;
  /** Newest first, capped. Everything received this app session, shown or not. */
  readonly items: readonly AppNotification[];
  /** Received since the bell was last opened. */
  readonly unread: number;
  readonly paused: boolean;
}

/** What `app.getLoginItemSettings()` reports, reduced to what the UI must say. */
export type LoginItemStatus =
  | 'enabled'
  | 'disabled'
  /** macOS 13+: registered, but the user must approve it in System Settings. */
  | 'requires-approval'
  /** macOS 13+: the OS did not record it — typical of an unsigned build. */
  | 'not-registered'
  /** Development build: `electron .` has no bundle to register. */
  | 'unsupported';

export interface BackgroundSettings {
  /** What the user chose. */
  readonly openAtLogin: boolean;
  /** What the OS says, which is what the UI shows — never the choice alone. */
  readonly loginItemStatus: LoginItemStatus;
  readonly detail: string | null;
}

// ── the task board (ADR-0018) ─────────────────────────────────────────────────

export type BoardColumn = 'todo' | 'in_progress' | 'in_review' | 'pr_created' | 'done';
/** `unknown`: the CLI sent no review state this app knows; the card claims nothing about the result. */
export type BoardReviewState = 'pending' | 'findings' | 'unread' | 'unknown';
export type BoardSessionStatus = 'active' | 'idle' | 'ended';

export interface BoardCounts {
  readonly todo: number;
  readonly in_progress: number;
  /** Tasks in the review window; 0 when an older CLI does not emit the field. */
  readonly in_review: number;
  /** Finished tasks whose pull/merge request is open; 0 when an older CLI does not emit the field. */
  readonly pr_created: number;
  readonly done: number;
  readonly total: number;
}

export type BoardPrKind = 'pr' | 'mr';
export type BoardPrState = 'open' | 'merged';

/** The pull request (`pr`) or merge request (`mr`) a task shipped in. `url` is the CLI's rebuilt, validated URL. */
export interface BoardTaskPr {
  readonly kind: BoardPrKind;
  readonly number: number;
  readonly url: string;
  readonly state: BoardPrState;
}

/** A pull/merge request of a session, for its chip. */
export interface BoardSessionPr extends BoardTaskPr {
  readonly head: string | null;
}

export type BoardRefSystem = 'jira' | 'github';

/** An issue the task refers to: `PROJ-12` (Jira) or `owner/repo#45` (GitHub). */
export interface BoardRef {
  readonly system: BoardRefSystem;
  readonly key: string;
  readonly url: string;
}

/** What a link host may be used for; the CLI decides, and the app re-checks every link against it. */
export type BoardLinkKind = 'github_pr' | 'github_issue' | 'gitlab_mr' | 'jira';

export interface BoardLinkHost {
  readonly host: string;
  readonly kinds: readonly BoardLinkKind[];
  /** Jira Server context path (`/jira`); absent means the host root. Never set on GitHub or GitLab entries. */
  readonly base_path?: string;
}

/** A task's review window; `findings` is null until a result is read. `since` is epoch seconds. */
export interface BoardReview {
  readonly state: BoardReviewState;
  readonly findings: number | null;
  readonly since: number;
}

export type BoardTaskKind = 'agent' | 'todo' | 'direct';

/** One turn of a `direct` task: an excerpt of the prompt that triggered the work. */
export interface BoardTurn {
  /** At most 100 characters, secret-redacted by the CLI; empty when the prompt was not captured. */
  readonly text: string;
  /** Epoch seconds. */
  readonly at: number;
}

/** One task, as `devteam tasks list|watch --json` derives it. Epoch fields are seconds. */
export interface BoardTask {
  readonly key: string;
  readonly content: string;
  readonly owner: string;
  readonly agent_type: string | null;
  readonly status: string;
  readonly column: BoardColumn;
  readonly created_at: number;
  /** When the task entered its current status; "time in column" is `now - status_since`. */
  readonly status_since: number;
  readonly completed_at: number | null;
  /** Seconds spent per status (`pending`, `in_progress`, `completed`, ...). */
  readonly durations: Readonly<Record<string, number>>;
  readonly stale: boolean;
  readonly abandoned: boolean;
  /**
   * `agent` for a spawned sub-agent run, `direct` for the one card of work the main session did
   * itself, `todo` otherwise (and for a CLI that predates the field or sends an unknown kind).
   */
  readonly kind: BoardTaskKind;
  /** An agent task whose run failed; false for a CLI that predates the field. */
  readonly failed: boolean;
  /** Null when the task is not in review (and for a CLI that predates the review window). */
  readonly review: BoardReview | null;
  /**
   * The linked worktree the task was started in; null in the main checkout (and for a CLI that
   * predates the field).
   */
  readonly worktree: BoardWorktree | null;
  /** The prompts behind a `direct` task, oldest first (at most 20); empty for other kinds and older CLIs. */
  readonly turns: readonly BoardTurn[];
  /** The PR/MR the task is a member of; null when none (and for a CLI that predates the field). */
  readonly pr: BoardTaskPr | null;
  /** Issue-tracker references; empty when none (and for a CLI that predates the field). */
  readonly refs: readonly BoardRef[];
}

export interface BoardWorktree {
  /** Relative to the main checkout when it lives under it (`.worktrees/feat/x`), else absolute. */
  readonly path: string;
  readonly branch: string | null;
}

export interface BoardSession {
  readonly session_id: string;
  /** The title the provider shows for the session; `null` when it has none or the CLI predates it. */
  readonly title: string | null;
  /** `claude`, `codex` or `opencode` today; kept open so a new provider degrades to a generic icon. */
  readonly provider: string;
  readonly branch: string | null;
  readonly cwd: string;
  readonly status: BoardSessionStatus;
  readonly created_at: number;
  readonly last_activity_at: number;
  readonly ended_at: number | null;
  /** A single-line shell command the CLI composed; `null` when the shape did not validate. */
  readonly resume_command: string | null;
  readonly counts: BoardCounts;
  /** Empty for a CLI that predates the field. */
  readonly prs: readonly BoardSessionPr[];
  readonly tasks: readonly BoardTask[];
}

export interface BoardProject {
  readonly project_id: ProjectId;
  readonly root: string;
  readonly providers: readonly string[];
  readonly sessions_total: number;
  readonly sessions_active: number;
  readonly counts: BoardCounts;
  readonly stale: number;
  readonly abandoned: number;
  /** Tasks in review with findings; 0 from an older CLI. */
  readonly with_findings: number;
  /** Epoch seconds the CLI computed this view at; absent from an older CLI. Live figures grow from it. */
  readonly as_of?: number;
  readonly last_activity_at: number;
  /** Hosts this project's links may point at, per kind; empty from an older CLI (no link opens). */
  readonly link_hosts: readonly BoardLinkHost[];
  readonly sessions: readonly BoardSession[];
}

export type BoardStreamStatus = 'starting' | 'live' | 'retrying' | 'unavailable';

/** What the main process keeps and pushes: the latest snapshot of every project with tasks. */
export interface BoardFeed {
  readonly status: BoardStreamStatus;
  /** Why the status is not `live`, in plain language; null when it is. */
  readonly detail: string | null;
  /** Newest activity first. Only projects with at least one task are ever here. */
  readonly projects: readonly BoardProject[];
  /** Set only on the answer to a manual refresh whose one-shot `list` failed; never pushed or stored. */
  readonly refreshError?: string;
}

/**
 * A request to open one link of the board. Ids only, never a URL: the main process looks the
 * link up in its own latest snapshot and validates it before the OS browser sees it.
 */
export interface OpenTaskLinkRequest {
  readonly project_id: string;
  readonly session_id: string;
  /** `null` for a link on a session chip (`type: 'pr'` indexes `session.prs`). */
  readonly task_key: string | null;
  /**
   * `pr`: the task's own PR/MR (index 0) or a session PR; `ref`: `task.refs[index]`. `expect` is
   * the number (`"12"`) or key (`"PROJ-3"`, `"o/r#4"`) the badge showed: a snapshot that moved
   * between render and click resolves to another link, and that one is refused, never opened.
   */
  readonly link: { readonly type: 'pr' | 'ref'; readonly index: number; readonly expect: string };
}

export type OpenTaskLinkAnswer = { readonly ok: true } | { readonly ok: false; readonly message: string };

/** App-local (`settings.json`); never a `preferences.json` key. */
export interface BoardSettings {
  /** An in-progress task older than this, in a live session, is flagged stale. */
  readonly staleAfterMinutes: number;
  /** The kanban hides done tasks older than this by default. */
  readonly doneRetentionDays: number;
  /** A "Direct work" card left in To Do (a turn that only read) is hidden after this long idle. */
  readonly directTodoTtlHours: number;
}

export type BoardSettingsAnswer =
  | { readonly ok: true; readonly settings: BoardSettings }
  | { readonly ok: false; readonly message: string };

/** The bounds `boardSettings` enforces; shared so the form and the main process agree. */
export const BOARD_SETTING_BOUNDS = {
  staleAfterMinutes: { min: 5, max: 1440, fallback: 60 },
  doneRetentionDays: { min: 1, max: 365, fallback: 7 },
  directTodoTtlHours: { min: 1, max: 720, fallback: 24 },
} as const;

/** The channel names, shared so main and preload cannot disagree about a string. */
export const CHANNELS = {
  buildInfo: 'devteam:build-info',
  environment: 'devteam:environment',
  resolveCli: 'devteam:resolve-cli',
  handshake: 'devteam:handshake',
  listProjects: 'devteam:list-projects',
  catalogSummary: 'devteam:catalog-summary',
  catalogListing: 'devteam:catalog-listing',
  catalogEntry: 'devteam:catalog-entry',
  doctor: 'devteam:doctor',
  projectNames: 'devteam:project-names',
  projectFolders: 'devteam:project-folders',
  saveProjectFolders: 'devteam:save-project-folders',
  chooseProjectDirectory: 'devteam:choose-project-directory',
  bindProject: 'devteam:bind-project',
  unbindProject: 'devteam:unbind-project',
  syncProject: 'devteam:sync-project',
  syncAllProjects: 'devteam:sync-all-projects',
  setPin: 'devteam:set-pin',
  planUpgrade: 'devteam:plan-upgrade',
  applyUpgrade: 'devteam:apply-upgrade',
  planMigration: 'devteam:plan-migration',
  applyMigration: 'devteam:apply-migration',
  projectPreferences: 'devteam:project-preferences',
  updateProjectPreferences: 'devteam:update-project-preferences',
  projectPlugins: 'devteam:project-plugins',
  setPluginEnabled: 'devteam:set-plugin-enabled',
  updatePluginConfig: 'devteam:update-plugin-config',
  runPluginAction: 'devteam:run-plugin-action',
  pickProjectPath: 'devteam:pick-project-path',
  integrationList: 'devteam:integration-list',
  integrationConnect: 'devteam:integration-connect',
  integrationTest: 'devteam:integration-test',
  integrationDisconnect: 'devteam:integration-disconnect',
  integrationConfigSet: 'devteam:integration-config-set',
  integrationConfigUnset: 'devteam:integration-config-unset',
  integrationResources: 'devteam:integration-resources',
  credentialsLocalShow: 'devteam:credentials-local-show',
  credentialsLocalInit: 'devteam:credentials-local-init',
  credentialsLocalPatch: 'devteam:credentials-local-patch',
  notificationFeed: 'devteam:notification-feed',
  markNotificationsRead: 'devteam:mark-notifications-read',
  setNotificationsPaused: 'devteam:set-notifications-paused',
  /** Main → renderer push. */
  notificationFeedChanged: 'devteam:notification-feed-changed',
  /** Main → renderer push. */
  openProject: 'devteam:open-project',
  takePendingProject: 'devteam:take-pending-project',
  backgroundSettings: 'devteam:background-settings',
  setOpenAtLogin: 'devteam:set-open-at-login',
  listSkills: 'devteam:list-skills',
  showSkill: 'devteam:show-skill',
  installSkill: 'devteam:install-skill',
  removeSkill: 'devteam:remove-skill',
  taskBoard: 'devteam:task-board',
  refreshTaskBoard: 'devteam:refresh-task-board',
  /** Main → renderer push. */
  taskBoardChanged: 'devteam:task-board-changed',
  boardSettings: 'devteam:board-settings',
  setBoardSettings: 'devteam:set-board-settings',
  openTaskLink: 'devteam:open-task-link',
} as const;
