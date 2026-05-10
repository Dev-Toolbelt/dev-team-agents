#!/usr/bin/env bash
# Shim — delegates to the canonical orphan-skill-scan at the end of each session.
exec "$(dirname "${BASH_SOURCE[0]}")/../../orphan-skill-scan.sh" --quiet "$@"
