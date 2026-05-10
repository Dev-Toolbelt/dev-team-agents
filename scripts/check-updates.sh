#!/usr/bin/env bash
# Shim — delegates to the canonical update-check hook.
exec "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh" "$@"
