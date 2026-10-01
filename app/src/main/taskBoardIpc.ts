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
} from '../shared/api.js';
import { boardSettingsProblem } from './settings.js';
import { trustedHandler, type RendererTarget } from './security.js';

export interface TaskBoardIpcDeps {
  /** Who may call these channels; see `trustedHandler` in `security.ts`. */
  readonly trustedRenderer: Pick<RendererTarget, 'indexUrl' | 'devServerOrigin'>;
  readonly feed: () => BoardFeed;
  readonly refresh: () => Promise<BoardFeed>;
  readonly boardSettings: () => Promise<BoardSettings>;
  /** Persist, then apply (the stream restarts when the stale threshold changed). */
  readonly saveBoardSettings: (settings: BoardSettings) => Promise<BoardSettings>;
}

export function registerTaskBoardIpc(deps: TaskBoardIpcDeps): void {
  const handle = (channel: string, listener: Parameters<typeof trustedHandler>[1]): void =>
    ipcMain.handle(channel, trustedHandler(deps.trustedRenderer, listener));
  handle(CHANNELS.taskBoard, () => deps.feed());
  handle(CHANNELS.refreshTaskBoard, () => deps.refresh());

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
