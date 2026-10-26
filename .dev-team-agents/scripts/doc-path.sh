#!/usr/bin/env bash
# Prints where a fact category's document lives in this project (ADR-0045), from
# the docs layout map scripts/lib/doc-layouts.json and project.json `docs_layout`.
# Run from the project root.
#
# Usage: bash .dev-team-agents/scripts/doc-path.sh <key>       → <write-root>/<path>, or an
#                                                                 empty line when the layout
#                                                                 has no such doc
#        bash .dev-team-agents/scripts/doc-path.sh --layout    → development | gated
#        bash .dev-team-agents/scripts/doc-path.sh --readonly  → read-only paths, one per line
#        bash .dev-team-agents/scripts/doc-path.sh --writable  → writable owner-doc paths, one per line
# Exit: 0 answered, 2 usage error or unknown key. Without Python it answers the
# `development` column under `docs` (lib/docs-root.sh).
set -euo pipefail

# shellcheck source=scripts/lib/docs-root.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/docs-root.sh"

case "${1:-}" in
    "" | -h | --help)
        echo "Usage: $0 <key> | --layout | --readonly | --writable" >&2
        exit 2
        ;;
    --layout) devteam_docs_layout "$PWD" ;;
    --readonly) devteam_doc_readonly "$PWD" ;;
    --writable) devteam_doc_writable "$PWD" ;;
    -*)
        echo "Usage: $0 <key> | --layout | --readonly | --writable" >&2
        exit 2
        ;;
    *)
        rc=0
        devteam_doc_path "$PWD" "$1" || rc=$?
        if [ "$rc" -ne 0 ]; then
            printf 'doc-path.sh: unknown doc key: %s\n' "$(printf '%s' "$1" | LC_ALL=C tr -d '\000-\037\177' | cut -c1-80)" >&2
            exit 2
        fi
        ;;
esac
