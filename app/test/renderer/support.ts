/**
 * Shared fixtures and a typed fake `window.devteam` for the renderer test suite.
 *
 * These are render tests, not invocation tests: nothing here spawns a process or touches
 * a real store (that layer is already covered by `invoke.test.ts`, `operations.test.ts`,
 * `ipc.test.ts` and `real-cli.test.ts`). Every bridge method is a `vi.fn()` a test wires
 * up to answer with a fixture, so a screen can be mounted against exactly the payload
 * shape a test wants to assert on.
 */
import { vi } from 'vitest';

import type {
  BindReport,
  BoardFeed,
  BoardSettings,
  BuildInfo,
  CliResolution,
  AppNotification,
  BackgroundSettings,
  DevteamBridge,
  NotificationFeed,
  DoctorReport,
  EnvironmentReport,
  HandshakeView,
  OperationResult,
  PluginConfigChange,
  PluginConfigField,
  PluginList,
  PluginRunResult,
  PluginView,
  PreferenceChange,
  ProjectPreferencesView,
  ProblemKind,
  ProjectRecord,
  UnbindReport,
  MigrationPlan,
  MigrationReport,
  UpgradePlan,
  UpgradeReport,
  CredentialsLocalView,
} from '../../src/shared/api.js';

/** A successful `OperationResult`, `notice` omitted unless given — matches the real shape. */
export function ok<T>(data: T, extra: { notice?: string; outcome?: 'success' | 'findings' } = {}): OperationResult<T> {
  return {
    ok: true,
    outcome: extra.outcome ?? 'success',
    data,
    command: 'devteam test',
    durationMs: 1,
    ...(extra.notice !== undefined ? { notice: extra.notice } : {}),
  };
}

/** A failed `OperationResult`, `hint` omitted unless given. */
export function fail(
  message: string,
  extra: { kind?: ProblemKind; hint?: string; exitCode?: number | null; reason?: string } = {},
): Extract<OperationResult<never>, { ok: false }> {
  return {
    ok: false,
    kind: extra.kind ?? 'environment',
    message,
    exitCode: extra.exitCode ?? 1,
    command: 'devteam test',
    durationMs: 1,
    ...(extra.hint !== undefined ? { hint: extra.hint } : {}),
    ...(extra.reason !== undefined ? { reason: extra.reason } : {}),
  };
}

export function project(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    project_id: 'proj-1',
    path: '/repo/project-1',
    providers: ['claude'],
    mode: 'link',
    pin: null,
    resolves_to: '2.48.0',
    path_exists: true,
    ...overrides,
  };
}

export function environment(overrides: Partial<EnvironmentReport> = {}): EnvironmentReport {
  return {
    declaration: { state: 'written', path: '/app/schemas.json' },
    settings: { path: '/app/settings.json', problem: null, cliPathConfigured: true },
    workingDirectory: '/repo/project-1',
    withheld: [],
    ...overrides,
  };
}

export function buildInfo(overrides: Partial<BuildInfo> = {}): BuildInfo {
  return {
    appVersion: '1.0.0',
    electronVersion: '30.0.0',
    packaged: false,
    codeSigned: false,
    hasWriteActions: false,
    mutatingCommandsRun: [],
    ...overrides,
  };
}

/** The `found: true` branch — the ordinary case a fake bridge should answer with. */
export function cliResolutionFound(overrides: {
  readonly cli?: Partial<Extract<CliResolution, { found: true }>['cli']>;
  readonly rejected?: CliResolution['rejected'];
} = {}): CliResolution {
  return {
    found: true,
    rejected: overrides.rejected ?? [],
    cli: {
      path: '/opt/homebrew/bin/devteam',
      source: 'path',
      sourceDetail: 'PATH',
      storeVersion: '2.48.0',
      jsonContract: 1,
      minAppVersion: null,
      storeSchemas: {},
      ...overrides.cli,
    },
  };
}

/** The `found: false` branch, for a test that needs the no-CLI state. */
export function cliResolutionNotFound(overrides: Partial<Extract<CliResolution, { found: false }>> = {}): CliResolution {
  return {
    found: false,
    rejected: [],
    searchedCount: 3,
    searchedBySource: [],
    remedy: ['Install the CLI: `brew install dev-toolbelt/devteam/devteam`.'],
    ...overrides,
  };
}

