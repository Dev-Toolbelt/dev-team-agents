#!/bin/bash
# render-provider.sh — Render the dev-team-agents canonical source into a
# provider-specific output tree.
#
# Usage:
#   scripts/render-provider.sh --provider <claude|opencode|codex> \
#       --source-dir <repo-root> --target-dir <staging-dir> \
#       [--agents-only] [--commands-only] [--dry-run]
#
# Output lands under:
#   <target>/.claude/{agents/dev-team,commands/devteam}/*.md   (provider=claude)
#   <target>/.opencode/agents/*.md + <target>/.opencode/commands.snippet.jsonc (provider=opencode)
#   <target>/.codex/agents/*.toml + <target>/.codex/prompts/devteam-*.md        (provider=codex)
#
# Fails fast (exit 1) on unknown provider, unknown tier, missing tiers.json
# column, or missing `tier:` key in an agent's frontmatter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$SCRIPT_DIR/lib/render_provider.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "render-provider: ERROR: python3 is required but not found on PATH." >&2
  exit 1
fi

exec python3 "$PY" "$@"