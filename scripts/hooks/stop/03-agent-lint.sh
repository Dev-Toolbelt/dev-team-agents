#!/usr/bin/env bash
# Shim — runs agent frontmatter lint at the end of each session.
exec "$(dirname "${BASH_SOURCE[0]}")/../../agent-lint.sh" --quiet "$@"
