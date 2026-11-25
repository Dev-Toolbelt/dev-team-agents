# ADR-0069: Link mode uses NTFS junctions on Windows without symlink privilege

**Date:** 2026-11-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/paths.py`, `scripts/lib/devteam/bind.py`, `scripts/lib/devteam/quarantine.py`, `scripts/lib/devteam/migrate.py`, `scripts/lib/devteam/doctor.py`, `scripts/lib/devteam/providers.py`, `scripts/lib/provider-ownership.sh`, `scripts/install-opencode.sh`, `scripts/install-codex.sh`

## Context

`link` is the bind mode the app recommends: it is the only one where a store update reaches every bound
project with no further step. On Windows it needed `os.symlink`, which Windows refuses without Developer
Mode or an elevated process. A user who accepted the recommendation got "this filesystem cannot create
symlinks, so --mode=link is impossible", and `vendored` crashed on the same refusal. Only `copy` and
`auto` worked there.

Every link a bind makes is to a directory: `.claude/agents/dev-team`, `.claude/commands/devteam`, one per
skill, `.dev-team-agents/{scripts,templates,plugins}`, and the opencode and Codex skills link. Windows lets
any user create an NTFS junction to a directory, and every tool follows it as it follows a symlink.

## Decision

1. **`link` mode falls back to a junction.** `paths.make_dir_link` tries `os.symlink` and, on Windows only,
   creates a junction when that is refused. `bind.symlink_supported` answers whether either works, so
   `--mode=link` and `auto` resolve to `link` on Windows without Developer Mode. The manifest records
   `link` either way.
2. **One notion of "link".** Python reports a junction as a directory, not a symlink. Code that decides
   whether a bind artifact is a link uses `paths.is_link` (symlink or junction, detected through
   `os.lstat` so the 3.9 floor needs no `Path.is_junction`), and removes it with `paths.remove_link`,
   which deletes the link and never the files it points to. `quarantine.move` refuses a junction: across
   volumes `shutil.move` would copy the store's files into quarantine and then delete them from the store.
3. **`vendored` never writes a junction.** A junction's target is absolute, so it would not survive the
   commit `vendored` exists for. Where symlinks are refused, `vendored` copies the Claude trees as real
   files instead of relative links.
4. **The opencode and Codex installers try a junction too**, before falling back to a copy, and only for
   an absolute (non-vendored) target.

## Consequences

### Positive
- All four modes work on Windows without Developer Mode, and the app's recommended mode is a real choice
  there.
- A store update reaches a Windows project with no `sync`, as it does on macOS and Linux.

### Negative
- Any new code that inspects a bind artifact with `is_symlink()`, `unlink()` or `rmtree` treats a junction
  as content and can move or delete the store's files through it. The rule is written in
  `CLAUDE-md/cli.md` § Bind modes, and `tests/test_windows_junctions.py` pins the dangerous paths, but only
  the Windows CI job runs them.
- A junction cannot point to a network share, so `link` on a project whose store sits on one still fails
  and needs `copy`.
- `vendored` without symlinks copies the Claude trees, so each re-vendor moves the previous copies to
  quarantine, as `copy` mode already does.

### Neutral
- The global skill symlinks (`global_skills.py`) are a separate feature and are not created as junctions.
  Its `_move_aside` does remove a junction it finds through `paths.remove_link`, because `quarantine.move`
  now refuses one.
- `create_junction` goes through `_winapi.CreateJunction` only. `cmd /c mklink` would parse `&`, `^` and `%`
  inside a path as syntax; the shell installers call the same API through `python3` with the paths as argv.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Recommend `auto` on Windows in the app | It hides the problem instead of fixing it: `link` would still be impossible there, and `vendored` would still crash |
| Ask the user to enable Developer Mode | A system setting changed for one tool, and many managed machines do not allow it |
| Hard links | They work for files only, and every bind link is a directory |
| `Path.is_junction` | It arrived in Python 3.12; the CLI's floor is 3.9 |
