#!/usr/bin/env bash
# scripts/lib/python.sh — make `python3` mean a working Python 3.9+. Sourced, never run.
#
# The shipped scripts call `python3` (and gate on `command -v python3`) in ~110 places.
# Git Bash on Windows often has no `python3`, or only the Microsoft Store stub that
# exits 9009, while `python` or `py -3` work. Rather than rewriting every call site,
# this file defines an exported `python3` function that runs the resolved interpreter,
# so `command -v python3` and `python3 …` keep working in this shell and in every bash
# child (a dispatcher's sub-scripts, an installer's helpers).
#
# Resolution order: $DEVTEAM_PYTHON (the CLI passes its own sys.executable), python3,
# python, `py -3`; each must report Python >= 3.9. On macOS/Linux with a `python3` on
# PATH nothing is probed and nothing is defined, so behavior there is unchanged.
# The result is cached in DTA_PYTHON / DTA_PYTHON_FLAG (exported), so children skip
# the probe. Bash 3.2 compatible.

[ -n "${_DTA_PYTHON_SH:-}" ] && return 0
_DTA_PYTHON_SH=1

_dta_is_windows() {
    case "${DEVTEAM_PLATFORM:-}" in
        win*) return 0 ;;
        darwin*|linux*) return 1 ;;
    esac
    case "$(uname -s 2>/dev/null)" in
        MINGW*|MSYS*|CYGWIN*) return 0 ;;
    esac
    return 1
}

_dta_python_ok() {
    "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1
}

_dta_python_shim() {
    python3() {
        if [ -n "${DTA_PYTHON_FLAG:-}" ]; then
            command "$DTA_PYTHON" "$DTA_PYTHON_FLAG" "$@"
        else
            command "$DTA_PYTHON" "$@"
        fi
    }
    export -f python3
}

_dta_python_pick() {
    DTA_PYTHON="$1"
    DTA_PYTHON_FLAG="${2:-}"
    export DTA_PYTHON DTA_PYTHON_FLAG
    # A real `python3` needs no shim; anything else is reached through one.
    if [ "$DTA_PYTHON" != "python3" ] || [ -n "$DTA_PYTHON_FLAG" ]; then
        _dta_python_shim
    fi
}

dta_python_resolve() {
    if [ -n "${DTA_PYTHON:-}" ]; then
        # Resolved by a parent. Re-arm the shim in case the exported function was
        # dropped on the way (a sanitized environment keeps plain variables only).
        if [ "$DTA_PYTHON" != "python3" ] || [ -n "${DTA_PYTHON_FLAG:-}" ]; then
            _dta_python_shim
        fi
        return 0
    fi
    if [ -z "${DEVTEAM_PYTHON:-}" ] && ! _dta_is_windows && command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    local explicit="${DEVTEAM_PYTHON:-}"
    if [ -n "$explicit" ]; then
        case "$explicit" in
            [A-Za-z]:*) command -v cygpath >/dev/null 2>&1 && explicit="$(cygpath -u "$explicit")" ;;
        esac
        if _dta_python_ok "$explicit"; then
            _dta_python_pick "$explicit"
            return 0
        fi
    fi
    if command -v python3 >/dev/null 2>&1 && _dta_python_ok python3; then
        _dta_python_pick python3
        return 0
    fi
    if command -v python >/dev/null 2>&1 && _dta_python_ok python; then
        _dta_python_pick python
        return 0
    fi
    if command -v py >/dev/null 2>&1 && _dta_python_ok py -3; then
        _dta_python_pick py -3
        return 0
    fi
    return 1
}

dta_python_resolve || true
