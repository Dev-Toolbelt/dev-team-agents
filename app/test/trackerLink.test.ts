/**
 * Tracker links: the validator that guards the one path to `shell.openExternal`, the
 * snapshot lookup, the `openTaskLink` IPC around them, and the parser's older-CLI fallbacks.
 */
import { describe, expect, it, onTestFinished, vi } from 'vitest';

import { asBoardProject } from '../src/cli/operations.js';
import { createLinkRateLimiter, validateTrackerLink, type TrackerLinkInput } from '../src/main/security.js';
import { resolveTaskLink } from '../src/main/taskBoard.js';
import type * as IpcModule from '../src/main/taskBoardIpc.js';
import type * as ApiModule from '../src/shared/api.js';
import type { BoardLinkHost, BoardLinkKind, BoardProject } from '../src/shared/api.js';
import { boardProject, boardSession, boardTask } from './fixtures/board.js';

const HOSTS: readonly BoardLinkHost[] = [
  { host: 'github.com', kinds: ['github_pr', 'github_issue'] },
  { host: 'gitlab.example.com', kinds: ['gitlab_mr'] },
  { host: 'jira.example.com', kinds: ['jira'] },
];

function check(url: string, kind: BoardLinkKind, identity: string, linkHosts: readonly BoardLinkHost[] = HOSTS) {
  const input: TrackerLinkInput = { url, kind, identity, linkHosts };
  return validateTrackerLink(input);
}

