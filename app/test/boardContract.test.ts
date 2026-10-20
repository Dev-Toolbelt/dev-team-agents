/**
 * The CLI's board JSON against the app's parser. `board-keys.json` is the key list the CLI emits
 * (pinned from the Python side by `BoardJsonKeysPinTest`); every key must either come out of
 * `asBoardProject` or be listed in IGNORED with a reason, so a key the CLI adds can never be dropped
 * silently, as `interrupted` once was.
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { asBoardProject } from '../src/cli/operations.js';

type Kind =
  | 'project' | 'session' | 'task' | 'counts' | 'session_pr' | 'task_pr' | 'ref' | 'review' | 'worktree'
  | 'turn' | 'link_host' | 'duration';

const KEYS = JSON.parse(readFileSync(new URL('./fixtures/board-keys.json', import.meta.url), 'utf8')) as Record<Kind, string[]>;

/** Keys the CLI emits that the app deliberately does not carry: `kind` -> `key` -> why. */
const IGNORED: Record<Kind, Record<string, string>> = {
  project: {}, session: {}, task: {}, counts: {}, session_pr: {}, task_pr: {}, ref: {}, review: {},
  worktree: {}, turn: {}, link_host: {}, duration: {},
};

const COUNTS = { todo: 1, in_progress: 2, in_review: 3, pr_created: 4, done: 5, total: 15 };
const SAMPLE: Record<Kind, Record<string, unknown>> = {
  project: {
    project_id: 'p1', root: '/r', providers: ['claude'], sessions_total: 1, sessions_active: 1, stale: 1, abandoned: 1,
    with_findings: 1, last_activity_at: 9, as_of: 9,
  },
  session: {
    session_id: 's1', title: 'T', provider: 'claude', branch: 'main', cwd: '/r', status: 'active', created_at: 1,
    last_activity_at: 9, ended_at: 10, resume_command: 'cd /r && claude --resume s1',
  },
  task: {
    key: 't1', content: 'c', owner: 'agent-1', agent_type: 'Explore', kind: 'agent', failed: true, interrupted: true,
    status: 'completed', column: 'done', created_at: 1, status_since: 2, completed_at: 3, stale: true, abandoned: true,
  },
  counts: COUNTS,
  session_pr: { kind: 'pr', number: 7, url: 'https://github.com/o/r/pull/7', state: 'open', head: 'feat' },
  task_pr: { kind: 'pr', number: 7, url: 'https://github.com/o/r/pull/7', state: 'open' },
  ref: { system: 'jira', key: 'ABC-1', url: 'https://x.atlassian.net/browse/ABC-1' },
  review: { state: 'findings', findings: 2, since: 5 },
  worktree: { path: '/wt', branch: 'feat' },
  turn: { text: 'hi', at: 4 },
  link_host: { host: 'x.atlassian.net', kinds: ['jira'], base_path: '/jira' },
  duration: { pending: 1, in_progress: 2, completed: 3, in_review: 4, pr_created: 5 },
};

/** A payload of the CLI's shape with every fixture key; `track` records each property the parser reads. */
function payload(track?: (kind: Kind, key: string) => void) {
  const watch = <T extends object>(kind: Kind, value: T): T =>
    track === undefined
      ? value
      : new Proxy(value, {
          get(target, prop, receiver) {
            if (typeof prop === 'string') track(kind, prop);
            return Reflect.get(target, prop, receiver) as unknown;
          },
        });
  const task = {
    ...SAMPLE.task,
    durations: watch('duration', { ...SAMPLE.duration }),
    review: watch('review', { ...SAMPLE.review }),
    worktree: watch('worktree', { ...SAMPLE.worktree }),
    turns: [watch('turn', { ...SAMPLE.turn })],
    pr: watch('task_pr', { ...SAMPLE.task_pr }),
    refs: [watch('ref', { ...SAMPLE.ref })],
  };
  const session = {
    ...SAMPLE.session,
    counts: watch('counts', { ...COUNTS }),
    prs: [watch('session_pr', { ...SAMPLE.session_pr })],
    tasks: [watch('task', task)],
  };
  return watch('project', {
    ...SAMPLE.project,
    counts: watch('counts', { ...COUNTS }),
    link_hosts: [watch('link_host', { ...SAMPLE.link_host })],
    sessions: [watch('session', session)],
  });
}

