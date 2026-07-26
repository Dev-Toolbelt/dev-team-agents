#!/usr/bin/env bash
# strip-tarball.sh — Single source of truth for the slim tarball strip rules
# applied by scripts/install.sh before placing files at .dev-team-agents/.
#
# Sourced by:
#   - scripts/install.sh                    (during normal tarball install)
#   - .github/scripts/ci/slim-bootstrap.sh  (the CI slim-shape contract test)
#
# Sourcing contract:
#   `apply_strip <extracted-root-absolute-or-relative-path>`
#       — removes dotfiles, repo-only scripts, and cross-CLI plumbing
#         (the slim Claude install footprint). Idempotent and silent on
#         already-stripped dirs/files.

apply_strip() {
  local extracted="$1"

  # KEEP_ROOT allowlist is enforced separately by install.sh. This function
  # only handles dotfiles, repo-only dirs, and explicit plumbing removal.

  rm -rf "$extracted/.claude"               # repo-level Claude config — not for user projects
  rm -rf "$extracted/.github"               # repo-level GitHub templates/CODEOWNERS — not for users
  rm -rf "$extracted/helpers"               # dev-only authoring tools — not for user projects
  rm -rf "$extracted/opencode"              # provider-plugin dir — fetched on demand via install-provider.sh
  rm -f  "$extracted/.gitignore"            # repo-level gitignore — not for user projects
  rm -f  "$extracted/scripts/install.sh"    # accessed via curl; never bundled in the package

  # Cross-CLI plumbing (opencode/Codex render engine and installer scripts)
  # is now INCLUDED in the slim Claude install so users can add Codex or
  # opencode support without network access. Run:
  #   .dev-team-agents/scripts/install-codex.sh    # add Codex CLI support
  #   .dev-team-agents/scripts/install-opencode.sh # add opencode support
  # These scripts are kept bundled despite being unused by Claude users
  # because the convenience of local (offline) provider install outweighs
  # the slimness gain from stripping them."
}