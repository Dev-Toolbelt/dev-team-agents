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

  # Slim Claude-runtime distribution: cross-CLI plumbing (opencode/Codex
  # render engine and their installer scripts) is NOT bundled in the Claude
  # install. Users who want opencode or Codex CLI support curl-pipe
  # install-provider.sh on demand, which fetches just these files fresh from
  # GitHub and runs the matching installer. See docs/providers.md.
  rm -f  "$extracted/scripts/install-opencode.sh"
  rm -f  "$extracted/scripts/install-codex.sh"
  rm -f  "$extracted/scripts/render-provider.sh"
  rm -f  "$extracted/scripts/lib/render_provider.py"
  rm -f  "$extracted/scripts/lib/tiers.json"
  rm -f  "$extracted/scripts/lib/tool-map.json"
  rm -f  "$extracted/scripts/lib/command-map.json"
  rm -f  "$extracted/scripts/lib/commands.json"
}