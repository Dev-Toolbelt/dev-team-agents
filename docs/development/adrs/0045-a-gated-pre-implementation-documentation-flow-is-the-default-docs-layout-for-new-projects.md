# ADR-0045: A gated pre-implementation documentation flow is the default docs layout for new projects

**Date:** 2026-10-23  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/doc-layouts.json`, `scripts/lib/docs_root.py`, `scripts/doc-path.sh`, `scripts/hooks/pre-tool-use/05-readonly-docs-guard.sh`, `skills/shared/doc-flow/**`, `templates/process-template.md`  
**Relates to:** [ADR-0008](0008-project-identity-via-committed-project-json-and-three-personal-preference-layers.md) (`project.json`), [ADR-0035](0035-planning-sequence-owned-by-the-main-conversation-per-scope-backlog-and-routing-in-every-provider-s-instruction-file.md) (planning sequence), [ADR-0037](0037-spec-status-scenario-ids-and-a-mechanical-spec-lint-close-the-spec-driven-loop.md) (scenario IDs, spec-lint), [ADR-0039](0039-adrs-declare-the-paths-they-govern-and-a-stop-hook-names-them-when-those-paths-change.md) (Applies to), [ADR-0044](0044-the-sprint-backlog-is-read-as-a-graph-by-the-cli-with-machine-local-expiring-claims-and-a-post-compaction-prime.md) (backlog graph)

## Context

A new system went from `product-analyst` to `software-architect` to implementation with every architecture fact under `docs/development/`. Coding agents still filled gaps by guessing: a screen state nobody drew, an endpoint the spec implied, a contract with an open point. The same fact was also written in more than one place — schema in both `architecture.md` and `database.md`, endpoints in `architecture.md` and `api-contracts.md` — so the copies drifted. A real project (multi-tenant support agent) designed a stricter flow whose goal is maximum context for the coding agent: every gap is either documented or blocks the task.

Changing paths for every project would break the ones already bound, whose docs, links and hooks assume `docs/development/`.

## Decision

1. **Two docs layouts, chosen per project.** `project.json` gets an optional, additive `docs_layout` key: `development` (absent means this — every existing project is unchanged) or `gated`. `/devteam:setup` writes `gated` only on FIRST_RUN of a new project. An existing project moves only through the opt-in migration in `skills/shared/doc-flow/references/migration.md`.
2. **One path map, one owner per fact.** `scripts/lib/doc-layouts.json` maps each fact category to exactly one owning document per layout, its owner agent and a read-only flag. Scripts read it through `docs_root.py` (`doc_path`, `layout`) and `scripts/doc-path.sh`; agent text resolves every `docs/development/<x>` mention through it (`skills/shared/project-context/SKILL.md` § Doc Layout), so the ~50 files that name those paths did not have to be rewritten. Schema facts live only in the `data-model` doc, endpoints only in `api-contracts`; `architecture.md` links to them. `templates/process-template.md` mirrors the gated column and `tests/test_process_template_mirror.py` fails on drift.
3. **The flow is a skill.** `skills/shared/doc-flow/SKILL.md` owns the principles, the stages (0 raw inputs → 1 product → 2a technical ‖ 2b design → 3 reconciliation → 4 feature spec → 5 plan → 6 implementation → 7 learn), each stage's exit gate, the trace chain, the Definition of Ready and the DoD additions. `/devteam:plan` walks stages 0→5 in the gated layout, stopping at each gate, and starts design (2b) in parallel with the technical stage (2a) once the PRD is approved.
4. **Raw inputs are immutable.** `docs/source/` and `docs/design/prototypes/` accept new dated files and refuse edits, by rule and by the PreToolUse guard `05-readonly-docs-guard.sh` on Claude Code, opencode and Codex. Like the credential guard, it is a hygiene gate, not a sandbox: a write through Bash is not covered.
5. **Gaps block mechanically.** In the gated layout `scripts/spec-lint.sh` reports `[NOT-READY]` for a pending task whose contract has open points, whose frontend spec has no flow or an unapproved state screenshot, or whose AI spec has no eval section. spec-gate's Scope Lock refuses such a task before any code is written.
6. **Existing mechanisms are reused, not replaced.** Scenario IDs stay `S<n>` and the global trace ID is `<feature>#S<n>` (ADR-0037). Amendment logs in owner docs use spec-gate's format. Sprint files stay in `docs/backlog/sprints/`, so the `devteam backlog` parser (ADR-0044) is untouched; in the gated layout `docs/backlog.md` becomes the single index, replacing both `backlog/README.md` and `sprints/sprints.md`. It keeps the `sprints.md` table format, so `devteam backlog prime` reads in-progress sprints from both indexes — the one change to ADR-0044's reader.

## Consequences

### Positive
- A coding agent in the gated layout gets every fact from one owning doc and is refused a task whose inputs are incomplete, instead of guessing.
- Existing projects see no change until they opt in.
- New docs are resolved from one map, so adding or moving one is a JSON edit plus its mirror.

### Negative
- Two layouts to keep working. Every rule that names a doc must name it by map key, and reviewers must catch a new hardcoded path.
- The gated flow costs more up-front stages and user approvals before the first line of code.

### Neutral
- A minor release (v2.49.0): the default changes for fresh installs only, so an existing installation behaves the same after the update (CLAUDE-md/versioning.md).
- `security-specialist` stays read-only; `software-architect` writes the threat model from its findings.
- Visual-regression tooling per stack is out of scope; the DoD only states the rule.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Move every project to the new paths | Breaks bound projects' links, hooks and habits; violates the No-Destruction Rule without consent |
| Detect the layout from which folders exist | A half-migrated or empty project is ambiguous; a committed key is explicit and reviewable |
| Rewrite every `docs/development/` mention in agents and skills | ~50 files, and the copies drift; the resolution rule is the pattern `new-adr.sh --dir` already uses |
| Adopt `<FEAT>-AC-<nn>` scenario IDs | `<feature>#S<n>` is already stable and global; a second format would need two parsers in spec-lint, Covers and tests |
| Move sprint files to `docs/backlog/sprint-NN.md` | Changes the `devteam backlog` parser and its contract (ADR-0044) for no gain in context |
