#!/usr/bin/env node
/**
 * A fake `devteam`, so the invocation layer can be tested against every shape the real
 * CLI can produce plus the ones it must never produce.
 *
 * The scenario is chosen by `FAKE_DEVTEAM_SCENARIO`, not by the arguments, so a test can
 * pin "this exact stdout with this exact exit code" without depending on a subcommand.
 * The received argv is echoed back inside the payload where the scenario allows it, which
 * is how `test/invoke.test.ts` asserts that `--json` was appended and that nothing was
 * passed through a shell.
 */

const scenario = process.env['FAKE_DEVTEAM_SCENARIO'] ?? 'ok';
const argv = process.argv.slice(2);

function emit(object) {
  process.stdout.write(`${JSON.stringify(object, null, 2)}\n`);
}

switch (scenario) {
  case 'ok':
    emit({ ok: true, argv, current: '3.0.0' });
    process.exit(0);
    break;

  case 'findings-payload':
    // What `devteam doctor` does: exit 1 with a complete report and `ok: false`.
    emit({ ok: false, status: 'fail', findings: [{ level: 'fail', category: 'store', message: 'no core' }], actions: [] });
    process.exit(1);
    break;

  case 'findings-error-document':
    // What a bare `DevteamError` does: exit 1 with an error document.
    emit({ ok: false, error: 'something was found and not fixed', exit_code: 1 });
    process.exit(1);
    break;

  case 'error-document-exit-zero':
    // What the CLI must never do: an error document with exit 0. Neither code's meaning
    // fits, so `toOperationResult` reports it rather than choosing a label for it.
    emit({ ok: false, error: 'an error document with exit 0', exit_code: 0 });
    process.exit(0);
    break;

  case 'list-projects':
    // Four rows, one per state `path_exists` can arrive in: true, false, absent, and a
    // non-boolean. The real CLI always sends a boolean; the point is what the *client*
    // does with the other two, which it cannot be made to produce on demand.
    emit({
      ok: true,
      current: '3.0.0',
      projects: [
        { project_id: 'p-true', path: '/a', providers: ['claude'], mode: 'link', pin: null, resolves_to: '3.0.0', path_exists: true, preferences: { auto_update: true, worktree_active: false, suppress_notifications: ['session-end', 7] } },
        { project_id: 'p-false', path: '/b', providers: [], mode: 'copy', pin: '2.9.0', resolves_to: '2.9.0', path_exists: false, preferences: { auto_update: 'yes', worktree_active: null, suppress_notifications: true } },
        { project_id: 'p-absent', path: '/c', providers: ['codex'], mode: null, pin: null, resolves_to: null },
        { project_id: 'p-junk', path: '/d', providers: [], mode: null, pin: null, resolves_to: null, path_exists: 'yes' },
      ],
    });
    process.exit(0);
    break;

  case 'catalog-malformed':
    // `catalog.py` -> `_malformed()`: the entry is listed with its path and the error, and
    // its `name` is a best-effort fallback. The summary can only count these; the per-kind
    // listing is the only place the user can see which one.
    emit({
      ok: true,
      version: '3.0.0',
      project_id: null,
      count: 2,
      skills: [
        { name: 'project-context', path: 'skills/shared/project-context/SKILL.md', version: '3.0.0', category: 'shared', description: 'ok' },
        { name: 'broken', path: 'skills/testing/broken/SKILL.md', version: '3.0.0', malformed: true, error: 'no frontmatter `name`' },
      ],
    });
    process.exit(0);
    break;

  case 'tasks-list': {
    // `devteam tasks list --json`: one project with one session and one task, plus a
    // project and a task the client must drop as unusable. The argv is echoed so a test
    // can assert what the app passed.
    const counts = { todo: 1, in_progress: 0, in_review: 1, done: 0, total: 2 };
    emit({
      ok: true,
      argv,
      generated_at: 1790000000,
      stale_after: 3600,
      ended_after: 21600,
      projects: [
        {
          project_id: 'proj-a',
          root: '/repo/a',
          providers: ['claude'],
          sessions_total: 1,
          sessions_active: 1,
          counts,
          stale: 0,
          abandoned: 0,
          with_findings: 1,
          last_activity_at: 1790000000,
          sessions: [
            {
              session_id: 's1',
              provider: 'claude',
              branch: 'main',
              cwd: '/repo/a',
              status: 'active',
              created_at: 1789990000,
              last_activity_at: 1790000000,
              ended_at: null,
              resume_command: "cd '/repo/a' && claude --resume 's1'",
              counts,
              tasks: [
                { key: 't1', content: 'ok', owner: 'main', agent_type: null, status: 'pending', column: 'todo', created_at: 1, status_since: 1, completed_at: null, durations: { pending: 5 }, stale: false, abandoned: false, review: null },
                { key: 't3', content: 'reviewed', owner: 'main', agent_type: null, status: 'in_progress', column: 'in_review', created_at: 1, status_since: 1, completed_at: null, durations: { in_progress: 5, in_review: 3 }, stale: false, abandoned: false, review: { state: 'findings', findings: 2, since: 4 } },
                { key: 't2', content: 'no column and no status', created_at: 1, status_since: 1 },
              ],
            },
          ],
        },
        { project_id: 'proj-bad', root: '/repo/bad' },
      ],
    });
    process.exit(0);
    break;
  }

  case 'usage':
    emit({ ok: false, error: '--client-schemas was given an empty value', exit_code: 2, hint: 'Pass a path.' });
    process.exit(2);
    break;

  case 'environment':
    emit({ ok: false, error: 'no active version', exit_code: 3, hint: 'Run `devteam update`.' });
    process.exit(3);
    break;

  case 'conflict':
    emit({
      ok: false,
      error: 'bind would write to this store, and the client declared via --client-schemas does not understand 1 shape(s) it uses',
      exit_code: 4,
      hint: 'Upgrade the client.',
      details: { may_write: false, unsupported: { project_layout: { store: 2, client: 1 } } },
    });
    process.exit(4);
    break;

  case 'empty-stdout':
    process.exit(0);
    break;

  case 'two-documents':
    emit({ ok: true, first: true });
    emit({ ok: true, second: true });
    process.exit(0);
    break;

  case 'json-on-stderr-only':
    process.stderr.write(`${JSON.stringify({ ok: true, wrong_channel: true })}\n`);
    process.exit(0);
    break;

  case 'warning-on-stderr':
    // The legitimate case: advisory text on stderr, one document on stdout.
    process.stderr.write('devteam: a warning that must not reach stdout\n');
    emit({ ok: true, current: '3.0.0' });
    process.exit(0);
    break;

  case 'not-json':
    process.stdout.write('Traceback (most recent call last):\n  File "x", line 1\n');
    process.exit(1);
    break;

  case 'trailing-output':
    emit({ ok: true, current: '3.0.0' });
    process.stdout.write('devteam: a stray print\n');
    process.exit(0);
    break;

  case 'not-an-object':
    process.stdout.write('[1, 2, 3]\n');
    process.exit(0);
    break;

  case 'missing-ok':
    process.stdout.write(`${JSON.stringify({ current: '3.0.0' })}\n`);
    process.exit(0);
    break;

  case 'truncated':
    process.stdout.write('{"ok": true, "projects": [');
    process.exit(0);
    break;

  case 'undocumented-exit':
    emit({ ok: true });
    process.exit(7);
    break;

  case 'hang':
    // Never exits, and ignores SIGTERM, so the hard-kill path is exercised too.
    process.on('SIGTERM', () => {});
    setInterval(() => {}, 1000);
    break;

  case 'orphan-grandchild': {
    // Answers and exits, but leaves a grandchild holding the inherited stdout/stderr pipes
    // open, so the `close` event never comes while it lives. It ends itself after 6 s so a
    // failing test does not leave it behind.
    const { spawn } = await import('node:child_process');
    const grandchild = spawn(
      process.execPath,
      ['-e', 'setTimeout(() => process.exit(0), 6000)'],
      { stdio: 'inherit', detached: false },
    );
    grandchild.unref();
    emit({ ok: true, argv, current: '3.0.0' });
    process.exit(0);
    break;
  }
  case 'linger':
    // Finishes on its own after a short while and does NOT handle SIGTERM, so a SIGTERM
    // ends it with a signal death — the difference between "let it finish" and "kill it".
    setTimeout(() => {
      emit({ ok: true, argv, finished: true });
      process.exit(0);
    }, 600);
    break;

  case 'echo-env':
    emit({ ok: true, env: process.env, argv });
    process.exit(0);
    break;

  case 'compat-compatible': {
    const store = { project: 1, project_layout: 2, registry: 1, bind_manifest: 1, credentials: 1 };
    const index = argv.indexOf('--client');
    const client = index === -1 ? null : JSON.parse(argv[index + 1]);
    emit({
      ok: true,
      json_contract: 1,
      min_app_version: null,
      store_schemas: store,
      client_schemas: client,
      may_write: true,
      unsupported: {},
    });
    process.exit(0);
    break;
  }

  case 'compat-behind': {
    // The store is ahead on `project_layout`. Exit 1: a finding, not a failure.
    const index = argv.indexOf('--client');
    const client = index === -1 ? null : JSON.parse(argv[index + 1]);
    emit({
      ok: false,
      json_contract: 1,
      min_app_version: null,
      store_schemas: { project: 1, project_layout: 9, registry: 1, bind_manifest: 1, credentials: 1 },
      client_schemas: client,
      may_write: false,
      unsupported: { project_layout: { store: 9, client: client?.project_layout ?? null } },
    });
    process.exit(1);
    break;
  }

  case 'compat-no-verdict':
    emit({ ok: true, json_contract: 1, min_app_version: null, store_schemas: {}, unsupported: {} });
    process.exit(0);
    break;

  case 'version-no-compat':
    // A program called `devteam` that is not this CLI.
    emit({ ok: true, current: '1.0.0' });
    process.exit(0);
    break;

  case 'version-with-compat':
    emit({
      ok: true,
      current: '3.0.0',
      installed: ['3.0.0'],
      core: '/tmp/core',
      compat: {
        json_contract: 1,
        min_app_version: null,
        store_schemas: { project: 1, project_layout: 2, registry: 1, bind_manifest: 1, credentials: 1 },
      },
    });
    process.exit(0);
    break;

  default:
    process.stderr.write(`fake-devteam: unknown scenario ${scenario}\n`);
    process.exit(64);
}
