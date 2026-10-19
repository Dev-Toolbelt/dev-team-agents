# ADR-0040: Provenance and content hash for skills installed into the providers' global skill directories

**Date:** 2026-10-19  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/global_skills.py`  
**Relates to:** [ADR-0020](0020-the-cli-manages-the-providers-global-skill-directories.md) (`devteam skills`), [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (machine-local records), [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (JSON contract)

## Context

`devteam skills install` (ADR-0020) copies a skill from a folder, an archive or a single file into the user-level skill roots Claude Code, Codex and opencode read. Once installed, nothing recorded where a skill came from or what its content was. A skill is instructions an agent follows with the user's permissions, so a file changed after install — by another tool, a sync client, or a hand edit — changed the agent's behavior with no trace.

CompozyOS keeps a `skills-lock.json` with the source and a computed hash of every third-party skill. The same idea fits here, scoped to what the CLI itself installed.

## Decision

1. `install` records each target root's copy in `data/machines/<machine-id>/global-skills-lock.json`: `{"schema":1,"skills":{"<root_id>/<name>":{source,kind,link,sha256,installed_at}}}`. `remove` drops the entry; `--replace` overwrites it. Writes are atomic under the existing `global-skills` lock.
2. `sha256` covers every entry of the installed copy, sorted by relative POSIX path: the path, a NUL byte, then the sha256 of a regular file's content (streamed), a symlink's target string (to a file or a directory, never followed), an empty-directory marker, or for any other entry its type alone. Directories and files are opened without following symlinks — directories listed through their own descriptors where the platform allows — and files without blocking, so hashing can neither block nor read outside the skill. The record itself is read the same way and capped at 8 MB. A copy that has since become a symlink or a non-directory reads as `modified`.
3. A `--link` install records `sha256: null`: the content is the user's live folder, and editing it is the point.
4. `skills list` and `skills show` add one key per skill, `provenance`: `null` when there is no entry, else the recorded fields plus `modified`, true only when a recorded hash no longer matches. Absence of an entry never reads as modified — skills installed before this change, by hand, or by bind have none.
5. The record is machine-local (`MACHINE_LOCAL_RECORDS`): source paths and hashes of directories under this host's home describe this host only.
6. A corrupt record reads as empty and is quarantined on the next write, never deleted (No-Destruction Rule).

## Consequences

### Positive
- A changed third-party skill is visible in `skills list` and in the desktop app, which reads the same `--json`.
- The `--json` change is additive, so no contract bump and no `deprecated` list (ADR-0014). `tests/test_json_contract.py` pins the new key.

### Negative
- `list` hashes every skill that has a recorded hash on each call. Skills are small, but a very large installed skill makes `list` proportionally slower.
- Detection, not prevention: `modified` is reported, and nothing refuses to load a modified skill.
- Not tamper evidence against someone who can write to the home directory: the record lives in the same trust domain, so such a writer can rewrite the stored hash or delete the entry. It catches changes made by tools and people that do not know the record exists.
- The record is written after the copy. If that write fails, the install call fails but the skill stays installed with no entry, and reads as `provenance: null` — unknown, not modified.

### Neutral
- Skills installed before this change stay `provenance: null` until reinstalled with `--replace`.
- `devteam doctor` does not check provenance yet.
- The record is not in `compat.store_schemas()`: only the CLI writes it, it is machine-local, and the app reads provenance through `--json`, never the file.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| A portable lock committed with user data | Source paths are absolute paths on one machine; the same file on another host would report everything as unknown or wrong |
| Hash on demand only (`skills verify`) | A check nobody runs finds nothing; `list` is what the user and the app already call |
| Refuse to list or load a modified skill | The CLI does not own how providers load skills, and a legitimate local edit would look like tampering |
