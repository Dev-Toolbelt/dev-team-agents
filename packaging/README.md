# Runbook: Publishing devteam to Homebrew and winget

**Last updated:** 2026-10-02
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
**What remains unproven is the published path**: the `homebrew-devteam` tap exists
but hosts no formula yet, no release tarball has ever been installed from it, no
Windows installer has been published, **no cask-installable artifact exists**, and the release
workflow has never been triggered. Nothing below claims otherwise — read the two
tables at the end for the split, item by item.

**The app exists now, and it is unsigned. Both halves of that matter.**
`app/` holds the Electron client decided by
[ADR-0015](../docs/development/adrs/0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md),
and `npm run dist:mac` produces a universal `Dev Team Agents.app` inside
`dev-team-agents-<version>.dmg` — a maintainer has run it on macOS and it built.
That is a recorded local build, in the same sense as the formula run above, and it
is **weaker than one**: nothing in the tree is the artifact (`app/.gitignore`
excludes `dist/` and `release/`), no CI job produces one —
`.github/scripts/ci/05-app.sh` runs `typecheck`, `lint` and `test` and
deliberately never `dist:mac`, because "one that builds an unsigned artifact is
shipping, not checking" — and the build is unsigned by configuration, not by
accident: `app/electron-builder.yml` signs and notarises only when the environment
carries credentials (none exist yet), and `app/build/after-build.cjs` prints
`UNSIGNED, UNNOTARISED BUILD — DIRECT-DOWNLOAD BETA ONLY` after every artifact built without them
([ADR-0027](../docs/development/adrs/0027-the-desktop-app-ships-an-unsigned-direct-download-beta-until-it-is-signed.md)
allows publishing it as a beta GitHub Release from an `app-v*` tag with
`SHA256SUMS.txt` beside it — never through this directory's cask or manifests;
`app/README.md` § Direct-download beta). A
universal build still carries an **ad-hoc** signature because macOS will not load
an unsigned arm64 Mach-O, and an ad-hoc signature is not a Developer ID
signature and carries no notarisation ticket: `brew audit --cask` rejects it, and
Gatekeeper refuses to open it without an explicit user override. So what the cask
still cannot describe is unchanged — a **signed, notarised** artifact at a **real
version** — and the app column of ADR-0011's channel table is still empty on both
platforms.

