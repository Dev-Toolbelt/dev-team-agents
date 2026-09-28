# Verifying a Homebrew formula when you have no tap

**Origin:** packaging M4.2 — proving `packaging/homebrew/devteam.rb` installs | 2026-09-28
**Tags:** homebrew, brew tap-new, brew trust, trust.json, brew audit, audit --new, brew style, XDG_CONFIG_HOME, Formulary, requires formulae to be in a tap, notable enough

> Homebrew 7 refuses a formula file that is not inside a tap, and `brew audit <path>` is
> disabled outright — which makes "we cannot verify the formula, we have no tap" a very
> natural and wrong conclusion. `brew tap-new --no-git` is the way through.

All observations below are from **Homebrew 7.0.6** on macOS. They are version-specific.

---

## What it is

A repository can carry a formula it has never published. Verifying it locally hits two
independent refusals:

```
Error: Homebrew requires formulae to be in a tap, rejecting: ./devteam.rb
Error: Calling `brew audit [path ...]` is disabled! Use `brew audit [name ...]` instead.
```

## How it works

1. `brew tap-new <user>/<repo> --no-git` creates a throwaway local tap. A formula copied into
   its `Formula/` directory is installable and auditable **by tap-qualified name**.
2. Homebrew 7 will not *load* a formula from an untrusted tap, so `brew trust --tap <tap>` is
   required as well.
3. Trust records live in `${XDG_CONFIG_HOME}/homebrew/trust.json`, or `~/.homebrew/trust.json`
   when that variable is unset. So the trust write is sandboxable by pointing
   `XDG_CONFIG_HOME` at a temp directory — but **per `brew` process only**, never as a global
   `export`: the same variable reroutes `git`'s `config`, `ignore` and `attributes`.

## Gotchas

- **`brew audit --new` is a trap on a private tap.** It implies `--strict --online`
  (`dev-cmd/audit.rb`: `strict = args.new? || args.strict?`) and adds nothing else, because
  every new-formula check in `FormulaAuditor` is gated on the core tap — the four git-forge
  notability checks reach it through `get_repo_data`, whose first line is
  `return unless @core_tap` (`formula_auditor.rb:858`), and the rest check directly. A clean
  `--new` therefore means *the checks did not run*, not that homebrew-core would accept the
  formula. Called directly, `SharedAudits.github` on this repository returns
  `GitHub repository not notable enough (<30 forks, <30 watchers and <75 stars)` — unreachable,
  not passing. Run `brew audit --strict --online` under its own name instead; `--online`
  genuinely fetches the url.
- **`brew style` reports a different cop set depending on where the file is.** On a bare path
  it also reports `Sorbet/StrictSigil`, `Sorbet/TrueSigil` and
  `Style/FrozenStringLiteralComment`; the same file inside a tap's `Formula/` reports none of
  them. Homebrew's own `.rubocop.yml` excludes those cops under `**/{Formula,Casks}/**/*.rb`,
  and `style.rb` passes `tap_rubocop_style.yml` rooted at the tap when every target is inside
  one tap. Anyone comparing a by-hand `brew style` against a script's clean result will
  otherwise conclude the script is lying.
- **`brew style` and `brew audit` are dev commands and leave something behind.** Both call
  `install_bundler_gems!`, which bootstraps rubocop and the audit gems into
  `$(brew --repository)/Library/Homebrew/vendor/bundle` — about 100 MB on a prefix that has
  never run a dev command. It is permanent and must **not** be deleted: it is Homebrew's own
  tooling cache, reused by every later dev command.
- **Passing a *path* to `brew install`/`brew info` makes Homebrew try the cask loader first.**
  Even for a file inside a tap it prints `Error: Failed to load cask … wrong constant name`,
  then `Warning: Treating … as a formula`, then succeeds. Alarming in a log, harmless, and
  avoided by passing the tap-qualified name.
- `HOMEBREW_DEVELOPER=1` **does** bypass the tap-only rejection — but it is not a shortcut
  worth taking: `brew audit <path>` stays disabled regardless, and the cask-loader noise and
  path-based cop set above both still apply.

## References

- `packaging/verify-formula-locally.sh` — the tap/trust/style/audit stages and the sandbox
- `packaging/README.md` § Verification, § What is proven, § What is unverified
