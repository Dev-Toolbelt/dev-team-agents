/**
 * The task board in the main process: the operations that validate what the CLI sends, the
 * supervisor that keeps the snapshots and restarts the stream, the IPC boundary, and the
 * app-local settings.
 */
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from 'vitest';

import { streamDevteam, type StreamEnd } from '../src/cli/stream.js';
import {
  argvProblem,
  asBoardProject,
  asBoardTask,
  asTaskWatchEvent,
  RESUME_COMMAND,
  listTasks,
  watchTasks,
  type TaskWatchEvent,
  TaskStreamRefused,
} from '../src/cli/operations.js';
import {
  BOARD_BACKOFF_MAX_MS,
  BOARD_BACKOFF_MIN_MS,
  BOARD_HEALTHY_MS,
  BOARD_WATCHDOG_MS,
  TaskBoard,
  saveBoardSettings,
  type TaskBoardDeps,
} from '../src/main/taskBoard.js';
import {
  SETTINGS_FILE_NAME,
  boardSettingsProblem,
  readSettings,
  writeBoardSettings,
  writeProjectName,
} from '../src/main/settings.js';
import type * as IpcModule from '../src/main/taskBoardIpc.js';
import type * as ApiModule from '../src/shared/api.js';
import type { BoardFeed, BoardProject } from '../src/shared/api.js';
import { NOW, boardProject, boardSession, boardTask, counts } from './fixtures/board.js';
import { readLauncherManifest, resolveFixtureBinary } from './fixtures/launcher-manifest.js';

const FAKE_WATCH = join(dirname(fileURLToPath(import.meta.url)), 'fixtures', 'fake-watch.mjs');
const FAKE_DEVTEAM = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));
const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const { binary: FAKE_BINARY, available: launcherAvailable } = resolveFixtureBinary(
  FAKE_DEVTEAM,
  readLauncherManifest()?.fakeDevteam,
);
const skipWithoutFake = process.platform === 'win32' && !launcherAvailable;

