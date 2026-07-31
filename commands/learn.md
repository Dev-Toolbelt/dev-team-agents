Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

You are running the **`/devteam:learn`** command.

**Purpose:** Consolidate everything that happened in this session — decisions made, patterns established, conventions updated — into the project's persistent knowledge base. Run this at the end of any session where something non-obvious was learned, decided, or changed.

---

## Step 1 — Gather session evidence

Collect the raw material before classifying anything. Read only headers and first
lines of the project docs — never whole files.

```bash
head -80 .dev-team-agents/user-data/session-summary.md 2>/dev/null || echo "(no session summary found)"
git log --oneline -15
git diff HEAD~3...HEAD --stat 2>/dev/null || git diff --stat
find docs/ -newer .dev-team-agents/user-data/session-summary.md -type f 2>/dev/null | head -20
head -5 docs/project.md docs/development/{architecture,code-standards,tech-stack}.md 2>/dev/null
ls docs/wiki/ 2>/dev/null
```

Extract from that output:
- **Done / Decisions / Next** from the most recent session-summary entry.
- Which files changed, in which layers, and how many commits were made today.
- Which docs were already updated this session (`find` hits) — skip those when patching.
- Which project docs and wiki domains already exist, so updates land as patches.

---

## Step 2 — Classify learnings into buckets

Analyze the evidence collected in Step 1. Map each finding to one or more update buckets:

| Bucket | Trigger | Target |
|--------|---------|--------|
| **Doc patch** | Architecture changed, new layer/module added, stack updated, standards detected or changed | `docs/development/*.md` or `docs/project.md` |
| **Wiki entry** | Non-obvious flow discovered, gotcha hit, behavior that differs from what the name implies, cross-layer invariant | `docs/wiki/<domain>/` |
| **ADR candidate** | Decision is hard to reverse, affects multiple components, has non-obvious reasoning | `docs/development/adrs/` |
| **Session summary** | Summary missing for today OR decisions were made that aren't captured yet | `.dev-team-agents/user-data/session-summary.md` |
| **Nothing to update** | Everything already documented, no decisions, trivial session | — |

**Scoring rules:**
- A finding goes into exactly one primary bucket; it may also flag a secondary bucket (e.g., an ADR candidate also triggers a wiki entry).
- Only include findings that are **non-obvious** — derivable from reading the code doesn't count.
- A changed pattern that already existed in docs requires a **patch** (update), not a new entry.

---

## Step 3 — Present plan

Before spawning any agent, present the classified findings as a plan:

```
## /devteam:learn — Session Knowledge Capture

### Evidence summary
[2–3 lines: what was done this session, sourced from Step 1]

### Proposed updates

| # | Bucket | Target file | What changes |
|---|--------|-------------|--------------|
| 1 | Doc patch | docs/development/architecture.md | [describe the patch] |
| 2 | Wiki entry | docs/wiki/<domain>/<topic>.md | [describe the entry] |
| 3 | ADR candidate | docs/development/adrs/NNNN-*.md | [describe the decision] |
...

### Agents to spawn
- technical-writer (always) — doc patches, wiki entries, session summary
- software-architect (if ADR candidates detected) — ADR authoring and decision framing

### Commit plan (auto-committed after execution)

This command commits the knowledge-base updates automatically once the agents finish.
Declare the commits up front — group the proposed updates by layer/type so each commit
is atomic and conventional:

| Commit # | Type & scope | Files | Message |
|----------|--------------|-------|---------|
| 1 | `docs(wiki)` | [wiki files] | [imperative summary] |
| 2 | `docs(adr)` | [adr file] | [imperative summary] |
| ... | ... | ... | ... |

> **Total: N commits.** Message format is governed by the `conventional-commits` skill
> (loaded in Step 5). Commits are local only; this command never pushes.

Awaiting your approval before proceeding. Approving this plan authorizes the listed commits.
```

If **nothing to update** was determined: output exactly:

```
Nothing to capture — session knowledge is already up to date.
```

Then stop.

---

## Step 4 — Execute (after user approval)

**MANDATORY:** Use the Task tool to spawn agents. Do NOT write files in the main context.

### Always spawn:

**`technical-writer`**

Hand it this prompt, substituting the classified findings:

```
You are performing a /devteam:learn consolidation pass.

Load `skills/shared/docs-sync/SKILL.md` before writing anything.

Session evidence:
[paste the evidence summary from Step 1]

Approved updates to execute:
[paste the approved table from Step 3]

Rules:
- **Location:** every documentation file goes under `docs/` at the project root, at the
  target the docs-sync skill defines for it. Never write documentation into `.opencode/`,
  `.claude/`, `.dev-team-agents/`, or any other hidden directory. The one exception is the
  session summary, which is framework data at `.dev-team-agents/user-data/session-summary.md`.
- Doc patches and wiki entries: follow docs-sync exactly — surgical Edit only, never a whole-file
  rewrite, `<!-- last-updated -->` refreshed, its token-economy rules respected.
- Session summary: if today's entry is missing or incomplete, write/append it now in the
  format defined in CLAUDE.md.
- For each file touched, output exactly one line: "PATCHED <filepath>"
```

### Spawn conditionally (only if ADR candidates were detected):

**`software-architect`**

```
You are performing a /devteam:learn ADR capture pass.

Load `skills/shared/adr/SKILL.md`.

ADR candidates identified this session:
[paste ADR candidates from Step 3]

For each candidate:
1. Run `bash .dev-team-agents/scripts/new-adr.sh "<decision title>"` to create the file.
2. Fill in the template: Context, Decision, Consequences. Keep it factual — record what was actually decided, not what could have been decided.
3. Set status to `Accepted`.
4. Output: "ADR created: <filepath>"

Do not create ADRs for decisions that are easily reversible or purely implementation-level.
```

---

## Step 5 — Auto-commit

After all agents complete, execute the **Commit plan** declared in Step 3 — do not wait
for the user to run `/devteam:commit`; the plan approval already authorized these commits.

1. Load `skills/shared/conventional-commits/SKILL.md` and follow it for message format,
   project-pattern detection (`git log --oneline -10`), and authorship rules.
2. For each manifest row, stage only that row's files (`git add …`) and commit it. One
   atomic commit per row; never mix layers; commit **locally only** — do not push.
3. If a file in the manifest was not actually created/changed, skip its commit and note it.

Then output a summary:

```
## Session knowledge captured & committed

[list each file patched/created, one per line]

Commits created (N):
[list each commit hash + message, one per line]
```

---

## $ARGUMENTS options

| Argument | Effect |
|----------|--------|
| _(none)_ | Full learn pass — all buckets |
| `docs` | Doc patches only — skip wiki and ADRs |
| `wiki` | Wiki entries only |
| `adr` | ADR candidates only |
| `--dry-run` | Show the classified plan (incl. commit manifest) only, do not spawn agents or commit |
| `--no-commit` | Run the full learn pass but skip the auto-commit — leave changes staged for manual commit |
