# ADR-0032: Bind writes provider-native ask rules for integration writes

**Date:** 2026-10-02
**Status:** Accepted
**Deciders:** dev-team-agents maintainers
**Relates to:** [ADR-0031](0031-agents-call-integration-apis-through-a-cli-proxy-that-holds-the-token.md) (closes the gap its Threat model names), [ADR-0022](0022-delegated-provider-installers-own-files-not-directories.md), [ADR-0007](0007-global-core-and-data-store-replacing-per-project-vendored-install.md)

## Context

ADR-0031 lets agents call an integration's API through `devteam integration call`. A write needs
`--allow-write`, but that flag is passed by the agent it guards. A prompt injection in an API
response can talk the agent into skipping the `AskUserQuestion` step the skill requires, and the
write then runs.

What closes that gap is a confirmation the agent cannot give itself: the provider's own approval
prompt. A hook cannot deliver it portably. The only hook signal all three providers honour is a
block (exit 2). Codex parses `permissionDecision: "ask"` but does not support it, and a decision it
does not recognise reportedly fails open. Each provider does, however, have a native permission rule
that prompts.

| Provider | Native rule | Matching | Where |
|---|---|---|---|
| Claude Code | `permissions.ask` | `*` anywhere; deny > ask > allow, so an ask beats a broader allow; still prompts in `bypassPermissions` | `.claude/settings.json` (project rules need no trust dialog) |
| opencode | `permission.bash` → `"ask"` | `*` anywhere; **the last matching key wins** | `opencode.json` / `.opencode/opencode.json` |
| Codex | `prefix_rule(..., decision="prompt")` | **prefix only**, token alternatives, no wildcard; the strictest decision wins | `.codex/rules/*.rules`, loaded **only for a trusted project** |

## Decision

### 1. The rules are written wherever the framework already wires a provider

| Provider | Who writes it | What is written | Removed by |
|---|---|---|---|
| claude | `bind`/`sync` through `hooks.wire` (the same `settings` manifest record as the hooks); the v2 `install.sh` | Ask rules merged into `permissions.ask` | `hooks.unwire`: the exact strings only |
| opencode | `install-opencode.sh`, after the `command` merge | Ask rules as the **last** `permission.bash` keys, re-appended on every run so they stay last | `unwire_opencode_commands`: the exact keys only |
| codex | `install-codex.sh` | `.codex/rules/devteam.rules`, a whole file of ours: an owned target in the ADR-0022 ledger | `unbind`, with the other owned files |

The rule text and the merges live in one module, `scripts/lib/devteam/permissions.py`. The bash
installers reach it through `scripts/lib/permission_rules.py`. A file that is not strict JSON, or
whose `permissions` / `permission.bash` has a shape we cannot merge into, is refused with exit 4 and
left untouched. The user's own rules are never edited.

### 2. The CLI fixes the form of a write

Codex can only match a prefix, so every rule keys on the method as the fourth word:
`devteam integration call <name> <METHOD>`. `call` refuses a `POST`, `PUT`, `PATCH` or `DELETE`
whose command line does not start that way. That rules out an option before the method and a
lower-case method, which would otherwise walk past the Codex rule. Reads keep any form.

On Claude and opencode, the rules also match `--allow-write` anywhere, as a second net.

### 3. `doctor` reports when a write would not ask

`devteam doctor` adds a `permissions` finding per bound provider:

- **Claude:** our rules are missing from `.claude/settings.json`.
- **opencode:**
  - our rules are missing;
  - a key listed after ours, which would override them;
  - an agent with its own `permission.bash`, which takes precedence over the global rules.
- **Codex:**
  - the rules file is missing or out of date;
  - the project is not trusted in `~/.codex/config.toml`, so Codex ignores the file.

### 4. The agent's own confirmation stays

The skill keeps its `AskUserQuestion` step. That step shows the before → after effect, which a
provider prompt cannot. The provider prompt is now the gate that does not depend on the agent.

## Consequences

- **Claude Code:** a write prompts the user in the provider's own dialog, even in `bypassPermissions`
  mode. A non-interactive `-p` run with permissions skipped denies the call instead.
- **opencode:** a write prompts. Answering "always" approves the pattern for the rest of the session,
  which is opencode's behaviour and not ours to change.
- **Codex:** a write prompts in a trusted project under `on-request`. `approval_policy = never`
  rejects it, which is the safe side. Whether `--dangerously-bypass-approvals-and-sandbox` skips
  prompt rules is **unverified**.
- **Not a sandbox.** A command spelled another way passes every provider's rule: `bash -c '…'`, the
  CLI run by path, `python3 …/devteam`. The providers' own documentation says this of every such
  rule. The CLI's form check, the forbidden endpoints of ADR-0031 and the audit line still apply.
- **Breaking change:** `call` no longer accepts a write in any form other than the canonical one. It
  shipped in no release before this one.
- **Adding a provider:** a new provider needs its own native rule. The tests key every per-provider
  map by `ALL_PROVIDERS`, so a provider added without one fails them.