async function until(check: () => boolean, ms = 5000): Promise<void> {
  const deadline = Date.now() + ms;
  while (!check()) {
    if (Date.now() > deadline) throw new Error('timed out waiting');
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

// ── argv and payload validation ───────────────────────────────────────────────

describe('task board argv', () => {
  it('allows tasks list and tasks watch with --stale-after, and nothing else', () => {
    expect(argvProblem(['tasks', 'list'])).toBeNull();
    expect(argvProblem(['tasks', 'list', '--stale-after', '3600', '--since', '100'])).toBeNull();
    expect(argvProblem(['tasks', 'watch', '--stale-after', '3600'])).toBeNull();
    expect(argvProblem(['tasks', 'watch', '--since', '1'])).toMatch(/may not be passed/);
    expect(argvProblem(['tasks', 'record'])).toMatch(/not a command this app is allowed/);
    expect(argvProblem(['tasks', 'mark', '--state', 'ended'])).toMatch(/not a command this app is allowed/);
  });
});

describe('asBoardProject', () => {
  it('accepts the documented shape', () => {
    const parsed = asBoardProject(JSON.parse(JSON.stringify(boardProject())));
    expect(typeof parsed).toBe('object');
    expect(parsed).toMatchObject({ project_id: 'proj-a', counts: { total: 1 } });
  });

  it.each([
    ['a non-object', 'nope'],
    ['no project_id', { root: '/x', counts: counts(1, 0, 0), sessions_total: 1, sessions_active: 1, sessions: [] }],
    ['non-numeric counts', { ...boardProject(), counts: { todo: 'a', in_progress: 0, done: 0, total: 0 } }],
    ['negative counts', { ...boardProject(), counts: { todo: -1, in_progress: 0, done: 0, total: 0 } }],
    ['no sessions array', { ...boardProject(), sessions: 'x' }],
    ['no session totals', { ...boardProject(), sessions_total: 'x' }],
  ])('rejects %s', (_name, raw) => {
    expect(typeof asBoardProject(raw)).toBe('string');
  });

  it('accepts output without the review fields (an older CLI): in_review 0, with_findings 0, review null', () => {
    const raw = JSON.parse(JSON.stringify(boardProject({ sessions: [boardSession({ tasks: [boardTask()] })] }))) as {
      with_findings?: number;
      counts: { in_review?: number };
      sessions: { counts: { in_review?: number }; tasks: { review?: unknown }[] }[];
    };
    delete raw.with_findings;
    delete raw.counts.in_review;
    delete raw.sessions[0]!.counts.in_review;
    delete raw.sessions[0]!.tasks[0]!.review;
    const parsed = asBoardProject(raw) as BoardProject;
    expect(parsed.counts.in_review).toBe(0);
    expect(parsed.with_findings).toBe(0);
    expect(parsed.sessions[0]?.counts.in_review).toBe(0);
    expect(parsed.sessions[0]?.tasks[0]?.review).toBeNull();
  });

  it.each([['a string', 'x'], ['a negative number', -3], ['null', null], ['an object', {}]])(
    'degrades a malformed optional review field (%s) to 0 instead of rejecting the project',
    (_name, bad) => {
      const raw = JSON.parse(JSON.stringify(boardProject({ sessions: [boardSession({ tasks: [boardTask()] })] }))) as {
        with_findings: unknown;
        counts: { in_review: unknown };
        sessions: { counts: { in_review: unknown } }[];
      };
      raw.with_findings = bad;
      raw.counts.in_review = bad;
      raw.sessions[0]!.counts.in_review = bad;
      const parsed = asBoardProject(raw);
      expect(typeof parsed).toBe('object');
      const project = parsed as BoardProject;
      expect(project.with_findings).toBe(0);
      expect(project.counts.in_review).toBe(0);
      expect(project.sessions[0]?.counts.in_review).toBe(0);
    },
  );

  it('drops a card with an unknown future column, without touching its neighbours or the session counts', () => {
    for (const column of ['archived', 'in_qa', '', 7, null]) {
      const session = boardSession({ tasks: [boardTask({ key: 'ok' }), { ...boardTask({ key: 'new' }), column: column as never }] });
      const parsed = asBoardProject(boardProject({ sessions: [session] })) as BoardProject;
      expect(parsed.sessions[0]?.tasks.map((t) => t.key)).toEqual(['ok']);
    }
  });

  it('reads the review window: column, state, findings, since, and the counts', () => {
    const review = { state: 'findings', findings: 3, since: NOW - 50 } as const;
    const task = boardTask({ key: 'r', column: 'in_review', status: 'in_progress', review });
    const parsed = asBoardProject(boardProject({ sessions: [boardSession({ tasks: [task] })] })) as BoardProject;
    expect(parsed.counts.in_review).toBe(1);
    expect(parsed.with_findings).toBe(1);
    expect(parsed.sessions[0]?.tasks[0]).toMatchObject({ column: 'in_review', review });
  });

  it.each([
    ['an unknown state', { state: 'done', findings: null, since: 1 }],
    ['negative findings', { state: 'findings', findings: -1, since: 1 }],
    ['fractional findings', { state: 'findings', findings: 1.5, since: 1 }],
    ['non-numeric findings', { state: 'findings', findings: '2', since: 1 }],
    ['a missing since', { state: 'pending', findings: null }],
    ['a non-object', 'pending'],
  ])('replaces the malformed review of a task with %s by an unread window, keeping the task', (_name, review) => {
    const task = asBoardTask({ ...boardTask({ column: 'in_review', status: 'in_progress' }), review });
    expect(task).not.toBeNull();
    expect(task?.review).toMatchObject({ state: 'unread', findings: null });
  });

  it.each([
    ['absent', undefined],
    ['null', null],
    ['malformed', { state: 'bogus', since: 'x' }],
  ])('gives a task in review whose review is %s an unread window from status_since', (_name, review) => {
    const raw = { ...boardTask({ column: 'in_review', status: 'in_progress', status_since: 777 }), review };
    if (review === undefined) delete (raw as { review?: unknown }).review;
    expect(asBoardTask(raw)?.review).toEqual({ state: 'unread', findings: null, since: 777 });
  });

  it('leaves a task outside review with no window', () => {
    expect(asBoardTask({ ...boardTask({ column: 'in_progress' }), review: null })?.review).toBeNull();
  });

  it('reads as_of when it is a non-negative number and ignores it otherwise', () => {
    const base = JSON.parse(JSON.stringify(boardProject())) as Record<string, unknown>;
    expect((asBoardProject({ ...base, as_of: 1_790_000_123 }) as BoardProject).as_of).toBe(1_790_000_123);
    for (const bad of ['x', -1, null, {}, Number.NaN]) {
      const parsed = asBoardProject({ ...base, as_of: bad }) as BoardProject;
      expect(parsed.as_of, JSON.stringify(bad)).toBeUndefined();
    }
    expect((asBoardProject(base) as BoardProject).as_of).toBeUndefined();
  });

  it('keeps a pending review with null findings', () => {
    const task = asBoardTask({ ...boardTask({ column: 'in_review' }), review: { state: 'pending', findings: null, since: 5 } });
    expect(task?.review).toEqual({ state: 'pending', findings: null, since: 5 });
  });

  it('drops a task with an unknown column or a missing time, and keeps the rest', () => {
    const session = boardSession({
      tasks: [boardTask({ key: 'ok' }), { ...boardTask({ key: 'bad' }), column: 'blocked' as never }],
    });
    const parsed = asBoardProject(boardProject({ sessions: [session] }));
    expect(typeof parsed).toBe('object');
    expect((parsed as BoardProject).sessions[0]?.tasks.map((t) => t.key)).toEqual(['ok']);
    expect(asBoardTask({ key: 'x', column: 'todo', created_at: 1 })).toBeNull();
  });

  it('drops a session with an unknown status', () => {
    const raw = boardProject({ sessions: [boardSession(), { ...boardSession({ session_id: 'b' }), status: 'zombie' as never }] });
    expect((asBoardProject(raw) as BoardProject).sessions.map((s) => s.session_id)).toEqual(['session-aaaaaaaa']);
  });

  it('withholds a resume command that is not one line of the documented shape', () => {
    const cases: [string, string | null][] = [
      ["cd '/repo' && claude --resume 'abc'", "cd '/repo' && claude --resume 'abc'"],
      ["cd '/repo' && codex resume 'abc'", "cd '/repo' && codex resume 'abc'"],
      ["cd '/repo' && opencode --session 'abc'", "cd '/repo' && opencode --session 'abc'"],
      ["cd '/repo' && rm -rf ~", null],
      ["cd '/repo' && claude --resume 'abc'\nrm -rf ~", null],
      ['claude --resume abc', null],
    ];
    for (const [command, expected] of cases) {
      const parsed = asBoardProject(boardProject({ sessions: [boardSession({ resume_command: command })] })) as BoardProject;
      expect(parsed.sessions[0]?.resume_command, command).toBe(expected);
    }
  });

  it('clamps an oversized task text', () => {
    const task = asBoardTask({ ...boardTask(), content: 'x'.repeat(10_000) });
    expect(task?.content.length).toBe(2_000);
  });
});

describe('asTaskWatchEvent', () => {
  it('types each event of the stream', () => {
    expect(asTaskWatchEvent({ event: 'snapshot', project: boardProject() })).toMatchObject({ event: 'snapshot' });
    expect(asTaskWatchEvent({ event: 'snapshot', project: { project_id: 'proj-b', removed: true } })).toEqual({
      event: 'removed',
      projectId: 'proj-b',
    });
    expect(asTaskWatchEvent({ event: 'ready' })).toEqual({ event: 'ready' });
    expect(asTaskWatchEvent({ event: 'heartbeat', ts: 1 })).toEqual({ event: 'heartbeat' });
    expect(asTaskWatchEvent({ event: 'end', reason: 'stdin-closed' })).toEqual({ event: 'end', reason: 'stdin-closed' });
    expect(asTaskWatchEvent({ event: 'error', error: 'boom', hint: 'try', exit_code: 3 })).toMatchObject({
      event: 'error',
      exitCode: 3,
    });
  });

  it('reports what it cannot use instead of throwing', () => {
    expect(typeof asTaskWatchEvent({ event: 'surprise' })).toBe('string');
    expect(typeof asTaskWatchEvent({ event: 'snapshot', project: { removed: true } })).toBe('string');
    expect(typeof asTaskWatchEvent({ event: 'snapshot', project: { project_id: 'x' } })).toBe('string');
  });
});

describe('watchTasks and listTasks', () => {
  it('passes --stale-after in seconds through the allow-list, with the declaration', () => {
    const spawnStream = vi.fn(() => ({ stop: () => undefined, pid: 1 }));
    watchTasks(
      { binary: '/bin/devteam', cwd: '/app', declarationFile: '/app/schemas.json' },
      { staleAfterSeconds: 3600 },
      { onEvent: () => undefined, onInvalid: () => undefined, onEnd: () => undefined },
      spawnStream,
    );
    expect(spawnStream).toHaveBeenCalledWith(
      expect.objectContaining({ args: ['tasks', 'watch', '--stale-after', '3600'], declarationFile: '/app/schemas.json' }),
    );
  });

  it('omits a threshold that is not a sane number of seconds instead of passing it', () => {
    const spawnStream = vi.fn(() => ({ stop: () => undefined, pid: 1 }));
    watchTasks({ binary: '/b', cwd: '/' }, { staleAfterSeconds: -5 }, { onEvent: () => undefined, onInvalid: () => undefined, onEnd: () => undefined }, spawnStream);
    expect(spawnStream).toHaveBeenCalledWith(expect.objectContaining({ args: ['tasks', 'watch'] }));
  });

  it('streams typed events from a real child, ending cleanly on stdin close', async () => {
    const events: TaskWatchEvent[] = [];
    const invalid: string[] = [];
    let resolveEnd: (end: StreamEnd) => void = () => undefined;
    const ended = new Promise<StreamEnd>((resolve) => {
      resolveEnd = resolve;
    });
    const handle = watchTasks(
      { binary: process.execPath, cwd: REPO_ROOT },
      { staleAfterSeconds: 60 },
      { onEvent: (event) => events.push(event), onInvalid: (detail) => invalid.push(detail), onEnd: resolveEnd },
      (options) => streamDevteam({ ...options, args: [FAKE_WATCH, 'tasks'], killGraceMs: 200 }),
    );
    expect(handle).not.toBeNull();
    await until(() => events.some((e) => e.event === 'ready'));
    handle?.stop();
    expect(await ended).toMatchObject({ kind: 'exited', code: 0 });
    expect(events.map((e) => e.event)).toEqual(['snapshot', 'snapshot', 'removed', 'ready', 'end']);
    expect(invalid).toEqual([]);
  });

  it.skipIf(skipWithoutFake)('tasks list validates the document and passes the threshold', async () => {
    const context = { binary: FAKE_BINARY, cwd: REPO_ROOT, env: { FAKE_DEVTEAM_SCENARIO: 'tasks-list' } };
    const result = await listTasks(context, { staleAfterSeconds: 1800 });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    // The project without the documented fields is dropped; the task without a column too.
    expect(result.data.projects.map((p) => p.project_id)).toEqual(['proj-a']);
    expect(result.data.projects[0]?.sessions[0]?.tasks.map((t) => t.key)).toEqual(['t1', 't3']);
    expect(result.data.projects[0]?.sessions[0]?.tasks[1]?.review).toEqual({ state: 'findings', findings: 2, since: 4 });
  });
});

// ── the supervisor ────────────────────────────────────────────────────────────

function harness(overrides: Partial<TaskBoardDeps> = {}) {
  type Handlers = Parameters<TaskBoardDeps['startStream']>[0];
  const streams: { handlers: Handlers; stop: ReturnType<typeof vi.fn> }[] = [];
  const timers: { fn: () => void; ms: number; cleared: boolean }[] = [];
  const feeds: BoardFeed[] = [];
  const deps: TaskBoardDeps = {
    startStream: (handlers) => {
      const stop = vi.fn();
      streams.push({ handlers, stop });
      return Promise.resolve({ stop, pid: streams.length });
    },
    list: () => Promise.resolve({ ok: true, outcome: 'success', data: { projects: [] }, command: 'devteam tasks list', durationMs: 1 }),
    onChange: (feed) => feeds.push(feed),
    setTimer: (fn, ms) => {
      const timer = { fn, ms, cleared: false };
      timers.push(timer);
      return timer;
    },
    clearTimer: (timer) => {
      (timer as { cleared: boolean }).cleared = true;
    },
    ...overrides,
  };
  const board = new TaskBoard(deps);
  const emit = (event: TaskWatchEvent) => streams[streams.length - 1]?.handlers.onEvent(event);
  const end = (value: StreamEnd) => streams[streams.length - 1]?.handlers.onEnd(value);
  const fire = (ms: number) => {
    const timer = timers.find((t) => !t.cleared && t.ms === ms);
    if (timer === undefined) throw new Error(`no pending timer of ${ms} ms`);
    timer.cleared = true;
    timer.fn();
  };
  const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
  return { board, streams, timers, feeds, emit, end, fire, flush };
}

const exit1: StreamEnd = { kind: 'exited', code: 1, signal: null, stderr: '' };
const snap = (project: BoardProject): TaskWatchEvent => ({ event: 'snapshot', project });

describe('TaskBoard — snapshots', () => {
  it('goes live on ready and keeps the latest snapshot per project, newest activity first', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'a', last_activity_at: 100 })));
    h.emit(snap(boardProject({ project_id: 'b', last_activity_at: 300 })));
    h.emit({ event: 'ready' });
    expect(h.board.snapshot().status).toBe('live');
    expect(h.board.snapshot().projects.map((p) => p.project_id)).toEqual(['b', 'a']);
    h.emit(snap(boardProject({ project_id: 'a', last_activity_at: 500 })));
    expect(h.board.snapshot().projects.map((p) => p.project_id)).toEqual(['a', 'b']);
  });

  it('shows nothing of a backlog until ready, so a half-loaded board never renders', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'a' })));
    expect(h.board.snapshot().projects).toHaveLength(0);
    h.emit({ event: 'ready' });
    expect(h.board.snapshot().projects).toHaveLength(1);
  });

  it('a removal drops the project, before or after ready', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'a' })));
    h.emit({ event: 'removed', projectId: 'a' });
    h.emit({ event: 'ready' });
    expect(h.board.snapshot().projects).toHaveLength(0);
    h.emit(snap(boardProject({ project_id: 'b' })));
    h.emit({ event: 'removed', projectId: 'b' });
    expect(h.board.snapshot().projects).toHaveLength(0);
  });

  it('a restarted stream replaces the old snapshots at ready: a project that vanished disappears', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'a' })));
    h.emit(snap(boardProject({ project_id: 'b' })));
    h.emit({ event: 'ready' });
    h.end(exit1);
    // While the child is down the last good state stays on screen.
    expect(h.board.snapshot().projects).toHaveLength(2);
    h.fire(BOARD_BACKOFF_MIN_MS);
    await h.flush();
    h.emit(snap(boardProject({ project_id: 'a' })));
    expect(h.board.snapshot().projects).toHaveLength(2);
    h.emit({ event: 'ready' });
    expect(h.board.snapshot().projects.map((p) => p.project_id)).toEqual(['a']);
  });

  it('a stream that dies before ready leaves the last good state alone', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'a' })));
    h.emit({ event: 'ready' });
    h.end(exit1);
    h.fire(BOARD_BACKOFF_MIN_MS);
    await h.flush();
    h.emit(snap(boardProject({ project_id: 'z' })));
    h.end(exit1);
    expect(h.board.snapshot().projects.map((p) => p.project_id)).toEqual(['a']);
  });

  it('notifies on every change', async () => {
    const h = harness();
    await h.board.start();
    h.emit({ event: 'ready' });
    const before = h.feeds.length;
    h.emit(snap(boardProject()));
    expect(h.feeds.length).toBe(before + 1);
    expect(h.feeds[h.feeds.length - 1]?.projects).toHaveLength(1);
  });

  it('finds a session’s resume command, and nothing for an unknown one', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject()));
    h.emit({ event: 'ready' });
    expect(h.board.resumeCommand('proj-a', 'session-aaaaaaaa')).toContain('claude --resume');
    expect(h.board.resumeCommand('proj-a', 'nope')).toBeNull();
    expect(h.board.resumeCommand('nope', 'session-aaaaaaaa')).toBeNull();
  });

  it('refresh replaces the snapshots from a one-shot list, and keeps them when it fails', async () => {
    const h = harness({
      list: () =>
        Promise.resolve({
          ok: true,
          outcome: 'success',
          data: { projects: [boardProject({ project_id: 'listed' })] },
          command: 'devteam tasks list',
          durationMs: 1,
        }),
    });
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'old' })));
    h.emit({ event: 'ready' });
    expect((await h.board.refresh()).projects.map((p) => p.project_id)).toEqual(['listed']);

    const failing = harness({
      list: () =>
        Promise.resolve({ ok: false, kind: 'environment', message: 'nope', exitCode: 3, command: 'devteam tasks list', durationMs: 1 }),
    });
    await failing.board.start();
    failing.emit(snap(boardProject({ project_id: 'kept' })));
    failing.emit({ event: 'ready' });
    expect((await failing.board.refresh()).projects.map((p) => p.project_id)).toEqual(['kept']);
  });
});

