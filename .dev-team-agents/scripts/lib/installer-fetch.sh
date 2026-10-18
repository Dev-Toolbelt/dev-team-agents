#!/usr/bin/env bash
# installer-fetch.sh — Shared "download and run install.sh" logic.
#
# Sourced by:
#   - scripts/update.sh    (upgrade to latest or to a pinned version)
#   - scripts/rollback.sh  (reinstall a previous version)
#
# Both scripts previously carried byte-for-byte copies of the HTTP tool
# detection, the GitHub coordinates, and the download-then-`bash` sequence.
# This file is the single source of truth for all three.
#
# Public interface (everything else is prefixed `_dta_`):
#   dta_http_get <url>                     → response body on stdout
#   dta_http_dl <dest> <url>               → writes the response to <dest>
#   dta_resolve_ref <version-arg>          → prints an immutable tag, or "main"
#   dta_fetch_installer <dest> <ref>       → download + verify install.sh
#   dta_installer_url <ref>                → the URL used for a given ref
#
# ── Integrity model, stated honestly ─────────────────────────────────────────
# `dta_fetch_installer` executes nothing; it only produces a file the caller
# then runs with bash. Before it hands that file back it enforces:
#
#   1. Transport      — HTTPS only, and the HTTP client must exit 0. Any
#                       failure is reported with the client's own stderr.
#   2. Pinned ref     — the installer is fetched from the SAME ref whose
#                       release is being installed, not from a moving `main`.
#                       For a rollback to v1.2.3 this means v1.2.3's installer
#                       runs, instead of whatever `main` happens to hold.
#   3. Shape + parse  — the payload must be a non-trivial bash script that
#                       `bash -n` accepts and that carries this project's
#                       markers. This is what catches the realistic corruption
#                       cases: truncated transfers, captive-portal/proxy HTML,
#                       and rate-limit or 404 bodies served with a 200.
#   4. Digest         — if a SHA-256 digest is available it MUST match, and a
#                       mismatch aborts (fail closed). A digest is taken from
#                       $DEVTEAM_INSTALLER_SHA256 when set, otherwise from
#                       scripts/install.sh.sha256 published at the same ref.
#
# What this does NOT do, so nobody mistakes it for more than it is: the
# project publishes no signatures and no out-of-band digests today, so an
# attacker who can write to the repository (or to a release tag) controls both
# the installer and any digest fetched from beside it, and can simply omit the
# digest file. Only publisher signing (minisign/GPG/Sigstore) with a key
# shipped separately from the payload would close that gap. Steps 1–3 are
# nonetheless real: they are what stands between a corrupt or substituted
# transfer and `bash <that file>`. Step 4 costs one request and gives the
# release process a working hook the moment it starts publishing digests.

GITHUB_OWNER="${GITHUB_OWNER:-Dev-Toolbelt}"
GITHUB_REPO="${GITHUB_REPO:-dev-team-agents}"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}"

# ── HTTP tool detection ──────────────────────────────────────────────────────
if command -v curl >/dev/null 2>&1; then
    dta_http_get() { curl -fsSL "$1"; }
    dta_http_dl()  { curl -fsSL -o "$1" "$2"; }
elif command -v wget >/dev/null 2>&1; then
    dta_http_get() { wget -qO- "$1"; }
    dta_http_dl()  { wget -qO "$1" "$2"; }
else
    dta_http_get() { echo "✗ Neither curl nor wget found." >&2; return 1; }
    dta_http_dl()  { echo "✗ Neither curl nor wget found." >&2; return 1; }
fi

dta_have_http_tool() {
    command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1
}

# ── SHA-256 ──────────────────────────────────────────────────────────────────
# Prints the digest of <file>, or nothing when no hashing tool is available.
dta_sha256() {
    local _file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$_file" 2>/dev/null | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$_file" 2>/dev/null | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 "$_file" 2>/dev/null | awk '{print $NF}'
    else
        return 0
    fi
}

