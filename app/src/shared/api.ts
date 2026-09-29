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
   * The app offers no write action of its own: no bind, no preference edit, no credential
   * change. Stated rather than implied, because the next field qualifies it.
   */
  readonly noWriteActions: true;
  /**
   * Commands the app runs that the framework classifies as **mutating**. Today: `doctor`,
   * which `compat.MUTATING` lists because it repairs what it finds. Surfaced so "read-only"
   * is not a claim the UI makes that the classification tables contradict.
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
  /** Commands the app is refusing right now, and why. Empty in the ordinary case. */
  readonly withheld: readonly { readonly command: string; readonly reason: string }[];
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
} as const;
