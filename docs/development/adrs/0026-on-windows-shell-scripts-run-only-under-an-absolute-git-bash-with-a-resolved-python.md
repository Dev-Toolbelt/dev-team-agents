# ADR-0026: On Windows, shell scripts run only under an absolute Git Bash with a resolved Python

**Date:** 2026-10-02  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers

## Context

ADR-0009 made python3 the CLI runtime and kept hooks, installers and helpers in bash. Running that split on Windows (the cross-OS / cross-provider audit of 2026-10-02, findings proven on the GitHub `windows-latest` runner) exposed three facts that make the POSIX assumptions wrong there:

- **A bare `bash` is not Git Bash.** On the runner `shutil.which("bash")` returned `C:\Program Files\Git\usr\bin\bash.EXE`, but `subprocess.run(["bash", ...])` follows the CreateProcess search order (System32 before PATH) and started `C:\Windows\System32\bash.exe`, the WSL launcher ("Windows Subsystem for Linux has no installed distributions"). The Microsoft Store alias under `WindowsApps` is the same kind of stub.
- **`python3` is often missing or broken in Git Bash.** The shipped shell scripts call `python3` (or gate on `command -v python3`) in about 110 places. On Windows `python3` is frequently absent or is the Store stub that exits 9009, while `python` or `py -3` work. Python also defaults to cp1252 there, so inline python reading UTF-8 sources crashes.
- **Git Bash children are outside the script's Windows process tree.** The MSYS2 runtime starts them, so `taskkill /F /T /PID <bash>` ended only bash; a `sleep.exe` it launched kept the plugin's stdout pipe open until it finished, defeating the plugin timeout.

## Decision

1. **bash is resolved, never named.** Every shell script run from Python (plugin interpreter, provider installers and their tool check) and every Codex hook command uses `devteam.shells.bash_path()`. On POSIX that is `shutil.which("bash")`. On Windows it is `find_git_bash()`: an absolute path only, rejecting anything under `\windows\system32\` (WSL launcher) or `\windowsapps\` (Store alias), falling back to the Git for Windows default folders (`%ProgramFiles%`, `%ProgramFiles(x86)%`, `%LOCALAPPDATA%\Programs`). The Codex hook command on Windows is `""<absolute Git Bash>" -c "<root walk>""` (`codex_hooks_merge.windows_command`).
2. **Shell scripts get a working `python3` from `scripts/lib/python.sh`**, sourced by the hook dispatchers, the installers, update/rollback/render-provider/check-updates, telemetry-send and the python-using `scripts/lib` libraries. It resolves `$DEVTEAM_PYTHON` (the CLI passes its own `sys.executable` to installers), then `python3`, `python`, `py -3`, each required to be Python 3.9+, and defines an exported `python3` shell function only when the real `python3` is missing or broken. The result is cached in exported variables so children skip the probe. On Windows it also exports `PYTHONUTF8=1`. On macOS/Linux with `python3` on PATH it probes nothing and defines nothing.
3. **Plugin processes are ended through a Windows Job Object.** Right after `Popen` the plugin script is assigned to a job (`CreateJobObjectW` + `AssignProcessToJobObject`); processes it starts join the job, and a timeout calls `TerminateJobObject`. There is no TERM grace period on Windows. `taskkill /F /T` (resolved from `%SystemRoot%`, never PATH) remains only as the fallback when the job could not be created.

## Rationale

The fix sits at the three choke points where Windows diverges — choosing the interpreter, choosing `python3`, and ending a process tree — instead of at every call site. Each choke point is a no-op on macOS/Linux, so the POSIX path the project is developed and used on does not change.

## Alternatives Considered

### WSL as the Windows runtime
- **Pros**: a real Linux userland; no Git Bash quirks.
- **Cons**: an extra install most Windows users of Claude Code, opencode or Codex do not have; paths, the keychain and the provider config live on the Windows side.
- **Why rejected**: it moves the problem to path translation across two filesystems and makes WSL a prerequisite.

### Rewrite every call site to a `dta_python` function
- **Pros**: explicit; no shadowing of `python3`.
- **Cons**: about 110 edits across hooks, installers and libraries, and every future script must remember the convention or silently break on Windows.
- **Why rejected**: the exported `python3` shim gives the same result with one sourced file, and `command -v python3` gates keep working unchanged.

### `taskkill /T` to end a timed-out plugin
- **Pros**: no ctypes; one subprocess call.
- **Cons**: proven not to reach Git Bash children, which keep the output pipe open.
- **Why rejected**: it does not end the process that blocks the timeout; it survives only as the no-job fallback.

## Consequences

**Positive**: hooks, installers and plugins run on a stock Windows with Git for Windows; a broken or absent `python3` no longer disables shell scripts; plugin timeouts hold on Windows.

**Negative**: Windows requires Git for Windows and Python 3.9+. Windows-only code paths (Git Bash resolution, the Job Object, the cmd.exe quoting) cannot run on the maintainers' macOS machines and are validated only on the GitHub `windows-latest` runner, where the full Python suite takes about 16 minutes.

**Risks**:
- The Codex hook command's `cmd /C` outer-quote form (`""<bash>" -c "<walk>""`) is unit-tested but not yet smoke-tested on a real Windows host running Codex. Mitigation: a real-host smoke test is pending before Windows Codex support is announced.
- When no Git Bash is found, `install-codex` warns and writes a bare `bash` into the hook command, which can resolve to the WSL launcher. Mitigation: the warning names the cause; installing Git for Windows and re-running the installer fixes it.
- A new shell script that calls `python3` without sourcing `scripts/lib/python.sh` works on POSIX and fails only on Windows. Mitigation: source it from the dispatcher or library the script is reached through.