describe('validateTrackerLink', () => {
  it('accepts a valid link of each kind and returns the canonical URL', () => {
    const cases: [string, BoardLinkKind, string][] = [
      ['https://github.com/acme/shop/pull/45', 'github_pr', '45'],
      ['https://github.com/acme/shop/issues/7', 'github_issue', 'acme/shop#7'],
      ['https://gitlab.example.com/acme/shop/-/merge_requests/12', 'gitlab_mr', '12'],
      ['https://gitlab.example.com/acme/team/sub/shop/-/merge_requests/12', 'gitlab_mr', '12'],
      ['https://jira.example.com/browse/PROJ-12', 'jira', 'PROJ-12'],
    ];
    for (const [url, kind, identity] of cases) {
      const verdict = check(url, kind, identity);
      expect(verdict, url).toMatchObject({ ok: true, canonical: url });
    }
  });

  it('pins the Jira path shape to <base_path>/browse/KEY-N, with the host root as the default', () => {
    expect(check('https://jira.example.com/jira/browse/PROJ-12', 'jira', 'PROJ-12')).toMatchObject({ ok: false });
    const ctx: BoardLinkHost[] = [{ host: 'jira.corp', kinds: ['jira'], base_path: '/jira' }];
    expect(check('https://jira.corp/jira/browse/PROJ-12', 'jira', 'PROJ-12', ctx)).toMatchObject({ ok: true });
    expect(check('https://jira.corp/browse/PROJ-12', 'jira', 'PROJ-12', ctx)).toMatchObject({ ok: false });
    expect(check('https://jira.corp/other/browse/PROJ-12', 'jira', 'PROJ-12', ctx)).toMatchObject({ ok: false });
    expect(check('https://jira.corp/jira/browse/PROJ-13', 'jira', 'PROJ-12', ctx)).toMatchObject({ ok: false });
    const gh: BoardLinkHost[] = [{ host: 'github.com', kinds: ['github_pr'], base_path: '/x' }];
    expect(check('https://github.com/acme/shop/pull/45', 'github_pr', '45', gh)).toMatchObject({ ok: true });
    expect(check('https://github.com/x/acme/shop/pull/45', 'github_pr', '45', gh)).toMatchObject({ ok: false });
    const verdict = check('https://tracker.example.org/browse/PROJ-12', 'jira', 'PROJ-12', [{ host: 'tracker.example.org', kinds: ['jira'] }]);
    expect(verdict).toMatchObject({ ok: true });
  });

  it('refuses a scheme other than https', () => {
    for (const url of [
      'http://github.com/acme/shop/pull/45',
      'javascript:alert(1)',
      'file:///etc/passwd',
      'ftp://github.com/acme/shop/pull/45',
    ]) {
      expect(check(url, 'github_pr', '45'), url).toMatchObject({ ok: false });
    }
  });

  it('refuses a host off the allow-list', () => {
    expect(check('https://evil.example/acme/shop/pull/45', 'github_pr', '45')).toMatchObject({ ok: false });
    expect(check('https://github.com/acme/shop/pull/45', 'github_pr', '45', [])).toMatchObject({ ok: false });
  });

  it('refuses a host that is allowed only for another kind', () => {
    // A GitLab-shaped path on the GitHub host, a Jira-shaped path on the GitHub host, a PR on the Jira host.
    expect(check('https://github.com/acme/shop/-/merge_requests/12', 'gitlab_mr', '12')).toMatchObject({ ok: false });
    expect(check('https://github.com/browse/PROJ-12', 'jira', 'PROJ-12')).toMatchObject({ ok: false });
    expect(check('https://jira.example.com/acme/shop/pull/45', 'github_pr', '45')).toMatchObject({ ok: false });
    expect(check('https://gitlab.example.com/acme/shop/issues/3', 'github_issue', 'acme/shop#3')).toMatchObject({ ok: false });
  });

  it('refuses percent-encoding, backslashes, userinfo, ports, query, fragment and dot segments', () => {
    const bad = [
      'https://github.com/acme/shop%2Fx/pull/45',
      'https://github.com/acme/sh%6Fp/pull/45',
      'https://github.com/acme/shop/pull/45%0A',
      'https://github.com/acme\\shop/pull/45',
      'https://github.com\\@evil.tld/acme/shop/pull/45',
      'https://github.com@evil.tld/acme/shop/pull/45',
      'https://user:pw@github.com/acme/shop/pull/45',
      'https://github.com:8443/acme/shop/pull/45',
      'https://github.com/acme/shop/pull/45?x=1',
      'https://github.com/acme/shop/pull/45#frag',
      'https://github.com/acme/shop/pull/45?',
      'https://github.com/acme/../shop/pull/45',
      'https://github.com/acme/./shop/pull/45',
      'https://github.com/acme/shop/pull/45/',
      'https://github.com//acme/shop/pull/45',
    ];
    for (const url of bad) expect(check(url, 'github_pr', '45'), url).toMatchObject({ ok: false });
    expect(check('https://gitlab.example.com/acme/../shop/-/merge_requests/12', 'gitlab_mr', '12')).toMatchObject({ ok: false });
    expect(check('https://gitlab.example.com/acme/.git/-/merge_requests/12', 'gitlab_mr', '12')).toMatchObject({ ok: false });
  });

  it('refuses uppercase, trailing-dot, IDN and punycode hosts', () => {
    const hosts: BoardLinkHost[] = [
      { host: 'github.com', kinds: ['github_pr'] },
      { host: 'GitHub.com.', kinds: ['github_pr'] },
    ];
    for (const url of [
      'https://GitHub.com/acme/shop/pull/45',
      'https://github.com./acme/shop/pull/45',
      'https://gıthub.com/acme/shop/pull/45',
      'https://xn--gthub-zua.com/acme/shop/pull/45',
      'https://github.com.evil.tld/acme/shop/pull/45',
    ]) {
      expect(check(url, 'github_pr', '45', hosts), url).toMatchObject({ ok: false });
    }
    // Punycode is accepted only when the configured host literally is that punycode name.
    const pony = 'https://xn--gthub-zua.com/acme/shop/pull/45';
    expect(check(pony, 'github_pr', '45', [{ host: 'xn--gthub-zua.com', kinds: ['github_pr'] }])).toMatchObject({ ok: true });
  });

  it('refuses a 3000-character string and an empty one', () => {
    const long = `https://github.com/acme/shop/pull/45${'a'.repeat(3000)}`;
    expect(check(long, 'github_pr', '45')).toMatchObject({ ok: false });
    expect(check('', 'github_pr', '45')).toMatchObject({ ok: false });
    expect(check('not a url', 'github_pr', '45')).toMatchObject({ ok: false });
  });

  it('refuses a number or key that is not the one the snapshot entry names', () => {
    expect(check('https://github.com/acme/shop/pull/46', 'github_pr', '45')).toMatchObject({ ok: false });
    expect(check('https://github.com/acme/shop/issues/8', 'github_issue', 'acme/shop#7')).toMatchObject({ ok: false });
    expect(check('https://github.com/acme/other/issues/7', 'github_issue', 'acme/shop#7')).toMatchObject({ ok: false });
    expect(check('https://gitlab.example.com/acme/shop/-/merge_requests/13', 'gitlab_mr', '12')).toMatchObject({ ok: false });
    expect(check('https://jira.example.com/browse/PROJ-13', 'jira', 'PROJ-12')).toMatchObject({ ok: false });
    // A PR path for an issue kind, and the reverse.
    expect(check('https://github.com/acme/shop/pull/7', 'github_issue', 'acme/shop#7')).toMatchObject({ ok: false });
    expect(check('https://github.com/acme/shop/issues/45', 'github_pr', '45')).toMatchObject({ ok: false });
    // Leading zeros are not a number.
    expect(check('https://github.com/acme/shop/pull/045', 'github_pr', '45')).toMatchObject({ ok: false });
  });
});