**The Windows packaging gap is closed at the scaffold level (M4.3 closeout), not at
the published-artifact level.** `app/electron-builder.yml` now has a `win` block
(NSIS, per-user, unsigned by configuration — see
[§ The Windows app installer shape — decided](#the-windows-app-installer-shape--decided)),
and `packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/` now exists with the
same three-file layout as the CLI's manifest. What has not changed: no Windows build
of the app has ever been produced, there is no Authenticode certificate, and nothing
here has been through `winget validate`. The gap this closes is a **decision** gap —
ADR-0011's channel table promised a shape and none existed; one now does, on paper,
in the same unpublished state as every other row in this document.

**The CI trigger, stated once.** `ci.yml`'s `push` trigger is `branches: [main]`
plus `tags: ["**"]`; every other branch is covered by `pull_request` only. So a
branch with no open PR gets no CI at all, and the accurate coverage for every
gate in this document is **every pull request, plus pushes to `main` and to
tags**. `ci.yml`'s own header states that trade-off and how to opt in (open a
draft PR). An earlier version of this file said "on every push" in four places;
it was simply false.

## What is left for the maintainer (by hand, and by exact name)

`release.yml` is written so that once the items below exist, **one tag push publishes
everything it can with no further code change**: `vX.Y.Z` for the framework and the CLI
channels, `app-vX.Y.Z` for the desktop app. Nothing in this section has been done, and
the workflow has never run — read § What is unverified before relying on any line of it.

### One-time: repository settings (Settings of `Dev-Toolbelt/dev-team-agents`)

- [ ] **Actions → General → Workflow permissions → "Allow GitHub Actions to create and
      approve pull requests".** Off by default for organisations; without it
      `open-formula-pr` fails (the tap publish is unaffected, the branch is still pushed)
- [ ] **Immutable releases on**, before the first publish (ADR-0027 § 4). The workflow
      creates each release as a draft, uploads, then publishes, so it is compatible
- [ ] **Make `Dev-Toolbelt/homebrew-devteam` public.** It was created private; `brew tap`
      fails for every user until it is public

### One-time: repository secrets (Settings → Secrets and variables → Actions)

| Secret | Needed for | Without it |
|--------|-----------|------------|
| `HOMEBREW_TAP_TOKEN` | `publish-homebrew-tap`: a fine-grained token, Contents read/write on `Dev-Toolbelt/homebrew-devteam` only | the job **fails** with a message naming the secret; the formula is then copied by hand |
| `MAC_CSC_LINK` | macOS signing: base64 of the exported Developer ID Application `.p12` (`base64 -i cert.p12`) | the dmg is built **unsigned** |
| `MAC_CSC_KEY_PASSWORD` | the `.p12`'s password | same |
| `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID` | notarisation, Apple-ID variant | no notarisation → the macOS build stays unsigned (a signed-but-not-notarised dmg still trips Gatekeeper) |
| `APPLE_API_KEY_P8`, `APPLE_API_KEY_ID`, `APPLE_API_ISSUER` | notarisation, API-key variant (contents of the `.p8`, key id, issuer id) — use **either** this set or the Apple-ID set | same |
| `WIN_CSC_LINK`, `WIN_CSC_KEY_PASSWORD` | Windows installer signing: base64 `.pfx` and its password | the installers are built **unsigned** |

No secret is ever needed for an unsigned build: that is the ADR-0027 beta, published as a
GitHub **prerelease**. Caveat on `WIN_CSC_*`: since the 2023 CA/B Forum rule new
Authenticode certificates live on hardware or in a cloud HSM and **cannot be exported to a
`.pfx`**. If that is the certificate you will hold, a `.pfx` secret does not apply and a
different mechanism (for example Azure Trusted Signing through electron-builder's
`win.azureSignOptions`) has to be wired — not done here.

### One-time: accounts

- [ ] **Apple Developer Program** membership; a **Developer ID Application** certificate
      exported as `.p12`; an app-specific password or an App Store Connect API key
      for `notarytool`
- [ ] **A code-signing certificate for Windows** (see the caveat above)
- [ ] **A GitHub personal access token with `public_repo`** for `wingetcreate`, kept on
      the machine that submits (`wingetcreate token --store`), never in this repository

### Every release

| Release | You push | The workflow produces | You do by hand |
|---------|----------|-----------------------|----------------|
| Framework + CLI | `vX.Y.Z` | the formula-bump PR, the macOS verification, the tap publish, the Windows CLI installers on the release, and the CLI's **winget manifests** (validated) as the artifact `winget-manifests-Devteam-X.Y.Z` | merge the formula PR; submit the winget manifests (below) |
| Desktop app | `app-vX.Y.Z` (must equal `app/package.json`'s `version`; `release-guard.mjs` enforces it) | the dmg and NSIS installers, `SHA256SUMS.txt`, a GitHub release (prerelease unless **both** platforms are verified signed). Only if the dmg passed `stapler` + `spctl`: the cask as `homebrew-cask-devteam-app`. Only if every installer verified Authenticode `Valid`: `winget-manifests-DevteamApp-X.Y.Z` | copy the cask to `Casks/devteam-app.rb` in the tap; submit the app's winget manifests **after** the CLI's (its manifest depends on `DevToolbelt.Devteam`) |

### Submitting to winget (manual, the exact command)

The manifests are in the run's artifact `winget-manifests-<Package>-<version>` (Actions
UI, or `gh run download <run-id> -n winget-manifests-Devteam-X.Y.Z -D wm`). Then:

```bash
winget install Microsoft.WingetCreate           # once
wingetcreate submit --token <PAT with public_repo> \
  wm/d/DevToolbelt/Devteam/X.Y.Z                # the directory holding the three .yaml files
```

`wingetcreate submit` forks `microsoft/winget-pkgs`, pushes the manifests and opens the
PR; Microsoft's validation pipeline and a human review follow. The CLI's first submission
creates the package; the app's follows once `DevToolbelt.Devteam` is accepted.

## What's in this directory

| Path | What it is | Status |
|------|-----------|--------|
| `homebrew/devteam.rb` | Formula for the CLI (`scripts/cli/devteam` + `scripts/lib/devteam/`) | Installs and passes its own `test do` block through a real Homebrew, via `verify-formula-locally.sh`'s throwaway tap. Never installed from a **published** tap, and its `url`/`sha256` are still placeholders. |
| `homebrew/devteam-app.rb` | Cask for the desktop app's signed, notarised `.dmg` | Still unpublishable, for a narrower reason than before: the app exists (`app/`, ADR-0015) and builds an **unsigned** `.dmg`; no signed, notarised artifact and no real version exist. Its macOS floor and bundle id are no longer guesses — both are now read from `app/electron-builder.yml` (see the row below). `ruby -c` is the only **CI** check that touches it, and it passes. `brew style` has been run on it by hand and reports four unfixed cask-cop findings — see § Verification. |
| `winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/` | winget multi-file manifest (version, installer, locale) for the **desktop app** | **M4.3 closeout.** Scaffold at a placeholder version, same discipline as the CLI's manifest. `InstallerType: nullsoft` is a **decided** shape (NSIS, per-user, unsigned-by-configuration — see [the Windows-app section](#the-windows-app-installer-shape--decided) below and `app/electron-builder.yml`'s `win`/`nsis` blocks), not a placeholder like the CLI's still-undecided `exe`. Still no Authenticode certificate to sign it with, and no Windows build has ever been produced. Contract-checked in CI; never through `winget validate`. |
| `winget/manifests/d/DevToolbelt/Devteam/0.0.0/` | winget multi-file manifest (version, installer, locale) for the CLI | Scaffold at a placeholder version — no Windows installer exists to point at. Contract-checked in CI; never through `winget validate`. |
| `verify-formula-locally.sh` | Exercises `devteam.rb` end to end through a real Homebrew (see Verification below) | Run and passing on macOS with Homebrew 7.0.6. Needs `brew` on PATH and Homebrew ≥ 7; the `packaging` job runs on `ubuntu-latest`, which has no Homebrew, so it is not run there. That is a cost choice, not an impossibility — Homebrew runs on Linux too, and `release.yml` runs this very script on a `macos-latest` runner. |
| `../.github/scripts/ci/04-packaging.sh` | The CI gate for this directory: `ruby -c` on both formulas, plus the winget manifest contract | Runs on every pull request and on pushes to `main`/tags (the `packaging` job in `ci.yml`). Two advisories fire today, deliberately — see below. |
| `../.github/scripts/release/bump-homebrew-formula.sh` | Rewrites the formula's `url`/`sha256` to a released tag and digest | Covered by `tests/test_release_bump.py` (23 tests, green). The **workflow** that calls it has still never run. |
| `../.github/workflows/release.yml` | On a `vX.Y.Z` tag push, downloads that tag's release tarball, hashes it, opens a PR bumping the formula, uploads the rewritten formula as an artifact, then on `macos-latest` asserts that artifact's `url`/`sha256` against the computed digest and that nothing else in the file changed, and brew-installs it against the real tarball | Automated, but unrun — no tag has been pushed since the workflow was added (the newest tag predates the commit that added it). **The `macos-latest` job is not a gate**: the bump job opens the PR in its own last step, so the PR is already open while the job runs, and no branch rule marks the check required. Its own `RESIDUAL` block says so. |
| `../.github/workflows/winget-manifests.yml` | Reusable workflow: renders a winget scaffold at the real version with the digests from the release's `SHA256SUMS.txt`, runs the `04-packaging.sh` winget gate over it, uploads it, and runs `winget validate` on `windows-latest` | Written, never run. The renderer is tested (`tests/test_release_render.py`); the Windows job is not |
| `../.github/scripts/release/render-winget-manifests.py`, `render-app-cask.py` | The renderers behind that workflow and the app's cask job | `tests/test_release_render.py` drives both, and runs the real gate over the rendered winget tree |
| `../.github/scripts/release/verify-mac-notarised.sh`, `stamp-code-signed.cjs` | Mounts the dmg and runs `codesign`, `stapler validate`, `spctl`; flips `CODE_SIGNED` in the CI working copy only | The negative path was run locally (an ad-hoc-signed dmg fails all but the first check, exit 1). The positive path needs a notarised build and has never run |

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

