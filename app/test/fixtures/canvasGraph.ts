/**
 * Builders for the `devteam tasks graph` payload (schema 1) the canvas tests render. One
 * project with two sessions: `s1` is active, has a traced turn whose top-level agent spawned two
 * sub-agents; `s2` ended and has no trace, so its agent sits flat under its main node.
 */
import type { GraphEdge, GraphGroup, GraphNode, TaskGraph } from '../../src/shared/api.js';
import { NOW } from './board.js';

export function graphGroup(overrides: Partial<GraphGroup> & Pick<GraphGroup, 'id' | 'kind'>): GraphGroup {
  return {
    parent: null,
    label: overrides.id,
    provider: null,
    status: null,
    branch: null,
    command: null,
    at: null,
    started_at: null,
    ended_at: null,
    prs: [],
    tokens: 0,
    usage_complete: true,
    session_id: null,
    ...overrides,
  };
}

export function graphNode(overrides: Partial<GraphNode> & Pick<GraphNode, 'id' | 'group'>): GraphNode {
  return {
    kind: 'agent',
    label: null,
    agent: null,
    description: null,
    persona: null,
    status: 'completed',
    model: 'sonnet',
    started_at: null,
    ended_at: null,
    duration_s: 0,
    tokens: 0,
    subtree_tokens: 0,
    usage_complete: true,
    findings: null,
    background: false,
    last_output: null,
    task_key: null,
    worktree: null,
    pr: null,
    todos: [],
    session_id: null,
    record_id: null,
    spawn_id: null,
    ...overrides,
  };
}

export function spawn(from: string, to: string): GraphEdge {
  return { id: `e:${from}>${to}`, from, to, kind: 'spawn' };
}

export const TURN = `turn:s1:${NOW - 900}`;

export function sampleGraph(): TaskGraph {
  return {
    schema: 1,
    project_id: 'proj-a',
    as_of: NOW,
    truncated: false,
    notices: ['no_trace:s2'],
    groups: [
      graphGroup({ id: 'session:s2', kind: 'session', label: 'Old session', provider: 'codex', status: 'ended', started_at: NOW - 5000, ended_at: NOW - 4000, usage_complete: false }),
      graphGroup({ id: 'session:s1', kind: 'session', label: 'Cart rework', provider: 'claude', status: 'active', branch: 'feat/cart', started_at: NOW - 1000, tokens: 9000 }),
      graphGroup({ id: TURN, kind: 'turn', parent: 'session:s1', label: '/devteam:orchestrate', command: 'orchestrate', at: NOW - 900, tokens: 9000 }),
    ],
    nodes: [
      graphNode({ id: 'main:s2', kind: 'main', group: 'session:s2', label: 'Main session', status: null, model: null }),
      graphNode({ id: 'span:s2:t1', group: 'session:s2', agent: 'qa-specialist', description: 'Check the release', model: null, usage_complete: false, task_key: 't1' }),
      graphNode({ id: 'main:s1', kind: 'main', group: 'session:s1', label: 'Orchestrator', persona: 'orchestrator', status: 'running', model: 'opus' }),
      graphNode({
        id: 'span:s1:a',
        group: TURN,
        agent: 'backend-developer',
        description: 'Build the cart API',
        started_at: NOW - 800,
        ended_at: NOW - 200,
        duration_s: 600,
        tokens: 4000,
        subtree_tokens: 7000,
        last_output: 'Cart API pushed on feat/cart',
        task_key: 't4',
        pr: { kind: 'pr', number: 42, url: 'https://github.com/o/r/pull/42', state: 'open' },
        worktree: { path: '.worktrees/feat/cart', branch: 'feat/cart' },
      }),
      graphNode({ id: 'span:s1:b', group: TURN, agent: 'frontend-developer', description: 'Cart screen', status: 'running', started_at: NOW - 850, tokens: 2000, subtree_tokens: 2000, background: true }),
      graphNode({ id: 'span:s1:a1', group: TURN, kind: 'review', agent: 'code-reviewer', description: 'Review the API', status: 'failed', started_at: NOW - 500, tokens: 1000, subtree_tokens: 1000 }),
      graphNode({ id: 'span:s1:a2', group: TURN, agent: 'backend-test-specialist', description: 'Tests', status: 'interrupted', started_at: NOW - 400, usage_complete: false }),
    ],
    edges: [
      spawn('main:s2', 'span:s2:t1'),
      spawn('main:s1', 'span:s1:a'),
      spawn('main:s1', 'span:s1:b'),
      spawn('span:s1:a', 'span:s1:a1'),
      spawn('span:s1:a', 'span:s1:a2'),
    ],
  };
}
