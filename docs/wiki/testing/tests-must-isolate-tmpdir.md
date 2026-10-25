# Tests Must Isolate TMPDIR

**Origin:** context-delivery branch-overlap and repair-ledger tests | 2026-10-25
**Tags:** TMPDIR, tempfile, sentinel file, devteam-branch-overlap, mock.patch.dict, shared temp directory, post-edit hook, test isolation

> Read this first: a test that writes into the real `$TMPDIR` leaves files that every repository on the machine reads. A stale sentinel there pushed every repo's post-edit hook from about 4 ms to about 48 ms.

---

## What it is
`$TMPDIR` is shared by every repository and session on the machine. Code that keeps state there (sentinels, markers, caches) is shared too, so a test that writes to it changes the behavior of unrelated repositories.

## How it works
1. `branch_overlap` and the repair code write sentinel files to `$TMPDIR/devteam-branch-overlap/`.
2. The post-edit hooks check those sentinels on every run. A sentinel that exists sends the hook down its slow path.
3. Tests that exercised those functions wrote sentinels into the real directory and left them behind.
4. Each repository's post-edit hook then took the slow path (about 48 ms instead of about 4 ms) until the stale files were removed by hand.
5. Isolate the test instead. Point `TMPDIR` at a test-owned directory for the whole test:
   - In-process: `mock.patch.dict(os.environ, {"TMPDIR": tmp_dir})`, using a `tempfile.TemporaryDirectory()` per test.
   - Subprocess: pass `env={**os.environ, "TMPDIR": tmp_dir}` to the child.

## Gotchas
- Patching `tempfile.gettempdir` alone is not enough when the code reads `TMPDIR` directly. Patch the environment the code reads.
- A subprocess inherits the parent's environment only if the test passes it. Setting `TMPDIR` in the test process does not reach a hook started with `subprocess.run`.
- After a test run, check the real directory: `ls "$TMPDIR/devteam-branch-overlap/" 2>/dev/null`. Any file there came from a test that was not isolated.
- Removing stale sentinels is a manual fix. Do not add a deletion step to the hook to hide the leak.

## References
- `scripts/lib/devteam/branch_overlap.py`
- `scripts/hooks/post-tool-use/04-branch-overlap.sh`
- `tests/` cases for branch overlap and repairs
