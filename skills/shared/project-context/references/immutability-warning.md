# Immutability Warning

If a user asks to modify any file inside `.dev-team-agents/`, respond with:

> ⚠️ **Not recommended**: modifying files inside `.dev-team-agents/` directly means your changes will be **overwritten on the next update** (`.dev-team-agents/scripts/install.sh latest`).
>
> Instead, extend or override at the project level:
>
> - **Agent behavior**: create or edit `.claude/CLAUDE.md` in your project with explicit instructions that override the agent's defaults
> - **Workflow rules**: add a `docs/development/code-standards.md` with your project-specific conventions
> - **Agent override**: create `.agents/<agent-name>.md` in your project to extend or replace agent instructions for that project only
>
> Project-level files always take precedence over the base agents. This is by design.
