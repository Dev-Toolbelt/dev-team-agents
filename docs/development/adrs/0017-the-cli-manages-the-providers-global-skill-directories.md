# ADR-0017: The CLI manages the providers' global skill directories

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

Claude Code, Codex and opencode each read **user-level** skills from a directory in the home
folder, outside any project: `~/.claude/skills`, `~/.agents/skills` (Codex, and opencode too),
the older `~/.codex/skills`, and `~/.config/opencode/skills`. Today the only way to see, add or
remove one is a terminal or a file manager. The desktop app should manage them.

Three existing decisions constrain how:

- [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) and
  [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md) make the app
  a pure client of the `devteam` CLI. It never reads or writes the filesystem itself, so a
  capability the app needs is a CLI command first.
- [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md)
  gates every command classified as mutating behind the client's schema declaration.
- The **No-Destruction Rule** (`skills/shared/setup-health-check/SKILL.md`) says a framework action
  moves or adapts and never deletes.

Every command until now wrote either into the store or into a bound project. This is the first
that writes into **directories owned by other programs**, which is why it needed deciding.

## Decision

1. **A `devteam skills` command group owns these directories:** `list` and `show` are read-only,
   and `install` and `remove` are in `compat.MUTATING`. The app reaches them only through these
   commands.
2. **`scripts/lib/global-skill-roots.json` is the single map of those directories.** Its unit is
   the physical directory (a *root*), each listing the providers that read it. The unit is not
   the provider, because opencode reads the Claude and `.agents` roots too, and a per-provider
   listing would show one directory's skills several times. `install_target` names the root each
   provider installs into. Codex installs into `~/.agents/skills`: `~/.codex/skills` stays listed,
   because it holds existing skills and the provider's own `.system/` bundle, but nothing new is
   written there, and `--root` only accepts roots that are an install target.
   - **Fewest roots:** an install covers the chosen providers with as few roots as possible. A
     provider already reached by a chosen root gets no copy of its own, so Claude plus opencode
     writes to `~/.claude/skills` only, and all three write to the Claude and `.agents` roots.
     When a same-named skill already sits in another root one of those providers reads, the
     payload reports it in `also_present` instead of creating a second copy silently.
3. **Nothing is deleted.** `remove`, and `install --replace`, move a real directory into the store's
   quarantine (`global-skills/<root>`). A symlink is unlinked, and what it points at is untouched.
   `remove` reports the link's target, because an unlinked symlink is not quarantined.
   - **The one removal allowed:** a copy this same call created (a staging directory, or a new
     copy being rolled back) is removed, because the source still holds the same content.
   - **Leftover staging:** a hidden `.devteam-staging-*` directory from an interrupted install is
     quarantined on the next install. It is never deleted.
4. **Skills the framework manages are refused.** Anything whose resolved path lies inside the core
   store is `managed`, including the children of a root that is itself a symlink into the core.
   Moving it would damage the versioned store, and `devteam sync` would restore it anyway.
   - **Telling refusals apart:** the refusal carries `details.reason = "managed"`, and a name
     conflict carries `"exists"`. Both are exit 4, so a client uses the reason to offer
     `--replace` only when it can help.
   - **`--link` sources:** a source inside the core, or inside a target root, is refused. Linking
     such a source would produce a link to itself, or an unremovable skill.
5. **Installing validates before it writes.**
   - The source must hold a `SKILL.md` with `name` and `description`, and `name` must follow the
     agentskills.io pattern. The skill is installed under that name, not under the source folder's
     name.
   - Archives (`.zip`, `.skill`) are checked before extraction. Absolute paths, `..` and symlink
     members are refused, and so are archives over 2000 entries or 50 MB unpacked.
   - A directory that is copied may not contain symlinks. `--link` symlinks the source directory
     instead of copying it.
   - All target roots are checked for a name conflict (exit 4) before any root is written.
   - **Staging and rollback:** the install then stages a copy in every root, and only then swaps
     each one into place. An I/O failure in either phase removes the stages. It also rolls back
     every root already swapped: what was replaced comes back from quarantine, or its symlink is
     recreated.
   - **Archive contents:** permission bits survive extraction (setuid, setgid and sticky never
     do), encrypted members are refused, and `__MACOSX/` debris is skipped.
6. **Frontmatter is read leniently.** Third-party skills use folded `description: >` blocks and
   nested keys. A strict reader would report working skills as malformed.
7. **A name is matched, never joined.** `show` and `remove` look the name up among a root's actual
   children. `.`, `..`, separators, NUL, drive letters and dot-names are refused before any path
   is built. The app applies the same guard on its side.
8. **`$DEVTEAM_USER_HOME` overrides `~`** for these roots. `StoreTestCase` pins it, so the suite
   (including the contract sweep, which runs `skills list` bare) can never read or write a
   developer's real home.

## Consequences

**Positive:**
- The app can list, inspect, install and remove global skills for all three providers. Every
  change goes through the same audited, gated CLI a terminal user runs.
- A mistaken removal can be recovered from quarantine.

**Negative:**
- The provider directories are someone else's convention. When a provider moves them, the JSON
  map has to follow.
- Quarantined skills accumulate in the data store, the same way other quarantined content does.

**Neutral:**
- Project-level skills stay with `bind`. Remote sources (git URLs, marketplaces) are not
  supported.

## Risks

| Risk | Mitigation | Residual |
|------|------------|----------|
| A provider changes its skill directory | One JSON file; `list` reports each root and whether it exists | A new location goes unseen until the map is updated |
| A hostile archive | Member validation before extraction, size and count limits | None known |
| The same skill is edited by the provider's own tooling while the CLI writes | Store lock around each write; staging directory plus `os.replace` in the same root | Nothing coordinates with the provider's own tooling |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| The app reads and writes the directories itself | This is the second source of truth that ADR-0015 rejects |
| One listing per provider | opencode reads three roots, so the same skill would show up several times |
| `remove` deletes | Violates the No-Destruction Rule; a wrong click would be unrecoverable |
