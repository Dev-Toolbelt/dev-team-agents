/**
 * The IPC channels for the task board.
 *
 * Like `notificationIpc.ts`, none of these runs a CLI command on the renderer's say-so:
 * the snapshot is the supervisor's in-memory state, and the settings are this app's own file. Every argument
 * from the renderer is re-checked here — a type is a compile-time claim, and this is a
 * process boundary.
 */

import { ipcMain } from 'electron';

import {
  CHANNELS,
  type BoardFeed,
  type BoardSettings,
  type BoardSettingsAnswer,
  type OpenTaskLinkAnswer,
  type OpenTaskLinkRequest,
} from '../shared/api.js';
import { boardSettingsProblem } from './settings.js';
import { createLinkRateLimiter, trustedHandler, validateTrackerLink, type RendererTarget } from './security.js';
import type { ResolvedTaskLink } from './taskBoard.js';

export interface TaskBoardIpcDeps {
  /** Who may call these channels; see `trustedHandler` in `security.ts`. */
  readonly trustedRenderer: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>;
  readonly feed: () => BoardFeed;
  readonly refresh: () => Promise<BoardFeed>;
  readonly boardSettings: () => Promise<BoardSettings>;
  /** Persist, then apply (the stream restarts when the stale threshold changed). */
  readonly saveBoardSettings: (settings: BoardSettings) => Promise<BoardSettings>;
  /** Look a link up in the board's own latest snapshot. */
  readonly linkFor: (request: OpenTaskLinkRequest) => ResolvedTaskLink | null;
  /** `shell.openExternal(url, { activate: true })`. */
  readonly openExternal: (url: string) => Promise<void>;
  /** Whether the focused window is one of this app's own. */
  readonly appWindowFocused: () => boolean;
  readonly now?: () => number;
  /** Never receives a full URL: host and kind only. */
  readonly log?: (message: string) => void;
}

const idOk = (value: unknown): value is string =>
  typeof value === 'string' && value.length >= 1 && value.length <= 512 && ![...value].some((ch) => ch.charCodeAt(0) < 0x20 || ch.charCodeAt(0) === 0x7f);
const LINK_REQUEST_KEYS = ['project_id', 'session_id', 'task_key', 'link'];

/** A request that is exactly the documented shape, or `null`. A type is a claim; this is the boundary. */
export function parseOpenTaskLink(raw: unknown): OpenTaskLinkRequest | null {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const keys = Object.keys(body);
  if (keys.length !== LINK_REQUEST_KEYS.length || !LINK_REQUEST_KEYS.every((key) => Object.hasOwn(body, key))) return null;
  const projectId = body['project_id'];
  const sessionId = body['session_id'];
  const taskKey = body['task_key'];
  const link = body['link'];
  if (!idOk(projectId)) return null;
  if (!idOk(sessionId)) return null;
  if (taskKey !== null && !idOk(taskKey)) return null;
  if (typeof link !== 'object' || link === null || Array.isArray(link)) return null;
  const linkBody = link as Record<string, unknown>;
  const linkKeys = Object.keys(linkBody);
  if (linkKeys.length !== 3 || !['type', 'index', 'expect'].every((key) => Object.hasOwn(linkBody, key))) return null;
  const type = linkBody['type'];
  const index = linkBody['index'];
  const expect = linkBody['expect'];
  if (type !== 'pr' && type !== 'ref') return null;
  if (typeof index !== 'number' || !Number.isSafeInteger(index) || index < 0 || index > 63) return null;
  if (!idOk(expect) || expect.length > 128) return null;
  return { project_id: projectId, session_id: sessionId, task_key: taskKey, link: { type, index, expect } };
}

export function registerTaskBoardIpc(deps: TaskBoardIpcDeps): void {
  const handle = (channel: string, listener: Parameters<typeof trustedHandler>[1]): void =>
    ipcMain.handle(channel, trustedHandler(deps.trustedRenderer, listener));
  handle(CHANNELS.taskBoard, () => deps.feed());
  handle(CHANNELS.refreshTaskBoard, () => deps.refresh());

  const mayOpen = createLinkRateLimiter(deps.now ?? Date.now);
  const refused = (why: string): OpenTaskLinkAnswer => {
    deps.log?.(`task link refused: ${why}`);
    return { ok: false, message: 'That link could not be opened.' };
  };
  handle(CHANNELS.openTaskLink, async (_event, raw: unknown): Promise<OpenTaskLinkAnswer> => {
    const request = parseOpenTaskLink(raw);
    if (request === null) return refused('malformed request');
    if (!deps.appWindowFocused()) return refused('app window not focused');
    const link = deps.linkFor(request);
    if (link === null) return refused('no such link in the snapshot');
    const verdict = validateTrackerLink(link);
    if (!verdict.ok) return refused(`${link.kind}: ${verdict.reason}`);
    if (!mayOpen()) {
      deps.log?.('task link refused: rate limited');
      return { ok: false, message: 'Links are opening too fast. Wait a moment and try again.' };
    }
    try {
      await deps.openExternal(verdict.canonical);
      deps.log?.(`task link opened: ${link.kind} on ${verdict.host}`);
      return { ok: true };
    } catch {
      return refused('the system could not open it');
    }
  });

  handle(CHANNELS.boardSettings, () => deps.boardSettings());
  handle(CHANNELS.setBoardSettings, async (_event, raw: unknown): Promise<BoardSettingsAnswer> => {
    const problem = boardSettingsProblem(raw);
    if (problem !== null) return { ok: false, message: problem };
    const { staleAfterMinutes, doneRetentionDays, directTodoTtlHours } = raw as BoardSettings;
    try {
      return { ok: true, settings: await deps.saveBoardSettings({ staleAfterMinutes, doneRetentionDays, directTodoTtlHours }) };
    } catch (error) {
      return { ok: false, message: `The settings could not be saved: ${String(error)}` };
    }
  });
}
