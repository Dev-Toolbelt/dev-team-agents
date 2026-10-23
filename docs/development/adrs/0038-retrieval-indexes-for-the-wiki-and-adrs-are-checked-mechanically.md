# ADR-0038: Retrieval indexes for the wiki and ADRs are checked mechanically

**Date:** 2026-10-17  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/index-lint.sh`, `scripts/lib/index_lint.py`, `scripts/hooks/stop/03g-index-lint.sh`, `scripts/new-adr.sh`  
**Relates to:** [ADR-0036](0036-path-scoped-and-severity-graded-rules-in-the-reuse-registry-enforced-at-stop-by-exit-2.md) (reuse-lint), [ADR-0037](0037-spec-status-scenario-ids-and-a-mechanical-spec-lint-close-the-spec-driven-loop.md) (spec-lint)

## Context

Agents never load `docs/` whole. They read two retrieval indexes and open only what matches the task: the wiki index (`docs/wiki/README.md`), and the ADR titles. An audit of a bound project with ~1M tokens of documentation showed that lookup failing at its source:

1. **Wiki entries had no retrieval key.** 118 of 168 entries had no `**Tags:**` line, so their index rows carried keywords improvised from the title (`ai, briefing and prompt context`). The format required Tags; nothing checked it.
2. **ADRs had no index at all.** 150 ADRs were reachable only by title, with no keywords and no status — a superseded ADR read the same as a current one.
3. **`new-adr.sh` could not follow the project.** It hardcoded `docs/development/adrs/`, while the project kept its series in `docs/adr/` as `ADR-NNNN-slug.md`. The project had to forbid the script, and ADR numbers collided across parallel work. `03e-adr-gap-check.sh` warned about a missing ADR in sessions that had added one.
4. **The overview went stale silently.** `project.md` described "Sprint 0" two months after the project shipped; the freshness warning matched only `<!-- last-updated -->` on line 1, and the project wrote the date differently.
5. **Plans never said whether they were current.** Implemented plans still read "proposed / awaiting approval"; superseded ones carried no marker.

## Decision

1. **The ADR directory is resolved in one place.** `new-adr.sh --dir` prints it: the first of `docs/development/adrs/` and `docs/adr/` that holds ADRs, else the first that exists, else `docs/development/adrs/`. A series named `ADR-NNNN-slug.md` keeps that scheme. A symlinked directory is refused. Every other mention of the path means the resolved directory.
2. **ADRs get a retrieval index**, `<adr-dir>/README.md`, one `ADR · Status · Keywords · Read it when` row per ADR (`skills/shared/adr/SKILL.md` § ADR Index). `new-adr.sh` writes the row; when it creates the index it adds a placeholder row for every existing ADR, because readers fall back to listing files only when there is no index. The context loading order greps it as it greps the wiki index.
3. **Both indexes and plan status lines are linted.** `scripts/index-lint.sh`, run by the Stop sub-script `03g-index-lint.sh` when a session touches `docs/wiki/`, the ADR directory or `docs/development/`. Only a row pointing at a file that does not exist is an ERROR. Everything else — missing Tags, an unindexed document, keyword drift, fewer than four keywords, an unfilled placeholder, a plan without a status — is a WARN, shown once per set of findings.
4. **Documents carry their lifecycle** (`skills/shared/docs-sync/SKILL.md` § Document Lifecycle): plans keep a `**Status:**` line with evidence; superseded documents and point-in-time snapshots get a historical banner; nothing is deleted.
5. **Freshness is read tolerantly**: either date form in the first five lines, and a missing date counts as stale.

## Rationale

- **Mechanical, because prose already failed.** The Tags requirement existed and 70% of entries ignored it. The sibling gates (ADR-0036, ADR-0037) took the same route for the same reason.
- **The severity split follows what blocks retrieval.** A dead row sends the lookup nowhere and is fixed in one edit. The rest is a backlog that every project predating these rules carries; blocking every Stop on it would teach people to ignore the hook.
- **The script resolves the directory, not each reader.** A rule restated in each skill drifted before; one resolver read through `--dir` cannot.
- **Indexes before embeddings.** The audited gaps were in indexing, not search technology. A vector index over untagged entries recovers them no better, at the cost of infrastructure.

## Alternatives Considered

- **Vector search over `docs/`.** Rejected for now: it does not fix missing keys or stale statuses, and adds a dependency to every project. Revisit as an optional plugin (ADR-0019) if lexical lookup still misses after indexes are complete.
- **Blocking on every finding.** Rejected: see the severity split above.
- **Keeping `docs/development/adrs/` as the only directory.** Rejected: projects that predate the default would keep forking a second series.

## Consequences

### Positive
- A document missing from its index is reported the session it happens, on every provider (opencode logs it).
- Projects with `docs/adr/` can use `new-adr.sh` again; the gap check stops warning falsely.
- Superseded ADRs and historical plans are distinguishable from current ones at lookup time.

### Negative
- Repositories with existing debt see one WARN banner the first time a session touches their docs. This repository had it too (keyword drift in 21 wiki entries, no ADR index); both were cleared in the change that introduced the lint.
- `new-adr.sh` refuses to run through a symlinked ADR directory, which a project may have set up deliberately.

> **Amendment (2026-10-20) — the paths are under the docs write root, not a literal `docs/`.**
> Decisions 1 and 3 name `docs/development/adrs/`, `docs/adr/`, `docs/wiki/` and `docs/development/`.
> They now mean those folders under the project's docs write root, the first `context_paths` entry
> (ADR-0008), resolved by `scripts/lib/docs_root.py` (bash: `scripts/lib/docs-root.sh`) and `docs` by
> default. `new-adr.sh --dir`, `index_lint.py` and the `03g` touched-path gate all ask that resolver,
> so a project whose write root is `.claude/docs` keeps its ADRs and wiki there. A symlink anywhere
> on the way to the ADR directory is still refused.
