/**
 * The IPC channels for the canvas.
 *
 * `taskGraph` runs one named, read-only command (`tasks graph --project <id>`); the renderer
 * names a project id and nothing else, and the id is re-checked here — a type is a
 * compile-time claim, and this is a process boundary. Subscriptions are counted per renderer,
 * so a window that closes without unsubscribing does not keep a poll alive.
 */

import { ipcMain } from 'electron';

import { CHANNELS, type ProjectId, type TaskGraphResult } from '../shared/api.js';
import { trustedHandler, type RendererTarget } from './security.js';

export interface TaskGraphIpcDeps {
  readonly trustedRenderer: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>;
  readonly get: (projectId: ProjectId) => Promise<TaskGraphResult>;
  readonly subscribe: (projectId: ProjectId) => void;
  readonly unsubscribe: (projectId: ProjectId) => void;
}

/** The part of `did-start-navigation`'s details that says whether the page is replaced. */
export interface NavigationDetails {
  readonly isMainFrame: boolean;
  readonly isSameDocument: boolean;
}

/** What `event.sender` must offer to be tracked. */
export interface Sender {
  readonly id: number;
  once(event: 'destroyed', listener: () => void): unknown;
  on?(event: 'render-process-gone', listener: () => void): unknown;
  on?(event: 'did-start-navigation', listener: (details: NavigationDetails) => void): unknown;
}

const MAX_SUBSCRIPTIONS_PER_SENDER = 64;

/** A project id as the registry writes them: bounded, printable, and never read as a flag. */
export function graphProjectId(raw: unknown): ProjectId | null {
  if (typeof raw !== 'string' || raw.length < 1 || raw.length > 128 || raw.startsWith('-')) return null;
  return /^[A-Za-z0-9._:-]+$/.test(raw) ? raw : null;
}

/**
 * Per-renderer subscription counts, released whole when the renderer goes away: destroyed,
 * crashed, or navigated to a new document (a reload leaves no page to unsubscribe).
 */
export class GraphSubscriptions {
  private readonly bySender = new Map<number, Map<ProjectId, number>>();
  /** Senders whose lifecycle events are already listened to, so a re-subscribe adds no listener. */
  private readonly watched = new Set<number>();

  constructor(private readonly deps: Pick<TaskGraphIpcDeps, 'subscribe' | 'unsubscribe'>) {}

  add(sender: Sender, projectId: ProjectId): boolean {
    let counts = this.bySender.get(sender.id);
    if (counts === undefined) {
      counts = new Map();
      this.bySender.set(sender.id, counts);
      this.watch(sender);
    }
    const count = counts.get(projectId) ?? 0;
    if (count === 0 && counts.size >= MAX_SUBSCRIPTIONS_PER_SENDER) return false;
    counts.set(projectId, count + 1);
    this.deps.subscribe(projectId);
    return true;
  }

  remove(senderId: number, projectId: ProjectId): void {
    const counts = this.bySender.get(senderId);
    const count = counts?.get(projectId) ?? 0;
    if (counts === undefined || count === 0) return;
    if (count === 1) counts.delete(projectId);
    else counts.set(projectId, count - 1);
    this.deps.unsubscribe(projectId);
  }

  private watch(sender: Sender): void {
    if (this.watched.has(sender.id)) return;
    this.watched.add(sender.id);
    sender.once('destroyed', () => {
      this.watched.delete(sender.id);
      this.release(sender.id);
    });
    sender.on?.('render-process-gone', () => this.release(sender.id));
    sender.on?.('did-start-navigation', (details: NavigationDetails) => {
      if (details.isMainFrame && !details.isSameDocument) this.release(sender.id);
    });
  }

  release(senderId: number): void {
    const counts = this.bySender.get(senderId);
    if (counts === undefined) return;
    this.bySender.delete(senderId);
    for (const [projectId, count] of counts) for (let i = 0; i < count; i += 1) this.deps.unsubscribe(projectId);
  }
}

const REFUSED: TaskGraphResult = { ok: false, reason: 'error', detail: 'That project id is not valid.' };

export function registerTaskGraphIpc(deps: TaskGraphIpcDeps): GraphSubscriptions {
  const subscriptions = new GraphSubscriptions(deps);
  const handle = (channel: string, listener: Parameters<typeof trustedHandler>[1]): void =>
    ipcMain.handle(channel, trustedHandler(deps.trustedRenderer, listener));

  handle(CHANNELS.taskGraph, (_event, raw: unknown): Promise<TaskGraphResult> => {
    const projectId = graphProjectId(raw);
    return projectId === null ? Promise.resolve(REFUSED) : deps.get(projectId);
  });
  handle(CHANNELS.taskGraphSubscribe, (event: { readonly sender: Sender }, raw: unknown): boolean => {
    const projectId = graphProjectId(raw);
    return projectId !== null && subscriptions.add(event.sender, projectId);
  });
  handle(CHANNELS.taskGraphUnsubscribe, (event: { readonly sender: Sender }, raw: unknown): void => {
    const projectId = graphProjectId(raw);
    if (projectId !== null) subscriptions.remove(event.sender.id, projectId);
  });
  return subscriptions;
}
