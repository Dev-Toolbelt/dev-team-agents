# Contributing to dev-team-agents

**Multi-agent development harness** — a harness for organizing AI agents in software development. Not just a bundle of agents: it is the layer that governs how those agents plan, execute, test, review, and record their work. Contributions are welcome — agents, skills, scripts, and documentation.

---

## Prerequisites

- Git
- Familiarity with at least one supported CLI — [Claude Code](https://claude.ai/code) (the default and reference implementation), [opencode](docs/install-opencode.md), or [OpenAI Codex CLI](docs/install-codex.md) — and how agents/skills work
- A project where you can test installations locally

---

## Setup

```bash
git clone https://github.com/dersonsena/dev-team-agents.git
cd dev-team-agents

# Test by installing into a local project (Claude Code — the default provider)
bash scripts/install.sh /path/to/your/test-project

# Or install for another provider — run these from the test project root
cd /path/to/your/test-project
bash /path/to/dev-team-agents/scripts/install-opencode.sh --source /path/to/dev-team-agents
bash /path/to/dev-team-agents/scripts/install-codex.sh    --source /path/to/dev-team-agents
```

---

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| New feature / agent / skill | `feature/<name>` | `feature/add-mobile-developer-agent` |
| Bug fix | `fix/<name>` | `fix/orphan-scan-false-positive` |
| Docs only | `docs/<name>` | `docs/update-workflow-steps` |

---

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/). Prefixes in use:

`feat` · `fix` · `refactor` · `docs` · `chore`

Do **not** include Claude attribution (`Co-Authored-By: Claude`, `🤖 Generated with Claude Code`) in commit messages or PR descriptions.

---

## PR Checklist

- [ ] `helpers/agent-lint.sh` passes (no frontmatter errors)
- [ ] `helpers/orphan-skill-scan.sh` shows no ACTION REQUIRED
- [ ] `README.md` and `README.pt-BR.md` are in sync (if either was changed)
- [ ] New agent files are ≤ 200 lines; new skill files are ≤ 500 lines
- [ ] `CLAUDE.md` was **not** modified (it is AI-only; human contribution rules go in this file)

---

## Authoring Standards

Rules for agents and skills live in `CLAUDE.md` under the **Authoring Standards** section. Key points:

- Every agent needs: `name`, `description`, `tier` frontmatter + Foundational Rule + Immutability Warning
- Agents never name a model. They declare a `tier` (`reasoning`, `backend-exec`, `frontend`, `repetitive`), which the render engine resolves to a per-provider model id via `scripts/lib/tiers.json` — edit that file to change a model, never the agent
- Coding agents need a `## Worktree Isolation` section
- Skills follow the [agentskills.io spec](https://agentskills.io/specification)

---

## Testing Locally

1. Install into a throwaway test project: `bash scripts/install.sh /path/to/test-project` (Claude Code — the default provider; use `install-opencode.sh` / `install-codex.sh` to test the other CLIs)
2. Open that project in the CLI you installed for
3. Run the agent or command you changed and verify behavior — commands are `/devteam:<name>` in Claude Code and opencode, `/prompts:devteam-<name>` in Codex CLI
4. Changes to `agents/`, `commands/`, or `scripts/lib/*.json` affect all three providers — re-render and re-check each one before opening the PR

---

## Licensing

By contributing, you agree your changes are licensed under the [MIT License](LICENSE).
