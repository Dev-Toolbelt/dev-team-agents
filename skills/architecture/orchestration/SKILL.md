---
name: orchestration
description: Delegation mechanics — execution gate, autonomous sprint protocol, agent roster, spawn rules.
---

# Orchestration

Reference material for an agent that plans work and delegates every implementation step to
specialized subagents via the Task tool. The orchestrator never writes implementation code.

---

## Execution Strategy Gate

**Mandatory step between plan approval and execution.** Present it before executing any step.

Load `skills/shared/interaction-patterns/SKILL.md` for the quiz structure.

1. Read worktree preferences:
   ```bash
   python3 -c "import json;d=json.load(open('.dev-team-agents/user-data/preferences.json'));print(json.dumps({k:d.get(k) for k in['worktree_active','worktree_base_branch','worktree_path','worktree_docker_isolate']}))" 2>/dev/null
   ```
   Defaults if unreadable: `worktree_active=true`, `worktree_base_branch` = auto-detected,
   `worktree_path=.worktrees`, `worktree_docker_isolate=true`.

2. Determine the recommendation:
   - `worktree_active == true` → **Isolated worktree** (first option)
   - `worktree_active == false` → **New branch** (second option)
   - key absent → **Isolated worktree**

3. Present the quiz via `AskUserQuestion` with 4 options: **Isolated worktree (Recommended)**,
   **New branch**, **Current branch**, **Other**. Translate the labels and descriptions to the
   user's language (`preferences.json` → `language`, default `en`). Interpolate the actual
   `worktree_base_branch`, `worktree_path`, and `worktree_docker_isolate` values into the
   recommended option's description.

4. Act on the choice:
   - **Isolated worktree** → execute the full worktree setup flow (`skills/shared/worktree/SKILL.md`)
   - **New branch** → ask for a branch name, run `git checkout -b <name>`
   - **Current branch** → proceed directly
   - **Other** → ask the user to describe their approach

5. Announce the chosen strategy, then proceed to execution.

---

## Autonomous Sprint Protocol

Activates when the user signals fully autonomous execution — "execute everything autonomously",
"don't ask me", "just tell me when it's done", "autonomous sprint", or equivalent in any language.
In this mode the Execution Strategy Gate quiz is **skipped entirely** — resolve everything silently.

1. **Auto-resolve the worktree** — read `preferences.json` (same command as above) without asking:
   - `worktree_active` is `true` or absent → create an isolated worktree + Docker stack
     (`skills/shared/worktree/SKILL.md`, full setup)
   - `worktree_active` is `false` → create a new branch: suggest a name, `git checkout -b <name>`

   **Announce the resolution immediately after, in one line, before spawning anything** — silent
   resolution is not silent execution: `"Isolated worktree at <worktree_path> on branch <branch>,
   Docker stack isolated."` or `"New branch <branch>, no worktree isolation (worktree_active=false)."`
   This is the autonomous-mode equivalent of Execution Strategy Gate step 5 (*Announce the chosen
   strategy*) — the mode being unattended is why the decision needs to be visible, not why it can be
   skipped.

2. **Write the session file BEFORE spawning any subagent**:
   ```bash
   echo "worktree=<yes|no> branch=<branch>" > .dev-team-agents/.worktree-session
   ```

3. **Spawn subagents with worktree context** — every Task prompt MUST carry `WORKTREE_PATH=<path>`,
   `BRANCH=<branch>`, and: "All file operations MUST target the WORKTREE_PATH. Do NOT write files
   in the main repo root."

4. **Scoped test execution** — never instruct a subagent to run the project's full test suite, and
   never pass "run the tests" unqualified. Each subagent runs the tests covering what it touched,
   per `skills/shared/scoped-test-execution/SKILL.md`. Only relay a full-suite run when the user
   asked for one in this session — and then say so explicitly in the spawn prompt.

5. **Automatic review cycle** — after all implementation subagents finish, spawn `code-reviewer`
   then `qa-specialist`. Resolve any findings in a new round autonomously; do not ask the user.

6. **Final notification** — notify only when implementation, review, QA, and the consolidated
   summary are all complete.

> **Critical**: subagents have no shell access and cannot create worktrees or branches. The
> worktree/branch MUST exist in the orchestrator's context before any subagent is spawned, and the
> path MUST be passed in every spawn prompt.

---

## Progress Visibility

A silent orchestrator running many sequential steps unattended is indistinguishable, from the
user's side, from one that has stalled or died. "Notify only at the end" (step 6 above) governs
the *final* handoff — it does not license silence in between.

**After every subagent in an autonomous sprint returns, emit one short visible line before
continuing to the next step**: `<agent> — <step> done (<one-clause result>). Continuing to
<next step>.` This is a log line, not a report — it must not repeat the subagent's full summary
or dump file contents (see *Subagent Report Economy*). Its only job is to give the user a
heartbeat they can see without asking.

