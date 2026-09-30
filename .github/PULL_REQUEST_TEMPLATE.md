## Summary

<!-- What does this PR do? 1-3 bullet points. -->

## Type of change

- [ ] New agent
- [ ] New skill
- [ ] New command
- [ ] Bug fix
- [ ] Refactor
- [ ] Docs / templates
- [ ] Scripts / hooks

## Checklist

- [ ] `helpers/agent-lint.sh` passes (no frontmatter errors)
- [ ] `helpers/orphan-skill-scan.sh` shows no ACTION REQUIRED
- [ ] New agents are ≤ 200 lines; new skills are ≤ 500 lines
- [ ] `README.md` and `README.pt-BR.md` are in sync (if either was changed)
- [ ] `CHANGELOG.md` [Unreleased] section updated (if user-visible behavior changed)
- [ ] Provider parity: a change to provider-facing behavior is implemented and tested for every provider in `providers.ALL_PROVIDERS` (claude, opencode, codex), or the PR says which one is excluded and why
- [ ] No Claude attribution in commit messages or PR description
