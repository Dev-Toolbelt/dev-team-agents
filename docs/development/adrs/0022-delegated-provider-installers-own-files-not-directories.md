# ADR-0022: Delegated provider installers own files, not directories

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

`devteam bind` promised that it never overwrites what it did not create
([ADR-0007](0007-global-core-and-data-store-replacing-per-project-vendored-install.md)): `_preflight` and
`_is_managed_path` refuse a foreign path before the first write. That promise held only for
Claude Code, whose artifacts `bind.py` materialises itself. opencode and Codex are delegated to
`install-opencode.sh` and `install-codex.sh`, and neither installer checked anything:

- `cp -f` overwrote a project agent that shared a name with a framework agent
  (`.codex/agents/backend-developer.toml`, `.opencode/agents/code-reviewer.md`).
- `rm -rf` removed `.codex/skills/devteam-*` and a real directory at `…/skills/dev-team-agents`.
- `find -delete` removed `devteam-*.md` from `.codex/prompts/` **and from `~/.codex/prompts/`**,
  outside the project.

`bind.py` then recorded `.codex/agents`, `.codex/skills`, `.codex/hooks.json`,
`.opencode/agents`, `.opencode/skills` and `.opencode/plugins` as whole-directory artifacts. A
directory record claims everything in it: `unbind` and the prune moved the project's own agents
and skills into quarantine, the `.git/info/exclude` block hid new project files from `git add`, and
`unbind` quarantined `.codex/hooks.json` with the project's own hooks in it.

## Decision

1. **The installer is the only list of what it writes.** Each delegated installer answers
   `--list-targets` with the project-relative paths it would write, without writing. `bind` asks
   for that list rather than re-deriving it, so the two cannot drift.
2. **One ownership rule, in both layers.** A target that already exists is replaced only when it
   is framework-owned: claimed by the bind manifest, a symlink into the framework, or — for a
   standalone install — listed in the installer's ledger
   `.dev-team-agents/.provider-owned-<provider>`. Anything else makes the installer exit **4**
   (`scripts/lib/provider-ownership.sh`) and `bind` raise `ConflictError` from `_preflight`, before
   the first write, exactly as it already did for Claude.
3. **The manifest records files.** A delegated artifact is one file or link the installer owns,
   never the directory holding it. `.codex/hooks.json` is recorded as `codex-hooks` — a merged
   file like `.claude/settings.json`: committed, not excluded, and `unbind` removes only the hook
   groups carrying the installer's marker.
4. **Old manifests migrate without moving anything of the project's.** A directory-level record is
   expanded to the installer's targets under that directory; the directory itself is never retired.
   The same expansion is what lets a target the old installer overwrote count as framework-owned.
5. **Nothing outside the project is touched**, and legacy prompt aliases are reported, not deleted.
6. **`--adopt`** is the explicit way past a conflict for a standalone install: the conflicting paths
   are moved to `.dev-team-agents/quarantine/<provider>-<stamp>/`, never deleted. `update.sh` passes
   it, because a v2 install from before the ledger has no record of the files its own earlier runs
   wrote.

## Consequences

- The bind guarantee is the same on every provider in `providers.ALL_PROVIDERS`, and
  `tests/test_provider_ownership.py` fails if a provider is added without its own case.
- `bind` runs each delegated installer's `--list-targets` once in the preflight — one extra render
  per delegated provider.
- The exclude block lists one line per delegated file (~70 for Codex, ~20 for opencode) instead of
  one per directory.
- `.codex/hooks.json` is no longer excluded from git; a project commits it as it commits
  `.claude/settings.json`.
- A standalone install that meets a same-named project file stops and says so, instead of
  replacing it. The user renames it or passes `--adopt`.

## Alternatives considered

- **A marker inside every generated file.** The rendered TOML and Markdown carry no stable marker,
  and a marker cannot protect a project file that merely shares a framework name — it has no marker
  to check.
- **Quarantine instead of refuse in `bind`.** Moving a project's agent out of the way to install
  one of the same name silently changes which agent runs. `bind` refuses for Claude; parity means it
  refuses for every provider.

## Amendment (2026-09-30) — every bind mode

The rule applies in every bind mode, not only `link` and `copy`:

- **Vendored mode runs the delegated installers.** It used to skip them, so a vendored project got
  nothing for opencode or Codex. Their output is portable: files, hook paths into the vendored
  `scripts/`, and a relative skills link, committed with the rest of the tree.
- **The skills link has one rule in both installers** (`po_link_skills`): the project's own
  `.dev-team-agents/skills` when it exists (v2, vendored), the source's `skills/` otherwise (v3 link
  or copy), and relative whenever the target is inside the project. The Codex link used to point at
  `<project>/.dev-team-agents/skills` unconditionally, which a v3 bind never creates — it dangled,
  and Codex saw no framework skills.
- **Vendored refuses a project-owned path too, for Claude as well.** `_preflight` no longer returns
  early in vendored mode: the Claude artifact paths and every delegated target are checked with the
  same `_is_managed_path` rule. Vendored still quarantines and re-vendors its own trees under
  `.dev-team-agents/`; it no longer moves a project's own `.claude/skills/<name>` out of the way.
- **The installers write nothing unrecorded into a bound project.** With `.dev-team-agents/project.json`
  present, `install-opencode.sh` no longer writes `.dev-team-agents/VERSION` and
  `ensure-claude-framework.sh` no longer recreates `.dev-team-agents/user-data/`, which
  `devteam upgrade` retires.
