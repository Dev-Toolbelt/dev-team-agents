# devteam-app.rb — Homebrew cask for the dev-team-agents desktop app (ADR-0011).
#
# ═══════════════════════════════════════════════════════════════════════════
# UNRELEASED. The app now EXISTS — `app/` holds the Electron client decided by
# ADR-0015, and `npm run dist:mac` is configured to produce exactly what the
# stanzas below name: a universal `dev-team-agents.app` inside
# `dev-team-agents-<version>.dmg`. A maintainer has run it locally and it
# built; nothing in the tree is that artifact (`app/.gitignore` excludes
# `release/`) and no CI job produces one. What does not exist is a
# **signed, notarised** artifact or a real version: `app/electron-builder.yml`
# sets `mac.identity: null` and `mac.notarize: false`, so every build is
# unsigned, announced as such by `app/build/after-build.cjs`, and would be
# rejected by `brew audit --cask` on sight. Do not publish this cask, and do
# not treat its presence — or the existence of a local build — as evidence the
# app is installable by anyone.
# ═══════════════════════════════════════════════════════════════════════════
#
# ── PLACEHOLDER VALUES — none of these are real, none imply a release ───────
#   version  "0.0.0-unreleased" — an explicit non-version so it cannot be
#            mistaken for "the first release is 0.0.0". Set to the app's
#            actual tag (e.g. "app-v1.0.0", per the release workflow's
#            `app-v*` tag convention — see packaging/README.md) when a build
#            first ships.
#   sha256   the literal string "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET" — there
#            is no *released* .dmg to hash. A real cask computes this from the
#            actual notarised artifact, the same way the CLI formula's sha256
#            is computed by .github/workflows/release.yml, never hand-written.
#            An unsigned local build is not that artifact and its digest must
#            never be pasted here.
#   url      shaped like the artifact the app build *will* produce (a signed,
#            notarised universal .dmg attached to a GitHub Release), but the
#            release referenced does not exist — this URL 404s today.
#
# ── THIS `version` AND `app/package.json`'s ARE ONE VALUE, NOT TWO ──────────
# `app/electron-builder.yml` sets `dmg.artifactName: ${productName}-${version}.dmg`,
# so the dmg filename is a function of **`app/package.json`'s `version`**, while
# the `url` below builds the same filename from **this cask's `version`**. The
# two must be the same string at release time or the cask downloads a filename
# that was never produced.
#
# Which one is authoritative: **neither file. The git tag is.**
# `packaging/README.md` § Version source of truth already rules that "if a
# future change needs a version *inside* a file (for example, for the desktop
# app's own `package.json`), that value must derive from the git tag at build
# time, not be maintained by hand alongside it." So the release path is:
# `app-vX.Y.Z` is pushed -> the build stamps `app/package.json`'s `version`
# from the tag -> the dmg is named from that -> this cask's `version` is set to
# the same string, and its sha256 to the digest of that artifact.
#
# The two values therefore **disagree today on purpose** and must not be
# reconciled by hand: `app/package.json` says `0.0.0`, the unstamped value a
# private, unpublished package carries, and this cask says `0.0.0-unreleased`,
# a string that is not a version at all. Editing either one to match the other
# would produce a matching pair that still describes no artifact, and would
# retire the signal that no stamping step exists yet. There is no such step:
# nothing in `.github/workflows/release.yml` builds the app, and
# `.github/scripts/ci/05-app.sh` deliberately never runs `dist:mac`.
cask "devteam-app" do
  version "0.0.0-unreleased"
  sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"

  url "https://github.com/Dev-Toolbelt/dev-team-agents/releases/download/app-v#{version}/dev-team-agents-#{version}.dmg"
  name "dev-team-agents"
  desc "Desktop client for the dev-team-agents multi-agent development harness"
  homepage "https://github.com/Dev-Toolbelt/dev-team-agents"

  # MEASURED against the build, which is what this comment used to ask for.
  # `app/node_modules/electron/dist/Electron.app/Contents/Info.plist` declares
  # `LSMinimumSystemVersion` **13.0** for the pinned Electron (44.5.1), so
  # Electron 44 does not launch on Monterey or older; `app/electron-builder.yml`
  # sets `mac.minimumSystemVersion: '13.0'` to match. The previous
  # `">= :big_sur"` was a guess and it was wrong in the dangerous direction —
  # it licenses `brew install` on a system where the app cannot start, which
  # the user experiences as the app being broken rather than as unsupported.
  #
  # **This floor moves with every Electron major and is therefore a per-release
  # check, not a one-time edit.** Re-read `LSMinimumSystemVersion` from the
  # Electron in `app/node_modules` after every Electron major bump and change
  # both this line and `mac.minimumSystemVersion` together. Nothing enforces
  # the pair: `.github/scripts/ci/04-packaging.sh` only runs `ruby -c` on this
  # file, and `05-app.sh` never reads the cask.
  depends_on macos: ">= :ventura"

  # The CLI is not an optional companion, it is what this app *is*. ADR-0011:
  # "The app is a client of the CLI. Every action in the UI invokes
  # `devteam <command> --json` … No bind rule, no preference merge, no credential
  # resolution is reimplemented in TypeScript." An app installed without a
  # `devteam` on PATH has no way to do anything at all.
  #
  # An architecture review of M4.1 found this line missing and named the failure it
  # lets through: with the cask and the formula as independent installs, nothing
  # decides which `devteam` the app invokes, so an older CLI can end up writing a
  # newer store — which is the exact case `devteam compat` exists to detect and the
  # one nothing was preventing. The dependency makes "which CLI" answerable; the
  # app must still call `devteam compat` before it writes, because a user can
  # upgrade the store from a terminal without touching the app.
  depends_on formula: "devteam"

  app "dev-team-agents.app"

  # Per ADR-0011: "macOS artifacts are signed and notarised." `brew audit
  # --cask` (unrun here, see packaging/README.md) verifies the codesign and
  # notarisation ticket at install time against Apple's Developer ID —
  # neither exists yet, so that check cannot pass and has not been attempted.

  # Deliberately does NOT zap `~/Library/Application Support/dev-team-agents`
  # or `~/Library/Caches/dev-team-agents` — per ADR-0011 and CLAUDE-md/cli.md
  # those are the CLI's core/data store, shared with the app ("the app is a
  # client of the CLI... no bind rule, no preference merge, no credential
  # resolution is reimplemented"). Zapping the app must not delete a store the
  # CLI (installed separately, via the `devteam` formula) still owns. Only the
  # app's own Electron chrome is listed here. The suffix `-app` is the
  # distinction: `app/src/main/index.ts` sets `userData` to `${appName}-app`,
  # which resolves to `~/Library/Application Support/dev-team-agents-app` on
  # macOS. That directory holds the app's settings and schema cache; the CLI's
  # store is at `~/Library/Application Support/dev-team-agents` (without the
  # suffix). The bundle id and product name are read from
  # `app/electron-builder.yml` — both are now enforced by
  # `.github/scripts/ci/05-app.sh` rather than edited in pairs by hand.
  zap trash: [
    "~/Library/Preferences/com.devtoolbelt.dev-team-agents-app.plist",
    "~/Library/Saved Application State/com.devtoolbelt.dev-team-agents-app.savedState",
    "~/Library/Application Support/dev-team-agents-app",
    "~/Library/Logs/dev-team-agents",
  ]
end