export function handshakeView(overrides: Partial<Extract<HandshakeView, { state: 'answered' }>> = {}): HandshakeView {
  return {
    state: 'answered',
    mayWrite: true,
    jsonContract: 1,
    minAppVersion: null,
    storeSchemas: {},
    clientSchemas: {},
    unsupported: {},
    summary: 'compatible',
    ...overrides,
  };
}

export function bindReport(overrides: Partial<BindReport> = {}): BindReport {
  return {
    path: '/repo/project-2',
    project_id: 'proj-2',
    version: '2.48.0',
    mode: 'link',
    providers: ['claude'],
    artifacts: 12,
    identity_created: true,
    gitignore: 'updated',
    git_exclude: 'updated',
    pin: null,
    fallback_reason: null,
    retired: [],
    merged_project_files: [],
    ...overrides,
  };
}

export function unbindReport(overrides: Partial<UnbindReport> = {}): UnbindReport {
  return {
    path: '/repo/project-1',
    project_id: 'proj-1',
    unlinked: Array.from({ length: 159 }, (_, index) => `file-${index}`),
    quarantined: [],
    kept: [],
    problems: [],
    ...overrides,
  };
}

export function upgradePlan(overrides: Partial<UpgradePlan> = {}): UpgradePlan {
  return {
    path: '/repo/project-1',
    project_id: 'proj-1',
    from_layout: 1,
    to_layout: 2,
    files: 3,
    source: '.dev-team-agents/user-data',
    destination: '/store/data/projects/proj-1',
    state_destination: '/store/data/machines/m1/projects/proj-1',
    machine_local: [],
    retained: [],
    collisions: [],
    git_tracked: [],
    actions: ['move session-summary.md'],
    ...overrides,
  };
}

export function upgradeReport(overrides: Partial<UpgradeReport> = {}): UpgradeReport {
  return {
    path: '/repo/project-1',
    project_id: 'proj-1',
    from_layout: 1,
    to_layout: 2,
    copied: 3,
    retained: [],
    destination: '/store/data/projects/proj-1',
    state_destination: '/store/data/machines/m1/projects/proj-1',
    quarantined: null,
    state_pointer: '/repo/project-1/.dev-team-agents/memory-dir',
    memory_pointer: '/repo/project-1/.dev-team-agents/memory-dir',
    git_tracked: [],
    ...overrides,
  };
}

export function migrationPlan(overrides: Partial<MigrationPlan> = {}): MigrationPlan {
  return {
    path: '/chosen/dir',
    layout: 'pre-root',
    install_dir: '.claude/dev-team-agents',
    providers: ['claude'],
    mode: 'link',
    actions: ['move .claude/dev-team-agents/agents into the data-store quarantine', 'bind providers: claude (mode=link)'],
    adopts_identity: false,
    memory_moves: [{ from: '.claude/user-data', to: '.dev-team-agents/user-data' }],
    context_paths_added: ['.claude/docs'],
    git_tracked: ['.claude/dev-team-agents/agents', '.claude/user-data'],
    git_tracked_artifacts: ['.claude/agents/dev-team'],
    preserved: ['user-data', 'project.json'],
    ...overrides,
  };
}

export function migrationReport(overrides: Partial<MigrationReport> = {}): MigrationReport {
  return {
    path: '/chosen/dir',
    layout: 'pre-root',
    project_id: 'proj-new',
    version: '2.48.0',
    mode: 'link',
    providers: ['claude'],
    adopted_identity: false,
    memory_moved: [{ from: '.claude/user-data', to: '.dev-team-agents/user-data' }],
    context_paths_added: ['.claude/docs'],
    quarantined: [{ from: '.claude/dev-team-agents/agents', to: '/store/data/quarantine/x/agents' }],
    quarantine_dir: '/store/data/quarantine/x',
    retired_links: [],
    git_tracked: ['.claude/dev-team-agents/agents', '.claude/user-data'],
    git_tracked_artifacts: ['.claude/agents/dev-team'],
    untracked: ['.claude/agents/dev-team', '.claude/dev-team-agents/agents', '.claude/user-data'],
    untrack_problem: null,
    unrecognised: [],
    ...overrides,
  };
}

