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
  type BoardFeed,
  type BoardSettings,
  type CopyResumeRequest,
  type CatalogKind,
  type DevteamBridge,
  type PluginConfigChange,
  type NotificationFeed,
  type PreferenceChange,
  type ProjectId,
  type SkillInstallRequest,
  type SkillProviderFilter,
  type SkillRemoveRequest,
} from '../shared/api.js';

const bridge: DevteamBridge = {
  buildInfo: () => ipcRenderer.invoke(CHANNELS.buildInfo),
  environment: () => ipcRenderer.invoke(CHANNELS.environment),
  resolveCli: () => ipcRenderer.invoke(CHANNELS.resolveCli),
  handshake: () => ipcRenderer.invoke(CHANNELS.handshake),
  listProjects: () => ipcRenderer.invoke(CHANNELS.listProjects),
  projectNames: () => ipcRenderer.invoke(CHANNELS.projectNames),
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
  copyResumeCommand: (request: CopyResumeRequest) =>
    ipcRenderer.invoke(CHANNELS.copyResumeCommand, {
      projectId: String(request.projectId),
      sessionId: String(request.sessionId),
    }),
  boardSettings: () => ipcRenderer.invoke(CHANNELS.boardSettings),
  setBoardSettings: (settings: BoardSettings) =>
    ipcRenderer.invoke(CHANNELS.setBoardSettings, {
      staleAfterMinutes: Number(settings.staleAfterMinutes),
      doneRetentionDays: Number(settings.doneRetentionDays),
    }),
};

contextBridge.exposeInMainWorld('devteam', bridge);
