---
model: haiku
---

You are running the **`/devteam:health-check`** command. Load `skills/shared/setup-health-check/SKILL.md` — it contains the 9 check categories, fix patterns, and output format. Load `skills/shared/output-format/SKILL.md` for the platform-agnostic output standard (pure markdown, no box-drawing Unicode, no decorative symbols). Apply it to ALL output produced by this command.

---

## Step 0 — Detect provider

Run each detection command; the first one that succeeds determines the active provider:

```bash
# Claude: .claude/settings.json is the primary Claude Code config file
[ -f .claude/settings.json ] && echo "claude" && exit 0
# opencode: opencode.json(c) is the primary config
ls .opencode/opencode.json .opencode/opencode.jsonc 2>/dev/null | head -1 | xargs -I{} echo "opencode:{}" && exit 0
# Codex: .codex/hooks.json is the primary hook config
[ -f .codex/hooks.json ] && echo "codex" && exit 0
# Fallback — neither provider detected
echo "unknown"
```

Store the result as `<provider>`. If `<provider>` is `unknown`, output:

```
Health check scope limited: no known provider config found
(.claude/settings.json, .opencode/opencode.json, .codex/hooks.json).
Running provider-agnostic checks only.
```

---

## Step 1 — Run health check categories

Run the 9 health check categories from `setup-health-check/references/checks-list.md` **in order**, following the same flow:

1. Symlinks
2. Scripts & Executability
3. User Data & Legacy Paths
4. settings.json / provider config
5. Graphify (skip if not enabled)
6. CLAUDE.md / AGENTS.md
7. .gitignore
8. User Preferences
9. Notifier

For **Category 4**, adapt the check to the detected provider:

- **claude**: check `.claude/settings.json` as documented in `checks-list.md` — hook dispatchers, `includeCoAuthoredBy`, no stale direct hook paths
- **opencode**: check `.opencode/opencode.json` — the `devteam:*` command entries are present under the `command` key, the plugin is at `.opencode/plugins/dev-team-agents.ts`. **Also verify agent model/variant mapping**: each `.opencode/agents/*.md` file must have `model:` and `variant:` in its frontmatter matching the tier-based resolution from `.dev-team-agents/scripts/lib/tiers.json`. If any agent is missing these fields, re-render by running `bash .dev-team-agents/scripts/install-opencode.sh` as auto-fix.
- **codex**: check `.codex/hooks.json` — the 4 managed hook entries (SessionStart, PreToolUse, Stop, PreCompact) are present and point to valid script paths; check `.codex/skills/` for generated `devteam-*` skill dirs with `SKILL.md` and `name: "devteam-*"` frontmatter; flag any leftover `devteam-*.md` prompt aliases under `.codex/prompts/`; verify agent model/effort mapping in `.codex/agents/*.toml` against `.dev-team-agents/scripts/lib/tiers.json` (including `agent_effort` overrides).

---

## Step 2 — Apply auto-fixes

For each category result:
- `✅ OK` — no action
- `⚠️ WARN` — apply fix silently (additive changes only)
- `🔧 FIX` — show diff for `settings.json` changes and ask confirmation; apply all others silently

Follow the fix patterns from `setup-health-check/references/fix-patterns.md`.

---

## Step 3 — Report summary

Present the results using the output-format standard (no box-drawing, no decorative symbols):

```
## Health Check — dev-team-agents

### Provider
[claude / opencode / codex]

### Results
| Category | Status |
|---|---|
| Symlinks | ✅ OK |
| Scripts | ⚠️ WARN (1 script not executable — fixed) |
| ... | ... |
| Notifier | ✅ OK |

### Actions taken
- [chmod +x .dev-team-agents/scripts/hooks/stop.sh]
- [settings.json — consolidated stale hooks into dispatcher]
- ...

### Recommendations
- [if any items require user action]
```

If all categories pass with no warnings or fixes:

```
Health Check: all categories passed. dev-team-agents is healthy.
```
