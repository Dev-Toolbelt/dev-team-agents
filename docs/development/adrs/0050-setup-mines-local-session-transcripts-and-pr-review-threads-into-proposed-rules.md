# ADR-0050: Setup mines local session transcripts and PR review threads into proposed rules

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/mining.py`, `skills/shared/history-mining/SKILL.md`, `agents/setup-assistant.md`, `scripts/lib/devteam/integrations/github.py`, `scripts/lib/devteam/integrations/__init__.py`  
**Relates to:** [ADR-0023](0023-integrations-are-account-level-connections-whose-network-calls-live-in-the-cli.md) (integration network calls), [ADR-0036](0036-path-scoped-and-severity-graded-rules-in-the-reuse-registry-enforced-at-stop-by-exit-2.md) (reuse registry), [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) / [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (`--json` contract), [ADR-0048](0048-a-context-hints-channel-and-deterministic-per-prompt-recall-from-the-retrieval-indexes.md) (recall)

## Context

Recall (ADR-0048) and `devteam check` (ADR-0049) only deliver what the indexes already hold. A newly bound project starts nearly empty, while its real conventions are already written down in two places nobody reads at setup: the corrections the user typed to agents in past sessions, and the review threads on merged PRs where a reviewer asked for a change and the author made it. The Correction Pattern Rule in `CLAUDE.md` catches a repeated correction only within one session.

## Decision

1. `devteam mine sessions --json` and `devteam mine reviews --json` in `scripts/lib/devteam/mining.py`. Both output **candidates only**.
2. **sessions** — one transcript reader per provider (`ALL_PROVIDERS`): claude `~/.claude/projects/<slug>/*.jsonl`, codex `${CODEX_HOME:-~/.codex}/sessions/**/rollout-*.jsonl`, opencode its local storage. A provider without a reader fails the per-provider fixture test.
   - Only messages the user typed: tool output, pasted content and headless runs are excluded.
   - A candidate is a correction or preference expressed on at least two distinct local days.
   - Secrets are scrubbed before output. No model call, no network.
3. **reviews** — inline review threads on the last 50 merged PRs that were resolved or outdated (the author changed the code), each tied to its file. Fetched through the GitHub integration adapter (ADR-0023); `gh` is a fallback only when the adapter cannot serve the request.
4. A new skill, `skills/shared/history-mining/SKILL.md`, drives proposing candidates one at a time via `AskUserQuestion` into a reuse-guidelines row (through the `/devteam:rule` flow), a wiki entry, or a preference (Correction Pattern Rule). **Nothing is written without the user's yes.**
5. `setup-assistant` references the skill from FIRST_RUN in one line; the agent is near its size ceiling, so the procedure lives in the skill.

## Consequences

### Positive
- A project's indexes start with rules it already follows, so recall and check have something to deliver from day one.
- Deterministic and offline for sessions; candidates are reproducible and reviewable.
- Every write passes through the user and an existing authoring flow, so the registry and wiki formats stay owned by their skills.

### Negative
- Transcripts are personal data on the user's machine. Reading them is local, never uploaded, and only user-typed text is considered, but the feature still widens what the CLI reads.
- Transcript formats are provider internals and can change without notice; a reader that fails returns no candidates rather than an error.
- Lexical correction detection misses corrections phrased without the marker patterns.

### Neutral
- Review mining needs a configured GitHub integration or `gh`; without either it reports nothing.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Summarize transcripts with a model | Cost, non-determinism, and sending private transcripts to a model call the user did not ask for |
| Write candidates directly into the registry | A false positive becomes a mandatory rule; consent per candidate is the safeguard |
| Mine all PR comments | Unresolved or debated comments are not settled conventions; resolved or outdated threads show the author acted on them |
| Call `gh` directly for reviews | Bypasses ADR-0023, which makes integrations own their network calls and credentials |
| One-occurrence threshold for session candidates | A single correction is often task-specific; two distinct days separates a habit from a one-off |

## Open Points

- **opencode legacy JSON storage is unverified.** The reader for the older layout (`storage/message/<session>/msg_*.json`, `storage/part/<message>/prt_*.json`) has no install to test against. The SQLite `opencode.db` reader is verified against a live install. Until the legacy layout is confirmed, a project whose history lives only in it gets no session candidates, and no error is raised.

## Amendment 2026-10-25

- **Applies to** now also lists `scripts/lib/devteam/integrations/github.py` and `scripts/lib/devteam/integrations/__init__.py`, which carry the review-thread request of Decision 3.
- **"Last 50 merged PRs" is approximate.** The GitHub query sorts merged PRs by `UPDATED_AT`, because the API offers no merge-date ordering; a PR merged earlier but commented on later can displace one merged more recently. Accepted: the goal is a recent sample of settled conventions, not an exact window.
- **Bounded reads.** Each provider's reader stops at a per-provider message cap, and the output reports per provider how many transcript files were skipped as unreadable or malformed, so an empty result can be told apart from a failed read.
- **Claude transcripts are matched by recorded cwd.** A transcript under `~/.claude/projects/<slug>/` is used only when the `cwd` recorded in its messages is this project, since the slug encoding is lossy and two paths can share one.
