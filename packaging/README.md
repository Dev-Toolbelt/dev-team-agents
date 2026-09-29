# Runbook: Publishing devteam to Homebrew and winget

**Last updated:** 2026-09-28
**Owner:** dev-team-agents maintainers
**Estimated time:** 30–90 minutes per channel, first time; ~10 minutes per channel on a routine release once the manual accounts below are set up

## Overview

This is the operator's guide to the packaging in this directory, produced against
[ADR-0011](../docs/development/adrs/0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md).
It covers what is now checked automatically, what `.github/workflows/release.yml`
automates, what still needs a human, and exactly which accounts and secrets each
channel requires.

**What is proven, and what is not, in one paragraph.**
`packaging/homebrew/devteam.rb` has been installed for real: `packaging/verify-formula-locally.sh`
builds a tarball with `git archive … HEAD` — committed sources only, not the
working tree — creates a throwaway local Homebrew tap, and runs `brew style`,
`brew audit --formula`, `brew audit --strict --online`,
`brew install --build-from-source`, `brew test` and a smoke test of the installed
binary. **One** such run is recorded — on one maintainer's macOS machine against
Homebrew 7.0.6 — and every stage reported `PASS`. That is a recorded run, not a
channel: nothing re-runs it. `.github/scripts/ci/04-packaging.sh` gates both formulas and
all three winget manifests on **every pull request and on pushes to `main` and to
tags** — not on every push; see the trigger note below — and
`tests/test_packaging.py` runs the formula's own declared payload on Linux in CI.
**What remains unproven is the published path**: no `homebrew-devteam` tap hosts
this formula, no release tarball has ever been installed from one, no Windows
installer has been built, **no cask-installable artifact exists**, and the release
workflow has never been triggered. Nothing below claims otherwise — read the two
tables at the end for the split, item by item.

**The app exists now, and it is unsigned. Both halves of that matter.**
`app/` holds the Electron client decided by
[ADR-0015](../docs/development/adrs/0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md),
and `npm run dist:mac` produces a universal `dev-team-agents.app` inside
`dev-team-agents-<version>.dmg` — a maintainer has run it on macOS and it built.
That is a recorded local build, in the same sense as the formula run above, and it
is **weaker than one**: nothing in the tree is the artifact (`app/.gitignore`
excludes `dist/` and `release/`), no CI job produces one —
`.github/scripts/ci/05-app.sh` runs `typecheck`, `lint` and `test` and
deliberately never `dist:mac`, because "one that builds an unsigned artifact is
shipping, not checking" — and the build is unsigned by configuration, not by
accident: `app/electron-builder.yml` sets `mac.identity: null` and
`mac.notarize: false`, and `app/build/after-build.cjs` prints
`UNSIGNED, UNNOTARISED BUILD — DO NOT DISTRIBUTE` after every artifact. A
universal build still carries an **ad-hoc** signature because macOS will not load
an unsigned arm64 Mach-O, and an ad-hoc signature is not a Developer ID
signature and carries no notarisation ticket: `brew audit --cask` rejects it, and
Gatekeeper refuses to open it without an explicit user override. So what the cask
still cannot describe is unchanged — a **signed, notarised** artifact at a **real
version** — and the app column of ADR-0011's channel table is still empty on both
platforms. On Windows it is emptier than that: **there is no app manifest at all**
under `packaging/winget/` (the three manifests there are the CLI,
`DevToolbelt.Devteam`; the word "app" appears once, in a comment), while
ADR-0011's channel table promises winget for the app as well as the CLI.

**The CI trigger, stated once.** `ci.yml`'s `push` trigger is `branches: [main]`
plus `tags: ["**"]`; every other branch is covered by `pull_request` only. So a
branch with no open PR gets no CI at all, and the accurate coverage for every
gate in this document is **every pull request, plus pushes to `main` and to
tags**. `ci.yml`'s own header states that trade-off and how to opt in (open a
draft PR). An earlier version of this file said "on every push" in four places;
it was simply false.

## What's in this directory

