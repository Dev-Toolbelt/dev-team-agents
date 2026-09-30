// A stand-in for `devteam notifications watch --json`, run as `node fake-watch.mjs <mode> …`.
//
// Modes:
//   stream  — one notification, `ready`, then waits for stdin to close and ends with
//             {"event":"end","reason":"stdin-closed"}, exactly like the real CLI.
//   garbage — prints a non-JSON line, then waits; the reader must kill it.
//   exit3   — writes an environment error to stderr and exits 3.
//   argv    — prints its own argv as one event, then ends.
const mode = process.argv[2];
const out = (event) => process.stdout.write(JSON.stringify({ ok: true, ...event }) + '\n');

if (mode === 'argv') {
  out({ event: 'argv', argv: process.argv.slice(3) });
  process.exit(0);
}
if (mode === 'exit3') {
  process.stderr.write('devteam: error: the store needs a layout migration first\n');
  process.exit(3);
}
if (mode === 'garbage') {
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
