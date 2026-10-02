# Diagnosing the Windows CI job: one module at a time, stacks dumped before the timeout

**Origin:** driving the `Python 3.x (windows-latest)` job back to green | 2026-10-02
**Tags:** windows, CI, windows-latest, hang, timeout, faulthandler, dump_traceback_later, temporary branch, gh api, job logs, subtests, unittest, set +e

> A hanging Windows job shows only dots and then "The operation was canceled": no test name, no stack. A temporary branch that runs each module under its own deadline, with `faulthandler` set to dump every thread before that deadline, names the hang in one round.

---

## Why the normal job tells you nothing

- `.github/scripts/ci/03-python.sh` runs `python3 -m unittest discover -s tests -t tests` without `-v` on purpose, so a hang leaves a row of dots and the job's own timeout kills it.
- Mapping the dot position back to a test id (by listing the suite in loader order locally) is only approximate: a failing subtest prints its own `F`, so every later position shifts.
- Job logs are fetchable only after the job ends. To read a hung job, cancel the run (`gh run cancel <id>`), wait a few seconds, then `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` (a 404 or `BlobNotFound` means it is not ready yet). `gh run view --log-failed` returns nothing while the run is still in progress.

## The workflow that worked

A throwaway branch with a throwaway workflow (`on: push: branches: [<that branch>]`, since `ci.yml` only runs on `main`, tags and PRs), deleted afterwards:

```bash
set +e                      # GitHub's bash step runs with -e: one failing module would end the loop
cd tests
for f in test_*.py; do
  m="${f%.py}"
  timeout 300 python3 -X faulthandler -c "import faulthandler, sys, unittest; faulthandler.dump_traceback_later(250, exit=True); unittest.main(module=None, argv=['unittest', sys.argv[1]])" "$m" > "../$m.out" 2>&1
  code=$?                   # capture before any other command: PIPESTATUS/$? are overwritten
  echo "MODULE-EXIT $m $code $(grep -aE '^(Ran|OK|FAILED)' "../$m.out" | tr '\n' ' ')"
  [ "$code" -ne 0 ] && sed -n '/^======/,$p' "../$m.out" | head -n 200
done
```

- `dump_traceback_later(…, exit=True)` fires before `timeout` kills the process, so the log holds every thread's stack: the hung test is the frame under `unittest/case.py` in the main thread.
- A step that also runs the whole suite in one process catches what only shows up when modules share a process (leftover locks, threads).
- A full Windows run takes about 16 minutes. Run only the affected modules for each fix, and the full suite once at the end.

## Reading the log

- Strip the timestamp prefix and the CRLFs first (`cut -c30- | tr -d '\r'`), or `grep`/`awk` miss lines that look fine on screen.
- `CalledProcessError` hides the child's stderr. When a subprocess fails only on Windows, run it directly in a workflow step (`bash -x <script>`) to see why.

## References

- `.github/workflows/ci.yml` (`python` job matrix) and `.github/scripts/ci/03-python.sh`
- `tests/devteam_support.py`: `requires_bash()`, `requires_posix_modes`, the policy for what is skipped on Windows
- `docs/wiki/windows/`: what these runs found
