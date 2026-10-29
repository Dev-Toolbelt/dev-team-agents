# ADR-0047: Third-party skills are vendored apart from the framework's own and pinned by commit and content hash

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `skills/third-party/**`, `helpers/third-party-skills.py`, `skills/design/third-party-design-skills/SKILL.md`, `skills/shared/third-party-writing-skills/SKILL.md`, `tests/test_third_party_skills.py`  
**Relates to:** [ADR-0020](0020-the-cli-manages-the-providers-global-skill-directories.md) (user-level skills), [ADR-0040](0040-provenance-and-content-hash-for-skills-installed-into-the-providers-global-skill-directories.md) (content hash)

## Context

The design and writing agents should be able to use well-known community skills (`ui-ux-pro-max`, `impeccable`, `emil-design-eng`, `stop-slop`) so their output improves. Those skills are written and maintained elsewhere, under their own licenses, and carry scripts and data beside their `SKILL.md`. Mixing them into the framework's categories would put upstream text under authoring rules it cannot follow (95-character description, 500-line body, `name`/`description`-only frontmatter) and would let a contributor edit them in place, after which nobody can tell what upstream shipped.

`devteam skills install` (ADR-0020) already installs skills, but into the user's home directories on one machine. That does not reach every bound project, nor the agents the framework ships.

## Decision

1. **Third-party skills live in `skills/third-party/<name>/`**, a category of their own, with the upstream folder copied unchanged plus its license files. Nothing else goes there.
2. **`skills/third-party/sources.json` pins each one**: repository, full 40-character commit, path inside the repository (`.` when the repository root is the skill), optional `exclude` globs, SPDX license, license files, and a `sha256` over the vendored tree (per file, sorted by relative POSIX path: path, NUL, exec flag, NUL, content hash; a symlink anywhere is an error).
3. **`helpers/third-party-skills.py` is the only writer.** `sync` validates the manifest entry, streams the pinned commit's tarball with caps on the whole decompressed archive, extracts only the skill's path (minus `exclude`) and its license files with their exec bit, refuses links, absolute or `..` members, license-file collisions and oversized trees, swaps the folder in by rename, and records the hash per skill; it refuses to overwrite a tree whose hash no longer matches unless `--force`. `verify` is offline and runs in the test suite (`tests/test_third_party_skills.py`). Updating a skill means changing the commit and running `sync`, in a reviewed change.
4. **Authoring lints exempt the category** from the checks upstream text cannot meet — non-canonical frontmatter keys, description budget, size limit — and keep the ones a provider depends on: required `name`/`description`, `name` equal to the directory, and global name uniqueness. The orphan scan counts a third-party skill as referenced when a framework skill names it.
5. **Agents reach them through one framework routing skill per category**, which routes by task, maps each provider's path, and limits what their executables may do. Design: `skills/design/third-party-design-skills/SKILL.md`, loaded by `ui-ux-designer`, `frontend-developer` and `frontend-reviewer`. Writing: `skills/shared/third-party-writing-skills/SKILL.md`, loaded by `technical-writer` and the PR Comment Gate in `pr-review`; it also lists the upstream rules that do not apply here. Project rules and the framework's own skills still win.
6. **No vendored executable may download or install anything.** A skill whose tools fetch and run code this repository cannot pin ships without those tools (`exclude`). `impeccable` therefore ships as instructions only: its `scripts/` launcher downloads an engine binary verified only against a checksum from the same release, caches it in `~/.impeccable/bin/`, and honours a download-base override. The skill's own "Launcher unavailable" path covers its design playbooks; the automated detector, critique history and live mode are lost.
7. **A project's own copy wins.** When a bound project already has a real `.claude/skills/<name>` for a third-party skill, bind keeps it, writes no framework link there, does not claim it in the manifest, and warns; `migrate` never treats it as a v2 copy (v2 never shipped this category). A collision with a framework skill's name is still refused.
8. **Delivery needs no provider-specific code.** The existing two-level skill layout already links each skill folder on Claude Code and the whole `skills/` tree on opencode and Codex; the test iterates `ALL_PROVIDERS` and checks that every file arrives.

## Consequences

### Positive
- Upstream content stays byte-for-byte reviewable, and any edit made outside `sync` fails `verify`.
- Every bound project, on every provider, receives the same pinned version, unless it carries its own copy (Decision 7).
- License attribution travels with each skill.

### Negative
- The package grows by about 6 MB, most of it `ui-ux-pro-max` data.
- `impeccable` loses its automated scan, critique history and live mode.
- The routing skill is advisory when a provider invokes a vendored skill directly by its description, without loading the routing skill. Decision 6 is what keeps that safe: no shipped executable can download or install code. Vendored text may still suggest it (`impeccable` mentions `npx impeccable update`); the routing skill forbids it, and the provider's permission prompt is the remaining guard when the routing skill is not loaded.
- On Claude Code a personal skill of the same name (`~/.claude/skills/<name>`) takes precedence over the project's, so the pinned version is not the one that runs there.
- The first `sync` of a pin trusts what codeload serves for that commit; the hash protects every run after it, and the diff review in the update procedure is the check on the first.
- Upstream fixes arrive only when a maintainer bumps the commit.

### Neutral
- Removing a vendored skill, or bumping a pin where upstream renames or drops one, follows the Immutability Contract: one minor version with a deprecation warning first.
- `skills/design/frontend-design` predates this category and stays where it is.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Put them in `skills/design/` with the framework's skills | Subjects upstream text to authoring rules it cannot meet, and hides what was not written here |
| Install per project through the CLI at bind time | Network at bind, a new command and a `--json` surface, and the framework's agents could not rely on the skills being present |
| Git submodules | Pulls whole upstream repositories, adds a clone step to every packaging path, and does not pin content beyond the commit |

> **Amendment (2026-10-29) — a writing category, a repository-root skill, and suspended upstream rules.**
> `stop-slop` is the first vendored skill outside design, so Decision 5 now names one routing skill
> per category, and the writing one is `skills/shared/third-party-writing-skills/SKILL.md`. Its
> upstream repository is the skill itself, so Decision 2 accepts `path: "."`. That extracts the whole
> repository minus `exclude`, a deny-list: whoever bumps the pin lists every new non-skill top-level
> file in `exclude` and reviews the vendored diff. A routing skill may also suspend upstream rules
> that clash with formats the framework fixes; the writing routing skill does so for absolutes,
> blanket adverb and passive bans, Wh- openers, em dashes and the two-items rule.
