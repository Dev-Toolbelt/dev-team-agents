#!/usr/bin/env bash
# devteam_docs_root <project-root> — prints the project's docs write root, relative
# (the first `context_paths` entry; lib/docs_root.py holds the rule). Answers `docs`
# when Python or the helper is missing, so a caller never needs its own fallback.

devteam_docs_root() {
    local lib root out=""
    root="${1:-$PWD}"
    lib="$(dirname "${BASH_SOURCE[0]}")"
    # No project.json, no context_paths: skip the interpreter (this runs on every Stop).
    if [ -f "$root/.dev-team-agents/project.json" ] && [ -f "$lib/docs_root.py" ]; then
        # python.sh picks a 3.9+ interpreter (and the Windows launcher) where one exists.
        # shellcheck source=scripts/lib/python.sh
        if [ -f "$lib/python.sh" ]; then . "$lib/python.sh" 2>/dev/null || true; fi
        if command -v python3 >/dev/null 2>&1; then
            out="$(python3 -I "$lib/docs_root.py" "$root" 2>/dev/null || true)"
        fi
    fi
    printf '%s\n' "${out:-docs}"
}

# devteam_regex_escape <text> — <text> as a literal for grep -E.
devteam_regex_escape() {
    printf '%s' "$1" | sed 's/[][\.*^$+?(){}|]/\\&/g'
}
