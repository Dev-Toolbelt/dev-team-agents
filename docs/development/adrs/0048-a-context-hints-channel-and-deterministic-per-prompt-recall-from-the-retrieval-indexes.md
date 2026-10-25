# ADR-0048: A context-hints channel and deterministic per-prompt recall from the retrieval indexes

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/hooks/lib/context-hints.sh`, `scripts/hooks/user-prompt-submit/05-recall.sh`, `scripts/lib/recall.py`, `opencode/plugin/dev-team-agents.ts`  
**Relates to:** [ADR-0038](0038-retrieval-indexes-for-the-wiki-and-adrs-are-checked-mechanically.md) (retrieval indexes), [ADR-0036](0036-path-scoped-and-severity-graded-rules-in-the-reuse-registry-enforced-at-stop-by-exit-2.md) (reuse registry), [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (machine-local records), [ADR-0018](0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md) (UserPromptSubmit hooks)

## Context

A project's knowledge already sits in three greppable indexes: the ADR index (`<adr-dir>/README.md`, ADR-0038), the wiki retrieval index (`docs/wiki/README.md`) and the reuse registry (`docs/development/reuse-guidelines.md`, ADR-0036). Reaching it depends on the agent obeying the Context Loading Order in `skills/shared/project-context/SKILL.md` and choosing the right keywords. Agents skip the lookup, or search with the wrong words, and then re-decide what an ADR already settled. ADR-0039 covers the Stop end of that gap; nothing covers the start of a task, when the decision is cheapest to respect.

The design is borrowed from trailhq/Trail-Code: deliver existing knowledge by deterministic code at the moment it matters, instead of asking the model to fetch it. Three later features (ADR-0051, ADR-0052) also need to put a short line in front of the agent from a hook, so the delivery path is decided once here.

## Decision

1. **Context-hints channel.** `scripts/hooks/lib/context-hints.sh` keeps a per-session pending-hints queue in the machine-local state dir, under a dot-prefixed name, so `paths.is_machine_local_record()` already classifies it without a new `MACHINE_LOCAL_RECORDS` entry. Hooks enqueue short hint lines; a delivery point drains them.
2. **Delivery per provider** (`providers.py:ALL_PROVIDERS`):
   - **claude** — a `UserPromptSubmit` hook's stdout is added to the model context. A hint raised in `PostToolUse` is emitted immediately through `hookSpecificOutput.additionalContext`.
   - **codex** — `UserPromptSubmit` stdout is added to the context, as on Claude. **Verified 2026-10-25** against `codex-rs/hooks/src/events/post_tool_use.rs, openai/codex commit 970111f6cb62`: a `PostToolUse` hook's `hookSpecificOutput.additionalContext` is parsed (`parse_post_tool_use`) and handed to the model, so a hint raised in `PostToolUse` is emitted immediately, exactly as on Claude. The shell tool is reported as `Bash` and the edit tool as `apply_patch` (`codex-rs/core/src/tools/hook_names.rs`).
   - **opencode** — `chat.message` stdout is dropped. The plugin (`opencode/plugin/dev-team-agents.ts`) captures lines prefixed `[DEVTEAM:RECALL]` and `[DEVTEAM:HINT]` and pushes them in `experimental.chat.system.transform`, the same mechanism that carries `[DEVTEAM:LANGUAGE]` today. `PostToolUse` hints are queued for the next prompt.
3. **Caps.** At most 5 lines and about 1200 characters per delivery; each pointer or hint is shown at most once per session.
4. **Prompt recall.** `scripts/hooks/user-prompt-submit/05-recall.sh` calls `scripts/lib/recall.py`, which matches the prompt against the three indexes: Accepted rows of the ADR index (directory resolved by the `new-adr.sh --dir` logic through `scripts/lib/docs_root.py`), wiki index rows (`path | keywords | read-it-when`), and reuse-registry rows (name, rule, scope).
   - **Relevance bar:** an entry is shown only with two shared keywords, or one keyword in its title or name. An unrelated entry never rides along.
   - Best first, at most 5, **pointers only** — path plus the one-line "read it when". Never the document body.
   - Output prefix `[DEVTEAM:RECALL]`.
5. **Fail-open and cheap.** Bash gates run before any python fork: prompt at least 12 characters, `recall_active` not `false`, at least one index present. Any error exits 0. Target under 150 ms typical.
6. **Preference** `recall_active`, default `true`, added to `scripts/lib/preferences-defaults.json` and its mirrors.

## Consequences

### Positive
- The decision that governs a task reaches the agent before work starts, whether or not the agent looks for it, on all three providers.
- One channel serves recall, repair hints (ADR-0051) and branch overlap (ADR-0052); a fourth producer adds no provider wiring.
- Output is a pointer, so context cost is bounded and constant regardless of how large the ADR or wiki entry is.

### Negative
- Keyword matching is lexical: a prompt in a different vocabulary than the index Keywords misses. Recall is only as good as the index rows ADR-0038 already lints.
- Every prompt pays the bash gates, and the python fork when they pass.
- On opencode a `PostToolUse` hint arrives one prompt late.

### Neutral
- The Context Loading Order stays in force; recall is a floor under it, not a replacement.
- Users can turn recall off per project with `recall_active: false`.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Rely on the Context Loading Order alone | That is the status quo whose misses motivated this ADR |
| Embedding or model-based retrieval | Needs a model call or a vector store per prompt, network or a heavy dependency, and is not deterministic; lexical match over curated keywords is enough at index sizes of tens to hundreds of rows |
| Inject the full matching document | Unbounded context cost; a pointer plus "read it when" lets the agent decide |
| A single-keyword match bar | Common words (`hook`, `test`) would attach unrelated entries to most prompts and teach the agent to ignore the line |
| Each feature writes to the context on its own | Three copies of the per-provider delivery logic, which drifts; the opencode capture would need three prefixes handled ad hoc |
| Queue `PostToolUse` hints on Codex | Was chosen while Codex's support was unverified; verified since, so immediate delivery is used (see the Codex line in Decision) |

**Amendment 2026-10-25.** Codex `PostToolUse` context injection verified (source above); delivery is decided by the payload's `hook_event_name`, not by an environment variable, in `devteam_hints_deliver` (`scripts/hooks/lib/context-hints.sh`).

**Amendment 2026-10-25 (untrusted text).** Hint and recall lines carry text read from project files, teammates' branch and author names, and tool output, so they are treated as data. Unicode format characters (bidi controls, zero-width characters, U+2028 and U+2029) are stripped from every `[DEVTEAM:HINT]` and `[DEVTEAM:RECALL]` line before delivery, so a line cannot hide text or break out of its own line. On opencode, where the lines are pushed into the system prompt, they are preceded by a framing line declaring that what follows is data, not instructions. `skills/shared/project-context/SKILL.md` § Untrusted Content names both prefixes.