function parsed(): Record<Kind, Record<string, unknown>[]> {
  const project = asBoardProject(payload());
  if (typeof project === 'string') throw new Error(project);
  const session = project.sessions[0]!;
  const task = session.tasks[0]!;
  return {
    project: [project as unknown as Record<string, unknown>],
    session: [session as unknown as Record<string, unknown>],
    task: [task as unknown as Record<string, unknown>],
    counts: [project.counts, session.counts] as unknown as Record<string, unknown>[],
    session_pr: session.prs as unknown as Record<string, unknown>[],
    task_pr: [task.pr] as unknown as Record<string, unknown>[],
    ref: task.refs as unknown as Record<string, unknown>[],
    review: [task.review] as unknown as Record<string, unknown>[],
    worktree: [task.worktree] as unknown as Record<string, unknown>[],
    turn: task.turns as unknown as Record<string, unknown>[],
    link_host: project.link_hosts as unknown as Record<string, unknown>[],
    duration: [task.durations],
  };
}

const KINDS = Object.keys(KEYS) as Kind[];

/** Keys that hold another kind's document: exempt from needing a sample value, per kind. */
const NESTED: Record<Kind, readonly string[]> = {
  project: ['counts', 'link_hosts', 'sessions'],
  session: ['counts', 'prs', 'tasks'],
  task: ['durations', 'review', 'worktree', 'turns', 'pr', 'refs'],
  counts: [], session_pr: [], task_pr: [], ref: [], review: [], worktree: [], turn: [], link_host: [], duration: [],
};

describe('board JSON contract', () => {
  it('knows every kind the fixture lists', () => {
    expect([...KINDS].sort()).toEqual(Object.keys(SAMPLE).sort());
    expect(Object.keys(IGNORED).sort()).toEqual(Object.keys(SAMPLE).sort());
  });

  for (const kind of Object.keys(SAMPLE) as Kind[]) {
    describe(kind, () => {
      it('has a sample value for every key the CLI emits', () => {
        const missing = KEYS[kind].filter((key) => !(key in SAMPLE[kind]) && !NESTED[kind].includes(key));
        expect(missing, `add a sample value for ${kind}.${missing.join(', ')} in boardContract.test.ts`).toEqual([]);
      });

      it('exposes every key the CLI emits, or lists it as ignored', () => {
        for (const entry of parsed()[kind]) {
          const dropped = KEYS[kind].filter((key) => !(key in entry) && !(key in IGNORED[kind]));
          expect(dropped, `${kind}: the app parser drops ${dropped.join(', ')}; parse it or add it to IGNORED with a reason`).toEqual([]);
        }
      });

      it('keeps the value it was sent', () => {
        for (const entry of parsed()[kind]) {
          for (const [key, value] of Object.entries(SAMPLE[kind])) {
            if (key in IGNORED[kind]) continue;
            expect(entry[key], `${kind}.${key}`).toEqual(value);
          }
        }
      });

      it('lists as ignored only keys the CLI still emits and the app really drops', () => {
        for (const key of Object.keys(IGNORED[kind])) {
          expect(KEYS[kind], `${kind}.${key} is ignored but the CLI no longer emits it`).toContain(key);
          for (const entry of parsed()[kind]) expect(key in entry, `${kind}.${key} is parsed, so drop it from IGNORED`).toBe(false);
        }
      });
    });
  }

  it('reads no key the CLI does not emit', () => {
    const read: Record<string, Set<string>> = {};
    const project = asBoardProject(payload((kind, key) => (read[kind] ??= new Set()).add(key)));
    expect(typeof project).not.toBe('string');
    for (const kind of KINDS) {
      // Duration keys are read by name from an open-ended map, never by a fixed key.
      const unknown = [...(read[kind] ?? [])].filter((key) => !KEYS[kind].includes(key) && !(key in Array.prototype));
      expect(unknown, `${kind}: the parser reads ${unknown.join(', ')}, which the CLI no longer emits`).toEqual([]);
    }
  });
});
