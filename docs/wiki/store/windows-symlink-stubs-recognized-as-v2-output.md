# Windows symlink stubs are decoded and recognised as v2 output

**Origin:** `devteam migrate` exit 4 on a v2 project cloned on Windows | 2026-10-06
**Tags:** Windows, symlink stub, core.symlinks=false, Git Bash, MSYS, Cygwin, Interix, migrate, bind, v2

> Symlink stubs committed on Windows are now decoded and recognised as v2-managed paths, so migration does not fail with "already exists and was not created by dev-team-agents".

---

## What it is

On Windows without native symlink support, `git core.symlinks=false` (the default) materialises relative symlinks as text files when they are committed to the repository. A v2 project cloned on Windows carries its `.claude/agents/dev-team`, `.claude/commands/devteam` and skill link stubs as regular files in three possible formats:

1. **Git plain text** — just the relative path (e.g., `../../.dev-team-agents/agents`)
2. **Interix/Cygwin/MSYS** — the `IntxLNK\x01` magic + UTF-16LE encoded target
3. **Cygwin** — the `!<symlink>` magic + UTF-16LE BOM or UTF-8 encoded target

Previously only the plain-text format was recognised; the encoded formats caused `bind` and `migrate` to treat them as foreign content.

## How it works now

`providers.read_link_stub()` decodes all three stub formats. A stub is recognised as v2-managed output only if:
- It is a regular file ≤4096 bytes (not a symlink, not a directory)
- Its target decodes to a path that resolves (by path components, no symlink traversal) inside `.dev-team-agents/` or `.claude/dev-team-agents/`

Recognised stubs are quarantined under `v2-install/…` — they are never deleted — so an interrupted `migrate` can always resume without the project's `.dev-team-agents/` tree needing to be intact. This applies to Claude (`.claude/agents/dev-team`, `.claude/commands/devteam`, `.claude/skills/*`) and, for parity, to Codex/opencode links (`.codex/skills/dev-team-agents`, `.opencode/skills/dev-team-agents`).

## Gotchas

- The encoded formats can be created only by Windows Git Bash (MSYS2 `ln -s` without symlink permission). Manually copying files as stubs bypasses the encoding. If a stub doesn't decode, it's treated as foreign content.
- Stubs are only recognised if their targets resolve **into** the framework path, not merely **under** it. A stub pointing elsewhere stays foreign.
- The 4096-byte limit prevents misidentifying large text files as stubs. Stubs are always small because the target is relative and short.

## References

- `scripts/lib/devteam/providers.py` — `read_link_stub()` function
- `docs/wiki/store/v2-links-materialized-as-copies.md` — broader context on v2 link materialization
