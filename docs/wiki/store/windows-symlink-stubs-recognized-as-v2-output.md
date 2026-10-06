# Windows symlink stubs are decoded and recognised as v2 output

**Origin:** `devteam migrate` exit 4 on a v2 project cloned on Windows | 2026-10-06
**Tags:** Windows, symlink stub, core.symlinks=false, Git Bash, MSYS, Cygwin, Interix, migrate, bind, v2

> A v2 link committed as a stub file (git text, MSYS `IntxLNK`, Cygwin `!<symlink>`) is v2 output: migrate quarantines it instead of refusing it as project content.

---

## What it is

A v2 install keeps its framework links (`.claude/agents/dev-team`, `.claude/commands/devteam`, `.claude/skills/*`, and for Codex / opencode `skills/dev-team-agents`) as symlinks. Where a symlink cannot be created, the link becomes a small regular file, and once committed it travels with the repository as content. Three formats exist, each from a different writer:

1. **Git plain text**: the target path as UTF-8 (e.g. `../../.dev-team-agents/agents`). Git writes this on checkout when `core.symlinks` is false, which Git for Windows falls back to when the user may not create symlinks.
2. **`IntxLNK\x01` + UTF-16LE target**: written by MSYS / Git Bash `ln -s` (Interix format) without symlink permission.
3. **`!<symlink>` + target**: Cygwin's format, UTF-16LE after a BOM or UTF-8.

## How it works

`providers.read_link_stub()` decodes all three and never raises. `bind._v2_link_file()` treats a stub as v2 output only when:
- it is a regular file of at most 4096 bytes, read without following a link;
- the stub itself lies inside the project (`require_inside`), so a committed `.claude` or `.codex` symlink cannot hand migrate another tree's file;
- its target, resolved from the stub's folder by path components, lands inside `.dev-team-agents/` or `.claude/dev-team-agents/`.

A recognised stub is listed in `v2_copies`, quarantined under `v2-install/<provider>/…` (never deleted) and, with `--untrack`, removed from the index. `bind` over one refuses with `reason: v2-install`, which is what makes the desktop app offer the migrate repair.

## Gotchas

- Reading a UTF-16 stub as UTF-8 does not fail: NUL is valid UTF-8, so the text just carries a `\x00` after every character and matches nothing. That is how the first fix missed this format.
- The target is resolved lexically, not on disk: the install it points at is usually already gone.
- A stub whose `../` depth is wrong resolves outside the install and stays foreign. That is deliberate: being too strict leaves a file in place, being too loose would move a project file.
- An MSYS absolute target (`/c/proj/...`) is read as its drive path only on Windows.

## References

- `scripts/lib/devteam/providers.py` — `read_link_stub()` function
- `docs/wiki/store/v2-links-materialized-as-copies.md` — broader context on v2 link materialization
