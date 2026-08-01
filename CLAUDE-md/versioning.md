## Versioning

Semantic versioning via git tags: `v1.0.0`, `v1.1.0`, `v2.0.0`.

| Bump | When | Real examples |
|------|------|---------------|
| **major** | A **contract breaks**: a skill or agent is removed, an installed path moves, an install/update flow stops working without manual intervention, or an existing project's behavior changes after an update without the user asking | — |
| **minor** | New agents or skills; a new mandatory rule that every agent must follow; changed defaults that apply to **fresh installs only**; a new provider or a new command | `v2.21.0` per-agent effort overrides · `v2.22.0` effort override extended to opencode and Codex · `v2.23.0` scoped-test rule made foundational, spawn integrity, changed install defaults |
| **patch** | Fixes, clarifications, doc updates, script patches — including a fix that adds behavior to every agent when it corrects something already specified | `v2.20.2` the closing run banner every agent now emits · `v2.22.1`/`v2.22.2` corrections to that fix |

**"Agent behavior change" alone is not a major bump.** This line used to read *"Breaking changes (agent behavior changes, removed skills) → major"*, which taken literally made almost every release a major — the repo never applied it that way. `v2.20.2` added a mandatory new emission to all 17 agents as a **patch**, and `v2.21.0` changed how five specialists reason as a **minor**. The parenthetical meant *breaking* agent behavior changes; it is spelled out above so the next release does not have to re-litigate it.

**The test that decides major:** does an existing installation behave differently after an update, without its user asking for it? If yes, major. Changed values in `scripts/lib/preferences-defaults.json` do **not** qualify on their own — an existing `preferences.json` is never rewritten, and consent keys are never backfilled as enabled (see [`preferences.md`](preferences.md)). If a future change does rewrite existing user state, that is a major regardless of how small the diff looks.
