# File Structure

Companion section of [`CLAUDE.md`](../CLAUDE.md): the repository tree and the two `helpers` directories.

```
dev-team-agents/
├── agents/          ← agent definitions (.md)
├── app/             ← Electron desktop client, a pure CLI client (ADR-0015); DEV-ONLY, dropped by install.sh's KEEP_ROOT
├── skills/          ← modular skill knowledge
│   ├── shared/      ← foundational rules used by all agents
│   ├── architecture/
│   ├── database/
│   ├── design/
│   ├── devops/      ← one skill per platform
│   ├── integrations/ ← platform/integration-specific reference skills
│   ├── legacy/      ← survival guides for legacy codebases (jquery)
│   ├── mobile/
│   ├── security/
│   ├── skill-creator/ ← user-invocable skill-authoring skill
│   ├── testing/
│   ├── third-party/ ← vendored upstream skills, pinned in sources.json (ADR-0047); never edited in place
│   └── ui-libraries/ ← UI component library reference skills
├── commands/        ← devteam slash commands (installed to .claude/commands/devteam/, invoked as /devteam:<name>)
├── templates/       ← document templates: adr, plan, runbook, spec, contract, and the gated-layout docs (prd, glossary, nfr, trd, data-model, threat-model, design-flow, evals, process)
├── CLAUDE-md/       ← companion sections of this file (preferences, notifications, user-data,
│                      versioning, hooks, commands, cli, file-structure)
├── plugins/         ← optional per-project integrations; see plugins/README.md and ADR-0019
│   ├── _schema/plugin.schema.json  ← manifest schema
│   └── graphify/    ← reference plugin: code graph builder
├── docs/            ← repository-level reports and internal docs (NOT installed to user projects)
│   ├── agents.md · agents.pt-BR.md            ← canonical agent reference
│   ├── installation.md · installation.pt-BR.md ← installation and advanced options guide
│   ├── install-claude.md · install-codex.md · install-opencode.md ← per-provider install guides
│   ├── providers.md     ← provider matrix and tier → model id map
│   └── reports/         ← audit reports and fingerprint index
├── helpers/         ← DEV-ONLY authoring tools, never shipped (see "Two helpers directories" below)
│   ├── agent-lint.sh              ← agent frontmatter (name/description/tier/model) +
│   │                                model↔tiers.json↔run-banner drift + skill
│   │                                identity (name == dir, unique) + quiz-first +
│   │                                orchestration roster ↔ agents/ (name + tier, both ways)
│   ├── size-limits.sh             ← agents 211 (200 content + run-banner + Before You Finish) · commands 200 · skills 500
│   ├── orphan-skill-scan.sh       ← repairs broken skill paths; never deletes
│   ├── orphan-template-scan.sh    ← template references must RESOLVE, not just be mentioned
│   ├── plugin-lint.sh             ← validates plugin manifests against schema; runs in CI
│   ├── canonical-facts.py         ← fails on claims known to be wrong (facts in canonical-facts.json); runs in CI
│   ├── third-party-skills.py      ← vendors skills/third-party/ at the pinned commit (sync) and checks their hashes (verify)
│   ├── gen-cpanel-uapi-reference.sh ← regenerates the cPanel skill's generated UAPI
│   │                                reference from the official OpenAPI spec (`--check` = drift)
│   └── archive-index.sh · check-fingerprint-uniqueness.sh ← report-index rotation and
│                                    global fingerprint uniqueness across live + archives
├── opencode/        ← opencode provider plugin source (plugin/dev-team-agents.ts); stripped at install,
│                      fetched on demand by install-opencode.sh / install-provider.sh
├── scripts/
│   ├── cli/devteam  ← v3 CLI entry point (python3); see CLAUDE-md/cli.md
│   ├── install.sh · update.sh · rollback.sh   ← install / update / rollback lifecycle
│   ├── install-cli.sh                ← macOS/Linux CLI bootstrap into ~/.local (ADR-0028); stripped from the package
│   ├── install-provider.sh · install-opencode.sh · install-codex.sh ← multi-provider installers
│   ├── render-provider.sh         ← renders the canonical source into a provider-specific tree
│   ├── check-codex-compat.sh      ← lints rendered Codex output for forbidden terms
│   ├── migrate-to-root.sh         ← migrates .claude/dev-team-agents/ → .dev-team-agents/
│   ├── fix-symlinks.sh · check-updates.sh (on-demand v2 update check) · new-adr.sh · doc-path.sh (docs layout map lookup) · docs-migrate.py (opt-in docs layout migration)
│   ├── graphify-refresh.sh (deprecated wrapper) · validate-commit-msg.sh · reuse-lint.sh · spec-lint.sh · index-lint.sh · design-token-lint.sh
│   ├── lib/         ← render-engine data, shared install logic, and the v3 CLI package
│   │   ├── devteam/ ← v3 CLI implementation: paths · lock · jsonio · project · registry ·
│   │   │              versions · providers · gitignore · bind · migrate · doctor ·
│   │   │              quarantine · update · output · errors · global_skills · integrations · permissions · plugins · cli
│   │   ├── tiers.json             ← CANONICAL tier → provider model id map (+ per-provider effort)
│   │   ├── global-skill-roots.json ← CANONICAL map of the providers' global skill dirs (`devteam skills`, ADR-0020)
│   │   ├── commands.json · command-map.json · tool-map.json ← renderer metadata
│   │   ├── preferences-defaults.json ← defaults written into user-data/preferences.json
│   │   ├── render_provider.py     ← render engine
│   │   ├── strip-tarball.sh       ← single source of truth for the package strip rules
│   │   ├── installer-fetch.sh     ← shared ref-pinned download + payload verification
│   │   │                            (update.sh, rollback.sh, the auto-update hook path)
│   │   ├── telemetry-guard.sh     ← single fail-closed definition of _telemetry_enabled
│   │   ├── python.sh              ← resolves `python3` to a working Python 3.9+ (Windows Git Bash: python / py -3)
│   │   ├── docs_root.py · docs-root.sh ← single resolver of the docs write root (context_paths[0])
│   │   ├── doc-layouts.json ← docs layout map: one owning doc per fact category, per layout (ADR-0045)
│   │   ├── provider-ownership.sh  ← which paths the opencode/Codex installers may write (ADR-0022)
│   │   └── ensure-claude-framework.sh
│   ├── helpers/     ← SHIPS and runs in user projects — telemetry-send.sh (called by install.sh, update.sh)
│   └── hooks/       ← session-start.sh, pre-compact.sh + pre-tool-use.sh, stop.sh (dispatchers)
│       ├── pre-tool-use/  ← PreToolUse sub-scripts
│       ├── stop/          ← Stop sub-scripts
│       │   └── tips/      ← notifier tip data, one file per locale
│       │                    (tips.en.txt · tips.pt-BR.txt · tips.es.txt)
│       └── lib/           ← shared hook logic, sourced not dispatched
│           ├── session-summary-detect.sh ← shared by pre-compact.sh and stop/01-
│           ├── touched-paths.sh          ← touched-path set computed once by stop.sh
│           ├── warn-once.sh              ← once-per-signature gate for Stop exit-2 warnings
│           ├── plugins.sh                ← plugin hook dispatcher and helper functions
│           └── update-check.sh           ← update-check engine behind session-start.sh and check-updates.sh
├── .github/         ← CI workflows (incl. release.yml), issue/PR templates, CODEOWNERS, scripts/ci/
│                      (incl. 04-packaging.sh, 05-app.sh ← the app/ JS gate) + scripts/release/bump-homebrew-formula.sh — stripped at install
├── packaging/       ← distribution manifests (ADR-0011): Homebrew formula + cask, winget manifests,
│                      the Windows CLI installer build (windows-cli/, ADR-0028) and the operator
│                      runbook. UNRELEASED — see packaging/README.md for what each placeholder
│                      needs. Never reaches a user project: install.sh's KEEP_ROOT allowlist drops it
├── tests/           ← devteam CLI test suite (stdlib unittest); DEV-ONLY, stripped from the package
├── user-data/       ← runtime state of this repo's own self-install; gitignored and untracked
├── README.md
├── README.pt-BR.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── PRIVACY.md
├── LICENSE
├── AGENTS.md        ← points Codex/opencode contributors at this file; ends with the banner block `install-codex.sh` appends
└── CLAUDE.md        ← this file
```

**Two `helpers` directories — do not confuse them:**

| Path | Ships to user projects? | Purpose |
|------|------------------------|---------|
| `helpers/` (repo root) | **No** — `rm -rf` by `scripts/lib/strip-tarball.sh` | Dev-only authoring tools for this repo: linting, orphan scans, size limits, fingerprint index maintenance. Run them from the repo root, never from an installed `.dev-team-agents/`. |
| `scripts/helpers/` | **Yes** — inside the allowlisted `scripts/` tree | Runtime helpers used by the installed package. Currently `telemetry-send.sh`, invoked by `install.sh` and `update.sh` at `.dev-team-agents/scripts/helpers/telemetry-send.sh`. |

When a rule or script path references "helpers", state which of the two it means.
