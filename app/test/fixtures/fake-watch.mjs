// A stand-in for `devteam notifications watch --json`, run as `node fake-watch.mjs <mode> …`.
//
// Modes:
//   stream  — one notification, `ready`, then waits for stdin to close and ends with
//             {"event":"end","reason":"stdin-closed"}, exactly like the real CLI.
//   garbage — prints a non-JSON line, then waits; the reader must kill it.
//   exit3   — writes an environment error to stderr and exits 3.
//   error3  — writes the error as one `{"event":"error",…}` line and exits 3.
//   indented3 — writes an indented, multi-line error document and exits 3.
//   orphan  — exits 0 at once but leaves a grandchild holding the inherited pipes open.
//   tasks   — `tasks watch`: two project snapshots, a removal, `ready`, then waits for stdin to close.
//   argv    — prints its own argv as one event, then ends.
const mode = process.argv[2];
const out = (event) => process.stdout.write(JSON.stringify({ ok: true, ...event }) + '\n');

if (mode === 'argv') {
  out({ event: 'argv', argv: process.argv.slice(3) });
  process.exit(0);
}
if (mode === 'orphan') {
  const { spawn } = await import('node:child_process');
  spawn(process.execPath, ['-e', 'setTimeout(() => process.exit(0), 6000)'], { stdio: 'inherit' }).unref();
  out({ event: 'ready', projects: 0 });
  process.exit(0);
}
if (mode === 'exit3') {
  process.stderr.write('devteam: error: the store needs a layout migration first\n');
  process.exit(3);
}
// The CLI's failure under --json, as the stream's own last line.
if (mode === 'error3') {
  out({ ok: false, event: 'error', error: 'the store needs a layout migration first', exit_code: 3 });
  process.exit(3);
}
// A pre-fix CLI: an indented error document (not JSON line by line), then exit 3.
if (mode === 'indented3') {
  process.stdout.write('{\n  "error": "the store needs a layout migration first",\n  "ok": false\n}\n');
  process.exit(3);
}
if (mode === 'tasks') {
  const counts = { todo: 1, in_progress: 0, in_review: 0, done: 0, total: 1 };
  const project = (id) => ({
    project_id: id,
    root: `/repo/${id}`,
    providers: ['claude'],
    sessions_total: 1,
    sessions_active: 1,
    counts,
    stale: 0,
    abandoned: 0,
    with_findings: 0,
    last_activity_at: 1790000000,
    sessions: [],
  });
  out({ event: 'snapshot', project: project('proj-a') });
  out({ event: 'snapshot', project: project('proj-b') });
  out({ event: 'snapshot', project: { project_id: 'proj-b', removed: true } });
  out({ event: 'ready' });
  process.stdin.on('data', () => undefined);
  process.stdin.on('end', () => {
    out({ event: 'end', reason: 'stdin-closed' });
    process.exit(0);
  });
} else if (mode === 'garbage') {
  process.stdout.write('this is not json\n');
  setInterval(() => undefined, 1000);
} else {
  out({
    event: 'notification',
    notification: {
      id: '1790000000-42-7',
      ts: 1790000000,
      project_id: 'proj-1',
      session_id: 's1',
      level: 'critical',
      code: 'context.critical',
      message: 'Context window at ≈65%.',
      dedupe_key: 'context.critical:s1',
      expires_at: 0,
      seen: false,
    },
  });
  out({ event: 'ready', projects: 1 });
  process.stdin.on('data', () => undefined);
  process.stdin.on('end', () => {
    out({ event: 'end', reason: 'stdin-closed' });
    process.exit(0);
  });
}