- [x] **The tap repository exists**: [`Dev-Toolbelt/homebrew-devteam`](https://github.com/Dev-Toolbelt/homebrew-devteam),
      holding a README. It has no `Formula/` yet — the first one is the first release
      that contains the CLI, published by `release.yml`
- [ ] **The tap is public.** It was created private; `brew tap` cannot read a private
      repository without credentials, so every user's install fails until it is public
- [ ] **`HOMEBREW_TAP_TOKEN`** as a repository secret here: a fine-grained token with
      Contents read/write on `Dev-Toolbelt/homebrew-devteam` only. `release.yml`'s
      `publish-homebrew-tap` job pushes the verified formula with it; `GITHUB_TOKEN`
      cannot push to another repository. Without it the job **fails** with a message
      naming the secret
- [ ] **Actions may create pull requests** (repository setting) — see § What is left

### Homebrew — app cask (`devteam-app.rb`)

- [x] The Electron app itself (`app/`, decided by ADR-0015) and a build that
      produces the artifact shape the cask names: `npm run dist:mac` →
      `release/dev-team-agents-<version>.dmg` containing a universal
      `Dev Team Agents.app`. **This box is ticked for existence only** — the
      build is unsigned, no CI job runs it, and no artifact is committed
- [x] The tag is the version authority: `release-guard.mjs` (run by the `app-prepare` job)
      refuses an `app-v*` tag that differs from `app/package.json`'s `version` or a dirty
      tree, and the cask's `version` is then rendered from that same tag
- [ ] An Apple Developer ID (paid Apple Developer Program membership), exported as a
      `.p12` into the secrets `MAC_CSC_LINK` / `MAC_CSC_KEY_PASSWORD`. **No config edit is
      needed any more**: `app/electron-builder.yml` signs when the environment carries
      credentials and builds unsigned when it does not (ADR-0027)
- [ ] Notarisation credentials (`APPLE_ID` + `APPLE_APP_SPECIFIC_PASSWORD` +
      `APPLE_TEAM_ID`, or `APPLE_API_KEY_P8` + `APPLE_API_KEY_ID` + `APPLE_API_ISSUER`) —
      generated from the Apple account, not something CI can create for itself
- [ ] A first `app-v*` release that ran with both, and whose `app-build-mac` job passed
      `verify-mac-notarised.sh`. Only then is the rendered cask worth copying to the tap
- [ ] The same tap repository as above (a cask lives in `Casks/`, alongside
      `Formula/`, in one tap)

### winget — CLI manifest

- [x] **A decided Windows packaging shape for the CLI** (ADR-0028): a per-user NSIS
      installer with an embedded CPython — see
      [the next section](#the-windows-installer-shape-for-the-cli--decided-adr-0028)
- [x] **A build that produces it**: `windows-cli/build.py`, run by `release.yml`'s
      `windows-cli-installer` job, which also attaches the installers and their
      `SHA256SUMS.txt` to the tag's release
- [ ] A code-signing certificate (Authenticode). winget does not require signing, but
      the unsigned installer triggers SmartScreen for every user, as the app does.
      The **CLI installer's signing is not wired** (`release.yml` builds it unsigned); only
      the app's installers sign, from `WIN_CSC_LINK` / `WIN_CSC_KEY_PASSWORD`
- [ ] A GitHub account able to open a pull request against
      `microsoft/winget-pkgs` (public repo, no special access needed — just review)

### winget — app manifest

- [x] **The manifest scaffold.** `packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/`
      exists now (M4.3 closeout), at the same placeholder version and hash discipline
      as the CLI's sibling manifest. **This box is ticked for existence only** — see
      the unchecked items below for everything it still needs
- [x] **A decided Windows packaging shape.** NSIS, per-user, unsigned by
      configuration — see [§ The Windows app installer shape — decided](#the-windows-app-installer-shape--decided).
      `app/electron-builder.yml` now has `win` and `nsis` blocks
- [ ] A Windows build of the app. The `app-build-win` job builds it on `app-v*` tags; it
      has never run
- [ ] Windows code-signing (Authenticode) via `WIN_CSC_LINK` / `WIN_CSC_KEY_PASSWORD`
      (see the exportability caveat in § What is left). Without it the installers are
      unsigned, SmartScreen warns, and **no app winget manifest is rendered**
- [ ] The rendered `winget-manifests-DevteamApp-<version>` artifact (real URLs and
      digests, from a verified-signed release) submitted with `wingetcreate submit`,
      after the CLI's package is accepted

## The Windows installer shape for the CLI — decided (ADR-0028)

This section is about the **CLI** package (`DevToolbelt.Devteam`) only; the app's shape
is [§ The Windows app installer shape — decided](#the-windows-app-installer-shape--decided).

| Piece | What it is | Where |
|-------|-----------|-------|
| Installer | NSIS, per-user (`%LOCALAPPDATA%\Programs\devteam`), no elevation, `devteam-setup-<version>-<arch>.exe` for x64 and arm64 | `windows-cli/devteam-cli.nsi` |
| Python | The official CPython **embeddable** distribution, pinned by URL and SHA-256 (cross-checked against python.org's sigstore bundle) | `windows-cli/pins.json` |
| `devteam.exe` | distlib's script launcher (the stub pip uses for console scripts), written at install time with an absolute shebang to the embedded `python.exe` | `windows-cli/postinstall.py` |
| Framework | The same version's tree, installed into the store with `devteam store install`; an installed version and an existing `current` are left alone | `windows-cli/postinstall.py` |
| PATH | `bin\` appended to the user `PATH` through `winreg`, never NSIS strings (their 1024-character limit would truncate a long PATH); the uninstaller removes it | `windows-cli/postinstall.py` |
| Git for Windows | Offered through `winget install Git.Git --scope user` when no Git Bash is found; a silent install skips the prompt and the manifest declares `Git.Git` instead | `windows-cli/devteam-cli.nsi`, the winget manifest |

The uninstaller removes only its own directory and its PATH entry — never the store.

**Build it locally** (macOS, Linux or Windows; needs `git` and `makensis`, and reuses
the NSIS electron-builder downloads for the app when there is no `makensis` on PATH):

```bash
python3 packaging/windows-cli/build.py --arch all
```

The installers and `SHA256SUMS.txt` land in `packaging/windows-cli/dist/` (gitignored).
The framework comes from `git archive HEAD`, so a build is the committed tree.

**What is proven where.** `tests/test_windows_cli_installer.py` runs anywhere: the PATH
edit, the launcher's payload (Python starts the real CLI through it), the staged layout
the NSIS script copies, and the pins. The release job installs silently on a Windows
runner, runs `devteam.exe`, checks the store and the PATH, and uninstalls. The wizard and
its Git prompt are exercised only by a person.

## The Windows app installer shape — decided

Unlike the CLI section above, this one is a decision, not a set of candidates left
open for a Windows machine to settle. The reason it can be decided here is that the
question is not winget's opinion (undecidable from macOS) — it is which
electron-builder Windows target to point at, which is documented behaviour, not a
runtime unknown.

### The three candidates electron-builder and winget both describe

| | Shape | Signing | Install scope / UAC | Update & uninstall | Toolchain |
|---|---|---|---|---|---|
| **NSIS (`.exe`)** — chosen | Unsigned installs with a SmartScreen warning, same trade-off the unsigned macOS `.dmg` already ships (Gatekeeper prompt) | `perMachine: false` (per-user) needs no admin elevation — an unsigned installer asking for elevation is the more alarming prompt of the two | NSIS's own generated uninstaller registers with Add/Remove Programs; no auto-update wired (electron-updater is out of scope for this decision) | None — electron-builder's default, best-documented target, no external toolset |
| **MSI** | Also installs unsigned (a warning, not a refusal) | Same per-user option exists but is less idiomatic for MSI, which enterprises expect per-machine with GPO deployment | MSI's own uninstall path via Windows Installer service | Needs the WiX toolset wired into the build for no benefit this project needs (no enterprise/GPO deployment story is in scope) |
| **AppX / MSIX** | **Requires a trusted signing identity to install outside the Microsoft Store at all** — even a self-signed certificate must be imported into the user's trusted root store by hand before sideloading works; there is no "warned but allowed" path the way NSIS and MSI have | N/A — blocked before scope matters | Cleanest update/uninstall story of the three (App Installer service) | Off the table outright: no Authenticode certificate exists (packaging/README.md § Prerequisites), and MSIX cannot substitute a self-signed cert the way an ad-hoc macOS signature stands in for a while |

**Chosen: NSIS**, `perMachine: false`, `oneClick: false` (shows the install-location
wizard so a user who sees the SmartScreen warning also sees what they are agreeing
to). Wired in `app/electron-builder.yml`'s `win` and `nsis` blocks, with
`forceCodeSigning: false` making a future accidental signing attempt (found
credentials on a build machine) a no-op rather than a build failure — the explicit
counterpart to `mac.identity: null` on the macOS side. No
`certificateFile`/`certificatePassword` keys are set anywhere in the config, because
none exist to set.

**What this decision does not resolve.** `winget validate` and `winget install
--manifest` have never been run against
`packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/` — see § Verification and
§ What is unverified below. Nothing here proves winget accepts an `InstallerType:
nullsoft` entry with a `Dependencies.PackageDependencies` pointing at
`DevToolbelt.Devteam`; that dependency stanza is this repository's best expression of
"the app needs the CLI" (ADR-0015's resolution order), not a confirmed winget
behaviour. And no Windows build of the app has ever been produced, so `InstallerUrl`
and `InstallerSha256` in that manifest are placeholders in exactly the sense the CLI's
are.

## Placeholders in this directory — what replaces them, and from where

| File | Placeholder | Replaced by | Source of the real value |
|------|------------|-------------|---------------------------|
| `homebrew/devteam.rb` | `url "...tags/vX.Y.Z.tar.gz"` | The real tag | `.github/scripts/release/bump-homebrew-formula.sh`, called by `release.yml`, from `github.ref_name` on tag push |
| `homebrew/devteam.rb` | `sha256 "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL"` | 64-char hex digest | The same script, automatically — `sha256sum` of the downloaded tag tarball, never hand-written. The script refuses anything that is not 64 lowercase hex characters |
| `homebrew/devteam-app.rb` | Entire file marked UNRELEASED | A real cask, once a **signed** build exists | Manual — write it against the actual signed, notarised `.dmg`; do not just fill in these placeholders. The header no longer claims the app is absent: `app/` exists and builds an unsigned dmg |
| `homebrew/devteam-app.rb` | `version "0.0.0-unreleased"` | The app's real release tag (e.g. `app-v1.0.0`) | The `app-v*` tag, which `release-guard.mjs` requires to equal `app/package.json`'s `version`; `render-app-cask.py` writes it into the cask. **Coupled**: `dmg.artifactName: dev-team-agents-${version}.dmg` derives the dmg filename from `app/package.json`'s `version` while the cask's `url` derives it from this line, so the two must be one string at release time. They disagree today on purpose (`0.0.0` vs `0.0.0-unreleased`) and must not be reconciled by hand — see the cask header |
| `homebrew/devteam-app.rb` | `sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"` | 64-char hex digest of the real notarised `.dmg` | Manual — hash the actual release artifact once it exists; do not reuse the CLI formula's automation blindly, since a cask's artifact is signed/notarised and that should be verified, not just hashed. **Never the digest of a local unsigned build**, which is a different artifact with the same filename |
| `homebrew/devteam-app.rb` | ~~`depends_on macos: ">= :big_sur"`~~ — **no longer a placeholder** | `">= :ventura"`, measured | `app/node_modules/electron/dist/Electron.app/Contents/Info.plist` → `LSMinimumSystemVersion` **13.0** for Electron 44.5.1, mirrored by `mac.minimumSystemVersion: '13.0'` in `app/electron-builder.yml`. Big Sur was wrong in the dangerous direction: it licensed an install on a system the app cannot launch on. **Re-measure on every Electron major** — the floor moves with it, nothing checks the pair, and this is the one row in this table that comes back |
| `homebrew/devteam-app.rb` | ~~placeholder bundle id in `zap trash:`~~ — **no longer a placeholder** | `com.devtoolbelt.dev-team-agents-app` | `appId` in `app/electron-builder.yml`; `app "Dev Team Agents.app"` likewise matches its `productName`. Both confirmed against the build config, both still unchecked by any gate |
| `winget/manifests/.../DevToolbelt.Devteam.yaml` (version dir + all 3 files) | `0.0.0` (`PackageVersion`, directory name) | The real release version | Manual — rename the `0.0.0/` directory and update `PackageVersion` in all three files together when a Windows installer first ships. `04-packaging.sh` fails the build if those four edits disagree with each other |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | Both `InstallerUrl` entries (`vX.Y.Z`, filenames) | Real asset URLs | Manual — wherever the installers actually get uploaded (a GitHub Release is the obvious place, not decided). `04-packaging.sh` refuses a half-bump in either direction: the URL's tag and `PackageVersion` must move together |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | Both `InstallerSha256` (64 zeros — deliberately not a plausible-looking fake hash) | Real digests of the real installers | Manual — hash the actual artifacts; **do this after signing**, if the chosen shape signs, since signing changes the bytes and therefore the hash |
| `winget/manifests/.../DevToolbelt.Devteam.installer.yaml` | ~~`InstallerType: exe`~~ — **decided**: `nullsoft` (ADR-0028) | — | The URLs and digests remain placeholders; the real digests are in the release's `SHA256SUMS.txt` |
| `winget/manifests/.../DevToolbelt.DevteamApp.yaml` (version dir + all 3 files) | `0.0.0` (`PackageVersion`, directory name) | The real release version | Manual — same four-edit discipline as the CLI's row above, once a Windows build of the app first ships |
| `winget/manifests/.../DevToolbelt.DevteamApp.installer.yaml` | Both `InstallerUrl` entries — the tag segment is `vX.Y.Z` **with** the prefix, the filename segment is `X.Y.Z` **without** it, because `nsis.artifactName` interpolates `${version}` and only the tag carries a `v`. Making the two match is a 404 | Real asset URLs | Manual — wherever the app's Windows build actually gets uploaded (a GitHub Release is the obvious place, matching `app/electron-builder.yml`'s `nsis.artifactName`). `04-packaging.sh` refuses a half-bump in either direction |
| `winget/manifests/.../DevToolbelt.DevteamApp.installer.yaml` | Both `InstallerSha256` (64 zeros) | Real digests of the real installer `.exe` per architecture | Manual — hash the actual built artifacts; nothing here signs them, so no post-signing re-hash step is needed unless a certificate is added later |

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
triggers on the same push. (An app release is tagged `app-vX.Y.Z` instead; CI's
`tag-name` job accepts both shapes, and every framework job skips on an app tag.)

**Do not create the GitHub release by hand.** `release.yml`'s `windows-cli-installer` job
creates it, and the app's "Install the CLI" accepts only a release whose author is
`github-actions[bot]` (ADR-0028): a release made by hand is skipped, and its installers are
never offered. Turn on immutable releases once per repository, so a published asset cannot be
swapped afterwards.

### 2. Let `release.yml` open its PR, and watch the macOS job

The first job downloads the tag's tarball, hashes it and runs
`bump-homebrew-formula.sh`; a separate job, `open-formula-pr`, opens
`chore(packaging): bump Homebrew formula to vX.Y.Z` against this repo (separate so that a
repository which forbids Actions from creating PRs cannot stop the verification and the
tap publish). The macOS job (`macos-latest`, which first makes sure Homebrew is >= 7) then downloads the formula the bump job uploaded, asserts its
`url` and `sha256` equal the digest that job computed, that the url ends in this
tag, and that **nothing else in the file changed** (both files normalised and
diffed) — then runs `verify-formula-locally.sh` in release mode against that exact
URL and digest: a real `brew install` of the formula the PR proposes.

**Expected output:** a PR modifying only `packaging/homebrew/devteam.rb`'s `url`
and `sha256` lines, and a green `macos-latest` check on the release run.

> **That check is not a gate on the PR, and must not be read as one.** The PR is
> opened in parallel with the `macos-latest` job and no branch rule marks the check
> required; it informs the human who merges. It does gate the tap: `publish-homebrew-tap`
> needs it. And neither job has ever executed: the bump logic is
> covered by `tests/test_release_bump.py`, the Actions run itself by nothing.

### 3. Review and merge that PR

Confirm the diff touches only those two lines, and that the sha256 is a 64-char
hex string (the script already refuses anything else, but review it again — this is
the value users' machines will trust). If the `macos-latest` job is red, the formula
does not install; do not merge on the strength of the textual diff alone.

### 4. Publish to the tap (automated, after the macOS verification passes)

`release.yml`'s `publish-homebrew-tap` job copies the formula the bump job produced —
the bytes the macOS job installed and tested — to `Formula/devteam.rb` in
`Dev-Toolbelt/homebrew-devteam` and pushes it (to the tap's default branch; an empty tap
gets `main`). Without `HOMEBREW_TAP_TOKEN` it **fails** with a message naming the secret;
then do it by hand:

```bash
# Inside a checkout of the homebrew-devteam tap repo:
cp <this-repo>/packaging/homebrew/devteam.rb Formula/devteam.rb
git commit -am "devteam X.Y.Z"
git push
```

**Expected output:** `brew install dev-toolbelt/devteam/devteam` resolves the new
version. **Unverified** — no release has run this job yet.

### 5. winget (manual, PR-gated)

`release.yml` builds the CLI installers and attaches them to the release, then its
`winget-cli-manifests` job renders the three manifests at this version (directory,
`PackageVersion`, `InstallerUrl`, `InstallerSha256` — the four edits `04-packaging.sh`
enforces — with digests read from the release's `SHA256SUMS.txt`), runs that gate over
them and runs `winget validate` on a Windows runner. Download the artifact and run
`wingetcreate submit` as written in § What is left. This step cannot be automated from
this repository — it is review by Microsoft, against Microsoft's repo.

### 6. The desktop app (`app-vX.Y.Z`)

`app-prepare` checks the tag and runs `release-guard.mjs`, and detects which secrets exist
(booleans only). `app-build-mac` and `app-build-win` build; with credentials, electron-builder
signs (and notarises on macOS), `app/build/after-build.cjs` inspects the result and **fails the
build** when credentials were supplied but the artifact does not verify, and the job then
checks the artifact a user would download: `verify-mac-notarised.sh` (`codesign`, `stapler
validate`, `spctl -a -vvv`) on the dmg, `Get-AuthenticodeSignature` on each installer.
`app-publish` writes `SHA256SUMS.txt` and publishes the release as a draft-then-publish
(immutable-release safe) — a **prerelease** unless both platforms verified. `app-cask` and
`winget-app-manifests` run only for a platform that verified, and only render artifacts.

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
winget manifests — **either set, CLI or app** — and cannot be from macOS or Linux.
`brew audit --cask` has never been run against `devteam-app.rb`. Neither channel has
been published. Adding the app's manifest set did not change this: `04-packaging.sh`
is a schema-and-cross-file-agreement check written against the manifest schema's own
JSON, not a stand-in for `winget validate`'s opinion, and it says nothing about
whether winget actually accepts `InstallerType: nullsoft` with a
`Dependencies.PackageDependencies` entry the way this manifest set writes it. A
Windows operator running `winget validate packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/`
is the only thing that answers that.

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
| The winget renderer produces the four coordinated edits for both packages, refuses a digest missing from `SHA256SUMS.txt` and a tag of the wrong shape, and its output passes the repository's own winget gate (while a directory left at `0.0.0` fails it) | `tests/test_release_render.py::WingetRenderTest`, which runs `04-packaging.sh` over the rendered tree via `WINGET_ROOT` / `PACKAGING_WINGET_ONLY` |
| The app cask renderer changes only `version` and `sha256`, drops the scaffold's comments, and its output parses | `tests/test_release_render.py::CaskRenderTest` |
| An unsigned or ad-hoc-signed dmg cannot pass `verify-mac-notarised.sh` | Run locally against an ad-hoc-signed test dmg: three of four checks fail, exit 1. Only the negative path has run |
| `after-build.cjs` prints the UNSIGNED banner and records `unsigned` when credentials are absent, and throws when credentials are present but the artifact cannot be verified | Run directly against synthetic build contexts; not under electron-builder |
| Every `run:` block in the three workflows parses as shell, and every `needs:` names a job | A local script (`bash -n` over each block, YAML load); not `actionlint`, which was not installed |
| Every shell script in this directory is shellchecked | `.github/scripts/ci/01-lint.sh` — its target set is `scripts helpers .github/scripts packaging`, 67 `*.sh` files, up from 55. Nothing under `packaging/` or `.github/scripts/` was linted by any gate before that change, so `verify-formula-locally.sh` and the release/CI scripts were unchecked when they were written |
| `manifestVersion 1.12.0`, the required-field sets, and the `InstallerType`/`NestedInstallerType` enums are what the manifests and this runbook say they are | Read from `microsoft/winget-cli`'s schema file for v1.12.0, confirmed 2026-09-28 (URL in the Windows-shape section above) |

## What is unverified, and exactly why

| Item | Why it cannot be verified from this repository |
|------|--------------------------------------------------|
| `brew install` from a **published tap** | There is no `homebrew-devteam` tap repository. `verify-formula-locally.sh` removes the *tap-less* obstacle: Homebrew 7 rejects a formula file that is **not inside a tap** ("Homebrew requires formulae to be in a tap"), and separately disables `brew audit <path>` outright in favour of `brew audit <name>`, and refuses to load a formula from an untrusted tap. So the script creates a throwaway tap, trusts it inside a sandboxed `trust.json`, and installs from a path **inside that tap** — `brew install --build-from-source <tap>/Formula/devteam.rb` is a file-path install and it works, because the path is in a tap. What that cannot reach is the published path: nobody has ever run `brew tap` against a real repository and installed this formula from it |
| `brew install` of a **real release tarball** | The formula's `url` and `sha256` are still placeholders, and no release tarball exists for any digest to describe. The local verification installs from `git archive … HEAD` — committed sources, the same file layout but not the same bytes GitHub's codeload serves. Worth naming precisely, because it is the gap inside the gap: the recorded run packaged **committed** sources while testing a formula copy whose own edits were **uncommitted**, so what was installed and what was audited did not come from the same tree state. `release.yml`'s `macos-latest` job closes the codeload half on the first tag that is pushed |
| `release.yml` itself running end to end | It has never been triggered — the newest tag in this repository predates the commit that added the workflow. Its rewrite logic is no longer the unverified part: that lives in `bump-homebrew-formula.sh` with 23 tests. What is untested is the Actions run — the tag validation step, GitHub's codeload timing and retry loop, the PR creation, the artifact hand-off, and the digest passed between the two jobs. And the `macos-latest` job is **not a gate** even once it runs: the PR is opened by the bump job's last step, so it is already open while the job runs, and no branch rule marks the check required. A red check is a signal to whoever merges |
| macOS code signing and notarisation of the app | The wiring exists (`electron-builder.yml`, `after-build.cjs`, `app-build-mac`) but needs an Apple Developer ID and notarisation credentials — account-level access this environment does not have and should not be given. Whether electron-builder 26.15.3 notarises by default from the `APPLE_*` variables with `mac.notarize` unset, and whether its default entitlements pass notarisation, are read from its documentation, not run |
| The `app-*` jobs, the `winget-*` jobs and `open-formula-pr` | Never executed. Specifically unconfirmed: that `winget` exists or can be bootstrapped on `windows-latest`; that `winget validate` accepts the `PackageDependencies` shape; that `Homebrew` on `macos-latest` can be brought to >= 7 with one `brew update`; that `choco install nsis --version 3.13.0` resolves; the draft-then-publish flow against the immutable-releases setting; the `CODE_SIGNED` stamp; the unpinned `actions/setup-node@v4` (the other actions are SHA-pinned) |
| `brew audit --cask` on the rendered cask | Not run anywhere: the render job checks `ruby -c` only. Run it on the tap once a notarised cask exists |
| The app's own signing banner | `app/src/main/build-info.ts` keeps `CODE_SIGNED = false`; the release jobs flip it in the CI working copy for a credentialed build. That makes the packaged app say "signed" only if the job's verification passes — but the mechanism is a text substitution nobody has run in CI |
| `brew audit --cask` / any install of `devteam-app.rb` | The app now exists and builds, so the reason has moved: what is absent is a **signed, notarised** `.dmg` at a real version, published at a `url` that resolves. An unsigned local build cannot stand in — `brew audit --cask` verifies a Developer ID signature and a notarisation ticket, which an ad-hoc-signed build does not have, so the audit's correct verdict on it is *reject*. The cask also still points at a 404 and carries `sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"`. **Static checking is not blocked, and is not clean:** `brew style` on the cask reports four genuine cask-cop findings today (`Cask/StanzaOrder` ×2, `Cask/StanzaGrouping`, `Cask/ArrayAlphabetization`), all unfixed — see § Verification. What is no longer unverified: the macOS floor and the bundle id, both now read off `app/electron-builder.yml` and the pinned Electron's `Info.plist` rather than guessed |
| Whether the dmg filename the cask builds is the one the build produces | The two `version` values that decide it are hand-maintained in two files and no step derives either from the `app-v*` tag. Nothing compares them: `04-packaging.sh` runs `ruby -c` on the cask and never reads `app/package.json`, and `05-app.sh` never reads the cask. A release whose stamping step is missing produces a cask whose `url` 404s for a reason that looks like a mirror problem |
| The app on winget, published | The manifest scaffold now exists (M4.3 closeout) — this row is no longer "there is no manifest", it is "the manifest has never been validated or installed". No Windows build of the app has ever been produced, so `InstallerUrl`/`InstallerSha256` are placeholders and there is nothing for `winget validate` to fetch yet |
| Whether winget accepts `InstallerType: nullsoft` with this manifest's `Dependencies.PackageDependencies` shape | The schema permits both fields; nothing here has asked `winget validate` whether it accepts a `PackageDependencies` entry naming a **CLI** package (`DevToolbelt.Devteam`) from an app manifest the way this file writes it. That is a winget-behaviour question, not a schema question, and only a real Windows machine answers it |
| Windows installer signing (CLI or app) | Needs an Authenticode code-signing certificate — same reasoning for both packages. Required outright by CLI candidate (a); recommended for the CLI's other candidates and for the app's NSIS installer |
| Anything winget accepts or rejects, for either package | `winget` runs on Windows only. `04-packaging.sh` checks the manifests against the schema's rules and against each other; it has never asked `winget validate` for its opinion, and the two are not the same authority. The CLI's installer shape is still undecided; the app's is decided (NSIS) but unbuilt |
| The `InstallerSha256` values in both winget installer manifests | 64 zeros in each — no Windows installer, CLI or app, has ever been built, signed or hashed |
| winget acceptance, for either package | Publication is itself a reviewed pull request to `microsoft/winget-pkgs`, against a real installer URL and hash that do not exist yet — review happens on Microsoft's infrastructure, not here |
| Whether a `portable` nested installer may point at a non-`.exe` launcher | The schema does not constrain it and Microsoft's manifest documentation does not address it. Only `winget validate` and `winget install --manifest` on a real Windows machine answer it — see the open question above. This applies to the CLI's candidates (b)/(c) only; the app's NSIS shape does not use a nested installer |

## Contacts

| Role | Name / Channel |
|------|---------------|
| Primary owner | dev-team-agents maintainers |
| Escalation | repository issues — `Dev-Toolbelt/dev-team-agents` |
| On-call | none — this is not a production service |
