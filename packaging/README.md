# Runbook: Publishing devteam to Homebrew and winget

**Last updated:** 2026-09-28
**Owner:** dev-team-agents maintainers
**Estimated time:** 30–90 minutes per channel, first time; ~10 minutes per channel on a routine release once the manual accounts below are set up

## Overview

This is the operator's guide to the packaging in this directory, produced against
[ADR-0011](../docs/development/adrs/0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md).
It covers what `.github/workflows/release.yml` automates, what still needs a
human, and exactly which accounts and secrets each channel requires.

**Nothing in this directory has been installed, run through `brew install`,
`brew audit`, or `winget validate`, or submitted anywhere.** There is no
`homebrew-devteam` tap repository, no Windows installer, and no Electron app
build. Everything here is scaffolding for channels ADR-0011 decided on, built
so the shape is right when each of those pieces exists — not a claim that any
of them are live.

## What's in this directory

| Path | What it is | Status |
|------|-----------|--------|
| `homebrew/devteam.rb` | Formula for the CLI (`scripts/cli/devteam` + `scripts/lib/devteam/`) | Buildable today — CLI exists. Formula itself never brew-tested (no tap). |
| `homebrew/devteam-app.rb` | Cask for the desktop app's signed, notarised `.dmg` | Groundwork only — the app does not exist |
| `winget/manifests/d/DevToolbelt/Devteam/0.0.0/` | winget multi-file manifest (version, installer, locale) for the CLI | Scaffold at a placeholder version — no Windows installer exists to point at |
| `../.github/workflows/release.yml` | On a `vX.Y.Z` tag push, downloads that tag's release tarball, hashes it, and opens a PR bumping `homebrew/devteam.rb`'s `url`/`sha256` | Automated, but unrun — no tag has triggered it yet |

## Version source of truth

**Checked before writing this workflow, per the task that produced it:**
[`CLAUDE-md/versioning.md`](../CLAUDE-md/versioning.md) defines the policy (what bump
for what kind of change) but **not a file that stores the current version** — there is
no `VERSION` file and no version string embedded in `scripts/lib/devteam/*.py`. The
version of record is **the most recent `vX.Y.Z` git tag** (`v2.48.0` as of this
writing), read by:
- `devteam version` / `devteam bind` — resolves what's in the core store, which is
  populated from a tag via `devteam store install`
- `scripts/install.sh` and `scripts/lib/installer-fetch.sh` — resolve `latest` via
  the GitHub Releases/tags API, or take an explicit `vX.Y.Z`
- CI's `tag-name` job (`.github/workflows/ci.yml`) — validates the pushed tag's shape

**`release.yml` reads the same source of truth and introduces no second one.** It
never hand-picks or increments a version; it only reacts to whatever tag was just
pushed (`github.ref_name`), and writes that same tag string into the formula. If a
future change needs a version *inside* a file (for example, for the desktop app's
own `package.json`), that value must derive from the git tag at build time, not be
maintained by hand alongside it.

## Design decision: one artifact shape, not two

The task that produced this packaging asked for a workflow that "builds the package
tarball." It does not build a bespoke one. `scripts/install.sh` already installs
projects from GitHub's own auto-generated source archive for a tag —
`https://github.com/Dev-Toolbelt/dev-team-agents/archive/refs/tags/<tag>.tar.gz` —
which GitHub materialises automatically the moment the tag exists, no upload step
needed. `packaging/homebrew/devteam.rb` points at that exact same URL. `release.yml`'s
only job is to download that URL after the tag lands and hash the bytes it actually
receives — not to invent a second, differently-built artifact that only Homebrew
users would get, and that could drift from what `install.sh` users get.

One consequence worth stating plainly: `strip-tarball.sh`'s strip rules (which
`install.sh` applies **after** download, client-side) are irrelevant to the formula.
The formula's `install` block picks out only `scripts/cli/devteam` and
`scripts/lib/devteam/*.py` from the full, unstripped source archive itself — it
does not rely on `strip-tarball.sh` at all.

## Prerequisites (per channel, before any of this can go live)

### Homebrew — CLI formula (`devteam.rb`)

