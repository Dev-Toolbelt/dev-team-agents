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

## Cross-surface impact

<!-- One line per surface: "unchanged", or what changed and how it is covered. "not applicable — docs only" is a valid answer for the whole section. -->

| Surface | Impact |
|---------|--------|
| Providers (claude, opencode, codex) — render engine, installers, hook wiring | |
| CLI `--json` output (the desktop app's API, ADR-0014) | |
| Hooks (`scripts/hooks/`) — new exit-2 paths, markers | |
| `preferences.json` defaults and their mirrors (CLAUDE.md § User Preferences) | |
| Machine-local records (`MACHINE_LOCAL_RECORDS` and its mirrors) | |
| Desktop app (`app/`) | |
| Docs — README / README.pt-BR, CLAUDE.md, CHANGELOG | |
