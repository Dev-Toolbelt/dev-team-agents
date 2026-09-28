# devteam-app.rb — Homebrew cask for the dev-team-agents desktop app (ADR-0011).
#
# ═══════════════════════════════════════════════════════════════════════════
# UNRELEASED AND UNVERIFIED. The Electron app described in ADR-0011 and
# ADR-0011's "app" column does not exist in this repository yet — there is no
# `app/` directory, no build pipeline, and no signed artifact. This file is
# groundwork only: it records the shape a cask for that app WILL need once the
# app ships, so the distribution story in the ADR has a concrete draft instead
# of only prose. Every value below is a placeholder. Do not publish this cask,
# and do not treat its presence as evidence the app is installable.
# ═══════════════════════════════════════════════════════════════════════════
#
# ── PLACEHOLDER VALUES — none of these are real, none imply a release ───────
#   version  "0.0.0-unreleased" — an explicit non-version so it cannot be
#            mistaken for "the first release is 0.0.0". Set to the app's
#            actual tag (e.g. "app-v1.0.0", per the release workflow's
#            `app-v*` tag convention — see packaging/README.md) when a build
#            first ships.
#   sha256   the literal string "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET" — there
#            is no .dmg to hash. A real cask computes this from the actual
#            notarised artifact, the same way the CLI formula's sha256 is
#            computed by .github/workflows/release.yml, never hand-written.
#   url      shaped like the artifact the app build *will* produce (a signed,
#            notarised universal .dmg attached to a GitHub Release), but the
#            release referenced does not exist — this URL 404s today.
cask "devteam-app" do
  version "0.0.0-unreleased"
  sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"

  url "https://github.com/Dev-Toolbelt/dev-team-agents/releases/download/app-v#{version}/dev-team-agents-#{version}.dmg"
  name "dev-team-agents"
  desc "Desktop client for the dev-team-agents multi-agent development harness"
  homepage "https://github.com/Dev-Toolbelt/dev-team-agents"

  # Placeholder floor — confirm against the app's actual Electron/Info.plist
  # minimum once the build exists; this is a guess, not a measured value.
  depends_on macos: ">= :big_sur"

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
  # app's own Electron chrome is listed here, under a placeholder bundle id —
  # confirm the real id from the app's Info.plist once it exists.
  zap trash: [
    "~/Library/Preferences/com.devtoolbelt.dev-team-agents-app.plist",
    "~/Library/Saved Application State/com.devtoolbelt.dev-team-agents-app.savedState",
    "~/Library/Logs/dev-team-agents-app",
  ]
end
