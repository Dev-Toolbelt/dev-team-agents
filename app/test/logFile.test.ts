/** The packaged-build diagnostic log: bounded, rotating, and never a source of failure. */

import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { LOG_FILE_NAME, OLD_LOG_FILE_NAME, createFileLog, describeError } from '../src/main/logFile.js';

let dir: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'devteam-app-log-'));
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

describe('createFileLog', () => {
  it('appends timestamped single-line records, creating the directory', async () => {
    const nested = join(dir, 'a', 'logs');
    const log = createFileLog(nested);
    log.write('first');
    log.write('two\nlines');
    const lines = (await readFile(join(nested, LOG_FILE_NAME), 'utf8')).trimEnd().split('\n');
    expect(lines).toHaveLength(2);
    expect(lines[0]).toMatch(/^\d{4}-\d\d-\d\dT[\d:.]+Z first$/);
    expect(lines[1]).toMatch(/two \| lines$/);
  });

  it('flattens every line break a CLI message can carry and caps one message', async () => {
    const log = createFileLog(dir);
    log.write('a\rb c d\r\ne');
    log.write('x'.repeat(100_000));
    const lines = (await readFile(join(dir, LOG_FILE_NAME), 'utf8')).trimEnd().split('\n');
    expect(lines).toHaveLength(2);
    expect(lines[0]).toMatch(/a \| b \| c \| d \| e$/);
    expect(lines[1]!.length).toBeLessThan(9 * 1024);
  });

  it('rotates to main.old.log at the size cap and keeps only one old file', async () => {
    const log = createFileLog(dir, 200);
    for (let index = 0; index < 30; index += 1) log.write(`record ${index} ${'x'.repeat(20)}`);
    const current = await readFile(join(dir, LOG_FILE_NAME), 'utf8');
    const old = await readFile(join(dir, OLD_LOG_FILE_NAME), 'utf8');
    expect(current.length).toBeLessThan(400);
    expect(old.length).toBeGreaterThan(0);
    expect(current).toContain('record 29');
  });

  it('never throws when the directory cannot be created', async () => {
    const blocker = join(dir, 'file');
    await writeFile(blocker, 'not a directory', 'utf8');
    const log = createFileLog(join(blocker, 'logs'));
    expect(() => log.write('lost, not thrown')).not.toThrow();
  });
});

describe('describeError', () => {
  it('keeps an Error\'s stack and renders non-errors as text', () => {
    expect(describeError(new Error('boom'))).toContain('boom');
    expect(describeError('plain')).toBe('plain');
    expect(describeError({ a: 1 })).toBe('{"a":1}');
    const cyclic: Record<string, unknown> = {};
    cyclic['self'] = cyclic;
    expect(describeError(cyclic)).toBe('[object Object]');
  });
});
