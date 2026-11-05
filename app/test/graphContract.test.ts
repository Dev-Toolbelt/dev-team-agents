/**
 * The CLI's `tasks graph` JSON against the app's parser. `graph-keys.json` is the key list the CLI
 * emits (pinned from the Python side); every key must either come out of `asTaskGraph` or be listed
 * in IGNORED with a reason, so a key the CLI adds can never be dropped silently.
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { asTaskGraph } from '../src/cli/operations.js';

type Kind = 'graph' | 'group' | 'node' | 'edge' | 'todo';

const KEYS = JSON.parse(readFileSync(new URL('./fixtures/graph-keys.json', import.meta.url), 'utf8')) as Record<Kind, string[]>;

/** Keys the CLI emits that the app deliberately does not carry: `kind` -> `key` -> why. */
const IGNORED: Record<Kind, Record<string, string>> = {
  graph: {},
  group: {},
  node: { persona_source: 'the canvas shows the persona, not which signal derived it' },
  edge: {},
  todo: {},
};

const SAMPLE: Record<Kind, Record<string, unknown>> = {
  graph: { schema: 1, project_id: 'p1', as_of: 9, truncated: true, notices: ['no_trace:s2'] },
  group: {
    id: 'turn:s1:5', kind: 'turn', parent: 'session:s1', label: '/devteam:sprint', provider: 'claude', status: 'active',
    branch: 'feat/x', command: 'sprint', at: 5, started_at: 5, ended_at: 8, tokens: 40, usage_complete: true,
    session_id: 's1',
  },
  node: {
    id: 'span:s1:a', kind: 'agent', group: 'turn:s1:5', label: 'backend-developer', agent: 'backend-developer',
    description: 'Build the API', persona: 'orchestrator', persona_source: 'command', status: 'completed', model: 'opus',
    started_at: 5, ended_at: 7, duration_s: 2, tokens: 10, subtree_tokens: 12, usage_complete: true, findings: 3,
    background: true, last_output: 'Done: 3 files', task_key: 't4',
    session_id: 's1', record_id: 's1-child', spawn_id: 'a',
  },
  edge: { id: 'e:main:s1>span:s1:a', from: 'main:s1', to: 'span:s1:a', kind: 'spawn' },
  todo: { key: 't1', content: 'write tests', status: 'in_progress' },
};

/** Keys that hold another document: exempt from needing a sample value, per kind. */
const NESTED: Record<Kind, readonly string[]> = {
  graph: ['groups', 'nodes', 'edges'],
  group: ['prs'],
  node: ['worktree', 'pr', 'todos'],
  edge: [],
  todo: [],
};

const PR = { kind: 'pr', number: 7, url: 'https://github.com/o/r/pull/7', state: 'open' };

/** A payload of the CLI's shape with every fixture key; `track` records each property the parser reads. */
function payload(track?: (kind: Kind, key: string) => void): Record<string, unknown> {
  const watch = <T extends object>(kind: Kind, value: T): T =>
    track === undefined
      ? value
      : new Proxy(value, {
          get(target, prop, receiver) {
            if (typeof prop === 'string') track(kind, prop);
            return Reflect.get(target, prop, receiver) as unknown;
          },
        });
  const session = { ...SAMPLE.group, id: 'session:s1', kind: 'session', parent: null, command: null, prs: [{ ...PR, head: 'feat/x' }] };
  const turn = { ...SAMPLE.group, prs: [] };
  const main = { ...SAMPLE.node, id: 'main:s1', kind: 'main', group: 'session:s1', worktree: null, pr: null, todos: [] };
  const span = {
    ...SAMPLE.node,
    worktree: { path: '.worktrees/feat/x', branch: 'feat/x' },
    pr: { ...PR },
    todos: [watch('todo', { ...SAMPLE.todo })],
  };
  return watch('graph', {
    ...SAMPLE.graph,
    groups: [watch('group', session), watch('group', turn)],
    nodes: [watch('node', main), watch('node', span)],
    edges: [watch('edge', { ...SAMPLE.edge })],
  });
}

function parsed(): Record<Kind, Record<string, unknown>[]> {
  const graph = asTaskGraph(payload());
  if (typeof graph === 'string') throw new Error(graph);
  const span = graph.nodes[1]!;
  return {
    graph: [graph as unknown as Record<string, unknown>],
    group: [graph.groups[1]] as unknown as Record<string, unknown>[],
    node: [span] as unknown as Record<string, unknown>[],
    edge: graph.edges as unknown as Record<string, unknown>[],
    todo: span.todos as unknown as Record<string, unknown>[],
  };
}

const KINDS = Object.keys(KEYS) as Kind[];

describe('graph JSON contract', () => {
  it('knows every kind the fixture lists', () => {
    expect([...KINDS].sort()).toEqual(Object.keys(SAMPLE).sort());
    expect(Object.keys(IGNORED).sort()).toEqual(Object.keys(SAMPLE).sort());
  });

  it('keeps every group, node and edge of a well-formed payload', () => {
    const graph = asTaskGraph(payload());
    if (typeof graph === 'string') throw new Error(graph);
    expect(graph.groups.map((group) => group.id)).toEqual(['session:s1', 'turn:s1:5']);
    expect(graph.nodes.map((node) => node.id)).toEqual(['main:s1', 'span:s1:a']);
    expect(graph.edges).toHaveLength(1);
    expect(graph.groups[0]!.prs).toEqual([{ ...PR, head: 'feat/x' }]);
    expect(graph.nodes[1]!.worktree).toEqual({ path: '.worktrees/feat/x', branch: 'feat/x' });
    expect(graph.nodes[1]!.pr).toEqual(PR);
  });

  for (const kind of Object.keys(SAMPLE) as Kind[]) {
    describe(kind, () => {
      it('has a sample value for every key the CLI emits', () => {
        const missing = KEYS[kind].filter((key) => !(key in SAMPLE[kind]) && !NESTED[kind].includes(key));
        expect(missing, `add a sample value for ${kind}.${missing.join(', ')} in graphContract.test.ts`).toEqual([]);
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
    const graph = asTaskGraph(payload((kind, key) => (read[kind] ??= new Set()).add(key)));
    expect(typeof graph).not.toBe('string');
    for (const kind of KINDS) {
      const unknown = [...(read[kind] ?? [])].filter((key) => !KEYS[kind].includes(key) && !(key in Array.prototype));
      expect(unknown, `${kind}: the parser reads ${unknown.join(', ')}, which the CLI does not emit`).toEqual([]);
    }
  });
});