**Never claim progress the orchestrator cannot ground in something it just observed.** A status
line like "6 tests still failing" or "committed and moving to the next step" must be backed by
the subagent's returned banner/report or a command the orchestrator itself ran (`git log`, `git
status`, test output) — not inferred from what the plan says *should* have happened by now. If
asked for status mid-sprint and nothing has changed since the last checkpoint line, say exactly
that — do not narrate invented progress to fill the gap. This includes the specific case of a
subagent that has not yet returned at all: see *Spawn Integrity* check 4 (Liveness) for what to say
instead of "still running."

This adds negligible token cost (one short line per completed step) against the cost of a user
losing trust in the run and needing to manually re-verify the repository state, which is what
prompted this rule.

---

## Agent Roster

Each agent's model is resolved from its tier plus the active provider at runtime
(`.dev-team-agents/scripts/lib/tiers.json`). The subagent auto-announces its model via the
model-identity skill — the orchestrator never names a model.

| Agent | Tier | Role |
|---|---|---|
| `backend-developer` | `backend-exec` | Server-side implementation |
| `frontend-developer` | `frontend` | Client-side implementation |
| `mobile-developer` | `backend-exec` | Mobile implementation |
| `database-specialist` | `backend-exec` | Schema, queries, migrations |
| `devops-specialist` | `backend-exec` | Docker, CI/CD, deploy |
| `security-specialist` | `reasoning` | Security audit, compliance |
| `backend-test-specialist` | `backend-exec` | Backend test coverage |
| `frontend-test-specialist` | `frontend` | Frontend test coverage |
| `code-reviewer` | `backend-exec` | Code review routing |
| `backend-reviewer` | `backend-exec` | Backend PR review |
| `frontend-reviewer` | `frontend` | Frontend PR review |
| `qa-specialist` | `backend-exec` | Behavioral validation |
| `technical-writer` | `repetitive` | Documentation |
| `product-analyst` | `reasoning` | Business requirements |
| `ui-ux-designer` | `frontend` | Design system, UX |
| `seo-specialist` | `frontend` | SEO quality gate, GEO/LLM readiness |

Canonical agent path: `.claude/agents/dev-team/<agent-name>.md` for every row above.

The roster is validated against `agents/` by `helpers/agent-lint.sh` — a row naming an agent that
does not exist, or declaring the wrong tier, fails the lint.

---

## Spawn Integrity

**A spawn that did not happen must never be reported as one that did.** Three checks, in order,
around every delegation round. They exist because the failure they prevent is silent: the user
reads a completion report, the UI shows no running work, and nothing was written to disk.

### 1. Preflight — is the Task tool actually available to you?

Check your own tool list before the first spawn. **If the Task tool is not there, stop.** Report
this and end your turn:

> Cannot delegate: the Task tool is not available in this context. No subagents were spawned and
> no work was done. Run this from the main conversation, or invoke the specialist agents directly.

Do not continue. Do not describe what the subagents would have done. Do not emit a consolidated
summary. An orchestrator with no Task tool has produced nothing.

**Nested delegation is where this bites.** An orchestrator that is itself running as a subagent may
not have the Task tool at all — the provider decides, not this skill. Never assume you have it
because the skill describes using it.

### 2. Name validation — roster names only

Every `subagent_type` you pass MUST appear verbatim in the Agent Roster above. Do not invent a
name, shorten one, or infer one from the role — `test-author`, `test-writer` and `api-dev` are not
agents. If the role you need has no roster row, delegate to the closest row or ask the user; never
guess. An unknown type makes the spawn fail, and a failed spawn narrated as a success is
indistinguishable from check 1's failure.

### 3. Evidence — every claimed spawn carries its returned run banner

Each subagent emits a model-identity run banner in its **final** message
(`skills/shared/model-identity/SKILL.md`), and that final message is the only thing that reaches
you. The banner is therefore proof of execution: **no banner returned means that agent did not
run.**

Fill the summary from what came back. A subagent that returned no banner is reported `NOT RUN`.
Never compose a banner yourself to fill the row — writing evidence you did not receive defeats the
only check that can catch a phantom spawn.

### 4. Liveness — "still running" is a claim, not a default

The Task tool is asynchronous and this skill has no poll/heartbeat primitive: the only signal that
a spawned subagent produces is its final returned message. Nothing distinguishes "still executing
normally" from "stalled or died silently" until that message arrives — so never fill that gap by
asserting the agent is still running. That is invented progress, exactly what *Progress Visibility*
already forbids for status lines; this check applies the same rule specifically to liveness claims.

Note the wall-clock time of each spawn. If the user asks for status and no return has arrived:

- **Before treating a spawn as stalled, actually call the status tool.** On Claude Code that means
  `TaskList` (or `TaskGet`/`TaskOutput` for the specific task id if you have it) — call it and read
  the result before saying anything about liveness. Do not skip straight to guessing, and do not
  substitute a re-read of the plan or your own last message for an actual tool call.
- **If no such check is available, or it returns nothing new**, say exactly that — do not say
  "still running." State the elapsed time since spawn and that no completion signal has been
  received, e.g.: "No update from `<agent>` since it was spawned <elapsed>. I cannot confirm it is
  still executing — only that no return message has arrived." Offer to re-spawn if the elapsed time
  is unreasonable for the task.
- **Never re-assert a previous "in progress" claim as new information.** Each time the user asks,
  re-derive the answer from what has actually been observed since the last checkpoint, not from
  what you last told them.

### 5. Auto-reactivation — schedule the checkback, don't wait to be asked

Check 4 fixes what the orchestrator *says* about liveness. It does not fix the underlying gap: with
no poll/heartbeat primitive, a subagent that stalls or a round the user stopped watching stays
silent until someone manually asks for status — in practice, the user re-prompting the orchestrator
every time. That burden belongs to the orchestrator, not the user.

**Whenever a delegation round leaves any subagent without a returned banner and the orchestrator's
own turn is about to end**, schedule a follow-up instead of ending silently:

- If `ScheduleWakeup` is available, call it before ending the turn: `delaySeconds` in the 1200–1800s
  range for routine rounds (tighter, matched to expected duration, only for work with a known
  short bound — see the tool's own guidance), `reason` naming which agent(s) are still outstanding.
  Do not schedule a wakeup to poll something a `Monitor`-tracked task will already notify you about
  — this is specifically for rounds with no other wake signal.
- On that wakeup, call the actual status tool (`TaskList`/`TaskGet`/`TaskOutput`) before doing
  anything else — same rule as check 4, no guessing.
- If a subagent still shows no return and enough wall-clock time has passed for its task, resume it
  directly (`SendMessage` to its agent id, per the Agent tool's continuation mechanism) with a short
  nudge to continue and report — do not silently re-spawn a duplicate, and do not fabricate progress
  in the meantime.
- If it has returned, fold the result into the summary per check 3 and stop rescheduling for that
  agent.
- **Cap it.** Two reactivation attempts per stalled agent is the default ceiling — past that, stop
  scheduling and surface it to the user as a real blocker ("`<agent>` has not reported back after two
  checkbacks over `<elapsed>` — want me to re-spawn it or investigate directly?") rather than looping
  indefinitely.

If `ScheduleWakeup` is not available in the current context, this check cannot be satisfied — fall
back to check 4's reactive behavior and say so if asked, rather than claiming a checkback is
scheduled when none was.

### 5. Periodic status table

While background sub-agents are working, load `skills/shared/work-feedback/SKILL.md` and follow it
for the check-in cadence and table format — gated entirely by `credentials.local.json`
(`work_feedback_active`, `work_feedback_interval_minutes`). Do not restate its gate check, loop
mechanics, or table format here.

---

## Background Process Discipline

Bash commands run with `run_in_background: true` are a different asynchronous primitive than Task
spawns, but the same failure mode applies: a background command nobody is watching produces the
same stalled-looking pile as an un-followed-up subagent.

- **Never open a new `sleep`/poll-loop Bash command to re-check something already being waited
  on.** A background command already running (a build, a test suite, a migration) has exactly one
  legitimate way to be watched: `Monitor` on that same command. Do not start a second
  `run_in_background` shell whose only job is to poll the first one's state.
- **Before starting any new background wait, check whether one is already outstanding for the same
  purpose** (recent tool calls this turn/session). If one exists, `Monitor` it instead of starting
  another.
- **A background command is not fire-and-forget.** Once started, either await it inline (if the
  answer is needed before continuing) or call `Monitor` so its completion produces a notification.
  Starting it and moving on without either is the Bash-side version of the gap Spawn Integrity
  check 5 closes for subagents.

---

## Subagent Report Economy

A subagent's final message is the only thing that reaches the orchestrator's context (see check 3
above) — every other line it produced along the way is invisible to you but still cost real tokens
to generate. That final message must be a **report**, not a transcript: what was done, key
decisions, files touched, and the run banner. Nothing else.

Every spawn prompt MUST include this instruction **verbatim, as the literal closing line of the
prompt text** — not a paraphrase, not a reference to a skill the subagent is trusted to recall:

> Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in
> your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise
> report only: files changed (paths, no diffs), key decisions and why, and anything the user must
> know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps.

Inlining it here, at spawn time, is not redundant with the same instruction already living in the
subagent's own `## Before You Finish` section (per CLAUDE.md's Run Banner Rule). It is the fix for
a specific, observed failure: `skills/shared/model-identity/SKILL.md` documents the closing banner
being dropped in 6 out of 6 multi-message runs when the only copy of the instruction is the one the
subagent read once, at the start of a long task, inside its own static definition. An instruction
placed fresh in the spawn prompt — right next to the report-shape instruction the subagent is about
to follow anyway — sits at the point of generation instead of buried behind everything the task did
in between. Every `commands/*.md` file that spawns an agent carries this exact line inline in its
`**MANDATORY:**` spawn instruction; do not add a new command that spawns via Task without it.