describe('TaskBoard — the stream is supervised', () => {
  it('restarts after an unexpected exit with a doubling backoff, reset once a child stays healthy', async () => {
    const h = harness();
    await h.board.start();
    h.end(exit1);
    expect(h.board.snapshot().status).toBe('retrying');
    h.fire(BOARD_BACKOFF_MIN_MS);
    await h.flush();
    expect(h.streams).toHaveLength(2);
    h.end(exit1);
    h.fire(BOARD_BACKOFF_MIN_MS * 2);
    await h.flush();
    h.emit({ event: 'ready' });
    h.fire(BOARD_HEALTHY_MS);
    h.end(exit1);
    expect(() => h.fire(BOARD_BACKOFF_MIN_MS)).not.toThrow();
  });

  it('does not reset the backoff for a child that dies right after ready', async () => {
    const h = harness();
    await h.board.start();
    h.end(exit1);
    h.fire(BOARD_BACKOFF_MIN_MS);
    await h.flush();
    h.emit({ event: 'ready' });
    h.end(exit1);
    expect(() => h.fire(BOARD_BACKOFF_MIN_MS * 2)).not.toThrow();
  });

  it('never waits longer than the cap', async () => {
    const h = harness();
    await h.board.start();
    let delay = BOARD_BACKOFF_MIN_MS;
    for (let i = 0; i < 10; i += 1) {
      h.end(exit1);
      h.fire(delay);
      await h.flush();
      delay = Math.min(delay * 2, BOARD_BACKOFF_MAX_MS);
    }
    const retries = h.timers.filter((t) => t.ms !== BOARD_WATCHDOG_MS);
    expect(retries.every((t) => t.ms <= BOARD_BACKOFF_MAX_MS)).toBe(true);
    expect(retries.some((t) => t.ms === BOARD_BACKOFF_MAX_MS)).toBe(true);
  });

  it('does not retry an environment error (exit 3), and says why', async () => {
    const h = harness();
    await h.board.start();
    h.emit({ event: 'error', message: 'this store needs a layout migration', hint: 'Run devteam migrate.', exitCode: 3 });
    h.end({ kind: 'exited', code: 3, signal: null, stderr: '' });
    expect(h.board.snapshot().status).toBe('unavailable');
    expect(h.board.snapshot().detail).toMatch(/layout migration Run devteam migrate\./);
    expect(h.timers.filter((t) => !t.cleared && t.ms === BOARD_BACKOFF_MIN_MS)).toHaveLength(0);
  });

  it('falls back to stderr for an exit 3 with no error event', async () => {
    const h = harness();
    await h.board.start();
    h.end({ kind: 'exited', code: 3, signal: null, stderr: 'devteam: error: store is ahead\n' });
    expect(h.board.snapshot().detail).toMatch(/store is ahead/);
  });

  it('restarts a child that has gone silent past the 90 s watchdog, and any event re-arms it', async () => {
    const h = harness();
    await h.board.start();
    expect(BOARD_WATCHDOG_MS).toBe(90_000);
    h.emit({ event: 'heartbeat' });
    const stale = h.timers.filter((t) => t.ms === BOARD_WATCHDOG_MS);
    expect(stale.length).toBeGreaterThanOrEqual(2);
    expect(stale[0]?.cleared).toBe(true);
    h.fire(BOARD_WATCHDOG_MS);
    expect(h.streams[0]?.stop).toHaveBeenCalled();
  });

  it('reports no CLI as unavailable instead of retrying forever', async () => {
    const h = harness({ startStream: () => Promise.resolve(null) });
    await h.board.start();
    expect(h.board.snapshot().status).toBe('unavailable');
  });

  it('retries a stream that fails to start', async () => {
    const h = harness({ startStream: () => Promise.reject(new Error('spawn boom')) });
    await h.board.start();
    expect(h.board.snapshot()).toMatchObject({ status: 'retrying' });
    expect(h.board.snapshot().detail).toMatch(/spawn boom/);
  });

  it('a restart while the first start is pending leaves exactly one child', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const stops: ReturnType<typeof vi.fn>[] = [];
    let calls = 0;
    const h = harness({
      startStream: async () => {
        calls += 1;
        if (calls === 1) await gate;
        const stop = vi.fn();
        stops.push(stop);
        return { stop, pid: calls };
      },
    });
    const first = h.board.start();
    await h.board.restart();
    release();
    await first;
    expect(stops).toHaveLength(2);
    expect(stops.filter((stop) => stop.mock.calls.length === 0)).toHaveLength(1);
  });

  it('start() twice does not begin a second child, and stop() ends the one running', async () => {
    const h = harness();
    await Promise.all([h.board.start(), h.board.start()]);
    expect(h.streams).toHaveLength(1);
    h.board.stop();
    expect(h.streams[0]?.stop).toHaveBeenCalled();
    h.end(exit1);
    expect(h.timers.filter((t) => !t.cleared && t.ms === BOARD_BACKOFF_MIN_MS)).toHaveLength(0);
  });

  it('ignores the events of a child a restart has replaced', async () => {
    const h = harness();
    await h.board.start();
    const old = h.streams[0]!;
    await h.board.restart();
    old.handlers.onEvent(snap(boardProject({ project_id: 'ghost' })));
    old.handlers.onEvent({ event: 'ready' });
    expect(h.board.snapshot().status).not.toBe('live');
    expect(h.board.snapshot().projects).toHaveLength(0);
  });
});

