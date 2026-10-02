#!/usr/bin/env bash
# install-cli.sh — install the `devteam` CLI on macOS or Linux without Homebrew (ADR-0028).
#
#   curl -fsSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-cli.sh | bash
#   bash scripts/install-cli.sh --from .          # from a clone, no download
#   bash scripts/install-cli.sh --version v2.48.0 # a specific release
#
# Installs, for the current user only (no sudo):
#   ~/.local/share/devteam/scripts/{cli,lib/devteam}   the CLI, laid out as the Homebrew formula does
#   ~/.local/bin/devteam                               a symlink to it
# then installs that release's framework into the store (`devteam store install`). An
# already-installed version is left alone and an existing `current` is never moved. Safe to
# re-run: it replaces only the CLI directory it owns, never the store.
#
# Dependencies: Python 3.9+ and git. On macOS both come with the Command Line Tools; when
# they are missing this starts their installer and asks you to re-run.
#
# Environment: DEVTEAM_CLI_HOME (default ~/.local/share/devteam), DEVTEAM_BIN_DIR (default
# ~/.local/bin).

set -euo pipefail

OWNER="Dev-Toolbelt"
REPO="dev-team-agents"
CLI_HOME="${DEVTEAM_CLI_HOME:-$HOME/.local/share/devteam}"
BIN_DIR="${DEVTEAM_BIN_DIR:-$HOME/.local/bin}"
# `devteam`'s exit code for "already installed" (errors.EXIT_CONFLICT).
EXIT_CONFLICT=4

SOURCE=""
VERSION=""

usage() {
    sed -n '2,20p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --from) SOURCE="${2:?--from needs a directory}"; shift 2 ;;
        --version) VERSION="${2:?--version needs a tag}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "install-cli: unknown argument: $1" >&2; exit 2 ;;
    esac
done

say() { printf '→ %s\n' "$*"; }
die() { printf 'install-cli: %s\n' "$*" >&2; exit 1; }

# ── Dependencies ──────────────────────────────────────────────────────────────
python_ok() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1
}

if [ "$(uname -s)" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
    say "The Command Line Tools (Python 3 and git) are not installed. Starting their installer..."
    xcode-select --install >/dev/null 2>&1 || true
    die "finish the Command Line Tools installation in the window that opened, then run this again."
fi

PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ] || ! python_ok "$PYTHON"; then
    die "Python 3.9+ is required and was not found as python3. Install it (macOS: xcode-select --install; Linux: your package manager), then run this again."
fi
command -v git >/dev/null 2>&1 \
    || die "git is required — the hooks run it. Install it, then run this again."

# ── Source tree ───────────────────────────────────────────────────────────────
WORK="$(mktemp -d "${TMPDIR:-/tmp}/devteam-cli.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

if [ -z "$SOURCE" ]; then
    command -v curl >/dev/null 2>&1 || die "curl is required to download a release."
    if [ -z "$VERSION" ]; then
        # The newest `vX.Y.Z`, by version — not `releases/latest`: the desktop app publishes
        # its own `app-v*` releases in this repository (ADR-0027), and those are not the CLI.
        # Releases first, then tags, as scripts/install.sh does: a tag need not have a release.
        newest_tag() {
            "$PYTHON" -c '
import json, re, sys
key = sys.argv[1]
names = [r.get(key, "") for r in json.load(sys.stdin) if not r.get("draft") and not r.get("prerelease")]
tags = [t for t in names if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
print(max(tags, key=lambda t: tuple(int(p) for p in t[1:].split("."))) if tags else "")
' "$1"
        }
        VERSION="$(curl -fsSL "https://api.github.com/repos/$OWNER/$REPO/releases?per_page=50" | newest_tag tag_name || true)"
        [ -n "$VERSION" ] || VERSION="$(curl -fsSL "https://api.github.com/repos/$OWNER/$REPO/tags?per_page=100" | newest_tag name || true)"
        [ -n "$VERSION" ] || die "could not find a vX.Y.Z release or tag on GitHub. Pass --version, or --from a clone."
    fi
    say "Downloading $VERSION"
    curl -fsSL -o "$WORK/src.tar.gz" "https://github.com/$OWNER/$REPO/archive/refs/tags/$VERSION.tar.gz" \
        || die "could not download $VERSION."
    mkdir "$WORK/src"
    tar -xzf "$WORK/src.tar.gz" -C "$WORK/src" --strip-components 1
    SOURCE="$WORK/src"
fi

if [ ! -f "$SOURCE/scripts/cli/devteam" ] || [ ! -d "$SOURCE/scripts/lib/devteam" ]; then
    [ -n "$VERSION" ] && die "release $VERSION predates the devteam CLI, so there is nothing to install from it. Install from a clone of the main branch: bash scripts/install-cli.sh --from ."
    die "$SOURCE is not a dev-team-agents tree (no scripts/cli/devteam)."
fi

# ── The CLI ───────────────────────────────────────────────────────────────────
# Staged beside the target and swapped in, so a failed copy never leaves half a CLI.
mkdir -p "$CLI_HOME" "$BIN_DIR"
STAGE="$CLI_HOME/.scripts.new"
rm -rf "$STAGE"
mkdir -p "$STAGE/cli" "$STAGE/lib"
cp "$SOURCE/scripts/cli/devteam" "$STAGE/cli/devteam"
cp -R "$SOURCE/scripts/lib/devteam" "$STAGE/lib/devteam"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
# The interpreter verified above, by absolute path — as the Homebrew formula does. A GUI
# app starts the CLI with a minimal PATH, where `env python3` could find another Python.
"$PYTHON" - "$STAGE/cli/devteam" "$PYTHON" <<'PY'
import sys
path, python = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as handle:
    lines = handle.read().split("\n")
if lines and lines[0].startswith("#!"):
    lines[0] = "#!" + python
with open(path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines))
PY
chmod 755 "$STAGE/cli/devteam"
rm -rf "$CLI_HOME/scripts"
mv "$STAGE" "$CLI_HOME/scripts"
ln -sfn "$CLI_HOME/scripts/cli/devteam" "$BIN_DIR/devteam"
say "Installed $BIN_DIR/devteam"

# ── The framework ─────────────────────────────────────────────────────────────
set +e
OUTPUT="$("$BIN_DIR/devteam" store install --from "$SOURCE" 2>&1)"
STATUS=$?
set -e
case "$STATUS" in
    0) say "$OUTPUT" ;;
    "$EXIT_CONFLICT") say "That framework version is already in the store; left as it is." ;;
    *) printf '%s\n' "$OUTPUT" >&2; die "devteam store install failed (exit $STATUS)." ;;
esac

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) say "Add $BIN_DIR to your PATH to run devteam from a terminal (the desktop app also searches ~/.local/bin):"
       # shellcheck disable=SC2016  # `$PATH` is meant literally: the user's shell expands it.
       printf '    echo '\''export PATH="%s:$PATH"'\'' >> ~/.zshrc\n' "$BIN_DIR" ;;
esac
say "Done. Run: devteam doctor"