This is not optional politeness — a verbose subagent report multiplies across every parallel spawn
in a round, and the orchestrator's own consolidated summary compounds on top of it. Applying
`skills/shared/token-efficiency/SKILL.md` to what the subagent *reads* still leaves its *output*
unbounded; this rule closes that gap.

---

## Spawn Prompt Economy

Report Economy above bounds what a subagent sends back. These two rules bound what the
orchestrator sends it in the first place — the input side of the same round-trip.

### Pass condensed context, not a re-read instruction

By the time a plan is approved, the orchestrator has already loaded and synthesized
`skills/shared/project-context/SKILL.md`'s Context Loading Order (stack, conventions, relevant
ADRs, active constraints). A spawn prompt that just tells the subagent to "load project context"
makes it redo that synthesis from raw files, and every subagent in the same parallel round repeats
it independently.

Instead, inline what you already know into the spawn prompt: the relevant stack facts,
conventions, and any ADR decisions that bear on this subagent's slice of work — a few lines, not a
file dump. The subagent still has the repository if it needs to go deeper; this only removes the
redundant re-derivation of what the orchestrator already established. Never omit the load
instruction entirely — condensed context is a head start, not a replacement for the subagent's own
Foundational Rule.

### Reference the plan file, don't paste the plan

When the approved plan exists on disk (e.g. saved by `/devteam:plan`), spawn prompts for a `Par.`
group MUST pass the **file path and the specific section/step** that agent owns, not the plan text
inlined into the prompt. Pasting the full plan into every parallel spawn multiplies its token cost
by the number of agents in the round for content each agent mostly doesn't need — its own step is
usually a fraction of the document.

