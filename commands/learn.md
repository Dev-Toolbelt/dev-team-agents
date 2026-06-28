Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

You are running the **`/devteam:learn`** command.

**Purpose:** Consolidate everything that happened in this session — decisions made, patterns established, conventions updated — into the project's persistent knowledge base. Run this at the end of any session where something non-obvious was learned, decided, or changed.

---

## Step 1 — Gather session evidence

Collect the raw material before classifying anything.

### 1a — Read session summary

```bash
head -80 .claude/user-data/session-summary.md 2>/dev/null || echo "(no session summary found)"
```

Extract from the most recent entry:
- **Done**: what was implemented or changed
- **Decisions**: key choices and why
- **Next**: what remains

### 1b — Read git evidence

```bash
git log --oneline -15
git diff HEAD~3...HEAD --stat 2>/dev/null || git diff --stat
```

Identify: which files changed, in which layers, how many commits were made today.

### 1c — List today's modified docs

```bash
find .claude/docs/ -newer .claude/user-data/session-summary.md -type f 2>/dev/null | head -20
```

This reveals which docs were already updated in the session — skip those when patching.

### 1d — Read current project docs state (surgical — only headers and first lines)

```bash
head -5 .claude/docs/project.md 2>/dev/null
head -5 .claude/docs/development/architecture.md 2>/dev/null
head -5 .claude/docs/development/code-standards.md 2>/dev/null
head -5 .claude/docs/development/tech-stack.md 2>/dev/null
ls .claude/docs/wiki/ 2>/dev/null
```

---

## Step 2 — Classify learnings into buckets

Analyze the evidence collected in Step 1. Map each finding to one or more update buckets:

| Bucket | Trigger | Target |
|--------|---------|--------|
| **Doc patch** | Architecture changed, new layer/module added, stack updated, standards detected or changed | `.claude/docs/development/*.md` or `.claude/docs/project.md` |
| **Wiki entry** | Non-obvious flow discovered, gotcha hit, behavior that differs from what the name implies, cross-layer invariant | `.claude/docs/wiki/<domain>/` |
| **ADR candidate** | Decision is hard to reverse, affects multiple components, has non-obvious reasoning | `.claude/docs/development/adrs/` |
| **Session summary** | Summary missing for today OR decisions were made that aren't captured yet | `.claude/user-data/session-summary.md` |
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
| 1 | Doc patch | .claude/docs/development/architecture.md | [describe the patch] |
| 2 | Wiki entry | .claude/docs/wiki/<domain>/<topic>.md | [describe the entry] |
| 3 | ADR candidate | .claude/docs/development/adrs/NNNN-*.md | [describe the decision] |
...

### Agents to spawn
- technical-writer (always) — doc patches, wiki entries, session summary
- software-architect (if ADR candidates detected) — ADR authoring and decision framing

Awaiting your approval before proceeding.
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

**`technical-writer`** at `.claude/agents/dev-team/technical-writer.md`

Hand it this prompt, substituting the classified findings:

```
You are performing a /devteam:learn consolidation pass.

Load `skills/shared/docs-sync/SKILL.md` before writing anything.

Session evidence:
[paste summary from Step 1a]

Approved updates to execute:
[paste the approved table from Step 3]

Rules:
- Doc patches: surgical Edit only — never rewrite a whole file. Update the `<!-- last-updated -->` marker.
- Wiki entries: create or update `.claude/docs/wiki/<domain>/<topic>.md` using the format in `skills/shared/docs-sync/references/wiki-format.md`.
- Session summary: if today's entry is missing or incomplete, write/append it now following the format in CLAUDE.md.
- Respect all token-economy rules from the docs-sync skill: tables over prose, no duplicates, no history.
- For each file touched, output exactly one line: "PATCHED <filepath>"
```

### Spawn conditionally (only if ADR candidates were detected):

**`software-architect`** at `.claude/agents/dev-team/software-architect.md`

```
You are performing a /devteam:learn ADR capture pass.

Load `skills/shared/adr/SKILL.md`.

ADR candidates identified this session:
[paste ADR candidates from Step 3]

For each candidate:
1. Run `bash .claude/dev-team-agents/scripts/new-adr.sh "<decision title>"` to create the file.
2. Fill in the template: Context, Decision, Consequences. Keep it factual — record what was actually decided, not what could have been decided.
3. Set status to `Accepted`.
4. Output: "ADR created: <filepath>"

Do not create ADRs for decisions that are easily reversible or purely implementation-level.
```

---

## Step 5 — Confirm

After all agents complete, output a summary of what was captured:

```
## Session knowledge captured

[list each file patched/created, one per line]

Run `/devteam:commit` to commit the knowledge base updates.
```

---

## $ARGUMENTS options

| Argument | Effect |
|----------|--------|
| _(none)_ | Full learn pass — all buckets |
| `docs` | Doc patches only — skip wiki and ADRs |
| `wiki` | Wiki entries only |
| `adr` | ADR candidates only |
| `--dry-run` | Show the classified plan only, do not spawn agents |
