/**
 * Which deadline `run()` hands to `invokeDevteam`. `invoke.ts` is replaced by a recorder so
 * the assertion is on the option itself rather than on a wall-clock race.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const invokeDevteam = vi.hoisted(() => vi.fn());

vi.mock('../src/cli/invoke.js', () => ({
  invokeDevteam,
  DEFAULT_TIMEOUT_MS: 20_000,
}));

import {
  GATED_COMMANDS,
  GATED_TIMEOUT_MS,
  INTEGRATION_NETWORK_TIMEOUT_MS,
  integrationConnect,
  integrationResources,
  integrationTest,
  run,
} from '../src/cli/operations.js';

beforeEach(() => {
  invokeDevteam.mockReset();
  invokeDevteam.mockResolvedValue({
    outcome: 'contract-breach',
    reason: 'no-document',
    detail: 'recorded only',
    exitCode: 0,
    stdout: '',
    stderr: '',
    command: { binary: 'x', args: [], display: 'x' },
    durationMs: 0,
  });
});

const CONTEXT = { binary: '/x/devteam', cwd: '/x' };

/** A spelled-out, allow-list-valid argv for each gated command. */
const GATED_ARGV: Readonly<Record<string, readonly string[]>> = {
  doctor: ['doctor', '--no-project'],
  bind: ['bind', '/p'],
  unbind: ['unbind', '--project-id', 'p'],
  sync: ['sync', '--all'],
  pin: ['pin', '--path', '/p', '--release'],
  upgrade: ['upgrade', '/p'],
  migrate: ['migrate', '/p', '--apply', '--untrack'],
  'prefs set': ['prefs', 'set', 'language', 'en', '--scope', 'project', '--path', '/p'],
  'prefs unset': ['prefs', 'unset', 'language', '--scope', 'project', '--path', '/p'],
  'notifications ack': ['notifications', 'ack', '1-2-3'],
  'skills install': ['skills', 'install', '--source', '/s'],
  'skills remove': ['skills', 'remove', 'a', '--root', 'claude'],
  'plugin enable': ['plugin', 'enable', 'demo', '--path', '/p'],
  'plugin disable': ['plugin', 'disable', 'demo', '--path', '/p'],
  'plugin config set': ['plugin', 'config', 'set', 'demo', 'key', 'v', '--path', '/p'],
  'plugin config unset': ['plugin', 'config', 'unset', 'demo', 'key', '--path', '/p'],
  'plugin run': ['plugin', 'run', 'demo', 'detect', '--path', '/p'],
  'integration connect': ['integration', 'connect', 'github', '--field', 'api_url=https://x', '--path', '/p'],
  'integration disconnect': ['integration', 'disconnect', 'github', '--keep-token'],
  'integration test': ['integration', 'test', 'github', '--path', '/p'],
  'integration config set': ['integration', 'config', 'set', 'github', 'repository', 'a/b', '--path', '/p'],
  'integration config unset': ['integration', 'config', 'unset', 'github', 'repository', '--path', '/p'],
  'cred local init': ['cred', 'local', 'init', '--path', '/p'],
  'cred local patch': ['cred', 'local', 'patch', '--path', '/p', '--expect-hash', 'h'],
};

describe('run() deadlines', () => {
  it('gives every gated command the long write deadline', async () => {
    for (const command of GATED_COMMANDS) {
      const argv = GATED_ARGV[command.join(' ')];
      if (argv === undefined) throw new Error(`no argv for gated command ${command.join(' ')}`);
      invokeDevteam.mockClear();
      await run(CONTEXT, argv, (body) => body);
      // Mutation: dropping the gated branch leaves `timeoutMs` unset (20 s) for a write.
      expect(invokeDevteam.mock.calls[0]?.[0].timeoutMs, command.join(' ')).toBe(GATED_TIMEOUT_MS);
    }
    expect(GATED_TIMEOUT_MS).toBeGreaterThan(20_000);
  });

  it('leaves a read-only command on invokeDevteam\'s default', async () => {
    await run(CONTEXT, ['list'], (body) => body);
    expect(invokeDevteam.mock.calls[0]?.[0]).not.toHaveProperty('timeoutMs');
    await run(CONTEXT, ['prefs', 'list', '--path', '/p'], (body) => body);
    expect(invokeDevteam.mock.calls[1]?.[0]).not.toHaveProperty('timeoutMs');
  });

  it('lets the caller\'s own timeoutMs win', async () => {
    await run({ ...CONTEXT, timeoutMs: 1234 }, ['sync', '--all'], (body) => body);
    expect(invokeDevteam.mock.calls[0]?.[0].timeoutMs).toBe(1234);
  });
});

describe('integration network deadlines', () => {
  it('gives connect and test the gated deadline, never the short read one', async () => {
    // Mutation: restoring the 30 s override would kill a write whose side effects already landed.
    await integrationConnect(CONTEXT, null, 'github', {}, null);
    await integrationTest(CONTEXT, null, 'github');
    expect(invokeDevteam.mock.calls.map((call: { timeoutMs?: number }[]) => call[0]?.timeoutMs)).toEqual([GATED_TIMEOUT_MS, GATED_TIMEOUT_MS]);
  });

  it('keeps the short deadline for the read-only resources call', async () => {
    await integrationResources(CONTEXT, null, 'github', 'repos');
    expect(invokeDevteam.mock.calls[0]?.[0].timeoutMs).toBe(INTEGRATION_NETWORK_TIMEOUT_MS);
    expect(INTEGRATION_NETWORK_TIMEOUT_MS).toBeLessThan(GATED_TIMEOUT_MS);
  });
});