- [ ] A `homebrew-devteam` tap repository, public on GitHub under an org/user that
      owns it (Homebrew taps are just git repos with a `Formula/` directory —
      **this does not exist yet**)
- [ ] Push access to that tap repo for whichever automation or maintainer publishes
      accepted formula bumps into it
- [ ] `GITHUB_TOKEN` (the default Actions token) — sufficient for opening the PR
      `release.yml` opens **in this repo**; a **separate** token/deploy key would be
      needed if a later step is added to also push the formula into the tap repo,
      since a tap is a different repository

### Homebrew — app cask (`devteam-app.rb`)

- [ ] The Electron app itself (`app/` directory, build pipeline — none of this
      exists in this repository yet)
- [ ] An Apple Developer ID (paid Apple Developer Program membership) to sign the
      `.dmg`
- [ ] An app-specific password (or API key) for `notarytool` to notarise the signed
      build — generated from the Apple ID account, not something CI can create for
      itself
- [ ] The same tap repository as above (a cask lives in `Casks/`, alongside
      `Formula/`, in one tap)

### winget — CLI manifest

- [ ] A decided Windows packaging shape for the CLI (this scaffold assumes a
      signed `.exe` installer wrapping the python payload — see the comment in
      `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` — but nothing has
      built one)
- [ ] A code-signing certificate (Authenticode) to sign that installer — winget
      does not require signing, but shipping an unsigned `.exe` triggers SmartScreen
      warnings for every user, which defeats "the tool their platform already has"
      from ADR-0011
- [ ] A GitHub account able to open a pull request against
      `microsoft/winget-pkgs` (public repo, no special access needed — just review)

### winget — app manifest

- [ ] Everything above, plus the app build itself and Windows code-signing for the
      installer it produces

## Placeholders in this directory — what replaces them, and from where

| File | Placeholder | Replaced by | Source of the real value |
|------|------------|-------------|---------------------------|
| `homebrew/devteam.rb` | `url "...tags/vX.Y.Z.tar.gz"` | The real tag | `release.yml`, automatically, from `github.ref_name` on tag push |
| `homebrew/devteam.rb` | `sha256 "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL"` | 64-char hex digest | `release.yml`, automatically — `sha256sum` of the downloaded tag tarball, never hand-written |
| `homebrew/devteam.rb` | `depends_on "python@3.12"` | Whatever python formula is current in `homebrew-core` at publish time | Manual — run `brew info python3` (or search `homebrew-core`) right before publishing; this name has drifted before and will again |
| `homebrew/devteam-app.rb` | Entire file marked UNRELEASED AND UNVERIFIED | A real formula, once the app exists | Manual — write it against the actual signed `.dmg` the app build produces; do not just fill in these placeholders |
| `homebrew/devteam-app.rb` | `version "0.0.0-unreleased"` | The app's real release tag (e.g. `app-v1.0.0`) | Manual, decided when the app first ships |
| `homebrew/devteam-app.rb` | `sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"` | 64-char hex digest of the real notarised `.dmg` | Manual — hash the actual release artifact once it exists; do not reuse the CLI formula's automation blindly, since a cask's artifact is signed/notarised and that should be verified, not just hashed |
| `winget/manifests/.../DevToolbelt.Devteam.yaml` (version dir + all 3 files) | `0.0.0` (`PackageVersion`, directory name) | The real release version | Manual — rename the `0.0.0/` directory and update `PackageVersion` in all three files together when a Windows installer first ships |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | Both `InstallerUrl` entries (`vX.Y.Z`, filenames) | Real asset URLs | Manual — wherever the signed `.exe` installers actually get uploaded (a GitHub Release is the obvious place, not decided) |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | Both `InstallerSha256` (64 zeros — deliberately not a plausible-looking fake hash) | Real digests of the signed installers | Manual — hash the actual signed `.exe` files; **do this after signing**, since signing changes the bytes and therefore the hash |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | `InstallerType: exe` | Whatever the Windows packaging decision actually lands on | Manual — this is a design placeholder, not a decided tool. Update alongside `InstallerSwitches` if it changes |

