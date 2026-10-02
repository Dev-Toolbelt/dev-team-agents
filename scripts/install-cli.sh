#!/usr/bin/env bash
# install-cli.sh — install the `devteam` CLI on macOS or Linux without Homebrew (ADR-0028).
#
#   curl -fsSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-cli.sh | bash
#   bash scripts/install-cli.sh --from .          # from a clone, no download
#   bash scripts/install-cli.sh --version v3.0.0  # a specific release
#
# Installs, for the current user only (no sudo):
#   ~/.local/share/devteam/scripts/{cli,lib/devteam}   the CLI, laid out as the Homebrew formula does
#   ~/.local/bin/devteam                               a launcher running it with the verified Python
# then installs that release's framework into the store (`devteam store install`). An
# already-installed version is left alone and an existing `current` is never moved. Safe to
# re-run — which is also how the CLI itself is upgraded: `devteam update` moves the
# framework, not the CLI. It replaces only the CLI directory it owns, never the store.
#
# Dependencies: Python 3.9+ and git. On macOS both come with the Command Line Tools; when
# they are missing this starts their installer and asks you to re-run.
#
# Environment: DEVTEAM_CLI_HOME (default ~/.local/share/devteam), DEVTEAM_BIN_DIR (default
# ~/.local/bin).
#
# The whole script is one function called on the last line, so a download cut short by the
# network runs nothing rather than half of it.

set -euo pipefail

main() {
    local owner="Dev-Toolbelt" repo="dev-team-agents"
    # `devteam`'s exit code for "already installed" (errors.EXIT_CONFLICT).
    local exit_conflict=4
    local source="" version=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --from) source="${2:?--from needs a directory}"; shift 2 ;;
            --version) version="${2:?--version needs a tag}"; shift 2 ;;
            -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" 2>/dev/null | sed 's/^# \{0,1\}//'; return 0 ;;
            *) echo "install-cli: unknown argument: $1" >&2; return 2 ;;
        esac
    done

    # ── Dependencies ──────────────────────────────────────────────────────────
    if [ "$(uname -s)" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
        say "The Command Line Tools (Python 3 and git) are not installed. Starting their installer..."
        xcode-select --install >/dev/null 2>&1 || true
        die "finish the Command Line Tools installation in the window that opened, then run this again."
    fi

    local python
    python="$(command -v python3 || true)"
    if [ -z "$python" ] || ! python_ok "$python"; then
        die "Python 3.9+ is required and was not found as python3. Install it (macOS: xcode-select --install; Linux: your package manager), then run this again."
    fi
    command -v git >/dev/null 2>&1 || die "git is required — the hooks run it. Install it, then run this again."

    # Absolute, so the launcher never names a path relative to wherever this ran.
    mkdir -p "${DEVTEAM_CLI_HOME:-$HOME/.local/share/devteam}" "${DEVTEAM_BIN_DIR:-$HOME/.local/bin}"
    local cli_home bin_dir
    cli_home="$(cd "${DEVTEAM_CLI_HOME:-$HOME/.local/share/devteam}" && pwd -P)"
    bin_dir="$(cd "${DEVTEAM_BIN_DIR:-$HOME/.local/bin}" && pwd -P)"

    # ── Source tree ───────────────────────────────────────────────────────────
    WORK="$(mktemp -d "${TMPDIR:-/tmp}/devteam-cli.XXXXXX")"
    trap 'rm -rf "$WORK"' EXIT

    if [ -z "$source" ]; then
        command -v curl >/dev/null 2>&1 || die "curl is required to download a release."
        if [ -z "$version" ]; then
            version="$(curl -fsSL "https://api.github.com/repos/$owner/$repo/releases?per_page=50" | newest_release "$python" || true)"
            [ -n "$version" ] || die "could not find a vX.Y.Z release on GitHub. Pass --version, or --from a clone."
        fi
        say "Downloading $version"
        curl -fsSL -o "$WORK/src.tar.gz" "https://github.com/$owner/$repo/archive/refs/tags/$version.tar.gz" \
            || die "could not download $version."
        mkdir "$WORK/src"
        tar -xzf "$WORK/src.tar.gz" -C "$WORK/src" --strip-components 1
        source="$WORK/src"
    fi

    if [ ! -f "$source/scripts/cli/devteam" ] || [ ! -d "$source/scripts/lib/devteam" ]; then
        [ -n "$version" ] && die "release $version predates the devteam CLI, so there is nothing to install from it. Install from a clone of the main branch: bash scripts/install-cli.sh --from ."
        die "$source is not a dev-team-agents tree (no scripts/cli/devteam)."
    fi

    # ── The CLI ───────────────────────────────────────────────────────────────
    # Staged in a fresh directory beside the target and swapped in, so a failed copy never
    # leaves half a CLI and two concurrent runs never share a staging directory.
    local stage
    stage="$(mktemp -d "$cli_home/.scripts.XXXXXX")"
    mkdir -p "$stage/cli" "$stage/lib"
    cp "$source/scripts/cli/devteam" "$stage/cli/devteam"
    cp -R "$source/scripts/lib/devteam" "$stage/lib/devteam"
    find "$stage" -name '__pycache__' -type d -prune -exec rm -rf {} +
    rm -rf "$cli_home/scripts"
    mv "$stage" "$cli_home/scripts"

    # A launcher, not a symlink to a script with a rewritten shebang: it names the verified
    # interpreter by absolute path — a GUI app starts the CLI with a minimal PATH, where
    # `env python3` could find another Python — and, unlike a shebang, it survives a space
    # in either path.
    local launcher="$bin_dir/devteam"
    rm -f "$launcher"
    printf '#!/bin/sh\nexec %s %s "$@"\n' "$(shell_quote "$python")" "$(shell_quote "$cli_home/scripts/cli/devteam")" > "$launcher"
    chmod 755 "$launcher"
    say "Installed $launcher"

    # ── The framework ─────────────────────────────────────────────────────────
    local output status
    set +e
    output="$("$launcher" store install --from "$source" 2>&1)"
    status=$?
    set -e
    case "$status" in
        0) say "$output" ;;
        "$exit_conflict") say "That framework version is already in the store; left as it is." ;;
        *) printf '%s\n' "$output" >&2; die "devteam store install failed (exit $status)." ;;
    esac
    hint_current "$launcher" "$python" "$source"

    case ":$PATH:" in
        *":$bin_dir:"*) ;;
        *) say "Add $bin_dir to your PATH to run devteam from a terminal (the desktop app also searches ~/.local/bin):"
           # shellcheck disable=SC2016  # `$PATH` is meant literally: the user's shell expands it.
           printf '    echo '\''export PATH="%s:$PATH"'\'' >> ~/.zshrc\n' "$bin_dir" ;;
    esac
    say "Done. Run: devteam doctor"
}

