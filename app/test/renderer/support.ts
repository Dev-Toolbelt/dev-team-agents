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
  BuildInfo,
  CliResolution,
  DevteamBridge,
  DoctorReport,
  EnvironmentReport,
  HandshakeView,
  OperationResult,
  PreferenceChange,
  ProjectPreferencesView,
  ProblemKind,
  ProjectRecord,
  UnbindReport,
  UpgradePlan,
  UpgradeReport,
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
  extra: { kind?: ProblemKind; hint?: string; exitCode?: number | null } = {},
): Extract<OperationResult<never>, { ok: false }> {
  return {
    ok: false,
    kind: extra.kind ?? 'environment',
    message,
    exitCode: extra.exitCode ?? 1,
    command: 'devteam test',
    durationMs: 1,
    ...(extra.hint !== undefined ? { hint: extra.hint } : {}),
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
      transcript_multiplier: 1.8,
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
      transcript_multiplier: 'defaults',
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

/** A fake bridge with every method stubbed to a benign default; tests override per case. */
export function fakeBridge(overrides: Partial<DevteamBridge> = {}): DevteamBridge {
  return {
    buildInfo: vi.fn(() => Promise.resolve(buildInfo())),
    environment: vi.fn(() => Promise.resolve(environment())),
    resolveCli: vi.fn(() => Promise.resolve(cliResolutionFound())),
    handshake: vi.fn(() => Promise.resolve(ok(handshakeView()))),
    listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects: [] }))),
    projectNames: vi.fn(() => Promise.resolve({})),
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
    projectPreferences: vi.fn(() => Promise.resolve(ok(projectPreferences()))),
    updateProjectPreferences: vi.fn((_projectId: string, changes: readonly PreferenceChange[]) =>
      Promise.resolve(ok({ applied: [...changes], failed: null })),
    ),
    ...overrides,
  };
}

/** Installs a fake bridge on `window.devteam`. `window.devteam` is `readonly` by its own
 * type contract (see `src/renderer/global.d.ts`) — enforced against the real preload, not
 * against a test replacing it, so this goes through `Object.defineProperty` rather than a
 * plain assignment. */
export function installBridge(bridge: DevteamBridge): void {
  Object.defineProperty(window, 'devteam', { value: bridge, configurable: true, writable: true });
}
