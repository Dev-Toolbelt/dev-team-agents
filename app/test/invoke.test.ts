/**
 * The invocation layer, against the fake CLI.
 *
 * Every assertion is on the **parsed outcome**, never on log text: a test that matched a
 * message would pass while the classification was wrong, which is the failure that
 * matters here.
 */

import { chmod, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { childEnvironment, invokeDevteam } from '../src/cli/invoke.js';
import { explain, ranAndAnswered } from '../src/cli/contract.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));

function run(
  scenario: string,
  args: readonly string[] = ['version'],
  timeoutMs?: number,
  killGraceMs?: number,
) {
  return invokeDevteam({
    binary: FAKE,
    args,
    env: { FAKE_DEVTEAM_SCENARIO: scenario },
    ...(timeoutMs !== undefined ? { timeoutMs } : {}),
    ...(killGraceMs !== undefined ? { killGraceMs } : {}),
  });
}

describe('exit-code mapping', () => {
  it('maps exit 0 to success and hands back the payload', async () => {
    const result = await run('ok');
    expect(result.outcome).toBe('success');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.exitCode).toBe(0);
    expect(result.document.kind).toBe('payload');
  });

  it('maps exit 1 to findings — a result carrying data, not a failure', async () => {
    const result = await run('findings-payload');
    expect(result.outcome).toBe('findings');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.exitCode).toBe(1);
    // The load-bearing assertion: `ok: false` on exit 1 is still a payload the UI shows.
    expect(result.document.kind).toBe('payload');
    if (result.document.kind !== 'payload') throw new Error('unreachable');
    expect(result.document.ok).toBe(false);
    expect(result.document.body['status']).toBe('fail');
    expect(result.document.body['findings']).toHaveLength(1);
  });

  it('recognises an error document on exit 1 as well, and does not confuse it with a payload', async () => {
    const result = await run('findings-error-document');
    expect(result.outcome).toBe('findings');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.document.kind).toBe('error');
    if (result.document.kind !== 'error') throw new Error('unreachable');
    expect(result.document.error).toContain('not fixed');
    expect(result.document.exitCode).toBe(1);
  });

  it('maps exit 2 to usage', async () => {
    const result = await run('usage');
    expect(result.outcome).toBe('usage');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.document.kind).toBe('error');
    if (result.document.kind !== 'error') throw new Error('unreachable');
    expect(result.document.hint).toBe('Pass a path.');
  });

  it('maps exit 3 to environment', async () => {
    const result = await run('environment');
    expect(result.outcome).toBe('environment');
  });

  it('maps exit 4 to conflict and keeps the machine-readable details', async () => {
    const result = await run('conflict');
    expect(result.outcome).toBe('conflict');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    if (result.document.kind !== 'error') throw new Error('expected an error document');
    expect(result.document.details?.['may_write']).toBe(false);
  });

  it('reports an exit code outside {0,1,2,3,4} rather than guessing', async () => {
    const result = await run('undocumented-exit');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('undocumented-exit-code');
    expect(result.exitCode).toBe(7);
  });

  it('gives every outcome a distinct name', async () => {
    const outcomes = await Promise.all(
      ['ok', 'findings-payload', 'usage', 'environment', 'conflict'].map(async (s) => (await run(s)).outcome),
    );
    expect(new Set(outcomes).size).toBe(5);
  });
});

describe('the one-document rule', () => {
  it('reports empty stdout instead of returning an empty success', async () => {
    const result = await run('empty-stdout');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('empty-stdout');
    // And specifically: it did NOT become a success with no data.
    expect(ranAndAnswered(result)).toBe(false);
  });

  it('reports two documents rather than parsing the first', async () => {
    const result = await run('two-documents');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('multiple-documents');
    expect(result.detail).toContain('2');
  });

  it('ignores JSON on stderr — stdout is the only channel', async () => {
    const result = await run('json-on-stderr-only');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('empty-stdout');
    // Captured for the report, never parsed.
    expect(result.stderr).toContain('wrong_channel');
  });

  it('accepts a warning on stderr beside one document on stdout', async () => {
    const result = await run('warning-on-stderr');
    expect(result.outcome).toBe('success');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.stderr).toContain('a warning that must not reach stdout');
  });

  it('reports non-JSON stdout, such as a traceback', async () => {
    const result = await run('not-json');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('not-json');
  });

  it('reports one document followed by stray text', async () => {
    const result = await run('trailing-output');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('trailing-output');
  });

  it('reports a document that is not an object', async () => {
    const result = await run('not-an-object');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('not-an-object');
  });

  it('reports a document with no `ok` field', async () => {
    const result = await run('missing-ok');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('missing-ok');
  });

  it('reports truncated output rather than a parse crash', async () => {
    const result = await run('truncated');
    expect(result.outcome).toBe('contract-breach');
    if (result.outcome !== 'contract-breach') throw new Error('unreachable');
    expect(result.reason).toBe('not-json');
    expect(result.detail).toContain('middle of a JSON value');
  });
});