describe('TaskBoard — races and restarts', () => {
  it('a refresh that raced the stream does not discard the snapshots applied meanwhile', async () => {
    let release: (projects: BoardProject[]) => void = () => undefined;
    const h = harness({
      list: () =>
        new Promise((resolve) => {
          release = (projects) =>
            resolve({ ok: true, outcome: 'success', data: { projects }, command: 'devteam tasks list', durationMs: 1 });
        }),
    });
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'old' })));
    h.emit({ event: 'ready' });
    const pending = h.board.refresh();
    h.emit(snap(boardProject({ project_id: 'newer' })));
    release([boardProject({ project_id: 'stale-list' })]);
    const feed = await pending;
    expect(feed.projects.map((p) => p.project_id).sort()).toEqual(['newer', 'old']);
  });

  it('keeps the live status and the data across a restart instead of flashing "starting"', async () => {
    const h = harness();
    await h.board.start();
    h.emit(snap(boardProject({ project_id: 'a' })));
    h.emit({ event: 'ready' });
    const before = h.feeds.length;
    await h.board.restart();
    expect(h.streams).toHaveLength(2);
    expect(h.board.snapshot().status).toBe('live');
    expect(h.board.snapshot().projects).toHaveLength(1);
    expect(h.feeds.slice(before).every((feed) => feed.status !== 'starting')).toBe(true);
  });

  it('a disposed board never spawns again: not on restart, not on start', async () => {
    const h = harness();
    await h.board.start();
    h.board.dispose();
    expect(h.streams[0]?.stop).toHaveBeenCalled();
    await h.board.restart();
    await h.board.start();
    expect(h.streams).toHaveLength(1);
  });
});

