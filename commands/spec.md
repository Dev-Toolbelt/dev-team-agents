---
description: Write the spec of a feature that already exists, verified against its behavior
argument-hint: <existing feature>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/shared/spec-gate/SKILL.md` — § Retroactive Spec is the rule this command runs, row by row; who sets each status and what each verdict means live there, not here.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

**MANDATORY:** the main conversation orchestrates this command and never edits the spec — `product-analyst` owns it. Spawned agents cannot ask the user: after **every** spawn below, relay its `## Open Decisions` and continue the same agent until its report has none, per the `interaction-patterns` skill § Sub-agent Question Relay. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

---

## Step 1 — Pick the feature

- `$ARGUMENTS` empty → ask which feature, in plain text (free-form input). Stop until answered.
- The feature is not in the code yet → stop and point to `/devteam:plan`; this command describes what is built.
- A spec for it exists under `docs/specs/`: `draft` → resume at Step 2; `approved` → resume at Step 3 only when no task under `docs/backlog/sprints/` cites it in `**Spec**:` — a planned spec is built through its tasks (spec-gate § Task Resolution), so point to the implementation commands or `/devteam:qa` and stop; `implemented` → ask **Validate it with `/devteam:qa`** / **Amend it** (Living Spec) / **Stop**. Never write a second spec for one feature.

## Step 2 — Draft and approval

Spawn `product-analyst` with the feature, its `<feature>` slug, and: "Write a retroactive spec per `spec-gate` § Retroactive Spec, rows Draft and Approve, from `.dev-team-agents/templates/spec-template.md`. Return every ambiguous behavior as an Open Decision, then the spec for approval."

The approval is one question: **Approve** / **Request changes** / **Stop**. Request changes → continue the agent with them and ask again. Stop → the spec stays `draft`; end the command (a re-run resumes here).

## Step 3 — Verify

Only once the spec is `approved`, spawn `qa-specialist`: "Run row Verify of `spec-gate` § Retroactive Spec on `docs/specs/<feature>.md`: one verdict per scenario ID. Change no file."

## Step 4 — Decide

Every `diverges` ID → one `AskUserQuestion` stating the scenario and what QA observed, with the two options of row Decide: **Describe current behavior** / **Keep the intended behavior**.

When any ID is described as built: continue `product-analyst` once with all of them, show the rewritten scenarios for one confirmation (**Confirm** / **Request changes**), then spawn `qa-specialist` again on those IDs only. A new `diverges` goes back to the top of this step.

## Step 5 — Tag and missing tests

Skip this step when `TESTS_REQUIRED=no` (resolved per `skills/shared/auto-routing/SKILL.md` § Test Gate), or when the spec's `touches` is empty — say which, and that the scenarios stay untagged.

Spawn one test author per `touches` layer, in parallel (`backend-test-specialist`, `frontend-test-specialist`, or `mobile-developer` in a tests-only spawn for Flutter/native): "Run row Tag of `spec-gate` § Retroactive Spec on `docs/specs/<feature>.md`. Tag existing tests only; write no new test."

Uncovered scenarios whose verdict is `matches` → ask once (a scenario kept as intended is a bug, never given a test here): **Write the missing tests (Recommended)** / **Not now**. Yes → continue the same authors to write them per row Tag, running only those tests. A failing new test returns its scenario to Step 4 as `diverges`, and the user decides whether that test is removed or kept for the `/devteam:fix` that follows.

## Step 6 — Close

1. Continue `product-analyst` for row Close: it sets the status from the latest verdicts.
2. Run `bash .dev-team-agents/scripts/spec-lint.sh`. An ERROR on this spec → continue `product-analyst` to fix it and run the lint once more; one still there is reported as open, never looped on.
3. Summary table: scenario · verdict · decision · test (tagged / written / none). The Agents table comes from returned run banners only (`skills/architecture/orchestration/SKILL.md` § Spawn Integrity).
4. Each scenario kept as intended → offer `/devteam:fix` with its ID and the observed behavior, in one `AskUserQuestion`. 5. Session summary and hand-off as `/devteam:fullstack` § Session close items 1 and 4.

When another command started this one, skip items 4 and 5: hand back to it with the spec path, the IDs kept as intended, and what QA observed for each.

---

**PLAN GATE — applies to every spawn that writes a file (`product-analyst`, and test authors writing new tests); the read-only `qa-specialist` verification and the tagging pass, which changes only test descriptions or one-line comments, are exempt:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision — a sub-agent returns that approval as an Open Decision (§ Sub-agent Question Relay).
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