/** What `migrate` answers for a directory with no v2 install: exit 2, and the bind proceeds. */
export function notV2(): Extract<OperationResult<never>, { ok: false }> {
  return fail('/chosen/dir has no vendored v2 install to migrate', { kind: 'usage', exitCode: 2 });
}

export function doctorReport(overrides: Partial<DoctorReport> = {}): DoctorReport {
  return {
    status: 'ok',
    findings: [],
    actions: [],
    ...overrides,
  };
}

/**
 * `prefs list --json` for one project, shaped like the real CLI's answer at 2.48.0, plus the
 * `inherited` cascade the main process adds. Only `language` differs from its inherited value.
 */
export function projectPreferences(overrides: Partial<ProjectPreferencesView> = {}): ProjectPreferencesView {
  const base = {
    project_id: 'proj-1',
    version: '2.48.0',
    values: {
      language: 'en',
      auto_update: false,
      telemetry: false,
      update_check_interval_hours: 24,
      model_max_tokens: 200000,
      context_window_percent_warning: 55,
      context_window_percent_limit: 60,
      session_no_commit_turns: 8,
      session_summary_max_days: 30,
      session_summary_max_entries: 30,
      docs_stale_after_days: 30,
      auto_learn_before_commit: true,
      worktree_active: true,
      worktree_base_branch: null,
      worktree_path: '.worktrees',
      worktree_commit_action: 'ask',
      worktree_docker_isolate: true,
      suppress_notifications: false,
      qa_browser: null,
      ci_cd_detected: null,
    },
    origin: {
      language: 'project',
      auto_update: 'consent-withheld',
      telemetry: 'consent-withheld',
      update_check_interval_hours: 'defaults',
      model_max_tokens: 'global',
      context_window_percent_warning: 'defaults',
      context_window_percent_limit: 'defaults',
      session_no_commit_turns: 'defaults',
      session_summary_max_days: 'defaults',
      session_summary_max_entries: 'defaults',
      docs_stale_after_days: 'defaults',
      auto_learn_before_commit: 'defaults',
      worktree_active: 'project',
      worktree_base_branch: 'defaults',
      worktree_path: 'defaults',
      worktree_commit_action: 'defaults',
      worktree_docker_isolate: 'defaults',
      suppress_notifications: 'defaults',
      qa_browser: 'defaults',
      ci_cd_detected: 'defaults',
    },
    unknown: [],
  };
  return { ...base, inherited: { ...base.values, language: 'pt-BR' }, ...overrides };
}

export function pluginField(overrides: Partial<PluginConfigField> = {}): PluginConfigField {
  return {
    key: 'targetPaths',
    type: 'string_list',
    label: 'Source paths',
    help: 'Directories, relative to the project root, that go into the graph.',
    required: true,
    default: [],
    placeholder: 'src',
    options: [],
    min: null,
    max: null,
    picker: null,
    ...overrides,
  };
}

/** A `PluginView` shaped like ADR-0019 § 3, with the manifest of `plugins/graphify` as the default. */
export function pluginView(overrides: Partial<PluginView> = {}): PluginView {
  return {
    name: 'graphify',
    title: 'Graphify',
    description: 'Builds a knowledge graph of the codebase.',
    homepage: null,
    enabled: false,
    source: 'none',
    settings_file: '.dev-team-agents/plugin-settings/graphify.json',
    requirements: [{ binary: 'graphify', found: true, install_hint: '/devteam:install graphify' }],
    ready: true,
    configured: false,
    config_fields: [
      pluginField(),
      pluginField({ key: 'auto_refresh', type: 'boolean', label: 'Refresh at session end', help: null, required: false, default: false, placeholder: null }),
    ],
    config: { targetPaths: [], auto_refresh: false },
    unknown_config: [],
    actions: [
      { id: 'detect', label: 'Detect paths', help: 'Propose source paths.', output: 'config', requires_enabled: false, writes: false, timeout_seconds: 60 },
      { id: 'rebuild', label: 'Rebuild graph', help: 'Rebuild now.', output: 'log', requires_enabled: true, writes: true, timeout_seconds: 1800 },
    ],
    hooks: ['stop'],
    status: null,
    ...overrides,
  };
}

export function pluginList(
  plugins: readonly PluginView[] = [pluginView()],
  invalid: PluginList['invalid'] = [],
): PluginList {
  return { project_id: 'proj-1', plugins, invalid };
}

