# Audit Carry-Over — v1 → v2 Consolidation

**Date:** 2026-07-30 · **Baseline:** `HEAD` = `7f85ed7` · **Supersedes:** all 20 dated report folders from 2026-05-06 to 2026-05-26

---

## What This Is

Between 2026-05-06 and 2026-05-26, twenty daily audit passes produced 106 report files and registered **517 fingerprinted findings** against `dev-team-agents`. Those passes ran while `HEAD` was frozen at `v1.7.0` — the last eight windows recorded **0% throughput**, so the backlog accumulated without being worked.

The repository has since moved to `v1.11.0` plus the unreleased multi-provider port, which is what `skills/shared/migration-v1-to-v2/SKILL.md` defines as **v2**: multi-provider rendering, symlinked installs rooted at `.dev-team-agents/`, explicit `/devteam:<name>` commands, and — critically for this backlog — the wholesale removal of the `workflows/` directory.

A large fraction of the v1 backlog described files and structures that no longer exist. This report is the surviving remainder: **every finding below was re-verified against the current tree, with fresh evidence.**

---

## Method

1. **Excluded by status** — 184 fingerprints marked ✅ Executed (181), ↩️ Reverted (2), or 🟢 Resolved (1) were dropped without re-verification, per the `_index.md` convention.
2. **Triaged** — the remaining **334** candidates (311 unmarked + 23 ⚠️ Partial) were partitioned by category prefix into six disjoint slices and verified in parallel.
3. **Survival test** — a finding survives only with **fresh evidence from the current tree**: a current `path:line` plus a quoted snippet. Line numbers from the v1 reports were treated as stale by default and re-located. Quantitative claims were re-measured, not copied.
4. **Migration check** — before killing a finding for "file no longer exists", each was checked for migration into `commands/<scope>.md`. A root cause that survived relocation was kept and annotated.
5. **Cross-slice dedup** — 26 findings appearing in more than one slice were merged into single entries with a consolidated evidence set.

Findings that could not be verified either way were recorded as dead with reason `unverifiable`. The bias is deliberate: a false survivor is worse than a missed one, because the point of the exercise is to stop carrying dead weight.

---

## Results

| Axis | Candidates | Survived | Died | Mortality |
|---|---|---|---|---|
| `token-*` | 86 | 45 | 41 | 48% |
| `flow-*` | 76 | 31 | 45 | **59%** |
| `ref-*` + `docs-*` | 64 | 28 | 36 | 56% |
| `agent-*` | 45 | 29 | 16 | 36% |
| `skill-*` | 34 | 12 | 22 | 65% |
| `auto-*` + `gov-*` | 29 | 12 | 17 | 59% |
| **Total** | **334** | **157** | **177** | **53%** |

After cross-slice deduplication: **131 distinct findings**.

| Severity | Count |
|---|---|
| HIGH | 11 |
| MEDIUM-HIGH | 7 |
| MEDIUM | 44 |
| LOW-MEDIUM | 42 |
| LOW | 27 |

### Why findings died

The 177 deaths were not uniform. The dominant causes:

- **`workflows/` removed wholesale** (26) — the directory and `skills/shared/workflow-detection/` were deleted by the port. Every finding targeting them was checked for migration into `commands/` first; those that migrated are kept and marked.
- **`model:` / `tools:` frontmatter removed** (7) — all 17 agents now declare `tier:` only, which invalidated a cluster of frontmatter-ordering and model-assignment findings outright.
- **Genuinely fixed** (~45) — bugs closed, validators added, `references/` extractions performed, skills created.
- **New CI surface** (5) — `.github/scripts/ci/` closed a handful of "no validator enforces X" findings. Notably fewer than expected: the provider contract checker (`_contract.py`) validates `tiers.json` and `tool-map.json`, not skills or docs, so it closed **none** of the documentation-drift findings.
- **Duplicates of a surviving canonical finding** (~30).

### Where the v2 tree got worse

Eight survivors are measurably larger or more numerous than when first reported. Full table in [04 — Token Economy](04-economia-tokens.md); the headline items: `install.sh` 503 → 803 lines, `CHANGELOG.md` ~130 → 441, agents over the 200-line cap 9/17 → **11/17**.

---

## Reports

| File | Axis | Findings |
|---|---|---|
| [01-referencias-e-consistencia.md](01-referencias-e-consistencia.md) | `ref-*` + `docs-*` | 21 |
| [02-fluxos-e-workflows.md](02-fluxos-e-workflows.md) | `flow-*` + `auto-*` + `gov-*` | 43 |
| [03-agentes-e-skills.md](03-agentes-e-skills.md) | `agent-*` + `skill-*` | 36 |
| [04-economia-tokens.md](04-economia-tokens.md) | `token-*` | 31 |

