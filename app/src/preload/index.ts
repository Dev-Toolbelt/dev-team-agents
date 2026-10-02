/**
 * The contextBridge. Compiled to CommonJS, which is not optional: a sandboxed preload is
 * loaded as CommonJS, and `sandbox: true` is not negotiable. `tsconfig.node.json` emits
 * CommonJS for the whole node side for that reason.
 *
 * **Named operations only.** There is no `invoke(channel, ...args)` and no
 * `run(command)`. A generic bridge would hand the renderer the ability to ask the main
 * process for an arbitrary command, which is precisely the capability the rest of the
 * security posture exists to remove — `sandbox: true` would then be decoration. Each
 * function below maps to one channel with one shape, and adding a capability means
 * editing this file, which is the review point.
 *
 * Nothing else is exposed: no `require`, no `process`, no paths, no filesystem.
 */

import { contextBridge, ipcRenderer } from 'electron';

import {
  CHANNELS,
  type BindRequest,
  type ProjectFolders,
  type BoardFeed,
  type BoardSettings,
  type OpenTaskLinkRequest,
  type CatalogKind,
  type CredentialsPatchOp,
  type MigrateRequest,
  type DevteamBridge,
  type PluginConfigChange,
  type PluginFieldPicker,
  type NotificationFeed,
  type PreferenceChange,
  type ProjectId,
  type SkillInstallRequest,
  type SkillProviderFilter,
  type SkillRemoveRequest,
} from '../shared/api.js';

function migrateRequest(request: MigrateRequest): Record<string, unknown> {
  return {
    path: String(request.path),
    ...(request.providers !== undefined ? { providers: [...request.providers] } : {}),
    ...(request.mode !== undefined ? { mode: request.mode } : {}),
    ...(request.name !== undefined ? { name: String(request.name) } : {}),
  };
}