| Path | What it is | Status |
|------|-----------|--------|
| `homebrew/devteam.rb` | Formula for the CLI (`scripts/cli/devteam` + `scripts/lib/devteam/`) | Installs and passes its own `test do` block through a real Homebrew, via `verify-formula-locally.sh`'s throwaway tap. Never installed from a **published** tap, and its `url`/`sha256` are still placeholders. |
| `homebrew/devteam-app.rb` | Cask for the desktop app's signed, notarised `.dmg` | Still unpublishable, for a narrower reason than before: the app exists (`app/`, ADR-0015) and builds an **unsigned** `.dmg`; no signed, notarised artifact and no real version exist. Its macOS floor and bundle id are no longer guesses — both are now read from `app/electron-builder.yml` (see the row below). `ruby -c` is the only **CI** check that touches it, and it passes. `brew style` has been run on it by hand and reports four unfixed cask-cop findings — see § Verification. |
| (absent) `winget/…/DevToolbelt.DevteamApp/` | The winget manifest ADR-0011's channel table promises for the **app** | **Does not exist.** Nothing under `packaging/winget/` is about the app; all three manifests are the CLI. Windows therefore has no app channel at all, scaffolded or otherwise, and no Authenticode certificate to sign one with. |
| `winget/manifests/d/DevToolbelt/Devteam/0.0.0/` | winget multi-file manifest (version, installer, locale) for the CLI | Scaffold at a placeholder version — no Windows installer exists to point at. Contract-checked in CI; never through `winget validate`. |
| `verify-formula-locally.sh` | Exercises `devteam.rb` end to end through a real Homebrew (see Verification below) | Run and passing on macOS with Homebrew 7.0.6. Needs `brew` on PATH and Homebrew ≥ 7; the `packaging` job runs on `ubuntu-latest`, which has no Homebrew, so it is not run there. That is a cost choice, not an impossibility — Homebrew runs on Linux too, and `release.yml` runs this very script on a `macos-latest` runner. |
| `../.github/scripts/ci/04-packaging.sh` | The CI gate for this directory: `ruby -c` on both formulas, plus the winget manifest contract | Runs on every pull request and on pushes to `main`/tags (the `packaging` job in `ci.yml`). Two advisories fire today, deliberately — see below. |
| `../.github/scripts/release/bump-homebrew-formula.sh` | Rewrites the formula's `url`/`sha256` to a released tag and digest | Covered by `tests/test_release_bump.py` (23 tests, green). The **workflow** that calls it has still never run. |
| `../.github/workflows/release.yml` | On a `vX.Y.Z` tag push, downloads that tag's release tarball, hashes it, opens a PR bumping the formula, uploads the rewritten formula as an artifact, then on `macos-latest` asserts that artifact's `url`/`sha256` against the computed digest and that nothing else in the file changed, and brew-installs it against the real tarball | Automated, but unrun — no tag has been pushed since the workflow was added (the newest tag predates the commit that added it). **The `macos-latest` job is not a gate**: the bump job opens the PR in its own last step, so the PR is already open while the job runs, and no branch rule marks the check required. Its own `RESIDUAL` block says so. |

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

## Design decision: two layers of payload verification, not one duplicated check

`tests/test_packaging.py` and `verify-formula-locally.sh` overlap on purpose, and
neither replaces the other:

| | `tests/test_packaging.py` | `verify-formula-locally.sh` |
|---|---|---|
| What it is | The CI-portable **proxy**: it parses the formula's `install` block, stages exactly the paths that block names, applies the same `inreplace` shebang rewrite by hand, and runs the staged CLI | The **real thing**: a real `brew install` of the real formula through a real Homebrew |
| Where it runs | Every pull request and every push to `main`/tags, on Linux, no Homebrew needed | Anywhere `brew` is on PATH at Homebrew ≥ 7 — a maintainer's macOS machine today, and `release.yml`'s `macos-latest` runner on a tag |
| What it cannot see | Anything Homebrew itself does — dependency resolution, digest verification, `brew audit`'s rules, `bin.install_symlink` | Nothing; but it is not on the `ubuntu-latest` runner the PR gate uses |

The proxy exists because the PR gate runs on `ubuntu-latest`, which ships no
Homebrew, and putting the real thing on every PR would mean a macOS runner per
PR — a cost choice, not an impossibility. The real thing exists because the proxy
assumes Homebrew behaves as the formula expects. Delete either and a whole class
of formula breakage stops being caught before a user hits it.

**What each one actually derives from the formula**, because they are not
symmetrical and an earlier version of this table claimed they were:

- `tests/test_packaging.py` parses the `install` block and derives **the payload**
  — every path the block's `.install` lines stage — so an edit to that block
  cannot leave the test checking the old file set. It also parses `depends_on` and
  the interpreter derivation and pins them against each other.
- `verify-formula-locally.sh` derives **the python dependency** from the
  `depends_on "python@X.Y"` line (it needs it to resolve the expected shebang and
  to know what the install may have pulled in). The payload paths it asserts are
  **written into the script**, not read out of the formula: the artifact stage
  greps the tarball listing for the literals `scripts/cli/devteam` and
  `scripts/lib/devteam/*.py`, and the install stage checks `lib/devteam` relative
  to the libexec directory it resolved. Moving the payload in the `install` block
  would be caught by the test, and by `brew install` failing outright, but not by
  a path this script derived.

## Prerequisites (per channel, before any of this can go live)

None of the items below has been done. They are account-level and third-party-review
prerequisites the repository owner holds; nothing in this session advanced any of them.

### Homebrew — CLI formula (`devteam.rb`)

- [ ] A `homebrew-devteam` tap repository, public on GitHub under an org/user that
      owns it (Homebrew taps are just git repos with a `Formula/` directory —
      **this does not exist yet**). The throwaway tap `verify-formula-locally.sh`
      creates is local, git-less and deleted on exit; it is not a published tap and
      proves nothing about one
- [ ] Push access to that tap repo for whichever automation or maintainer publishes
      accepted formula bumps into it
- [ ] `GITHUB_TOKEN` (the default Actions token) — sufficient for opening the PR
      `release.yml` opens **in this repo**; a **separate** token/deploy key would be
      needed if a later step is added to also push the formula into the tap repo,
      since a tap is a different repository

### Homebrew — app cask (`devteam-app.rb`)

- [x] The Electron app itself (`app/`, decided by ADR-0015) and a build that
      produces the artifact shape the cask names: `npm run dist:mac` →
      `release/dev-team-agents-<version>.dmg` containing a universal
      `dev-team-agents.app`. **This box is ticked for existence only** — the
      build is unsigned, no CI job runs it, and no artifact is committed
- [ ] A step that stamps `app/package.json`'s `version` from the `app-v*` git tag
      at build time. Without it the dmg filename and this cask's `version` are two
      hand-maintained strings for one value; see the cask's own header for the rule
      and § Version source of truth for why the tag is the authority