**Why the sha256 placeholders look the way they do:** `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL`
and `NO_RELEASE_SHA256_DOES_NOT_EXIST_YET` cannot be mistaken for real hashes — they
fail Homebrew's format check immediately. The winget zeros (`00000...0`, 64
characters, matching the required hex-digest length) are the same idea in a format
that must pass the schema's length/hex-pattern check to be visibly wrong at review
time rather than a plausible fake. A plausible-looking fake digest is worse than
either: it can be committed and shipped without anyone noticing it doesn't match
the actual artifact.

## Steps — routine release (once every prerequisite above is met)

### 1. Cut the release the same way as always

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

**Expected output:** CI's `tag-name` job validates the tag shape; `release.yml`
triggers on the same push.

### 2. Let `release.yml` open its PR

No action needed — it downloads the tag's tarball, hashes it, and opens
`chore(packaging): bump Homebrew formula to vX.Y.Z` against this repo.

**Expected output:** a PR modifying only `packaging/homebrew/devteam.rb`'s `url`
and `sha256` lines.

### 3. Review and merge that PR

Confirm the diff touches only those two lines, and that the sha256 is a 64-char
hex string (the workflow already asserts this before opening the PR, but review it
again — this is the value users' machines will trust).

### 4. Publish to the tap (manual, no tooling exists for this step yet)

```bash
# Inside a checkout of the homebrew-devteam tap repo:
cp <this-repo>/packaging/homebrew/devteam.rb Formula/devteam.rb
git commit -am "devteam vX.Y.Z"
git push
```

**Expected output:** `brew install Dev-Toolbelt/devteam/devteam` resolves the new
version for users of the tap. **Unverified here** — there is no tap to push to yet.

### 5. winget (manual, PR-gated, only after a signed Windows installer exists)

Update `PackageVersion` and the version directory, fill in the real
`InstallerUrl`/`InstallerSha256` values from the signed `.exe`, then open a PR
against `microsoft/winget-pkgs` following their contribution guide. This step
cannot be automated from this repository — it is review by Microsoft, against
Microsoft's repo.

## Verification

```bash
ruby -c packaging/homebrew/devteam.rb
ruby -c packaging/homebrew/devteam-app.rb
python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('packaging/winget/manifests/**/*.yaml', recursive=True)]"
bash .github/scripts/ci/01-lint.sh
```

**Expected result:** both formulas report `Syntax OK`, the YAML load raises
nothing, and lint exits 0. None of these three checks are a substitute for
`brew audit`/`brew install`/`winget validate` against real, hosted artifacts —
they only catch syntax errors, not whether Homebrew or winget actually accept
these files.

## What is unverified, and exactly why

| Item | Why it cannot be verified from this repository |
|------|--------------------------------------------------|
| `brew install`/`brew audit` of either formula | No Homebrew tap exists to install from, and this environment does not (and should not) install a tap-less formula for real |
| macOS code signing and notarisation of the app | Needs an Apple Developer ID and an app-specific password/API key — account-level access this environment does not have and should not be given |
| Windows installer signing | Needs an Authenticode code-signing certificate — same reasoning |
| The `sha256` currently in `devteam.rb` | It is a placeholder string, not a digest — there is no release tarball yet for any hash to describe. `release.yml` computes the real one the first time a tag is pushed |
| The `InstallerSha256` values in the winget installer manifest | 64 zeros — no Windows installer has ever been built, signed, or hashed |
| winget acceptance | Publication is itself a reviewed pull request to `microsoft/winget-pkgs`, against a real installer URL and hash that do not exist yet — review happens on Microsoft's infrastructure, not here |
| `release.yml` itself running end to end | It has never been triggered — no `vX.Y.Z` tag has been pushed since this file was added. The sed/verification logic was dry-run locally against a copy of `devteam.rb` with a fake tag and hash (documented in the session that authored this), which is not the same as a real Actions run |

## Contacts

| Role | Name / Channel |
|------|---------------|
| Primary owner | dev-team-agents maintainers |
| Escalation | repository issues — `Dev-Toolbelt/dev-team-agents` |
| On-call | none — this is not a production service |
