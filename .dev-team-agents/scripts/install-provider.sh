#!/bin/bash
# install-provider.sh — Bootstrap cross-CLI provider support (opencode or Codex)
# into a project that already has dev-team-agents installed for Claude Code, OR
# that has nothing yet (will create the framework install on the fly).
#
# curl-pipeable. Fetches ONLY the cross-CLI plumbing from GitHub and runs the
# matching installer. Slim Claude installs do not bundle this plumbing, so
# this script is the entry point for adding opencode or Codex support.
#
# Usage:
#   bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) opencode
#   bash <(curl -sSL .../install-provider.sh) codex
#   bash <(curl -sSL .../install-provider.sh) opencode --source /abs/path/to/dev-team-agents-clone   # dev mode
#   bash <(curl -sSL .../install-provider.sh) opencode --version v1.11.0                              # pin a version
#   bash <(curl -sSL .../install-provider.sh) codex --adopt       # quarantine same-named project files first
#
# What it does:
#   1. Parses the provider arg (opencode | codex).
#   2. If --source is passed, uses that local clone directly.
#      Otherwise downloads a tarball of the requested version (or main).
#   3. Extracts into a temp staging dir and runs
#      `<staging>/scripts/install-<provider>.sh --source <staging>`.
#   4. Cleans up temp dir. Install artefacts land in the project's
#      .opencode/ or .codex/ (and may extend .opencode/opencode.json).

set -euo pipefail

PROVIDER="${1:-}"
shift || true
if [[ "$PROVIDER" != "opencode" && "$PROVIDER" != "codex" ]]; then
  echo "install-provider: ERROR: first arg must be 'opencode' or 'codex' (got '$PROVIDER')" >&2
  echo "  Usage:" >&2
  echo "    bash <(curl -sSL .../install-provider.sh) opencode" >&2
  echo "    bash <(curl -sSL .../install-provider.sh) codex" >&2
  echo "    bash <(curl -sSL .../install-provider.sh) opencode --source /abs/path" >&2
  echo "    bash <(curl -sSL .../install-provider.sh) opencode --version vX.Y.Z" >&2
  exit 2
fi

# ── parse remaining flags ────────────────────────────────────────────
SOURCE_OVERRIDE=""
VERSION="main"
INSTALLER_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_OVERRIDE="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    --adopt) INSTALLER_ARGS+=("--adopt"); shift ;;
    *) echo "install-provider: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── locate or fetch dev-team-agents source ───────────────────────────
STAGING=""

if [[ -n "$SOURCE_OVERRIDE" ]]; then
  STAGING="$(cd "$SOURCE_OVERRIDE" && pwd)"
  echo "install-provider: using local source: $STAGING"
else
  GITHUB_OWNER="Dev-Toolbelt"
  GITHUB_REPO="dev-team-agents"
  if [[ "$VERSION" == "main" ]]; then
    TARBALL_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/heads/main.tar.gz"
    echo "install-provider: fetching latest (main) tarball…"
  else
    TARBALL_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/tags/${VERSION}.tar.gz"
    echo "install-provider: fetching version $VERSION…"
  fi

  if command -v curl >/dev/null 2>&1; then
    HTTP_GET_FILE() { curl -fsSL -o "$2" "$1"; }
  elif command -v wget >/dev/null 2>&1; then
    HTTP_GET_FILE() { wget -qO "$2" "$1"; }
  else
    echo "install-provider: ERROR: curl or wget required." >&2; exit 1
  fi

  TMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TMP_DIR"' EXIT
  TMP_TAR="$TMP_DIR/archive.tar.gz"

  if ! HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>/dev/null; then
    echo "install-provider: ERROR: failed to download $TARBALL_URL" >&2
    exit 1
  fi

  mkdir -p "$TMP_DIR/extracted"
  tar -xzf "$TMP_TAR" -C "$TMP_DIR/extracted"
  EXTRACTED_ROOT=$(find "$TMP_DIR/extracted" -maxdepth 1 -mindepth 1 -type d | head -1)
  if [[ -z "$EXTRACTED_ROOT" ]]; then
    echo "install-provider: ERROR: tarball extraction produced no directory." >&2; exit 1
  fi
  STAGING="$EXTRACTED_ROOT"
fi

INSTALLER="$STAGING/scripts/install-${PROVIDER}.sh"
if [[ ! -f "$INSTALLER" ]]; then
  echo "install-provider: ERROR: $INSTALLER not found in source." >&2; exit 1
fi

# ── account gate (ADR-0029 SR-30) ───────────────────────────────────
# The delegated installer gates itself too; this covers a pinned older tarball whose
# installer predates the gate. The gate comes from THIS script's own tree, never from the
# downloaded one, so an old `--version` cannot opt out of it or choose its own gate_mode
# (SR-42). Only when this script runs outside any tree (piped from curl) is the staged lib
# used; with neither, the CLI on PATH decides through `ag`'s own fallback.
_IP_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
_IP_GATE_SCRIPTS=""
for _ip_candidate in "$_IP_SELF_DIR" "$STAGING/scripts"; do
  if [[ -n "$_ip_candidate" && -f "$_ip_candidate/lib/auth-gate.sh" ]]; then
    _IP_GATE_SCRIPTS="$_ip_candidate"; break
  fi
done
if [[ -n "$_IP_GATE_SCRIPTS" ]]; then
  # shellcheck source=lib/auth-gate.sh
  source "$_IP_GATE_SCRIPTS/lib/auth-gate.sh"
  ag_gate install-provider "$_IP_GATE_SCRIPTS" || exit $?
elif command -v devteam >/dev/null 2>&1; then
  _ip_rc=0
  _ip_out="$(devteam auth check --json 2>/dev/null)" || _ip_rc=$?
  if [[ "$_ip_rc" != 0 ]] && printf '%s' "$_ip_out" | grep -q '"gate_mode": *"enforce"'; then
    echo "install-provider: blocked: the account is not entitled. Run \`devteam auth login\`, then re-run." >&2
    exit 5
  fi
else
  echo "install-provider: account check skipped (no gate library and no devteam CLI)" >&2
fi

# ── run the provider installer with --source ────────────────────────
bash "$INSTALLER" --source "$STAGING" ${INSTALLER_ARGS[@]+"${INSTALLER_ARGS[@]}"}