const bridge: DevteamBridge = {
  buildInfo: () => ipcRenderer.invoke(CHANNELS.buildInfo),
  environment: () => ipcRenderer.invoke(CHANNELS.environment),
  resolveCli: () => ipcRenderer.invoke(CHANNELS.resolveCli),
  handshake: () => ipcRenderer.invoke(CHANNELS.handshake),
  listProjects: () => ipcRenderer.invoke(CHANNELS.listProjects),
  projectNames: () => ipcRenderer.invoke(CHANNELS.projectNames),
  projectFolders: () => ipcRenderer.invoke(CHANNELS.projectFolders),
  // Rebuilt into plain JSON rather than passed through; the main process validates it again.
  saveProjectFolders: (folders: ProjectFolders) =>
    ipcRenderer.invoke(CHANNELS.saveProjectFolders, JSON.parse(JSON.stringify(folders)) as unknown),
  catalogSummary: () => ipcRenderer.invoke(CHANNELS.catalogSummary),
  // The argument is coerced to a string here and validated again in the main process.
  // The renderer is not trusted to have sent a member of the union just because the type
  // says it did — a type is a compile-time claim and this is a process boundary.
  catalogListing: (kind: CatalogKind) => ipcRenderer.invoke(CHANNELS.catalogListing, String(kind)),
  catalogEntry: (name: string) => ipcRenderer.invoke(CHANNELS.catalogEntry, String(name)),
  doctor: () => ipcRenderer.invoke(CHANNELS.doctor),

  // Write actions. Every argument is rebuilt into a plain, minimal object here rather
  // than passed through — the main process validates it again regardless (see
  // `main/ipc.ts` -> `validateBindRequest`), but this is the same boundary discipline as
  // `catalogListing` above: nothing the renderer handed this function crosses the bridge
  // unexamined, including a `BindRequest` it built itself.
  chooseProjectDirectory: () => ipcRenderer.invoke(CHANNELS.chooseProjectDirectory),
  bindProject: (request: BindRequest) =>
    ipcRenderer.invoke(CHANNELS.bindProject, {
      path: String(request.path),
      ...(request.providers !== undefined ? { providers: [...request.providers] } : {}),
      ...(request.mode !== undefined ? { mode: request.mode } : {}),
      ...(request.pin !== undefined ? { pin: request.pin } : {}),
      ...(request.name !== undefined ? { name: String(request.name) } : {}),
    }),
  unbindProject: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.unbindProject, String(projectId)),
  syncProject: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.syncProject, String(projectId)),
  syncAllProjects: () => ipcRenderer.invoke(CHANNELS.syncAllProjects),
  // `version: null` is a release, and must reach the main process as `null` — never
  // coerced to the string `"null"` or to `""`, either of which `setPin` in
  // `cli/operations.ts` would build into an argv `pin --release` does not mean.
  setPin: (projectId: ProjectId, version: string | null) =>
    ipcRenderer.invoke(CHANNELS.setPin, String(projectId), version === null ? null : String(version)),
  planUpgrade: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.planUpgrade, String(projectId)),
  applyUpgrade: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.applyUpgrade, String(projectId)),
  // Rebuilt like `bindProject`'s request, and validated by the same `validateBindRequest`.
  planMigration: (request: MigrateRequest) => ipcRenderer.invoke(CHANNELS.planMigration, migrateRequest(request)),
  applyMigration: (request: MigrateRequest) => ipcRenderer.invoke(CHANNELS.applyMigration, migrateRequest(request)),
  projectPreferences: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.projectPreferences, String(projectId)),
  // Rebuilt into plain objects, like `bindProject`'s request; `main/ipc.ts` validates each
  // change again against the project's own `prefs list` answer.
  updateProjectPreferences: (projectId: ProjectId, changes: readonly PreferenceChange[]) =>
    ipcRenderer.invoke(
      CHANNELS.updateProjectPreferences,
      String(projectId),
      changes.map((change) =>
        change.action === 'unset'
          ? { key: String(change.key), action: 'unset' }
          : { key: String(change.key), action: 'set', value: change.value },
      ),
    ),

  // Plugins (ADR-0019). Names and ids are coerced to strings and the change list is rebuilt
  // into plain objects, as above; `main/ipc.ts` validates each against the project's own
  // `plugin list` answer regardless.
  projectPlugins: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.projectPlugins, String(projectId)),
  setPluginEnabled: (projectId: ProjectId, name: string, enabled: boolean) =>
    ipcRenderer.invoke(CHANNELS.setPluginEnabled, String(projectId), String(name), enabled === true),
  updatePluginConfig: (projectId: ProjectId, name: string, changes: readonly PluginConfigChange[]) =>
    ipcRenderer.invoke(
      CHANNELS.updatePluginConfig,
      String(projectId),
      String(name),
      changes.map((change) =>
        change.action === 'unset'
          ? { key: String(change.key), action: 'unset' }
          : {
              key: String(change.key),
              action: 'set',
              value: Array.isArray(change.value) ? [...(change.value as readonly string[])] : change.value,
            },
      ),
    ),
  runPluginAction: (projectId: ProjectId, name: string, actionId: string) =>
    ipcRenderer.invoke(CHANNELS.runPluginAction, String(projectId), String(name), String(actionId)),
  // Integrations (ADR-0023). Everything is coerced to a string (or boolean / null) here; the token
  // is passed straight through to main, which forwards it over stdin and validates every value.
  integrationList: (projectId: ProjectId | null) =>
    ipcRenderer.invoke(CHANNELS.integrationList, projectId === null ? null : String(projectId)),
  integrationConnect: (
    name: string,
    fields: Readonly<Record<string, string>>,
    token: string | null,
    projectId: ProjectId | null,
  ) =>
    ipcRenderer.invoke(
      CHANNELS.integrationConnect,
      String(name),
      Object.fromEntries(Object.entries(fields).map(([key, value]) => [String(key), String(value)])),
      token === null ? null : String(token),
      projectId === null ? null : String(projectId),
    ),
  integrationTest: (name: string, projectId: ProjectId | null) =>
    ipcRenderer.invoke(CHANNELS.integrationTest, String(name), projectId === null ? null : String(projectId)),
  integrationDisconnect: (name: string, keepToken: boolean) =>
    ipcRenderer.invoke(CHANNELS.integrationDisconnect, String(name), keepToken === true),
  integrationConfigSet: (name: string, key: string, value: string, projectId: ProjectId | null) =>
    ipcRenderer.invoke(
      CHANNELS.integrationConfigSet,
      String(name),
      String(key),
      String(value),
      projectId === null ? null : String(projectId),
    ),
  integrationConfigUnset: (name: string, key: string, projectId: ProjectId | null) =>
    ipcRenderer.invoke(CHANNELS.integrationConfigUnset, String(name), String(key), projectId === null ? null : String(projectId)),
  integrationResources: (name: string, kind: string, projectId: ProjectId | null) =>
    ipcRenderer.invoke(
      CHANNELS.integrationResources,
      String(name),
      String(kind),
      projectId === null ? null : String(projectId),
    ),
  // Local credentials file (ADR-0024). Ops are copied to plain data here; main validates and
  // forwards them over stdin.
  credentialsLocalShow: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.credentialsLocalShow, String(projectId)),
  credentialsLocalInit: (projectId: ProjectId) => ipcRenderer.invoke(CHANNELS.credentialsLocalInit, String(projectId)),
  credentialsLocalPatch: (projectId: ProjectId, expectHash: string, ops: readonly CredentialsPatchOp[]) =>
    ipcRenderer.invoke(
      CHANNELS.credentialsLocalPatch,
      String(projectId),
      String(expectHash),
      ops.map((entry) => ({
        op: entry.op,
        pointer: String(entry.pointer),
        ...('value' in entry ? { value: entry.value } : {}),
      })),
    ),
  pickProjectPath: (projectId: ProjectId, picker: PluginFieldPicker) =>
    ipcRenderer.invoke(CHANNELS.pickProjectPath, String(projectId), String(picker)),
  notificationFeed: () => ipcRenderer.invoke(CHANNELS.notificationFeed),
  markNotificationsRead: () => ipcRenderer.invoke(CHANNELS.markNotificationsRead),
  setNotificationsPaused: (paused: boolean) => ipcRenderer.invoke(CHANNELS.setNotificationsPaused, paused === true),
  // Subscriptions hand the listener the payload only — never Electron's `event`, whose
  // `sender` is a handle into the main process the renderer has no business holding.
  onNotificationFeed: (listener: (feed: NotificationFeed) => void) => {
    const handler = (_event: unknown, feed: NotificationFeed): void => listener(feed);
    ipcRenderer.on(CHANNELS.notificationFeedChanged, handler);
    return () => {
      ipcRenderer.removeListener(CHANNELS.notificationFeedChanged, handler);
    };
  },
  onOpenProject: (listener: (projectId: ProjectId) => void) => {
    const handler = (_event: unknown, projectId: unknown): void => {
      if (typeof projectId === 'string') listener(projectId);
    };
    ipcRenderer.on(CHANNELS.openProject, handler);
    return () => {
      ipcRenderer.removeListener(CHANNELS.openProject, handler);
    };
  },
  takePendingProject: () => ipcRenderer.invoke(CHANNELS.takePendingProject),
  backgroundSettings: () => ipcRenderer.invoke(CHANNELS.backgroundSettings),
  setOpenAtLogin: (enabled: boolean) => ipcRenderer.invoke(CHANNELS.setOpenAtLogin, enabled === true),
  // Global skills. Requests are rebuilt into plain objects; the install request names a
  // *kind* of source, and the picker that yields the path opens in the main process.
  listSkills: (provider: SkillProviderFilter) => ipcRenderer.invoke(CHANNELS.listSkills, String(provider)),
  showSkill: (name: string, root: string) => ipcRenderer.invoke(CHANNELS.showSkill, String(name), String(root)),
  installSkill: (request: SkillInstallRequest) =>
    ipcRenderer.invoke(CHANNELS.installSkill, {
      source: String(request.source),
      providers: [...request.providers].map(String),
      replace: request.replace === true,
      link: request.link === true,
    }),
  removeSkill: (request: SkillRemoveRequest) =>
    ipcRenderer.invoke(CHANNELS.removeSkill, { name: String(request.name), root: String(request.root) }),

  // The task board. Requests are rebuilt into plain objects; the main process validates
  // them again, and copies only text the CLI itself sent.
  taskBoard: () => ipcRenderer.invoke(CHANNELS.taskBoard),
  refreshTaskBoard: () => ipcRenderer.invoke(CHANNELS.refreshTaskBoard),
  onTaskBoard: (listener: (feed: BoardFeed) => void) => {
    const handler = (_event: unknown, feed: BoardFeed): void => listener(feed);
    ipcRenderer.on(CHANNELS.taskBoardChanged, handler);
    return () => {
      ipcRenderer.removeListener(CHANNELS.taskBoardChanged, handler);
    };
  },
  boardSettings: () => ipcRenderer.invoke(CHANNELS.boardSettings),
  setBoardSettings: (settings: BoardSettings) =>
    ipcRenderer.invoke(CHANNELS.setBoardSettings, {
      staleAfterMinutes: Number(settings.staleAfterMinutes),
      doneRetentionDays: Number(settings.doneRetentionDays),
    }),
  openTaskLink: (request: OpenTaskLinkRequest) =>
    ipcRenderer.invoke(CHANNELS.openTaskLink, {
      project_id: String(request.project_id),
      session_id: String(request.session_id),
      task_key: request.task_key === null ? null : String(request.task_key),
      link: { type: request.link.type, index: Number(request.link.index), expect: String(request.link.expect) },
    }),
};

contextBridge.exposeInMainWorld('devteam', bridge);