describe('TaskBoard — round-2 races and failures', () => {
  it('an argv the allow-list refuses is its own terminal outcome, not "no CLI found" and not a retry loop', async () => {
    const h = harness({ startStream: () => Promise.reject(new TaskStreamRefused('unknown command')) });
    await h.board.start();
    const feed = h.board.snapshot();
    expect(feed.status).toBe('unavailable');
    expect(feed.detail).toMatch(/refused by the argument allow-list: unknown command/);
    expect(feed.detail).not.toMatch(/No devteam CLI/);
    expect(h.timers.filter((t) => !t.cleared)).toEqual([]);
  });

  it('overlapping refresh calls share one list and both see the same, latest answer', async () => {
    let release: (projects: BoardProject[]) => void = () => undefined;
    const list = vi.fn(
      () =>
        new Promise<Awaited<ReturnType<TaskBoardDeps['list']>>>((resolve) => {
          release = (projects) => resolve({ ok: true, outcome: 'success', data: { projects }, command: 'devteam tasks list', durationMs: 1 });
        }),
    );
    const h = harness({ list });
    const first = h.board.refresh();
    const second = h.board.refresh();
    expect(list).toHaveBeenCalledTimes(1);
    release([boardProject({ project_id: 'fresh' })]);
    const [a, b] = await Promise.all([first, second]);
    expect(a.projects.map((p) => p.project_id)).toEqual(['fresh']);
    expect(b.projects.map((p) => p.project_id)).toEqual(['fresh']);
    void h.board.refresh();
    expect(list).toHaveBeenCalledTimes(2);
  });

  it('a restart clears the heartbeat watchdog of the child it drops', async () => {
    let calls = 0;
    const h = harness({
      startStream: () => {
        calls += 1;
        return calls === 1 ? Promise.resolve({ stop: vi.fn(), pid: 1 }) : Promise.resolve(null);
      },
    });
    await h.board.start();
    const watchdog = h.timers.find((t) => t.ms === BOARD_WATCHDOG_MS && !t.cleared);
    expect(watchdog).toBeDefined();
    await h.board.restart();
    expect(watchdog?.cleared).toBe(true);
  });
});

