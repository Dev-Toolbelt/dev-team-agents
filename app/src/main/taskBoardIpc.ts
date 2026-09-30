/**
 * The IPC channels for the task board.
 *
 * Like `notificationIpc.ts`, none of these runs a CLI command on the renderer's say-so:
 * the snapshot is the supervisor's in-memory state, the copy handler puts a string the
 * *CLI* sent on the clipboard, and the settings are this app's own file. Every argument
 * from the renderer is re-checked here — a type is a compile-time claim, and this is a
 * process boundary.
 */

import { ipcMain } from 'electron';

import {
  CHANNELS,
  type BoardFeed,
  type BoardSettings,
  type BoardSettingsAnswer,
  type CopyResumeAnswer,
  type CopyResumeRequest,
} from '../shared/api.js';
import { boardSettingsProblem } from './settings.js';
import { trustedHandler, type RendererTarget } from './security.js';

export interface TaskBoardIpcDeps {
  /** Who may call these channels; see `trustedHandler` in `security.ts`. */
  readonly trustedRenderer: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>;
  readonly feed: () => BoardFeed;
  readonly refresh: () => Promise<BoardFeed>;
  /** The resume command the CLI sent for a session, or `null` when there is none. */
  readonly resumeCommand: (projectId: string, sessionId: string) => string | null;
  readonly copyText: (text: string) => void;
  readonly boardSettings: () => Promise<BoardSettings>;
  /** Persist, then apply (the stream restarts when the stale threshold changed). */
  readonly saveBoardSettings: (settings: BoardSettings) => Promise<BoardSettings>;
}

const MAX_ID = 512;
// eslint-disable-next-line no-control-regex
const CONTROL = /[\u0000-\u001f\u007f]/;

/** The renderer's copy request, rebuilt from `unknown`; a sentence when it is not one. */
export function parseCopyRequest(raw: unknown): CopyResumeRequest | string {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return 'the request is not an object';
  const { projectId, sessionId } = raw as { projectId?: unknown; sessionId?: unknown };
  for (const [name, value] of [['projectId', projectId], ['sessionId', sessionId]] as const) {
    if (typeof value !== 'string' || value === '' || value.length > MAX_ID || CONTROL.test(value)) {
      return `\`${name}\` is not a well-formed id`;
    }
  }
  return { projectId: projectId as string, sessionId: sessionId as string };
}

export function registerTaskBoardIpc(deps: TaskBoardIpcDeps): void {
  const handle = (channel: string, listener: Parameters<typeof trustedHandler>[1]): void =>
    ipcMain.handle(channel, trustedHandler(deps.trustedRenderer, listener));
  handle(CHANNELS.taskBoard, () => deps.feed());
  handle(CHANNELS.refreshTaskBoard, () => deps.refresh());

  handle(CHANNELS.copyResumeCommand, (_event, raw: unknown): CopyResumeAnswer => {
    const request = parseCopyRequest(raw);
    if (typeof request === 'string') return { copied: false, message: `Nothing was copied: ${request}.` };
    const command = deps.resumeCommand(request.projectId, request.sessionId);
    if (command === null) {
      return { copied: false, message: 'This session has no resume command the app could verify, so nothing was copied.' };
    }
    deps.copyText(command);
    return { copied: true, command };
  });

  handle(CHANNELS.boardSettings, () => deps.boardSettings());
  handle(CHANNELS.setBoardSettings, async (_event, raw: unknown): Promise<BoardSettingsAnswer> => {
    const problem = boardSettingsProblem(raw);
    if (problem !== null) return { ok: false, message: problem };
    const { staleAfterMinutes, doneRetentionDays } = raw as BoardSettings;
    try {
      return { ok: true, settings: await deps.saveBoardSettings({ staleAfterMinutes, doneRetentionDays }) };
    } catch (error) {
      return { ok: false, message: `The settings could not be saved: ${String(error)}` };
    }
  });
}
