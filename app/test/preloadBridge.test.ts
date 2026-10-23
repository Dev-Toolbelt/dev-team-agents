/**
 * The REAL preload bridge against a fake `ipcRenderer`: what it sends is what main's validator sees.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { credentialsOpsProblem } from '../src/cli/operations.js';
import { boardSettingsProblem } from '../src/main/settings.js';
import { CHANNELS, type DevteamBridge } from '../src/shared/api.js';

const invoke = vi.fn(() => Promise.resolve(undefined));
let exposed: DevteamBridge | null = null;

vi.mock('electron', () => ({
  ipcRenderer: { invoke: (...args: unknown[]) => (invoke as (...a: unknown[]) => unknown)(...args), on: vi.fn(), removeListener: vi.fn() },
  contextBridge: {
    exposeInMainWorld: (_name: string, api: unknown) => {
      exposed = api as DevteamBridge;
    },
  },
}));

beforeEach(async () => {
  invoke.mockClear();
  await import('../src/preload/index.js');
});

describe('preload bridge — setBoardSettings', () => {
  it('sends all three board settings, and main accepts the payload', async () => {
    await exposed!.setBoardSettings({ staleAfterMinutes: 30, doneRetentionDays: 14, directTodoTtlHours: 48 });
    const call = (invoke.mock.calls as unknown[][]).find((args) => args[0] === CHANNELS.setBoardSettings)!;
    const payload = call[1];
    expect(payload).toEqual({ staleAfterMinutes: 30, doneRetentionDays: 14, directTodoTtlHours: 48 });
    expect(boardSettingsProblem(payload)).toBeNull();
  });
});

describe('preload bridge — credentialsLocalPatch', () => {
  it('keeps `from` on a move, and main accepts the payload', async () => {
    const hash = 'a'.repeat(64);
    await exposed!.credentialsLocalPatch('p1' as never, hash, [
      { op: 'move', from: '/example', pointer: '/api' },
      { op: 'set', pointer: '/api/url', value: 'https://staging.test' },
      { op: 'unset', pointer: '/api/username' },
    ]);
    const call = (invoke.mock.calls as unknown[][]).find((args) => args[0] === CHANNELS.credentialsLocalPatch)!;
    const ops = call[3];
    expect(ops).toEqual([
      { op: 'move', from: '/example', pointer: '/api' },
      { op: 'set', pointer: '/api/url', value: 'https://staging.test' },
      { op: 'unset', pointer: '/api/username' },
    ]);
    expect(credentialsOpsProblem(ops)).toBeNull();
  });
});