describe('saveBoardSettings', () => {
  function store(previous: { staleAfterMinutes: number; doneRetentionDays: number }) {
    let current = previous;
    const restart = vi.fn();
    return {
      restart,
      io: {
        read: () => Promise.resolve(current),
        write: (next: typeof previous) => {
          current = next;
          return Promise.resolve();
        },
        restartStream: restart,
      },
    };
  }

  it('restarts the stream only when the stale threshold changed', async () => {
    const changed = store({ staleAfterMinutes: 60, doneRetentionDays: 7 });
    await saveBoardSettings(changed.io, { staleAfterMinutes: 30, doneRetentionDays: 7 });
    expect(changed.restart).toHaveBeenCalledTimes(1);
  });

  it('leaves the stream alone on a retention-only save, and returns what was stored', async () => {
    const retention = store({ staleAfterMinutes: 60, doneRetentionDays: 7 });
    const saved = await saveBoardSettings(retention.io, { staleAfterMinutes: 60, doneRetentionDays: 14 });
    expect(retention.restart).not.toHaveBeenCalled();
    expect(saved).toEqual({ staleAfterMinutes: 60, doneRetentionDays: 14 });
  });
});

describe('RESUME_COMMAND', () => {
  const shlexQuote = (value: string) =>
    /^[\w@%+=:,./-]+$/.test(value) ? value : `'${value.replace(/'/g, `'"'"'`)}'`;
  const command = (root: string, id: string) => `cd ${shlexQuote(root)} && claude --resume ${shlexQuote(id)}`;

  it('accepts what shlex.quote writes, including a path with a space and an embedded quote', () => {
    for (const each of [
      command('/repo/storefront', 'session-aaaaaaaa'),
      command('/My Projects/shop', 'abc'),
      command("/o'brien/shop", 'abc'),
      command('/repo', "it's"),
      "cd '/r' && codex resume 's1'",
      "cd /r && opencode --session ses_1",
    ]) {
      expect(RESUME_COMMAND.test(each), each).toBe(true);
    }
  });

  it('rejects an operand that is not a single shell-safe token', () => {
    for (const each of [
      'cd /a; rm -rf ~ && claude --resume x',
      'cd /a && claude --resume x; rm -rf ~',
      'cd /a && claude --resume $(reboot)',
      'cd /a && claude --resume `id`',
      'cd /a b && claude --resume x',
      "cd '/a'; rm -rf ~ && claude --resume 'x'",
      "cd '/a' && claude --resume 'x' && rm -rf ~",
      "cd '/a\nb' && claude --resume 'x'",
      "cd /a && claude --resume x | sh",
      "cd '/a' && claude --resume 'x'y'z'",
    ]) {
      expect(RESUME_COMMAND.test(each), each).toBe(false);
    }
  });

  it('asBoardSession nulls a hostile resume command and keeps a real one', () => {
    const hostile = { ...JSON.parse(JSON.stringify(boardSession())), resume_command: 'cd /a; rm -rf ~ && claude --resume x' };
    const real = { ...JSON.parse(JSON.stringify(boardSession())), resume_command: command("/o'b", 'abc') };
    const parse = (session: unknown) =>
      asBoardProject({ ...JSON.parse(JSON.stringify(boardProject())), sessions: [session] });
    expect((parse(hostile) as BoardProject).sessions[0]?.resume_command).toBeNull();
    expect((parse(real) as BoardProject).sessions[0]?.resume_command).toBe(command("/o'b", 'abc'));
  });
});