If the plan was only ever presented in-conversation and never written to disk, inlining the
relevant excerpt is the fallback — but prefer writing it to a file first when the round has more
than one or two parallel spawns.

---

## Orchestration Flow

1. **Classify the scope**:

   | Scope | Delegate to |
   |---|---|
   | API, services, business logic | `backend-developer` |
   | UI, components, pages | `frontend-developer` |
   | Backend + frontend | both of the above |
   | Schema, migrations, queries | `database-specialist` |
   | Mobile (native or cross-platform) | `mobile-developer` |
   | Docker, CI/CD, deploy | `devops-specialist` |
   | Auth, encryption, compliance | `security-specialist` |
   | Tests (after implementation) | `backend-test-specialist` / `frontend-test-specialist` |

   If the scope is unclear, ask the user which areas to delegate.

2. **Spawn via the Task tool.** Each prompt must include: the task description from the closed
   scope; `WORKTREE_PATH=<path>` and `BRANCH=<branch>`; references to `docs/development/`
   (`architecture.md`, `tech-stack.md`, `code-standards.md`) and any relevant ADR; and the
   instruction: "Read the architecture documents before implementing, then load
   `skills/shared/model-identity/SKILL.md` and announce your model. All file operations MUST target
   WORKTREE_PATH — never write files outside this directory."

3. **Spawning rules:**
   - Agents with no dependency on each other MUST be spawned in **parallel**
   - Schema before backend: `database-specialist` completes before `backend-developer` starts
   - Tests run after their implementation agent completes
   - Log what each agent did as it completes; capture output for the summary

4. **Consolidated summary** after all agents complete. The Agents table is an **evidence record,
   not a recollection** — every row is filled from what the subagent actually returned, per
   *Spawn Integrity* check 3:

   ```markdown
   ## Implementation Complete

   ### Agents spawned
   | Agent | Model (from its returned banner) | Result |
   |---|---|---|
   | `backend-developer` | `sonnet` | what it reported doing |
   | `frontend-test-specialist` | — | NOT RUN — no banner returned |

   ### Documents produced / modified
   [list]

   ### Next steps
   Run `/devteam:review` for code review and QA handoff.
   ```

   If every row reads `NOT RUN`, that is the headline: the task was not executed. Say so first,
   before anything else — do not bury it under a summary of intended work.
