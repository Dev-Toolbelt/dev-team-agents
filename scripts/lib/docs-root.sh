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

# The docs layout map (ADR-0045): lib/doc-layouts.json, read by lib/docs_root.py.
# Without project.json the answer is fixed — the `development` column under `docs` —
# so the interpreter is skipped; without Python the same plain defaults are printed.
# _devteam_doc_rel mirrors the map's `development` column; tests/test_doc_layouts.py
# fails when the two drift.
_devteam_doc_rel() {
    case "$1" in
        architecture) printf '%s' "development/architecture.md" ;;
        tech-stack) printf '%s' "development/tech-stack.md" ;;
        code-standards) printf '%s' "development/code-standards.md" ;;
        reuse-guidelines) printf '%s' "development/reuse-guidelines.md" ;;
        data-model) printf '%s' "development/database.md" ;;
        api-contracts) printf '%s' "development/api-contracts.md" ;;
        adr) printf '%s' "development/adrs/" ;;
        conformance-report) printf '%s' "development/conformance-report.md" ;;
        design-system) printf '%s' "design/design-system.md" ;;
        specs) printf '%s' "specs/" ;;
        testing) printf '%s' "tests/testing-strategy.md" ;;
        backlog-index) printf '%s' "backlog/sprints/sprints.md" ;;
        backlog-readme) printf '%s' "backlog/README.md" ;;
        dod) printf '%s' "backlog/dod.md" ;;
        overview) printf '%s' "backlog/" ;;
        sprints) printf '%s' "backlog/sprints/" ;;
        project) printf '%s' "project.md" ;;
        wiki) printf '%s' "wiki/" ;;
        infrastructure) printf '%s' "devops/infrastructure.md" ;;
        source|prd|glossary|nfr|trd|threat-model|design-tokens|design-prototypes) ;;
        design-screens|design-flows|evals|process) ;;
        *) return 2 ;;
    esac
}

# _devteam_doc_query <project-root> <docs_root.py args…> — the helper's answer, or
# exit 3 when it cannot be asked (no project.json, no Python, no helper or map).
_devteam_doc_query() {
    local lib root rc=0 out
    root="$1"
    shift
    lib="$(dirname "${BASH_SOURCE[0]}")"
    [ -f "$root/.dev-team-agents/project.json" ] && [ -f "$lib/docs_root.py" ] \
        && [ -f "$lib/doc-layouts.json" ] || return 3
    # shellcheck source=scripts/lib/python.sh
    if [ -f "$lib/python.sh" ]; then . "$lib/python.sh" 2>/dev/null || true; fi
    command -v python3 >/dev/null 2>&1 || return 3
    out="$(python3 -I "$lib/docs_root.py" "$@" "$root" 2>/dev/null)" || rc=$?
    case "$rc" in
        0) printf '%s\n' "$out" ;;
        2) return 2 ;;
        *) return 3 ;;
    esac
}

# devteam_doc_path <project-root> <key> — `<write-root>/<path>` for <key> under the
# project's layout, an empty line when the layout has no such doc; returns 2 on a
# key the map does not define.
devteam_doc_path() {
    local root key rc=0 rel
    root="${1:-$PWD}"
    key="${2:-}"
    _devteam_doc_query "$root" --path "$key" || rc=$?
    [ "$rc" -eq 0 ] && return 0
    [ "$rc" -eq 2 ] && return 2
    rel="$(_devteam_doc_rel "$key")" || return 2
    # Under the write root, not a literal `docs/`: the map may be missing while Python and
    # docs_root.py are not, and context_paths[0] still holds (devteam_docs_root answers
    # `docs` itself when it cannot ask).
    if [ -n "$rel" ]; then printf '%s/%s\n' "$(devteam_docs_root "$root")" "$rel"; else printf '\n'; fi
}

# devteam_docs_layout <project-root> — `development` or `gated`.
devteam_docs_layout() {
    _devteam_doc_query "${1:-$PWD}" --layout || printf '%s\n' "development"
}

# devteam_doc_writable <project-root> — the layout's writable owner-doc paths, one per
# line; empty when Python or the map is missing (callers then keep their own default).
devteam_doc_writable() {
    _devteam_doc_query "${1:-$PWD}" --writable || true
}

# devteam_doc_readonly <project-root> — the layout's read-only paths, one per line
# (none in the `development` layout, which is also the fallback).
devteam_doc_readonly() {
    _devteam_doc_query "${1:-$PWD}" --readonly || true
}
