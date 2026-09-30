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

export type BindProvider = 'claude' | 'opencode' | 'codex';
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
  chooseProjectDirectory: 'devteam:choose-project-directory',
  bindProject: 'devteam:bind-project',
  unbindProject: 'devteam:unbind-project',
  syncProject: 'devteam:sync-project',
  syncAllProjects: 'devteam:sync-all-projects',
  setPin: 'devteam:set-pin',
  planUpgrade: 'devteam:plan-upgrade',
  applyUpgrade: 'devteam:apply-upgrade',
  projectPreferences: 'devteam:project-preferences',
  updateProjectPreferences: 'devteam:update-project-preferences',
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
} as const;