---

## The 11 HIGH findings

| # | Finding | File |
|---|---|---|
| 1 | `docs/agents.md` Model column wrong for 2/17, mirrored into pt-BR, unvalidated — and `Haiku` is unreachable in `tiers.json` | [01](01-referencias-e-consistencia.md) |
| 2 | `CLAUDE.md:180` says `code-reviewer` delegates to the test specialists; it routes to the reviewers | [01](01-referencias-e-consistencia.md) |
| 3 | Two directories named `helpers` with opposite packaging fates; the shipped one is undocumented | [01](01-referencias-e-consistencia.md) |
| 4 | `CLAUDE.md` File Structure omits six real top-level entries, one of which it links to four times | [01](01-referencias-e-consistencia.md) |
| 5 | The 200-line agent cap is warn-only, has no Stop hook, and 11/17 agents violate it | [02](02-fluxos-e-workflows.md) |
| 6 | Telemetry defaults ON in non-interactive `curl \| bash` — the documented install path | [02](02-fluxos-e-workflows.md) |
| 7 | `helpers/archive-index.sh` implements a 90-day rotation policy and is invoked by nothing | [02](02-fluxos-e-workflows.md) |
| 8 | `security-specialist` hardcodes per-ecosystem SAST commands in a stack-agnostic agent | [03](03-agentes-e-skills.md) |
| 9 | `backend-developer` re-states provider rules inline for 8 integrations (~95 lines, always loaded) | [03](03-agentes-e-skills.md) |
| 10 | `frontend-test-specialist` embeds React and Vue hook-test recipes with code samples | [03](03-agentes-e-skills.md) |
| 11 | `devops-specialist` Decision Framework remains stack-prescriptive after three reopenings | [03](03-agentes-e-skills.md) |

---

## Surfaced during triage — not in any v1 fingerprint

These were found while verifying other claims. They are v2-specific or were simply never noticed:

| Observation | Where |
|---|---|
| `CLAUDE.md` Authoring Standards still mandate `model:` and `tools:` frontmatter. Zero agents carry either key; `agent-lint.sh` requires `tier:`, which the block never mentions. **Following the canonical doc now produces an agent that fails CI.** | [01](01-referencias-e-consistencia.md) |
| `software-architect` is the largest agent at **372 lines** (+86% over cap). No v1 finding covers it — the v1 reports still named `frontend-test-specialist` as the largest. | [02](02-fluxos-e-workflows.md) |
| `skills/shared/migration-v1-to-v2/SKILL.md` — the skill that defines v2 — is itself an orphan with no agent reference, reported live by `orphan-skill-scan.sh` in the non-blocking CI tier. | [02](02-fluxos-e-workflows.md) |
| `.github/CODEOWNERS:9` still assigns ownership of `workflows/`, a directory the port deleted. | [02](02-fluxos-e-workflows.md) |
| `discovery-mode` lock handling has two undocumented defects: the acquire block returns before the staleness check is reachable, and `date -d` is GNU-only, so on macOS every lock is deleted unconditionally. | [03](03-agentes-e-skills.md) |
| `skills/database/db-comparison/SKILL.md:37` routes pgvector/RAG questions to `database-multitenancy`, an unrelated skill. | [03](03-agentes-e-skills.md) |
| `/devteam:health-check` is absent from the canonical command table, both READMEs, and the `current-context` exception list — surfaced independently by two slices. | [02](02-fluxos-e-workflows.md) |
| The package-exclusions table fell behind `strip-tarball.sh` again: `opencode/` is stripped but undocumented. The four items originally flagged were fixed and the table drifted one release later. | [01](01-referencias-e-consistencia.md) |

---

## Reading this alongside `_index.md`

`docs/reports/_index.md` was rewritten as part of this consolidation. It now carries only the 131 surviving fingerprints, all pointing at this folder. The 517-entry v1 history — including the 184 resolved findings and the per-pass Guardian audit notes — remains in git history at `c9cb5c2`.

Two mechanisms the old index promised are still not wired, and this rewrite does not fix them:

- **Rotation.** `helpers/archive-index.sh` has no trigger (HIGH, [02](02-fluxos-e-workflows.md)). The index will grow unbounded again.
- **Cross-file uniqueness.** `helpers/check-fingerprint-uniqueness.sh` is scoped to a single file, so it degrades from a global to a per-file guarantee the moment rotation does happen ([02](02-fluxos-e-workflows.md)).
