# A bare `bash` on Windows can be WSL's launcher, even when `shutil.which` says Git Bash

**Origin:** `test_plugin_lint` printing "Windows Subsystem for Linux has no installed distributions" on the runner | 2026-10-02
**Tags:** windows, bash, WSL, System32, bash.exe, WindowsApps, Store alias, CreateProcess search order, shutil.which, Git Bash, subprocess, cmd.exe, hooks.json

> `subprocess.run(["bash", ...])` and a `cmd.exe` command starting with `bash` resolve the name with CreateProcess's search order, which looks in `System32` **before** PATH. That finds `C:\Windows\System32\bash.exe`, the WSL launcher, while `shutil.which("bash")` on the same machine returned `C:\Program Files\Git\usr\bin\bash.EXE`.

---

## Why it matters

The WSL launcher is not Git Bash. It runs the script inside a Linux distribution, if one is installed, with different paths and tools. Without a distribution it prints a message and fails. Even when it works, the processes it starts are out of reach of the Windows-side kill (see `git-bash-children-escape-taskkill.md`). The Microsoft Store alias under `WindowsApps` is the same kind of stub.

## The rule

Resolve an **absolute** Git Bash and run that: `devteam.shells.bash_path()`. On POSIX it is just `shutil.which("bash")`. On Windows it takes the PATH hit only when it is outside `\windows\system32\` and `\windowsapps\`, else the Git for Windows default folders, else `None`. Plugin runtimes, the opencode/Codex installers (`providers._run_installer`, `require_tools`) and the Codex hook command (`codex_hooks_merge.windows_command`) all go through it. The reuse rule `bash_path_resolution` in `docs/development/reuse-guidelines.md` enforces it.

## Gotchas

- Tests that drive a shell script through `"bash"` hit the same stub on the runner, which is why they are skipped there (`devteam_support.requires_bash()`).
- When no Git Bash is found, `install-codex` still writes a bare `bash` into the hook command, with a warning (see ADR-0026, Risks).

## References

- `scripts/lib/devteam/shells.py`
- `docs/development/adrs/0026-on-windows-shell-scripts-run-only-under-an-absolute-git-bash-with-a-resolved-python.md`
