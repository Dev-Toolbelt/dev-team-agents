# A Git Bash script's children are not in its Windows process tree

**Origin:** plugin timeout test taking the full `sleep 5` on the Windows runner | 2026-10-02
**Tags:** windows, git bash, MSYS2, process tree, taskkill /T, TerminateProcess, Job Object, CreateJobObjectW, AssignProcessToJobObject, TerminateJobObject, timeout, plugin, pipe

> Killing a script run under Git Bash, even with `taskkill /F /T`, leaves the commands it started running. They keep the output pipes open, so a "timed out" run still waits for them. Only a Job Object reaches them.

---

## What was measured

On `windows-latest`, `bash.exe slow.sh` (where the script runs `sleep 5`) was started from Python and given `taskkill /F /T /PID <bash>` after 1 s. `tasklist` showed `sleep.exe` running, and taskkill reported that **only** the bash pid was terminated. `communicate()` then returned 5 s after the start, when `sleep` finished on its own. `CREATE_NEW_PROCESS_GROUP` made no difference. The MSYS2 runtime starts a script's commands so that Windows does not record them as children of that bash. A plain `TerminateProcess` (`Popen.kill`) has the same gap.

## The fix

`plugins._windows_job` creates a Job Object and assigns the script's process to it right after `Popen`. Every process a job member creates joins the job, so on timeout `TerminateJobObject` ends all of them, and `taskkill /T` stays only as a fallback. There is also no TERM grace on Windows, because there is no TERM to deliver.

## Gotchas

- Assignment happens after the process starts. A child created in that window would escape. Git Bash's startup is far slower than the assignment, but `CREATE_SUSPENDED` plus a resume would close the gap if it ever matters.
- Close the job handle when the run ends (`_close_job`). The job is created without `KILL_ON_JOB_CLOSE`, so closing it never kills a script that finished normally.

## References

- `scripts/lib/devteam/plugins.py`: `_windows_job`, `_close_job`, `_kill_group`, `_spawn`
- `tests/test_plugins.py`: `RunTest.test_a_timeout_kills_the_script_and_reports_it`, with the same 4.5 s bound on every OS