describe('the binary itself', () => {
  it('reports a missing binary as unavailable/not-found', async () => {
    const result = await invokeDevteam({ binary: join(tmpdir(), 'definitely-not-here-devteam'), args: ['version'] });
    expect(result.outcome).toBe('unavailable');
    if (result.outcome !== 'unavailable') throw new Error('unreachable');
    expect(result.reason).toBe('not-found');
    expect(explain(result)).toContain('could not be started');
  });

  it('reports a non-executable file as unavailable/not-executable', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'devteam-app-test-'));
    const path = join(dir, 'devteam');
    await writeFile(path, '#!/bin/sh\necho hi\n');
    await chmod(path, 0o600);
    const result = await invokeDevteam({ binary: path, args: ['version'] });
    expect(result.outcome).toBe('unavailable');
    if (result.outcome !== 'unavailable') throw new Error('unreachable');
    expect(result.reason).toBe('not-executable');
    // Removed, not left behind: this file used to leak one directory per run.
    await rm(dir, { recursive: true, force: true });
  });
});

describe('timeout', () => {
  it('kills a hung process, says what timed out, and escalates past an ignored SIGTERM', async () => {
    // A short kill grace, not the production two seconds: the assertion is that the hard
    // kill fires at all, and waiting out a real 2 s window is what made this test fail on a
    // loaded machine while passing on an idle one.
    const result = await run('hang', ['version'], 1_500, 150);
    expect(result.outcome).toBe('timeout');
    if (result.outcome !== 'timeout') throw new Error('unreachable');
    expect(result.timeoutMs).toBe(1_500);
    // The fixture ignores SIGTERM, so the deadline only holds if the hard kill fires.
    expect(result.signal).toBe('SIGKILL');
    expect(result.command.display).toContain('version');
    expect(explain(result)).toContain('1500 ms');
  });
});

describe('argument and environment handling', () => {
  it('appends --json itself so no operation can forget it', async () => {
    const result = await run('ok', ['catalog', 'agents']);
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    if (result.document.kind !== 'payload') throw new Error('expected a payload');
    expect(result.document.body['argv']).toEqual(['catalog', 'agents', '--json']);
  });

  it('puts --client-schemas before the subcommand, where the global flag belongs', async () => {
    const result = await invokeDevteam({
      binary: FAKE,
      args: ['list'],
      env: { FAKE_DEVTEAM_SCENARIO: 'ok' },
      declarationFile: '/tmp/client-schemas.json',
    });
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    if (result.document.kind !== 'payload') throw new Error('expected a payload');
    expect(result.document.body['argv']).toEqual([
      '--client-schemas',
      '/tmp/client-schemas.json',
      'list',
      '--json',
    ]);
  });

  it('passes arguments as an array, so shell metacharacters are inert', async () => {
    // If any shell were involved, `; echo pwned` would run. It arrives as one argv entry.
    const hostile = '; echo pwned #$(whoami) `id` && rm -rf /';
    const result = await run('ok', ['catalog', 'show', hostile]);
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    if (result.document.kind !== 'payload') throw new Error('expected a payload');
    expect(result.document.body['argv']).toEqual(['catalog', 'show', hostile, '--json']);
    // A shell would have run the `echo`, putting its output on stdout beside the document
    // — which would surface as a `trailing-output` breach, not a clean success.
    expect(result.outcome).toBe('success');
    expect(result.stderr).toBe('');
  });

  it('hands the child a minimal environment and lets DEVTEAM_HOME through', () => {
    const env = childEnvironment(
      { PATH: '/usr/bin', HOME: '/home/x', DEVTEAM_HOME: '/tmp/store', AWS_SECRET_ACCESS_KEY: 'nope' },
      { FAKE_DEVTEAM_SCENARIO: 'ok' },
    );
    expect(env['DEVTEAM_HOME']).toBe('/tmp/store');
    expect(env['PATH']).toBe('/usr/bin');
    expect(env['AWS_SECRET_ACCESS_KEY']).toBeUndefined();
    expect(env['FAKE_DEVTEAM_SCENARIO']).toBe('ok');
  });

  it('never builds a shell string from the arguments', async () => {
    const result = await run('ok', ['version']);
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    // `display` exists for messages; the spawned vector is the array.
    expect(result.command.args).toEqual(['version', '--json']);
    expect(result.command.binary).toBe(FAKE);
  });
});