# ── Ref resolution ───────────────────────────────────────────────────────────
# Turns the caller's version argument into the ref the installer is fetched
# from. A concrete version is used as-is (immutable tag). "latest" is resolved
# through the GitHub API to the newest release tag so that the installer and
# the payload it downloads come from the same release; if the API cannot be
# reached the function falls back to "main" — the pre-existing behaviour — so
# the upgrade path keeps working on a rate-limited or offline-ish network.
dta_resolve_ref() {
    local _want="${1:-latest}"
    local _json _tag=""

    if [ -z "$_want" ] || [ "$_want" = "main" ]; then
        printf 'main\n'
        return 0
    fi

    if [ "$_want" != "latest" ]; then
        if ! dta_is_safe_ref "$_want"; then
            echo "✗ Refusing to use unsafe version/ref: '$_want'" >&2
            return 1
        fi
        printf '%s\n' "$_want"
        return 0
    fi

    _json=$(dta_http_get "${GITHUB_API}/releases/latest" 2>/dev/null || true)
    _tag=$(printf '%s' "$_json" | grep '"tag_name"' | head -1 \
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/' || true)

    if [ -z "$_tag" ]; then
        _json=$(dta_http_get "${GITHUB_API}/tags" 2>/dev/null || true)
        _tag=$(printf '%s' "$_json" | grep '"name"' | head -1 \
            | sed 's/.*"name": *"\([^"]*\)".*/\1/' || true)
    fi

    if [ -z "$_tag" ] || ! dta_is_safe_ref "$_tag"; then
        printf 'main\n'
        return 0
    fi
    printf '%s\n' "$_tag"
}

# A ref goes straight into a URL path — keep it boring.
dta_is_safe_ref() {
    local _ref="$1"
    [ -n "$_ref" ] || return 1
    case "$_ref" in
        *..*|*/*|*' '*) return 1 ;;
    esac
    printf '%s' "$_ref" | grep -Eq '^[A-Za-z0-9._-]+$'
}

dta_installer_url() {
    printf '%s/%s/scripts/install.sh\n' "$GITHUB_RAW" "$1"
}

# ── Payload verification ─────────────────────────────────────────────────────
# Rejects anything that is not plausibly this project's installer. Returns
# non-zero (fail closed) on every doubt.
dta_verify_installer() {
    local _file="$1"
    local _ref="$2"
    local _size

    if [ ! -s "$_file" ]; then
        echo "✗ Downloaded installer is empty." >&2
        return 1
    fi

    _size=$(wc -c <"$_file" | tr -d '[:space:]')
    if [ "${_size:-0}" -lt 2048 ]; then
        echo "✗ Downloaded installer is implausibly small (${_size} bytes)." >&2
        echo "  This is usually a 404 page, a rate-limit body, or a truncated transfer." >&2
        return 1
    fi

    if ! head -1 "$_file" | grep -q '^#!.*sh'; then
        echo "✗ Downloaded installer does not start with a shell shebang." >&2
        echo "  The server most likely returned an error page instead of the script." >&2
        return 1
    fi

    if ! grep -q 'dev-team-agents' "$_file" || ! grep -q 'INSTALL_DIR=' "$_file"; then
        echo "✗ Downloaded installer does not look like the dev-team-agents installer." >&2
        return 1
    fi

    # A truncated script very often still starts correctly — this is the check
    # that actually catches it.
    if ! bash -n "$_file" 2>/dev/null; then
        echo "✗ Downloaded installer is not valid bash (truncated or corrupted download)." >&2
        return 1
    fi

    dta_verify_digest "$_file" "$_ref"
}

# Verifies <file> against a SHA-256 digest when one can be obtained.
# Mismatch → abort. No digest available → proceed (see the integrity model
# note at the top of this file; the project publishes none today).
dta_verify_digest() {
    local _file="$1"
    local _ref="$2"
    local _expected="${DEVTEAM_INSTALLER_SHA256:-}"
    local _actual _tmp

    if [ -z "$_expected" ]; then
        _tmp=$(mktemp)
        if dta_http_dl "$_tmp" "${GITHUB_RAW}/${_ref}/scripts/install.sh.sha256" 2>/dev/null; then
            _expected=$(awk 'NR==1{print $1}' "$_tmp" 2>/dev/null || true)
        fi
        rm -f "$_tmp"
    fi

    # Not a digest (missing file, HTML body, empty) → nothing to check against.
    printf '%s' "$_expected" | grep -Eq '^[a-fA-F0-9]{64}$' || return 0

    _actual=$(dta_sha256 "$_file")
    if [ -z "$_actual" ]; then
        echo "✗ A SHA-256 digest was published for this release but no hashing tool" >&2
        echo "  (sha256sum / shasum / openssl) is available to verify it." >&2
        return 1
    fi

    if [ "$(printf '%s' "$_actual" | tr 'A-F' 'a-f')" != "$(printf '%s' "$_expected" | tr 'A-F' 'a-f')" ]; then
        echo "✗ SHA-256 MISMATCH on the downloaded installer — aborting." >&2
        echo "    expected: $_expected" >&2
        echo "    actual:   $_actual" >&2
        return 1
    fi

    echo "→ Installer SHA-256 verified."
    return 0
}

# ── Fetch ────────────────────────────────────────────────────────────────────
# dta_fetch_installer <dest-file> <ref>
# Downloads install.sh from <ref> into <dest-file> and verifies it. Any failure
# leaves <dest-file> unusable and returns non-zero — the caller must not run it.
dta_fetch_installer() {
    local _dest="$1"
    local _ref="$2"
    local _url _err _rc=0

    if ! dta_is_safe_ref "$_ref"; then
        echo "✗ Refusing to fetch the installer from unsafe ref: '$_ref'" >&2
        return 1
    fi

    _url=$(dta_installer_url "$_ref")
    _err=$(mktemp)

    dta_http_dl "$_dest" "$_url" 2>"$_err" || _rc=$?

    if [ "$_rc" -ne 0 ]; then
        echo "✗ Failed to download the installer (HTTP client exit $_rc)." >&2
        echo "  URL: $_url" >&2
        if [ -s "$_err" ]; then
            echo "  Reported by the HTTP client:" >&2
            awk 'NF && !seen[$0]++' "$_err" | head -5 | sed 's|^|    |' >&2
        fi
        if [ "$_ref" != "main" ]; then
            echo "  Check that the version tag exists:" >&2
            echo "    https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases" >&2
        fi
        rm -f "$_err"
        return 1
    fi
    rm -f "$_err"

    dta_verify_installer "$_dest" "$_ref"
}