export function runResult(overrides: Partial<PluginRunResult> = {}): PluginRunResult {
  return { plugin: 'graphify', action: 'detect', ok: true, exit_code: 0, duration_ms: 420, output: null, log_tail: '', ...overrides };
}

/** A fake bridge with every method stubbed to a benign default; tests override per case. */
export function fakeBridge(overrides: Partial<DevteamBridge> = {}): DevteamBridge {
  return {
    buildInfo: vi.fn(() => Promise.resolve(buildInfo())),
    environment: vi.fn(() => Promise.resolve(environment())),
    resolveCli: vi.fn(() => Promise.resolve(cliResolutionFound())),
    handshake: vi.fn(() => Promise.resolve(ok(handshakeView()))),
    listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
    projectNames: vi.fn(() => Promise.resolve({})),
    projectFolders: vi.fn(() => Promise.resolve({ folders: [], membership: {} })),
    saveProjectFolders: vi.fn((folders) => Promise.resolve({ ok: true as const, folders })),
    catalogSummary: vi.fn(),
    catalogListing: vi.fn(),
    catalogEntry: vi.fn(),
    doctor: vi.fn(() => Promise.resolve(ok(doctorReport()))),
    chooseProjectDirectory: vi.fn(() => Promise.resolve(({ chosen: false }) as const)),
    bindProject: vi.fn(() => Promise.resolve(ok(bindReport()))),
    unbindProject: vi.fn(() => Promise.resolve(ok(unbindReport()))),
    syncProject: vi.fn(() => Promise.resolve(ok(bindReport()))),
    syncAllProjects: vi.fn(() => Promise.resolve(ok({ synced: [], problems: [] }))),
    setPin: vi.fn(() => Promise.resolve(ok({ project_id: 'proj-1', path: '/repo/project-1', pin: null }))),
    planUpgrade: vi.fn(() => Promise.resolve(ok(upgradePlan()))),
    applyUpgrade: vi.fn(() => Promise.resolve(ok(upgradeReport()))),
    planMigration: vi.fn(() => Promise.resolve(notV2())),
    applyMigration: vi.fn(() => Promise.resolve(ok(migrationReport()))),
    projectPreferences: vi.fn(() => Promise.resolve(ok(projectPreferences()))),
    updateProjectPreferences: vi.fn((_projectId: string, changes: readonly PreferenceChange[]) =>
      Promise.resolve(ok({ applied: [...changes], failed: null })),
    ),
    credentialsLocalShow: vi.fn(() => Promise.resolve(ok(credentialsView()))),
    credentialsLocalInit: vi.fn(() => Promise.resolve(ok(credentialsView()))),
    credentialsLocalPatch: vi.fn(() => Promise.resolve(ok(credentialsView()))),
    projectPlugins: vi.fn(() => Promise.resolve(ok(pluginList()))),
    setPluginEnabled: vi.fn((_projectId: string, name: string, enabled: boolean) =>
      Promise.resolve(ok({ plugin: pluginView({ name, enabled }), changed: true, seeded: false })),
    ),
    updatePluginConfig: vi.fn((_projectId: string, _name: string, changes: readonly PluginConfigChange[]) =>
      Promise.resolve(ok({ applied: [...changes], failed: null })),
    ),
    integrationList: vi.fn(() => Promise.resolve(ok({ project_id: null, integrations: [] }))),
    integrationConnect: vi.fn(() => Promise.reject(new Error('integrationConnect is not stubbed'))),
    integrationTest: vi.fn(() => Promise.reject(new Error('integrationTest is not stubbed'))),
    integrationDisconnect: vi.fn(() => Promise.reject(new Error('integrationDisconnect is not stubbed'))),
    integrationConfigSet: vi.fn(() => Promise.reject(new Error('integrationConfigSet is not stubbed'))),
    integrationConfigUnset: vi.fn(() => Promise.reject(new Error('integrationConfigUnset is not stubbed'))),
    integrationResources: vi.fn(() => Promise.resolve(ok({ items: [], truncated: false }))),
    runPluginAction: vi.fn(() => Promise.resolve(ok(runResult()))),
    pickProjectPath: vi.fn(() => Promise.resolve({ picked: false as const })),
    notificationFeed: vi.fn(() => Promise.resolve(notificationFeed())),
    markNotificationsRead: vi.fn(() => Promise.resolve(notificationFeed())),
    setNotificationsPaused: vi.fn((paused: boolean) => Promise.resolve(notificationFeed({ paused }))),
    onNotificationFeed: vi.fn(() => () => undefined),
    onOpenProject: vi.fn(() => () => undefined),
    takePendingProject: vi.fn(() => Promise.resolve(null)),
    backgroundSettings: vi.fn(() => Promise.resolve(backgroundSettings())),
    setOpenAtLogin: vi.fn((enabled: boolean) => Promise.resolve(backgroundSettings({ openAtLogin: enabled }))),
    listSkills: vi.fn(() => Promise.resolve(ok({ provider: 'all', roots: [], skills: [] }))),
    showSkill: vi.fn(),
    installSkill: vi.fn(() => Promise.resolve({ picked: false } as const)),
    removeSkill: vi.fn(),
    taskBoard: vi.fn(() => Promise.resolve(boardFeed())),
    refreshTaskBoard: vi.fn(() => Promise.resolve(boardFeed())),
    onTaskBoard: vi.fn(() => () => undefined),
    boardSettings: vi.fn(() => Promise.resolve(boardSettings())),
    setBoardSettings: vi.fn((settings: BoardSettings) => Promise.resolve({ ok: true, settings } as const)),
    openTaskLink: vi.fn(() => Promise.resolve({ ok: true } as const)),
    ...overrides,
  };
}

