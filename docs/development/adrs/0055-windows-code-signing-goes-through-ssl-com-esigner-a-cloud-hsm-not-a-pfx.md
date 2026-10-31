# ADR-0055: Windows code signing goes through SSL.com eSigner, a cloud HSM, not a pfx

**Date:** 2026-10-31  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `app/build/sign-windows.cjs`, `app/build/after-build.cjs`, `app/electron-builder.yml`, `.github/scripts/release/install-codesigntool.sh`, `.github/workflows/release.yml`, `.github/workflows/windows-cli.yml`, `.github/workflows/windows-signing-sandbox.yml`

## Context

This ADR narrows [ADR-0027](0027-the-desktop-app-ships-an-unsigned-direct-download-beta-until-it-is-signed.md), implements [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md)'s Windows signing
bar ("the Windows installer is code-signed") and wires signing for the [ADR-0028](0028-the-devteam-cli-installs-with-its-dependencies-on-windows-and-macos.md) CLI
installer. ADR-0027's end condition stays; this decides how the signature is made.

The Windows signing path wired in `electron-builder.yml` and `release.yml` took a `.pfx`
(`WIN_CSC_LINK` / `WIN_CSC_KEY_PASSWORD`). Since the 2023 CA/B Forum rule, a newly issued
Authenticode certificate keeps its private key on hardware or in a cloud HSM and cannot be exported
to a `.pfx`, so that path could never be fed a certificate bought today.

The publisher is a Brazilian company. The options were weighed on cost per year and on whether a
release can be signed by CI with nobody at a keyboard:

| Option | Cost per year | Publisher shown | Unattended in CI |
|---|---|---|---|
| Azure Artifact Signing | ~US$ 120 | the company | yes — but organizations in Brazil are not eligible |
| SignPath Foundation | free | "SignPath Foundation" | yes, with a manual approval per release |
| Certum Open Source | ~€ 49 | an individual | no — SimplySign asks for an interactive OTP |
| OV certificate with a physical token | ~US$ 100–200 | the company | no — a Windows machine and a person per release |
| **SSL.com OV + eSigner** | ~US$ 310–370 (certificate + eSigner subscription) | the company | **yes** |

## Decision

1. **Windows executables are signed through SSL.com eSigner.** `app/build/sign-windows.cjs` sends
   each file to eSigner with SSL.com's CodeSignTool and signs it in place. It is electron-builder's
   `win.signtoolOptions.sign` hook for the app (its executable, uninstaller and installers) and a
   script for the CLI installers in `windows-cli.yml`.
2. **Four secrets, all or none:** `WIN_ESIGNER_USERNAME`, `WIN_ESIGNER_PASSWORD`,
   `WIN_ESIGNER_CREDENTIAL_ID`, `WIN_ESIGNER_TOTP_SECRET`. None → the build is unsigned, as before.
   Some → the build fails, in the workflows and in the hook: a mistyped secret must not ship an
   unsigned release.
   The `.pfx` path is removed: a `WIN_CSC_LINK` without eSigner credentials fails the build instead
   of being silently ignored. `CSC_LINK`, which electron-builder also falls back to for Windows, is
   left alone: on a Mac it is the macOS `.p12`, and the Windows half of `dist:all` stays unsigned.
3. **The credentials reach only the step that signs, and only builds that publish sign.** The app's
   JS build (`npm run build`) runs without them; electron-builder runs as a step of its own that
   holds them. `sign-windows.cjs` hashes the jar against its pin and rewrites CodeSignTool's config
   right before each signing, which reduces what a dependency script could change on disk. It does
   not remove it: see Negative. The CLI installers sign only when they will be attached to a release
   (a release call, or a dispatch from `main`); pull requests and rebuilds that attach nothing never
   sign and never see the secrets. The production secrets belong in the `esigner-production`
   environment, restricted to release tags, which both signing jobs use.
4. **sha256 only.** electron-builder's default second, sha1 signature is turned off: it would be a
   second billed signing per file and no supported Windows version needs it.
5. **CodeSignTool is pinned by version and SHA-256.** `install-codesigntool.sh` checks the zip
   before unpacking it; `sign-windows.cjs` checks the jar before every use and owns the production
   and sandbox endpoints.
6. **The sandbox proves the chain before anything is bought.** `windows-signing-sandbox.yml` is
   dispatch-only, reads SSL.com's published demo account from the `esigner-sandbox` environment as
   `WIN_ESIGNER_SANDBOX_*` (names of their own, so a missing environment secret can never fall back
   to the production repository secret), signs both sets of installers and checks a signature is present. A sandbox signature is never
   reported as signed: `after-build.cjs` records `signed-sandbox`, and the release workflow still
   requires `Get-AuthenticodeSignature` to report `Valid`.
7. **The certificate is bought when the Windows app is released for real,** not before: a code
   signing certificate is valid for at most 458 days, and until then the app ships as the ADR-0027
   unsigned beta.

## Consequences

### Positive
- Releases are signed by CI from a tag, with no machine or person in the loop, and in the
  company's name.
- The whole chain is exercised against the sandbox at no cost, so buying the certificate is the
  only step left.

### Negative
- About US$ 310–370 a year, part of it a monthly eSigner subscription billed by signature count.
  A release signs 12 files, measured in the sandbox run of 2026-10-31: per architecture the app's
  executable and `elevate.exe`, three NSIS uninstallers, three app installers and two CLI
  installers. The eSigner plan's monthly quota must cover that per release.
- A third party's tool (CodeSignTool, a Java jar) runs in the release job with the signing
  credentials. The pin limits it to one reviewed version.
- Everything that runs in the signing job is inside the trust boundary: electron-builder and the
  dependencies `npm ci` installed run in the step that holds the credentials, and a process an
  install script left running can read CodeSignTool's command line. The lockfile is part of what
  is trusted to sign.
- Keeping the TOTP secret as a CI secret removes eSigner's second factor: whoever holds the four
  secrets can sign anything in the company's name, unattended. Rotate the password and re-enroll
  the TOTP on any suspicion, and keep the secrets in the tag-restricted environment only.
- The certificate is renewed at least every 458 days, and the four secrets updated with it.

### Neutral
- Signing does not make SmartScreen silent on day one: an OV certificate builds reputation from
  downloads. The warning names the publisher instead of "unknown publisher".
- The CLI installer's uninstaller, written by the installer at install time, stays unsigned.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Azure Artifact Signing | Not available to organizations in Brazil |
| SignPath Foundation | Its program is for projects with no proprietary or commercial component; this product has licensed plans (ADR-0029), and the publisher shown would not be the company |
| Certum Open Source Code Signing | Issued to an individual for non-commercial software, and cannot sign unattended |
| OV certificate on a physical token | Needs a Windows machine and a person for every release; the saving does not pay for that |
| EV certificate | Costs more and, since 2024, no longer grants immediate SmartScreen reputation |
| Keeping the `.pfx` path beside eSigner | No certificate issued today can feed it, and a custom sign hook replaces electron-builder's signtool call for every file |