- [ ] An Apple Developer ID (paid Apple Developer Program membership) to sign the
      `.dmg`, and `mac.identity`/`mac.notarize` in `app/electron-builder.yml`
      flipped off their `null`/`false` placeholders, plus `CODE_SIGNED` in
      `app/src/main/build-info.ts` flipped to `true` in the same change — the app
      states its own signing status from that constant, in the UI and on startup
- [ ] An app-specific password (or API key) for `notarytool` to notarise the signed
      build — generated from the Apple ID account, not something CI can create for
      itself
- [ ] The same tap repository as above (a cask lives in `Casks/`, alongside
      `Formula/`, in one tap)

### winget — CLI manifest

- [ ] A decided Windows packaging shape for the CLI. The scaffold assumes a signed
      `.exe` installer wrapping the python payload, and that is an explicit design
      placeholder rather than a decision — see
      [the next section](#the-windows-installer-shape--undecided-and-the-test-that-decides-it),
      which records the candidates and the one test that settles them
- [ ] A code-signing certificate (Authenticode) — **required by candidate (a) only**,
      recommended by the others. winget does not require signing, but shipping an
      unsigned `.exe` triggers SmartScreen warnings for every user, which defeats
      "the tool their platform already has" from ADR-0011
- [ ] A GitHub account able to open a pull request against
      `microsoft/winget-pkgs` (public repo, no special access needed — just review)

### winget — app manifest

- [ ] **The manifest itself. It does not exist** — no directory, no scaffold, no
      placeholder, unlike every other row in this document. ADR-0011's channel
      table promises winget for the app; nothing here delivers even a draft of it
- [ ] A Windows build of the app. `app/electron-builder.yml` has **no `win`
      block**, and says why: adding one "would imply a decided shape" while
      ADR-0011's winget row is still a placeholder. So the app builds on macOS
      only today
- [ ] Windows code-signing (Authenticode) for whatever installer that build
      produces

## The Windows installer shape — undecided, and the test that decides it

`winget/manifests/.../DevToolbelt.Devteam.installer.yaml` carries
`InstallerType: exe`. **That is an honest design placeholder, and this section does
not replace it with a decision.** The choice cannot be made from this repository:
every candidate below is discriminated by running `winget` on a real Windows
machine, and nothing here can do that. What this section does is record the three
candidates and, for each, the exact test that settles it — so whoever has a Windows
machine can close the question in one sitting instead of re-deriving it.

**Schema facts below were read from the manifest schema itself**,
`https://raw.githubusercontent.com/microsoft/winget-cli/master/schemas/JSON/manifests/v1.12.0/manifest.installer.1.12.0.json`
(confirmed 2026-09-28, the same `manifestVersion 1.12.0` the manifests declare):

- `InstallerType` enum: `msix`, `msi`, `appx`, `exe`, `zip`, `inno`, `nullsoft`,
  `wix`, `burn`, `pwa`, `portable`, `font`
- `NestedInstallerType` enum: the same set **minus `zip` and `pwa`** — so a `zip`
  cannot nest a `zip`
- `NestedInstallerFiles` entries: `RelativeFilePath` (**required**) and
  `PortableCommandAlias` (optional, portable only)
- `Dependencies.PackageDependencies` — entries of `PackageIdentifier` (required) and
  `MinimumVersion` (optional) — exists at **both** the root level and the
  per-installer level

### The three candidates

| | Shape | Needs | Does not need | The test that discriminates it |
|---|---|---|---|---|
| **(a)** | `InstallerType: exe` — a signed installer executable wrapping the python payload (the current placeholder) | An Authenticode code-signing certificate; a bespoke Windows installer build (PyInstaller + Inno/NSIS, pynsist, or similar); `InstallerSwitches` that actually match whatever produced the `.exe` | A system python3 on the user's machine | Build the `.exe`, then run `winget install --manifest <dir>` with the real digest and confirm the recorded `Silent` switch installs with no UI. Until an `.exe` exists there is nothing to test — which is why this candidate is the most expensive to even evaluate |
| **(b)** | `InstallerType: zip` + `NestedInstallerType: portable`, wrapping a built `devteam.exe` (e.g. PyInstaller) with `PortableCommandAlias: devteam` | A Windows build job — **which CI can do with no credentials**, since PyInstaller needs no certificate and no account | A certificate (signing becomes recommended, not required); a system python3 | `winget validate` the manifest, then `winget install --manifest <dir>` and confirm `devteam --help` resolves through the `PortableCommandAlias` shim in a fresh shell |
| **(c)** | The same zip/portable shape, but the zip ships the **python sources plus a launcher**, with `Dependencies.PackageDependencies` naming a python package | Nothing to build and nothing to sign — the payload is the same files the formula installs | Build tooling, a certificate, an Apple-style account of any kind | The same two commands as (b), **plus** the open question below — because the nested file is a launcher, not an `.exe` |

### The open question that decides between (b) and (c)

**Does winget's `portable` nested installer accept a non-`.exe` file, such as a
`.cmd` launcher?**

This is unresolved, and it is the whole difference between (b) and (c). Two sources
were checked and neither answers it:

- The JSON schema above does **not** constrain the file type. `RelativeFilePath` is
  a plain string with a length bound; nothing restricts its extension, and
  `NestedInstallerType: portable` carries no companion field that would.
- Microsoft's [Create your package manifest](https://learn.microsoft.com/en-us/windows/package-manager/package/manifest)
  page does not address it either — it documents the manifest fields and the
  multi-file layout without saying what a portable target may be.

A schema that permits something and a client that accepts it are not the same
claim, so this is settled only by `winget validate` and `winget install --manifest`
against a real manifest on a real Windows machine. Candidate (c) is the cheapest
shape by a wide margin — no build, no certificate — so it is worth testing first;
if the launcher is rejected, (b) is the fallback and needs a build job but still no
credentials.

### Two constraints from the same documentation, worth recording because they bound the design

Both are quoted on the Microsoft page linked above:

- **winget manifests do not support all of YAML.** Anchors, complex keys and sets
  are explicitly unsupported. So no candidate may factor repetition out of the
  installer manifest with an anchor — the two per-architecture entries stay written
  out in full, as they are today.
- **Every tool must support a silent install.** winget-pkgs states that an
  executable without a silent install cannot be accepted. That is a hard gate on
  candidate (a)'s `InstallerSwitches`, and it is a reason the portable shapes are
  attractive: a portable install has no installer UI to silence.

## Placeholders in this directory — what replaces them, and from where

| File | Placeholder | Replaced by | Source of the real value |
|------|------------|-------------|---------------------------|
| `homebrew/devteam.rb` | `url "...tags/vX.Y.Z.tar.gz"` | The real tag | `.github/scripts/release/bump-homebrew-formula.sh`, called by `release.yml`, from `github.ref_name` on tag push |
| `homebrew/devteam.rb` | `sha256 "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL"` | 64-char hex digest | The same script, automatically — `sha256sum` of the downloaded tag tarball, never hand-written. The script refuses anything that is not 64 lowercase hex characters |
| `homebrew/devteam-app.rb` | Entire file marked UNRELEASED | A real cask, once a **signed** build exists | Manual — write it against the actual signed, notarised `.dmg`; do not just fill in these placeholders. The header no longer claims the app is absent: `app/` exists and builds an unsigned dmg |
| `homebrew/devteam-app.rb` | `version "0.0.0-unreleased"` | The app's real release tag (e.g. `app-v1.0.0`) | The `app-v*` git tag, via a build step that stamps `app/package.json` from it. **Coupled**: `dmg.artifactName: ${productName}-${version}.dmg` derives the dmg filename from `app/package.json`'s `version` while the cask's `url` derives it from this line, so the two must be one string at release time. They disagree today on purpose (`0.0.0` vs `0.0.0-unreleased`) and must not be reconciled by hand — see the cask header |
| `homebrew/devteam-app.rb` | `sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"` | 64-char hex digest of the real notarised `.dmg` | Manual — hash the actual release artifact once it exists; do not reuse the CLI formula's automation blindly, since a cask's artifact is signed/notarised and that should be verified, not just hashed. **Never the digest of a local unsigned build**, which is a different artifact with the same filename |
| `homebrew/devteam-app.rb` | ~~`depends_on macos: ">= :big_sur"`~~ — **no longer a placeholder** | `">= :monterey"`, measured | `app/node_modules/electron/dist/Electron.app/Contents/Info.plist` → `LSMinimumSystemVersion` **12.0** for Electron 39.8.10, mirrored by `mac.minimumSystemVersion: '12.0'` in `app/electron-builder.yml`. Big Sur was wrong in the dangerous direction: it licensed an install on a system the app cannot launch on. **Re-measure on every Electron major** — the floor moves with it, nothing checks the pair, and this is the one row in this table that comes back |
| `homebrew/devteam-app.rb` | ~~placeholder bundle id in `zap trash:`~~ — **no longer a placeholder** | `com.devtoolbelt.dev-team-agents-app` | `appId` in `app/electron-builder.yml`; `app "dev-team-agents.app"` likewise matches its `productName`. Both confirmed against the build config, both still unchecked by any gate |
| `winget/manifests/.../DevToolbelt.Devteam.yaml` (version dir + all 3 files) | `0.0.0` (`PackageVersion`, directory name) | The real release version | Manual — rename the `0.0.0/` directory and update `PackageVersion` in all three files together when a Windows installer first ships. `04-packaging.sh` fails the build if those four edits disagree with each other |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | Both `InstallerUrl` entries (`vX.Y.Z`, filenames) | Real asset URLs | Manual — wherever the installers actually get uploaded (a GitHub Release is the obvious place, not decided). `04-packaging.sh` refuses a half-bump in either direction: the URL's tag and `PackageVersion` must move together |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | Both `InstallerSha256` (64 zeros — deliberately not a plausible-looking fake hash) | Real digests of the real installers | Manual — hash the actual artifacts; **do this after signing**, if the chosen shape signs, since signing changes the bytes and therefore the hash |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | `InstallerType: exe` | Whatever the Windows packaging decision lands on | Manual — a design placeholder, not a decided tool. See [the section above](#the-windows-installer-shape--undecided-and-the-test-that-decides-it); update alongside `InstallerSwitches`, `NestedInstallerType`/`NestedInstallerFiles` and `Dependencies` as one edit |

**`depends_on "python@3.14"` is no longer on this list, and that is a change worth
naming.** It used to be here as a manual pre-publish step: *run `brew info python3`
and confirm the name has not drifted.* It had already drifted when that instruction
was written — the formula said `python@3.12` while homebrew-core's `python3` had
moved to `python@3.14`, which would have made every installer pull a second, older
python (~68 MB) for devteam alone. Two things changed. The declared dependency is
now current, and it is the **only** place the python version appears: `install`
reads the version back off the dependency instead of repeating it in the shebang
path. And the check is no longer something a human has to remember —
`verify-formula-locally.sh` parses the `depends_on` line, resolves
`brew info --json=v2 python3`, prints the two side by side on every run and calls
out a difference. It is still worth a glance at that output before publishing; it is
no longer a step that only happens if someone remembers it.

**Why the sha256 placeholders look the way they do:** `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL`
and `NO_RELEASE_SHA256_DOES_NOT_EXIST_YET` cannot be mistaken for real hashes — they
fail Homebrew's format check immediately, and `bump-homebrew-formula.sh` refuses them
on the way in too. The winget zeros (`00000...0`, 64 characters, matching the required
hex-digest length) are the same idea in a format that must pass the schema's
length/hex-pattern check to be visibly wrong at review time rather than a plausible
fake. A plausible-looking fake digest is worse than either: it can be committed and
shipped without anyone noticing it doesn't match the actual artifact.

## Steps — routine release (once every prerequisite above is met)

### 1. Cut the release the same way as always

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

**Expected output:** CI's `tag-name` job validates the tag shape; `release.yml`
triggers on the same push.

### 2. Let `release.yml` open its PR, and watch its second job

The first job downloads the tag's tarball, hashes it, runs
`bump-homebrew-formula.sh`, and opens
`chore(packaging): bump Homebrew formula to vX.Y.Z` against this repo. The second
job (`macos-latest`) then downloads the formula the bump job uploaded, asserts its
`url` and `sha256` equal the digest that job computed, that the url ends in this
tag, and that **nothing else in the file changed** (both files normalised and
diffed) — then runs `verify-formula-locally.sh` in release mode against that exact
URL and digest: a real `brew install` of the formula the PR proposes.

**Expected output:** a PR modifying only `packaging/homebrew/devteam.rb`'s `url`
and `sha256` lines, and a green `macos-latest` check on the release run.

> **That check is not a gate, and must not be read as one.** The PR is opened by
> the bump job's own last step, so it is already open while the `macos-latest` job
> runs, and no branch rule marks the check required. It informs the human who
> merges; it stops nothing. And neither job has ever executed: the bump logic is
> covered by `tests/test_release_bump.py`, the Actions run itself by nothing.

### 3. Review and merge that PR

Confirm the diff touches only those two lines, and that the sha256 is a 64-char
hex string (the script already refuses anything else, but review it again — this is
the value users' machines will trust). If the `macos-latest` job is red, the formula
does not install; do not merge on the strength of the textual diff alone.

### 4. Publish to the tap (manual, no tooling exists for this step yet)

```bash
# Inside a checkout of the homebrew-devteam tap repo:
cp <this-repo>/packaging/homebrew/devteam.rb Formula/devteam.rb
git commit -am "devteam vX.Y.Z"
git push
```

**Expected output:** `brew install Dev-Toolbelt/devteam/devteam` resolves the new
version for users of the tap. **Unverified** — there is no tap to push to yet.

### 5. winget (manual, PR-gated, only after the installer shape is decided and built)

Decide the shape (see the section above), build the artifact, update `PackageVersion`
and the version directory, fill in the real `InstallerUrl`/`InstallerSha256` values,
then open a PR against `microsoft/winget-pkgs` following their contribution guide.
This step cannot be automated from this repository — it is review by Microsoft,
against Microsoft's repo.

## Verification

### Runs anywhere (no macOS, no Homebrew)

```bash
# The packaging gate: ruby -c on both formulas + the winget manifest contract.
# This is what CI's `packaging` job runs. Needs ruby and pyyaml; it installs
# pyyaml once if it is missing and fails rather than skipping if it still cannot.
bash .github/scripts/ci/04-packaging.sh

# Does the formula's declared payload actually run? Parses the install block,
# stages exactly those files, applies the shebang rewrite, runs the CLI.
python3 -m unittest tests.test_packaging

# Does the release bump script rewrite the formula correctly, idempotently, and
# refuse malformed input? Drives the real script against copies of the real formula.
python3 -m unittest tests.test_release_bump
```

**Expected result:** the gate prints
`packaging OK ✓ (with advisory findings: homebrew: release placeholders winget: unreleased scaffold)`
and exits 0; both test modules report `OK` — `Ran 12 tests` and `Ran 23 tests`
respectively. (Every count in this file was re-measured by running the command
printed beside it. Note the trap the third module carries:
`python3 -m unittest tests.test_json_contract` reports `Ran 1 test`, because that
module only yields its cases under discovery. Its real command is
`python3 -m unittest discover -s tests -t tests -p "test_json_contract.py"`, which
reports `Ran 35 tests`. The whole suite — `python3 -m unittest discover -s tests -t tests`,
which is what `.github/scripts/ci/03-python.sh` runs — reports `Ran 396 tests`.)

**The two advisory findings are expected and must stay green.** They report that
the Homebrew formula still carries its `vX.Y.Z`/`REPLACE_WITH_SHA256…` placeholders
and that winget is still at the `0.0.0`/`vX.Y.Z`/64-zeros scaffold — which is the
true state of this directory. They exist for the day someone reads `packaging/` and
concludes the channels are live. `04-packaging.sh`'s header records when each should
be promoted to blocking: once a release has actually gone out through that channel.

### Needs Homebrew ≥ 7 on PATH

Not macOS specifically — Homebrew runs on Linux and installs formulae there. What
this needs is `brew`, which the `ubuntu-latest` runner the `packaging` job uses does
not have. `release.yml` runs this same script on a `macos-latest` runner, so keeping
it out of the PR gate is a cost choice, not an impossibility.

```bash
# Real brew style + audit --formula + audit --strict --online +
# install --build-from-source + test + smoke, via a uniquely-named throwaway tap,
# against a tarball built from HEAD (`git archive … HEAD` — committed sources).
# Requires Homebrew >= 7; the preflight stage fails with that reason if it is older.
bash packaging/verify-formula-locally.sh
```

**Expected result:** a per-stage verdict table over twelve stages —
`preflight`, `artifact`, `tapsetup`, `style`, `audit`, `audit-strict`, `install`,
`brewtest`, `smoke`, `teardown`, `trust`, `immutability`.

`PASS` is what nine of them must report: `preflight`, `artifact`, `tapsetup`,
`install`, `brewtest`, `smoke`, `teardown`, `trust`, `immutability`. The other
three — `style`, `audit` and `audit-strict` — **record a verdict without gating
the run**: each reports `PASS` when clean and `FINDINGS` when not, and neither
value changes the exit code, because homebrew-core's house rules and a private
tap's requirements are not the same set. All three were `PASS` on the recorded
run. With `--keep`, `teardown` reports `SKIPPED` instead.

Read the script's header before the first run — it changes the machine and says
so. Reversible: it creates and removes a throwaway tap, installs and uninstalls
the `devteam` formula, and **will install the formula's declared python dependency
if the machine does not already have it** (announced loudly before the install,
and uninstalled again on exit only if that run is what installed it). Formulae
Homebrew pulled in *transitively* are detected and **reported, not removed** — the
teardown prints them with the `brew uninstall` line to run, because something else
on the machine may now depend on them, so "leaves the machine as it found it" is
not a claim this script makes.

**One change is permanent and deliberately not undone.** `brew style` and
`brew audit` are Homebrew *dev* commands; both bootstrap rubocop and the audit
gems into `$(brew --repository)/Library/Homebrew/vendor/bundle` — about 100 MB on a
prefix that has never run a dev command before (101 MB on the macOS machine these
documents were checked against). The script announces it before the stage that triggers it
and then leaves it alone: deleting that tree would damage Homebrew's own state,
and Homebrew reuses it for every later dev command.

Sandboxing: `DEVTEAM_HOME` points at a temp directory for every `devteam`
invocation, and `XDG_CONFIG_HOME` is set **per `brew` invocation** rather than
exported process-wide — git reads `$XDG_CONFIG_HOME/git/*` too, and the artifact
stage's `git describe`/`git archive` must see the user's real config. At exit the
script asserts the real `trust.json` and the tracked formula are both
byte-identical. Pass `--keep` to skip the **teardown only**: those two
assertions are read-only and still run, so a run that wrote to the tracked
formula cannot exit 0. After `--keep`, clean up by hand — the script prints the
three commands.

### What none of these replace

`winget validate` and `winget install --manifest` have never been run against the
winget manifests, and cannot be from macOS or Linux. `brew audit --cask` has never
been run against `devteam-app.rb`. Neither channel has been published.

On the cask, be precise about what the missing artifact does and does not block —
and note that "missing" now means *missing a signed, released* `.dmg`, not missing
any `.dmg`: `app/` builds an unsigned one locally, and that build is not a
substitute for the audit's subject. What is blocked is the **install**, the
**digest** and the **codesign/notarisation** checks — there is nothing published to
fetch or hash, and nothing signed to verify a signature on. It does not
block static style checking, and that checking is not clean:
`brew style packaging/homebrew/devteam-app.rb` reports seven offenses today, of
which **four are genuine cask cops** and are recorded here as a known, unfixed
state:

| Cop | Where |
|-----|-------|
| `Cask/StanzaOrder` | `depends_on macos:` out of order |
| `Cask/StanzaGrouping` | blank line inside a stanza group |
| `Cask/StanzaOrder` | `depends_on formula: "devteam"` out of order |
| `Cask/ArrayAlphabetization` | the `zap trash:` array is not alphabetical |

The other three (`Sorbet/StrictSigil`, `Sorbet/TrueSigil`,
`Style/FrozenStringLiteralComment`) are artefacts of checking a file *by path*:
Homebrew's rubocop config excludes those cops under `**/{Formula,Casks}/**/*.rb`,
and this file lives in `packaging/homebrew/`. Inside a tap's `Casks/` directory
they would not fire; the four cask cops would. None of the four is fixed.

**The same artefact applies to the formula, so do not read a bare
`brew style packaging/homebrew/devteam.rb` as contradicting the "clean" row
below.** Run directly on the tracked file it reports six offenses: the same three
path artefacts, plus three `FormulaAudit/Checksum` cops that fire on the
`REPLACE_WITH_SHA256_OF_RELEASE_TARBALL` placeholder. `verify-formula-locally.sh`
sees neither set — it styles a temporary copy that lives inside the throwaway
tap's `Formula/` directory and already carries a real url and digest. That is why
its `style` stage is clean while the tracked file is not, and both statements are
true of what they describe.

## What is proven, and by what

Every row names the thing that asserts it. A row with no named test or run does not
belong in this table.

| Claim | What asserts it |
|-------|-----------------|
| `devteam.rb` installs through a real Homebrew with its `install` block unmodified, and the resulting `bin/devteam` is executable and resolves | `verify-formula-locally.sh` stage `install`, run on macOS against Homebrew 7.0.6 |
| The `inreplace` shebang rewrite actually fires — the installed entry point runs the **declared** python, not whatever `python3` is first on `PATH` | Same run; the `install` stage reads the shebang off the fully-resolved binary and fails if it is still `#!/usr/bin/env python3` |
| `cli/` and `lib/devteam` land as siblings under `libexec/scripts`, which is what the entry point's `parent.parent / "lib"` lookup needs | Same run, `install` stage; and `tests/test_packaging.py::FormulaPayloadTest` from the parsed `install` block |
| The formula's own `test do` block passes | `verify-formula-locally.sh` stage `brewtest` (`brew test --verbose devteam`) |
| The installed binary answers `path --json` and `version --json` with exactly one JSON object carrying `ok: true`, and creates no store | Same run, `smoke` stage, with `DEVTEAM_HOME` pointed at a temp directory |
| `brew style` and `brew audit --formula` are clean on this formula, as is `brew audit --strict --online` | Same run, stages `style`, `audit` and `audit-strict`. `brew audit` reported three real findings on the formula as first written — `Formula[…].opt_bin` where `formula_opt_bin(…)` is wanted, and two `refute_predicate` assertions where `refute_path_exists` is wanted. All three are fixed in the file today, and the re-run was clean. **`brew audit --new` is deliberately not run and its result must not be quoted:** every new-formula check in Homebrew 7's `FormulaAuditor` is gated on the core tap — the four git-forge notability checks via `get_repo_data`'s `return unless @core_tap` (`formula_auditor.rb:858`), the rest directly — so on a private-tap formula `--new` is byte-identical to `--strict --online` and reports nothing about homebrew-core eligibility. And it would not pass if it were reached: `verify-formula-locally.sh`'s own comment records that calling `SharedAudits.github("Dev-Toolbelt", "dev-team-agents")` directly returns `GitHub repository not notable enough (<30 forks, <30 watchers and <75 stars)` — the check is unreachable, not passing. A clean `--new` here would mean "the checks did not run", not "the formula would be accepted" |
| The declared python dependency and the interpreter the shebang points at can never name different versions | The formula derives the interpreter from `deps` instead of repeating the version (`devteam.rb`'s `install`), and `tests/test_packaging.py::test_python_dependency_and_interpreter_path_name_the_same_formula` pins it |
| Drift between the declared python and homebrew-core's current `python3` is reported, not remembered | `verify-formula-locally.sh` preflight parses the `depends_on` line, resolves `brew info --json=v2 python3`, and prints both with a note when they differ |
| The files the `install` block's `.install` lines name are **sufficient** to start the CLI — nothing else in the framework is needed | `tests/test_packaging.py::StagedPayloadRunTest`, on Linux in CI, with the `devteam` package reachable only through `subprocess` so the repository's own `sys.path` cannot satisfy a missing import. **Bound:** only the `.install` lines are read. Any other line in the block — an `rm_f`, a `mv`, a conditional — is skipped, so nothing here proves the block does not *subtract* from the payload afterwards. The module's own docstring states this |
| The formula bump rewrites exactly the `url` and `sha256` lines, is idempotent, re-bumps an already-released formula, refuses malformed tags and digests, and leaves every other line byte-identical | `tests/test_release_bump.py` — 23 tests driving the real `bump-homebrew-formula.sh` against copies of the real formula |
| A wrong `--repo` cannot write this release's digest into a formula whose `url` already carries the requested tag | The url verification is repo-qualified — it matches the whole `url "https://github.com/<repo>/archive/refs/tags/<tag>.tar.gz"` line, not the tag fragment — and `test_a_wrong_repo_is_refused_even_when_the_url_already_carries_the_tag` pins it. Before that, the tag-fragment grep matched a url that was already there while the repo-independent `sha256` anchor matched the digest just written, and the run exited 0 |
| A formula where the rewrite would land in more than one place is refused, not rewritten on a guess | The script counts occurrences of the same two EREs it rewrites with, and dies if either exceeds one; `test_a_second_string_literal_digest_is_refused_and_the_file_is_untouched` and `test_a_second_url_matching_the_anchor_is_refused`. A `bottle do` block is unaffected — its digests are spelled `sha256 <platform>: "…"` and carry no `sha256 "` for the anchor to match — so such a formula still bumps correctly (`test_a_bottle_blocks_keyword_digests_are_not_ambiguous_and_the_bump_lands`) |
| A failed bump leaves the formula byte-identical rather than half-rewritten | The script stages its write to a sibling temp file and `mv`s it into place only after verification passes; asserted by `test_a_wrong_repo_fails_and_leaves_the_formula_byte_identical` and the two temp-file tests |
| Both formulas are valid ruby, and the winget manifests agree with each other and with their version directory | `.github/scripts/ci/04-packaging.sh`, blocking, in the `packaging` job of `ci.yml`, on every pull request and on pushes to `main`/tags. It checks `ruby -c`; and for winget: YAML parse, classification by **declared** `ManifestType` (not by filename — a spec-correct additional `locale` manifest is legal, and there may be N of them beside the one `defaultLocale`), the filename then checked against that type, the required-field set per type, agreement of `PackageIdentifier`/`PackageVersion`/`ManifestVersion` across the files, the version-directory name matching `PackageVersion`, digest format, and `InstallerUrl` ↔ version agreement including a refusal of a half-done bump in either direction |
| An `InstallerUrl` cannot be pointed somewhere other than this project's releases | Same gate. The origin is **derived** from `scripts/install.sh`'s own `GITHUB_OWNER`/`GITHUB_REPO` — a file outside `packaging/`, so the edit that redirects the InstallerUrls cannot move the goalpost with them — and failure to read it is exit 2, not a finding. The URL is parsed rather than substring-matched: the tag is the first path segment after `…/download/` and must equal `v<PackageVersion>` exactly, so `v1.0.0-rc1` no longer satisfies `1.0.0` |
| A 64-zero `InstallerSha256` cannot reach a release | Same gate, blocking, with no manual promotion step: the zeros digest is licensed only while `PackageVersion` **and** the URL tag are both still the scaffold placeholders. Once both are real it fails; a half-bump is itself a blocking finding, so there is no path through the middle |
| Every shell script in this directory is shellchecked | `.github/scripts/ci/01-lint.sh` — its target set is `scripts helpers .github/scripts packaging`, 67 `*.sh` files, up from 55. Nothing under `packaging/` or `.github/scripts/` was linted by any gate before that change, so `verify-formula-locally.sh` and the release/CI scripts were unchecked when they were written |
| `manifestVersion 1.12.0`, the required-field sets, and the `InstallerType`/`NestedInstallerType` enums are what the manifests and this runbook say they are | Read from `microsoft/winget-cli`'s schema file for v1.12.0, confirmed 2026-09-28 (URL in the Windows-shape section above) |

## What is unverified, and exactly why

| Item | Why it cannot be verified from this repository |
|------|--------------------------------------------------|
| `brew install` from a **published tap** | There is no `homebrew-devteam` tap repository. `verify-formula-locally.sh` removes the *tap-less* obstacle: Homebrew 7 rejects a formula file that is **not inside a tap** ("Homebrew requires formulae to be in a tap"), and separately disables `brew audit <path>` outright in favour of `brew audit <name>`, and refuses to load a formula from an untrusted tap. So the script creates a throwaway tap, trusts it inside a sandboxed `trust.json`, and installs from a path **inside that tap** — `brew install --build-from-source <tap>/Formula/devteam.rb` is a file-path install and it works, because the path is in a tap. What that cannot reach is the published path: nobody has ever run `brew tap` against a real repository and installed this formula from it |
| `brew install` of a **real release tarball** | The formula's `url` and `sha256` are still placeholders, and no release tarball exists for any digest to describe. The local verification installs from `git archive … HEAD` — committed sources, the same file layout but not the same bytes GitHub's codeload serves. Worth naming precisely, because it is the gap inside the gap: the recorded run packaged **committed** sources while testing a formula copy whose own edits were **uncommitted**, so what was installed and what was audited did not come from the same tree state. `release.yml`'s `macos-latest` job closes the codeload half on the first tag that is pushed |
| `release.yml` itself running end to end | It has never been triggered — the newest tag in this repository predates the commit that added the workflow. Its rewrite logic is no longer the unverified part: that lives in `bump-homebrew-formula.sh` with 23 tests. What is untested is the Actions run — the tag validation step, GitHub's codeload timing and retry loop, the PR creation, the artifact hand-off, and the digest passed between the two jobs. And the `macos-latest` job is **not a gate** even once it runs: the PR is opened by the bump job's last step, so it is already open while the job runs, and no branch rule marks the check required. A red check is a signal to whoever merges |
| macOS code signing and notarisation of the app | Needs an Apple Developer ID and an app-specific password/API key — account-level access this environment does not have and should not be given |
| `brew audit --cask` / any install of `devteam-app.rb` | The app now exists and builds, so the reason has moved: what is absent is a **signed, notarised** `.dmg` at a real version, published at a `url` that resolves. An unsigned local build cannot stand in — `brew audit --cask` verifies a Developer ID signature and a notarisation ticket, which an ad-hoc-signed build does not have, so the audit's correct verdict on it is *reject*. The cask also still points at a 404 and carries `sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"`. **Static checking is not blocked, and is not clean:** `brew style` on the cask reports four genuine cask-cop findings today (`Cask/StanzaOrder` ×2, `Cask/StanzaGrouping`, `Cask/ArrayAlphabetization`), all unfixed — see § Verification. What is no longer unverified: the macOS floor and the bundle id, both now read off `app/electron-builder.yml` and the pinned Electron's `Info.plist` rather than guessed |
| Whether the dmg filename the cask builds is the one the build produces | The two `version` values that decide it are hand-maintained in two files and no step derives either from the `app-v*` tag. Nothing compares them: `04-packaging.sh` runs `ruby -c` on the cask and never reads `app/package.json`, and `05-app.sh` never reads the cask. A release whose stamping step is missing produces a cask whose `url` 404s for a reason that looks like a mirror problem |
| The app on winget, at all | There is no manifest to verify — see § Prerequisites. This row is not "an artifact exists and cannot be checked here"; it is an absence, and it is the one gap in this directory that ADR-0011's channel table promises and nothing here drafts |
| Windows installer signing | Needs an Authenticode code-signing certificate — same reasoning. Required outright by candidate (a); recommended by (b) and (c) |
| Anything winget accepts or rejects | `winget` runs on Windows only. `04-packaging.sh` checks the manifests against the schema's rules and against each other; it has never asked `winget validate` for its opinion, and the two are not the same authority. The installer shape itself is undecided |
| The `InstallerSha256` values in the winget installer manifest | 64 zeros — no Windows installer has ever been built, signed or hashed |
| winget acceptance | Publication is itself a reviewed pull request to `microsoft/winget-pkgs`, against a real installer URL and hash that do not exist yet — review happens on Microsoft's infrastructure, not here |
| Whether a `portable` nested installer may point at a non-`.exe` launcher | The schema does not constrain it and Microsoft's manifest documentation does not address it. Only `winget validate` and `winget install --manifest` on a real Windows machine answer it — see the open question above |

## Contacts

| Role | Name / Channel |
|------|---------------|
| Primary owner | dev-team-agents maintainers |
| Escalation | repository issues — `Dev-Toolbelt/dev-team-agents` |
| On-call | none — this is not a production service |