say() { printf '→ %s\n' "$*"; }
die() { printf 'install-cli: %s\n' "$*" >&2; exit 1; }

python_ok() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1
}

# Single-quoted for /bin/sh, with any single quote inside escaped.
shell_quote() {
    printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

# The newest `vX.Y.Z` release by version, from the releases listing on stdin. Releases only —
# a bare tag has no release, and anyone who can push a tag would otherwise choose what this
# installs. Not `releases/latest`: `app-v*` releases share this repository (ADR-0027).
newest_release() {
    "$1" -c '
import json, re, sys
tags = [r.get("tag_name", "") for r in json.load(sys.stdin) if not r.get("draft") and not r.get("prerelease")]
tags = [t for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
print(max(tags, key=lambda t: tuple(int(p) for p in t[1:].split("."))) if tags else "")
'
}

# An install never moves `current`; say how, when the store's current is not this release.
hint_current() {
    local launcher="$1" python="$2" source="$3" installed current
    installed="$(PYTHONPATH="$source/scripts/lib" "$python" -c 'import sys; from devteam.versions import version_from_tree; print(version_from_tree(sys.argv[1]) or "")' "$source" 2>/dev/null || true)"
    current="$("$launcher" store list --json 2>/dev/null | "$python" -c 'import json, sys; print(json.load(sys.stdin).get("current") or "")' 2>/dev/null || true)"
    if [ -n "$installed" ] && [ -n "$current" ] && [ "$installed" != "$current" ]; then
        say "The store's current framework is $current. To use $installed: devteam store use $installed && devteam sync --all"
    fi
}

main "$@"
