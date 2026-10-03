# ADR-0027: The desktop app ships an unsigned direct-download beta until it is signed

**Date:** 2026-10-02
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

This ADR narrows ADR-0011; it does not reverse it. ADR-0011's channel table and its "macOS artifacts
are signed and notarised; the Windows installer is code-signed" stay the bar for the Homebrew cask and
winget. This ADR adds a provisional row beside them, for the app only, with an end condition.

## Context

Every amendment to ADR-0011 ends at the same blocker: an Apple Developer ID and an Authenticode
certificate that the repository owner does not hold yet. Waiting for both has left the app with no
users, so nothing about it — the CLI resolution order of ADR-0015 § 5, the client write gate of
ADR-0014, the background supervisor — has met a machine other than the maintainer's.

`npm run dist:all` already produces the universal `.dmg` and the NSIS installers (combined, x64,
arm64) in one pass on a Mac. ADR-0011's last amendment said "no Windows build of the app has ever been
produced"; that no longer holds. The rest of its blocker list does: nothing is signed, notarised or
published.

## Decision

1. **A direct-download beta row, app only.** The installers `dist:all` produces may be published as a
   GitHub Release, linked from the project's website. Nothing unsigned is ever submitted to the cask or
   winget, whose placeholders stay. `CODE_SIGNED` in `app/src/main/build-info.ts` stays `false`.
2. **Published only from a tagged, clean commit.** The tag is `app-v<version>`, the convention the cask
   already uses, matching `app/package.json`'s `version` — never `v<version>`, which
   `.github/workflows/release.yml` (`tags: ["v*.*.*"]`) treats as a framework release.
   `npm run dist:beta` runs `app/scripts/release-guard.mjs` first and refuses to build unless HEAD
   carries exactly that tag and the working tree is clean, so a publishable build cannot come from an
   untagged or edited tree by accident. `dist:all` stays unguarded for test builds.
3. **Digests ship with the installers.** `dist:all` ends by writing `release/SHA256SUMS.txt`
   (`app/scripts/checksums.mjs`, GNU `sha256sum` format). The installer list lives once, in
   `app/scripts/release-artifacts.mjs`, so the zip and the digests cannot disagree about what a release
   contains. The `-unsigned.zip` is for handing a build to a test machine and is never published.
4. **The release is immutable.** The repository's GitHub immutable releases setting is on before the
   first publish, so an asset cannot be deleted and re-uploaded under the same name after users have
   checked its digest.
5. **The download page carries the user-facing text in `app/README.md` § Direct-download beta**,
   every point of it: beta and unsigned; the CLI is required and how to install it per platform; the
   checksum is checked first and a mismatch means delete and stop; Gatekeeper and SmartScreen steps
   that apply only to this verified file; no auto-update, and where security fixes are announced.
6. **The no-CLI screen tells the truth during the beta.** No Homebrew formula is published, so the
   macOS remedy in `app/src/cli/resolve.ts` gives the from-a-clone install instead of a
   `brew install` line that cannot work today.

**When it ends.** The first signed, notarised `.dmg` replaces the beta on macOS, and the first signed
Windows installer replaces it on Windows: the download then serves the signed artifact or points at
the channel, and this ADR's conditions stop applying to that platform. When both have happened, this
ADR is Superseded.

## Rationale

The beta's purpose is to put the app in front of real machines while signing is unavailable, without
weakening the two channels that will outlive it. Every condition above is either enforced by a script
(the tag and clean-tree guard, the shared installer list, the digests) or by a repository setting
(immutable releases); only the download-page text depends on someone copying it.

## Alternatives Considered

### Wait for signing
- **Pros**: no unsigned binary reaches anyone; no user is taught to click past an OS warning.
- **Cons**: the date depends on account-level credentials with no schedule, and the app's real-world
  assumptions stay untested until then.
- **Why rejected**: the cost of waiting grows with every app change nobody else has run.

### ADR-0011's rejected "Own installer only (.exe/.msi + PowerShell script)"
ADR-0011 rejected this for "a private update channel to maintain and much worse discovery". The beta is
not that alternative: it runs **beside** the two channels rather than instead of them, it has an end
condition, and it has **no** update channel at all — so there is nothing private to maintain. Discovery
is worse, which is acceptable for a beta that is meant to reach few people.

### Sign `SHA256SUMS.txt` with minisign, GPG or Sigstore
- **Pros**: authorship evidence that does not depend on the GitHub account that hosts the files.
- **Cons**: a key and a key-distribution story that do not exist; users would need a tool most do not
  have.
- **Why rejected for now**: build provenance from a tag-triggered macOS Actions job
  (`actions/attest-build-provenance`, verified with `gh attestation verify`) gives the same kind of
  evidence with no key to manage. It is the recorded next step, not part of this decision.

## Consequences

### Positive
- The app reaches users, and ADR-0015 § 5's resolution order is exercised outside the maintainer's
  machine — on macOS at least; see the CLI risk below for Windows.