// ── IPC ───────────────────────────────────────────────────────────────────────

type Handler = (...args: unknown[]) => unknown;

async function loadIpc() {
  vi.resetModules();
  const handlers = new Map<string, Handler>();
  vi.doMock('electron', () => ({
    ipcMain: {
      handle: (channel: string, listener: Handler) => {
        handlers.set(channel, listener);
      },
    },
  }));
  const ipc: typeof IpcModule = await import('../src/main/taskBoardIpc.js');
  const api: typeof ApiModule = await import('../src/shared/api.js');
  onTestFinished(() => {
    vi.doUnmock('electron');
  });
  return { handlers, ...ipc, CHANNELS: api.CHANNELS };
}

const TRUSTED_RENDERER = { indexUrl: 'file:///app/dist/renderer/index.html', devServerOrigin: null } as const;
const TRUSTED = { senderFrame: { url: TRUSTED_RENDERER.indexUrl, parent: null } };

describe('task board IPC', () => {
  function deps(overrides: Partial<IpcModule.TaskBoardIpcDeps> = {}): IpcModule.TaskBoardIpcDeps & { copied: string[] } {
    const copied: string[] = [];
    return {
      copied,
      trustedRenderer: TRUSTED_RENDERER,
      feed: () => ({ status: 'live', detail: null, projects: [] }),
      refresh: () => Promise.resolve({ status: 'live', detail: null, projects: [] }),
      resumeCommand: (projectId, sessionId) =>
        projectId === 'proj-a' && sessionId === 's1' ? "cd '/r' && claude --resume 's1'" : null,
      copyText: (text) => copied.push(text),
      boardSettings: () => Promise.resolve({ staleAfterMinutes: 60, doneRetentionDays: 7 }),
      saveBoardSettings: (settings) => Promise.resolve(settings),
      ...overrides,
    };
  }

  it('parseCopyRequest accepts two well-formed ids and refuses anything else', async () => {
    const { parseCopyRequest } = await loadIpc();
    expect(parseCopyRequest({ projectId: 'p', sessionId: 's' })).toEqual({ projectId: 'p', sessionId: 's' });
    for (const bad of [null, 'x', [], {}, { projectId: 'p' }, { projectId: 1, sessionId: 's' }, { projectId: '', sessionId: 's' },
      { projectId: 'p', sessionId: 'a\nb' }, { projectId: 'p', sessionId: 'x'.repeat(600) }]) {
      expect(typeof parseCopyRequest(bad), JSON.stringify(bad)).toBe('string');
    }
  });

  it('copies only the command the CLI sent for the named session', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    const d = deps();
    registerTaskBoardIpc(d);
    const copy = handlers.get(CHANNELS.copyResumeCommand)!;
    // Extra fields, including a `command` the renderer tries to supply, change nothing.
    expect(copy(TRUSTED, { projectId: 'proj-a', sessionId: 's1', command: 'rm -rf ~' })).toEqual({
      copied: true,
      command: "cd '/r' && claude --resume 's1'",
    });
    expect(d.copied).toEqual(["cd '/r' && claude --resume 's1'"]);
  });

  it('copies nothing for an unknown session or a malformed request', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    const d = deps();
    registerTaskBoardIpc(d);
    const copy = handlers.get(CHANNELS.copyResumeCommand)!;
    expect(copy(TRUSTED, { projectId: 'proj-a', sessionId: 'nope' })).toMatchObject({ copied: false });
    expect(copy(TRUSTED, 'x')).toMatchObject({ copied: false });
    expect(d.copied).toEqual([]);
  });

  it('refuses every channel to a sender that is not this app\'s renderer', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    const d = deps();
    registerTaskBoardIpc(d);
    const foreign = { senderFrame: { url: 'https://evil.example/', parent: null } };
    for (const channel of [CHANNELS.taskBoard, CHANNELS.refreshTaskBoard, CHANNELS.copyResumeCommand,
      CHANNELS.boardSettings, CHANNELS.setBoardSettings]) {
      expect(() => handlers.get(channel)!(foreign, { projectId: 'proj-a', sessionId: 's1' }), channel).toThrow(/refused/);
    }
    expect(d.copied).toEqual([]);
  });

  it('serves the feed and the refresh', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    registerTaskBoardIpc(deps());
    expect(handlers.get(CHANNELS.taskBoard)!(TRUSTED)).toMatchObject({ status: 'live' });
    expect(await handlers.get(CHANNELS.refreshTaskBoard)!(TRUSTED)).toMatchObject({ status: 'live' });
  });

  it('validates the settings before it saves anything', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    const save = vi.fn((s) => Promise.resolve(s));
    registerTaskBoardIpc(deps({ saveBoardSettings: save }));
    const set = handlers.get(CHANNELS.setBoardSettings)!;
    for (const bad of [null, 'x', { staleAfterMinutes: 60 }, { staleAfterMinutes: '60', doneRetentionDays: 7 },
      { staleAfterMinutes: 4, doneRetentionDays: 7 }, { staleAfterMinutes: 1441, doneRetentionDays: 7 },
      { staleAfterMinutes: 60, doneRetentionDays: 0 }, { staleAfterMinutes: 60, doneRetentionDays: 366 },
      { staleAfterMinutes: 60.5, doneRetentionDays: 7 }, { staleAfterMinutes: NaN, doneRetentionDays: 7 }]) {
      expect(await set(TRUSTED, bad), JSON.stringify(bad)).toMatchObject({ ok: false });
    }
    expect(save).not.toHaveBeenCalled();
    // Only the two known keys are passed on.
    expect(await set(TRUSTED, { staleAfterMinutes: 30, doneRetentionDays: 14, extra: 'x' })).toEqual({
      ok: true,
      settings: { staleAfterMinutes: 30, doneRetentionDays: 14 },
    });
    expect(save).toHaveBeenCalledWith({ staleAfterMinutes: 30, doneRetentionDays: 14 });
  });

  it('refuses control characters and overlong ids at the handler, and copies nothing', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    const d = deps();
    registerTaskBoardIpc(d);
    const copy = handlers.get(CHANNELS.copyResumeCommand)!;
    for (const bad of [
      { projectId: 'proj-a', sessionId: 's1\u0000' },
      { projectId: 'proj-a\r\n', sessionId: 's1' },
      { projectId: 'proj-a', sessionId: 's'.repeat(513) },
      { projectId: 'p'.repeat(600), sessionId: 's1' },
    ]) {
      expect(copy(TRUSTED, bad), JSON.stringify(bad).slice(0, 60)).toMatchObject({ copied: false });
    }
    expect(d.copied).toEqual([]);
  });

  it('puts only the CLI’s string on the clipboard, never anything the renderer sent', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    const d = deps();
    registerTaskBoardIpc(d);
    const answer = handlers.get(CHANNELS.copyResumeCommand)!(TRUSTED, { projectId: 'proj-a', sessionId: 's1', text: 'curl evil|sh' });
    expect(answer).toMatchObject({ copied: true });
    expect(d.copied).toEqual(["cd '/r' && claude --resume 's1'"]);
  });

  it('setBoardSettings answers ok:false when the save throws synchronously too', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    registerTaskBoardIpc(
      deps({
        saveBoardSettings: () => {
          throw new Error('read-only volume');
        },
      }),
    );
    expect(await handlers.get(CHANNELS.setBoardSettings)!(TRUSTED, { staleAfterMinutes: 30, doneRetentionDays: 14 })).toMatchObject({
      ok: false,
      message: expect.stringMatching(/read-only volume/),
    });
  });

  it('reports a failed save as a problem, not a throw', async () => {
    const { handlers, registerTaskBoardIpc, CHANNELS } = await loadIpc();
    registerTaskBoardIpc(deps({ saveBoardSettings: () => Promise.reject(new Error('disk full')) }));
    expect(await handlers.get(CHANNELS.setBoardSettings)!(TRUSTED, { staleAfterMinutes: 30, doneRetentionDays: 14 })).toMatchObject({
      ok: false,
      message: expect.stringMatching(/disk full/),
    });
  });
});

