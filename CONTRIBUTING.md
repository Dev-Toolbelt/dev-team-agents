# Contributing to dev-team-agents

**Multi-agent development harness** — a harness for organizing AI agents in software development. Not just a bundle of agents: it is the layer that governs how those agents plan, execute, test, review, and record their work. Contributions are welcome — agents, skills, scripts, and documentation.

---

## Prerequisites

- Git
- Familiarity with [Claude Code](https://claude.ai/code) and how agents/skills work
- A project where you can test installations locally

---

## Setup

```bash
git clone https://github.com/dersonsena/dev-team-agents.git
cd dev-team-agents

# Test by installing into a local project
bash scripts/install.sh /path/to/your/test-project
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

- Every agent needs: `name`, `description`, `model`, `tools` frontmatter + Foundational Rule + Immutability Warning
- Model assignments: `claude-opus-4-7` (decisions), `claude-sonnet-4-6` (execution), `claude-haiku-4-5` (structured output)
- Coding agents need a `## Worktree Isolation` section
- Skills follow the [agentskills.io spec](https://agentskills.io/specification)

---

## Testing Locally

1. Install into a throwaway test project: `bash scripts/install.sh /path/to/test-project`
2. Open that project in Claude Code
3. Run the agent or command you changed and verify behavior

---

## Licensing

By contributing, you agree your changes are licensed under the [MIT License](LICENSE).