- The digests, the guard and immutable releases give integrity and a reproducible "which commit was
  this" without any signing credential.

### Negative
- Users are asked to approve an app the OS could not verify.
- Every beta user upgrades by hand.

### Neutral
- The cask and winget manifests are untouched, and still placeholders.

## Risks

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **Digests prove integrity, not authorship.** `SHA256SUMS.txt` sits beside the installers, so whoever can replace an installer can replace it too: a compromised GitHub account or token, or a compromised build Mac, which produces the installer and its matching digest in one step. Repeating the digests in the release notes adds nothing — the same account edits both. | Immutable releases stop a later swap of a published asset. The guard ties a build to a tagged, clean commit. | Nothing independent of the GitHub account and the build host vouches for the files. Build provenance from Actions (see Alternatives) is the next step that would; signing is the one that closes it. |
| **Users learn to click past the OS.** "Open Anyway", `xattr -dr com.apple.quarantine` and SmartScreen's "Run anyway" are the exact steps fake-app and infostealer campaigns script. A user who learns them here repeats them elsewhere, and removing quarantine means Gatekeeper never checks that bundle again. | The download text makes a passing checksum the gate for every step, prefers "Open Anyway" over `xattr`, names the canonical download URL, and says never to run these steps because another site or app asks. | Wording, not a mechanism. Only signing removes the prompts. |
| **Electron fuses and the install location are not controls here.** `enableEmbeddedAsarIntegrityValidation` and `onlyLoadAppFromAsar` assume a signature that does not exist: an ad-hoc-signed bundle can be modified and re-signed ad hoc, and the unsigned NSIS install lives in a per-user folder any user-level process can write. | None in this ADR; stated so nobody counts them. | Unchanged until signing. |
| **No auto-update, so old betas stay in use.** A beta user does not learn about a fix, and an old app keeps running against a store that `devteam update` moves forward. | ADR-0015 § 6: the app degrades rather than writing a store shape it does not understand (ADR-0014's write gate). The download text tells users to watch the repository's Releases and Security Advisories. | Depends on the user watching. The store side is covered only while every write action stays behind the gate. |
| **No published CLI channel.** The app does nothing without `devteam`, and no formula or winget package exists. On macOS the from-a-clone install puts it in `/usr/local/bin`, a location the app searches. On Windows the app finds it only through `DEVTEAM_CLI_PATH` or `cliPath`, with Python 3 on PATH. | The download text gives both installs step by step, and the no-CLI screen says the same thing (decision 6). | On Windows the beta exercises only the manual-path step of ADR-0015 § 5, not the channel lookup. |

> **Amended by ADR-0028 (2026-10-02) — the CLI has a channel.** The Risks row "No published CLI
> channel" is addressed on both platforms: on Windows the no-CLI screen's **Install the CLI** action
> downloads the newest CLI installer from the project's releases, checks it against that release's
> `SHA256SUMS.txt` and runs it; on macOS the remedy gives `scripts/install-cli.sh`, which installs
> into `~/.local/bin`, a directory the app now searches. Decision 6's rule — the no-CLI screen names
> no command that cannot work — still holds: neither a `brew install` nor a `winget install` line is
> shown until those channels are published. Both installers work only from the first release that
> contains the CLI; every earlier tag predates it.

> **Note (2026-10-02) — signing is wired and gated on credentials; the status stays Accepted.**
> `app/electron-builder.yml` no longer disables signing: electron-builder signs and notarises
> macOS (`CSC_LINK`/`CSC_KEY_PASSWORD` plus `APPLE_ID`/`APPLE_APP_SPECIFIC_PASSWORD`/`APPLE_TEAM_ID`
> or an API key) and signs the Windows installers (`WIN_CSC_LINK`/`WIN_CSC_KEY_PASSWORD`) only when
> those variables exist, and builds exactly the unsigned beta described above when they do not.
> `app/build/after-build.cjs` inspects the artifact (`codesign`, `stapler`, Authenticode) and fails
> the build when credentials were supplied but the result does not verify; it prints the UNSIGNED
> banner whenever credentials were absent. An `app-v*` tag in `.github/workflows/release.yml` builds
> both platforms, verifies the dmg with `stapler validate` and `spctl`, writes `SHA256SUMS.txt`, and
> publishes the release (a prerelease unless both platforms verified). Only a verified platform
> renders its Homebrew cask or winget manifests, and only as workflow artifacts. `CODE_SIGNED` stays
> `false` in the repository; the credentialed CI build flips it in its own working copy. **Nothing
> here has run against a real Apple or Authenticode credential**, no cask or winget manifest is
> published, and this ADR's conditions, including decision 1's "nothing unsigned goes to the cask or
> winget", stay in force until a verified signed release has actually shipped. Operator steps:
> `packaging/README.md` § What is left for the maintainer.