describe('createLinkRateLimiter', () => {
  it('allows one open per 750 ms and ten per minute, and a refusal does not count', () => {
    let t = 1_000_000;
    const may = createLinkRateLimiter(() => t);
    expect(may()).toBe(true);
    t += 749;
    expect(may()).toBe(false);
    t += 1;
    expect(may()).toBe(true);
    for (let i = 0; i < 8; i += 1) {
      t += 750;
      expect(may(), `open ${i + 3}`).toBe(true);
    }
    // Ten opens within the minute; the eleventh waits for the window.
    t += 750;
    expect(may()).toBe(false);
    t += 60_000;
    expect(may()).toBe(true);
  });
});

describe('resolveTaskLink', () => {
  const task = boardTask({
    key: 't1',
    column: 'pr_created',
    pr: { kind: 'pr', number: 45, url: 'https://github.com/acme/shop/pull/45', state: 'open' },
    refs: [
      { system: 'jira', key: 'PROJ-12', url: 'https://jira.example.com/browse/PROJ-12' },
      { system: 'github', key: 'acme/shop#7', url: 'https://github.com/acme/shop/issues/7' },
    ],
  });
  const project = boardProject({
    link_hosts: HOSTS,
    sessions: [
      boardSession({
        session_id: 's1',
        tasks: [task],
        prs: [{ kind: 'mr', number: 12, url: 'https://gitlab.example.com/acme/shop/-/merge_requests/12', state: 'open', head: 'feat/x' }],
      }),
    ],
  });
  const EXPECT: Record<string, string> = { 't1:pr:0': '45', 't1:ref:0': 'PROJ-12', 't1:ref:1': 'acme/shop#7', 'null:pr:0': '12' };
  const ask = (taskKey: string | null, type: 'pr' | 'ref', index: number, session = 's1', expect?: string) => ({
    project_id: 'proj-a',
    session_id: session,
    task_key: taskKey,
    link: { type, index, expect: expect ?? EXPECT[`${taskKey}:${type}:${index}`] ?? 'none' },
  });

  it('refuses a link whose number or key is not the one the badge showed', () => {
    expect(resolveTaskLink(project, ask('t1', 'pr', 0, 's1', '46'))).toBeNull();
    expect(resolveTaskLink(project, ask('t1', 'ref', 0, 's1', 'acme/shop#7'))).toBeNull();
    expect(resolveTaskLink(project, ask('t1', 'ref', 1, 's1', 'ACME/shop#7'))).toMatchObject({ identity: 'acme/shop#7' });
  });

  it('resolves a task PR, a task ref and a session PR to the snapshot entry', () => {
    expect(resolveTaskLink(project, ask('t1', 'pr', 0))).toMatchObject({ kind: 'github_pr', identity: '45', url: task.pr!.url });
    expect(resolveTaskLink(project, ask('t1', 'ref', 0))).toMatchObject({ kind: 'jira', identity: 'PROJ-12' });
    expect(resolveTaskLink(project, ask('t1', 'ref', 1))).toMatchObject({ kind: 'github_issue', identity: 'acme/shop#7' });
    expect(resolveTaskLink(project, ask(null, 'pr', 0))).toMatchObject({ kind: 'gitlab_mr', identity: '12' });
    expect(resolveTaskLink(project, ask('t1', 'pr', 0))!.linkHosts).toEqual(HOSTS);
  });

  it('returns null for every miss', () => {
    expect(resolveTaskLink(undefined, ask('t1', 'pr', 0))).toBeNull();
    expect(resolveTaskLink(project, ask('t1', 'pr', 0, 'nope'))).toBeNull();
    expect(resolveTaskLink(project, ask('nope', 'pr', 0))).toBeNull();
    expect(resolveTaskLink(project, ask('t1', 'pr', 1))).toBeNull();
    expect(resolveTaskLink(project, ask('t1', 'ref', 2))).toBeNull();
    expect(resolveTaskLink(project, ask(null, 'pr', 1))).toBeNull();
    expect(resolveTaskLink(project, ask(null, 'ref', 0))).toBeNull();
    const noPr = boardProject({ sessions: [boardSession({ session_id: 's1', tasks: [boardTask({ key: 't1' })] })] });
    expect(resolveTaskLink(noPr, ask('t1', 'pr', 0))).toBeNull();
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
const REQUEST = { project_id: 'proj-a', session_id: 's1', task_key: 't1', link: { type: 'pr', index: 0, expect: '45' } };
const GOOD = { url: 'https://github.com/acme/shop/pull/45', kind: 'github_pr', identity: '45', linkHosts: HOSTS } as const;

describe('openTaskLink IPC', () => {
  async function setup(overrides: Partial<IpcModule.TaskBoardIpcDeps> = {}) {
    const mod = await loadIpc();
    const openExternal = vi.fn<(url: string, options: { activate: boolean }) => Promise<void>>(() => Promise.resolve());
    const log = vi.fn();
    let now = 5_000_000;
    const deps: IpcModule.TaskBoardIpcDeps = {
      trustedRenderer: TRUSTED_RENDERER,
      feed: () => ({ status: 'live', detail: null, projects: [] }),
      refresh: () => Promise.resolve({ status: 'live', detail: null, projects: [] }),
      boardSettings: () => Promise.resolve({ staleAfterMinutes: 60, doneRetentionDays: 7 }),
      saveBoardSettings: (settings) => Promise.resolve(settings),
      linkFor: () => GOOD,
      openExternal: (url) => openExternal(url, { activate: true }),
      appWindowFocused: () => true,
      now: () => now,
      log,
      ...overrides,
    };
    mod.registerTaskBoardIpc(deps);
    const open = mod.handlers.get(mod.CHANNELS.openTaskLink)!;
    return { open, openExternal, log, advance: (ms: number) => (now += ms) };
  }

  it('opens the canonical URL from the snapshot exactly once, with activate:true', async () => {
    const { open, openExternal } = await setup();
    expect(await open(TRUSTED, REQUEST)).toEqual({ ok: true });
    expect(openExternal).toHaveBeenCalledTimes(1);
    expect(openExternal).toHaveBeenCalledWith('https://github.com/acme/shop/pull/45', { activate: true });
  });

  it('refuses a request that carries a URL or any key beyond the documented shape', async () => {
    const { open, openExternal } = await setup();
    const bad = [
      { ...REQUEST, url: 'https://evil.example/' },
      { ...REQUEST, link: { type: 'pr', index: 0, expect: '45', url: 'https://evil.example/' } },
      { ...REQUEST, link: { type: 'pr', index: 0 } },
      { ...REQUEST, link: { type: 'pr', index: 0, expect: '' } },
      { ...REQUEST, link: { type: 'pr', index: 0, expect: 45 } },
      { project_id: 'proj-a', session_id: 's1', task_key: 't1', link: 'https://evil.example/' },
      'https://evil.example/',
      null,
      [],
      { ...REQUEST, link: { type: 'url', index: 0, expect: '45' } },
      { ...REQUEST, link: { type: 'pr', index: -1, expect: '45' } },
      { ...REQUEST, link: { type: 'pr', index: 64, expect: '45' } },
      { ...REQUEST, link: { type: 'pr', index: 1.5, expect: '45' } },
      { ...REQUEST, session_id: '' },
      { ...REQUEST, session_id: 'a'.repeat(513) },
      { ...REQUEST, project_id: 'a\nb' },
      { ...REQUEST, task_key: 7 },
    ];
    for (const raw of bad) expect(await open(TRUSTED, raw), JSON.stringify(raw)).toMatchObject({ ok: false });
    expect(openExternal).not.toHaveBeenCalled();
  });

  it('refuses when the link is not in main\'s own snapshot', async () => {
    const { open, openExternal, log } = await setup({ linkFor: () => null });
    expect(await open(TRUSTED, REQUEST)).toMatchObject({ ok: false });
    expect(openExternal).not.toHaveBeenCalled();
    expect(log).toHaveBeenCalledWith(expect.stringMatching(/refused/));
  });

  it('refuses a snapshot link that fails validation', async () => {
    const { open, openExternal } = await setup({ linkFor: () => ({ ...GOOD, url: 'https://evil.example/acme/shop/pull/45' }) });
    expect(await open(TRUSTED, REQUEST)).toMatchObject({ ok: false });
    expect(openExternal).not.toHaveBeenCalled();
  });

  it('refuses an untrusted sender', async () => {
    const { open, openExternal } = await setup();
    const foreign = { senderFrame: { url: 'https://evil.example/', parent: null } };
    expect(() => open(foreign, REQUEST)).toThrow(/refused/);
    expect(openExternal).not.toHaveBeenCalled();
  });

  it('refuses when the focused window is not one of this app\'s own', async () => {
    const { open, openExternal } = await setup({ appWindowFocused: () => false });
    expect(await open(TRUSTED, REQUEST)).toMatchObject({ ok: false });
    expect(openExternal).not.toHaveBeenCalled();
  });

  it('rate-limits to one open per 750 ms and ten per minute on a fake clock', async () => {
    const { open, openExternal, advance } = await setup();
    expect(await open(TRUSTED, REQUEST)).toEqual({ ok: true });
    advance(100);
    expect(await open(TRUSTED, REQUEST)).toEqual({ ok: false, message: 'Links are opening too fast. Wait a moment and try again.' });
    expect(openExternal).toHaveBeenCalledTimes(1);
    for (let i = 0; i < 9; i += 1) {
      advance(750);
      expect(await open(TRUSTED, REQUEST), `open ${i + 2}`).toEqual({ ok: true });
    }
    advance(750);
    expect(await open(TRUSTED, REQUEST)).toMatchObject({ ok: false });
    expect(openExternal).toHaveBeenCalledTimes(10);
    advance(60_000);
    expect(await open(TRUSTED, REQUEST)).toEqual({ ok: true });
  });

  it('answers ok:false, without leaking the error, when the system cannot open it; and never logs the URL', async () => {
    const { open, log } = await setup({ openExternal: () => Promise.reject(new Error('secret detail')) });
    const answer = await open(TRUSTED, REQUEST);
    expect(answer).toMatchObject({ ok: false });
    expect(JSON.stringify(answer)).not.toContain('secret detail');
    for (const [message] of log.mock.calls) expect(String(message)).not.toContain('github.com/acme');
  });
});

// ── parser ────────────────────────────────────────────────────────────────────

describe('asBoardProject — links', () => {
  /* eslint-disable @typescript-eslint/no-explicit-any */
  function raw(): Record<string, any> {
    return JSON.parse(JSON.stringify(boardProject({ sessions: [boardSession({ tasks: [boardTask({ key: 'a' })] })] }))) as Record<string, any>;
  }
  /* eslint-enable @typescript-eslint/no-explicit-any */

  it('reads pr, refs, prs, link_hosts and pr_created from a current CLI', () => {
    const body = raw();
    body.link_hosts = HOSTS;
    body.counts.pr_created = 1;
    body.sessions[0].counts.pr_created = 1;
    body.sessions[0].prs = [{ kind: 'mr', number: 3, url: 'https://gitlab.example.com/a/b/-/merge_requests/3', state: 'merged', head: 'x' }];
    body.sessions[0].tasks[0].pr = { kind: 'pr', number: 45, url: 'https://github.com/acme/shop/pull/45', state: 'open' };
    body.sessions[0].tasks[0].refs = [{ system: 'jira', key: 'PROJ-1', url: 'https://jira.example.com/browse/PROJ-1' }];
    const parsed = asBoardProject(body) as BoardProject;
    expect(parsed.link_hosts).toEqual(HOSTS);
    expect(parsed.counts.pr_created).toBe(1);
    expect(parsed.sessions[0]!.prs).toHaveLength(1);
    expect(parsed.sessions[0]!.tasks[0]!.pr).toMatchObject({ number: 45, kind: 'pr' });
    expect(parsed.sessions[0]!.tasks[0]!.refs).toHaveLength(1);
  });

  it('reads a valid jira base_path, ignores it on other kinds, and drops a jira entry with a malformed one', () => {
    const body = raw();
    body.link_hosts = [
      { host: 'jira.corp', kinds: ['jira'], base_path: '/jira' },
      { host: 'github.com', kinds: ['github_pr'], base_path: '/x' },
      { host: 'bad1.corp', kinds: ['jira'], base_path: '/a/../b' },
      { host: 'bad2.corp', kinds: ['jira'], base_path: 'jira' },
      { host: 'bad3.corp', kinds: ['jira'], base_path: '/a b' },
      { host: 'bad4.corp', kinds: ['jira'], base_path: '/jira/' },
      { host: 'bad5.corp', kinds: ['jira'], base_path: 7 },
      { host: 'root.corp', kinds: ['jira'], base_path: '' },
    ];
    const parsed = asBoardProject(body) as BoardProject;
    expect(parsed.link_hosts).toEqual([
      { host: 'jira.corp', kinds: ['jira'], base_path: '/jira' },
      { host: 'github.com', kinds: ['github_pr'] },
      { host: 'root.corp', kinds: ['jira'] },
    ]);
  });

  it('degrades an older CLI (no pr, refs, prs, link_hosts, pr_created) to null, [] and 0', () => {
    const body = raw();
    delete body.link_hosts;
    delete body.counts.pr_created;
    delete body.sessions[0].counts.pr_created;
    delete body.sessions[0].prs;
    delete body.sessions[0].tasks[0].pr;
    delete body.sessions[0].tasks[0].refs;
    const parsed = asBoardProject(body) as BoardProject;
    expect(parsed.link_hosts).toEqual([]);
    expect(parsed.counts.pr_created).toBe(0);
    expect(parsed.sessions[0]!.counts.pr_created).toBe(0);
    expect(parsed.sessions[0]!.prs).toEqual([]);
    expect(parsed.sessions[0]!.tasks[0]!.pr).toBeNull();
    expect(parsed.sessions[0]!.tasks[0]!.refs).toEqual([]);
  });

  it('drops malformed pr and ref entries instead of trusting them', () => {
    const body = raw();
    body.sessions[0].prs = [{ kind: 'x', number: 1, url: 'u', state: 'open' }, { kind: 'pr', number: 0, url: 'u', state: 'open' }, 'str', null];
    body.sessions[0].tasks[0].pr = { kind: 'pr', number: 'forty', url: 'u', state: 'open' };
    body.sessions[0].tasks[0].refs = [{ system: 'svn', key: 'a', url: 'u' }, { system: 'jira', key: 'A-1' }, 5];
    const parsed = asBoardProject(body) as BoardProject;
    expect(parsed.sessions[0]!.prs).toEqual([]);
    expect(parsed.sessions[0]!.tasks[0]!.pr).toBeNull();
    expect(parsed.sessions[0]!.tasks[0]!.refs).toEqual([]);
  });

  it('keeps an unknown column in the column its status implies, with pr_created absent', () => {
    const body = raw();
    body.sessions[0].tasks[0] = { ...body.sessions[0].tasks[0], column: 'archived', status: 'completed' };
    const parsed = asBoardProject(body) as BoardProject;
    expect(parsed.sessions[0]!.tasks[0]!.column).toBe('done');
  });

  it('accepts the pr_created column from the CLI', () => {
    const body = raw();
    body.sessions[0].tasks[0] = { ...body.sessions[0].tasks[0], column: 'pr_created', status: 'completed' };
    expect((asBoardProject(body) as BoardProject).sessions[0]!.tasks[0]!.column).toBe('pr_created');
  });
});