export function boardFeed(overrides: Partial<BoardFeed> = {}): BoardFeed {
  return { status: 'live', detail: null, projects: [], ...overrides };
}

export function boardSettings(overrides: Partial<BoardSettings> = {}): BoardSettings {
  return { staleAfterMinutes: 60, doneRetentionDays: 7, directTodoTtlHours: 24, ...overrides };
}

export function notificationFeed(overrides: Partial<NotificationFeed> = {}): NotificationFeed {
  return { status: 'live', detail: null, items: [], unread: 0, paused: false, ...overrides };
}

export function appNotification(overrides: Partial<AppNotification> = {}): AppNotification {
  return {
    id: '1790000000-123-456',
    level: 'warning',
    code: 'context.warning',
    message: 'Context window approaching its limit (≈57%).',
    ts: Math.floor(Date.now() / 1000) - 30,
    projectId: 'proj-1',
    sessionId: 's1',
    expiresAt: 0,
    seen: false,
    projectName: 'Storefront',
    ...overrides,
  };
}

export function backgroundSettings(overrides: Partial<BackgroundSettings> = {}): BackgroundSettings {
  return { openAtLogin: false, loginItemStatus: 'disabled', detail: null, ...overrides };
}

/** Installs a fake bridge on `window.devteam`. `window.devteam` is `readonly` by its own
 * type contract (see `src/renderer/global.d.ts`) — enforced against the real preload, not
 * against a test replacing it, so this goes through `Object.defineProperty` rather than a
 * plain assignment. */
export function installBridge(bridge: DevteamBridge): void {
  Object.defineProperty(window, 'devteam', { value: bridge, configurable: true, writable: true });
}

/** A promise a test settles by hand, for asserting on what a screen does *while* a call is in flight. */
export function deferred<T>(): {
  readonly promise: Promise<T>;
  readonly resolve: (value: T) => void;
  readonly reject: (reason: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

export function credentialsView(overrides: Partial<CredentialsLocalView> = {}): CredentialsLocalView {
  return {
    path: '/repo/project-1/.dev-team-agents/credentials.local.json',
    exists: true,
    valid: true,
    error: null,
    hash: 'hash-1',
    data: {
      work_feedback_active: true,
      work_feedback_interval_minutes: 5,
      example: {
        staging: {
          url: 'https://staging.test',
          username: 'bot',
          password: { secret: true, set: false, marked: true },
          $secrets: ['password'],
        },
        production: {
          $production: true,
          url: 'https://prod.test',
          password: { secret: true, set: true, marked: true },
          token: { secret: true, set: true, marked: false },
          $secrets: ['password'],
          db: { host: 'db.prod.test' },
        },
      },
    },
    ...overrides,
  };
}