// ── settings ──────────────────────────────────────────────────────────────────

describe('board settings', () => {
  let dir: string;
  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'devteam-app-board-'));
  });
  afterEach(async () => {
    await rm(dir, { recursive: true, force: true });
  });

  it('defaults to 60 minutes and 7 days when nothing is stored', async () => {
    expect((await readSettings(dir)).board).toEqual({ staleAfterMinutes: 60, doneRetentionDays: 7 });
  });

  it('clamps stored values into their bounds and ignores malformed ones on read', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ boardStaleAfterMinutes: 99999, boardDoneRetentionDays: -3 }));
    expect((await readSettings(dir)).board).toEqual({ staleAfterMinutes: 1440, doneRetentionDays: 1 });
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ boardStaleAfterMinutes: 'soon', boardDoneRetentionDays: null }));
    expect((await readSettings(dir)).board).toEqual({ staleAfterMinutes: 60, doneRetentionDays: 7 });
  });

  it('keeps board values readable when the file has a bad cliPath', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ cliPath: 42, boardStaleAfterMinutes: 30 }));
    const read = await readSettings(dir);
    expect(read.problem).toBeDefined();
    expect(read.board.staleAfterMinutes).toBe(30);
  });

  it('round-trips a write and never drops cliPath or project names', async () => {
    await writeFile(join(dir, SETTINGS_FILE_NAME), JSON.stringify({ cliPath: '/opt/devteam', projectNames: { p: 'Storefront' } }));
    await writeBoardSettings(dir, { staleAfterMinutes: 30, doneRetentionDays: 14 });
    const read = await readSettings(dir);
    expect(read).toMatchObject({ cliPath: '/opt/devteam', projectNames: { p: 'Storefront' }, board: { staleAfterMinutes: 30, doneRetentionDays: 14 } });
    // A later, unrelated write carries the board values forward.
    await writeProjectName(dir, 'q', 'Billing');
    expect((await readSettings(dir)).board).toEqual({ staleAfterMinutes: 30, doneRetentionDays: 14 });
  });

  it('writes nothing for a board left at its defaults', async () => {
    await writeBoardSettings(dir, { staleAfterMinutes: 60, doneRetentionDays: 7 });
    const written = JSON.parse(await readFile(join(dir, SETTINGS_FILE_NAME), 'utf8')) as Record<string, unknown>;
    expect(Object.keys(written)).toEqual(['projectNames']);
  });

  it('boardSettingsProblem names the bound that was broken', () => {
    expect(boardSettingsProblem({ staleAfterMinutes: 60, doneRetentionDays: 7 })).toBeNull();
    expect(boardSettingsProblem({ staleAfterMinutes: 2, doneRetentionDays: 7 })).toMatch(/between 5 and 1440/);
    expect(boardSettingsProblem({ staleAfterMinutes: 60, doneRetentionDays: 400 })).toMatch(/between 1 and 365/);
  });
});
