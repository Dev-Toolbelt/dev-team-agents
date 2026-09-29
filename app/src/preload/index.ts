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

import { CHANNELS, type CatalogKind, type DevteamBridge } from '../shared/api.js';

const bridge: DevteamBridge = {
  buildInfo: () => ipcRenderer.invoke(CHANNELS.buildInfo),
  environment: () => ipcRenderer.invoke(CHANNELS.environment),
  resolveCli: () => ipcRenderer.invoke(CHANNELS.resolveCli),
  handshake: () => ipcRenderer.invoke(CHANNELS.handshake),
  listProjects: () => ipcRenderer.invoke(CHANNELS.listProjects),
  catalogSummary: () => ipcRenderer.invoke(CHANNELS.catalogSummary),
  // The argument is coerced to a string here and validated again in the main process.
  // The renderer is not trusted to have sent a member of the union just because the type
  // says it did — a type is a compile-time claim and this is a process boundary.
  catalogListing: (kind: CatalogKind) => ipcRenderer.invoke(CHANNELS.catalogListing, String(kind)),
  catalogEntry: (name: string) => ipcRenderer.invoke(CHANNELS.catalogEntry, String(name)),
  doctor: () => ipcRenderer.invoke(CHANNELS.doctor),
};

contextBridge.exposeInMainWorld('devteam', bridge);
